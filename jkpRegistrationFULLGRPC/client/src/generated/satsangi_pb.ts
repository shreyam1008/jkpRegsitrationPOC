/**
 * Hand-written protobuf message classes for grpc-web client.
 *
 * These correspond 1:1 with the messages in proto/satsangi.proto.
 * Uses google-protobuf's BinaryWriter/BinaryReader for wire-format
 * serialization so the browser speaks real protobuf over grpc-web.
 *
 * NOTE: google-protobuf's field access methods (getField, setField,
 * getFieldWithDefault, etc.) are STATIC on jspb.Message, not instance
 * methods.  Every class must call jspb.Message.initialize() in its
 * constructor.
 */

import * as jspb from 'google-protobuf'

// Shorter aliases for the verbose static helpers
const _get    = jspb.Message.getFieldWithDefault
const _getOpt = jspb.Message.getField
const _set    = jspb.Message.setField
const _init   = jspb.Message.initialize

// ---------------------------------------------------------------------------
// SatsangiCreate message  (proto field numbers 1-31)
// ---------------------------------------------------------------------------

export class SatsangiCreate extends jspb.Message {
  constructor() { super(); _init(this, [], 0, -1, null, null) }

  getFirstName(): string { return _get(this, 1, '') as string }
  setFirstName(v: string) { _set(this, 1, v) }

  getLastName(): string { return _get(this, 2, '') as string }
  setLastName(v: string) { _set(this, 2, v) }

  getPhoneNumber(): string { return _get(this, 3, '') as string }
  setPhoneNumber(v: string) { _set(this, 3, v) }

  getAge(): number | undefined { return _getOpt(this, 4) as number | undefined }
  setAge(v: number) { _set(this, 4, v) }
  hasAge(): boolean { return _getOpt(this, 4) != null }

  getDateOfBirth(): string | undefined { return _getOpt(this, 5) as string | undefined }
  setDateOfBirth(v: string) { _set(this, 5, v) }
  hasDateOfBirth(): boolean { return _getOpt(this, 5) != null }

  getPan(): string | undefined { return _getOpt(this, 6) as string | undefined }
  setPan(v: string) { _set(this, 6, v) }
  hasPan(): boolean { return _getOpt(this, 6) != null }

  getGender(): string | undefined { return _getOpt(this, 7) as string | undefined }
  setGender(v: string) { _set(this, 7, v) }
  hasGender(): boolean { return _getOpt(this, 7) != null }

  getSpecialCategory(): string | undefined { return _getOpt(this, 8) as string | undefined }
  setSpecialCategory(v: string) { _set(this, 8, v) }
  hasSpecialCategory(): boolean { return _getOpt(this, 8) != null }

  getNationality(): string { return _get(this, 9, 'Indian') as string }
  setNationality(v: string) { _set(this, 9, v) }

  getGovtIdType(): string | undefined { return _getOpt(this, 10) as string | undefined }
  setGovtIdType(v: string) { _set(this, 10, v) }
  hasGovtIdType(): boolean { return _getOpt(this, 10) != null }

  getGovtIdNumber(): string | undefined { return _getOpt(this, 11) as string | undefined }
  setGovtIdNumber(v: string) { _set(this, 11, v) }
  hasGovtIdNumber(): boolean { return _getOpt(this, 11) != null }

  getIdExpiryDate(): string | undefined { return _getOpt(this, 12) as string | undefined }
  setIdExpiryDate(v: string) { _set(this, 12, v) }
  hasIdExpiryDate(): boolean { return _getOpt(this, 12) != null }

  getIdIssuingCountry(): string | undefined { return _getOpt(this, 13) as string | undefined }
  setIdIssuingCountry(v: string) { _set(this, 13, v) }
  hasIdIssuingCountry(): boolean { return _getOpt(this, 13) != null }

  getNickName(): string | undefined { return _getOpt(this, 14) as string | undefined }
  setNickName(v: string) { _set(this, 14, v) }
  hasNickName(): boolean { return _getOpt(this, 14) != null }

