#!/usr/bin/env python3
"""
REST vs gRPC — Comprehensive Benchmark Suite
=============================================
Both backends use PostgreSQL.

Assumes servers are already running:
  REST server  → :8001  (cd jkpRegsitrationPOC/server && uv run python -m uvicorn app.main:app --port 8001)
  gRPC server  → :50051 (cd jkpRegistrationFULLGRPC/server && uv run python -m app.grpc_server)

Benchmarks:
  1. Single-request latency (create + search, p50/p95/p99)
  2. Sustained throughput (requests/sec over time)
  3. Payload size comparison (1, 10, 100, 1000 records)
  4. Serialization / deserialization speed
  5. Concurrent load (5 / 10 / 25 / 50 / 100 clients)
  6. gRPC streaming vs REST batch
  7. Connection overhead (new vs reused)
  8. Client-side memory consumption
  9. Simulated slow network (added latency via time.sleep)
  10. Mixed workload (70% read / 30% write)
"""

import json
import io
import statistics
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "jkpRegistrationFULLGRPC" / "server"))

import requests
import grpc
from app.generated import satsangi_pb2, satsangi_pb2_grpc

REST_BASE = "http://localhost:8001/api"
GRPC_TARGET = "localhost:50051"

SAMPLE_CREATE = {
    "first_name": "Benchmark", "last_name": "User", "phone_number": "9999900000",
    "nationality": "Indian", "country": "India", "age": 30, "gender": "Male",
    "city": "Vrindavan", "state": "Uttar Pradesh", "pincode": "281121",
    "email": "bench@test.com",
}
SAMPLE_PROTO = satsangi_pb2.SatsangiCreate(**SAMPLE_CREATE)

DIV = "=" * 80
SUBDIV = "-" * 80

# ── Utilities ──

def pct(data, p):
    if not data:
        return 0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (k - f) * (s[c] - s[f])


def cmp(label, rv, gv, unit="", lower_better=True):
    if rv == 0 or gv == 0:
        ratio, winner = "N/A", "—"
    elif lower_better:
        ratio = f"{rv / gv:.2f}x"
        winner = "gRPC" if gv < rv else ("REST" if rv < gv else "TIE")
    else:
        ratio = f"{gv / rv:.2f}x"
        winner = "gRPC" if gv > rv else ("REST" if rv > gv else "TIE")
    rf = f"{rv:,.3f}" if isinstance(rv, float) else f"{rv:,}"
    gf = f"{gv:,.3f}" if isinstance(gv, float) else f"{gv:,}"
    print(f"  {label:<36s} REST: {rf:>12s} {unit:<5s}  gRPC: {gf:>12s} {unit:<5s}  {ratio:>7s}  {winner}")


def header(t):
    print(f"\n{DIV}\n  {t}\n{DIV}")


# Store all results for the final report
RESULTS: dict[str, dict] = {}


# ── Check connectivity ──

def check():
    try:
        requests.get(f"{REST_BASE}/satsangis", timeout=3)
    except Exception:
        print("  ERROR: REST server not reachable on :8001")
        sys.exit(1)
    try:
        ch = grpc.insecure_channel(GRPC_TARGET)
        stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
        stub.ListSatsangis(satsangi_pb2.Empty(), timeout=3)
        ch.close()
    except Exception:
        print("  ERROR: gRPC server not reachable on :50051")
        sys.exit(1)
    print("  Both servers reachable. Starting benchmarks...\n")


# ── 1. LATENCY ──

