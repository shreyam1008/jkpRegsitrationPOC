"""Benchmark Suite 6: Protobuf Serialization & Encoding Overhead.

Isolates the cost of each data transformation in the pipeline:

  Browser side:
    1. JS object → protobuf binary (ConnectRPC)
    2. protobuf binary → grpc-web frame (5-byte header)
    3. grpc-web frame → base64 text

  Proxy side:
    4. base64 decode
    5. grpc-web frame strip (5-byte header removal)
    6. Forward raw bytes (zero-copy)
    7. Response: protobuf → frame → base64

  Server side:
    8. protobuf deserialize → Python object
    9. Proto → Pydantic model conversion
    10. Pydantic model → Proto conversion
    11. protobuf serialize → bytes

This suite benchmarks steps 4-11 (the Python-side transformations).
"""

from __future__ import annotations

import base64
import struct
import time

from helpers import (
    BenchResult,
    Timer,
    fake_satsangi_dict,
    logger,
    print_results,
    seed_mock_store,
)

from app.generated import satsangi_pb2  # noqa: E402
from app.models import Satsangi, SatsangiCreate  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — build proto messages with various sizes
# ---------------------------------------------------------------------------


def _make_create_proto(full: bool = False) -> satsangi_pb2.SatsangiCreate:
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


def _make_satsangi_proto(full: bool = True) -> satsangi_pb2.Satsangi:
    """Build a Satsangi proto (response-like) with satsangi_id and created_at."""
    d = fake_satsangi_dict(full=full)
    kwargs = {
        "satsangi_id": "ABCD1234",
        "created_at": "2026-03-24T14:00:00",
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
    return satsangi_pb2.Satsangi(**kwargs)


def _make_list_proto(count: int) -> satsangi_pb2.SatsangiList:
    """Build a SatsangiList with N satsangis."""
    return satsangi_pb2.SatsangiList(
        satsangis=[_make_satsangi_proto(full=True) for _ in range(count)]
    )


# ---------------------------------------------------------------------------
# Suite A: Protobuf serialize / deserialize
# ---------------------------------------------------------------------------


def bench_proto_serialize(n: int = 5000) -> list[BenchResult]:
    """Measure protobuf serialization speed at different payload sizes."""
    results = []

    # Minimal create
    msg_min = _make_create_proto(full=False)
    latencies: list[float] = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            _ = msg_min.SerializeToString()
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    result = BenchResult("Proto serialize (minimal ~50B)", n, duration, latencies)
    result.extra["bytes"] = len(msg_min.SerializeToString())
    results.append(result)

    # Full create
    msg_full = _make_create_proto(full=True)
    latencies = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            _ = msg_full.SerializeToString()
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    result = BenchResult("Proto serialize (full ~300B)", n, duration, latencies)
    result.extra["bytes"] = len(msg_full.SerializeToString())
    results.append(result)

    # Large list response
    for count in [10, 100, 500, 1000]:
        msg_list = _make_list_proto(count)
        latencies = []
        nn = min(n, 500)
        t0 = time.perf_counter()
        for _ in range(nn):
            with Timer() as t:
                _ = msg_list.SerializeToString()
            latencies.append(t.elapsed_ms)
        duration = time.perf_counter() - t0
        result = BenchResult(f"Proto serialize (list×{count})", nn, duration, latencies)
        result.extra["bytes"] = len(msg_list.SerializeToString())
        results.append(result)

    return results


def bench_proto_deserialize(n: int = 5000) -> list[BenchResult]:
    """Measure protobuf deserialization speed."""
    results = []

    # Minimal
    raw_min = _make_create_proto(full=False).SerializeToString()
    latencies: list[float] = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            msg = satsangi_pb2.SatsangiCreate()
            msg.ParseFromString(raw_min)
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult(f"Proto deserialize (minimal {len(raw_min)}B)", n, duration, latencies))

    # Full
    raw_full = _make_create_proto(full=True).SerializeToString()
    latencies = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            msg = satsangi_pb2.SatsangiCreate()
            msg.ParseFromString(raw_full)
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult(f"Proto deserialize (full {len(raw_full)}B)", n, duration, latencies))

    # List responses
    for count in [10, 100, 500, 1000]:
        raw_list = _make_list_proto(count).SerializeToString()
        latencies = []
        nn = min(n, 500)
        t0 = time.perf_counter()
        for _ in range(nn):
            with Timer() as t:
                msg = satsangi_pb2.SatsangiList()
                msg.ParseFromString(raw_list)
            latencies.append(t.elapsed_ms)
        duration = time.perf_counter() - t0
        results.append(BenchResult(f"Proto deserialize (list×{count}, {len(raw_list)}B)", nn, duration, latencies))

    return results


# ---------------------------------------------------------------------------
# Suite B: Base64 encode / decode (grpc-web specific)
# ---------------------------------------------------------------------------