  getPrintOnCard(): boolean { return _get(this, 15, false) as boolean }
  setPrintOnCard(v: boolean) { _set(this, 15, v) }

  getIntroducer(): string | undefined { return _getOpt(this, 16) as string | undefined }
  setIntroducer(v: string) { _set(this, 16, v) }
  hasIntroducer(): boolean { return _getOpt(this, 16) != null }

  getCountry(): string { return _get(this, 17, 'India') as string }
  setCountry(v: string) { _set(this, 17, v) }

  getAddress(): string | undefined { return _getOpt(this, 18) as string | undefined }
  setAddress(v: string) { _set(this, 18, v) }
  hasAddress(): boolean { return _getOpt(this, 18) != null }

  getCity(): string | undefined { return _getOpt(this, 19) as string | undefined }
  setCity(v: string) { _set(this, 19, v) }
  hasCity(): boolean { return _getOpt(this, 19) != null }

  getDistrict(): string | undefined { return _getOpt(this, 20) as string | undefined }
  setDistrict(v: string) { _set(this, 20, v) }
  hasDistrict(): boolean { return _getOpt(this, 20) != null }

  getState(): string | undefined { return _getOpt(this, 21) as string | undefined }
  setState(v: string) { _set(this, 21, v) }
  hasState(): boolean { return _getOpt(this, 21) != null }

  getPincode(): string | undefined { return _getOpt(this, 22) as string | undefined }
  setPincode(v: string) { _set(this, 22, v) }
  hasPincode(): boolean { return _getOpt(this, 22) != null }

  getEmergencyContact(): string | undefined { return _getOpt(this, 23) as string | undefined }
  setEmergencyContact(v: string) { _set(this, 23, v) }
  hasEmergencyContact(): boolean { return _getOpt(this, 23) != null }

  getExCenterSatsangiId(): string | undefined { return _getOpt(this, 24) as string | undefined }
  setExCenterSatsangiId(v: string) { _set(this, 24, v) }
  hasExCenterSatsangiId(): boolean { return _getOpt(this, 24) != null }

  getIntroducedBy(): string | undefined { return _getOpt(this, 25) as string | undefined }
  setIntroducedBy(v: string) { _set(this, 25, v) }
  hasIntroducedBy(): boolean { return _getOpt(this, 25) != null }

  getHasRoomInAshram(): boolean { return _get(this, 26, false) as boolean }
  setHasRoomInAshram(v: boolean) { _set(this, 26, v) }

  getEmail(): string | undefined { return _getOpt(this, 27) as string | undefined }
  setEmail(v: string) { _set(this, 27, v) }
  hasEmail(): boolean { return _getOpt(this, 27) != null }

  getBanned(): boolean { return _get(this, 28, false) as boolean }
  setBanned(v: boolean) { _set(this, 28, v) }

  getFirstTimer(): boolean { return _get(this, 29, false) as boolean }
  setFirstTimer(v: boolean) { _set(this, 29, v) }

  getDateOfFirstVisit(): string | undefined { return _getOpt(this, 30) as string | undefined }
  setDateOfFirstVisit(v: string) { _set(this, 30, v) }
  hasDateOfFirstVisit(): boolean { return _getOpt(this, 30) != null }

  getNotes(): string | undefined { return _getOpt(this, 31) as string | undefined }
  setNotes(v: string) { _set(this, 31, v) }
  hasNotes(): boolean { return _getOpt(this, 31) != null }

  serializeBinary(): Uint8Array {
    const writer = new jspb.BinaryWriter()
    SatsangiCreate.serializeBinaryToWriter(this, writer)
    return writer.getResultBuffer()
  }

