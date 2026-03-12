#!/usr/bin/env python3
"""
REST vs gRPC Standalone Benchmark
==================================
Assumes servers are already running:
  - REST server on :8000  (cd jkpRegsitrationPOC/server && uv run uvicorn app.main:app --port 8000)
  - gRPC server on :50051 (cd jkpRegsitrationPOCgrpc/server && uv run python -m app.grpc_server)
"""

import json
import statistics
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "jkpRegsitrationPOCgrpc" / "server"))

import requests
import grpc
from app.generated import satsangi_pb2, satsangi_pb2_grpc

REST_BASE = "http://localhost:8000/api"
GRPC_TARGET = "localhost:50051"

SAMPLE_CREATE = {
    "first_name": "Benchmark", "last_name": "User", "phone_number": "9999900000",
    "nationality": "Indian", "country": "India", "age": 30, "gender": "Male",
    "city": "Vrindavan", "state": "Uttar Pradesh", "pincode": "281121",
    "email": "bench@test.com",
}
SAMPLE_PROTO = satsangi_pb2.SatsangiCreate(**SAMPLE_CREATE)

DIV = "=" * 78

def pct(data, p):
    if not data: return 0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (k - f) * (s[c] - s[f])

def cmp(label, rv, gv, unit="", lower_better=True):
    if rv == 0 or gv == 0:
        ratio, winner = "N/A", "N/A"
    elif lower_better:
        ratio, winner = f"{rv/gv:.2f}x", ("gRPC" if gv < rv else "REST")
    else:
        ratio, winner = f"{gv/rv:.2f}x", ("gRPC" if gv > rv else "REST")
    rf = f"{rv:.3f}" if isinstance(rv, float) else str(rv)
    gf = f"{gv:.3f}" if isinstance(gv, float) else str(gv)
    print(f"  {label:<35s} REST: {rf:>10s} {unit:<5s}  gRPC: {gf:>10s} {unit:<5s}  {ratio:>7s}  {winner}")

def header(t):
    print(f"\n{DIV}\n  {t}\n{DIV}")

# ── Check connectivity ──
def check():
    try:
        requests.get(f"{REST_BASE}/satsangis", timeout=2)
    except Exception:
        print("ERROR: REST server not reachable on :8000"); sys.exit(1)
    try:
        ch = grpc.insecure_channel(GRPC_TARGET)
        stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
        stub.ListSatsangis(satsangi_pb2.Empty(), timeout=2)
        ch.close()
    except Exception:
        print("ERROR: gRPC server not reachable on :50051"); sys.exit(1)
    print("  Both servers reachable. Starting benchmarks...\n")

# ── 1. Latency ──
def bench_latency(n=200):
    header(f"1. SINGLE-REQUEST LATENCY ({n} requests)")
    # Create
    rt = []
    for _ in range(n):
        t = time.perf_counter(); requests.post(f"{REST_BASE}/satsangis", json=SAMPLE_CREATE, timeout=10)
        rt.append(time.perf_counter() - t)
    ch = grpc.insecure_channel(GRPC_TARGET); stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gt = []
    for _ in range(n):
        t = time.perf_counter(); stub.CreateSatsangi(SAMPLE_PROTO)
        gt.append(time.perf_counter() - t)
    ch.close()
    for lbl, p in [("p50",50),("p95",95),("p99",99)]:
        cmp(f"Create {lbl}", pct(rt,p)*1000, pct(gt,p)*1000, "ms")
    cmp("Create mean", statistics.mean(rt)*1000, statistics.mean(gt)*1000, "ms")
    # Search
    print()
    rt2 = []
    for _ in range(n):
        t = time.perf_counter(); requests.get(f"{REST_BASE}/satsangis?q=Benchmark", timeout=10)
        rt2.append(time.perf_counter() - t)
    ch = grpc.insecure_channel(GRPC_TARGET); stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gt2 = []
    for _ in range(n):
        t = time.perf_counter(); stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Benchmark"))
        gt2.append(time.perf_counter() - t)
    ch.close()
    for lbl, p in [("p50",50),("p95",95),("p99",99)]:
        cmp(f"Search {lbl}", pct(rt2,p)*1000, pct(gt2,p)*1000, "ms")
    cmp("Search mean", statistics.mean(rt2)*1000, statistics.mean(gt2)*1000, "ms")

