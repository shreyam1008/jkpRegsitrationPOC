"""Benchmark Suite 3: Concurrent Load Simulation — Multi-User Stress Tests.

Simulates multiple simultaneous users hitting the gRPC server and proxy.
Tests: thread-pool saturation, connection multiplexing, mixed workloads,
       ramp-up behavior, and sustained concurrent load.

Finds the breaking point: where latency degrades, errors start, or throughput plateaus.
"""

from __future__ import annotations

import asyncio
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import grpc
import httpx

from helpers import (
    BenchResult,
    Timer,
    encode_grpc_web_request,
    fake_satsangi_dict,
    logger,
    print_results,
    random_search_term,
    reset_mock_store,
    seed_mock_store,
    start_mock_grpc_server,
    start_mock_proxy,
)

from app.generated import satsangi_pb2, satsangi_pb2_grpc  # noqa: E402

_SERVICE_PREFIX = "jkp.registration.v1.SatsangiService"
_HEADERS = {"content-type": "application/grpc-web-text", "x-grpc-web": "1"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_create_bytes(full: bool = True) -> bytes:
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
    return satsangi_pb2.SatsangiCreate(**kwargs).SerializeToString()


# ---------------------------------------------------------------------------
# Suite A: Direct gRPC concurrent users
# ---------------------------------------------------------------------------


def _grpc_worker_health(stub: satsangi_pb2_grpc.SatsangiServiceStub, n: int) -> tuple[list[float], int]:
    """Single worker: call Health n times, return (latencies, errors)."""
    latencies = []
    errors = 0
    for _ in range(n):
        with Timer() as t:
            try:
                stub.Health(satsangi_pb2.HealthRequest())
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    return latencies, errors


def _grpc_worker_mixed(stub: satsangi_pb2_grpc.SatsangiServiceStub, n: int) -> tuple[list[float], int]:
    """Single worker: mixed workload (60% search, 30% create, 10% list)."""
    latencies = []
    errors = 0
    for _ in range(n):
        roll = random.random()
        with Timer() as t:
            try:
                if roll < 0.6:
                    stub.SearchSatsangis(satsangi_pb2.SearchRequest(query=random_search_term()))
                elif roll < 0.9:
                    payload = _build_create_bytes(full=random.choice([True, False]))
                    req = satsangi_pb2.SatsangiCreate()
                    req.ParseFromString(payload)
                    stub.CreateSatsangi(req)
                else:
                    stub.ListSatsangis(satsangi_pb2.ListRequest(limit=50))
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    return latencies, errors


def bench_grpc_concurrent_health(
    grpc_port: int,
    concurrency: int,
    requests_per_user: int = 100,
) -> BenchResult:
    """N concurrent users each sending Health RPCs."""
    channel = grpc.insecure_channel(f"localhost:{grpc_port}")
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)

    all_latencies: list[float] = []
    total_errors = 0

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(_grpc_worker_health, stub, requests_per_user) for _ in range(concurrency)]
        for f in as_completed(futures):
            lats, errs = f.result()
            all_latencies.extend(lats)
            total_errors += errs
    duration = time.perf_counter() - t0

    channel.close()
    total = concurrency * requests_per_user
    return BenchResult(f"gRPC {concurrency} users × Health", total, duration, all_latencies, total_errors)


def bench_grpc_concurrent_mixed(
    grpc_port: int,
    concurrency: int,
    requests_per_user: int = 50,
) -> BenchResult:
    """N concurrent users with mixed workload (search/create/list)."""
    seed_mock_store(500, full=True)
    channel = grpc.insecure_channel(f"localhost:{grpc_port}")
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)

    all_latencies: list[float] = []
    total_errors = 0

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(_grpc_worker_mixed, stub, requests_per_user) for _ in range(concurrency)]
        for f in as_completed(futures):
            lats, errs = f.result()
            all_latencies.extend(lats)
            total_errors += errs
    duration = time.perf_counter() - t0

    channel.close()
    total = concurrency * requests_per_user
    return BenchResult(f"gRPC {concurrency} users × Mixed", total, duration, all_latencies, total_errors)


# ---------------------------------------------------------------------------
# Suite B: Proxy concurrent users (async httpx)
# ---------------------------------------------------------------------------


