"""Small standard-library load test for the public health endpoint.

Usage:
    python scripts/load_test.py http://127.0.0.1:8000/core/healthz/ 20 100

Arguments: URL, concurrent workers, total requests.
"""
import concurrent.futures
import statistics
import sys
import time
import urllib.request

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/core/healthz/"
workers = int(sys.argv[2]) if len(sys.argv) > 2 else 10
total = int(sys.argv[3]) if len(sys.argv) > 3 else 100


def one(_):
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            response.read()
            return (time.perf_counter() - start) * 1000, response.status
    except Exception:
        return None, 0

with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
    results = list(pool.map(one, range(total)))

latencies = [latency for latency, status in results if latency is not None]
errors = sum(1 for latency, status in results if status >= 500 or latency is None)

print(f"requests={total} workers={workers}")
print(f"success={len(latencies)} errors={errors}")
if latencies:
    print(f"avg_ms={statistics.mean(latencies):.2f}")
    print(f"p95_ms={sorted(latencies)[int(len(latencies) * 0.95) - 1]:.2f}")
print(f"error_rate={errors / total * 100:.2f}%")

raise SystemExit(1 if errors else 0)
