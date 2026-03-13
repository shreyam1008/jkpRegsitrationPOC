"""PostgreSQL-backed storage for satsangi records (REST version)."""

import psycopg2.extras
from app.db import get_connection
from app.models import Satsangi, SatsangiCreate

# All columns in insertion order (excluding created_at which is auto-generated)
_INSERT_FIELDS = [
    "satsangi_id", "first_name", "last_name", "phone_number", "age",
    "date_of_birth", "pan", "gender", "special_category", "nationality",
    "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country",
    "nick_name", "print_on_card", "introducer", "country", "address", "city",
    "district", "state", "pincode", "emergency_contact", "ex_center_satsangi_id",
    "introduced_by", "has_room_in_ashram", "email", "banned", "first_timer",
    "date_of_first_visit", "notes",
]

_ALL_FIELDS = [
    "satsangi_id", "created_at", "first_name", "last_name", "phone_number",
    "age", "date_of_birth", "pan", "gender", "special_category", "nationality",
    "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country",
    "nick_name", "print_on_card", "introducer", "country", "address", "city",
    "district", "state", "pincode", "emergency_contact", "ex_center_satsangi_id",
    "introduced_by", "has_room_in_ashram", "email", "banned", "first_timer",
    "date_of_first_visit", "notes",
]


def _row_to_satsangi(row: dict) -> Satsangi:
    """Convert a database row dict to a Satsangi model."""
    data = dict(row)
    # Convert timestamp to ISO string
    if data.get("created_at"):
        data["created_at"] = data["created_at"].isoformat()
    return Satsangi(**data)


def create_satsangi(data: SatsangiCreate) -> Satsangi:
    """Insert a new satsangi into the database and return it."""
    satsangi = Satsangi(**data.model_dump())
    placeholders = ", ".join(["%s"] * len(_INSERT_FIELDS))
    columns = ", ".join(_INSERT_FIELDS)
    values = [getattr(satsangi, f) for f in _INSERT_FIELDS]

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"INSERT INTO satsangis ({columns}) VALUES ({placeholders}) "
                f"RETURNING {', '.join(_ALL_FIELDS)}",
                values,
            )
            row = cur.fetchone()
        conn.commit()
        return _row_to_satsangi(row)
    finally:
        conn.close()


def search_satsangis(query: str) -> list[Satsangi]:
    """Search satsangis using ILIKE across multiple fields."""
    if not query.strip():
        return get_all_satsangis()

    pattern = f"%{query.strip()}%"
    sql = f"""
        SELECT {', '.join(_ALL_FIELDS)} FROM satsangis
        WHERE LOWER(first_name) LIKE LOWER(%s)
           OR LOWER(last_name) LIKE LOWER(%s)
           OR LOWER(first_name || ' ' || last_name) LIKE LOWER(%s)
           OR phone_number LIKE %s
           OR LOWER(satsangi_id) LIKE LOWER(%s)
           OR LOWER(COALESCE(email, '')) LIKE LOWER(%s)
           OR LOWER(COALESCE(pan, '')) LIKE LOWER(%s)
           OR LOWER(COALESCE(govt_id_number, '')) LIKE LOWER(%s)
           OR LOWER(COALESCE(nick_name, '')) LIKE LOWER(%s)
           OR LOWER(COALESCE(ex_center_satsangi_id, '')) LIKE LOWER(%s)
           OR LOWER(COALESCE(city, '')) LIKE LOWER(%s)
           OR COALESCE(pincode, '') LIKE %s
        ORDER BY created_at DESC
    """
    params = [pattern] * 12

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [_row_to_satsangi(row) for row in rows]
    finally:
        conn.close()


def get_all_satsangis() -> list[Satsangi]:
    """Return all satsangis, newest first."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT {', '.join(_ALL_FIELDS)} FROM satsangis ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
        return [_row_to_satsangi(row) for row in rows]
    finally:
        conn.close()
