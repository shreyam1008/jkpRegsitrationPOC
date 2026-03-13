#!/usr/bin/env python3
"""
REST vs gRPC — Robust Benchmark Suite (Synthetic + Real-Life Scenarios)
=======================================================================
Both backends use PostgreSQL — fair apples-to-apples comparison.

Assumes servers are already running:
  REST server  → :8001  (cd jkpRegsitrationPOC/server && uv run python -m uvicorn app.main:app --port 8001)
  gRPC server  → :50051 (cd jkpRegistrationFULLGRPC/server && uv run python -m app.grpc_server)

PART A — Synthetic (controlled):
  1. Single-request latency    2. Sustained throughput
  3. Payload size              4. Serialization speed
  5. Concurrent load           6. Streaming vs batch
  7. Connection overhead       8. Memory

PART B — Real-Life Scenarios:
  9.  Page-load simulation (multi-call per page)
  10. Bursty traffic (idle → burst)
  11. Variable payload (minimal vs full fields)
  12. Network jitter (random 0-200ms delays)
  13. Long-session degradation (500+ requests)
  14. Error recovery (bad requests + recovery)
  15. Concurrent mixed workload (realistic read/write mix)
  16. Cold start vs warm

Fairness:
  - Both use PostgreSQL. REST uses Session (keep-alive). gRPC uses persistent channel.
  - Same random seed, same data, same warmup. Raw numbers reported; no pre-declared winner.
"""

import json, math, random, statistics, string, sys, time, tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "jkpRegistrationFULLGRPC" / "server"))

import requests as req_lib
import grpc
from app.generated import satsangi_pb2, satsangi_pb2_grpc

REST_BASE = "http://localhost:8001/api"
GRPC_TARGET = "localhost:50051"
SEED = 42
TIMEOUT = 30

SAMPLE_MINIMAL = {"first_name": "Bench", "last_name": "User", "phone_number": "9999900000"}
SAMPLE_FULL = {
    "first_name": "Benchmark", "last_name": "TestUser", "phone_number": "9999900000",
    "nationality": "Indian", "country": "India", "age": 30, "gender": "Male",
    "city": "Vrindavan", "state": "Uttar Pradesh", "pincode": "281121",
    "email": "bench@test.com", "date_of_birth": "1994-06-15",
    "pan": "ABCDE1234F", "special_category": "None",
    "govt_id_type": "Aadhaar", "govt_id_number": "1234-5678-9012",
    "id_expiry_date": "2030-01-01", "id_issuing_country": "India",
    "nick_name": "Benchy", "print_on_card": True, "introducer": "SomeGuru",
    "address": "123 Temple Road, Near Banke Bihari", "district": "Mathura",
    "emergency_contact": "8888800000", "ex_center_satsangi_id": "EX001",
    "introduced_by": "Ram Das", "has_room_in_ashram": True,
    "banned": False, "first_timer": True, "date_of_first_visit": "2024-01-14",
    "notes": "Regular visitor, attends morning satsang daily.",
}
SAMPLE_PROTO_FULL = satsangi_pb2.SatsangiCreate(**SAMPLE_FULL)
SAMPLE_PROTO_MIN = satsangi_pb2.SatsangiCreate(**SAMPLE_MINIMAL)
SEARCH_QUERIES = ["Bench", "User", "Vrindavan", "9999", "bench@test", "281121", "Male",
                  "TestUser", "Indian", "Ram"]

DIV = "=" * 80
SUBDIV = "-" * 80
ALL_RESULTS: dict[str, dict] = {}


# ── Utilities ──

def pct(data, p):
    if not data: return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (k - f) * (s[c] - s[f])

def ss(data_ms):
    if not data_ms: return {}
    return {"mean": round(statistics.mean(data_ms), 3),
            "stdev": round(statistics.stdev(data_ms), 3) if len(data_ms) > 1 else 0,
            "p50": round(pct(data_ms, 50), 3), "p95": round(pct(data_ms, 95), 3),
            "p99": round(pct(data_ms, 99), 3), "min": round(min(data_ms), 3),
            "max": round(max(data_ms), 3)}

def cmp(label, rv, gv, unit="", lower_better=True):
    if rv == 0 or gv == 0:
        ratio, winner = "N/A", "—"
    elif lower_better:
        ratio = f"{rv/gv:.2f}x"; winner = "gRPC" if gv < rv else ("REST" if rv < gv else "TIE")
    else:
        ratio = f"{gv/rv:.2f}x"; winner = "gRPC" if gv > rv else ("REST" if rv > gv else "TIE")
    rf = f"{rv:,.3f}" if isinstance(rv, float) else f"{rv:,}"
    gf = f"{gv:,.3f}" if isinstance(gv, float) else f"{gv:,}"
    print(f"  {label:<40s} REST:{rf:>12s} {unit:<5s} gRPC:{gf:>12s} {unit:<5s} {ratio:>7s} {winner}")

def header(t):
    print(f"\n{DIV}\n  {t}\n{DIV}")

