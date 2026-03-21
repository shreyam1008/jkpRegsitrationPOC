"""PostgreSQL-backed storage for devotee + visit records."""

import psycopg2.extras
from app.db import get_connection
from app.models import Devotee, DevoteeCreate, Visit, VisitCreate

# ─── Column lists ───

_DEVOTEE_INSERT = [
    "satsangi_id", "first_name", "last_name", "phone_number", "email",
    "gender", "date_of_birth", "age", "nationality", "special_category",
    "nick_name", "pan",
    "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country",
    "country", "address", "city", "district", "state", "pincode",
    "emergency_contact", "introducer", "introduced_by", "ex_center_satsangi_id",
    "print_on_card", "has_room_in_ashram", "banned", "first_timer",
    "date_of_first_visit", "notes",
]

_DEVOTEE_ALL = ["id", "satsangi_id", "created_at", "updated_at"] + [
    c for c in _DEVOTEE_INSERT if c != "satsangi_id"
]

_VISIT_INSERT = [
    "devotee_id", "location", "arrival_date", "departure_date", "purpose", "notes",
]
_VISIT_ALL = ["id"] + _VISIT_INSERT + ["created_at"]


def _ts(row: dict) -> dict:
    """Convert timestamp fields to ISO strings."""
    d = dict(row)
    for key in ("created_at", "updated_at"):
        if d.get(key):
            d[key] = d[key].isoformat()
    # Convert date fields to string
    for key in ("date_of_birth", "id_expiry_date", "date_of_first_visit",
                "arrival_date", "departure_date"):
        if d.get(key):
            d[key] = str(d[key])
    return d


# ─── Devotees ───

def create_devotee(data: DevoteeCreate) -> Devotee:
    from uuid import uuid4
    dump = data.model_dump()
    dump["satsangi_id"] = uuid4().hex[:8].upper()
    cols = ", ".join(_DEVOTEE_INSERT)
    phs = ", ".join(["%s"] * len(_DEVOTEE_INSERT))
    vals = [dump.get(f) for f in _DEVOTEE_INSERT]
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"INSERT INTO devotees ({cols}) VALUES ({phs}) RETURNING {', '.join(_DEVOTEE_ALL)}",
                vals,
            )
            row = cur.fetchone()
        conn.commit()
        return Devotee(**_ts(row))
    finally:
        conn.close()


def get_devotee_by_satsangi_id(satsangi_id: str) -> Devotee | None:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT {', '.join(_DEVOTEE_ALL)} FROM devotees WHERE satsangi_id = %s",
                (satsangi_id,),
            )
            row = cur.fetchone()
        return Devotee(**_ts(row)) if row else None
    finally:
        conn.close()


def search_devotees(query: str) -> list[Devotee]:
    if not query.strip():
        return get_all_devotees()
    pattern = f"%{query.strip()}%"
    sql = f"""
        SELECT {', '.join(_DEVOTEE_ALL)} FROM devotees
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
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, [pattern] * 12)
            rows = cur.fetchall()
        return [Devotee(**_ts(r)) for r in rows]
    finally:
        conn.close()


def get_all_devotees() -> list[Devotee]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT {', '.join(_DEVOTEE_ALL)} FROM devotees ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
        return [Devotee(**_ts(r)) for r in rows]
    finally:
        conn.close()


# ─── Visits ───

def create_visit(data: VisitCreate) -> Visit:
    cols = ", ".join(_VISIT_INSERT)
    phs = ", ".join(["%s"] * len(_VISIT_INSERT))
    vals = [getattr(data, f) for f in _VISIT_INSERT]
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"INSERT INTO visits ({cols}) VALUES ({phs}) RETURNING {', '.join(_VISIT_ALL)}",
                vals,
            )
            row = cur.fetchone()
        conn.commit()
        return Visit(**_ts(row))
    finally:
        conn.close()


def get_visits_for_devotee(devotee_id: int) -> list[Visit]:
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT {', '.join(_VISIT_ALL)} FROM visits "
                f"WHERE devotee_id = %s ORDER BY arrival_date DESC",
                (devotee_id,),
            )
            rows = cur.fetchall()
        return [Visit(**_ts(r)) for r in rows]
    finally:
        conn.close()
