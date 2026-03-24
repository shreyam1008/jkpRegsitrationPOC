"""Benchmark Suite 1: Native gRPC Server — Direct Protocol Benchmarks.

Tests the gRPC server layer directly (no proxy, no HTTP).
Measures: RPC latency, throughput, payload sizes, per-method performance.

All DB calls are mocked — this isolates the gRPC + protobuf + Python overhead.
"""

from __future__ import annotations

import sys
import time

import grpc

from helpers import (
    BenchResult,
    Timer,
    fake_satsangi_dict,
    logger,
    print_results,
    random_search_term,
    reset_mock_store,
    seed_mock_store,
    start_mock_grpc_server,
)

# ---------------------------------------------------------------------------
# Proto imports (available after helpers sets up sys.path)
# ---------------------------------------------------------------------------

from app.generated import satsangi_pb2, satsangi_pb2_grpc  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_create_request(full: bool = False) -> satsangi_pb2.SatsangiCreate:
    d = fake_satsangi_dict(full=full)
    kwargs = {
        "first_name": d["first_name"],
        "last_name": d["last_name"],
        "phone_number": d["phone_number"],
        "nationality": d["nationality"],
        "country": d["country"],
        "print_on_card": d["print_on_card"],
        "has_room_in_ashram": d["has_room_in_ashram"],
        "banned": d["banned"],
        "first_timer": d["first_timer"],
    }
    if full:
        for key in (
            "age", "date_of_birth", "pan", "gender", "special_category",
            "govt_id_type", "govt_id_number", "id_expiry_date",
            "id_issuing_country", "nick_name", "introducer", "address",
            "city", "district", "state", "pincode", "emergency_contact",
            "ex_center_satsangi_id", "introduced_by", "email",
            "date_of_first_visit", "notes",
        ):
            if key in d and d[key] is not None:
                kwargs[key] = d[key]
    return satsangi_pb2.SatsangiCreate(**kwargs)


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------


def bench_health(stub: satsangi_pb2_grpc.SatsangiServiceStub, n: int = 500) -> BenchResult:
    """Health RPC — lightest possible call, measures pure gRPC overhead."""
    latencies: list[float] = []
    errors = 0
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            try:
                stub.Health(satsangi_pb2.HealthRequest())
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    return BenchResult("gRPC Health (no-op)", n, duration, latencies, errors)


def bench_create_minimal(stub: satsangi_pb2_grpc.SatsangiServiceStub, n: int = 500) -> BenchResult:
    """CreateSatsangi with minimal fields — measures write path overhead."""
    latencies: list[float] = []
    errors = 0
    reset_mock_store()
    t0 = time.perf_counter()
    for _ in range(n):
        req = _build_create_request(full=False)
        with Timer() as t:
            try:
                stub.CreateSatsangi(req)
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    return BenchResult("gRPC CreateSatsangi (minimal)", n, duration, latencies, errors)


def bench_create_full(stub: satsangi_pb2_grpc.SatsangiServiceStub, n: int = 500) -> BenchResult:
    """CreateSatsangi with ALL fields populated — max payload."""
    latencies: list[float] = []
    errors = 0
    reset_mock_store()
    t0 = time.perf_counter()
    for _ in range(n):
        req = _build_create_request(full=True)
        with Timer() as t:
            try:
                stub.CreateSatsangi(req)
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    return BenchResult("gRPC CreateSatsangi (full payload)", n, duration, latencies, errors)


def bench_search(stub: satsangi_pb2_grpc.SatsangiServiceStub, n: int = 500, store_size: int = 500) -> BenchResult:
    """SearchSatsangis — measures read path + ILIKE simulation."""
    seed_mock_store(store_size, full=True)
    latencies: list[float] = []
    errors = 0
    t0 = time.perf_counter()
    for _ in range(n):
        req = satsangi_pb2.SearchRequest(query=random_search_term())
        with Timer() as t:
            try:
                stub.SearchSatsangis(req)
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    return BenchResult(f"gRPC Search ({store_size} records)", n, duration, latencies, errors)


