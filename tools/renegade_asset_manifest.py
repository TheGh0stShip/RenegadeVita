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
import struct
import sys
from collections import defaultdict

SCHEMA_VERSION = 1
TOOL_VERSION = "1.2"
BASE_REQUIRED = ("always.dat", "always2.dat", "always.dbs", "m00_tutorial.mix")
# Campaign requirements come from retail campaign.ini. The other profiles
# remain explicit, limited archive checks; none proves gameplay completeness.
PROFILE_REQUIRED = {
    "campaign": (),
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


def campaign_required(data_root: pathlib.Path):
    # The authored retail flow is independent of the current port's source
    # selection. Never certify the whole campaign using M00 prerequisites.
    if __package__ in (None, ''):
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from tools.collect_retail_content_baseline import flow_records
    from tools.renegade_cinematic_dependency_scan import MixArchive
    for search_root in (data_root, data_root.parent):
        if any(p.name.casefold() == 'campaign.ini' for p in search_root.iterdir()):
            raise ValueError('loose campaign override requires factory-precedence review')
    matches = [p for p in data_root.iterdir() if p.name.casefold() == 'always.dat']
    if len(matches) != 1:
        raise ValueError('campaign profile needs one unambiguous always.dat')
    archive = MixArchive(matches[0])
    if sum(name.casefold() == 'campaign.ini' for name, *_ in archive.entry_records) != 1:
        raise ValueError('campaign profile needs one unambiguous campaign.ini')
    payload = archive.read_binary('campaign.ini')
    steps = flow_records(payload)
    required = list(BASE_REQUIRED)
    level_count = 0
    for step in steps:
        kind, tokens = step['kind'], step['tokens']
        if kind not in ('level', 'movie', 'score', 'message'):
            raise ValueError('unclassified campaign directive; resource requirements incomplete')
        if kind not in ('level', 'movie'):
            continue
        if len(tokens) < 2 or (kind == 'level' and len(tokens) != 2):
            raise ValueError('unreviewed campaign resource syntax')
        logical = tokens[1].replace('\\', '/')
        parts = logical.split('/')
        if logical.startswith('/') or ':' in logical or any(p in ('', '.', '..') for p in parts):
            raise ValueError('unsafe campaign resource path')
        if kind == 'movie':
            if parts[0].casefold() != 'data' or len(parts) < 2:
                raise ValueError('campaign movie is outside the Data-root manifest scope')
            logical = '/'.join(parts[1:])
        else:
            level_count += 1
        if logical.lower() not in required:
            required.append(logical.lower())
    if not level_count:
        raise ValueError('campaign flow contains no levels')
    return tuple(required), {'kind': 'retail campaign flow',
                             'campaign_ini_sha256': hashlib.sha256(payload).hexdigest(),
                             'flow_entries': len(steps), 'level_entries': level_count}


def required_for_profile(profile: str, data_root=None) -> tuple[str, ...]:
    normalized = profile.lower()
    if normalized not in PROFILE_REQUIRED:
        raise ValueError("unknown resource profile: " + profile)
    if normalized == 'campaign':
        if data_root is None:
            raise ValueError('campaign requirements must be derived from a retail Data root')
        return campaign_required(data_root)[0]
    return BASE_REQUIRED + PROFILE_REQUIRED[normalized]


def build_manifest(data_root: pathlib.Path, profile: str = "campaign") -> dict:
    data_root = data_root.resolve()
    if not data_root.is_dir():
        raise ValueError(f"retail Data directory is missing: {data_root}")
    normalized_profile = profile.lower()
    profile_errors = []
    derivation = {'kind': 'explicit limited archive profile'}
    if normalized_profile == 'campaign':
        derivation = {'kind': 'retail campaign flow'}
        try:
            required, derivation = campaign_required(data_root)
        except (ValueError, OSError, KeyError, UnicodeError, struct.error) as error:
            required = BASE_REQUIRED
            profile_errors.append(str(error))
    else:
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
            "profile_derivation": derivation, "profile_errors": profile_errors,
            "validation_scope": "File availability/identity only; not gameplay or full content completeness",
            "gameplay_parity_verified": False,
            "files": files, "required_missing": required_missing, "optional_present": optional_present,
            "case_conflicts": conflicts, "valid": not required_missing and not conflicts and not profile_errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_root", type=pathlib.Path)
    parser.add_argument("--profile", choices=sorted(PROFILE_REQUIRED), default="campaign",
                        help="source-availability profile (default: retail-derived campaign)")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.data_root.resolve()):
        parser.error('manifest output must remain outside the retail Data tree')
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
    for error in result['profile_errors']:
        print('campaign requirement discovery failed: ' + error, file=sys.stderr)
    return 0 if result["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