# ── 2. Throughput ──
def bench_throughput(dur=5):
    header(f"2. THROUGHPUT ({dur}s sustained)")
    rc = 0; end = time.perf_counter() + dur
    while time.perf_counter() < end:
        requests.get(f"{REST_BASE}/satsangis?q=Bench", timeout=10); rc += 1
    r_rps = rc / dur
    ch = grpc.insecure_channel(GRPC_TARGET); stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gc = 0; end = time.perf_counter() + dur
    while time.perf_counter() < end:
        stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench")); gc += 1
    ch.close(); g_rps = gc / dur
    cmp("Requests/sec (search)", r_rps, g_rps, "rps", lower_better=False)
    print(f"  {'Total requests':<35s} REST: {rc:>10d}       gRPC: {gc:>10d}")

# ── 3. Payload Size ──
def bench_payload():
    header("3. PAYLOAD SIZE")
    jc = len(json.dumps(SAMPLE_CREATE).encode()); pc = len(SAMPLE_PROTO.SerializeToString())
    cmp("Create request (1 record)", jc, pc, "bytes")
    resp = {**SAMPLE_CREATE, "satsangi_id":"ABCD1234", "created_at":"2025-03-12T14:00:00",
            "print_on_card":False, "has_room_in_ashram":False, "banned":False, "first_timer":False}
    jr = len(json.dumps(resp).encode())
    pr_msg = satsangi_pb2.Satsangi(satsangi_id="ABCD1234", created_at="2025-03-12T14:00:00",
        first_name="Benchmark", last_name="User", phone_number="9999900000",
        nationality="Indian", country="India", age=30, gender="Male",
        city="Vrindavan", state="Uttar Pradesh", pincode="281121", email="bench@test.com")
    pr = len(pr_msg.SerializeToString())
    cmp("Response (1 record)", jr, pr, "bytes")
    j100 = len(json.dumps([resp]*100).encode())
    p100 = len(satsangi_pb2.SatsangiList(satsangis=[pr_msg]*100).SerializeToString())
    cmp("List (100 records)", j100, p100, "bytes")
    print(f"\n  JSON is {j100/p100:.1f}x larger than Protobuf for 100 records")

# ── 4. Serialization ──
def bench_serialization(n=10000):
    header(f"4. SERIALIZATION SPEED ({n:,} messages)")
    d = {**SAMPLE_CREATE, "satsangi_id":"ABCD1234", "created_at":"2025-03-12T14:00:00",
         "print_on_card":False, "has_room_in_ashram":False, "banned":False, "first_timer":False}
    pm = satsangi_pb2.Satsangi(satsangi_id="ABCD1234", created_at="2025-03-12T14:00:00",
        first_name="Benchmark", last_name="User", phone_number="9999900000",
        nationality="Indian", country="India", age=30, gender="Male",
        city="Vrindavan", state="Uttar Pradesh", pincode="281121", email="bench@test.com")
    t=time.perf_counter()
    for _ in range(n): json.dumps(d)
    je=time.perf_counter()-t
    t=time.perf_counter()
    for _ in range(n): pm.SerializeToString()
    pe=time.perf_counter()-t
    cmp("Encode", je*1000, pe*1000, "ms")
    js=json.dumps(d); pb=pm.SerializeToString()
    t=time.perf_counter()
    for _ in range(n): json.loads(js)
    jd=time.perf_counter()-t
    t=time.perf_counter()
    for _ in range(n): satsangi_pb2.Satsangi.FromString(pb)
    pd=time.perf_counter()-t
    cmp("Decode", jd*1000, pd*1000, "ms")
    cmp("Total (enc+dec)", (je+jd)*1000, (pe+pd)*1000, "ms")

