#!/usr/bin/env python3

"""Validate one bounded Renegade Vita raw-controller route."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


MAGIC = b"RVINPUT1"
LEGACY_VERSION = 1
VERSION = 2
HEADER = struct.Struct("<8s6I")
SAMPLE = struct.Struct("<IBBBB")
TIMED_SAMPLE = struct.Struct("<IBBBBI")
FLAG_COMPLETE = 1
FLAG_TRUNCATED = 2
KNOWN_FLAGS = FLAG_COMPLETE | FLAG_TRUNCATED
MAX_SAMPLES = 18_000


def fnv1a32(payload: bytes) -> int:
    value = 2_166_136_261
    for byte in payload:
        value ^= byte
        value = (value * 16_777_619) & 0xFFFFFFFF
    return value


def validate(path: Path, reject_truncated: bool) -> dict:
    data = path.read_bytes()
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: object) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    check("minimum_header_size", len(data) >= HEADER.size, len(data))
    if len(data) < HEADER.size:
        return {
            "schema_version": 1,
            "status": "FAIL",
            "route": str(path),
            "sha256": hashlib.sha256(data).hexdigest(),
            "checks": checks,
        }

    magic, version, sample_size, sample_count, flags, checksum, reserved = HEADER.unpack_from(data)
    supported_format = (
        (version == LEGACY_VERSION and sample_size == SAMPLE.size)
        or (version == VERSION and sample_size == TIMED_SAMPLE.size)
    )
    expected_sample_size = sample_size if supported_format else SAMPLE.size
    expected_size = HEADER.size + sample_count * expected_sample_size
    payload = data[HEADER.size:]
    truncated = bool(flags & FLAG_TRUNCATED)
    check("magic", magic == MAGIC, magic.decode("ascii", errors="replace"))
    check("version", version in (LEGACY_VERSION, VERSION), version)
    check("sample_size", supported_format, sample_size)
    check("sample_count_bounded", 0 < sample_count <= MAX_SAMPLES, sample_count)
    check("complete", bool(flags & FLAG_COMPLETE), flags)
    check("known_flags_only", not flags & ~KNOWN_FLAGS, flags)
    check("reserved_zero", reserved == 0, reserved)
    check("exact_file_size", len(data) == expected_size, {"actual": len(data), "expected": expected_size})
    actual_checksum = fnv1a32(payload)
    check("payload_checksum", actual_checksum == checksum, {"actual": actual_checksum, "expected": checksum})
    check("not_truncated", not reject_truncated or not truncated, truncated)

    status = "PASS" if all(item["passed"] for item in checks) else "FAIL"
    return {
        "schema_version": 1,
        "status": status,
        "route": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "format_version": version,
        "sample_count": sample_count,
        "sample_size": sample_size,
        "timebase": "recorded-delta-us" if version == VERSION else "legacy60hz",
        "payload_checksum_fnv1a32": f"{checksum:08x}",
        "truncated": truncated,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("route", type=Path)
    parser.add_argument("--reject-truncated", action="store_true")
    args = parser.parse_args()
    try:
        result = validate(args.route, args.reject_truncated)
    except (OSError, struct.error) as error:
        result = {
            "schema_version": 1,
            "status": "FAIL",
            "route": str(args.route),
            "error": str(error),
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
