"""Shared benchmark infrastructure.

Provides:
  • Mock DB layer (no real PostgreSQL needed)
  • Fake data generators that match the proto schema
  • Timing / statistics helpers
  • gRPC server + grpc-web proxy bootstrap (in-process)
  • Result collection and pretty-printing
"""

from __future__ import annotations

import base64
import contextlib
import logging
import os
import random
import statistics
import string
import struct
import sys
import threading
import time
from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path setup — make `app.*` importable from the gRPC server package
# ---------------------------------------------------------------------------

_SERVER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "jkpRegistrationFULLGRPC",
    "server",
)
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)
logger = logging.getLogger("bench")
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Fake data generators
# ---------------------------------------------------------------------------

_FIRST_NAMES = [
    "Ram", "Shyam", "Radha", "Krishna", "Meera", "Arjun", "Sita", "Lakshmi",
    "Gopal", "Anand", "Priya", "Deepak", "Sunita", "Vijay", "Neha", "Mohan",
    "Geeta", "Harsh", "Kavita", "Suresh", "Pooja", "Rajesh", "Asha", "Manoj",
]
_LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Patel", "Joshi", "Mishra", "Pandey",
    "Agarwal", "Yadav", "Tiwari", "Chauhan", "Dubey", "Saxena", "Rastogi",
]
_CITIES = [
    "Vrindavan", "Mathura", "Prem Mandir", "Bhakti Dham", "Mangarh",
    "Delhi", "Mumbai", "Kolkata", "Chennai", "Lucknow", "Patna", "Jaipur",
]
_STATES = [
    "Uttar Pradesh", "Madhya Pradesh", "Rajasthan", "Bihar", "Maharashtra",
    "Gujarat", "West Bengal", "Tamil Nadu", "Karnataka", "Haryana",
]
_GENDERS = ["Male", "Female"]
_CATEGORIES = ["VIP", "Seva", "General", "Student", "Senior"]
_SEARCH_TERMS = [
    "Ram", "Sharma", "Delhi", "9876", "Vrindavan", "Patel", "Mohan",
    "Gupta", "Kolkata", "Sita", "Krishna", "Priya", "Mumbai", "Singh",
]


def _rand_phone() -> str:
    return f"+91{''.join(random.choices(string.digits, k=10))}"


def _rand_id() -> str:
    return "".join(random.choices(string.hexdigits[:16], k=8)).upper()


def _rand_email(first: str, last: str) -> str:
    return f"{first.lower()}.{last.lower()}@example.com"


def fake_satsangi_dict(*, full: bool = False) -> dict[str, Any]:
    """Return a dict matching SatsangiCreate fields.

    If full=True, populates all optional fields for max-payload testing.
    """
    first = random.choice(_FIRST_NAMES)
    last = random.choice(_LAST_NAMES)
    data: dict[str, Any] = {
        "first_name": first,
        "last_name": last,
        "phone_number": _rand_phone(),
        "nationality": "Indian",
        "country": "India",
        "print_on_card": random.choice([True, False]),
        "has_room_in_ashram": random.choice([True, False]),
        "banned": False,
        "first_timer": random.choice([True, False]),
    }
    if full:
        data.update(
            age=random.randint(18, 80),
            date_of_birth=f"19{random.randint(45, 99)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            pan=f"{''.join(random.choices(string.ascii_uppercase, k=5))}{''.join(random.choices(string.digits, k=4))}{''.join(random.choices(string.ascii_uppercase, k=1))}",
            gender=random.choice(_GENDERS),
            special_category=random.choice(_CATEGORIES),
            govt_id_type="Aadhaar",
            govt_id_number="".join(random.choices(string.digits, k=12)),
            id_expiry_date="2035-12-31",
            id_issuing_country="India",
            nick_name=first[:3].lower(),
            introducer=random.choice(_FIRST_NAMES),
            address=f"{random.randint(1,999)} {random.choice(['Main St','Temple Rd','Ashram Lane'])}",
            city=random.choice(_CITIES),
            district=random.choice(_CITIES),
            state=random.choice(_STATES),
            pincode=f"{random.randint(100000, 999999)}",
            emergency_contact=_rand_phone(),
            ex_center_satsangi_id=_rand_id(),
            introduced_by=random.choice(_LAST_NAMES),
            email=_rand_email(first, last),
            date_of_first_visit="2025-01-15",
            notes="Benchmark test record",
        )
    return data


def random_search_term() -> str:
    return random.choice(_SEARCH_TERMS)


# ---------------------------------------------------------------------------
# Mock DB layer — replaces psycopg2 pool entirely
# ---------------------------------------------------------------------------

# In-memory store used by the mock
_mock_store: list[dict[str, Any]] = []
_mock_store_lock = threading.Lock()