async def _proxy_worker_health(
    client: httpx.AsyncClient,
    base_url: str,
    n: int,
) -> tuple[list[float], int]:
    payload = encode_grpc_web_request(satsangi_pb2.HealthRequest().SerializeToString())
    latencies = []
    errors = 0
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            r = await client.post(
                f"{base_url}/{_SERVICE_PREFIX}/Health",
                content=payload,
                headers=_HEADERS,
            )
            if r.headers.get("grpc-status") != "0":
                errors += 1
        except Exception:
            errors += 1
        latencies.append((time.perf_counter() - t0) * 1000)
    return latencies, errors


async def _proxy_worker_mixed(
    client: httpx.AsyncClient,
    base_url: str,
    n: int,
) -> tuple[list[float], int]:
    latencies = []
    errors = 0
    for _ in range(n):
        roll = random.random()
        t0 = time.perf_counter()
        try:
            if roll < 0.6:
                payload = encode_grpc_web_request(
                    satsangi_pb2.SearchRequest(query=random_search_term()).SerializeToString()
                )
                r = await client.post(
                    f"{base_url}/{_SERVICE_PREFIX}/SearchSatsangis",
                    content=payload,
                    headers=_HEADERS,
                )
            elif roll < 0.9:
                payload = encode_grpc_web_request(_build_create_bytes(full=True))
                r = await client.post(
                    f"{base_url}/{_SERVICE_PREFIX}/CreateSatsangi",
                    content=payload,
                    headers=_HEADERS,
                )
            else:
                payload = encode_grpc_web_request(
                    satsangi_pb2.ListRequest(limit=50).SerializeToString()
                )
                r = await client.post(
                    f"{base_url}/{_SERVICE_PREFIX}/ListSatsangis",
                    content=payload,
                    headers=_HEADERS,
                )
            if r.headers.get("grpc-status") != "0":
                errors += 1
        except Exception:
            errors += 1
        latencies.append((time.perf_counter() - t0) * 1000)
    return latencies, errors


async def _run_proxy_concurrent(
    base_url: str,
    concurrency: int,
    requests_per_user: int,
    mixed: bool = False,
) -> BenchResult:
    async with httpx.AsyncClient(timeout=30.0) as client:
        all_latencies: list[float] = []
        total_errors = 0

        t0 = time.perf_counter()
        if mixed:
            tasks = [_proxy_worker_mixed(client, base_url, requests_per_user) for _ in range(concurrency)]
        else:
            tasks = [_proxy_worker_health(client, base_url, requests_per_user) for _ in range(concurrency)]
        results = await asyncio.gather(*tasks)
        for lats, errs in results:
            all_latencies.extend(lats)
            total_errors += errs
        duration = time.perf_counter() - t0

    total = concurrency * requests_per_user
    label = "Mixed" if mixed else "Health"
    return BenchResult(f"Proxy {concurrency} users × {label}", total, duration, all_latencies, total_errors)


def bench_proxy_concurrent(
    base_url: str,
    concurrency: int,
    requests_per_user: int = 50,
    mixed: bool = False,
) -> BenchResult:
    return asyncio.run(_run_proxy_concurrent(base_url, concurrency, requests_per_user, mixed))


# ---------------------------------------------------------------------------
# Suite C: Ramp-up test — gradually increase concurrency
# ---------------------------------------------------------------------------


def bench_grpc_ramp_up(grpc_port: int) -> list[BenchResult]:
    """Increase concurrent users from 1 to 200 — find the saturation point."""
    results = []
    for users in [1, 5, 10, 25, 50, 100, 150, 200]:
        r = bench_grpc_concurrent_health(grpc_port, concurrency=users, requests_per_user=50)
        r.name = f"gRPC Ramp-Up: {users} users"
        results.append(r)
        logger.info("    %d users → %.1f rps, p99=%.2fms, err=%d", users, r.rps, r.p99, r.errors)
    return results


def bench_proxy_ramp_up(base_url: str) -> list[BenchResult]:
    """Increase concurrent users from 1 to 200 through the proxy."""
    results = []
    for users in [1, 5, 10, 25, 50, 100, 150, 200]:
        r = bench_proxy_concurrent(base_url, concurrency=users, requests_per_user=30)
        r.name = f"Proxy Ramp-Up: {users} users"
        results.append(r)
        logger.info("    %d users → %.1f rps, p99=%.2fms, err=%d", users, r.rps, r.p99, r.errors)
    return results


# ---------------------------------------------------------------------------
# Suite D: Sustained load — hold N users for M seconds
# ---------------------------------------------------------------------------


