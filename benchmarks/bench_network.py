"""Benchmark Suite 4: Network Condition Simulation.

Simulates degraded network conditions by injecting latency into the DB layer
and measuring how each layer of the stack responds:

  • Fast DB (0ms)     — baseline, isolate protocol overhead
  • Normal DB (2ms)   — typical localhost PostgreSQL
  • Slow DB (10ms)    — remote DB or busy server
  • Very slow DB (50ms) — cross-region DB or overloaded server
  • Extreme DB (200ms)  — worst-case, simulates network partition recovery

Also tests:
  • Timeout behavior under slow conditions
  • Latency amplification through proxy layers
  • How slow DB affects concurrent users
"""

from __future__ import annotations

import asyncio
import contextlib
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import grpc
import httpx

from helpers import (
    BenchResult,
    Timer,
    _MockConnection,
    encode_grpc_web_request,
    fake_satsangi_dict,
    logger,
    print_results,
    random_search_term,
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
# Suite A: DB Latency Sweep — gRPC direct
# ---------------------------------------------------------------------------


def bench_grpc_latency_sweep(port: int = 50060) -> list[BenchResult]:
    """Measure gRPC RPC latency at various simulated DB latencies.

    Reuses a single port — stops server fully, waits, restarts with new latency.
    """
    results = []
    latency_configs = [
        (0.0, "0ms (in-memory)"),
        (1.0, "1ms (fast SSD)"),
        (2.0, "2ms (localhost PG)"),
        (5.0, "5ms (local network)"),
        (10.0, "10ms (remote DB)"),
        (25.0, "25ms (cross-AZ)"),
        (50.0, "50ms (cross-region)"),
        (100.0, "100ms (intercontinental)"),
        (200.0, "200ms (extreme)"),
    ]

    for db_latency, label in latency_configs:
        server = start_mock_grpc_server(port=port, max_workers=10, db_latency_ms=db_latency)
        time.sleep(0.3)

        channel = grpc.insecure_channel(f"localhost:{port}")
        stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)

        seed_mock_store(200, full=True)
        latencies: list[float] = []
        errors = 0
        n = 200 if db_latency < 100 else 50
        t0 = time.perf_counter()
        for _ in range(n):
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
        duration = time.perf_counter() - t0

        channel.close()
        server.stop(grace=0).wait()
        time.sleep(0.5)  # ensure port is fully released

        result = BenchResult(f"DB latency {label}", n, duration, latencies, errors)
        result.extra["db_latency_ms"] = db_latency
        results.append(result)
        logger.info("    DB=%s → p50=%.2fms, p99=%.2fms, rps=%.1f", label, result.p50, result.p99, result.rps)

    return results


# ---------------------------------------------------------------------------
# Suite B: Proxy latency amplification — same sweep through the proxy
# ---------------------------------------------------------------------------