def bench_base64_encoding(n: int = 5000) -> list[BenchResult]:
    """Base64 encoding overhead — this is the grpc-web tax."""
    results = []
    payloads = [
        ("50B request", _make_create_proto(full=False).SerializeToString()),
        ("300B request", _make_create_proto(full=True).SerializeToString()),
        ("3KB list×10", _make_list_proto(10).SerializeToString()),
        ("30KB list×100", _make_list_proto(100).SerializeToString()),
        ("150KB list×500", _make_list_proto(500).SerializeToString()),
    ]

    for label, raw in payloads:
        # Encode
        frame = struct.pack(">BI", 0x00, len(raw)) + raw
        latencies: list[float] = []
        nn = min(n, 2000)
        t0 = time.perf_counter()
        for _ in range(nn):
            with Timer() as t:
                _ = base64.b64encode(frame)
            latencies.append(t.elapsed_ms)
        duration = time.perf_counter() - t0
        result = BenchResult(f"Base64 encode ({label})", nn, duration, latencies)
        result.extra["raw_bytes"] = len(frame)
        result.extra["encoded_bytes"] = len(base64.b64encode(frame))
        result.extra["overhead_pct"] = (len(base64.b64encode(frame)) - len(frame)) / len(frame) * 100
        results.append(result)

        # Decode
        encoded = base64.b64encode(frame)
        latencies = []
        t0 = time.perf_counter()
        for _ in range(nn):
            with Timer() as t:
                _ = base64.b64decode(encoded)
            latencies.append(t.elapsed_ms)
        duration = time.perf_counter() - t0
        results.append(BenchResult(f"Base64 decode ({label})", nn, duration, latencies))

    return results


# ---------------------------------------------------------------------------
# Suite C: grpc-web frame pack / unpack
# ---------------------------------------------------------------------------


def bench_frame_operations(n: int = 10000) -> list[BenchResult]:
    """grpc-web frame header pack/unpack — the proxy's inner loop."""
    results = []

    payload = _make_create_proto(full=True).SerializeToString()

    # Pack (encode data frame)
    latencies: list[float] = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            _ = struct.pack(">BI", 0x00, len(payload)) + payload
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Frame pack (DATA frame)", n, duration, latencies))

    # Unpack (decode frame header)
    frame = struct.pack(">BI", 0x00, len(payload)) + payload
    latencies = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            length = struct.unpack(">I", frame[1:5])[0]
            _ = frame[5:5 + length]
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Frame unpack (strip header)", n, duration, latencies))

    return results


# ---------------------------------------------------------------------------
# Suite D: Proto ↔ Pydantic model conversion
# ---------------------------------------------------------------------------


def bench_proto_to_pydantic(n: int = 5000) -> list[BenchResult]:
    """Proto message → Pydantic model (server receive path)."""
    results = []

    # Import the conversion function from grpc_server
    from app.grpc_server import _proto_to_create

    req = _make_create_proto(full=True)
    latencies: list[float] = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            _ = _proto_to_create(req)
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Proto → Pydantic (SatsangiCreate)", n, duration, latencies))

    return results


def bench_pydantic_to_proto(n: int = 5000) -> list[BenchResult]:
    """Pydantic model → Proto message (server response path)."""
    results = []

    from app.grpc_server import _model_to_proto

    model = Satsangi(**fake_satsangi_dict(full=True))
    latencies: list[float] = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            _ = _model_to_proto(model)
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Pydantic → Proto (Satsangi)", n, duration, latencies))

    return results


def bench_pydantic_model_creation(n: int = 5000) -> list[BenchResult]:
    """Pydantic model instantiation — the validation overhead."""
    results = []

    # SatsangiCreate (input validation)
    d_min = fake_satsangi_dict(full=False)
    latencies: list[float] = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            _ = SatsangiCreate(**d_min)
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Pydantic SatsangiCreate (minimal)", n, duration, latencies))

    # Full Satsangi (with defaults)
    d_full = fake_satsangi_dict(full=True)
    latencies = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            _ = Satsangi(**d_full)
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Pydantic Satsangi (full + defaults)", n, duration, latencies))

    return results


# ---------------------------------------------------------------------------
# Suite E: Full pipeline — measure each step's contribution
# ---------------------------------------------------------------------------


