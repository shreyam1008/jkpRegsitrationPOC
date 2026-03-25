"""Async PostgreSQL connection pool and schema management (psycopg v3).

Resilience:
  • init_pool retries up to 5 times (2 s backoff) so the server survives
    a DB that isn't ready yet at boot (common with Docker Compose).
  • AsyncConnectionPool auto-validates and recycles dead connections.
  • All I/O is non-blocking — never stalls the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection, OperationalError
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

DB_CONNINFO = (
    f"host={os.environ.get('DB_HOST', 'localhost')} "
    f"port={os.environ.get('DB_PORT', '5432')} "
    f"dbname={os.environ.get('DB_NAME', 'jkp_reg_poc_grpc')} "
    f"user={os.environ.get('DB_USER', 'postgres')} "
    f"password={os.environ.get('DB_PASSWORD', 'postgres')}"
)

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
# Async connection pool (created once at startup)
# ---------------------------------------------------------------------------

_pool: AsyncConnectionPool | None = None


async def init_pool(
    min_size: int = 2,
    max_size: int = 20,
    retries: int = 5,
    backoff: float = 2.0,
) -> None:
    """Create the async connection pool and initialize the DB schema.

    Retries up to *retries* times with exponential backoff so the server
    can start even when the DB container is still booting.
    """
    global _pool

    for attempt in range(1, retries + 1):
        try:
            _pool = AsyncConnectionPool(
                conninfo=DB_CONNINFO,
                min_size=min_size,
                max_size=max_size,
                open=False,
            )
            await _pool.open()
            # Initialize schema
            async with _pool.connection() as conn:
                await conn.execute(CREATE_TABLE_SQL)
            logger.info("DB pool created (%d–%d conns), schema initialized", min_size, max_size)
            return
        except OperationalError:
            if attempt == retries:
                raise
            wait = backoff * attempt
            logger.warning(
                "DB not ready (attempt %d/%d), retrying in %.1fs…", attempt, retries, wait
            )
            await asyncio.sleep(wait)


async def close_pool() -> None:
    """Shut down the pool (call on app exit)."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_conn() -> AsyncGenerator[AsyncConnection, None]:
    """Borrow an async connection from the pool; auto-returns on exit.

    The pool handles liveness checks and stale connection replacement
    automatically via its built-in health-check mechanism.
    """
    if _pool is None:
        raise RuntimeError("DB pool not initialized — call init_pool() first")
    async with _pool.connection() as conn:
        yield conn