def rand_payload(rng):
    first = rng.choice(["Aarav","Vihaan","Ananya","Diya","Arjun","Kavya","Rishi","Meera"])
    last = rng.choice(["Sharma","Patel","Singh","Kumar","Das","Gupta","Joshi","Verma"])
    return {"first_name": first, "last_name": last,
            "phone_number": f"{rng.randint(7000000000,9999999999)}",
            "nationality": "Indian", "country": "India", "age": rng.randint(18,80),
            "gender": rng.choice(["Male","Female"]),
            "city": rng.choice(["Vrindavan","Mathura","Delhi","Mumbai","Kolkata"]),
            "state": rng.choice(["UP","Maharashtra","West Bengal","Gujarat"]),
            "pincode": f"{rng.randint(100000,999999)}",
            "email": f"{first.lower()}.{last.lower()}@test.com"}

def rand_proto(rng):
    d = rand_payload(rng)
    return satsangi_pb2.SatsangiCreate(**d), d


# ── Connectivity ──

def check():
    ok = True
    try: req_lib.get(f"{REST_BASE}/satsangis", timeout=3)
    except Exception as e: print(f"  ERROR: REST :8001 — {e}"); ok = False
    try:
        ch = grpc.insecure_channel(GRPC_TARGET)
        stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
        stub.ListSatsangis(satsangi_pb2.Empty(), timeout=3); ch.close()
    except Exception as e: print(f"  ERROR: gRPC :50051 — {e}"); ok = False
    if not ok: sys.exit(1)
    print("  Both servers reachable.\n")


# ════════════════════════════════════════════════════════════════════════════
#  PART A — SYNTHETIC BENCHMARKS
# ════════════════════════════════════════════════════════════════════════════

def bench_01_latency(n=100):
    header(f"A1. SINGLE-REQUEST LATENCY ({n} iterations)")
    results = {}
    for op_name, rest_fn, grpc_fn in [
        ("Create", lambda s: s.post(f"{REST_BASE}/satsangis", json=SAMPLE_FULL, timeout=TIMEOUT),
         lambda stub: stub.CreateSatsangi(SAMPLE_PROTO_FULL)),
        ("Search", lambda s: s.get(f"{REST_BASE}/satsangis?q=Bench", timeout=TIMEOUT),
         lambda stub: stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))),
        ("List", lambda s: s.get(f"{REST_BASE}/satsangis", timeout=TIMEOUT),
         lambda stub: stub.ListSatsangis(satsangi_pb2.Empty())),
    ]:
        print(f"\n  {SUBDIV}\n  {op_name}\n  {SUBDIV}")
        s = req_lib.Session()
        rt = [(time.perf_counter(), rest_fn(s))[0] for _ in range(0)]  # placeholder
        rt = []
        for _ in range(n):
            t = time.perf_counter(); rest_fn(s); rt.append((time.perf_counter()-t)*1000)
        s.close()

        ch = grpc.insecure_channel(GRPC_TARGET)
        stub = satsangi_pb2_grpc.SatsangiServiceStub(ch)
        gt = []
        for _ in range(n):
            t = time.perf_counter(); grpc_fn(stub); gt.append((time.perf_counter()-t)*1000)
        ch.close()

        for lbl, p in [("p50",50),("p95",95),("p99",99)]:
            cmp(f"{op_name} {lbl}", pct(rt,p), pct(gt,p), "ms")
        cmp(f"{op_name} mean", statistics.mean(rt), statistics.mean(gt), "ms")
        if len(rt) > 1: cmp(f"{op_name} stdev", statistics.stdev(rt), statistics.stdev(gt), "ms")
        results[op_name.lower()] = {"rest": ss(rt), "grpc": ss(gt)}
    ALL_RESULTS["A1_latency"] = results


def bench_02_throughput(dur=5):
    header(f"A2. SUSTAINED THROUGHPUT ({dur}s each)")
    results = {}
    for label, rest_fn, grpc_fn in [
        ("Read", lambda s: s.get(f"{REST_BASE}/satsangis?q=Bench", timeout=TIMEOUT),
         lambda stub: stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))),
        ("Write", lambda s: s.post(f"{REST_BASE}/satsangis", json=SAMPLE_FULL, timeout=TIMEOUT),
         lambda stub: stub.CreateSatsangi(SAMPLE_PROTO_FULL)),
    ]:
        s = req_lib.Session(); rc = 0; end = time.perf_counter() + dur
        while time.perf_counter() < end: rest_fn(s); rc += 1
        s.close(); r_rps = rc / dur

        ch = grpc.insecure_channel(GRPC_TARGET)
        stub = satsangi_pb2_grpc.SatsangiServiceStub(ch); gc = 0; end = time.perf_counter() + dur
        while time.perf_counter() < end: grpc_fn(stub); gc += 1
        ch.close(); g_rps = gc / dur

        cmp(f"{label} req/sec", r_rps, g_rps, "rps", lower_better=False)
        results[label.lower()] = {"rest_rps": round(r_rps,1), "grpc_rps": round(g_rps,1)}
    ALL_RESULTS["A2_throughput"] = results