class _MockCursor:
    """Simulates a psycopg2 RealDictCursor backed by an in-memory list."""

    def __init__(self, *, latency_ms: float = 0.0) -> None:
        self._latency = latency_ms / 1000.0
        self._result: list[dict[str, Any]] = []
        self._description = None

    def execute(self, sql: str, params: Any = None) -> None:
        if self._latency > 0:
            time.sleep(self._latency)

        sql_upper = sql.strip().upper()

        if sql_upper.startswith("SELECT 1"):
            self._result = [{"?column?": 1}]
            return

        if sql_upper.startswith("CREATE"):
            self._result = []
            return

        if sql_upper.startswith("INSERT"):
            # Build a row from the params
            from app.store import _INSERT_FIELDS, _ALL_FIELDS

            row: dict[str, Any] = {}
            for i, fname in enumerate(_INSERT_FIELDS):
                row[fname] = params[i] if params and i < len(params) else None
            row["created_at"] = datetime.now()
            with _mock_store_lock:
                _mock_store.append(row)
            self._result = [row]
            return

        if "ILIKE" in sql_upper:
            # Search — simple substring match on first_name/last_name
            pattern = ""
            if params:
                pattern = str(params[0]).strip("%").lower()
            with _mock_store_lock:
                if pattern:
                    self._result = [
                        r for r in _mock_store
                        if pattern in str(r.get("first_name", "")).lower()
                        or pattern in str(r.get("last_name", "")).lower()
                        or pattern in str(r.get("phone_number", "")).lower()
                        or pattern in str(r.get("city", "")).lower()
                    ]
                else:
                    self._result = list(_mock_store)
            return

        if sql_upper.startswith("SELECT") and "FROM SATSANGIS" in sql_upper:
            # LIST
            with _mock_store_lock:
                result = list(_mock_store)
            # Handle LIMIT
            if params:
                result = result[: params[0]]
            self._result = result
            return

        self._result = []

    def fetchone(self) -> dict[str, Any] | None:
        return self._result[0] if self._result else None

    def fetchall(self) -> list[dict[str, Any]]:
        return self._result

    def __enter__(self) -> "_MockCursor":
        return self

    def __exit__(self, *_: Any) -> None:
        pass


class _MockConnection:
    """Simulates a psycopg2 connection."""

    def __init__(self, *, latency_ms: float = 0.0) -> None:
        self._latency_ms = latency_ms

    def cursor(self, cursor_factory: Any = None) -> _MockCursor:
        return _MockCursor(latency_ms=self._latency_ms)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


@contextlib.contextmanager
def mock_get_conn(
    *, latency_ms: float = 0.0
) -> Generator[_MockConnection, None, None]:
    yield _MockConnection(latency_ms=latency_ms)


def reset_mock_store() -> None:
    """Clear the in-memory mock store."""
    global _mock_store
    with _mock_store_lock:
        _mock_store.clear()


def seed_mock_store(n: int = 100, *, full: bool = True) -> None:
    """Pre-populate the mock store with n records."""
    reset_mock_store()
    from uuid import uuid4

    with _mock_store_lock:
        for _ in range(n):
            d = fake_satsangi_dict(full=full)
            d["satsangi_id"] = uuid4().hex[:8].upper()
            d["created_at"] = datetime.now()
            _mock_store.append(d)


# ---------------------------------------------------------------------------
# gRPC server bootstrap (with mocked DB)
# ---------------------------------------------------------------------------


def start_mock_grpc_server(
    port: int = 50051,
    max_workers: int = 10,
    db_latency_ms: float = 0.0,
) -> Any:
    """Start the real gRPC server with the DB layer mocked out.

    Patches both app.db.get_conn AND app.store.get_conn because store.py
    binds get_conn at import time via `from app.db import get_conn`.
    """
    import app.db as db_mod
    import app.store as store_mod

    # Patch init_pool to no-op and get_conn to use mock
    db_mod.init_pool = lambda **kw: None  # type: ignore[assignment]
    db_mod.close_pool = lambda: None  # type: ignore[assignment]

    @contextlib.contextmanager
    def _patched_get_conn() -> Generator[_MockConnection, None, None]:
        yield _MockConnection(latency_ms=db_latency_ms)

    db_mod.get_conn = _patched_get_conn  # type: ignore[assignment]
    store_mod.get_conn = _patched_get_conn  # type: ignore[assignment]

    from app.grpc_server import serve
    server = serve(port=port, max_workers=max_workers)
    return server


# ---------------------------------------------------------------------------
# grpc-web proxy bootstrap (FastAPI + uvicorn in a background thread)
# ---------------------------------------------------------------------------


