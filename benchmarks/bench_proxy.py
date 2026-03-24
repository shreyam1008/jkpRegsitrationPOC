"""Benchmark Suite 2: grpc-web Proxy — Full HTTP Path Benchmarks.

Tests the complete browser-to-gRPC path:
  Browser POST (grpc-web-text, base64) → FastAPI proxy → gRPC server → mock DB

Measures: HTTP overhead, base64 encode/decode cost, proxy translation latency,
          end-to-end throughput through the full stack.
"""

from __future__ import annotations

import time

import httpx

from helpers import (
    BenchResult,
    Timer,
    decode_grpc_web_response,
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

from app.generated import satsangi_pb2  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SERVICE_PREFIX = "jkp.registration.v1.SatsangiService"
_HEADERS = {
    "content-type": "application/grpc-web-text",
    "x-grpc-web": "1",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_grpc_web(
    client: httpx.Client,
    base_url: str,
    method: str,
    proto_bytes: bytes,
) -> httpx.Response:
    """Send a grpc-web-text POST and return the raw response."""
    body = encode_grpc_web_request(proto_bytes)
    return client.post(
        f"{base_url}/{_SERVICE_PREFIX}/{method}",
        content=body,
        headers=_HEADERS,
    )


def _build_create_bytes(full: bool = False) -> bytes:
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
# Benchmarks
# ---------------------------------------------------------------------------


def bench_proxy_health(client: httpx.Client, base_url: str, n: int = 500) -> BenchResult:
    """GET /healthz — FastAPI health endpoint (no gRPC involved)."""
    latencies: list[float] = []
    errors = 0
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            try:
                r = client.get(f"{base_url}/healthz")
                if r.status_code != 200:
                    errors += 1
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    return BenchResult("Proxy GET /healthz", n, duration, latencies, errors)


def bench_proxy_grpc_health(client: httpx.Client, base_url: str, n: int = 500) -> BenchResult:
    """Health RPC through the proxy — measures full proxy overhead."""
    payload = satsangi_pb2.HealthRequest().SerializeToString()
    latencies: list[float] = []
    errors = 0
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            try:
                r = _post_grpc_web(client, base_url, "Health", payload)
                if r.headers.get("grpc-status") != "0":
                    errors += 1
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    return BenchResult("Proxy → gRPC Health", n, duration, latencies, errors)


def bench_proxy_create_minimal(client: httpx.Client, base_url: str, n: int = 500) -> BenchResult:
    """CreateSatsangi (minimal) through the full proxy stack."""
    reset_mock_store()
    latencies: list[float] = []
    errors = 0
    t0 = time.perf_counter()
    for _ in range(n):
        payload = _build_create_bytes(full=False)
        with Timer() as t:
            try:
                r = _post_grpc_web(client, base_url, "CreateSatsangi", payload)
                if r.headers.get("grpc-status") != "0":
                    errors += 1
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    return BenchResult("Proxy → CreateSatsangi (minimal)", n, duration, latencies, errors)


def bench_proxy_create_full(client: httpx.Client, base_url: str, n: int = 500) -> BenchResult:
    """CreateSatsangi (full payload) through the full proxy stack."""
    reset_mock_store()
    latencies: list[float] = []
    errors = 0
    t0 = time.perf_counter()
    for _ in range(n):
        payload = _build_create_bytes(full=True)
        with Timer() as t:
            try:
                r = _post_grpc_web(client, base_url, "CreateSatsangi", payload)
                if r.headers.get("grpc-status") != "0":
                    errors += 1
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    return BenchResult("Proxy → CreateSatsangi (full)", n, duration, latencies, errors)


def bench_proxy_search(client: httpx.Client, base_url: str, n: int = 500, store_size: int = 500) -> BenchResult:
    """SearchSatsangis through the proxy — measures large response encoding."""
    seed_mock_store(store_size, full=True)
    latencies: list[float] = []
    errors = 0
    t0 = time.perf_counter()
    for _ in range(n):
        payload = satsangi_pb2.SearchRequest(query=random_search_term()).SerializeToString()
        with Timer() as t:
            try:
                r = _post_grpc_web(client, base_url, "SearchSatsangis", payload)
                if r.headers.get("grpc-status") != "0":
                    errors += 1
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    return BenchResult(f"Proxy → Search ({store_size} recs)", n, duration, latencies, errors)


def bench_proxy_list_scaling(client: httpx.Client, base_url: str) -> list[BenchResult]:
    """ListSatsangis at various sizes — proxy must base64-encode large responses."""
    results = []
    for size in [100, 500, 1000, 2000]:
        seed_mock_store(size, full=True)
        payload = satsangi_pb2.ListRequest(limit=0).SerializeToString()
        latencies: list[float] = []
        errors = 0
        n = 100
        t0 = time.perf_counter()
        for _ in range(n):
            with Timer() as t:
                try:
                    r = _post_grpc_web(client, base_url, "ListSatsangis", payload)
                    if r.headers.get("grpc-status") != "0":
                        errors += 1
                except Exception:
                    errors += 1
            latencies.append(t.elapsed_ms)
        duration = time.perf_counter() - t0
        results.append(BenchResult(f"Proxy → ListAll (store={size})", n, duration, latencies, errors))
    return results


def bench_proxy_payload_sizes(client: httpx.Client, base_url: str) -> list[BenchResult]:
    """Measure the base64 encoding overhead at different payload sizes."""
    results = []
    # Minimal create
    payload_min = _build_create_bytes(full=False)
    payload_full = _build_create_bytes(full=True)

    for label, payload in [("~50 bytes (minimal)", payload_min), ("~300 bytes (full)", payload_full)]:
        encoded = encode_grpc_web_request(payload)
        latencies: list[float] = []
        errors = 0
        n = 300
        t0 = time.perf_counter()
        for _ in range(n):
            with Timer() as t:
                try:
                    r = _post_grpc_web(client, base_url, "CreateSatsangi", payload)
                    if r.headers.get("grpc-status") != "0":
                        errors += 1
                except Exception:
                    errors += 1
            latencies.append(t.elapsed_ms)
        duration = time.perf_counter() - t0
        result = BenchResult(f"Proxy payload {label}", n, duration, latencies, errors)
        result.extra["raw_bytes"] = len(payload)
        result.extra["wire_bytes"] = len(encoded)
        result.extra["overhead_pct"] = (len(encoded) - len(payload)) / len(payload) * 100
        results.append(result)
    return results


def bench_proxy_rapid_fire(client: httpx.Client, base_url: str, duration_s: float = 5.0) -> BenchResult:
    """Sustained throughput — max requests/second through the proxy."""
    payload = satsangi_pb2.HealthRequest().SerializeToString()
    latencies: list[float] = []
    errors = 0
    count = 0
    deadline = time.perf_counter() + duration_s
    t0 = time.perf_counter()
    while time.perf_counter() < deadline:
        with Timer() as t:
            try:
                r = _post_grpc_web(client, base_url, "Health", payload)
                if r.headers.get("grpc-status") != "0":
                    errors += 1
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
        count += 1
    elapsed = time.perf_counter() - t0
    return BenchResult(f"Proxy Rapid-Fire ({duration_s:.0f}s)", count, elapsed, latencies, errors)


def bench_proxy_malformed(client: httpx.Client, base_url: str, n: int = 200) -> BenchResult:
    """Send malformed grpc-web frames — test error handling path."""
    latencies: list[float] = []
    errors = 0
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            try:
                r = client.post(
                    f"{base_url}/{_SERVICE_PREFIX}/Health",
                    content=b"not-valid-base64!!!",
                    headers=_HEADERS,
                )
                if r.status_code == 400:
                    pass  # expected
                else:
                    errors += 1
            except Exception:
                errors += 1
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    result = BenchResult("Proxy malformed request handling", n, duration, latencies, errors)
    result.extra["note"] = "400 responses are expected (not errors)"
    return result


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_all(grpc_port: int = 50052, proxy_port: int = 18080) -> list[BenchResult]:
    """Run all proxy benchmarks and return results."""
    logger.info("Starting grpc-web proxy benchmarks (proxy=%d, grpc=%d)", proxy_port, grpc_port)

    server = start_mock_grpc_server(port=grpc_port, max_workers=10)
    time.sleep(0.3)
    start_mock_proxy(proxy_port=proxy_port, grpc_port=grpc_port)

    base_url = f"http://127.0.0.1:{proxy_port}"
    client = httpx.Client(timeout=30.0)

    results: list[BenchResult] = []

    logger.info("  [1/8] HTTP healthz baseline...")
    results.append(bench_proxy_health(client, base_url, n=500))

    logger.info("  [2/8] gRPC Health through proxy...")
    results.append(bench_proxy_grpc_health(client, base_url, n=500))

    logger.info("  [3/8] CreateSatsangi (minimal) through proxy...")
    results.append(bench_proxy_create_minimal(client, base_url, n=500))

    logger.info("  [4/8] CreateSatsangi (full) through proxy...")
    results.append(bench_proxy_create_full(client, base_url, n=500))

    logger.info("  [5/8] Search through proxy...")
    results.append(bench_proxy_search(client, base_url, n=300, store_size=500))

    logger.info("  [6/8] ListAll scaling through proxy...")
    results.extend(bench_proxy_list_scaling(client, base_url))

    logger.info("  [7/8] Payload size comparison...")
    results.extend(bench_proxy_payload_sizes(client, base_url))

    logger.info("  [8/8] Rapid-fire throughput (5s)...")
    results.append(bench_proxy_rapid_fire(client, base_url, duration_s=5.0))

    client.close()
    server.stop(grace=1)

    print_results(results, "grpc-web Proxy Benchmarks (Full HTTP Path)")
    return results


if __name__ == "__main__":
    run_all()
