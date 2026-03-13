/**
 * Hand-written protobuf message classes for grpc-web client.
 *
 * These correspond 1:1 with the messages in proto/satsangi.proto.
 * Uses google-protobuf's BinaryWriter/BinaryReader for wire-format
 * serialization so the browser speaks real protobuf over grpc-web.
 */

import * as jspb from 'google-protobuf'

// ---------------------------------------------------------------------------
// SatsangiCreate message
// ---------------------------------------------------------------------------

export class SatsangiCreate extends jspb.Message {
  getFirstName(): string { return this.getFieldWithDefault(1, '') as string }
  setFirstName(v: string) { this.setField(1, v) }

  getLastName(): string { return this.getFieldWithDefault(2, '') as string }
  setLastName(v: string) { this.setField(2, v) }

  getPhoneNumber(): string { return this.getFieldWithDefault(3, '') as string }
  setPhoneNumber(v: string) { this.setField(3, v) }

  getAge(): number | undefined { return this.getField(4) as number | undefined }
  setAge(v: number) { this.setField(4, v) }
  hasAge(): boolean { return this.hasField(4) }

  getDateOfBirth(): string | undefined { return this.getField(5) as string | undefined }
  setDateOfBirth(v: string) { this.setField(5, v) }
  hasDateOfBirth(): boolean { return this.hasField(5) }

  getPan(): string | undefined { return this.getField(6) as string | undefined }
  setPan(v: string) { this.setField(6, v) }
  hasPan(): boolean { return this.hasField(6) }

  getGender(): string | undefined { return this.getField(7) as string | undefined }
  setGender(v: string) { this.setField(7, v) }
  hasGender(): boolean { return this.hasField(7) }

  getSpecialCategory(): string | undefined { return this.getField(8) as string | undefined }
  setSpecialCategory(v: string) { this.setField(8, v) }
  hasSpecialCategory(): boolean { return this.hasField(8) }

  getNationality(): string { return this.getFieldWithDefault(9, 'Indian') as string }
  setNationality(v: string) { this.setField(9, v) }

  getGovtIdType(): string | undefined { return this.getField(10) as string | undefined }
  setGovtIdType(v: string) { this.setField(10, v) }
  hasGovtIdType(): boolean { return this.hasField(10) }

  getGovtIdNumber(): string | undefined { return this.getField(11) as string | undefined }
  setGovtIdNumber(v: string) { this.setField(11, v) }
  hasGovtIdNumber(): boolean { return this.hasField(11) }

  getIdExpiryDate(): string | undefined { return this.getField(12) as string | undefined }
  setIdExpiryDate(v: string) { this.setField(12, v) }
  hasIdExpiryDate(): boolean { return this.hasField(12) }

  getIdIssuingCountry(): string | undefined { return this.getField(13) as string | undefined }
  setIdIssuingCountry(v: string) { this.setField(13, v) }
  hasIdIssuingCountry(): boolean { return this.hasField(13) }

  getNickName(): string | undefined { return this.getField(14) as string | undefined }
  setNickName(v: string) { this.setField(14, v) }
  hasNickName(): boolean { return this.hasField(14) }

  getPrintOnCard(): boolean { return this.getFieldWithDefault(15, false) as boolean }
  setPrintOnCard(v: boolean) { this.setField(15, v) }

  getIntroducer(): string | undefined { return this.getField(16) as string | undefined }
  setIntroducer(v: string) { this.setField(16, v) }
  hasIntroducer(): boolean { return this.hasField(16) }

  getCountry(): string { return this.getFieldWithDefault(17, 'India') as string }
  setCountry(v: string) { this.setField(17, v) }

  getAddress(): string | undefined { return this.getField(18) as string | undefined }
  setAddress(v: string) { this.setField(18, v) }
  hasAddress(): boolean { return this.hasField(18) }

  getCity(): string | undefined { return this.getField(19) as string | undefined }
  setCity(v: string) { this.setField(19, v) }
  hasCity(): boolean { return this.hasField(19) }

