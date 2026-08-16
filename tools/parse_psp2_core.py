#!/usr/bin/env python3
"""Bounded inspector for gzip-wrapped Vita psp2dmp ELF cores.

The parser intentionally never emits arbitrary note payload bytes and never
decodes undocumented private register-note schemas.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct

PT_NOTE = 4
PARSER_VERSION = "1.1.0"
SCHEMA_VERSION = 2


def padded(n: int) -> int:
    return (n + 3) & ~3


def _read_u16(data: bytes, offset: int) -> int | None:
    if offset + 2 > len(data):
        return None
    return struct.unpack_from("<H", data, offset)[0]


def _read_u32(data: bytes, offset: int) -> int | None:
    if offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def _parse_header(data: bytes):
    if len(data) < 52:
        return ['truncated ELF header']
    if data[:4] != b"\x7fELF":
        return ['not an ELF payload']
    if data[4] != 1:
        return ['not a 32-bit ELF payload']
    if data[5] != 1:
        return ['not a little-endian ELF payload']
    if data[18:20] != b"\x28\x00":
        return ['not an ARM ELF payload']
    return []


def notes(data: bytes):
    parse_errors: list[str] = []
    notes_result: list[tuple[str, int, int, bytes]] = []

    phoff = _read_u32(data, 28)
    phentsize = _read_u16(data, 42)
    phnum = _read_u16(data, 44)
    if phoff is None or phentsize is None or phnum is None:
        return notes_result, parse_errors + ['truncated ELF program header table metadata']

    for index in range(phnum):
        offset = phoff + index * phentsize
        if offset + 32 > len(data):
            parse_errors.append(f"truncated program header {index}")
            break

        typ, fileoff, _va, _pa, filesz, _memsz, _flags, _align = struct.unpack_from(
            "<IIIIIIII", data, offset
        )
        if typ != PT_NOTE:
            continue

        segment_end = fileoff + filesz
        if segment_end > len(data):
            parse_errors.append(f"truncated PT_NOTE segment {index}")
            continue

        note_offset = fileoff
        while note_offset + 12 <= segment_end:
            namesz, descsz, note_type = struct.unpack_from("<III", data, note_offset)
            name_offset = note_offset + 12
            desc_offset = name_offset + padded(namesz)
            if desc_offset + descsz > segment_end:
                parse_errors.append(f"truncated note payload in PT_NOTE segment {index}")
                break

            owner = data[name_offset:name_offset + namesz].rstrip(b"\0").decode("ascii", "replace")
            notes_result.append((owner, note_type, descsz, data[desc_offset:desc_offset + descsz]))
            note_offset = desc_offset + padded(descsz)

    return notes_result, parse_errors


def thread_info(desc: bytes):
    result = {
        "schema_version": None,
        "record_size": None,
        "record_count": 0,
        "threads": [],
        "thread_reg_info": {
            "available": False,
            "status": "unavailable_private_schema",
        },
        "parse_errors": [],
    }

    if len(desc) < 12:
        result["parse_errors"].append("truncated THREAD_INFO header")
        return result

    record_count, version, record_size = struct.unpack_from("<III", desc)
    result["schema_version"] = version
    result["record_size"] = record_size
    result["record_count"] = record_count

    if version != 4 or record_size != 200:
        result["parse_errors"].append("unsupported private THREAD_INFO schema")
        return result

    for i in range(min(record_count, (len(desc) - 12) // record_size)):
        start = 12 + i * record_size
        record = desc[start:start + record_size]
        if len(record) < 156:
            result["parse_errors"].append(f"truncated THREAD_INFO record {i}")
            break

        thread_id = struct.unpack_from("<I", record, 0)[0]
        thread_name = record[4:36].split(b"\0", 1)[0].decode("ascii", "replace")
        pc = struct.unpack_from("<I", record, 152)[0]
        result["threads"].append(
            {
                "thread_id": f"0x{thread_id:08X}",
                "thread_name": thread_name,
                "pc": f"0x{pc:08X}",
                "pc_verified": True,
            }
        )

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dump")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.dump, "rb") as stream:
        raw_input = stream.read()

    with gzip.open(args.dump, "rb") as stream:
        data = stream.read()

    header_errors = _parse_header(data)
    if header_errors:
        raise SystemExit(header_errors[0])

    parsed_notes, parse_errors = notes(data)
    out = {
        "schema": SCHEMA_VERSION,
        "parser_version": PARSER_VERSION,
        "core_format": "ELF32 ARM EABI5",
        "input_identity": {
            "sha256": hashlib.sha256(raw_input).hexdigest(),
            "byte_count": len(raw_input),
        },
        "payload_identity": {
            "sha256": hashlib.sha256(data).hexdigest(),
            "byte_count": len(data),
        },
        "notes_inventory": {
            "count": len(parsed_notes),
            "types": [f"0x{note_type:08X}" for _, note_type, _, _ in parsed_notes],
        },
        "notes": [],
        "thread_info": None,
        "parse_errors": parse_errors,
    }

    for owner, note_type, desc_len, desc in parsed_notes:
        out["notes"].append(
            {
                "owner": owner,
                "type": f"0x{note_type:08X}",
                "size": desc_len,
            }
        )
        if owner == "THREAD_INFO":
            out["thread_info"] = thread_info(desc)

    with open(args.output, "w", encoding="utf-8") as stream:
        json.dump(out, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
