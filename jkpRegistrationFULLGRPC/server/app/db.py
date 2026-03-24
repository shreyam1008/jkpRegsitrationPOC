"""PostgreSQL connection pool and schema management."""

from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import Generator

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
# Thread-safe connection pool (created once at startup)
# ---------------------------------------------------------------------------

_pool: pool.ThreadedConnectionPool | None = None


def init_pool(minconn: int = 2, maxconn: int = 20) -> None:
    """Create the connection pool and initialize the DB schema."""
    global _pool
    _pool = pool.ThreadedConnectionPool(minconn, maxconn, **DB_CONFIG)
    conn = _pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        logger.info("DB pool created (%d–%d conns), schema initialized", minconn, maxconn)
    finally:
        _pool.putconn(conn)


def close_pool() -> None:
    """Shut down the pool (call on app exit)."""
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None


@contextlib.contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Borrow a connection from the pool; auto-returns on exit."""
    if _pool is None:
        raise RuntimeError("DB pool not initialised — call init_pool() first")
    conn = _pool.getconn()
    try:
        yield conn
    finally:
        _pool.putconn(conn)
