#!/usr/bin/env python3
"""Deterministically inventory user-owned Renegade retail data.

This tool deliberately does not decode, extract, copy, or redistribute game
assets.  It records the supplied Data tree so host tooling and a future Vita
cache can reject missing, case-conflicting, or changed source inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections import defaultdict

SCHEMA_VERSION = 1
TOOL_VERSION = "1.1"
BASE_REQUIRED = ("always.dat", "always2.dat", "always.dbs", "m00_tutorial.mix")
# These profiles deliberately validate only archives proven by the retained
# original factory/Combat probes. They are not guesses about every transitive
# entry a future campaign route may request.
PROFILE_REQUIRED = {
    "m00": (),
    "m01": ("m01.mix",),
    "city": ("c&c_city.mix",),
}
OPTIONAL = ("always3.dat",)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(name: str) -> str:
    suffix = pathlib.PurePosixPath(name).suffix.lower()
    if suffix == ".mix":
        if name.lower().startswith("m") and len(name) >= 3 and name[1:3].isdigit():
            return "mission_mix"
        return "mix"
    return {".dat": "dat", ".dbs": "database", ".w3d": "w3d", ".ini": "config"}.get(suffix, "other")


def required_for_profile(profile: str) -> tuple[str, ...]:
    normalized = profile.lower()
    if normalized not in PROFILE_REQUIRED:
        raise ValueError("unknown resource profile: " + profile)
    return BASE_REQUIRED + PROFILE_REQUIRED[normalized]


def build_manifest(data_root: pathlib.Path, profile: str = "m00") -> dict:
    data_root = data_root.resolve()
    if not data_root.is_dir():
        raise ValueError(f"retail Data directory is missing: {data_root}")
    normalized_profile = profile.lower()
    required = required_for_profile(normalized_profile)
    files = []
    names: dict[str, list[str]] = defaultdict(list)
    for path in sorted((item for item in data_root.rglob("*") if item.is_file()), key=lambda p: p.as_posix().lower()):
        relative = path.relative_to(data_root).as_posix()
        normalized = relative.lower()
        names[normalized].append(relative)
        stat = path.stat()
        files.append({"path": relative, "normalized_path": normalized, "size": stat.st_size,
                      "sha256": sha256(path), "kind": classify(relative)})
    present = {entry["normalized_path"] for entry in files}
    required_missing = [name for name in required if name not in present]
    optional_present = [name for name in OPTIONAL if name in present]
    conflicts = [{"normalized_path": name, "paths": sorted(values)} for name, values in sorted(names.items()) if len(values) > 1]
    digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"schema_version": SCHEMA_VERSION, "tool_version": TOOL_VERSION,
            "data_root_name": data_root.name, "required_profile": normalized_profile,
            "required_files": list(required), "file_count": len(files), "content_digest": digest,
            "files": files, "required_missing": required_missing, "optional_present": optional_present,
            "case_conflicts": conflicts, "valid": not required_missing and not conflicts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_root", type=pathlib.Path)
    parser.add_argument("--profile", choices=sorted(PROFILE_REQUIRED), default="m00",
                        help="validated source-availability profile (default: m00)")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        result = build_manifest(args.data_root, args.profile)
    except ValueError as error:
        print(f"asset manifest: {error}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"asset manifest: profile={result['required_profile']} files={result['file_count']} digest={result['content_digest']} valid={result['valid']}")
    if result["required_missing"]:
        print("missing required: " + ", ".join(result["required_missing"]), file=sys.stderr)
    if result["case_conflicts"]:
        print("case-conflicting retail paths detected", file=sys.stderr)
    return 0 if result["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