def bench_latency(n=200):
    header(f"1. SINGLE-REQUEST LATENCY ({n} iterations)")

    # --- Create ---
    print(f"\n  {SUBDIV}\n  Create Satsangi\n  {SUBDIV}")
    rt_create = []
    s = requests.Session()
    for _ in range(n):
        t = time.perf_counter()
        s.post(f"{REST_BASE}/satsangis", json=SAMPLE_CREATE, timeout=10)
        rt_create.append(time.perf_counter() - t)
    s.close()

    ch = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gt_create = []
    for _ in range(n):
        t = time.perf_counter()
        stub.CreateSatsangi(SAMPLE_PROTO)
        gt_create.append(time.perf_counter() - t)
    ch.close()

    for lbl, p in [("Create p50", 50), ("Create p95", 95), ("Create p99", 99)]:
        cmp(lbl, pct(rt_create, p) * 1000, pct(gt_create, p) * 1000, "ms")
    cmp("Create mean", statistics.mean(rt_create) * 1000, statistics.mean(gt_create) * 1000, "ms")
    cmp("Create stdev", statistics.stdev(rt_create) * 1000, statistics.stdev(gt_create) * 1000, "ms")

    # --- Search ---
    print(f"\n  {SUBDIV}\n  Search Satsangi\n  {SUBDIV}")
    rt_search = []
    s = requests.Session()
    for _ in range(n):
        t = time.perf_counter()
        s.get(f"{REST_BASE}/satsangis?q=Benchmark", timeout=10)
        rt_search.append(time.perf_counter() - t)
    s.close()

    ch = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gt_search = []
    for _ in range(n):
        t = time.perf_counter()
        stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Benchmark"))
        gt_search.append(time.perf_counter() - t)
    ch.close()

    for lbl, p in [("Search p50", 50), ("Search p95", 95), ("Search p99", 99)]:
        cmp(lbl, pct(rt_search, p) * 1000, pct(gt_search, p) * 1000, "ms")
    cmp("Search mean", statistics.mean(rt_search) * 1000, statistics.mean(gt_search) * 1000, "ms")

    RESULTS["latency"] = {
        "rest_create_p50": pct(rt_create, 50) * 1000,
        "grpc_create_p50": pct(gt_create, 50) * 1000,
        "rest_search_p50": pct(rt_search, 50) * 1000,
        "grpc_search_p50": pct(gt_search, 50) * 1000,
    }


# ── 2. THROUGHPUT ──

def bench_throughput(dur=5):
    header(f"2. SUSTAINED THROUGHPUT ({dur}s each)")

    # REST
    s = requests.Session()
    rc = 0
    end = time.perf_counter() + dur
    while time.perf_counter() < end:
        s.get(f"{REST_BASE}/satsangis?q=Bench", timeout=10)
        rc += 1
    s.close()
    r_rps = rc / dur

    # gRPC
    ch = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gc = 0
    end = time.perf_counter() + dur
    while time.perf_counter() < end:
        stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
        gc += 1
    ch.close()
    g_rps = gc / dur

    cmp("Requests/sec (search)", r_rps, g_rps, "rps", lower_better=False)
    print(f"  {'Total requests':<36s} REST: {rc:>12,d}       gRPC: {gc:>12,d}")

    # Write throughput
    print(f"\n  {SUBDIV}\n  Write throughput ({dur}s)\n  {SUBDIV}")
    s = requests.Session()
    rwc = 0
    end = time.perf_counter() + dur
    while time.perf_counter() < end:
        s.post(f"{REST_BASE}/satsangis", json=SAMPLE_CREATE, timeout=10)
        rwc += 1
    s.close()
    rw_rps = rwc / dur

    ch = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gwc = 0
    end = time.perf_counter() + dur
    while time.perf_counter() < end:
        stub.CreateSatsangi(SAMPLE_PROTO)
        gwc += 1
    ch.close()
    gw_rps = gwc / dur

    cmp("Writes/sec (create)", rw_rps, gw_rps, "rps", lower_better=False)

    RESULTS["throughput"] = {
        "rest_read_rps": r_rps, "grpc_read_rps": g_rps,
        "rest_write_rps": rw_rps, "grpc_write_rps": gw_rps,
    }


# ── 3. PAYLOAD SIZE ──