  static serializeBinaryToWriter(msg: SatsangiCreate, writer: jspb.BinaryWriter) {
    const f1 = msg.getFirstName()
    if (f1.length > 0) writer.writeString(1, f1)
    const f2 = msg.getLastName()
    if (f2.length > 0) writer.writeString(2, f2)
    const f3 = msg.getPhoneNumber()
    if (f3.length > 0) writer.writeString(3, f3)
    if (msg.hasAge()) writer.writeInt32(4, msg.getAge()!)
    if (msg.hasDateOfBirth()) writer.writeString(5, msg.getDateOfBirth()!)
    if (msg.hasPan()) writer.writeString(6, msg.getPan()!)
    if (msg.hasGender()) writer.writeString(7, msg.getGender()!)
    if (msg.hasSpecialCategory()) writer.writeString(8, msg.getSpecialCategory()!)
    const f9 = msg.getNationality()
    if (f9.length > 0) writer.writeString(9, f9)
    if (msg.hasGovtIdType()) writer.writeString(10, msg.getGovtIdType()!)
    if (msg.hasGovtIdNumber()) writer.writeString(11, msg.getGovtIdNumber()!)
    if (msg.hasIdExpiryDate()) writer.writeString(12, msg.getIdExpiryDate()!)
    if (msg.hasIdIssuingCountry()) writer.writeString(13, msg.getIdIssuingCountry()!)
    if (msg.hasNickName()) writer.writeString(14, msg.getNickName()!)
    if (msg.getPrintOnCard()) writer.writeBool(15, true)
    if (msg.hasIntroducer()) writer.writeString(16, msg.getIntroducer()!)
    const f17 = msg.getCountry()
    if (f17.length > 0) writer.writeString(17, f17)
    if (msg.hasAddress()) writer.writeString(18, msg.getAddress()!)
    if (msg.hasCity()) writer.writeString(19, msg.getCity()!)
    if (msg.hasDistrict()) writer.writeString(20, msg.getDistrict()!)
    if (msg.hasState()) writer.writeString(21, msg.getState()!)
    if (msg.hasPincode()) writer.writeString(22, msg.getPincode()!)
    if (msg.hasEmergencyContact()) writer.writeString(23, msg.getEmergencyContact()!)
    if (msg.hasExCenterSatsangiId()) writer.writeString(24, msg.getExCenterSatsangiId()!)
    if (msg.hasIntroducedBy()) writer.writeString(25, msg.getIntroducedBy()!)
    if (msg.getHasRoomInAshram()) writer.writeBool(26, true)
    if (msg.hasEmail()) writer.writeString(27, msg.getEmail()!)
    if (msg.getBanned()) writer.writeBool(28, true)
    if (msg.getFirstTimer()) writer.writeBool(29, true)
    if (msg.hasDateOfFirstVisit()) writer.writeString(30, msg.getDateOfFirstVisit()!)
    if (msg.hasNotes()) writer.writeString(31, msg.getNotes()!)
  }

  static deserializeBinary(bytes: Uint8Array): SatsangiCreate {
    const msg = new SatsangiCreate()
    const reader = new jspb.BinaryReader(bytes)
    while (reader.nextField()) {
      if (reader.isEndGroup()) break
      switch (reader.getFieldNumber()) {
        case 1: msg.setFirstName(reader.readString()); break
        case 2: msg.setLastName(reader.readString()); break
        case 3: msg.setPhoneNumber(reader.readString()); break
        case 4: msg.setAge(reader.readInt32()); break
        case 5: msg.setDateOfBirth(reader.readString()); break
        case 6: msg.setPan(reader.readString()); break
        case 7: msg.setGender(reader.readString()); break
        case 8: msg.setSpecialCategory(reader.readString()); break
        case 9: msg.setNationality(reader.readString()); break
        case 10: msg.setGovtIdType(reader.readString()); break
        case 11: msg.setGovtIdNumber(reader.readString()); break
        case 12: msg.setIdExpiryDate(reader.readString()); break
        case 13: msg.setIdIssuingCountry(reader.readString()); break
        case 14: msg.setNickName(reader.readString()); break
        case 15: msg.setPrintOnCard(reader.readBool()); break
        case 16: msg.setIntroducer(reader.readString()); break
        case 17: msg.setCountry(reader.readString()); break
        case 18: msg.setAddress(reader.readString()); break
        case 19: msg.setCity(reader.readString()); break
        case 20: msg.setDistrict(reader.readString()); break
        case 21: msg.setState(reader.readString()); break
        case 22: msg.setPincode(reader.readString()); break
        case 23: msg.setEmergencyContact(reader.readString()); break
        case 24: msg.setExCenterSatsangiId(reader.readString()); break
        case 25: msg.setIntroducedBy(reader.readString()); break
        case 26: msg.setHasRoomInAshram(reader.readBool()); break
        case 27: msg.setEmail(reader.readString()); break
        case 28: msg.setBanned(reader.readBool()); break
        case 29: msg.setFirstTimer(reader.readBool()); break
        case 30: msg.setDateOfFirstVisit(reader.readString()); break
        case 31: msg.setNotes(reader.readString()); break
        default: reader.skipField(); break
      }
    }
    return msg
  }
}