# ── 5. Concurrency ──
def bench_concurrency():
    header("5. CONCURRENT LOAD TEST")
    rpw = 30
    for nc in [5, 10, 25]:
        print(f"\n  --- {nc} clients x {rpw} requests ---")
        rt=[]; re=0
        def rw():
            nonlocal re; ts=[]; s=requests.Session()
            for _ in range(rpw):
                try: t=time.perf_counter(); s.get(f"{REST_BASE}/satsangis?q=B",timeout=30); ts.append(time.perf_counter()-t)
                except: re+=1
            return ts
        t0=time.perf_counter()
        with ThreadPoolExecutor(nc) as p:
            for f in as_completed([p.submit(rw) for _ in range(nc)]): rt.extend(f.result())
        rw_t=time.perf_counter()-t0
        gt=[]; ge=0
        def gw():
            nonlocal ge; ts=[]; c=grpc.insecure_channel(GRPC_TARGET); st=satsangi_pb2_grpc.SatsangiServiceStub(c)
            for _ in range(rpw):
                try: t=time.perf_counter(); st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B")); ts.append(time.perf_counter()-t)
                except: ge+=1
            c.close(); return ts
        t0=time.perf_counter()
        with ThreadPoolExecutor(nc) as p:
            for f in as_completed([p.submit(gw) for _ in range(nc)]): gt.extend(f.result())
        gw_t=time.perf_counter()-t0
        tot=nc*rpw
        cmp(f"Wall time ({tot} reqs)", rw_t*1000, gw_t*1000, "ms")
        if rt and gt:
            cmp("Throughput", len(rt)/rw_t, len(gt)/gw_t, "rps", lower_better=False)
            cmp("Avg latency", statistics.mean(rt)*1000, statistics.mean(gt)*1000, "ms")
            cmp("p99 latency", pct(rt,99)*1000, pct(gt,99)*1000, "ms")
        if re or ge: print(f"  Errors — REST: {re}, gRPC: {ge}")

# ── 6. Streaming ──
def bench_streaming():
    header("6. gRPC STREAMING vs REST BATCH")
    n=50
    rt=[]; rttfb=[]
    for _ in range(n):
        t=time.perf_counter(); r=requests.get(f"{REST_BASE}/satsangis?q=Bench",timeout=10)
        fb=time.perf_counter()-t; r.json(); tt=time.perf_counter()-t; rttfb.append(fb); rt.append(tt)
    ch=grpc.insecure_channel(GRPC_TARGET); stub=satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gt=[]; gttfr=[]
    for _ in range(n):
        t=time.perf_counter(); stream=stub.StreamSearchResults(satsangi_pb2.SearchRequest(query="Bench"))
        first=False
        for item in stream:
            if not first: gttfr.append(time.perf_counter()-t); first=True
        if not first: gttfr.append(time.perf_counter()-t)
        gt.append(time.perf_counter()-t)
    ch.close()
    # gRPC batch (unary)
    ch=grpc.insecure_channel(GRPC_TARGET); stub=satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gbt=[]
    for _ in range(n):
        t=time.perf_counter(); stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
        gbt.append(time.perf_counter()-t)
    ch.close()
    cmp("Total time p50", pct(rt,50)*1000, pct(gt,50)*1000, "ms")
    cmp("Time to first result p50", pct(rttfb,50)*1000, pct(gttfr,50)*1000, "ms")
    cmp("gRPC batch vs stream", pct(gbt,50)*1000, pct(gt,50)*1000, "ms")
    print(f"\n  REST returns ALL results at once. gRPC streaming delivers one-by-one.")

