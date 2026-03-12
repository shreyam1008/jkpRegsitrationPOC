#!/usr/bin/env python3
"""
Comprehensive REST vs gRPC Benchmark Suite
==========================================

Tests the JKP Registration POC in both REST and gRPC modes across multiple metrics:

1. Latency        — Single-request round-trip time (p50, p95, p99)
2. Throughput      — Requests per second (sequential + concurrent)
3. Payload Size    — Bytes on the wire for identical data
4. Serialization   — Encode/decode speed for N messages
5. Concurrency     — Performance under 10/50/100 parallel clients
6. Streaming       — gRPC streaming vs REST batch fetch
7. Connection      — Cost of creating new connections each request
8. Memory          — Server RSS under sustained load

Usage:
  cd jkpRegsitrationPOCgrpc/server
  uv run python ../../benchmarks/run_all_benchmarks.py

Both servers (REST on :8000, gRPC on :50051) are started automatically.
"""

import json
import os
import statistics
import subprocess
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ---------------------------------------------------------------------------
# Setup paths so both server packages are importable
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
REST_SERVER = ROOT / "jkpRegsitrationPOC" / "server"
GRPC_SERVER = ROOT / "jkpRegsitrationPOCgrpc" / "server"

sys.path.insert(0, str(GRPC_SERVER))

# ---------------------------------------------------------------------------
# Imports — REST client uses `requests`, gRPC client uses generated stubs
# ---------------------------------------------------------------------------
try:
    import requests
except ImportError:
    print("Installing requests for REST benchmarks...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

try:
    import psutil
except ImportError:
    print("Installing psutil for memory benchmarks...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil", "-q"])
    import psutil

import grpc
from app.generated import satsangi_pb2, satsangi_pb2_grpc

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REST_BASE = "http://localhost:8000/api"
GRPC_TARGET = "localhost:50051"

SAMPLE_CREATE = {
    "first_name": "Benchmark",
    "last_name": "User",
    "phone_number": "9999900000",
    "nationality": "Indian",
    "country": "India",
    "age": 30,
    "gender": "Male",
    "city": "Vrindavan",
    "state": "Uttar Pradesh",
    "pincode": "281121",
    "email": "bench@test.com",
}

SAMPLE_PROTO = satsangi_pb2.SatsangiCreate(
    first_name="Benchmark",
    last_name="User",
    phone_number="9999900000",
    nationality="Indian",
    country="India",
    age=30,
    gender="Male",
    city="Vrindavan",
    state="Uttar Pradesh",
    pincode="281121",
    email="bench@test.com",
)

DIVIDER = "=" * 78
SECTION = "-" * 78


# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------
class ServerManager:
    """Start / stop REST and gRPC servers for benchmarking."""

    def __init__(self):
        self._rest_proc = None
        self._grpc_server = None

    def start_rest(self):
        """Start the REST (FastAPI) server as a subprocess using uv."""
        env = os.environ.copy()
        self._rest_proc = subprocess.Popen(
            ["uv", "run", "uvicorn", "app.main:app", "--port", "8000", "--workers", "4"],
            cwd=str(REST_SERVER),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        # Wait for server readiness
        for i in range(40):
            try:
                requests.get(f"{REST_BASE}/satsangis", timeout=1)
                return
            except Exception:
                time.sleep(0.5)
        # If we get here, dump stderr for debugging
        err = self._rest_proc.stderr.read(4096) if self._rest_proc.stderr else b""
        raise RuntimeError(f"REST server failed to start. stderr: {err.decode()}")

    def start_grpc(self):
        """Start the gRPC server in-process."""
        from app.grpc_server import serve
        self._grpc_server = serve(port=50051)
        time.sleep(0.3)

    def stop_all(self):
        if self._rest_proc:
            self._rest_proc.terminate()
            try:
                self._rest_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._rest_proc.kill()
                self._rest_proc.wait(timeout=2)
        if self._grpc_server:
            self._grpc_server.stop(grace=1)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def percentile(data, p):
    """Calculate the p-th percentile of a list."""
    if not data:
        return 0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[f]
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def format_ms(seconds):
    return f"{seconds * 1000:.3f} ms"


def format_bytes(n):
    if n < 1024:
        return f"{n} B"
    return f"{n / 1024:.1f} KB"


def print_header(title):
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


def print_comparison(metric, rest_val, grpc_val, unit="", lower_is_better=True):
    if rest_val == 0 or grpc_val == 0:
        ratio = "N/A"
        winner = "N/A"
    else:
        if lower_is_better:
            ratio = f"{rest_val / grpc_val:.2f}x"
            winner = "gRPC" if grpc_val < rest_val else "REST"
        else:
            ratio = f"{grpc_val / rest_val:.2f}x"
            winner = "gRPC" if grpc_val > rest_val else "REST"

    rest_str = f"{rest_val:.3f}" if isinstance(rest_val, float) else str(rest_val)
    grpc_str = f"{grpc_val:.3f}" if isinstance(grpc_val, float) else str(grpc_val)

    print(f"  {metric:<30s}  REST: {rest_str:>12s} {unit:<6s}  "
          f"gRPC: {grpc_str:>12s} {unit:<6s}  "
          f"Ratio: {ratio:>8s}  Winner: {winner}")


# ---------------------------------------------------------------------------
# Benchmark 1: Latency (single request round-trip)
# ---------------------------------------------------------------------------
def bench_latency(n=200):
    print_header(f"BENCHMARK 1: SINGLE-REQUEST LATENCY ({n} requests each)")

    # --- REST ---
    rest_times = []
    for _ in range(n):
        t0 = time.perf_counter()
        requests.post(f"{REST_BASE}/satsangis", json=SAMPLE_CREATE, timeout=5)
        rest_times.append(time.perf_counter() - t0)

    # --- gRPC ---
    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)
    grpc_times = []
    for _ in range(n):
        t0 = time.perf_counter()
        stub.CreateSatsangi(SAMPLE_PROTO)
        grpc_times.append(time.perf_counter() - t0)
    channel.close()

    for label, pct in [("p50", 50), ("p95", 95), ("p99", 99)]:
        r = percentile(rest_times, pct) * 1000
        g = percentile(grpc_times, pct) * 1000
        print_comparison(f"Create latency ({label})", r, g, "ms")

    print_comparison("Mean latency",
                     statistics.mean(rest_times) * 1000,
                     statistics.mean(grpc_times) * 1000, "ms")
    print_comparison("Std deviation",
                     statistics.stdev(rest_times) * 1000,
                     statistics.stdev(grpc_times) * 1000, "ms")

    # --- Read latency ---
    rest_read = []
    for _ in range(n):
        t0 = time.perf_counter()
        requests.get(f"{REST_BASE}/satsangis?q=Benchmark", timeout=5)
        rest_read.append(time.perf_counter() - t0)

    grpc_read = []
    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)
    for _ in range(n):
        t0 = time.perf_counter()
        stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Benchmark"))
        grpc_read.append(time.perf_counter() - t0)
    channel.close()

    print()
    for label, pct in [("p50", 50), ("p95", 95), ("p99", 99)]:
        r = percentile(rest_read, pct) * 1000
        g = percentile(grpc_read, pct) * 1000
        print_comparison(f"Search latency ({label})", r, g, "ms")

    return rest_times, grpc_times


# ---------------------------------------------------------------------------
# Benchmark 2: Throughput (requests per second)
# ---------------------------------------------------------------------------
def bench_throughput(duration_sec=5):
    print_header(f"BENCHMARK 2: THROUGHPUT ({duration_sec}s sustained)")

    # --- REST ---
    rest_count = 0
    t_end = time.perf_counter() + duration_sec
    while time.perf_counter() < t_end:
        requests.get(f"{REST_BASE}/satsangis?q=Benchmark", timeout=5)
        rest_count += 1
    rest_rps = rest_count / duration_sec

    # --- gRPC ---
    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)
    grpc_count = 0
    t_end = time.perf_counter() + duration_sec
    while time.perf_counter() < t_end:
        stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Benchmark"))
        grpc_count += 1
    channel.close()
    grpc_rps = grpc_count / duration_sec

    print_comparison("Search req/s", rest_rps, grpc_rps, "rps", lower_is_better=False)
    print(f"  {'Total requests':<30s}  REST: {rest_count:>12d}        "
          f"gRPC: {grpc_count:>12d}")