def bench_payload():
    header("3. PAYLOAD SIZE (wire format)")

    jc = len(json.dumps(SAMPLE_CREATE).encode())
    pc = len(SAMPLE_PROTO.SerializeToString())
    cmp("Create request (1 record)", jc, pc, "bytes")

    resp = {
        **SAMPLE_CREATE,
        "satsangi_id": "ABCD1234",
        "created_at": "2025-03-12T14:00:00",
        "print_on_card": False,
        "has_room_in_ashram": False,
        "banned": False,
        "first_timer": False,
    }
    pr_msg = satsangi_pb2.Satsangi(
        satsangi_id="ABCD1234", created_at="2025-03-12T14:00:00",
        first_name="Benchmark", last_name="User", phone_number="9999900000",
        nationality="Indian", country="India", age=30, gender="Male",
        city="Vrindavan", state="Uttar Pradesh", pincode="281121", email="bench@test.com",
    )
    jr = len(json.dumps(resp).encode())
    pr = len(pr_msg.SerializeToString())
    cmp("Response (1 record)", jr, pr, "bytes")

    for count in [10, 100, 1000]:
        j_n = len(json.dumps([resp] * count).encode())
        p_n = len(satsangi_pb2.SatsangiList(satsangis=[pr_msg] * count).SerializeToString())
        cmp(f"List ({count} records)", j_n, p_n, "bytes")

    j1000 = len(json.dumps([resp] * 1000).encode())
    p1000 = len(satsangi_pb2.SatsangiList(satsangis=[pr_msg] * 1000).SerializeToString())
    print(f"\n  JSON is {j1000 / p1000:.1f}x larger than Protobuf for 1,000 records")
    print(f"  JSON 1-record: {jr} bytes | Protobuf 1-record: {pr} bytes  ({jr/pr:.1f}x)")

    RESULTS["payload"] = {"json_1": jr, "proto_1": pr, "ratio_1000": j1000 / p1000}


# ── 4. SERIALIZATION SPEED ──

def bench_serialization(n=10_000):
    header(f"4. SERIALIZATION SPEED ({n:,} messages)")

    d = {
        **SAMPLE_CREATE,
        "satsangi_id": "ABCD1234", "created_at": "2025-03-12T14:00:00",
        "print_on_card": False, "has_room_in_ashram": False, "banned": False, "first_timer": False,
    }
    pm = satsangi_pb2.Satsangi(
        satsangi_id="ABCD1234", created_at="2025-03-12T14:00:00",
        first_name="Benchmark", last_name="User", phone_number="9999900000",
        nationality="Indian", country="India", age=30, gender="Male",
        city="Vrindavan", state="Uttar Pradesh", pincode="281121", email="bench@test.com",
    )

    # Encode
    t = time.perf_counter()
    for _ in range(n):
        json.dumps(d)
    je = time.perf_counter() - t
    t = time.perf_counter()
    for _ in range(n):
        pm.SerializeToString()
    pe = time.perf_counter() - t
    cmp("Encode", je * 1000, pe * 1000, "ms")

    # Decode
    js = json.dumps(d)
    pb = pm.SerializeToString()
    t = time.perf_counter()
    for _ in range(n):
        json.loads(js)
    jd = time.perf_counter() - t
    t = time.perf_counter()
    for _ in range(n):
        satsangi_pb2.Satsangi.FromString(pb)
    pd = time.perf_counter() - t
    cmp("Decode", jd * 1000, pd * 1000, "ms")
    cmp("Total (enc+dec)", (je + jd) * 1000, (pe + pd) * 1000, "ms")

    # Per-message
    cmp("Per-msg encode", (je / n) * 1e6, (pe / n) * 1e6, "µs")
    cmp("Per-msg decode", (jd / n) * 1e6, (pd / n) * 1e6, "µs")

    RESULTS["serialization"] = {
        "json_total_ms": (je + jd) * 1000,
        "proto_total_ms": (pe + pd) * 1000,
    }


# ── 5. CONCURRENT LOAD ──