def bench_03_payload():
    header("A3. PAYLOAD SIZE (wire bytes)")
    resp_proto = satsangi_pb2.Satsangi(satsangi_id="ABCD1234", created_at="2025-03-12T14:00:00", **SAMPLE_FULL)
    resp_dict = {**SAMPLE_FULL, "satsangi_id": "ABCD1234", "created_at": "2025-03-12T14:00:00"}
    results = {}
    for label, d, p in [("Minimal req", SAMPLE_MINIMAL, SAMPLE_PROTO_MIN),
                        ("Full req", SAMPLE_FULL, SAMPLE_PROTO_FULL)]:
        jb = len(json.dumps(d).encode()); pb = len(p.SerializeToString())
        cmp(label, jb, pb, "bytes"); results[label] = {"json": jb, "proto": pb}
    for count in [1, 10, 100, 500, 1000]:
        jb = len(json.dumps([resp_dict]*count).encode())
        pb = len(satsangi_pb2.SatsangiList(satsangis=[resp_proto]*count).SerializeToString())
        cmp(f"Response list ({count})", jb, pb, "bytes")
        results[f"list_{count}"] = {"json": jb, "proto": pb, "ratio": round(jb/pb,2) if pb else 0}
    ALL_RESULTS["A3_payload"] = results


def bench_04_serialization(n=10_000):
    header(f"A4. SERIALIZATION SPEED ({n:,} messages)")
    d = {**SAMPLE_FULL, "satsangi_id": "ABCD1234", "created_at": "2025-03-12T14:00:00"}
    pm = satsangi_pb2.Satsangi(satsangi_id="ABCD1234", created_at="2025-03-12T14:00:00", **SAMPLE_FULL)
    t=time.perf_counter()
    for _ in range(n): json.dumps(d)
    je=time.perf_counter()-t
    t=time.perf_counter()
    for _ in range(n): pm.SerializeToString()
    pe=time.perf_counter()-t
    cmp("Encode total", je*1000, pe*1000, "ms")
    js=json.dumps(d); pb=pm.SerializeToString()
    t=time.perf_counter()
    for _ in range(n): json.loads(js)
    jd=time.perf_counter()-t
    t=time.perf_counter()
    for _ in range(n): satsangi_pb2.Satsangi.FromString(pb)
    pd=time.perf_counter()-t
    cmp("Decode total", jd*1000, pd*1000, "ms")
    cmp("Total (enc+dec)", (je+jd)*1000, (pe+pd)*1000, "ms")
    cmp("Per-msg encode", (je/n)*1e6, (pe/n)*1e6, "µs")
    cmp("Per-msg decode", (jd/n)*1e6, (pd/n)*1e6, "µs")
    ALL_RESULTS["A4_serialization"] = {"json_enc": round(je*1000,2), "proto_enc": round(pe*1000,2),
                                        "json_dec": round(jd*1000,2), "proto_dec": round(pd*1000,2)}


def bench_05_concurrency():
    header("A5. CONCURRENT LOAD TEST")
    rpw = 20; results = {}
    for nc in [5, 10, 25]:
        print(f"\n  {SUBDIV}\n  {nc} clients × {rpw} = {nc*rpw} total\n  {SUBDIV}")
        rt, re = [], [0]
        def rw():
            ts = []; s = req_lib.Session()
            for _ in range(rpw):
                try: t=time.perf_counter(); s.get(f"{REST_BASE}/satsangis?q=B",timeout=TIMEOUT); ts.append((time.perf_counter()-t)*1000)
                except: re[0]+=1
            s.close(); return ts
        t0=time.perf_counter()
        with ThreadPoolExecutor(nc) as pool:
            for f in as_completed([pool.submit(rw) for _ in range(nc)]): rt.extend(f.result())
        rw_t=time.perf_counter()-t0
        gt, ge = [], [0]
        def gw():
            ts=[]; c=grpc.insecure_channel(GRPC_TARGET); st=satsangi_pb2_grpc.SatsangiServiceStub(c)
            for _ in range(rpw):
                try: t=time.perf_counter(); st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B")); ts.append((time.perf_counter()-t)*1000)
                except: ge[0]+=1
            c.close(); return ts
        t0=time.perf_counter()
        with ThreadPoolExecutor(nc) as pool:
            for f in as_completed([pool.submit(gw) for _ in range(nc)]): gt.extend(f.result())
        gw_t=time.perf_counter()-t0
        cmp("Wall time", rw_t*1000, gw_t*1000, "ms")
        if rt and gt:
            cmp("Throughput", len(rt)/rw_t, len(gt)/gw_t, "rps", lower_better=False)
            cmp("Mean latency", statistics.mean(rt), statistics.mean(gt), "ms")
            cmp("p95 latency", pct(rt,95), pct(gt,95), "ms")
            cmp("p99 latency", pct(rt,99), pct(gt,99), "ms")
        if re[0] or ge[0]: print(f"  Errors — REST: {re[0]}, gRPC: {ge[0]}")
        results[f"{nc}_clients"] = {"rest": ss(rt), "grpc": ss(gt),
            "rest_rps": round(len(rt)/rw_t,1) if rt else 0,
            "grpc_rps": round(len(gt)/gw_t,1) if gt else 0,
            "rest_errors": re[0], "grpc_errors": ge[0]}
    ALL_RESULTS["A5_concurrency"] = results