def bench_search_scaling(stub: satsangi_pb2_grpc.SatsangiServiceStub) -> list[BenchResult]:
    """Search at different store sizes to find scaling behavior."""
    results = []
    for size in [100, 500, 1000, 5000]:
        r = bench_search(stub, n=200, store_size=size)
        r.name = f"gRPC Search (store={size})"
        results.append(r)
    return results


def bench_list_all(stub: satsangi_pb2_grpc.SatsangiServiceStub, n: int = 200, store_size: int = 500) -> BenchResult:
    """ListSatsangis — return all records, measures serialization of large responses."""
    seed_mock_store(store_size, full=True)
    latencies: list[float] = []
    errors = 0
    t0 = time.perf_counter()
    for _ in range(n):
        req = satsangi_pb2.ListRequest(limit=0)
        with Timer() as t:
            try:
                resp = stub.ListSatsangis(req)
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    return BenchResult(f"gRPC ListAll ({store_size} records)", n, duration, latencies, errors)


def bench_list_scaling(stub: satsangi_pb2_grpc.SatsangiServiceStub) -> list[BenchResult]:
    """List at different store sizes — find where serialization becomes the bottleneck."""
    results = []
    for size in [100, 500, 1000, 2000, 5000]:
        r = bench_list_all(stub, n=100, store_size=size)
        r.name = f"gRPC ListAll (store={size})"
        results.append(r)
    return results


def bench_rapid_fire(stub: satsangi_pb2_grpc.SatsangiServiceStub, duration_s: float = 5.0) -> BenchResult:
    """Sustained max-throughput test — how many Health RPCs in N seconds."""
    latencies: list[float] = []
    errors = 0
    count = 0
    deadline = time.perf_counter() + duration_s
    t0 = time.perf_counter()
    while time.perf_counter() < deadline:
        with Timer() as t:
            try:
                stub.Health(satsangi_pb2.HealthRequest())
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
        count += 1
    elapsed = time.perf_counter() - t0
    return BenchResult(f"gRPC Rapid-Fire Health ({duration_s:.0f}s)", count, elapsed, latencies, errors)


def bench_empty_search(stub: satsangi_pb2_grpc.SatsangiServiceStub, n: int = 300) -> BenchResult:
    """Search with empty query — returns all records (worst case)."""
    seed_mock_store(500, full=True)
    latencies: list[float] = []
    errors = 0
    t0 = time.perf_counter()
    for _ in range(n):
        req = satsangi_pb2.SearchRequest(query="")
        with Timer() as t:
            try:
                stub.SearchSatsangis(req)
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    return BenchResult("gRPC Search (empty query, 500 recs)", n, duration, latencies, errors)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_all(grpc_port: int = 50051) -> list[BenchResult]:
    """Run all native gRPC benchmarks and return results."""
    logger.info("Starting native gRPC benchmarks on port %d", grpc_port)

    server = start_mock_grpc_server(port=grpc_port, max_workers=10)
    time.sleep(0.3)

    channel = grpc.insecure_channel(f"localhost:{grpc_port}")
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)

    results: list[BenchResult] = []

    logger.info("  [1/8] Health RPC baseline...")
    results.append(bench_health(stub, n=1000))

    logger.info("  [2/8] CreateSatsangi (minimal payload)...")
    results.append(bench_create_minimal(stub, n=500))

    logger.info("  [3/8] CreateSatsangi (full payload)...")
    results.append(bench_create_full(stub, n=500))

    logger.info("  [4/8] Search (500 records)...")
    results.append(bench_search(stub, n=500, store_size=500))

    logger.info("  [5/8] Search scaling (100→5000 records)...")
    results.extend(bench_search_scaling(stub))

    logger.info("  [6/8] ListAll scaling (100→5000 records)...")
    results.extend(bench_list_scaling(stub))

    logger.info("  [7/8] Empty search (worst case)...")
    results.append(bench_empty_search(stub, n=300))

    logger.info("  [8/8] Rapid-fire throughput (5s sustained)...")
    results.append(bench_rapid_fire(stub, duration_s=5.0))

    channel.close()
    server.stop(grace=1)

    print_results(results, "Native gRPC Server Benchmarks")
    return results


if __name__ == "__main__":
    run_all()