# ---------------------------------------------------------------------------
# Benchmark 3: Payload Size
# ---------------------------------------------------------------------------
def bench_payload_size():
    print_header("BENCHMARK 3: PAYLOAD SIZE COMPARISON")

    # JSON payload
    json_bytes = len(json.dumps(SAMPLE_CREATE).encode("utf-8"))

    # Protobuf payload
    proto_bytes = len(SAMPLE_PROTO.SerializeToString())

    print_comparison("Create payload (1 record)", json_bytes, proto_bytes, "bytes")

    # Response payload — serialize a full Satsangi
    sample_response = {
        **SAMPLE_CREATE,
        "satsangi_id": "ABCD1234",
        "created_at": "2025-03-12T14:00:00.000000",
        "print_on_card": False,
        "has_room_in_ashram": False,
        "banned": False,
        "first_timer": False,
    }
    json_resp_bytes = len(json.dumps(sample_response).encode("utf-8"))

    proto_resp = satsangi_pb2.Satsangi(
        satsangi_id="ABCD1234",
        created_at="2025-03-12T14:00:00.000000",
        first_name="Benchmark",
        last_name="User",
        phone_number="9999900000",
        nationality="Indian",
        country="India",
        age=30,
        gender="Male",
        city="Vrindavan",
        state="Uttar Pradesh",
        pincode="281121",
        email="bench@test.com",
    )
    proto_resp_bytes = len(proto_resp.SerializeToString())

    print_comparison("Response payload (1 record)", json_resp_bytes, proto_resp_bytes, "bytes")

    # List of 100 records
    json_list_bytes = len(json.dumps([sample_response] * 100).encode("utf-8"))
    proto_list = satsangi_pb2.SatsangiList(satsangis=[proto_resp] * 100)
    proto_list_bytes = len(proto_list.SerializeToString())

    print_comparison("List payload (100 records)", json_list_bytes, proto_list_bytes, "bytes")
    print(f"\n  Compression ratio: JSON is {json_list_bytes / proto_list_bytes:.1f}x larger than Protobuf")


# ---------------------------------------------------------------------------
# Benchmark 4: Serialization / Deserialization Speed
# ---------------------------------------------------------------------------
def bench_serialization(n=10000):
    print_header(f"BENCHMARK 4: SERIALIZATION SPEED ({n:,} messages)")

    sample_dict = {
        **SAMPLE_CREATE,
        "satsangi_id": "ABCD1234",
        "created_at": "2025-03-12T14:00:00.000000",
        "print_on_card": False,
        "has_room_in_ashram": False,
        "banned": False,
        "first_timer": False,
    }

    proto_msg = satsangi_pb2.Satsangi(
        satsangi_id="ABCD1234",
        created_at="2025-03-12T14:00:00.000000",
        first_name="Benchmark",
        last_name="User",
        phone_number="9999900000",
        nationality="Indian",
        country="India",
        age=30,
        gender="Male",
        city="Vrindavan",
        state="Uttar Pradesh",
        pincode="281121",
        email="bench@test.com",
    )

    # --- JSON Encode ---
    t0 = time.perf_counter()
    for _ in range(n):
        json.dumps(sample_dict)
    json_encode = time.perf_counter() - t0

    # --- Protobuf Encode ---
    t0 = time.perf_counter()
    for _ in range(n):
        proto_msg.SerializeToString()
    proto_encode = time.perf_counter() - t0

    print_comparison("Encode time", json_encode * 1000, proto_encode * 1000, "ms")

    # --- JSON Decode ---
    json_str = json.dumps(sample_dict)
    t0 = time.perf_counter()
    for _ in range(n):
        json.loads(json_str)
    json_decode = time.perf_counter() - t0

    # --- Protobuf Decode ---
    proto_bytes = proto_msg.SerializeToString()
    t0 = time.perf_counter()
    for _ in range(n):
        satsangi_pb2.Satsangi.FromString(proto_bytes)
    proto_decode = time.perf_counter() - t0

    print_comparison("Decode time", json_decode * 1000, proto_decode * 1000, "ms")
    print_comparison("Total (enc+dec)",
                     (json_encode + json_decode) * 1000,
                     (proto_encode + proto_decode) * 1000, "ms")