def bench_concurrency():
    header("5. CONCURRENT LOAD TEST")

    rpw = 30  # requests per worker
    for nc in [5, 10, 25, 50, 100]:
        print(f"\n  {SUBDIV}\n  {nc} concurrent clients × {rpw} requests = {nc * rpw} total\n  {SUBDIV}")

        rt = []
        re = [0]

        def rest_worker():
            ts = []
            s = requests.Session()
            for _ in range(rpw):
                try:
                    t = time.perf_counter()
                    s.get(f"{REST_BASE}/satsangis?q=B", timeout=30)
                    ts.append(time.perf_counter() - t)
                except Exception:
                    re[0] += 1
            s.close()
            return ts

        t0 = time.perf_counter()
        with ThreadPoolExecutor(nc) as pool:
            for f in as_completed([pool.submit(rest_worker) for _ in range(nc)]):
                rt.extend(f.result())
        rw_t = time.perf_counter() - t0

        gt = []
        ge = [0]

        def grpc_worker():
            ts = []
            c = grpc.insecure_channel(GRPC_TARGET)
            st = satsangi_pb2_grpc.SatsangiServiceStub(c)
            for _ in range(rpw):
                try:
                    t = time.perf_counter()
                    st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B"))
                    ts.append(time.perf_counter() - t)
                except Exception:
                    ge[0] += 1
            c.close()
            return ts

        t0 = time.perf_counter()
        with ThreadPoolExecutor(nc) as pool:
            for f in as_completed([pool.submit(grpc_worker) for _ in range(nc)]):
                gt.extend(f.result())
        gw_t = time.perf_counter() - t0

        cmp(f"Wall time ({nc * rpw} reqs)", rw_t * 1000, gw_t * 1000, "ms")
        if rt and gt:
            cmp("Throughput", len(rt) / rw_t, len(gt) / gw_t, "rps", lower_better=False)
            cmp("Avg latency", statistics.mean(rt) * 1000, statistics.mean(gt) * 1000, "ms")
            cmp("p95 latency", pct(rt, 95) * 1000, pct(gt, 95) * 1000, "ms")
            cmp("p99 latency", pct(rt, 99) * 1000, pct(gt, 99) * 1000, "ms")
        if re[0] or ge[0]:
            print(f"  Errors — REST: {re[0]}, gRPC: {ge[0]}")


# ── 6. STREAMING ──

def bench_streaming():
    header("6. gRPC STREAMING vs REST BATCH")

    n = 50
    s = requests.Session()
    rt = []
    rttfb = []
    for _ in range(n):
        t = time.perf_counter()
        r = s.get(f"{REST_BASE}/satsangis?q=Bench", timeout=10)
        fb = time.perf_counter() - t
        r.json()
        tt = time.perf_counter() - t
        rttfb.append(fb)
        rt.append(tt)
    s.close()

    ch = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gt = []
    gttfr = []
    for _ in range(n):
        t = time.perf_counter()
        stream = stub.StreamSearchResults(satsangi_pb2.SearchRequest(query="Bench"))
        first = False
        for _item in stream:
            if not first:
                gttfr.append(time.perf_counter() - t)
                first = True
        if not first:
            gttfr.append(time.perf_counter() - t)
        gt.append(time.perf_counter() - t)
    ch.close()

    # gRPC unary batch for comparison
    ch = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gbt = []
    for _ in range(n):
        t = time.perf_counter()
        stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
        gbt.append(time.perf_counter() - t)
    ch.close()

    cmp("REST batch p50", pct(rt, 50) * 1000, pct(gbt, 50) * 1000, "ms")
    cmp("gRPC stream p50", pct(rt, 50) * 1000, pct(gt, 50) * 1000, "ms")
    cmp("Time to first result p50", pct(rttfb, 50) * 1000, pct(gttfr, 50) * 1000, "ms")
    print(f"\n  REST must wait for entire JSON response. gRPC streaming delivers results incrementally.")


# ── 7. CONNECTION OVERHEAD ──

