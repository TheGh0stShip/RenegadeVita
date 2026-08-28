#!/usr/bin/env python3
"""Fail closed when a packaged Vita candidate has an incoherent runtime identity."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path


SCHEMA_VERSION = 1
DEFAULT_PROHIBITED = (
    "A3.5-dev1",
    "a35-dev1-runtime.log",
    "Renegade Vita A3.1 development",
    "A31 CAPTURE",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def contains(blob: bytes, value: str) -> bool:
    return value.encode("utf-8") in blob


def contains_prohibited_identity(blob: bytes, value: str) -> bool:
    """Match a stale candidate token without treating dev1 as part of dev10."""
    encoded = re.escape(value.encode("utf-8"))
    if re.fullmatch(r"A\d+\.\d+-dev\d+", value):
        return re.search(encoded + rb"(?!\d)", blob) is not None
    return re.search(encoded, blob) is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    parser.add_argument("--self", required=True, type=Path)
    parser.add_argument("--vpk", required=True, type=Path)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--runtime-log", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--prohibit", action="append", default=[])
    args = parser.parse_args(argv)

    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    candidate_valid = bool(re.fullmatch(r"A\d+\.\d+-dev\d+", args.candidate))
    check("candidate_label", candidate_valid, args.candidate)
    for path, kind in ((args.elf, "elf"), (args.self, "self"), (args.vpk, "vpk")):
        check(f"{kind}_exists", path.is_file() and path.stat().st_size > 0, path.name)

    elf_bytes = args.elf.read_bytes() if args.elf.is_file() else b""
    display_label = f"Renegade Vita {args.candidate}"
    check("elf_display_label", contains(elf_bytes, display_label), display_label)
    check("elf_runtime_log_path", contains(elf_bytes, args.runtime_log), args.runtime_log)
    check("elf_capture_label", contains(elf_bytes, f"{args.candidate} CAPTURE"),
          f"{args.candidate} CAPTURE")
    prohibited = tuple(DEFAULT_PROHIBITED) + tuple(args.prohibit)
    for stale in sorted(set(prohibited)):
        check(
            f"elf_no_stale_{stale}",
            not contains_prohibited_identity(elf_bytes, stale),
            stale,
        )

    self_hash = sha256(args.self) if args.self.is_file() else ""
    packaged = b""
    try:
        with zipfile.ZipFile(args.vpk) as archive:
            names = tuple(sorted(archive.namelist()))
            check("vpk_expected_entries", names == ("eboot.bin", "sce_sys/param.sfo"),
                  ",".join(names))
            packaged = archive.read("eboot.bin")
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        check("vpk_readable", False, type(error).__name__)
    else:
        check("vpk_readable", True, "eboot.bin")
    packaged_hash = hashlib.sha256(packaged).hexdigest() if packaged else ""
    check("packaged_eboot_matches_self", bool(packaged) and packaged_hash == self_hash,
          packaged_hash)
    self_is_not_older = args.self.is_file() and args.elf.is_file() and \
        args.self.stat().st_mtime_ns >= args.elf.stat().st_mtime_ns
    check("self_not_older_than_elf", self_is_not_older, "build-time lineage")

    result = {
        "schema_version": SCHEMA_VERSION,
        "candidate": args.candidate,
        "runtime_log": args.runtime_log,
        "elf_sha256": sha256(args.elf) if args.elf.is_file() else "",
        "self_sha256": self_hash,
        "packaged_eboot_sha256": packaged_hash,
        "checks": checks,
    }
    result["status"] = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"candidate identity: {result['status']} ({args.candidate})")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
