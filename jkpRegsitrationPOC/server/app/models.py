from pydantic import BaseModel, Field
from uuid import uuid4


# ─── Devotee ───

class DevoteeCreate(BaseModel):
    """Payload for creating a new devotee."""
    # Personal
    first_name: str
    last_name: str
    phone_number: str
    email: str | None = None
    gender: str | None = None
    date_of_birth: str | None = None
    age: int | None = None
    nationality: str = "Indian"
    special_category: str | None = None
    nick_name: str | None = None
    pan: str | None = None

    # Government ID
    govt_id_type: str | None = None
    govt_id_number: str | None = None
    id_expiry_date: str | None = None
    id_issuing_country: str | None = None

    # Address
    country: str = "India"
    address: str | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    pincode: str | None = None

    # Other
    emergency_contact: str | None = None
    introducer: str | None = None
    introduced_by: str | None = None
    ex_center_satsangi_id: str | None = None
    print_on_card: bool = False
    has_room_in_ashram: bool = False
    banned: bool = False
    first_timer: bool = False
    date_of_first_visit: str | None = None
    notes: str | None = None


class Devotee(DevoteeCreate):
    """Full devotee record returned from DB."""
    id: int
    satsangi_id: str = Field(default_factory=lambda: uuid4().hex[:8].upper())
    created_at: str = ""
    updated_at: str = ""


# ─── Visit ───

class VisitCreate(BaseModel):
    """Payload for logging a new visit."""
    devotee_id: int
    location: str | None = None
    arrival_date: str | None = None
    departure_date: str | None = None
    purpose: str | None = None
    notes: str | None = None


class Visit(VisitCreate):
    """Full visit record returned from DB."""
    id: int
    created_at: str = ""