  getDistrict(): string | undefined { return this.getField(20) as string | undefined }
  setDistrict(v: string) { this.setField(20, v) }
  hasDistrict(): boolean { return this.hasField(20) }

  getState(): string | undefined { return this.getField(21) as string | undefined }
  setState(v: string) { this.setField(21, v) }
  hasState(): boolean { return this.hasField(21) }

  getPincode(): string | undefined { return this.getField(22) as string | undefined }
  setPincode(v: string) { this.setField(22, v) }
  hasPincode(): boolean { return this.hasField(22) }

  getEmergencyContact(): string | undefined { return this.getField(23) as string | undefined }
  setEmergencyContact(v: string) { this.setField(23, v) }
  hasEmergencyContact(): boolean { return this.hasField(23) }

  getExCenterSatsangiId(): string | undefined { return this.getField(24) as string | undefined }
  setExCenterSatsangiId(v: string) { this.setField(24, v) }
  hasExCenterSatsangiId(): boolean { return this.hasField(24) }

  getIntroducedBy(): string | undefined { return this.getField(25) as string | undefined }
  setIntroducedBy(v: string) { this.setField(25, v) }
  hasIntroducedBy(): boolean { return this.hasField(25) }

  getHasRoomInAshram(): boolean { return this.getFieldWithDefault(26, false) as boolean }
  setHasRoomInAshram(v: boolean) { this.setField(26, v) }

  getEmail(): string | undefined { return this.getField(27) as string | undefined }
  setEmail(v: string) { this.setField(27, v) }
  hasEmail(): boolean { return this.hasField(27) }

  getBanned(): boolean { return this.getFieldWithDefault(28, false) as boolean }
  setBanned(v: boolean) { this.setField(28, v) }

  getFirstTimer(): boolean { return this.getFieldWithDefault(29, false) as boolean }
  setFirstTimer(v: boolean) { this.setField(29, v) }

  getDateOfFirstVisit(): string | undefined { return this.getField(30) as string | undefined }
  setDateOfFirstVisit(v: string) { this.setField(30, v) }
  hasDateOfFirstVisit(): boolean { return this.hasField(30) }

  getNotes(): string | undefined { return this.getField(31) as string | undefined }
  setNotes(v: string) { this.setField(31, v) }
  hasNotes(): boolean { return this.hasField(31) }

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
// Satsangi message (extends SatsangiCreate fields + id + created_at)
// ---------------------------------------------------------------------------

export class SatsangiMsg extends jspb.Message {
  getSatsangiId(): string { return this.getFieldWithDefault(1, '') as string }
  setSatsangiId(v: string) { this.setField(1, v) }

  getCreatedAt(): string { return this.getFieldWithDefault(2, '') as string }
  setCreatedAt(v: string) { this.setField(2, v) }

  getFirstName(): string { return this.getFieldWithDefault(3, '') as string }
  setFirstName(v: string) { this.setField(3, v) }

  getLastName(): string { return this.getFieldWithDefault(4, '') as string }
  setLastName(v: string) { this.setField(4, v) }

  getPhoneNumber(): string { return this.getFieldWithDefault(5, '') as string }
  setPhoneNumber(v: string) { this.setField(5, v) }

  getAge(): number | undefined { return this.getField(6) as number | undefined }
  setAge(v: number) { this.setField(6, v) }
  hasAge(): boolean { return this.hasField(6) }

  getDateOfBirth(): string | undefined { return this.getField(7) as string | undefined }
  setDateOfBirth(v: string) { this.setField(7, v) }

  getPan(): string | undefined { return this.getField(8) as string | undefined }
  setPan(v: string) { this.setField(8, v) }

  getGender(): string | undefined { return this.getField(9) as string | undefined }
  setGender(v: string) { this.setField(9, v) }

  getSpecialCategory(): string | undefined { return this.getField(10) as string | undefined }
  setSpecialCategory(v: string) { this.setField(10, v) }