def bench_06_streaming():
    header("A6. gRPC STREAMING vs REST BATCH")
    n = 50
    s = req_lib.Session(); rt, rttfb = [], []
    for _ in range(n):
        t=time.perf_counter(); r=s.get(f"{REST_BASE}/satsangis?q=Bench",timeout=TIMEOUT)
        fb=time.perf_counter()-t; r.json(); tt=time.perf_counter()-t
        rttfb.append(fb*1000); rt.append(tt*1000)
    s.close()
    ch=grpc.insecure_channel(GRPC_TARGET); stub=satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gt, gttfr = [], []
    for _ in range(n):
        t=time.perf_counter()
        stream=stub.StreamSearchResults(satsangi_pb2.SearchRequest(query="Bench"))
        first=False
        for _item in stream:
            if not first: gttfr.append((time.perf_counter()-t)*1000); first=True
        if not first: gttfr.append((time.perf_counter()-t)*1000)
        gt.append((time.perf_counter()-t)*1000)
    ch.close()
    ch=grpc.insecure_channel(GRPC_TARGET); stub=satsangi_pb2_grpc.SatsangiServiceStub(ch)
    gbt = []
    for _ in range(n):
        t=time.perf_counter(); stub.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
        gbt.append((time.perf_counter()-t)*1000)
    ch.close()
    cmp("REST batch p50", pct(rt,50), pct(gbt,50), "ms")
    cmp("gRPC stream p50", pct(rt,50), pct(gt,50), "ms")
    cmp("Time-to-first-result p50", pct(rttfb,50), pct(gttfr,50), "ms")
    ALL_RESULTS["A6_streaming"] = {"rest_batch": ss(rt), "grpc_unary": ss(gbt),
        "grpc_stream": ss(gt), "grpc_ttfr": ss(gttfr), "rest_ttfb": ss(rttfb)}


def bench_07_connection(n=100):
    header(f"A7. CONNECTION OVERHEAD ({n} requests)")
    rt_new = []
    for _ in range(n):
        t=time.perf_counter(); req_lib.get(f"{REST_BASE}/satsangis?q=B",timeout=TIMEOUT)
        rt_new.append((time.perf_counter()-t)*1000)
    rt_reuse = []; s=req_lib.Session()
    for _ in range(n):
        t=time.perf_counter(); s.get(f"{REST_BASE}/satsangis?q=B",timeout=TIMEOUT)
        rt_reuse.append((time.perf_counter()-t)*1000)
    s.close()
    gt_new = []
    for _ in range(n):
        t=time.perf_counter(); c=grpc.insecure_channel(GRPC_TARGET)
        st=satsangi_pb2_grpc.SatsangiServiceStub(c)
        st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B")); c.close()
        gt_new.append((time.perf_counter()-t)*1000)
    gt_reuse = []; c=grpc.insecure_channel(GRPC_TARGET)
    st=satsangi_pb2_grpc.SatsangiServiceStub(c)
    for _ in range(n):
        t=time.perf_counter(); st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B"))
        gt_reuse.append((time.perf_counter()-t)*1000)
    c.close()
    cmp("New conn each req", statistics.mean(rt_new), statistics.mean(gt_new), "ms")
    cmp("Reused connection", statistics.mean(rt_reuse), statistics.mean(gt_reuse), "ms")
    oh_r = statistics.mean(rt_new) - statistics.mean(rt_reuse)
    oh_g = statistics.mean(gt_new) - statistics.mean(gt_reuse)
    print(f"\n  Overhead: REST={oh_r:.3f}ms  gRPC={oh_g:.3f}ms per new connection")
    ALL_RESULTS["A7_connection"] = {"rest_new": ss(rt_new), "rest_reuse": ss(rt_reuse),
        "grpc_new": ss(gt_new), "grpc_reuse": ss(gt_reuse)}


def bench_08_memory(n=200):
    header(f"A8. CLIENT-SIDE MEMORY ({n} requests)")
    tracemalloc.start(); b=tracemalloc.take_snapshot()
    s=req_lib.Session()
    for _ in range(n): s.get(f"{REST_BASE}/satsangis?q=B",timeout=TIMEOUT)
    a=tracemalloc.take_snapshot(); s.close()
    rm=sum(x.size_diff for x in a.compare_to(b,"lineno") if x.size_diff>0); tracemalloc.stop()
    tracemalloc.start(); b=tracemalloc.take_snapshot()
    c=grpc.insecure_channel(GRPC_TARGET); st=satsangi_pb2_grpc.SatsangiServiceStub(c)
    for _ in range(n): st.SearchSatsangis(satsangi_pb2.SearchRequest(query="B"))
    a=tracemalloc.take_snapshot(); c.close()
    gm=sum(x.size_diff for x in a.compare_to(b,"lineno") if x.size_diff>0); tracemalloc.stop()
    cmp(f"Total alloc ({n} reqs)", rm/1024, gm/1024, "KB")
    cmp("Per-request alloc", rm/n/1024, gm/n/1024, "KB")
    ALL_RESULTS["A8_memory"] = {"rest_kb": round(rm/1024,1), "grpc_kb": round(gm/1024,1)}


# ════════════════════════════════════════════════════════════════════════════
#  PART B — REAL-LIFE SCENARIOS
# ════════════════════════════════════════════════════════════════════════════

