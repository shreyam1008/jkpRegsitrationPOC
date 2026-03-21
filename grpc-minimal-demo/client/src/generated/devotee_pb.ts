/**
 * Protobuf message classes for devotee.proto — MINIMAL version.
 *
 * These match 1:1 with the proto messages. The field numbers here
 * MUST match the field numbers in devotee.proto exactly — that's
 * how protobuf knows which bytes map to which field.
 *
 * Uses google-protobuf's BinaryWriter/BinaryReader for wire-format
 * serialization so the browser speaks real protobuf over grpc-web.
 */

import * as jspb from 'google-protobuf'

// Shorter aliases for the static helpers on jspb.Message
const _get    = jspb.Message.getFieldWithDefault
const _getOpt = jspb.Message.getField
const _set    = jspb.Message.setField
const _init   = jspb.Message.initialize

// ─── Devotee message (field numbers 1-11 from devotee.proto) ───

export class DevoteeMsg extends jspb.Message {
  constructor() { super(); _init(this, [], 0, -1, null, null) }

  // Required fields
  getId(): number { return _get(this, 1, 0) as number }
  setId(v: number) { _set(this, 1, v) }

  getSatsangiId(): string { return _get(this, 2, '') as string }
  setSatsangiId(v: string) { _set(this, 2, v) }

  getFirstName(): string { return _get(this, 3, '') as string }
  setFirstName(v: string) { _set(this, 3, v) }

  getLastName(): string { return _get(this, 4, '') as string }
  setLastName(v: string) { _set(this, 4, v) }

  getPhoneNumber(): string { return _get(this, 5, '') as string }
  setPhoneNumber(v: string) { _set(this, 5, v) }

  // Optional fields
  getGender(): string | undefined { return _getOpt(this, 6) as string | undefined }
  setGender(v: string) { _set(this, 6, v) }

  getAge(): number | undefined { return _getOpt(this, 7) as number | undefined }
  setAge(v: number) { _set(this, 7, v) }
  hasAge(): boolean { return _getOpt(this, 7) != null }

  getCity(): string | undefined { return _getOpt(this, 8) as string | undefined }
  setCity(v: string) { _set(this, 8, v) }

  getState(): string | undefined { return _getOpt(this, 9) as string | undefined }
  setState(v: string) { _set(this, 9, v) }

  getNationality(): string { return _get(this, 10, '') as string }
  setNationality(v: string) { _set(this, 10, v) }

  getCreatedAt(): string { return _get(this, 11, '') as string }
  setCreatedAt(v: string) { _set(this, 11, v) }

  // ─── Serialization (object → binary) ───

  serializeBinary(): Uint8Array {
    const writer = new jspb.BinaryWriter()
    DevoteeMsg.serializeBinaryToWriter(this, writer)
    return writer.getResultBuffer()
  }

  static serializeBinaryToWriter(msg: DevoteeMsg, writer: jspb.BinaryWriter) {
    const id = msg.getId(); if (id !== 0) writer.writeInt32(1, id)
    const sid = msg.getSatsangiId(); if (sid.length > 0) writer.writeString(2, sid)
    const fn = msg.getFirstName(); if (fn.length > 0) writer.writeString(3, fn)
    const ln = msg.getLastName(); if (ln.length > 0) writer.writeString(4, ln)
    const ph = msg.getPhoneNumber(); if (ph.length > 0) writer.writeString(5, ph)
    const g = msg.getGender(); if (g) writer.writeString(6, g)
    if (msg.hasAge()) writer.writeInt32(7, msg.getAge()!)
    const c = msg.getCity(); if (c) writer.writeString(8, c)
    const s = msg.getState(); if (s) writer.writeString(9, s)
    const n = msg.getNationality(); if (n.length > 0) writer.writeString(10, n)
    const ca = msg.getCreatedAt(); if (ca.length > 0) writer.writeString(11, ca)
  }

  // ─── Deserialization (binary → object) ───

  static deserializeBinary(bytes: Uint8Array): DevoteeMsg {
    const msg = new DevoteeMsg()
    const reader = new jspb.BinaryReader(bytes)
    while (reader.nextField()) {
      if (reader.isEndGroup()) break
      switch (reader.getFieldNumber()) {
        case 1: msg.setId(reader.readInt32()); break
        case 2: msg.setSatsangiId(reader.readString()); break
        case 3: msg.setFirstName(reader.readString()); break
        case 4: msg.setLastName(reader.readString()); break
        case 5: msg.setPhoneNumber(reader.readString()); break
        case 6: msg.setGender(reader.readString()); break
        case 7: msg.setAge(reader.readInt32()); break
        case 8: msg.setCity(reader.readString()); break
        case 9: msg.setState(reader.readString()); break
        case 10: msg.setNationality(reader.readString()); break
        case 11: msg.setCreatedAt(reader.readString()); break
        default: reader.skipField(); break
      }
    }
    return msg
  }
}

// ─── DevoteeList message (repeated Devotee, field 1) ───

export class DevoteeList extends jspb.Message {
  constructor() { super(); _init(this, [], 0, -1, [1], null) }

  getDevoteesList(): DevoteeMsg[] {
    return (_getOpt(this, 1) || []) as DevoteeMsg[]
  }

  serializeBinary(): Uint8Array {
    const writer = new jspb.BinaryWriter()
    for (const d of this.getDevoteesList()) {
      writer.writeMessage(1, d, DevoteeMsg.serializeBinaryToWriter)
    }
    return writer.getResultBuffer()
  }

  static deserializeBinary(bytes: Uint8Array): DevoteeList {
    const msg = new DevoteeList()
    const list: DevoteeMsg[] = []
    const reader = new jspb.BinaryReader(bytes)
    while (reader.nextField()) {
      if (reader.isEndGroup()) break
      if (reader.getFieldNumber() === 1) {
        const sub = new DevoteeMsg()
        reader.readMessage(sub, (m: DevoteeMsg, r: jspb.BinaryReader) => {
          while (r.nextField()) {
            if (r.isEndGroup()) break
            switch (r.getFieldNumber()) {
              case 1: m.setId(r.readInt32()); break
              case 2: m.setSatsangiId(r.readString()); break
              case 3: m.setFirstName(r.readString()); break
              case 4: m.setLastName(r.readString()); break
              case 5: m.setPhoneNumber(r.readString()); break
              case 6: m.setGender(r.readString()); break
              case 7: m.setAge(r.readInt32()); break
              case 8: m.setCity(r.readString()); break
              case 9: m.setState(r.readString()); break
              case 10: m.setNationality(r.readString()); break
              case 11: m.setCreatedAt(r.readString()); break
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

// ─── Empty message (no fields) ───

export class Empty extends jspb.Message {
  constructor() { super(); _init(this, [], 0, -1, null, null) }

  serializeBinary(): Uint8Array {
    return new Uint8Array(0)
  }

  static deserializeBinary(_bytes: Uint8Array): Empty {
    return new Empty()
  }
}