def bench_full_pipeline(n: int = 2000) -> list[BenchResult]:
    """Measure the total cost of the full encode → proxy → decode pipeline.

    Breaks down: base64_decode + frame_strip + grpc_forward + frame_pack + base64_encode
    """
    results = []

    payload = _make_create_proto(full=True).SerializeToString()
    frame = struct.pack(">BI", 0x00, len(payload)) + payload
    encoded = base64.b64encode(frame)

    # Step 1: base64 decode
    latencies: list[float] = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            decoded = base64.b64decode(encoded)
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Pipeline: base64 decode", n, duration, latencies))

    # Step 2: frame strip
    latencies = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            length = struct.unpack(">I", frame[1:5])[0]
            proto_bytes = frame[5:5 + length]
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Pipeline: frame strip", n, duration, latencies))

    # Step 3: proto deserialize
    latencies = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            msg = satsangi_pb2.SatsangiCreate()
            msg.ParseFromString(payload)
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Pipeline: proto deserialize", n, duration, latencies))

    # Step 4: proto → pydantic
    from app.grpc_server import _proto_to_create
    req = _make_create_proto(full=True)
    latencies = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            _ = _proto_to_create(req)
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Pipeline: proto → pydantic", n, duration, latencies))

    # Step 5: pydantic → proto
    from app.grpc_server import _model_to_proto
    model = Satsangi(**fake_satsangi_dict(full=True))
    latencies = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            proto_msg = _model_to_proto(model)
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Pipeline: pydantic → proto", n, duration, latencies))

    # Step 6: proto serialize
    latencies = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            resp_bytes = proto_msg.SerializeToString()
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Pipeline: proto serialize", n, duration, latencies))

    # Step 7: frame pack + trailer
    _OK_TRAILERS = b"grpc-status:0\r\ngrpc-message:OK\r\n"
    _OK_TRAILER_FRAME = struct.pack(">BI", 0x80, len(_OK_TRAILERS)) + _OK_TRAILERS
    latencies = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            _ = struct.pack(">BI", 0x00, len(resp_bytes)) + resp_bytes + _OK_TRAILER_FRAME
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Pipeline: frame pack + trailer", n, duration, latencies))

    # Step 8: base64 encode response
    resp_frame = struct.pack(">BI", 0x00, len(resp_bytes)) + resp_bytes + _OK_TRAILER_FRAME
    latencies = []
    t0 = time.perf_counter()
    for _ in range(n):
        with Timer() as t:
            _ = base64.b64encode(resp_frame)
        latencies.append(t.elapsed_ms)
    duration = time.perf_counter() - t0
    results.append(BenchResult("Pipeline: base64 encode response", n, duration, latencies))

    return results


# ---------------------------------------------------------------------------
# Suite F: Payload size analysis
# ---------------------------------------------------------------------------


def bench_payload_sizes() -> list[BenchResult]:
    """Comprehensive payload size analysis across the wire format."""
    results = []

    configs = [
        ("Minimal SatsangiCreate", _make_create_proto(full=False)),
        ("Full SatsangiCreate", _make_create_proto(full=True)),
        ("Satsangi response", _make_satsangi_proto(full=True)),
        ("SatsangiList×10", _make_list_proto(10)),
        ("SatsangiList×50", _make_list_proto(50)),
        ("SatsangiList×100", _make_list_proto(100)),
        ("SatsangiList×500", _make_list_proto(500)),
    ]

    for label, msg in configs:
        proto_bytes = msg.SerializeToString()
        frame = struct.pack(">BI", 0x00, len(proto_bytes)) + proto_bytes
        b64 = base64.b64encode(frame)

        # Measure round-trip encode+decode
        n = 1000
        latencies: list[float] = []
        t0 = time.perf_counter()
        for _ in range(n):
            with Timer() as t:
                encoded = base64.b64encode(frame)
                decoded = base64.b64decode(encoded)
            latencies.append(t.elapsed_ms)
        duration = time.perf_counter() - t0

        result = BenchResult(f"Wire: {label}", n, duration, latencies)
        result.extra["proto_bytes"] = len(proto_bytes)
        result.extra["frame_bytes"] = len(frame)
        result.extra["base64_bytes"] = len(b64)
        result.extra["overhead_vs_proto"] = f"{(len(b64) - len(proto_bytes)) / len(proto_bytes) * 100:.1f}%"
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_all() -> list[BenchResult]:
    """Run all serialization benchmarks."""
    logger.info("Starting serialization & encoding benchmarks...")

    results: list[BenchResult] = []

    logger.info("  [1/7] Protobuf serialization...")
    results.extend(bench_proto_serialize())

    logger.info("  [2/7] Protobuf deserialization...")
    results.extend(bench_proto_deserialize())

    logger.info("  [3/7] Base64 encode/decode...")
    results.extend(bench_base64_encoding())

    logger.info("  [4/7] Frame pack/unpack...")
    results.extend(bench_frame_operations())

    logger.info("  [5/7] Proto ↔ Pydantic conversion...")
    results.extend(bench_proto_to_pydantic())
    results.extend(bench_pydantic_to_proto())
    results.extend(bench_pydantic_model_creation())

    logger.info("  [6/7] Full pipeline breakdown...")
    results.extend(bench_full_pipeline())

    logger.info("  [7/7] Payload size analysis...")
    results.extend(bench_payload_sizes())

    print_results(results, "Serialization & Encoding Overhead")
    return results


if __name__ == "__main__":
    run_all()