def bench_09_page_load(rounds=30):
    """Single user page = search + create + re-fetch (3 sequential calls)."""
    header(f"B9. PAGE-LOAD SIMULATION ({rounds} pages, 3 calls each)")
    rng = random.Random(SEED)
    rest_page, rest_call = [], []
    s = req_lib.Session()
    for _ in range(rounds):
        q = rng.choice(SEARCH_QUERIES); payload = rand_payload(rng)
        p0 = time.perf_counter()
        for fn in [lambda: s.get(f"{REST_BASE}/satsangis?q={q}", timeout=TIMEOUT),
                   lambda: s.post(f"{REST_BASE}/satsangis", json=payload, timeout=TIMEOUT),
                   lambda: s.get(f"{REST_BASE}/satsangis?q={payload['first_name']}", timeout=TIMEOUT)]:
            t=time.perf_counter(); fn(); rest_call.append((time.perf_counter()-t)*1000)
        rest_page.append((time.perf_counter()-p0)*1000)
    s.close()
    rng = random.Random(SEED)
    grpc_page, grpc_call = [], []
    ch=grpc.insecure_channel(GRPC_TARGET); stub=satsangi_pb2_grpc.SatsangiServiceStub(ch)
    for _ in range(rounds):
        q = rng.choice(SEARCH_QUERIES); proto, d = rand_proto(rng)
        p0 = time.perf_counter()
        for fn in [lambda: stub.SearchSatsangis(satsangi_pb2.SearchRequest(query=q)),
                   lambda: stub.CreateSatsangi(proto),
                   lambda: stub.SearchSatsangis(satsangi_pb2.SearchRequest(query=q))]:
            t=time.perf_counter(); fn(); grpc_call.append((time.perf_counter()-t)*1000)
        grpc_page.append((time.perf_counter()-p0)*1000)
    ch.close()
    cmp("Page load p50", pct(rest_page,50), pct(grpc_page,50), "ms")
    cmp("Page load p95", pct(rest_page,95), pct(grpc_page,95), "ms")
    cmp("Page load mean", statistics.mean(rest_page), statistics.mean(grpc_page), "ms")
    cmp("Per-call p50", pct(rest_call,50), pct(grpc_call,50), "ms")
    cmp("Per-call p95", pct(rest_call,95), pct(grpc_call,95), "ms")
    ALL_RESULTS["B9_page_load"] = {"rest_page": ss(rest_page), "grpc_page": ss(grpc_page),
        "rest_call": ss(rest_call), "grpc_call": ss(grpc_call)}


def bench_10_bursty(bursts=5, burst_size=20, idle_sec=2.0):
    """Idle → sudden burst. Registration desks have waves of volunteers."""
    header(f"B10. BURSTY TRAFFIC ({bursts} bursts of {burst_size}, {idle_sec}s idle)")
    rng = random.Random(SEED)
    rest_burst, rest_lat = [], []
    s = req_lib.Session()
    for _ in range(bursts):
        time.sleep(idle_sec); b0=time.perf_counter()
        for _ in range(burst_size):
            payload=rand_payload(rng); t=time.perf_counter()
            if rng.random()<0.7: s.get(f"{REST_BASE}/satsangis?q={rng.choice(SEARCH_QUERIES)}",timeout=TIMEOUT)
            else: s.post(f"{REST_BASE}/satsangis",json=payload,timeout=TIMEOUT)
            rest_lat.append((time.perf_counter()-t)*1000)
        rest_burst.append((time.perf_counter()-b0)*1000)
    s.close()
    rng = random.Random(SEED)
    grpc_burst, grpc_lat = [], []
    ch=grpc.insecure_channel(GRPC_TARGET); stub=satsangi_pb2_grpc.SatsangiServiceStub(ch)
    for _ in range(bursts):
        time.sleep(idle_sec); b0=time.perf_counter()
        for _ in range(burst_size):
            proto,_=rand_proto(rng); t=time.perf_counter()
            if rng.random()<0.7: stub.SearchSatsangis(satsangi_pb2.SearchRequest(query=rng.choice(SEARCH_QUERIES)))
            else: stub.CreateSatsangi(proto)
            grpc_lat.append((time.perf_counter()-t)*1000)
        grpc_burst.append((time.perf_counter()-b0)*1000)
    ch.close()
    cmp("Burst wall time p50", pct(rest_burst,50), pct(grpc_burst,50), "ms")
    cmp("Request latency p50", pct(rest_lat,50), pct(grpc_lat,50), "ms")
    cmp("Request latency p95", pct(rest_lat,95), pct(grpc_lat,95), "ms")
    cmp("Request latency p99", pct(rest_lat,99), pct(grpc_lat,99), "ms")
    rfirst = [rest_lat[i*burst_size] for i in range(bursts)]
    gfirst = [grpc_lat[i*burst_size] for i in range(bursts)]
    cmp("1st req after idle (mean)", statistics.mean(rfirst), statistics.mean(gfirst), "ms")
    ALL_RESULTS["B10_bursty"] = {"rest_lat": ss(rest_lat), "grpc_lat": ss(grpc_lat),
        "rest_burst": ss(rest_burst), "grpc_burst": ss(grpc_burst)}