// ---------------------------------------------------------------------------
// Satsangi message (proto field numbers 1-33)
// ---------------------------------------------------------------------------

export class SatsangiMsg extends jspb.Message {
  constructor() { super(); _init(this, [], 0, -1, null, null) }

  getSatsangiId(): string { return _get(this, 1, '') as string }
  setSatsangiId(v: string) { _set(this, 1, v) }

  getCreatedAt(): string { return _get(this, 2, '') as string }
  setCreatedAt(v: string) { _set(this, 2, v) }

  getFirstName(): string { return _get(this, 3, '') as string }
  setFirstName(v: string) { _set(this, 3, v) }

  getLastName(): string { return _get(this, 4, '') as string }
  setLastName(v: string) { _set(this, 4, v) }

  getPhoneNumber(): string { return _get(this, 5, '') as string }
  setPhoneNumber(v: string) { _set(this, 5, v) }

  getAge(): number | undefined { return _getOpt(this, 6) as number | undefined }
  setAge(v: number) { _set(this, 6, v) }
  hasAge(): boolean { return _getOpt(this, 6) != null }

  getDateOfBirth(): string | undefined { return _getOpt(this, 7) as string | undefined }
  setDateOfBirth(v: string) { _set(this, 7, v) }

  getPan(): string | undefined { return _getOpt(this, 8) as string | undefined }
  setPan(v: string) { _set(this, 8, v) }

  getGender(): string | undefined { return _getOpt(this, 9) as string | undefined }
  setGender(v: string) { _set(this, 9, v) }

  getSpecialCategory(): string | undefined { return _getOpt(this, 10) as string | undefined }
  setSpecialCategory(v: string) { _set(this, 10, v) }

  getNationality(): string { return _get(this, 11, '') as string }
  setNationality(v: string) { _set(this, 11, v) }

  getGovtIdType(): string | undefined { return _getOpt(this, 12) as string | undefined }
  setGovtIdType(v: string) { _set(this, 12, v) }

  getGovtIdNumber(): string | undefined { return _getOpt(this, 13) as string | undefined }
  setGovtIdNumber(v: string) { _set(this, 13, v) }

  getIdExpiryDate(): string | undefined { return _getOpt(this, 14) as string | undefined }
  setIdExpiryDate(v: string) { _set(this, 14, v) }

  getIdIssuingCountry(): string | undefined { return _getOpt(this, 15) as string | undefined }
  setIdIssuingCountry(v: string) { _set(this, 15, v) }

  getNickName(): string | undefined { return _getOpt(this, 16) as string | undefined }
  setNickName(v: string) { _set(this, 16, v) }

  getPrintOnCard(): boolean { return _get(this, 17, false) as boolean }
  setPrintOnCard(v: boolean) { _set(this, 17, v) }

  getIntroducer(): string | undefined { return _getOpt(this, 18) as string | undefined }
  setIntroducer(v: string) { _set(this, 18, v) }

  getCountry(): string { return _get(this, 19, '') as string }
  setCountry(v: string) { _set(this, 19, v) }

  getAddress(): string | undefined { return _getOpt(this, 20) as string | undefined }
  setAddress(v: string) { _set(this, 20, v) }

  getCity(): string | undefined { return _getOpt(this, 21) as string | undefined }
  setCity(v: string) { _set(this, 21, v) }