def bench_proxy_latency_sweep(grpc_port: int = 50061, proxy_port: int = 18090) -> list[BenchResult]:
    """Same DB latency sweep but through the grpc-web proxy.

    Reveals how much latency the proxy adds on top of the DB latency.
    Uses a single grpc+proxy port pair, restarting between configs.
    """
    results = []
    latency_configs = [
        (0.0, "0ms"),
        (2.0, "2ms"),
        (10.0, "10ms"),
        (50.0, "50ms"),
    ]

    for db_latency, label in latency_configs:
        server = start_mock_grpc_server(port=grpc_port, max_workers=10, db_latency_ms=db_latency)
        time.sleep(0.3)
        start_mock_proxy(proxy_port=proxy_port, grpc_port=grpc_port, db_latency_ms=db_latency)

        base_url = f"http://127.0.0.1:{proxy_port}"
        client = httpx.Client(timeout=30.0)

        seed_mock_store(200, full=True)
        latencies: list[float] = []
        errors = 0
        n = 150 if db_latency < 100 else 50
        t0 = time.perf_counter()
        for _ in range(n):
            payload = encode_grpc_web_request(
                satsangi_pb2.SearchRequest(query=random_search_term()).SerializeToString()
            )
            with Timer() as t:
                try:
                    r = client.post(
                        f"{base_url}/{_SERVICE_PREFIX}/SearchSatsangis",
                        content=payload,
                        headers=_HEADERS,
                    )
                    if r.headers.get("grpc-status") != "0":
                        errors += 1
                except Exception:
                    errors += 1
            latencies.append(t.elapsed_ms)
        duration = time.perf_counter() - t0

        client.close()
        server.stop(grace=0).wait()
        time.sleep(0.5)
        # Note: proxy (uvicorn daemon thread) cannot be stopped cleanly,
        # but the next start_mock_proxy will bind to a new port or reuse.
        # We increment ports to avoid conflicts with the daemon thread.
        proxy_port += 1
        grpc_port += 1

        result = BenchResult(f"Proxy + DB latency {label}", n, duration, latencies, errors)
        result.extra["db_latency_ms"] = db_latency
        results.append(result)
        logger.info("    Proxy+DB=%s → p50=%.2fms, p99=%.2fms", label, result.p50, result.p99)

    return results


# ---------------------------------------------------------------------------
# Suite C: Slow DB + concurrent users — how does latency degrade?
# ---------------------------------------------------------------------------


def _grpc_worker_slow(
    stub: satsangi_pb2_grpc.SatsangiServiceStub,
    n: int,
) -> tuple[list[float], int]:
    latencies = []
    errors = 0
    for _ in range(n):
        with Timer() as t:
            try:
                stub.SearchSatsangis(satsangi_pb2.SearchRequest(query=random_search_term()))
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    return latencies, errors


def bench_slow_db_concurrent(port: int = 50066) -> list[BenchResult]:
    """50 concurrent users with various DB latencies.

    Tests: does slow DB cause thread-pool starvation?
    With ThreadPoolExecutor(10) and 50ms DB latency, each thread is blocked for 50ms,
    meaning max throughput = 10 threads / 0.05s = 200 rps theoretical max.
    """
    results = []
    configs = [
        (0.0, "0ms DB + 50 users"),
        (5.0, "5ms DB + 50 users"),
        (20.0, "20ms DB + 50 users"),
        (50.0, "50ms DB + 50 users"),
    ]

    for db_latency, label in configs:
        server = start_mock_grpc_server(port=port, max_workers=10, db_latency_ms=db_latency)
        time.sleep(0.3)

        seed_mock_store(200, full=True)
        channel = grpc.insecure_channel(f"localhost:{port}")
        stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)

        all_latencies: list[float] = []
        total_errors = 0
        concurrency = 50
        requests_per_user = 20

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(_grpc_worker_slow, stub, requests_per_user) for _ in range(concurrency)]
            for f in as_completed(futures):
                lats, errs = f.result()
                all_latencies.extend(lats)
                total_errors += errs
        duration = time.perf_counter() - t0

        channel.close()
        server.stop(grace=0).wait()
        time.sleep(0.5)

        total = concurrency * requests_per_user
        result = BenchResult(label, total, duration, all_latencies, total_errors)
        result.extra["db_latency_ms"] = db_latency
        result.extra["theoretical_max_rps"] = 10 / (db_latency / 1000) if db_latency > 0 else float("inf")
        results.append(result)
        logger.info(
            "    %s → rps=%.1f (max=%.0f), p99=%.2fms",
            label, result.rps, result.extra["theoretical_max_rps"], result.p99,
        )

    return results


# ---------------------------------------------------------------------------
# Suite D: Timeout behavior — what happens when server is overwhelmed?
# ---------------------------------------------------------------------------


