"""
locust_test.py — Load testing for the FastAPI recommendation service.

Usage:
  # Interactive web UI:
  locust -f load_testing/locust_test.py --host http://localhost:8000

  # Headless CI mode (1000 users, ramp 50/s, run 60s):
  locust -f load_testing/locust_test.py --host http://localhost:8000 \
         --headless -u 1000 -r 50 --run-time 60s --csv=results/load_test

Target metrics:
  - Throughput : 500+ RPS
  - p95 latency: < 50 ms
  - Error rate  : < 1%
"""

import random
from locust import HttpUser, task, between, events

VISITOR_IDS = [str(i) for i in range(1, 5001)]
ITEM_IDS    = [str(i) for i in range(1, 1001)]
EVENTS      = ["view", "addtocart", "transaction"]


class RecommendationUser(HttpUser):
    """
    Realistic traffic mix:
      80 % → GET /recommend/{visitor_id}      (hot read path, should hit Redis)
      15 % → POST /interaction                (write path, invalidates cache)
       4 % → GET /ab-test/metrics             (analytics, low-frequency)
       1 % → GET /health                      (infrastructure probe)
    """
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.visitor_id = random.choice(VISITOR_IDS)

    @task(8)
    def get_recommendations(self):
        vid = random.choice(VISITOR_IDS)
        with self.client.get(
            f"/recommend/{vid}",
            name="/recommend/[visitor_id]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(2)
    def log_interaction(self):
        payload = {
            "visitor_id": random.choice(VISITOR_IDS),
            "item_id":    random.choice(ITEM_IDS),
            "event":      random.choice(EVENTS),
        }
        with self.client.post(
            "/interaction/",
            json=payload,
            name="POST /interaction",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"HTTP {resp.status_code}")

    @task(1)
    def ab_metrics(self):
        self.client.get("/ab-test/metrics", name="GET /ab-test/metrics")

    @task(1)
    def health(self):
        self.client.get("/health", name="GET /health")


class BurstUser(HttpUser):
    """
    Burst traffic — minimal wait, used to find throughput ceiling.
    Increase weight with  --user-classes BurstUser  flag.
    """
    wait_time = between(0.01, 0.05)

    @task
    def burst_recommend(self):
        vid = random.choice(VISITOR_IDS)
        self.client.get(f"/recommend/{vid}", name="/recommend/[visitor_id] (burst)")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "=" * 60)
    print("  RetailRocket Recommendation Engine — Locust Load Test")
    print("  Target: 500+ RPS | p95 < 50 ms | Error rate < 1%")
    print("=" * 60 + "\n")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    stats = environment.stats.total
    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print(f"  Total Requests  : {stats.num_requests:,}")
    print(f"  Failures        : {stats.num_failures:,}  ({100 * stats.fail_ratio:.1f}%)")
    print(f"  RPS (peak)      : {stats.max_rps:.1f}")
    print(f"  Avg latency     : {stats.avg_response_time:.1f} ms")
    print(f"  p95 latency     : {stats.get_response_time_percentile(0.95):.1f} ms")
    print(f"  p99 latency     : {stats.get_response_time_percentile(0.99):.1f} ms")
    print("=" * 60 + "\n")