  getDistrict(): string | undefined { return _getOpt(this, 22) as string | undefined }
  setDistrict(v: string) { _set(this, 22, v) }

  getState(): string | undefined { return _getOpt(this, 23) as string | undefined }
  setState(v: string) { _set(this, 23, v) }

  getPincode(): string | undefined { return _getOpt(this, 24) as string | undefined }
  setPincode(v: string) { _set(this, 24, v) }

  getEmergencyContact(): string | undefined { return _getOpt(this, 25) as string | undefined }
  setEmergencyContact(v: string) { _set(this, 25, v) }

  getExCenterSatsangiId(): string | undefined { return _getOpt(this, 26) as string | undefined }
  setExCenterSatsangiId(v: string) { _set(this, 26, v) }

  getIntroducedBy(): string | undefined { return _getOpt(this, 27) as string | undefined }
  setIntroducedBy(v: string) { _set(this, 27, v) }

  getHasRoomInAshram(): boolean { return _get(this, 28, false) as boolean }
  setHasRoomInAshram(v: boolean) { _set(this, 28, v) }

  getEmail(): string | undefined { return _getOpt(this, 29) as string | undefined }
  setEmail(v: string) { _set(this, 29, v) }

  getBanned(): boolean { return _get(this, 30, false) as boolean }
  setBanned(v: boolean) { _set(this, 30, v) }

  getFirstTimer(): boolean { return _get(this, 31, false) as boolean }
  setFirstTimer(v: boolean) { _set(this, 31, v) }

  getDateOfFirstVisit(): string | undefined { return _getOpt(this, 32) as string | undefined }
  setDateOfFirstVisit(v: string) { _set(this, 32, v) }

  getNotes(): string | undefined { return _getOpt(this, 33) as string | undefined }
  setNotes(v: string) { _set(this, 33, v) }

  serializeBinary(): Uint8Array {
    const writer = new jspb.BinaryWriter()
    SatsangiMsg.serializeBinaryToWriter(this, writer)
    return writer.getResultBuffer()
  }

  static serializeBinaryToWriter(msg: SatsangiMsg, writer: jspb.BinaryWriter) {
    const f1 = msg.getSatsangiId(); if (f1.length > 0) writer.writeString(1, f1)
    const f2 = msg.getCreatedAt(); if (f2.length > 0) writer.writeString(2, f2)
    const f3 = msg.getFirstName(); if (f3.length > 0) writer.writeString(3, f3)
    const f4 = msg.getLastName(); if (f4.length > 0) writer.writeString(4, f4)
    const f5 = msg.getPhoneNumber(); if (f5.length > 0) writer.writeString(5, f5)
    if (msg.hasAge()) writer.writeInt32(6, msg.getAge()!)
    const f7 = msg.getDateOfBirth(); if (f7) writer.writeString(7, f7)
    const f8 = msg.getPan(); if (f8) writer.writeString(8, f8)
    const f9 = msg.getGender(); if (f9) writer.writeString(9, f9)
    const f10 = msg.getSpecialCategory(); if (f10) writer.writeString(10, f10)
    const f11 = msg.getNationality(); if (f11.length > 0) writer.writeString(11, f11)
    const f12 = msg.getGovtIdType(); if (f12) writer.writeString(12, f12)
    const f13 = msg.getGovtIdNumber(); if (f13) writer.writeString(13, f13)
    const f14 = msg.getIdExpiryDate(); if (f14) writer.writeString(14, f14)
    const f15 = msg.getIdIssuingCountry(); if (f15) writer.writeString(15, f15)
    const f16 = msg.getNickName(); if (f16) writer.writeString(16, f16)
    if (msg.getPrintOnCard()) writer.writeBool(17, true)
    const f18 = msg.getIntroducer(); if (f18) writer.writeString(18, f18)
    const f19 = msg.getCountry(); if (f19.length > 0) writer.writeString(19, f19)
    const f20 = msg.getAddress(); if (f20) writer.writeString(20, f20)
    const f21 = msg.getCity(); if (f21) writer.writeString(21, f21)
    const f22 = msg.getDistrict(); if (f22) writer.writeString(22, f22)
    const f23 = msg.getState(); if (f23) writer.writeString(23, f23)
    const f24 = msg.getPincode(); if (f24) writer.writeString(24, f24)
    const f25 = msg.getEmergencyContact(); if (f25) writer.writeString(25, f25)
    const f26 = msg.getExCenterSatsangiId(); if (f26) writer.writeString(26, f26)
    const f27 = msg.getIntroducedBy(); if (f27) writer.writeString(27, f27)
    if (msg.getHasRoomInAshram()) writer.writeBool(28, true)
    const f29 = msg.getEmail(); if (f29) writer.writeString(29, f29)
    if (msg.getBanned()) writer.writeBool(30, true)
    if (msg.getFirstTimer()) writer.writeBool(31, true)
    const f32 = msg.getDateOfFirstVisit(); if (f32) writer.writeString(32, f32)
    const f33 = msg.getNotes(); if (f33) writer.writeString(33, f33)
  }

