from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime


class SatsangiCreate(BaseModel):
    first_name: str
    last_name: str
    phone_number: str
    age: int | None = None
    date_of_birth: str | None = None
    pan: str | None = None
    gender: str | None = None
    special_category: str | None = None
    nationality: str = "Indian"
    govt_id_type: str | None = None
    govt_id_number: str | None = None
    id_expiry_date: str | None = None
    id_issuing_country: str | None = None
    nick_name: str | None = None
    print_on_card: bool = False
    introducer: str | None = None
    country: str = "India"
    address: str | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    pincode: str | None = None
    emergency_contact: str | None = None
    ex_center_satsangi_id: str | None = None
    introduced_by: str | None = None
    has_room_in_ashram: bool = False
    email: str | None = None
    banned: bool = False
    first_timer: bool = False
    date_of_first_visit: str | None = None
    notes: str | None = None


class Satsangi(SatsangiCreate):
    satsangi_id: str = Field(default_factory=lambda: uuid4().hex[:8].upper())
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
