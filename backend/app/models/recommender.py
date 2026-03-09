"""
recommender.py — Memory-efficient Item-Based Collaborative Filtering.

Key design decision:
  The full item×item cosine similarity matrix for RetailRocket (235k items) would
  require 235k × 235k × 8 bytes ≈ 338 GiB of RAM — completely infeasible.

  Solution: compute similarity in BATCHES and store only the top-K neighbours
  per item as a sparse dict  {item_idx -> [(neighbour_idx, score), ...]}.
  This reduces memory from O(N²) to O(N × K_neighbours), e.g. 235k items with
  K=50 neighbours ≈ ~90 MB — fits on any laptop.

  Inference: for a visitor, look up neighbours only for items they interacted
  with, aggregate scores, return top-N.
"""

import numpy as np
import pickle
import logging
from typing import List, Dict, Optional, Tuple
from scipy.sparse import csr_matrix
from sklearn.preprocessing import normalize

logger = logging.getLogger(__name__)

EVENT_WEIGHTS = {
    "view": 1.0,
    "addtocart": 3.0,
    "transaction": 5.0,
}

# Number of nearest neighbours stored per item.
# 50 gives a good precision/memory trade-off; raise to 100 for better recall.
DEFAULT_K_NEIGHBOURS = 50
# Batch size for similarity computation — tune down if RAM is tight.
DEFAULT_BATCH_SIZE = 500


