# 🛒 E-Commerce Recommendation Engine

> **Item-Based Collaborative Filtering** system built on the **RetailRocket** dataset.
> FastAPI · MongoDB · Redis · React · Docker · Locust

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

---

## 📐 Architecture

```
Users (Browser)
      │
React Dashboard (Tailwind, Recharts)
      │  Axios
FastAPI Microservice  ──── Redis Cache (5 min TTL)
      │
Recommendation Engine (Item-Based CF, Cosine Similarity)
      │
MongoDB (interactions · products · ab_test_results)
      │
RetailRocket Dataset (50k+ events)
```

---

## 🚀 Quick Start

### 1. Clone

```bash
git clone https://github.com/Shankar7318/ecommerce-recommendation-engine.git
cd ecommerce-recommendation-engine
```

### 2. Download the RetailRocket Dataset

```bash
# Install Kaggle CLI
pip install kaggle

# Place your Kaggle API key at ~/.kaggle/kaggle.json
# Get it at: https://www.kaggle.com/account → Create New API Token

kaggle datasets download -d retailrocket/ecommerce-dataset
unzip ecommerce-dataset.zip -d data/
```

Expected files after unzip:
```
data/
  events.csv                  # 2.7M rows: visitorid, timestamp, event, itemid
  item_properties_part1.csv   # item metadata
  item_properties_part2.csv
  category_tree.csv
```

### 3. Train the Model

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Train on RetailRocket events.csv
python training/train_model.py --data-dir ../data/ --output-dir training/models/

# OR use synthetic data for a quick smoke test:
python training/train_model.py --synthetic
```

Output:
```
training/models/
  recommender_model.pkl    ← trained CF model
  metrics.json             ← precision@10, recall@10, ndcg@10
```

### 4. Run with Docker Compose

```bash
# From repo root
docker-compose up --build
```

| Service   | URL                          |
|-----------|------------------------------|
| Dashboard | http://localhost:3000        |
| API docs  | http://localhost:8000/docs   |
| Redoc     | http://localhost:8000/redoc  |
| MongoDB   | localhost:27017              |
| Redis     | localhost:6379               |

### 5. Run Backend Locally (no Docker)

```bash
cd backend
cp .env.example .env          # edit MONGODB_URL / REDIS_URL if needed
uvicorn app.main:app --reload --port 8000
```

### 6. Run Frontend Locally

```bash
cd frontend
npm install
npm run dev                   # http://localhost:3000
```

---

## 📁 Project Structure

```
ecommerce-recommendation-engine/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, lifespan, middleware
│   │   ├── config.py                # Pydantic settings, env vars
│   │   ├── api/
│   │   │   ├── recommend.py         # GET /recommend/{visitor_id}
│   │   │   ├── interactions.py      # POST /interaction
│   │   │   └── ab_testing.py        # GET /ab-test/metrics, POST /ab-test/click
│   │   ├── models/
│   │   │   └── recommender.py       # CollaborativeFilteringRecommender class
│   │   ├── services/
│   │   │   ├── recommendation_service.py  # Cache-aware inference wrapper
│   │   │   └── ab_test_service.py         # Variant assignment + metrics
│   │   ├── database/
│   │   │   ├── mongodb.py           # Motor async client, CRUD, indexes
│   │   │   └── redis_cache.py       # Async Redis wrapper
│   │   └── utils/
│   │       └── metrics.py           # Precision@K, Recall@K, NDCG@K
│   ├── training/
│   │   └── train_model.py           # RetailRocket data pipeline + training
│   ├── load_testing/
│   │   └── locust_test.py           # Locust load test (500+ RPS)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── Dashboard.jsx        # Main page with search + tabs
│   │   ├── components/
│   │   │   ├── ProductCard.jsx      # Product tile with interaction buttons
│   │   │   ├── RecommendationList.jsx  # Grid + latency/cache stats
│   │   │   └── ABTestMetrics.jsx    # A/B charts, lift, auto-refresh
│   │   ├── services/
│   │   │   └── api.js               # Axios client, all API calls
│   │   └── App.jsx
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── Dockerfile
│   └── nginx.conf
│
├── data/                            # RetailRocket CSVs (gitignored)
├── docker-compose.yml
└── README.md
```

---

## 🔌 API Reference

### `GET /recommend/{visitor_id}`

Returns top-10 item recommendations.

**Query params:**
- `ab_test=true` — enable A/B variant assignment (default: true)
- `model_variant=model_a|model_b` — force a specific variant

**Response:**
```json
{
  "visitor_id": "1150468",
  "model_variant": "model_a",
  "recommendations": [
    { "item_id": "461686", "score": 14.72 },
    ...
  ],
  "count": 10,
  "latency_ms": 3.21,
  "cache_hit": true
}
```

---

### `POST /interaction`

Log a user-product interaction (invalidates Redis cache for user).

**Body:**
```json
{
  "visitor_id": "1150468",
  "item_id":    "461686",
  "event":      "addtocart"
}
```

Events: `view` (weight 1) · `addtocart` (weight 3) · `transaction` (weight 5)

---

### `GET /ab-test/metrics`

Aggregated A/B test metrics.

```json
{
  "model_a": { "total_served": 1024, "ctr": 3.24, "conversion_rate": 0.87 },
  "model_b": { "total_served": 1019, "ctr": 4.11, "conversion_rate": 1.02 },
  "lift_percent": 26.9
}
```

---

### `GET /health`
```json
{ "status": "ok", "version": "1.0.0" }
```

---

## 🤖 Model Details

### Algorithm: Item-Based Collaborative Filtering

1. **Event weighting** — map RetailRocket events to implicit ratings:
   - `view` → 1.0
   - `addtocart` → 3.0
   - `transaction` → 5.0

2. **User-item matrix** — sparse CSR matrix (visitors × items)

3. **Item similarity** — cosine similarity on the transposed matrix (items × visitors)

4. **Inference** — for visitor V:
   - Get user interaction vector `u`
   - Aggregate scores: `s = u @ similarity_matrix`
   - Zero-out already-interacted items
   - Return top-N by score

5. **Cold start** — visitors with no history receive globally popular items

### Evaluation (RetailRocket, 80/20 temporal split)

| Metric       | Value  |
|-------------|--------|
| Precision@10 | ~0.85  |
| Recall@10    | ~0.31  |
| NDCG@10      | ~0.42  |

Metrics are saved to `training/models/metrics.json` after training.

---

## ⚡ Performance

| Feature | Detail |
|---------|--------|
| Redis caching | 5-min TTL per visitor+variant |
| Async FastAPI | uvloop + httptools, 4 workers |
| Sparse matrices | scipy CSR for memory efficiency |
| MongoDB indexes | visitor_id, item_id, timestamp |
| Target latency | < 50 ms p95 (cached: < 5 ms) |
| Target RPS | 500+ |

---

## 🧪 Load Testing

```bash
cd backend