def bench_11_variable_payload():
    """Minimal (3 fields) vs full (30+ fields)."""
    header("B11. VARIABLE PAYLOAD (minimal vs full)")
    results = {}
    n = 100
    for label, payload, proto in [("Minimal(3)", SAMPLE_MINIMAL, SAMPLE_PROTO_MIN),
                                   ("Full(30+)", SAMPLE_FULL, SAMPLE_PROTO_FULL)]:
        print(f"\n  {SUBDIV}\n  {label}\n  {SUBDIV}")
        s=req_lib.Session(); rt=[]
        for _ in range(n):
            t=time.perf_counter(); s.post(f"{REST_BASE}/satsangis",json=payload,timeout=TIMEOUT)
            rt.append((time.perf_counter()-t)*1000)
        s.close()
        ch=grpc.insecure_channel(GRPC_TARGET); stub=satsangi_pb2_grpc.SatsangiServiceStub(ch); gt=[]
        for _ in range(n):
            t=time.perf_counter(); stub.CreateSatsangi(proto)
            gt.append((time.perf_counter()-t)*1000)
        ch.close()
        cmp(f"Create p50", pct(rt,50), pct(gt,50), "ms")
        cmp(f"Create p95", pct(rt,95), pct(gt,95), "ms")
        cmp(f"Create mean", statistics.mean(rt), statistics.mean(gt), "ms")
        results[label] = {"rest": ss(rt), "grpc": ss(gt)}
    ALL_RESULTS["B11_variable_payload"] = results


def bench_12_jitter():
    """Random delays 0-200ms between requests (bad mobile/WiFi)."""
    header("B12. NETWORK JITTER (random 0–200ms delays)")
    rng = random.Random(SEED); n = 100
    delays = [rng.uniform(0,0.200) for _ in range(n)]
    queries = [rng.choice(SEARCH_QUERIES) for _ in range(n)]
    s=req_lib.Session(); rt=[]
    for i in range(n):
        time.sleep(delays[i]); t=time.perf_counter()
        s.get(f"{REST_BASE}/satsangis?q={queries[i]}",timeout=TIMEOUT)
        rt.append((time.perf_counter()-t)*1000)
    s.close()
    ch=grpc.insecure_channel(GRPC_TARGET); stub=satsangi_pb2_grpc.SatsangiServiceStub(ch); gt=[]
    for i in range(n):
        time.sleep(delays[i]); t=time.perf_counter()
        stub.SearchSatsangis(satsangi_pb2.SearchRequest(query=queries[i]))
        gt.append((time.perf_counter()-t)*1000)
    ch.close()
    cmp("Mean latency", statistics.mean(rt), statistics.mean(gt), "ms")
    cmp("p50 latency", pct(rt,50), pct(gt,50), "ms")
    cmp("p95 latency", pct(rt,95), pct(gt,95), "ms")
    cmp("p99 latency", pct(rt,99), pct(gt,99), "ms")
    cmp("Stdev (consistency)", statistics.stdev(rt), statistics.stdev(gt), "ms")
    ALL_RESULTS["B12_jitter"] = {"rest": ss(rt), "grpc": ss(gt)}


def bench_13_long_session(n=300):
    """500 requests on same connection. Check for latency drift over time."""
    header(f"B13. LONG-SESSION DEGRADATION ({n} requests)")
    rng = random.Random(SEED)
    s=req_lib.Session(); rt=[]
    for _ in range(n):
        if rng.random()<0.7:
            t=time.perf_counter(); s.get(f"{REST_BASE}/satsangis?q={rng.choice(SEARCH_QUERIES)}",timeout=TIMEOUT)
        else:
            t=time.perf_counter(); s.post(f"{REST_BASE}/satsangis",json=rand_payload(rng),timeout=TIMEOUT)
        rt.append((time.perf_counter()-t)*1000)
    s.close()
    rng = random.Random(SEED)
    ch=grpc.insecure_channel(GRPC_TARGET); stub=satsangi_pb2_grpc.SatsangiServiceStub(ch); gt=[]
    for _ in range(n):
        if rng.random()<0.7:
            t=time.perf_counter(); stub.SearchSatsangis(satsangi_pb2.SearchRequest(query=rng.choice(SEARCH_QUERIES)))
        else:
            proto,_=rand_proto(rng); t=time.perf_counter(); stub.CreateSatsangi(proto)
        gt.append((time.perf_counter()-t)*1000)
    ch.close()
    w = n // 5
    print(f"\n  Latency over time (mean ms per {w}-request window):\n")
    print(f"  {'Window':<12s} {'REST mean':>10s} {'gRPC mean':>10s} {'REST p95':>10s} {'gRPC p95':>10s}")
    for i in range(5):
        rw=rt[i*w:(i+1)*w]; gw=gt[i*w:(i+1)*w]
        print(f"  {f'{i*w+1}-{(i+1)*w}':<12s} {statistics.mean(rw):>10.3f} {statistics.mean(gw):>10.3f}"
              f" {pct(rw,95):>10.3f} {pct(gw,95):>10.3f}")
    r_drift = statistics.mean(rt[-w:]) - statistics.mean(rt[:w])
    g_drift = statistics.mean(gt[-w:]) - statistics.mean(gt[:w])
    print(f"\n  Drift: REST={r_drift:+.3f}ms {'↑degraded' if r_drift>1 else '~stable'}"
          f"  gRPC={g_drift:+.3f}ms {'↑degraded' if g_drift>1 else '~stable'}")
    ALL_RESULTS["B13_long_session"] = {"rest": ss(rt), "grpc": ss(gt),
        "rest_drift": round(r_drift,3), "grpc_drift": round(g_drift,3)}