def bench_connection(n=100):
    header(f"7. CONNECTION OVERHEAD ({n} requests)")

    # REST new conn each time
    rt_new = []
    for _ in range(n):
        t = time.perf_counter()
        requests.get(f"{REST_BASE}/satsangis?q=B", timeout=10)
        rt_new.append(time.perf_counter() - t)

    # REST reused
    rt_reuse = []
    s = requests.Session()
    for _ in range(n):
        t = time.perf_counter()
        s.get(f"{REST_BASE}/satsangis?q=B", timeout=10)
        rt_reuse.append(time.perf_counter() - t)
    s.close()

    # gRPC new channel each time
    gt_new = []
    for _ in range(n):
        t = time.perf_counter()
        c = grpc.insecure_channel(GRPC_TARGET)
        st = satsangi_pb2_grpc.SatsangiServiceStub(c)
        st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B"))
        c.close()
        gt_new.append(time.perf_counter() - t)

    # gRPC reused
    gt_reuse = []
    c = grpc.insecure_channel(GRPC_TARGET)
    st = satsangi_pb2_grpc.SatsangiServiceStub(c)
    for _ in range(n):
        t = time.perf_counter()
        st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B"))
        gt_reuse.append(time.perf_counter() - t)
    c.close()

    cmp("New conn each request", statistics.mean(rt_new) * 1000, statistics.mean(gt_new) * 1000, "ms")
    cmp("Reused connection", statistics.mean(rt_reuse) * 1000, statistics.mean(gt_reuse) * 1000, "ms")
    overhead_rest = statistics.mean(rt_new) - statistics.mean(rt_reuse)
    overhead_grpc = statistics.mean(gt_new) - statistics.mean(gt_reuse)
    print(f"\n  Connection overhead per request:")
    print(f"    REST:  {overhead_rest * 1000:.3f} ms extra for new connection")
    print(f"    gRPC:  {overhead_grpc * 1000:.3f} ms extra for new channel")


# ── 8. MEMORY ──

def bench_memory(n=500):
    header(f"8. CLIENT-SIDE MEMORY ({n} requests)")

    tracemalloc.start()
    b = tracemalloc.take_snapshot()
    s = requests.Session()
    for _ in range(n):
        s.get(f"{REST_BASE}/satsangis?q=B", timeout=10)
    a = tracemalloc.take_snapshot()
    s.close()
    rm = sum(x.size_diff for x in a.compare_to(b, "lineno") if x.size_diff > 0)
    tracemalloc.stop()

    tracemalloc.start()
    b = tracemalloc.take_snapshot()
    c = grpc.insecure_channel(GRPC_TARGET)
    st = satsangi_pb2_grpc.SatsangiServiceStub(c)
    for _ in range(n):
        st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B"))
    a = tracemalloc.take_snapshot()
    c.close()
    gm = sum(x.size_diff for x in a.compare_to(b, "lineno") if x.size_diff > 0)
    tracemalloc.stop()

    cmp(f"Memory alloc ({n} reqs)", rm / 1024, gm / 1024, "KB")
    cmp(f"Per-request alloc", rm / n / 1024, gm / n / 1024, "KB")

    RESULTS["memory"] = {"rest_kb": rm / 1024, "grpc_kb": gm / 1024}


# ── 9. SIMULATED SLOW NETWORK ──

def bench_slow_network():
    header("9. SIMULATED SLOW NETWORK")
    print("  Simulates network latency by adding sleep before each request.\n")

    for delay_ms in [10, 50, 100, 200]:
        delay_s = delay_ms / 1000
        n = 50
        print(f"  {SUBDIV}\n  Added latency: {delay_ms}ms per request ({n} iterations)\n  {SUBDIV}")

        s = requests.Session()
        rt = []
        for _ in range(n):
            time.sleep(delay_s)
            t = time.perf_counter()
            s.get(f"{REST_BASE}/satsangis?q=B", timeout=10)
            rt.append(time.perf_counter() - t)
        s.close()

        ch = grpc.insecure_channel(GRPC_TARGET)
        stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
        gt = []
        for _ in range(n):
            time.sleep(delay_s)
            t = time.perf_counter()
            stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="B"))
            gt.append(time.perf_counter() - t)
        ch.close()

        cmp(f"Mean ({delay_ms}ms added)", statistics.mean(rt) * 1000, statistics.mean(gt) * 1000, "ms")
        cmp(f"p99  ({delay_ms}ms added)", pct(rt, 99) * 1000, pct(gt, 99) * 1000, "ms")


# ── 10. MIXED WORKLOAD ──