class CollaborativeFilteringRecommender:
    """
    Item-Based CF with sparse top-K neighbourhood storage.

    Memory footprint: O(n_items × k_neighbours) instead of O(n_items²).
    Compatible with 200k+ item catalogues on a standard developer machine.
    """

    def __init__(
        self,
        top_n: int = 10,
        k_neighbours: int = DEFAULT_K_NEIGHBOURS,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self.top_n = top_n
        self.k_neighbours = k_neighbours
        self.batch_size = batch_size

        # Sparse neighbourhood: item_idx → array of (neighbour_idx, similarity)
        # stored as two parallel arrays for fast numpy lookup.
        self._neighbour_indices: Optional[np.ndarray] = None  # shape (n_items, K)
        self._neighbour_scores:  Optional[np.ndarray] = None  # shape (n_items, K)

        self.user_item_matrix: Optional[csr_matrix] = None
        self.item_ids:   List[str] = []
        self.user_ids:   List[str] = []
        self._item_index: Dict[str, int] = {}
        self._user_index: Dict[str, int] = {}
        self.is_trained = False

    # ─────────────────────────────────────────────────────────────── fit ──

    def fit(self, interactions: List[Dict]) -> "CollaborativeFilteringRecommender":
        """Train on a list of {visitor_id, item_id, event} dicts."""
        logger.info(f"Building interaction map from {len(interactions):,} events...")

        # ── 1. Weighted interaction map ──────────────────────────────────
        interaction_map: Dict[Tuple[str, str], float] = {}
        for row in interactions:
            uid = str(row["visitor_id"])
            iid = str(row["item_id"])
            w   = EVENT_WEIGHTS.get(str(row.get("event", "view")), 1.0)
            key = (uid, iid)
            interaction_map[key] = interaction_map.get(key, 0.0) + w

        visitors = list({k[0] for k in interaction_map})
        items    = list({k[1] for k in interaction_map})
        n_users, n_items = len(visitors), len(items)

        self.user_ids    = visitors
        self.item_ids    = items
        self._user_index = {u: i for i, u in enumerate(visitors)}
        self._item_index = {it: i for i, it in enumerate(items)}

        logger.info(f"  {n_users:,} visitors × {n_items:,} items")

        # ── 2. Build sparse CSR user-item matrix ─────────────────────────
        rows, cols, data = [], [], []
        for (uid, iid), weight in interaction_map.items():
            rows.append(self._user_index[uid])
            cols.append(self._item_index[iid])
            data.append(weight)

        self.user_item_matrix = csr_matrix(
            (data, (rows, cols)), shape=(n_users, n_items), dtype=np.float32
        )

        # ── 3. Sparse top-K item similarity ──────────────────────────────
        # item_matrix shape: (n_items, n_users) — L2-normalised rows
        item_matrix = self.user_item_matrix.T.tocsr()
        item_matrix_norm = normalize(item_matrix, norm="l2", axis=1)  # still sparse

        K = min(self.k_neighbours, n_items - 1)
        logger.info(
            f"Computing top-{K} neighbours for {n_items:,} items "
            f"in batches of {self.batch_size} ..."
        )

        neighbour_indices = np.zeros((n_items, K), dtype=np.int32)
        neighbour_scores  = np.zeros((n_items, K), dtype=np.float32)

        for start in range(0, n_items, self.batch_size):
            end   = min(start + self.batch_size, n_items)
            batch = item_matrix_norm[start:end]  # (batch, n_users) sparse

            # Dense dot: (batch, n_users) × (n_users, n_items) → (batch, n_items)
            sim_block = (batch @ item_matrix_norm.T).toarray()  # float32-ish

            # Zero self-similarity
            for local_i, global_i in enumerate(range(start, end)):
                sim_block[local_i, global_i] = 0.0

            # Top-K per row (argpartition is O(n) vs argsort O(n log n))
            if n_items > K:
                top_k_idx = np.argpartition(sim_block, -K, axis=1)[:, -K:]
            else:
                top_k_idx = np.tile(np.arange(n_items), (end - start, 1))

            for local_i in range(end - start):
                idx   = top_k_idx[local_i]
                scores = sim_block[local_i, idx]
                order  = np.argsort(scores)[::-1]
                neighbour_indices[start + local_i] = idx[order]
                neighbour_scores [start + local_i] = scores[order]

            if (start // self.batch_size) % 10 == 0:
                pct = 100 * end / n_items
                logger.info(f"  Similarity progress: {end:,}/{n_items:,}  ({pct:.0f}%)")

        self._neighbour_indices = neighbour_indices
        self._neighbour_scores  = neighbour_scores
        self.is_trained = True

        mem_mb = (neighbour_indices.nbytes + neighbour_scores.nbytes) / 1024 / 1024
        logger.info(f"Training complete. Neighbourhood index: {mem_mb:.1f} MB")
        return self

    # ─────────────────────────────────────────────────────────────── recommend ──

    def recommend(self, visitor_id: str) -> List[Dict]:
        """Return top-N recommendations for visitor_id."""
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call fit() first.")

        if visitor_id not in self._user_index:
            return self._popular_items()

        user_idx    = self._user_index[visitor_id]
        user_vector = self.user_item_matrix[user_idx]   # sparse (1, n_items)
        interacted  = set(user_vector.indices)           # item indices with weight > 0

        # Accumulate neighbour scores weighted by interaction weight
        score_accum: Dict[int, float] = {}
        user_data = zip(user_vector.indices, user_vector.data)
        for item_idx, weight in user_data:
            nbr_idx    = self._neighbour_indices[item_idx]   # (K,)
            nbr_scores = self._neighbour_scores[item_idx]    # (K,)
            for ni, ns in zip(nbr_idx, nbr_scores):
                if ni not in interacted and ns > 0:
                    score_accum[ni] = score_accum.get(ni, 0.0) + float(weight * ns)

        if not score_accum:
            return self._popular_items()

        # Top-N
        sorted_items = sorted(score_accum.items(), key=lambda x: x[1], reverse=True)
        return [
            {"item_id": self.item_ids[idx], "score": round(score, 4)}
            for idx, score in sorted_items[: self.top_n]
        ]

    # ─────────────────────────────────────────────────────────────── helpers ──

    def _popular_items(self) -> List[Dict]:
        """Cold-start fallback: return globally popular items."""
        if self.user_item_matrix is None:
            return []
        popularity = np.asarray(self.user_item_matrix.sum(axis=0)).flatten()
        k = min(self.top_n, len(popularity))
        top_idx = np.argpartition(popularity, -k)[-k:]
        top_idx = top_idx[np.argsort(popularity[top_idx])[::-1]]
        return [
            {"item_id": self.item_ids[i], "score": float(popularity[i]), "cold_start": True}
            for i in top_idx
        ]

    def precision_at_k(self, test_interactions: List[Dict], k: int = 10) -> float:
        test_map: Dict[str, set] = {}
        for row in test_interactions:
            test_map.setdefault(str(row["visitor_id"]), set()).add(str(row["item_id"]))
        scores = []
        for uid, relevant in test_map.items():
            recs     = {r["item_id"] for r in self.recommend(uid)[:k]}
            scores.append(len(recs & relevant) / k)
        return float(np.mean(scores)) if scores else 0.0

    # ─────────────────────────────────────────────────────────────── I/O ──

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(f"Model saved → {path}")

    @classmethod
    def load(cls, path: str) -> "CollaborativeFilteringRecommender":
        with open(path, "rb") as f:
            model = pickle.load(f)
        logger.info(f"Model loaded ← {path}")
        return model