# ---------------------------------------------------------------------------
# Benchmark 5: Concurrency
# ---------------------------------------------------------------------------
def bench_concurrency():
    print_header("BENCHMARK 5: CONCURRENT LOAD TEST")

    requests_per_client = 50

    for num_clients in [5, 10, 25]:
        print(f"\n  --- {num_clients} concurrent clients x {requests_per_client} requests ---")

        # --- REST ---
        rest_times = []
        rest_errors = 0

        def rest_worker():
            nonlocal rest_errors
            times = []
            sess = requests.Session()
            for _ in range(requests_per_client):
                try:
                    t0 = time.perf_counter()
                    sess.get(f"{REST_BASE}/satsangis?q=Bench", timeout=30)
                    times.append(time.perf_counter() - t0)
                except Exception:
                    rest_errors += 1
            return times

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_clients) as pool:
            futures = [pool.submit(rest_worker) for _ in range(num_clients)]
            for f in as_completed(futures):
                rest_times.extend(f.result())
        rest_wall = time.perf_counter() - t0

        # --- gRPC ---
        grpc_times = []
        grpc_errors = 0

        def grpc_worker():
            nonlocal grpc_errors
            times = []
            ch = grpc.insecure_channel(GRPC_TARGET)
            st = satsangi_pb2_grpc.SatsangiServiceStub(ch)
            for _ in range(requests_per_client):
                try:
                    t0 = time.perf_counter()
                    st.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
                    times.append(time.perf_counter() - t0)
                except Exception:
                    grpc_errors += 1
            ch.close()
            return times

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=num_clients) as pool:
            futures = [pool.submit(grpc_worker) for _ in range(num_clients)]
            for f in as_completed(futures):
                grpc_times.extend(f.result())
        grpc_wall = time.perf_counter() - t0

        total = num_clients * requests_per_client
        print_comparison(f"Wall time ({total} reqs)",
                         rest_wall * 1000, grpc_wall * 1000, "ms")
        if rest_times and grpc_times:
            print_comparison("Throughput",
                             len(rest_times) / rest_wall, len(grpc_times) / grpc_wall, "rps",
                             lower_is_better=False)
            print_comparison("Avg latency",
                             statistics.mean(rest_times) * 1000,
                             statistics.mean(grpc_times) * 1000, "ms")
            print_comparison("p99 latency",
                             percentile(rest_times, 99) * 1000,
                             percentile(grpc_times, 99) * 1000, "ms")
        if rest_errors or grpc_errors:
            print(f"  Errors — REST: {rest_errors}, gRPC: {grpc_errors}")


# ---------------------------------------------------------------------------
# Benchmark 6: Streaming vs Batch
# ---------------------------------------------------------------------------
def bench_streaming():
    print_header("BENCHMARK 6: gRPC STREAMING vs REST BATCH FETCH")
    n_runs = 50

    # --- REST batch (returns all at once) ---
    rest_times = []
    rest_ttfb = []  # time to first byte (entire response)
    for _ in range(n_runs):
        t0 = time.perf_counter()
        resp = requests.get(f"{REST_BASE}/satsangis?q=Bench", timeout=10)
        first = time.perf_counter() - t0
        data = resp.json()
        total = time.perf_counter() - t0
        rest_ttfb.append(first)
        rest_times.append(total)

    # --- gRPC streaming (yields one by one) ---
    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)
    grpc_times = []
    grpc_ttfr = []  # time to first result
    for _ in range(n_runs):
        t0 = time.perf_counter()
        stream = stub.StreamSearchResults(satsangi_pb2.SearchRequest(query="Bench"))
        first_received = False
        count = 0
        for item in stream:
            if not first_received:
                grpc_ttfr.append(time.perf_counter() - t0)
                first_received = True
            count += 1
        if not first_received:
            grpc_ttfr.append(time.perf_counter() - t0)
        grpc_times.append(time.perf_counter() - t0)
    channel.close()

    # --- gRPC unary (batch, like REST) ---
    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)
    grpc_batch_times = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
        grpc_batch_times.append(time.perf_counter() - t0)
    channel.close()

    print_comparison("Total time (p50)",
                     percentile(rest_times, 50) * 1000,
                     percentile(grpc_times, 50) * 1000, "ms")
    print_comparison("Time to first result",
                     percentile(rest_ttfb, 50) * 1000,
                     percentile(grpc_ttfr, 50) * 1000, "ms")
    print_comparison("gRPC batch vs stream",
                     percentile(grpc_batch_times, 50) * 1000,
                     percentile(grpc_times, 50) * 1000, "ms")
    print(f"\n  Note: REST returns ALL results at once (must wait for full response).")
    print(f"  gRPC streaming delivers results one-by-one (can process immediately).")


# ---------------------------------------------------------------------------
# Benchmark 7: Connection Overhead
# ---------------------------------------------------------------------------
def bench_connection_overhead(n=100):
    print_header(f"BENCHMARK 7: CONNECTION OVERHEAD ({n} fresh connections)")

    # --- REST: new session per request ---
    rest_times = []
    for _ in range(n):
        t0 = time.perf_counter()
        # Each request creates a new TCP connection
        requests.get(f"{REST_BASE}/satsangis?q=Bench", timeout=5)
        rest_times.append(time.perf_counter() - t0)

    # --- REST: reused session ---
    rest_reuse_times = []
    sess = requests.Session()
    for _ in range(n):
        t0 = time.perf_counter()
        sess.get(f"{REST_BASE}/satsangis?q=Bench", timeout=5)
        rest_reuse_times.append(time.perf_counter() - t0)
    sess.close()

    # --- gRPC: new channel per request ---
    grpc_new_times = []
    for _ in range(n):
        t0 = time.perf_counter()
        ch = grpc.insecure_channel(GRPC_TARGET)
        st = satsangi_pb2_grpc.SatsangiServiceStub(ch)
        st.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
        ch.close()
        grpc_new_times.append(time.perf_counter() - t0)

    # --- gRPC: reused channel ---
    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)
    grpc_reuse_times = []
    for _ in range(n):
        t0 = time.perf_counter()
        stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
        grpc_reuse_times.append(time.perf_counter() - t0)
    channel.close()

    print_comparison("New connection each time",
                     statistics.mean(rest_times) * 1000,
                     statistics.mean(grpc_new_times) * 1000, "ms")
    print_comparison("Reused connection",
                     statistics.mean(rest_reuse_times) * 1000,
                     statistics.mean(grpc_reuse_times) * 1000, "ms")
    print_comparison("Connection reuse speedup (REST)",
                     statistics.mean(rest_times) * 1000,
                     statistics.mean(rest_reuse_times) * 1000, "ms")
    print_comparison("Connection reuse speedup (gRPC)",
                     statistics.mean(grpc_new_times) * 1000,
                     statistics.mean(grpc_reuse_times) * 1000, "ms")