def start_mock_proxy(
    proxy_port: int = 18080,
    grpc_port: int = 50051,
    db_latency_ms: float = 0.0,
) -> threading.Thread:
    """Start uvicorn serving the grpc-web proxy in a daemon thread.

    Key fix: reset the singleton grpc.aio channel so it gets created inside
    uvicorn's event loop, not the main thread's loop. Without this,
    grpc.aio raises "attached to a different loop" under concurrent load.
    """
    import app.db as db_mod
    import app.main as main_mod

    # Patch DB
    @contextlib.contextmanager
    def _patched_get_conn() -> Generator[_MockConnection, None, None]:
        yield _MockConnection(latency_ms=db_latency_ms)

    db_mod.get_conn = _patched_get_conn  # type: ignore[assignment]
    db_mod.init_pool = lambda **kw: None  # type: ignore[assignment]
    db_mod.close_pool = lambda: None  # type: ignore[assignment]

    # Override the gRPC target to point to our test server
    main_mod.GRPC_TARGET = f"localhost:{grpc_port}"

    # CRITICAL: Reset the singleton channel so it gets created fresh inside
    # uvicorn's event loop thread. Otherwise grpc.aio raises RuntimeError.
    main_mod._channel = None

    import uvicorn

    def _run_uvicorn() -> None:
        """Run uvicorn in a fresh asyncio event loop."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Force channel recreation in this loop
        main_mod._channel = None
        config = uvicorn.Config(
            main_mod.app,
            host="127.0.0.1",
            port=proxy_port,
            log_level="error",
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        loop.run_until_complete(server.serve())

    t = threading.Thread(target=_run_uvicorn, daemon=True)
    t.start()

    # Wait for it to be ready
    import httpx
    for _ in range(50):
        try:
            r = httpx.get(f"http://127.0.0.1:{proxy_port}/healthz", timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.1)

    return t


# ---------------------------------------------------------------------------
# grpc-web frame encoding (for proxy benchmarks)
# ---------------------------------------------------------------------------


def encode_grpc_web_request(proto_bytes: bytes) -> bytes:
    """Encode protobuf bytes into a grpc-web-text (base64) request body."""
    frame = struct.pack(">BI", 0x00, len(proto_bytes)) + proto_bytes
    return base64.b64encode(frame)


def decode_grpc_web_response(body: bytes) -> bytes:
    """Decode a grpc-web-text (base64) response to get the protobuf payload."""
    raw = base64.b64decode(body)
    if len(raw) < 5:
        raise ValueError("Response too short")
    length = struct.unpack(">I", raw[1:5])[0]
    return raw[5 : 5 + length]


# ---------------------------------------------------------------------------
# Timing + statistics
# ---------------------------------------------------------------------------


@dataclass
class BenchResult:
    """Result of a single benchmark run."""
    name: str
    total_requests: int
    duration_s: float
    latencies_ms: list[float] = field(default_factory=list)
    errors: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def rps(self) -> float:
        return self.total_requests / self.duration_s if self.duration_s > 0 else 0

    @property
    def success_rate(self) -> float:
        return (self.total_requests - self.errors) / self.total_requests * 100 if self.total_requests > 0 else 0

    @property
    def p50(self) -> float:
        return _percentile(self.latencies_ms, 50)

    @property
    def p95(self) -> float:
        return _percentile(self.latencies_ms, 95)

    @property
    def p99(self) -> float:
        return _percentile(self.latencies_ms, 99)

    @property
    def mean(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.latencies_ms) if len(self.latencies_ms) > 1 else 0

    @property
    def min_ms(self) -> float:
        return min(self.latencies_ms) if self.latencies_ms else 0

    @property
    def max_ms(self) -> float:
        return max(self.latencies_ms) if self.latencies_ms else 0

    def summary_line(self) -> str:
        return (
            f"  {self.name:<45s}  "
            f"reqs={self.total_requests:>5d}  "
            f"rps={self.rps:>8.1f}  "
            f"p50={self.p50:>7.2f}ms  "
            f"p95={self.p95:>7.2f}ms  "
            f"p99={self.p99:>7.2f}ms  "
            f"err={self.errors}"
        )

    def to_markdown_row(self) -> str:
        return (
            f"| {self.name} "
            f"| {self.total_requests} "
            f"| {self.rps:.1f} "
            f"| {self.mean:.2f} "
            f"| {self.p50:.2f} "
            f"| {self.p95:.2f} "
            f"| {self.p99:.2f} "
            f"| {self.min_ms:.2f} "
            f"| {self.max_ms:.2f} "
            f"| {self.success_rate:.1f}% |"
        )


def _percentile(data: list[float], pct: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(s):
        return s[f]
    return s[f] + (k - f) * (s[c] - s[f])


class Timer:
    """Simple context-manager timer returning elapsed ms."""

    def __init__(self) -> None:
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000.0


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

_MARKDOWN_TABLE_HEADER = (
    "| Benchmark | Requests | RPS | Mean (ms) | p50 (ms) | p95 (ms) "
    "| p99 (ms) | Min (ms) | Max (ms) | Success |"
)
_MARKDOWN_TABLE_SEP = (
    "|---|---|---|---|---|---|---|---|---|---|"
)


def print_results(results: list[BenchResult], title: str = "Results") -> None:
    print(f"\n{'='*90}")
    print(f"  {title}")
    print(f"{'='*90}")
    for r in results:
        print(r.summary_line())
    print(f"{'='*90}\n")


def results_to_markdown_table(results: list[BenchResult]) -> str:
    lines = [_MARKDOWN_TABLE_HEADER, _MARKDOWN_TABLE_SEP]
    for r in results:
        lines.append(r.to_markdown_row())
    return "\n".join(lines)
