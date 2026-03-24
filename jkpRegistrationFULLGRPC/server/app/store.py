"""PostgreSQL-backed storage for satsangi records.

All functions borrow a connection from the shared pool (db.get_conn)
and return it automatically via the context manager.
"""

from __future__ import annotations

from typing import Any

import psycopg2.extras

from app.db import get_conn
from app.models import Satsangi, SatsangiCreate

# ---------------------------------------------------------------------------
# Column lists + pre-computed SQL fragments (built once at import time)
# ---------------------------------------------------------------------------

_INSERT_FIELDS = (
    "satsangi_id", "first_name", "last_name", "phone_number", "age",
    "date_of_birth", "pan", "gender", "special_category", "nationality",
    "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country",
    "nick_name", "print_on_card", "introducer", "country", "address", "city",
    "district", "state", "pincode", "emergency_contact", "ex_center_satsangi_id",
    "introduced_by", "has_room_in_ashram", "email", "banned", "first_timer",
    "date_of_first_visit", "notes",
)

_ALL_FIELDS = (
    "satsangi_id", "created_at", "first_name", "last_name", "phone_number",
    "age", "date_of_birth", "pan", "gender", "special_category", "nationality",
    "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country",
    "nick_name", "print_on_card", "introducer", "country", "address", "city",
    "district", "state", "pincode", "emergency_contact", "ex_center_satsangi_id",
    "introduced_by", "has_room_in_ashram", "email", "banned", "first_timer",
    "date_of_first_visit", "notes",
)

_COLS = ", ".join(_ALL_FIELDS)
_INSERT_COLS = ", ".join(_INSERT_FIELDS)
_INSERT_PH = ", ".join(["%s"] * len(_INSERT_FIELDS))

_INSERT_SQL = (
    f"INSERT INTO satsangis ({_INSERT_COLS}) VALUES ({_INSERT_PH}) "
    f"RETURNING {_COLS}"
)

_SEARCH_SQL = f"""
    SELECT {_COLS} FROM satsangis
    WHERE first_name ILIKE %s
       OR last_name ILIKE %s
       OR (first_name || ' ' || last_name) ILIKE %s
       OR phone_number ILIKE %s
       OR satsangi_id ILIKE %s
       OR COALESCE(email, '') ILIKE %s
       OR COALESCE(pan, '') ILIKE %s
       OR COALESCE(govt_id_number, '') ILIKE %s
       OR COALESCE(nick_name, '') ILIKE %s
       OR COALESCE(ex_center_satsangi_id, '') ILIKE %s
       OR COALESCE(city, '') ILIKE %s
       OR COALESCE(pincode, '') ILIKE %s
    ORDER BY created_at DESC
"""

_LIST_SQL = f"SELECT {_COLS} FROM satsangis ORDER BY created_at DESC"
_COUNT_SQL = "SELECT COUNT(*) FROM satsangis"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_satsangi(row: dict[str, Any]) -> Satsangi:
    """Convert a database row dict to a Satsangi model."""
    data = dict(row)
    if data.get("created_at"):
        data["created_at"] = data["created_at"].isoformat()
    return Satsangi(**data)


# ---------------------------------------------------------------------------
# Public API (called by grpc_server.py)
# ---------------------------------------------------------------------------


def create_satsangi(data: SatsangiCreate) -> Satsangi:
    """Insert a new satsangi into the database and return it."""
    satsangi = Satsangi(**data.model_dump())
    values = [getattr(satsangi, f) for f in _INSERT_FIELDS]

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(_INSERT_SQL, values)
            row = cur.fetchone()
        conn.commit()
        return _row_to_satsangi(row)


def search_satsangis(query: str) -> tuple[list[Satsangi], int]:
    """Search satsangis using ILIKE across multiple fields. Returns (results, total_count)."""
    if not query.strip():
        return get_all_satsangis()

    pattern = f"%{query.strip()}%"
    params = [pattern] * 12

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(_SEARCH_SQL, params)
            rows = cur.fetchall()
        results = [_row_to_satsangi(row) for row in rows]
        return results, len(results)


def get_all_satsangis(limit: int = 0, offset: int = 0) -> tuple[list[Satsangi], int]:
    """Return satsangis, newest first. Returns (results, total_count)."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(_COUNT_SQL)
            total = cur.fetchone()["count"]

            sql = _LIST_SQL
            params: list[Any] = []
            if limit > 0:
                sql += " LIMIT %s"
                params.append(limit)
            if offset > 0:
                sql += " OFFSET %s"
                params.append(offset)

            cur.execute(sql, params)
            rows = cur.fetchall()
        return [_row_to_satsangi(row) for row in rows], total