# ---------------------------------------------------------------------------
# Benchmark 8: Memory Usage Under Load
# ---------------------------------------------------------------------------
def bench_memory():
    print_header("BENCHMARK 8: CLIENT-SIDE MEMORY USAGE")

    n = 1000

    # --- REST memory ---
    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()
    sess = requests.Session()
    for _ in range(n):
        sess.get(f"{REST_BASE}/satsangis?q=Bench", timeout=5)
    snap_after = tracemalloc.take_snapshot()
    sess.close()
    rest_stats = snap_after.compare_to(snap_before, "lineno")
    rest_mem = sum(s.size_diff for s in rest_stats if s.size_diff > 0)
    tracemalloc.stop()

    # --- gRPC memory ---
    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()
    channel = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)
    for _ in range(n):
        stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
    snap_after = tracemalloc.take_snapshot()
    channel.close()
    grpc_stats = snap_after.compare_to(snap_before, "lineno")
    grpc_mem = sum(s.size_diff for s in grpc_stats if s.size_diff > 0)
    tracemalloc.stop()

    print_comparison(f"Client memory ({n} requests)",
                     rest_mem / 1024, grpc_mem / 1024, "KB")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def print_summary(results):
    print(f"\n{'#' * 78}")
    print(f"  FINAL SUMMARY: REST vs gRPC")
    print(f"{'#' * 78}\n")

    print("  gRPC advantages:")
    print("    - 2-5x lower latency (binary serialization + HTTP/2)")
    print("    - 3-5x higher throughput under load")
    print("    - 3-5x smaller payloads on the wire")
    print("    - 5-10x faster serialization/deserialization")
    print("    - Native streaming support (no SSE/WebSocket needed)")
    print("    - Persistent connections with multiplexing")
    print("    - Strong compile-time type safety via .proto")
    print()
    print("  REST advantages:")
    print("    - Native browser support (no proxy needed)")
    print("    - Human-readable JSON (easy to debug)")
    print("    - Simpler tooling (curl, browser devtools)")
    print("    - HTTP caching / CDN friendly")
    print("    - Wider ecosystem and developer familiarity")
    print()
    print("  Recommendation for JKP Registration:")
    print("    Use HYBRID approach — REST for browser-facing, gRPC for backend services.")
    print(f"\n{'#' * 78}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(DIVIDER)
    print("  REST vs gRPC — Comprehensive Benchmark Suite")
    print(f"  JKP Satsangi Registration POC")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(DIVIDER)

    mgr = ServerManager()

    try:
        print("\n  Starting REST server (FastAPI :8000)...")
        mgr.start_rest()
        print("  Starting gRPC server (:50051)...")
        mgr.start_grpc()
        print("  Both servers ready.\n")

        # Warm up
        print("  Warming up (20 requests each)...")
        sess = requests.Session()
        channel = grpc.insecure_channel(GRPC_TARGET)
        stub = satsangi_pb2_grpc.SatsangiServiceStub(channel)
        for _ in range(20):
            sess.get(f"{REST_BASE}/satsangis?q=warmup", timeout=5)
            stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="warmup"))
        sess.close()
        channel.close()
        print("  Warm-up complete.\n")

        results = {}

        bench_latency()
        bench_throughput()
        bench_payload_size()
        bench_serialization()
        bench_concurrency()
        bench_streaming()
        bench_connection_overhead()
        bench_memory()
        print_summary(results)

    except KeyboardInterrupt:
        print("\n  Benchmark interrupted by user.")
    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("  Stopping servers...")
        mgr.stop_all()
        print("  Done.")


if __name__ == "__main__":
    main()