  static deserializeBinary(bytes: Uint8Array): SatsangiMsg {
    const msg = new SatsangiMsg()
    const reader = new jspb.BinaryReader(bytes)
    while (reader.nextField()) {
      if (reader.isEndGroup()) break
      switch (reader.getFieldNumber()) {
        case 1: msg.setSatsangiId(reader.readString()); break
        case 2: msg.setCreatedAt(reader.readString()); break
        case 3: msg.setFirstName(reader.readString()); break
        case 4: msg.setLastName(reader.readString()); break
        case 5: msg.setPhoneNumber(reader.readString()); break
        case 6: msg.setAge(reader.readInt32()); break
        case 7: msg.setDateOfBirth(reader.readString()); break
        case 8: msg.setPan(reader.readString()); break
        case 9: msg.setGender(reader.readString()); break
        case 10: msg.setSpecialCategory(reader.readString()); break
        case 11: msg.setNationality(reader.readString()); break
        case 12: msg.setGovtIdType(reader.readString()); break
        case 13: msg.setGovtIdNumber(reader.readString()); break
        case 14: msg.setIdExpiryDate(reader.readString()); break
        case 15: msg.setIdIssuingCountry(reader.readString()); break
        case 16: msg.setNickName(reader.readString()); break
        case 17: msg.setPrintOnCard(reader.readBool()); break
        case 18: msg.setIntroducer(reader.readString()); break
        case 19: msg.setCountry(reader.readString()); break
        case 20: msg.setAddress(reader.readString()); break
        case 21: msg.setCity(reader.readString()); break
        case 22: msg.setDistrict(reader.readString()); break
        case 23: msg.setState(reader.readString()); break
        case 24: msg.setPincode(reader.readString()); break
        case 25: msg.setEmergencyContact(reader.readString()); break
        case 26: msg.setExCenterSatsangiId(reader.readString()); break
        case 27: msg.setIntroducedBy(reader.readString()); break
        case 28: msg.setHasRoomInAshram(reader.readBool()); break
        case 29: msg.setEmail(reader.readString()); break
        case 30: msg.setBanned(reader.readBool()); break
        case 31: msg.setFirstTimer(reader.readBool()); break
        case 32: msg.setDateOfFirstVisit(reader.readString()); break
        case 33: msg.setNotes(reader.readString()); break
        default: reader.skipField(); break
      }
    }
    return msg
  }
}

// ---------------------------------------------------------------------------
// SearchRequest message
// ---------------------------------------------------------------------------

export class SearchRequest extends jspb.Message {
  constructor() { super(); _init(this, [], 0, -1, null, null) }

  getQuery(): string { return _get(this, 1, '') as string }
  setQuery(v: string) { _set(this, 1, v) }

  serializeBinary(): Uint8Array {
    const writer = new jspb.BinaryWriter()
    const q = this.getQuery()
    if (q.length > 0) writer.writeString(1, q)
    return writer.getResultBuffer()
  }