def _sustained_grpc_worker(
    stub: satsangi_pb2_grpc.SatsangiServiceStub,
    deadline: float,
) -> tuple[list[float], int, int]:
    latencies = []
    errors = 0
    count = 0
    while time.perf_counter() < deadline:
        roll = random.random()
        with Timer() as t:
            try:
                if roll < 0.5:
                    stub.SearchSatsangis(satsangi_pb2.SearchRequest(query=random_search_term()))
                elif roll < 0.8:
                    payload = _build_create_bytes(full=True)
                    req = satsangi_pb2.SatsangiCreate()
                    req.ParseFromString(payload)
                    stub.CreateSatsangi(req)
                else:
                    stub.Health(satsangi_pb2.HealthRequest())
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
        count += 1
    return latencies, errors, count


def bench_sustained_load(grpc_port: int, concurrency: int = 50, duration_s: float = 10.0) -> BenchResult:
    """Hold N concurrent users for M seconds — realistic sustained load."""
    seed_mock_store(500, full=True)
    channel = grpc.insecure_channel(f"localhost:{grpc_port}")
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)

    all_latencies: list[float] = []
    total_errors = 0
    total_count = 0
    deadline = time.perf_counter() + duration_s

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(_sustained_grpc_worker, stub, deadline) for _ in range(concurrency)]
        for f in as_completed(futures):
            lats, errs, cnt = f.result()
            all_latencies.extend(lats)
            total_errors += errs
            total_count += cnt
    elapsed = time.perf_counter() - t0

    channel.close()
    return BenchResult(
        f"Sustained {concurrency} users × {duration_s:.0f}s",
        total_count, elapsed, all_latencies, total_errors,
    )


# ---------------------------------------------------------------------------
# Suite E: Thread pool saturation — exceed max_workers
# ---------------------------------------------------------------------------


def bench_thread_pool_saturation(grpc_port: int) -> list[BenchResult]:
    """Server has ThreadPoolExecutor(10). Push 5, 10, 20, 50 concurrent users.

    This directly tests whether exceeding the thread pool degrades performance
    or causes queuing.
    """
    seed_mock_store(200, full=True)
    results = []
    for users in [5, 10, 20, 50]:
        r = bench_grpc_concurrent_mixed(grpc_port, concurrency=users, requests_per_user=50)
        r.name = f"ThreadPool stress: {users} users (pool=10)"
        results.append(r)
        logger.info("    %d users (pool=10) → rps=%.1f, p99=%.2fms", users, r.rps, r.p99)
    return results


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_all(grpc_port: int = 50053, proxy_port: int = 18081) -> list[BenchResult]:
    """Run all concurrency benchmarks."""
    logger.info("Starting concurrent load benchmarks (grpc=%d, proxy=%d)", grpc_port, proxy_port)

    server = start_mock_grpc_server(port=grpc_port, max_workers=10)
    time.sleep(0.3)
    start_mock_proxy(proxy_port=proxy_port, grpc_port=grpc_port)

    base_url = f"http://127.0.0.1:{proxy_port}"
    results: list[BenchResult] = []

    # --- gRPC direct concurrency ---
    logger.info("  [1/6] gRPC ramp-up (1→200 users)...")
    results.extend(bench_grpc_ramp_up(grpc_port))

    logger.info("  [2/6] gRPC mixed workload concurrency...")
    for users in [10, 50, 100]:
        results.append(bench_grpc_concurrent_mixed(grpc_port, concurrency=users, requests_per_user=50))

    logger.info("  [3/6] Thread pool saturation test...")
    results.extend(bench_thread_pool_saturation(grpc_port))

    logger.info("  [4/6] Sustained load (50 users, 10s)...")
    results.append(bench_sustained_load(grpc_port, concurrency=50, duration_s=10.0))

    # --- Proxy concurrency ---
    logger.info("  [5/6] Proxy ramp-up (1→200 users)...")
    results.extend(bench_proxy_ramp_up(base_url))

    logger.info("  [6/6] Proxy mixed workload concurrency...")
    for users in [10, 50, 100]:
        seed_mock_store(500, full=True)
        results.append(bench_proxy_concurrent(base_url, concurrency=users, requests_per_user=30, mixed=True))

    server.stop(grace=1)

    print_results(results, "Concurrent Load Simulation")
    return results


if __name__ == "__main__":
    run_all()
