import json
from pathlib import Path
from app.models import Satsangi, SatsangiCreate

DATA_FILE = Path(__file__).parent.parent / "data" / "satsangis.json"


def _ensure_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]")


def _read_all() -> list[Satsangi]:
    _ensure_file()
    raw = json.loads(DATA_FILE.read_text())
    return [Satsangi(**item) for item in raw]


def _write_all(items: list[Satsangi]) -> None:
    _ensure_file()
    DATA_FILE.write_text(json.dumps([item.model_dump() for item in items], indent=2))


def create_satsangi(data: SatsangiCreate) -> Satsangi:
    items = _read_all()
    satsangi = Satsangi(**data.model_dump())
    items.append(satsangi)
    _write_all(items)
    return satsangi


def _match(value: str | None, q: str) -> bool:
    return bool(value and q in value.lower())


def search_satsangis(query: str) -> list[Satsangi]:
    items = _read_all()
    if not query.strip():
        return items
    q = query.lower().strip()
    return [
        s
        for s in items
        if q in s.first_name.lower()
        or q in s.last_name.lower()
        or q in f"{s.first_name} {s.last_name}".lower()
        or q in s.phone_number.lower()
        or q in s.satsangi_id.lower()
        or _match(s.email, q)
        or _match(s.pan, q)
        or _match(s.govt_id_number, q)
        or _match(s.nick_name, q)
        or _match(s.ex_center_satsangi_id, q)
        or _match(s.city, q)
        or _match(s.pincode, q)
    ]


def get_all_satsangis() -> list[Satsangi]:
    return _read_all()