  static deserializeBinary(bytes: Uint8Array): SearchRequest {
    const msg = new SearchRequest()
    const reader = new jspb.BinaryReader(bytes)
    while (reader.nextField()) {
      if (reader.isEndGroup()) break
      if (reader.getFieldNumber() === 1) msg.setQuery(reader.readString())
      else reader.skipField()
    }
    return msg
  }
}

// ---------------------------------------------------------------------------
// SatsangiList message
// ---------------------------------------------------------------------------

export class SatsangiList extends jspb.Message {
  constructor() { super(); _init(this, [], 0, -1, [1], null) }

  getSatsangisList(): SatsangiMsg[] {
    return (_getOpt(this, 1) || []) as SatsangiMsg[]
  }

  serializeBinary(): Uint8Array {
    const writer = new jspb.BinaryWriter()
    const list = this.getSatsangisList()
    for (const s of list) {
      writer.writeMessage(1, s, SatsangiMsg.serializeBinaryToWriter)
    }
    return writer.getResultBuffer()
  }

  static deserializeBinary(bytes: Uint8Array): SatsangiList {
    const msg = new SatsangiList()
    const list: SatsangiMsg[] = []
    const reader = new jspb.BinaryReader(bytes)
    while (reader.nextField()) {
      if (reader.isEndGroup()) break
      if (reader.getFieldNumber() === 1) {
        const sub = new SatsangiMsg()
        reader.readMessage(sub, (m: SatsangiMsg, r: jspb.BinaryReader) => {
          while (r.nextField()) {
            if (r.isEndGroup()) break
            switch (r.getFieldNumber()) {
              case 1: m.setSatsangiId(r.readString()); break
              case 2: m.setCreatedAt(r.readString()); break
              case 3: m.setFirstName(r.readString()); break
              case 4: m.setLastName(r.readString()); break
              case 5: m.setPhoneNumber(r.readString()); break
              case 6: m.setAge(r.readInt32()); break
              case 7: m.setDateOfBirth(r.readString()); break
              case 8: m.setPan(r.readString()); break
              case 9: m.setGender(r.readString()); break
              case 10: m.setSpecialCategory(r.readString()); break
              case 11: m.setNationality(r.readString()); break
              case 12: m.setGovtIdType(r.readString()); break
              case 13: m.setGovtIdNumber(r.readString()); break
              case 14: m.setIdExpiryDate(r.readString()); break
              case 15: m.setIdIssuingCountry(r.readString()); break
              case 16: m.setNickName(r.readString()); break
              case 17: m.setPrintOnCard(r.readBool()); break
              case 18: m.setIntroducer(r.readString()); break
              case 19: m.setCountry(r.readString()); break
              case 20: m.setAddress(r.readString()); break
              case 21: m.setCity(r.readString()); break
              case 22: m.setDistrict(r.readString()); break
              case 23: m.setState(r.readString()); break
              case 24: m.setPincode(r.readString()); break
              case 25: m.setEmergencyContact(r.readString()); break
              case 26: m.setExCenterSatsangiId(r.readString()); break
              case 27: m.setIntroducedBy(r.readString()); break
              case 28: m.setHasRoomInAshram(r.readBool()); break
              case 29: m.setEmail(r.readString()); break
              case 30: m.setBanned(r.readBool()); break
              case 31: m.setFirstTimer(r.readBool()); break
              case 32: m.setDateOfFirstVisit(r.readString()); break
              case 33: m.setNotes(r.readString()); break
              default: r.skipField(); break
            }
          }
        })
        list.push(sub)
      } else {
        reader.skipField()
      }
    }
    _set(msg, 1, list)
    return msg
  }
}

// ---------------------------------------------------------------------------
// Empty message
// ---------------------------------------------------------------------------

export class Empty extends jspb.Message {
  constructor() { super(); _init(this, [], 0, -1, null, null) }

  serializeBinary(): Uint8Array {
    return new Uint8Array(0)
  }

  static deserializeBinary(_bytes: Uint8Array): Empty {
    return new Empty()
  }
}