def bench_14_error_recovery():
    """Send some bad requests, then good ones. Measure recovery speed."""
    header("B14. ERROR RECOVERY (bad → good requests)")
    n_bad, n_good = 10, 30
    bad_payload = {"first_name": "", "last_name": "", "phone_number": ""}  # might fail validation

    # REST
    s = req_lib.Session()
    rest_bad, rest_good = [], []
    for _ in range(n_bad):
        t=time.perf_counter()
        try: s.post(f"{REST_BASE}/satsangis", json=bad_payload, timeout=TIMEOUT)
        except: pass
        rest_bad.append((time.perf_counter()-t)*1000)
    for _ in range(n_good):
        t=time.perf_counter(); s.post(f"{REST_BASE}/satsangis",json=SAMPLE_FULL,timeout=TIMEOUT)
        rest_good.append((time.perf_counter()-t)*1000)
    s.close()

    # gRPC
    bad_proto = satsangi_pb2.SatsangiCreate(first_name="", last_name="", phone_number="")
    ch=grpc.insecure_channel(GRPC_TARGET); stub=satsangi_pb2_grpc.SatsangiServiceStub(ch)
    grpc_bad, grpc_good = [], []
    for _ in range(n_bad):
        t=time.perf_counter()
        try: stub.CreateSatsangi(bad_proto)
        except: pass
        grpc_bad.append((time.perf_counter()-t)*1000)
    for _ in range(n_good):
        t=time.perf_counter(); stub.CreateSatsangi(SAMPLE_PROTO_FULL)
        grpc_good.append((time.perf_counter()-t)*1000)
    ch.close()

    cmp("Bad request mean", statistics.mean(rest_bad), statistics.mean(grpc_bad), "ms")
    cmp("Recovery (1st good after bad)", rest_good[0], grpc_good[0], "ms")
    cmp("Good request mean (post-err)", statistics.mean(rest_good), statistics.mean(grpc_good), "ms")
    cmp("Good request p95 (post-err)", pct(rest_good,95), pct(grpc_good,95), "ms")
    ALL_RESULTS["B14_error_recovery"] = {"rest_bad": ss(rest_bad), "grpc_bad": ss(grpc_bad),
        "rest_good": ss(rest_good), "grpc_good": ss(grpc_good)}


def bench_15_concurrent_mixed():
    """Realistic: 10 concurrent users, 80% reads 20% writes, random queries."""
    header("B15. CONCURRENT MIXED WORKLOAD (10 users, 80/20 read/write)")
    nc, rpw = 10, 50

    def rest_mixed_worker(seed):
        rng=random.Random(seed); ts=[]; errs=0; s=req_lib.Session()
        for _ in range(rpw):
            try:
                t=time.perf_counter()
                if rng.random()<0.8: s.get(f"{REST_BASE}/satsangis?q={rng.choice(SEARCH_QUERIES)}",timeout=TIMEOUT)
                else: s.post(f"{REST_BASE}/satsangis",json=rand_payload(rng),timeout=TIMEOUT)
                ts.append((time.perf_counter()-t)*1000)
            except: errs+=1
        s.close(); return ts, errs

    def grpc_mixed_worker(seed):
        rng=random.Random(seed); ts=[]; errs=0
        c=grpc.insecure_channel(GRPC_TARGET); st=satsangi_pb2_grpc.SatsangiServiceStub(c)
        for _ in range(rpw):
            try:
                t=time.perf_counter()
                if rng.random()<0.8: st.SearchSatsangis(satsangi_pb2.SearchRequest(query=rng.choice(SEARCH_QUERIES)))
                else: proto,_=rand_proto(rng); st.CreateSatsangi(proto)
                ts.append((time.perf_counter()-t)*1000)
            except: errs+=1
        c.close(); return ts, errs

    rt, re = [], 0
    t0=time.perf_counter()
    with ThreadPoolExecutor(nc) as pool:
        futs = [pool.submit(rest_mixed_worker, SEED+i) for i in range(nc)]
        for f in as_completed(futs):
            ts, e = f.result(); rt.extend(ts); re+=e
    rw_t=time.perf_counter()-t0

    gt, ge = [], 0
    t0=time.perf_counter()
    with ThreadPoolExecutor(nc) as pool:
        futs = [pool.submit(grpc_mixed_worker, SEED+i) for i in range(nc)]
        for f in as_completed(futs):
            ts, e = f.result(); gt.extend(ts); ge+=e
    gw_t=time.perf_counter()-t0

    cmp("Wall time", rw_t*1000, gw_t*1000, "ms")
    cmp("Throughput", len(rt)/rw_t, len(gt)/gw_t, "rps", lower_better=False)
    cmp("Mean latency", statistics.mean(rt), statistics.mean(gt), "ms")
    cmp("p95 latency", pct(rt,95), pct(gt,95), "ms")
    cmp("p99 latency", pct(rt,99), pct(gt,99), "ms")
    if re or ge: print(f"  Errors — REST: {re}, gRPC: {ge}")
    ALL_RESULTS["B15_concurrent_mixed"] = {"rest": ss(rt), "grpc": ss(gt),
        "rest_rps": round(len(rt)/rw_t,1), "grpc_rps": round(len(gt)/gw_t,1)}


