"""PostgreSQL connection pool and schema management.

Resilience:
  • init_pool retries up to 5 times (2 s backoff) so the server survives
    a DB that isn't ready yet at boot (common with Docker Compose).
  • get_conn validates the borrowed connection with a lightweight query.
    If it's dead, the bad conn is discarded and a fresh one is fetched.
  • If the entire pool is dead (closeall'd / corrupted), get_conn
    transparently recreates it.
"""

from __future__ import annotations

import contextlib
import logging
import os
import threading
import time
from collections.abc import Generator

import psycopg2
import psycopg2.extensions
from psycopg2 import pool

logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "5432")),
    "dbname": os.environ.get("DB_NAME", "jkp_reg_poc_grpc"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "postgres"),
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS satsangis (
    satsangi_id         VARCHAR(8) PRIMARY KEY,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    phone_number        VARCHAR(20) NOT NULL,
    age                 INTEGER,
    date_of_birth       VARCHAR(20),
    pan                 VARCHAR(20),
    gender              VARCHAR(10),
    special_category    VARCHAR(30),
    nationality         VARCHAR(30) NOT NULL DEFAULT 'Indian',
    govt_id_type        VARCHAR(30),
    govt_id_number      VARCHAR(50),
    id_expiry_date      VARCHAR(20),
    id_issuing_country  VARCHAR(30),
    nick_name           VARCHAR(100),
    print_on_card       BOOLEAN NOT NULL DEFAULT FALSE,
    introducer          VARCHAR(200),
    country             VARCHAR(30) NOT NULL DEFAULT 'India',
    address             TEXT,
    city                VARCHAR(100),
    district            VARCHAR(100),
    state               VARCHAR(100),
    pincode             VARCHAR(10),
    emergency_contact   VARCHAR(20),
    ex_center_satsangi_id VARCHAR(20),
    introduced_by       VARCHAR(30),
    has_room_in_ashram  BOOLEAN NOT NULL DEFAULT FALSE,
    email               VARCHAR(200),
    banned              BOOLEAN NOT NULL DEFAULT FALSE,
    first_timer         BOOLEAN NOT NULL DEFAULT FALSE,
    date_of_first_visit VARCHAR(20),
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS idx_satsangis_name
    ON satsangis (LOWER(first_name), LOWER(last_name));
CREATE INDEX IF NOT EXISTS idx_satsangis_phone
    ON satsangis (phone_number);
CREATE INDEX IF NOT EXISTS idx_satsangis_email
    ON satsangis (LOWER(email)) WHERE email IS NOT NULL;
"""

# ---------------------------------------------------------------------------
# Thread-safe connection pool with retry and auto-reconnect
# ---------------------------------------------------------------------------

_pool: pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()
_pool_minconn: int = 2
_pool_maxconn: int = 20


def _create_pool(minconn: int, maxconn: int) -> pool.ThreadedConnectionPool:
    """Low-level pool creation (no retry, no schema init)."""
    return pool.ThreadedConnectionPool(minconn, maxconn, **DB_CONFIG)


def init_pool(
    minconn: int = 2,
    maxconn: int = 20,
    retries: int = 5,
    backoff: float = 2.0,
) -> None:
    """Create the connection pool and initialize the DB schema.

    Retries up to *retries* times with exponential backoff so the server
    can start even when the DB container is still booting.
    """
    global _pool, _pool_minconn, _pool_maxconn
    _pool_minconn, _pool_maxconn = minconn, maxconn

    for attempt in range(1, retries + 1):
        try:
            _pool = _create_pool(minconn, maxconn)
            conn = _pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(CREATE_TABLE_SQL)
                conn.commit()
            finally:
                _pool.putconn(conn)
            logger.info("DB pool created (%d–%d conns), schema initialized", minconn, maxconn)
            return
        except psycopg2.OperationalError:
            if attempt == retries:
                raise
            wait = backoff * attempt
            logger.warning("DB not ready (attempt %d/%d), retrying in %.1fs…", attempt, retries, wait)
            time.sleep(wait)


def close_pool() -> None:
    """Shut down the pool (call on app exit)."""
    global _pool
    with _pool_lock:
        if _pool:
            _pool.closeall()
            _pool = None


def _ensure_pool() -> pool.ThreadedConnectionPool:
    """Return the live pool, recreating it if it was lost."""
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is None:
            logger.warning("DB pool lost — recreating (%d–%d)", _pool_minconn, _pool_maxconn)
            _pool = _create_pool(_pool_minconn, _pool_maxconn)
        return _pool


@contextlib.contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Borrow a connection from the pool; auto-returns on exit.

    If the borrowed connection is dead (server restarted, network blip),
    it is discarded and a fresh one is fetched — one automatic retry.
    """
    p = _ensure_pool()
    conn = p.getconn()
    try:
        # Lightweight liveness check (costs ~0.1 ms on localhost)
        conn.cursor().execute("SELECT 1")
    except (psycopg2.OperationalError, psycopg2.InterfaceError):
        # Connection is dead — throw it away and get a new one
        logger.warning("Stale DB connection detected — replacing")
        p.putconn(conn, close=True)
        conn = p.getconn()
    try:
        yield conn
    finally:
        p.putconn(conn)
