/**
 * gRPC-web API layer.
 *
 * The browser talks REAL gRPC (protobuf over grpc-web) — no REST anywhere.
 * Communication path:
 *   Browser  --grpc-web-->  Proxy (:8080)  --gRPC-->  Server (:50051)  --SQL-->  PostgreSQL
 */

import { SatsangiServiceClient } from './generated/SatsangiServiceClientPb'
import {
  SatsangiCreate as SatsangiCreatePb,
  SatsangiMsg,
  SatsangiList,
  SearchRequest,
  Empty,
} from './generated/satsangi_pb'

// ---------------------------------------------------------------------------
// gRPC-web client — connects to the grpc-web proxy
// ---------------------------------------------------------------------------

const GRPC_WEB_URL = 'http://localhost:8080'
const client = new SatsangiServiceClient(GRPC_WEB_URL)

// ---------------------------------------------------------------------------
// TypeScript interfaces (used by UI components)
// ---------------------------------------------------------------------------

export interface SatsangiCreate {
  first_name: string
  last_name: string
  phone_number: string
  age?: number | null
  date_of_birth?: string | null
  pan?: string | null
  gender?: string | null
  special_category?: string | null
  nationality?: string
  govt_id_type?: string | null
  govt_id_number?: string | null
  id_expiry_date?: string | null
  id_issuing_country?: string | null
  nick_name?: string | null
  print_on_card?: boolean
  introducer?: string | null
  country?: string
  address?: string | null
  city?: string | null
  district?: string | null
  state?: string | null
  pincode?: string | null
  emergency_contact?: string | null
  ex_center_satsangi_id?: string | null
  introduced_by?: string | null
  has_room_in_ashram?: boolean
  email?: string | null
  banned?: boolean
  first_timer?: boolean
  date_of_first_visit?: string | null
  notes?: string | null
}

export interface Satsangi extends SatsangiCreate {
  satsangi_id: string
  created_at: string
}

// ---------------------------------------------------------------------------
// Converters: TS interface ↔ Protobuf message
// ---------------------------------------------------------------------------

function toProtoCreate(data: SatsangiCreate): SatsangiCreatePb {
  const msg = new SatsangiCreatePb()
  msg.setFirstName(data.first_name)
  msg.setLastName(data.last_name)
  msg.setPhoneNumber(data.phone_number)
  if (data.age != null) msg.setAge(data.age)
  if (data.date_of_birth) msg.setDateOfBirth(data.date_of_birth)
  if (data.pan) msg.setPan(data.pan)
  if (data.gender) msg.setGender(data.gender)
  if (data.special_category) msg.setSpecialCategory(data.special_category)
  msg.setNationality(data.nationality ?? 'Indian')
  if (data.govt_id_type) msg.setGovtIdType(data.govt_id_type)
  if (data.govt_id_number) msg.setGovtIdNumber(data.govt_id_number)
  if (data.id_expiry_date) msg.setIdExpiryDate(data.id_expiry_date)
  if (data.id_issuing_country) msg.setIdIssuingCountry(data.id_issuing_country)
  if (data.nick_name) msg.setNickName(data.nick_name)
  msg.setPrintOnCard(data.print_on_card ?? false)
  if (data.introducer) msg.setIntroducer(data.introducer)
  msg.setCountry(data.country ?? 'India')
  if (data.address) msg.setAddress(data.address)
  if (data.city) msg.setCity(data.city)
  if (data.district) msg.setDistrict(data.district)
  if (data.state) msg.setState(data.state)
  if (data.pincode) msg.setPincode(data.pincode)
  if (data.emergency_contact) msg.setEmergencyContact(data.emergency_contact)
  if (data.ex_center_satsangi_id) msg.setExCenterSatsangiId(data.ex_center_satsangi_id)
  if (data.introduced_by) msg.setIntroducedBy(data.introduced_by)
  msg.setHasRoomInAshram(data.has_room_in_ashram ?? false)
  if (data.email) msg.setEmail(data.email)
  msg.setBanned(data.banned ?? false)
  msg.setFirstTimer(data.first_timer ?? false)
  if (data.date_of_first_visit) msg.setDateOfFirstVisit(data.date_of_first_visit)
  if (data.notes) msg.setNotes(data.notes)
  return msg
}

function fromProtoSatsangi(msg: SatsangiMsg): Satsangi {
  return {
    satsangi_id: msg.getSatsangiId(),
    created_at: msg.getCreatedAt(),
    first_name: msg.getFirstName(),
    last_name: msg.getLastName(),
    phone_number: msg.getPhoneNumber(),
    age: msg.hasAge() ? msg.getAge() : null,
    date_of_birth: msg.getDateOfBirth() || null,
    pan: msg.getPan() || null,
    gender: msg.getGender() || null,
    special_category: msg.getSpecialCategory() || null,
    nationality: msg.getNationality() || 'Indian',
    govt_id_type: msg.getGovtIdType() || null,
    govt_id_number: msg.getGovtIdNumber() || null,
    id_expiry_date: msg.getIdExpiryDate() || null,
    id_issuing_country: msg.getIdIssuingCountry() || null,
    nick_name: msg.getNickName() || null,
    print_on_card: msg.getPrintOnCard(),
    introducer: msg.getIntroducer() || null,
    country: msg.getCountry() || 'India',
    address: msg.getAddress() || null,
    city: msg.getCity() || null,
    district: msg.getDistrict() || null,
    state: msg.getState() || null,
    pincode: msg.getPincode() || null,
    emergency_contact: msg.getEmergencyContact() || null,
    ex_center_satsangi_id: msg.getExCenterSatsangiId() || null,
    introduced_by: msg.getIntroducedBy() || null,
    has_room_in_ashram: msg.getHasRoomInAshram(),
    email: msg.getEmail() || null,
    banned: msg.getBanned(),
    first_timer: msg.getFirstTimer(),
    date_of_first_visit: msg.getDateOfFirstVisit() || null,
    notes: msg.getNotes() || null,
  }
}

// ---------------------------------------------------------------------------
// Public API (same function signatures as the REST version)
// ---------------------------------------------------------------------------

export async function createSatsangi(data: SatsangiCreate): Promise<Satsangi> {
  const req = toProtoCreate(data)
  const result: SatsangiMsg = await client.createSatsangi(req)
  return fromProtoSatsangi(result)
}

export async function searchSatsangis(query: string): Promise<Satsangi[]> {
  let result: SatsangiList
  if (query.trim()) {
    const req = new SearchRequest()
    req.setQuery(query)
    result = await client.searchSatsangis(req)
  } else {
    result = await client.listSatsangis(new Empty())
  }
  return result.getSatsangisList().map(fromProtoSatsangi)
}