def bench_timeout_behavior(grpc_port: int = 50067) -> list[BenchResult]:
    """Test gRPC timeout handling under extreme DB latency.

    With 500ms DB latency and a 1s timeout, some requests should time out.
    """
    results = []

    # Start server with very high DB latency
    server = start_mock_grpc_server(port=grpc_port, max_workers=5, db_latency_ms=500)
    time.sleep(0.2)
    seed_mock_store(50, full=True)

    channel = grpc.insecure_channel(f"localhost:{grpc_port}")
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)

    for timeout_s, label in [(2.0, "2s timeout"), (1.0, "1s timeout"), (0.3, "300ms timeout")]:
        latencies: list[float] = []
        errors = 0
        timeouts = 0
        n = 30
        t0 = time.perf_counter()
        for _ in range(n):
            with Timer() as t:
                try:
                    stub.SearchSatsangis(
                        satsangi_pb2.SearchRequest(query=random_search_term()),
                        timeout=timeout_s,
                    )
                except grpc.RpcError as e:
                    if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                        timeouts += 1
                    errors += 1
                except Exception:
                    errors += 1
            latencies.append(t.elapsed_ms)
        duration = time.perf_counter() - t0

        result = BenchResult(f"Timeout test: {label} (DB=500ms)", n, duration, latencies, errors)
        result.extra["timeouts"] = timeouts
        result.extra["timeout_pct"] = timeouts / n * 100
        results.append(result)
        logger.info("    %s → timeouts=%d/%d (%.0f%%)", label, timeouts, n, timeouts / n * 100)

    channel.close()
    server.stop(grace=0).wait()
    time.sleep(0.5)
    return results


# ---------------------------------------------------------------------------
# Suite E: Jitter simulation — variable latency (real networks are noisy)
# ---------------------------------------------------------------------------


def bench_jitter_simulation(grpc_port: int = 50068) -> BenchResult:
    """Simulate realistic network jitter: base 5ms ± random 0-20ms.

    Real networks don't have constant latency. This tests how the system
    handles variable response times.
    """
    import app.db as db_mod
    import app.store as store_mod

    # Custom jittery get_conn
    @contextlib.contextmanager
    def _jittery_get_conn():
        jitter = random.uniform(0, 20)  # 0-20ms random jitter
        yield _MockConnection(latency_ms=5.0 + jitter)

    db_mod.get_conn = _jittery_get_conn  # type: ignore[assignment]
    store_mod.get_conn = _jittery_get_conn  # type: ignore[assignment]

    from app.grpc_server import serve
    server = serve(port=grpc_port, max_workers=10)
    time.sleep(0.2)
    seed_mock_store(200, full=True)

    channel = grpc.insecure_channel(f"localhost:{grpc_port}")
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)

    latencies: list[float] = []
    errors = 0
    n = 300
    t0 = time.perf_counter()
    for _ in range(n):
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
    duration = time.perf_counter() - t0

    channel.close()
    server.stop(grace=0).wait()
    time.sleep(0.3)

    result = BenchResult("Jitter sim (5ms ± 0-20ms)", n, duration, latencies, errors)
    result.extra["jitter_range_ms"] = "5-25ms"
    return result


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_all() -> list[BenchResult]:
    """Run all network simulation benchmarks."""
    logger.info("Starting network condition simulation benchmarks...")

    results: list[BenchResult] = []

    logger.info("  [1/5] DB latency sweep (gRPC direct)...")
    results.extend(bench_grpc_latency_sweep())

    logger.info("  [2/5] DB latency sweep (through proxy)...")
    results.extend(bench_proxy_latency_sweep())

    logger.info("  [3/5] Slow DB + concurrent users...")
    results.extend(bench_slow_db_concurrent())

    logger.info("  [4/5] Timeout behavior under extreme latency...")
    results.extend(bench_timeout_behavior())

    logger.info("  [5/5] Jitter simulation...")
    results.append(bench_jitter_simulation())

    print_results(results, "Network Condition Simulation")
    return results


if __name__ == "__main__":
    run_all()