  getNationality(): string { return this.getFieldWithDefault(11, '') as string }
  setNationality(v: string) { this.setField(11, v) }

  getGovtIdType(): string | undefined { return this.getField(12) as string | undefined }
  setGovtIdType(v: string) { this.setField(12, v) }

  getGovtIdNumber(): string | undefined { return this.getField(13) as string | undefined }
  setGovtIdNumber(v: string) { this.setField(13, v) }

  getIdExpiryDate(): string | undefined { return this.getField(14) as string | undefined }
  setIdExpiryDate(v: string) { this.setField(14, v) }

  getIdIssuingCountry(): string | undefined { return this.getField(15) as string | undefined }
  setIdIssuingCountry(v: string) { this.setField(15, v) }

  getNickName(): string | undefined { return this.getField(16) as string | undefined }
  setNickName(v: string) { this.setField(16, v) }

  getPrintOnCard(): boolean { return this.getFieldWithDefault(17, false) as boolean }
  setPrintOnCard(v: boolean) { this.setField(17, v) }

  getIntroducer(): string | undefined { return this.getField(18) as string | undefined }
  setIntroducer(v: string) { this.setField(18, v) }

  getCountry(): string { return this.getFieldWithDefault(19, '') as string }
  setCountry(v: string) { this.setField(19, v) }

  getAddress(): string | undefined { return this.getField(20) as string | undefined }
  setAddress(v: string) { this.setField(20, v) }

  getCity(): string | undefined { return this.getField(21) as string | undefined }
  setCity(v: string) { this.setField(21, v) }

  getDistrict(): string | undefined { return this.getField(22) as string | undefined }
  setDistrict(v: string) { this.setField(22, v) }

  getState(): string | undefined { return this.getField(23) as string | undefined }
  setState(v: string) { this.setField(23, v) }

  getPincode(): string | undefined { return this.getField(24) as string | undefined }
  setPincode(v: string) { this.setField(24, v) }

  getEmergencyContact(): string | undefined { return this.getField(25) as string | undefined }
  setEmergencyContact(v: string) { this.setField(25, v) }

  getExCenterSatsangiId(): string | undefined { return this.getField(26) as string | undefined }
  setExCenterSatsangiId(v: string) { this.setField(26, v) }

  getIntroducedBy(): string | undefined { return this.getField(27) as string | undefined }
  setIntroducedBy(v: string) { this.setField(27, v) }

  getHasRoomInAshram(): boolean { return this.getFieldWithDefault(28, false) as boolean }
  setHasRoomInAshram(v: boolean) { this.setField(28, v) }

  getEmail(): string | undefined { return this.getField(29) as string | undefined }
  setEmail(v: string) { this.setField(29, v) }

  getBanned(): boolean { return this.getFieldWithDefault(30, false) as boolean }
  setBanned(v: boolean) { this.setField(30, v) }

  getFirstTimer(): boolean { return this.getFieldWithDefault(31, false) as boolean }
  setFirstTimer(v: boolean) { this.setField(31, v) }

  getDateOfFirstVisit(): string | undefined { return this.getField(32) as string | undefined }
  setDateOfFirstVisit(v: string) { this.setField(32, v) }

  getNotes(): string | undefined { return this.getField(33) as string | undefined }
  setNotes(v: string) { this.setField(33, v) }

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
  getQuery(): string { return this.getFieldWithDefault(1, '') as string }
  setQuery(v: string) { this.setField(1, v) }

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
  getSatsangisList(): SatsangiMsg[] {
    return (this.getField(1) || []) as SatsangiMsg[]
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
    msg.setField(1, list)
    return msg
  }
}

// ---------------------------------------------------------------------------
// Empty message
// ---------------------------------------------------------------------------

export class Empty extends jspb.Message {
  serializeBinary(): Uint8Array {
    return new Uint8Array(0)
  }

  static deserializeBinary(_bytes: Uint8Array): Empty {
    return new Empty()
  }
}
