from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SatsangiCreate(_message.Message):
    __slots__ = ("first_name", "last_name", "phone_number", "age", "date_of_birth", "pan", "gender", "special_category", "nationality", "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country", "nick_name", "print_on_card", "introducer", "country", "address", "city", "district", "state", "pincode", "emergency_contact", "ex_center_satsangi_id", "introduced_by", "has_room_in_ashram", "email", "banned", "first_timer", "date_of_first_visit", "notes")
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    AGE_FIELD_NUMBER: _ClassVar[int]
    DATE_OF_BIRTH_FIELD_NUMBER: _ClassVar[int]
    PAN_FIELD_NUMBER: _ClassVar[int]
    GENDER_FIELD_NUMBER: _ClassVar[int]
    SPECIAL_CATEGORY_FIELD_NUMBER: _ClassVar[int]
    NATIONALITY_FIELD_NUMBER: _ClassVar[int]
    GOVT_ID_TYPE_FIELD_NUMBER: _ClassVar[int]
    GOVT_ID_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ID_EXPIRY_DATE_FIELD_NUMBER: _ClassVar[int]
    ID_ISSUING_COUNTRY_FIELD_NUMBER: _ClassVar[int]
    NICK_NAME_FIELD_NUMBER: _ClassVar[int]
    PRINT_ON_CARD_FIELD_NUMBER: _ClassVar[int]
    INTRODUCER_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    DISTRICT_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    PINCODE_FIELD_NUMBER: _ClassVar[int]
    EMERGENCY_CONTACT_FIELD_NUMBER: _ClassVar[int]
    EX_CENTER_SATSANGI_ID_FIELD_NUMBER: _ClassVar[int]
    INTRODUCED_BY_FIELD_NUMBER: _ClassVar[int]
    HAS_ROOM_IN_ASHRAM_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    BANNED_FIELD_NUMBER: _ClassVar[int]
    FIRST_TIMER_FIELD_NUMBER: _ClassVar[int]
    DATE_OF_FIRST_VISIT_FIELD_NUMBER: _ClassVar[int]
    NOTES_FIELD_NUMBER: _ClassVar[int]
    first_name: str
    last_name: str
    phone_number: str
    age: int
    date_of_birth: str
    pan: str
    gender: str
    special_category: str
    nationality: str
    govt_id_type: str
    govt_id_number: str
    id_expiry_date: str
    id_issuing_country: str
    nick_name: str
    print_on_card: bool
    introducer: str
    country: str
    address: str
    city: str
    district: str
    state: str
    pincode: str
    emergency_contact: str
    ex_center_satsangi_id: str
    introduced_by: str
    has_room_in_ashram: bool
    email: str
    banned: bool
    first_timer: bool
    date_of_first_visit: str
    notes: str
    def __init__(self, first_name: _Optional[str] = ..., last_name: _Optional[str] = ..., phone_number: _Optional[str] = ..., age: _Optional[int] = ..., date_of_birth: _Optional[str] = ..., pan: _Optional[str] = ..., gender: _Optional[str] = ..., special_category: _Optional[str] = ..., nationality: _Optional[str] = ..., govt_id_type: _Optional[str] = ..., govt_id_number: _Optional[str] = ..., id_expiry_date: _Optional[str] = ..., id_issuing_country: _Optional[str] = ..., nick_name: _Optional[str] = ..., print_on_card: bool = ..., introducer: _Optional[str] = ..., country: _Optional[str] = ..., address: _Optional[str] = ..., city: _Optional[str] = ..., district: _Optional[str] = ..., state: _Optional[str] = ..., pincode: _Optional[str] = ..., emergency_contact: _Optional[str] = ..., ex_center_satsangi_id: _Optional[str] = ..., introduced_by: _Optional[str] = ..., has_room_in_ashram: bool = ..., email: _Optional[str] = ..., banned: bool = ..., first_timer: bool = ..., date_of_first_visit: _Optional[str] = ..., notes: _Optional[str] = ...) -> None: ...