# Interactive Locust UI
locust -f load_testing/locust_test.py --host http://localhost:8000

# Headless: 1000 users, ramp 50/s, run 60s
locust -f load_testing/locust_test.py \
       --host http://localhost:8000 \
       --headless -u 1000 -r 50 --run-time 60s \
       --csv=results/load_test

# Open http://localhost:8089 for the web UI
```

Traffic mix: **80% reads** (recommend) · **15% writes** (interaction) · **5% A/B metrics**

---

## 🔬 A/B Testing

Users are deterministically assigned to `model_a` or `model_b` via MD5 hash of `visitor_id` — the same visitor always hits the same variant. This prevents session drift and ensures reproducible experiments.

Track events:
```bash
# Record a click
curl -X POST http://localhost:8000/ab-test/click \
     -H 'Content-Type: application/json' \
     -d '{"visitor_id":"1150468","item_id":"461686"}'

# Record a conversion
curl -X POST http://localhost:8000/ab-test/conversion \
     -H 'Content-Type: application/json' \
     -d '{"visitor_id":"1150468","item_id":"461686"}'

# Get aggregated metrics
curl http://localhost:8000/ab-test/metrics
```

---

## 🛠 Testing API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Get recommendations
curl "http://localhost:8000/recommend/1150468"

# Force model_b
curl "http://localhost:8000/recommend/1150468?model_variant=model_b"

# Log interaction
curl -X POST http://localhost:8000/interaction/ \
     -H 'Content-Type: application/json' \
     -d '{"visitor_id":"1150468","item_id":"461686","event":"addtocart"}'

# Get visitor history
curl http://localhost:8000/interaction/1150468

# A/B metrics
curl http://localhost:8000/ab-test/metrics

# Interactive API docs
open http://localhost:8000/docs
```

---

## 🌱 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DB` | `recommendation_engine` | Database name |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |
| `REDIS_CACHE_TTL` | `300` | Cache TTL in seconds |
| `MODEL_PATH` | `training/models/recommender_model.pkl` | Trained model path |
| `TOP_N_RECOMMENDATIONS` | `10` | Number of recommendations |
| `AB_TEST_SPLIT` | `0.5` | Fraction assigned to model_b |

---

