#!/usr/bin/env python3
"""
Benchmark all 3 implementations: REST, Partial gRPC, Full gRPC + PostgreSQL.

Usage:
    python bench_all.py <label> <base_url> [num_requests]

Examples:
    python bench_all.py "REST" http://localhost:8000 200
    python bench_all.py "Partial gRPC" http://localhost:8000 200
    python bench_all.py "Full gRPC + PG" http://localhost:8000 200
"""

import json
import sys
import time
import statistics
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SAMPLE_PAYLOAD = {
    "first_name": "Benchmark",
    "last_name": "Test",
    "phone_number": "+919876543210",
    "age": 30,
    "gender": "Male",
    "nationality": "Indian",
    "country": "India",
    "city": "Mathura",
    "state": "Uttar Pradesh",
    "email": "bench@test.com",
    "pincode": "281001",
}


def _post(url: str, data: dict) -> tuple[float, int, bytes]:
    """POST JSON; return (elapsed_seconds, status, body_bytes)."""
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req) as resp:
        resp_body = resp.read()
    elapsed = time.perf_counter() - t0
    return elapsed, resp.status, resp_body


def _get(url: str) -> tuple[float, int, bytes]:
    """GET; return (elapsed_seconds, status, body_bytes)."""
    req = urllib.request.Request(url)
    t0 = time.perf_counter()
    with urllib.request.urlopen(req) as resp:
        resp_body = resp.read()
    elapsed = time.perf_counter() - t0
    return elapsed, resp.status, resp_body


def pct(values: list[float], p: int) -> float:
    """Percentile from sorted values."""
    values_sorted = sorted(values)
    idx = int(len(values_sorted) * p / 100)
    idx = min(idx, len(values_sorted) - 1)
    return values_sorted[idx]


def run_benchmark(label: str, base_url: str, n: int) -> dict:
    api = f"{base_url}/api/satsangis"

    print(f"\n{'='*60}")
    print(f"  Benchmarking: {label}")
    print(f"  URL: {base_url}  |  Requests: {n}")
    print(f"{'='*60}")

    # ----- 1. Health check -----
    try:
        _get(api)
    except Exception as e:
        print(f"  ❌ Server not reachable: {e}")
        return {}

    # ----- 2. CREATE latency -----
    print(f"\n  [1/5] CREATE latency ({n} requests)...")
    create_times = []
    create_response_sizes = []
    create_request_sizes = []
    req_body = json.dumps(SAMPLE_PAYLOAD).encode()
    for i in range(n):
        elapsed, status, body = _post(api, SAMPLE_PAYLOAD)
        create_times.append(elapsed * 1000)  # ms
        create_response_sizes.append(len(body))
        create_request_sizes.append(len(req_body))
        if (i + 1) % 50 == 0:
            print(f"        {i+1}/{n} done")

    # ----- 3. SEARCH latency (cold: different queries) -----
    print(f"\n  [2/5] SEARCH latency ({n} requests)...")
    search_times = []
    search_response_sizes = []
    queries = ["Benchmark", "Test", "Mathura", "+919876", "bench@test", "281001", "Male"]
    for i in range(n):
        q = queries[i % len(queries)]
        elapsed, status, body = _get(f"{api}?q={q}")
        search_times.append(elapsed * 1000)
        search_response_sizes.append(len(body))
        if (i + 1) % 50 == 0:
            print(f"        {i+1}/{n} done")

    # ----- 4. LIST ALL latency -----
    print(f"\n  [3/5] LIST ALL latency (20 requests)...")
    list_times = []
    list_sizes = []
    for i in range(20):
        elapsed, status, body = _get(api)
        list_times.append(elapsed * 1000)
        list_sizes.append(len(body))

    # ----- 5. Throughput (burst) -----
    print(f"\n  [4/5] Throughput burst ({n} creates)...")
    t0 = time.perf_counter()
    for i in range(n):
        _post(api, SAMPLE_PAYLOAD)
    burst_elapsed = time.perf_counter() - t0
    throughput = n / burst_elapsed

    # ----- 6. Serialization -----
    print(f"\n  [5/5] Serialization overhead...")
    ser_times = []
    for _ in range(1000):
        t0 = time.perf_counter()
        json.dumps(SAMPLE_PAYLOAD).encode()
        ser_times.append((time.perf_counter() - t0) * 1_000_000)  # microseconds

    # ----- Compile results -----
    results = {
        "label": label,
        "num_requests": n,
        "create": {
            "median_ms": round(statistics.median(create_times), 2),
            "mean_ms": round(statistics.mean(create_times), 2),
            "p95_ms": round(pct(create_times, 95), 2),
            "p99_ms": round(pct(create_times, 99), 2),
            "min_ms": round(min(create_times), 2),
            "max_ms": round(max(create_times), 2),
        },
        "search": {
            "median_ms": round(statistics.median(search_times), 2),
            "mean_ms": round(statistics.mean(search_times), 2),
            "p95_ms": round(pct(search_times, 95), 2),
            "p99_ms": round(pct(search_times, 99), 2),
            "min_ms": round(min(search_times), 2),
            "max_ms": round(max(search_times), 2),
        },
        "list_all": {
            "median_ms": round(statistics.median(list_times), 2),
            "mean_ms": round(statistics.mean(list_times), 2),
            "avg_response_bytes": round(statistics.mean(list_sizes)),
        },
        "throughput": {
            "requests_per_sec": round(throughput, 1),
            "total_time_sec": round(burst_elapsed, 2),
        },
        "payload": {
            "avg_request_bytes": round(statistics.mean(create_request_sizes)),
            "avg_create_response_bytes": round(statistics.mean(create_response_sizes)),
            "avg_search_response_bytes": round(statistics.mean(search_response_sizes)),
        },
        "serialization": {
            "json_encode_median_us": round(statistics.median(ser_times), 2),
        },
    }

    # Print summary
    print(f"\n  ── Results for {label} ──")
    print(f"  CREATE  median={results['create']['median_ms']}ms  p95={results['create']['p95_ms']}ms  p99={results['create']['p99_ms']}ms")
    print(f"  SEARCH  median={results['search']['median_ms']}ms  p95={results['search']['p95_ms']}ms  p99={results['search']['p99_ms']}ms")
    print(f"  LIST    median={results['list_all']['median_ms']}ms  avg_size={results['list_all']['avg_response_bytes']}B")
    print(f"  THROUGHPUT  {results['throughput']['requests_per_sec']} req/s")
    print(f"  PAYLOAD  req={results['payload']['avg_request_bytes']}B  resp={results['payload']['avg_create_response_bytes']}B")

    return results


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    label = sys.argv[1]
    base_url = sys.argv[2].rstrip("/")
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 200

    results = run_benchmark(label, base_url, n)

    # Save to JSON
    out_file = f"/tmp/bench_{label.replace(' ', '_').replace('+', 'plus').lower()}.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to {out_file}")