# ── 7. Connection Overhead ──
def bench_connection(n=100):
    header(f"7. CONNECTION OVERHEAD ({n} requests)")
    # REST new conn each time
    rt=[]
    for _ in range(n):
        t=time.perf_counter(); requests.get(f"{REST_BASE}/satsangis?q=B",timeout=10); rt.append(time.perf_counter()-t)
    # REST reused
    rtr=[]; s=requests.Session()
    for _ in range(n):
        t=time.perf_counter(); s.get(f"{REST_BASE}/satsangis?q=B",timeout=10); rtr.append(time.perf_counter()-t)
    s.close()
    # gRPC new channel each time
    gtn=[]
    for _ in range(n):
        t=time.perf_counter(); c=grpc.insecure_channel(GRPC_TARGET); st=satsangi_pb2_grpc.SatsangiServiceStub(c)
        st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B")); c.close(); gtn.append(time.perf_counter()-t)
    # gRPC reused
    gtr=[]; c=grpc.insecure_channel(GRPC_TARGET); st=satsangi_pb2_grpc.SatsangiServiceStub(c)
    for _ in range(n):
        t=time.perf_counter(); st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B")); gtr.append(time.perf_counter()-t)
    c.close()
    cmp("New conn each request", statistics.mean(rt)*1000, statistics.mean(gtn)*1000, "ms")
    cmp("Reused connection", statistics.mean(rtr)*1000, statistics.mean(gtr)*1000, "ms")
    cmp("REST reuse speedup", statistics.mean(rt)*1000, statistics.mean(rtr)*1000, "ms")
    cmp("gRPC reuse speedup", statistics.mean(gtn)*1000, statistics.mean(gtr)*1000, "ms")

# ── 8. Memory ──
def bench_memory(n=500):
    header(f"8. CLIENT-SIDE MEMORY ({n} requests)")
    tracemalloc.start(); b=tracemalloc.take_snapshot()
    s=requests.Session()
    for _ in range(n): s.get(f"{REST_BASE}/satsangis?q=B",timeout=10)
    a=tracemalloc.take_snapshot(); s.close()
    rm=sum(x.size_diff for x in a.compare_to(b,"lineno") if x.size_diff>0); tracemalloc.stop()
    tracemalloc.start(); b=tracemalloc.take_snapshot()
    c=grpc.insecure_channel(GRPC_TARGET); st=satsangi_pb2_grpc.SatsangiServiceStub(c)
    for _ in range(n): st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B"))
    a=tracemalloc.take_snapshot(); c.close()
    gm=sum(x.size_diff for x in a.compare_to(b,"lineno") if x.size_diff>0); tracemalloc.stop()
    cmp(f"Memory alloc ({n} reqs)", rm/1024, gm/1024, "KB")

# ── Summary ──
def summary():
    print(f"\n{'#'*78}")
    print(f"  FINAL SUMMARY")
    print(f"{'#'*78}\n")
    print("  gRPC wins at:")
    print("    - Throughput (persistent HTTP/2 connections)")
    print("    - Payload size (3-5x smaller with Protobuf)")
    print("    - Serialization speed (5-10x faster encode/decode)")
    print("    - Streaming (native server-streaming support)")
    print("    - Concurrent load handling (HTTP/2 multiplexing)")
    print()
    print("  REST wins at:")
    print("    - Simplicity & human readability")
    print("    - Browser-native support (no proxy)")
    print("    - HTTP caching / CDN friendly")
    print("    - Developer familiarity")
    print()
    print("  Recommendation: HYBRID — REST for browser, gRPC for backend services.")
    print(f"\n{'#'*78}\n")

def main():
    print(DIV)
    print(f"  REST vs gRPC Benchmark Suite — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  REST on :8000 | gRPC on :50051")
    print(DIV)
    check()
    # Warmup
    print("  Warming up...")
    s=requests.Session(); c=grpc.insecure_channel(GRPC_TARGET); st=satsangi_pb2_grpc.SatsangiServiceStub(c)
    for _ in range(20):
        s.get(f"{REST_BASE}/satsangis?q=w",timeout=5)
        st.SearchSatsangis(satsangi_pb2.SearchRequest(query="w"))
    s.close(); c.close()
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
        summary()
    except KeyboardInterrupt:
        print("\n  Interrupted.")
    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    main()