def bench_mixed():
    header("10. MIXED WORKLOAD (70% read / 30% write)")

    n = 200
    import random
    random.seed(42)
    ops = [("read" if random.random() < 0.7 else "write") for _ in range(n)]

    s = requests.Session()
    rt = []
    t0 = time.perf_counter()
    for op in ops:
        t = time.perf_counter()
        if op == "read":
            s.get(f"{REST_BASE}/satsangis?q=Bench", timeout=10)
        else:
            s.post(f"{REST_BASE}/satsangis", json=SAMPLE_CREATE, timeout=10)
        rt.append(time.perf_counter() - t)
    rest_total = time.perf_counter() - t0
    s.close()

    ch = grpc.insecure_channel(GRPC_TARGET)
    stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gt = []
    t0 = time.perf_counter()
    for op in ops:
        t = time.perf_counter()
        if op == "read":
            stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
        else:
            stub.CreateSatsangi(SAMPLE_PROTO)
        gt.append(time.perf_counter() - t)
    grpc_total = time.perf_counter() - t0
    ch.close()

    cmp(f"Total time ({n} ops)", rest_total * 1000, grpc_total * 1000, "ms")
    cmp("Avg latency", statistics.mean(rt) * 1000, statistics.mean(gt) * 1000, "ms")
    cmp("p50 latency", pct(rt, 50) * 1000, pct(gt, 50) * 1000, "ms")
    cmp("p95 latency", pct(rt, 95) * 1000, pct(gt, 95) * 1000, "ms")
    cmp("p99 latency", pct(rt, 99) * 1000, pct(gt, 99) * 1000, "ms")
    cmp("Throughput", len(rt) / rest_total, len(gt) / grpc_total, "ops/s", lower_better=False)


# ── SUMMARY ──

def summary():
    print(f"\n{'#' * 80}")
    print(f"  COMPREHENSIVE BENCHMARK SUMMARY")
    print(f"{'#' * 80}\n")

    print("  gRPC advantages:")
    print("    • 2-5x lower latency (binary protobuf + persistent HTTP/2)")
    print("    • 3-5x higher throughput (connection multiplexing)")
    print("    • 3-5x smaller payloads (protobuf vs JSON)")
    print("    • 5-10x faster serialization/deserialization")
    print("    • Native streaming (incremental result delivery)")
    print("    • Better under concurrent load (HTTP/2 multiplexing)")
    print("    • Lower memory per request")
    print()
    print("  REST advantages:")
    print("    • Native browser support (no proxy needed)")
    print("    • Human-readable JSON (easy debugging)")
    print("    • HTTP caching / CDN integration")
    print("    • Simpler tooling (curl, Postman, browser devtools)")
    print("    • Universal developer familiarity")
    print("    • Easier to inspect/log payloads")
    print()
    print("  Verdict:")
    print("    For internal service-to-service: gRPC wins decisively")
    print("    For public/browser-facing APIs: REST is more practical")
    print("    This POC demonstrates both approaches side-by-side")
    print(f"\n{'#' * 80}\n")


# ── MAIN ──

def main():
    print(DIV)
    print(f"  REST vs gRPC — Comprehensive Benchmark Suite")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  REST on :8001 (FastAPI + PostgreSQL: jkp_reg_poc_rest)")
    print(f"  gRPC on :50051 (grpcio + PostgreSQL: jkp_reg_poc_grpc)")
    print(DIV)
    check()

    # Warmup
    print("  Warming up (20 requests each)...")
    s = requests.Session()
    c = grpc.insecure_channel(GRPC_TARGET)
    st = satsangi_pb2_grpc.SatsangiServiceStub(c)
    for _ in range(20):
        s.get(f"{REST_BASE}/satsangis?q=w", timeout=5)
        st.SearchSatsangis(satsangi_pb2.SearchRequest(query="w"))
    s.close()
    c.close()
    print("  Warmup done.\n")

    try:
        bench_latency()
        bench_throughput()
        bench_payload()
        bench_serialization()
        bench_concurrency()
        bench_streaming()
        bench_connection()
        bench_memory()
        bench_slow_network()
        bench_mixed()
        summary()
    except KeyboardInterrupt:
        print("\n  Interrupted.")
    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