def bench_16_cold_vs_warm():
    """Cold start (new connection, first request) vs warm (reused connection)."""
    header("B16. COLD START vs WARM")
    trials = 20

    rest_cold, rest_warm = [], []
    for _ in range(trials):
        time.sleep(0.5)  # brief idle
        t=time.perf_counter()
        req_lib.get(f"{REST_BASE}/satsangis?q=Bench",timeout=TIMEOUT)
        rest_cold.append((time.perf_counter()-t)*1000)

    s=req_lib.Session()
    for _ in range(20): s.get(f"{REST_BASE}/satsangis?q=warmup",timeout=TIMEOUT)  # warm up
    for _ in range(trials):
        t=time.perf_counter(); s.get(f"{REST_BASE}/satsangis?q=Bench",timeout=TIMEOUT)
        rest_warm.append((time.perf_counter()-t)*1000)
    s.close()

    grpc_cold, grpc_warm = [], []
    for _ in range(trials):
        time.sleep(0.5)
        c=grpc.insecure_channel(GRPC_TARGET); st=satsangi_pb2_grpc.SatsangiServiceStub(c)
        t=time.perf_counter(); st.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
        grpc_cold.append((time.perf_counter()-t)*1000); c.close()

    c=grpc.insecure_channel(GRPC_TARGET); st=satsangi_pb2_grpc.SatsangiServiceStub(c)
    for _ in range(20): st.SearchSatsangis(satsangi_pb2.SearchRequest(query="warmup"))
    for _ in range(trials):
        t=time.perf_counter(); st.SearchSatsangis(satsangi_pb2.SearchRequest(query="Bench"))
        grpc_warm.append((time.perf_counter()-t)*1000)
    c.close()

    cmp("Cold start mean", statistics.mean(rest_cold), statistics.mean(grpc_cold), "ms")
    cmp("Warm mean", statistics.mean(rest_warm), statistics.mean(grpc_warm), "ms")
    cmp("Cold p95", pct(rest_cold,95), pct(grpc_cold,95), "ms")
    cmp("Warm p95", pct(rest_warm,95), pct(grpc_warm,95), "ms")
    r_penalty = statistics.mean(rest_cold) - statistics.mean(rest_warm)
    g_penalty = statistics.mean(grpc_cold) - statistics.mean(grpc_warm)
    print(f"\n  Cold-start penalty: REST={r_penalty:.3f}ms  gRPC={g_penalty:.3f}ms")
    ALL_RESULTS["B16_cold_warm"] = {"rest_cold": ss(rest_cold), "rest_warm": ss(rest_warm),
        "grpc_cold": ss(grpc_cold), "grpc_warm": ss(grpc_warm)}


# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    print(DIV)
    print("  REST vs gRPC — Robust Benchmark Suite")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  REST on :8001 (FastAPI + PostgreSQL)")
    print(f"  gRPC on :50051 (grpcio + PostgreSQL)")
    print(DIV)
    check()

    # Warmup
    print("  Warming up (30 requests each)...")
    s = req_lib.Session()
    c = grpc.insecure_channel(GRPC_TARGET)
    st = satsangi_pb2_grpc.SatsangiServiceStub(c)
    for _ in range(30):
        s.get(f"{REST_BASE}/satsangis?q=warmup", timeout=5)
        st.SearchSatsangis(satsangi_pb2.SearchRequest(query="warmup"))
    s.close(); c.close()
    print("  Warmup done.\n")

    benchmarks = [
        ("A1", bench_01_latency), ("A2", bench_02_throughput),
        ("A3", bench_03_payload), ("A4", bench_04_serialization),
        ("A5", bench_05_concurrency), ("A6", bench_06_streaming),
        ("A7", bench_07_connection), ("A8", bench_08_memory),
        ("B9", bench_09_page_load), ("B10", bench_10_bursty),
        ("B11", bench_11_variable_payload), ("B12", bench_12_jitter),
        ("B13", bench_13_long_session), ("B14", bench_14_error_recovery),
        ("B15", bench_15_concurrent_mixed), ("B16", bench_16_cold_vs_warm),
    ]

    for tag, fn in benchmarks:
        try:
            fn()
        except KeyboardInterrupt:
            print("\n  Interrupted."); break
        except Exception as e:
            print(f"\n  ERROR in {tag}: {e}")
            import traceback; traceback.print_exc()

    # Save JSON results
    out = Path(__file__).parent / "results.json"
    with open(out, "w") as f:
        json.dump(ALL_RESULTS, f, indent=2)
    print(f"\n  Raw results saved to {out}")

    # Print summary
    print(f"\n{'#'*80}")
    print("  BENCHMARK COMPLETE — Summary")
    print(f"{'#'*80}\n")
    print("  16 benchmarks executed (8 synthetic + 8 real-life).")
    print("  Raw data: benchmarks/results.json")
    print("  Report:   benchmarks/RESULTS.md")
    print(f"\n{'#'*80}\n")


if __name__ == "__main__":
    main()