class Satsangi(_message.Message):
    __slots__ = ("satsangi_id", "created_at", "first_name", "last_name", "phone_number", "age", "date_of_birth", "pan", "gender", "special_category", "nationality", "govt_id_type", "govt_id_number", "id_expiry_date", "id_issuing_country", "nick_name", "print_on_card", "introducer", "country", "address", "city", "district", "state", "pincode", "emergency_contact", "ex_center_satsangi_id", "introduced_by", "has_room_in_ashram", "email", "banned", "first_timer", "date_of_first_visit", "notes")
    SATSANGI_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    AGE_FIELD_NUMBER: _ClassVar[int]
    DATE_OF_BIRTH_FIELD_NUMBER: _ClassVar[int]
    PAN_FIELD_NUMBER: _ClassVar[int]
    GENDER_FIELD_NUMBER: _ClassVar[int]
    SPECIAL_CATEGORY_FIELD_NUMBER: _ClassVar[int]
    NATIONALITY_FIELD_NUMBER: _ClassVar[int]
    GOVT_ID_TYPE_FIELD_NUMBER: _ClassVar[int]
    GOVT_ID_NUMBER_FIELD_NUMBER: _ClassVar[int]
    ID_EXPIRY_DATE_FIELD_NUMBER: _ClassVar[int]
    ID_ISSUING_COUNTRY_FIELD_NUMBER: _ClassVar[int]
    NICK_NAME_FIELD_NUMBER: _ClassVar[int]
    PRINT_ON_CARD_FIELD_NUMBER: _ClassVar[int]
    INTRODUCER_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    DISTRICT_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    PINCODE_FIELD_NUMBER: _ClassVar[int]
    EMERGENCY_CONTACT_FIELD_NUMBER: _ClassVar[int]
    EX_CENTER_SATSANGI_ID_FIELD_NUMBER: _ClassVar[int]
    INTRODUCED_BY_FIELD_NUMBER: _ClassVar[int]
    HAS_ROOM_IN_ASHRAM_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    BANNED_FIELD_NUMBER: _ClassVar[int]
    FIRST_TIMER_FIELD_NUMBER: _ClassVar[int]
    DATE_OF_FIRST_VISIT_FIELD_NUMBER: _ClassVar[int]
    NOTES_FIELD_NUMBER: _ClassVar[int]
    satsangi_id: str
    created_at: str
    first_name: str
    last_name: str
    phone_number: str
    age: int
    date_of_birth: str
    pan: str
    gender: str
    special_category: str
    nationality: str
    govt_id_type: str
    govt_id_number: str
    id_expiry_date: str
    id_issuing_country: str
    nick_name: str
    print_on_card: bool
    introducer: str
    country: str
    address: str
    city: str
    district: str
    state: str
    pincode: str
    emergency_contact: str
    ex_center_satsangi_id: str
    introduced_by: str
    has_room_in_ashram: bool
    email: str
    banned: bool
    first_timer: bool
    date_of_first_visit: str
    notes: str
    def __init__(self, satsangi_id: _Optional[str] = ..., created_at: _Optional[str] = ..., first_name: _Optional[str] = ..., last_name: _Optional[str] = ..., phone_number: _Optional[str] = ..., age: _Optional[int] = ..., date_of_birth: _Optional[str] = ..., pan: _Optional[str] = ..., gender: _Optional[str] = ..., special_category: _Optional[str] = ..., nationality: _Optional[str] = ..., govt_id_type: _Optional[str] = ..., govt_id_number: _Optional[str] = ..., id_expiry_date: _Optional[str] = ..., id_issuing_country: _Optional[str] = ..., nick_name: _Optional[str] = ..., print_on_card: bool = ..., introducer: _Optional[str] = ..., country: _Optional[str] = ..., address: _Optional[str] = ..., city: _Optional[str] = ..., district: _Optional[str] = ..., state: _Optional[str] = ..., pincode: _Optional[str] = ..., emergency_contact: _Optional[str] = ..., ex_center_satsangi_id: _Optional[str] = ..., introduced_by: _Optional[str] = ..., has_room_in_ashram: bool = ..., email: _Optional[str] = ..., banned: bool = ..., first_timer: bool = ..., date_of_first_visit: _Optional[str] = ..., notes: _Optional[str] = ...) -> None: ...

class SearchRequest(_message.Message):
    __slots__ = ("query",)
    QUERY_FIELD_NUMBER: _ClassVar[int]
    query: str
    def __init__(self, query: _Optional[str] = ...) -> None: ...

class SatsangiList(_message.Message):
    __slots__ = ("satsangis",)
    SATSANGIS_FIELD_NUMBER: _ClassVar[int]
    satsangis: _containers.RepeatedCompositeFieldContainer[Satsangi]
    def __init__(self, satsangis: _Optional[_Iterable[_Union[Satsangi, _Mapping]]] = ...) -> None: ...

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
