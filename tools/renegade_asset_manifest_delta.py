#!/usr/bin/env python3
"""Compare two Renegade asset-manifest JSON files.

The comparator is intentionally read-only and deterministic:
- validates both input manifests against a narrow schema,
- rejects unknown schema versions and duplicate normalized identities,
- compares identities and SHA-256 values only,
- reports added/removed/changed records, case-only path conflicts, and
  profile-required-input deltas,
- writes sorted JSON and Markdown outputs.

Only manifest inputs are read. No archive payloads are read or converted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
import sys


KNOWN_SCHEMA_VERSION = 1


def _fail(message: str) -> None:
    raise ValueError(message)


def canonical_manifest_digest(files: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_hex64(value: str, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        _fail(f"{label}: sha256 must be a lowercase/uppercase hex string")
    try:
        int(value, 16)
    except ValueError as error:
        _fail(f"{label}: sha256 must be hexadecimal")


def validate_manifest(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"{path}: failed to load JSON: {error}")

    if not isinstance(payload, dict):
        _fail(f"{path}: manifest payload must be an object")

    schema_version = payload.get("schema_version")
    if schema_version != KNOWN_SCHEMA_VERSION:
        _fail(f"{path}: unknown schema version {schema_version!r}")

    for key in ("required_profile", "required_files", "required_missing", "optional_present",
                "file_count", "content_digest", "files", "valid"):
        if key not in payload:
            _fail(f"{path}: missing required key {key!r}")

    if not isinstance(payload["required_profile"], str):
        _fail(f"{path}: required_profile must be a string")
    if not isinstance(payload["required_files"], list) or not all(isinstance(item, str) for item in payload["required_files"]):
        _fail(f"{path}: required_files must be a string list")
    if not isinstance(payload["required_missing"], list) or not all(isinstance(item, str) for item in payload["required_missing"]):
        _fail(f"{path}: required_missing must be a string list")
    if not isinstance(payload["optional_present"], list) or not all(isinstance(item, str) for item in payload["optional_present"]):
        _fail(f"{path}: optional_present must be a string list")
    if not isinstance(payload["file_count"], int) or payload["file_count"] < 0:
        _fail(f"{path}: file_count must be a non-negative integer")
    if not isinstance(payload["content_digest"], str):
        _fail(f"{path}: content_digest must be a string")
    if not isinstance(payload["files"], list):
        _fail(f"{path}: files must be an array")
    if not isinstance(payload["valid"], bool):
        _fail(f"{path}: valid must be a boolean")

    entries = payload["files"]
    indexed: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            _fail(f"{path}: file entry #{index} must be an object")
        for key in ("path", "normalized_path", "sha256", "kind"):
            if key not in entry:
                _fail(f"{path}: file entry #{index} missing key {key!r}")
        normalized = entry["normalized_path"]
        path_value = entry["path"]
        digest = entry["sha256"]
        size = entry.get("size")
        if not isinstance(normalized, str) or not normalized:
            _fail(f"{path}: file entry #{index} normalized_path must be non-empty string")
        if not isinstance(path_value, str) or not path_value:
            _fail(f"{path}: file entry #{index} path must be non-empty string")
        validate_hex64(digest, f"{path}: file entry #{index} ({path_value}) sha256")
        if not isinstance(size, int) or size < 0:
            _fail(f"{path}: file entry #{index} size must be non-negative integer")
        if not isinstance(entry["kind"], str) or not entry["kind"]:
            _fail(f"{path}: file entry #{index} kind must be non-empty string")
        normalized_lower = normalized.lower()
        if normalized_lower in indexed:
            _fail(f"{path}: duplicate identity {normalized_lower!r} in manifest files")
        indexed[normalized_lower] = entry

    if payload["file_count"] != len(entries):
        _fail(f"{path}: file_count={payload['file_count']} does not match files length={len(entries)}")
    if payload["content_digest"] != canonical_manifest_digest(entries):
        _fail(f"{path}: content_digest does not match files payload")

    return payload, indexed


def compare_records(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_payload, before_files = before
    after_payload, after_files = after
    before_identities = set(before_files)
    after_identities = set(after_files)
    all_identities = sorted(before_identities | after_identities)

    added: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    case_conflicts: list[dict[str, Any]] = []

    for identity in all_identities:
        before_entry = before_files.get(identity)
        after_entry = after_files.get(identity)
        if before_entry is None and after_entry is not None:
            added.append({
                "normalized_path": identity,
                "path": after_entry["path"],
                "sha256": after_entry["sha256"],
                "size": after_entry["size"],
            })
            continue
        if before_entry is not None and after_entry is None:
            removed.append({
                "normalized_path": identity,
                "path": before_entry["path"],
                "sha256": before_entry["sha256"],
                "size": before_entry["size"],
            })
            continue
        # Identity exists in both manifests.
        if before_entry["sha256"] != after_entry["sha256"]:
            changed.append({
                "normalized_path": identity,
                "before": {"path": before_entry["path"], "sha256": before_entry["sha256"], "size": before_entry["size"]},
                "after": {"path": after_entry["path"], "sha256": after_entry["sha256"], "size": after_entry["size"]},
            })
        if before_entry["path"] != after_entry["path"]:
            case_conflicts.append({
                "normalized_path": identity,
                "before_path": before_entry["path"],
                "after_path": after_entry["path"],
            })

    profile_before = {
        "required_profile": before_payload["required_profile"],
        "required_files": sorted(before_payload["required_files"]),
        "required_missing": sorted(before_payload["required_missing"]),
    }
    profile_after = {
        "required_profile": after_payload["required_profile"],
        "required_files": sorted(after_payload["required_files"]),
        "required_missing": sorted(after_payload["required_missing"]),
    }

    required_files_before = set(profile_before["required_files"])
    required_files_after = set(profile_after["required_files"])
    required_missing_before = set(profile_before["required_missing"])
    required_missing_after = set(profile_after["required_missing"])

    return {
        "before": {
            "manifest": str(before_payload.get("manifest_path", "")),
            "schema_version": KNOWN_SCHEMA_VERSION,
            "required_profile": before_payload["required_profile"],
            "required_files": profile_before["required_files"],
            "required_missing": profile_before["required_missing"],
        },
        "after": {
            "manifest": str(after_payload.get("manifest_path", "")),
            "schema_version": KNOWN_SCHEMA_VERSION,
            "required_profile": after_payload["required_profile"],
            "required_files": profile_after["required_files"],
            "required_missing": profile_after["required_missing"],
        },
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "case_conflicts": len(case_conflicts),
        },
        "added": sorted(added, key=lambda item: item["normalized_path"]),
        "removed": sorted(removed, key=lambda item: item["normalized_path"]),
        "changed": sorted(changed, key=lambda item: item["normalized_path"]),
        "case_conflicts": sorted(case_conflicts, key=lambda item: item["normalized_path"]),
        "profile_required_input_changes": {
            "before_profile": profile_before["required_profile"],
            "after_profile": profile_after["required_profile"],
            "required_files_added": sorted(required_files_after - required_files_before),
            "required_files_removed": sorted(required_files_before - required_files_after),
            "required_missing_added": sorted(required_missing_after - required_missing_before),
            "required_missing_removed": sorted(required_missing_before - required_missing_after),
        },
    }


def format_markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    before = result["before"]
    after = result["after"]
    changed_profile = before["required_profile"] != after["required_profile"]
    lines: list[str] = [
        "# Renegade Asset Manifest Delta",
        "",
        f"- before: `{before['manifest']}`",
        f"- after: `{after['manifest']}`",
        f"- before_profile: `{before['required_profile']}`",
        f"- after_profile: `{after['required_profile']}`",
        f"- schema_version: `{before['schema_version']}`",
        "",
        "## Summary",
        f"- added: {summary['added']}",
        f"- removed: {summary['removed']}",
        f"- changed: {summary['changed']}",
        f"- case_conflicts: {summary['case_conflicts']}",
        "",
        "## Added",
    ]
    if result["added"]:
        for item in result["added"]:
            lines.append(f"- `{item['normalized_path']}` -> `{item['path']}` (`{item['sha256'][:8]}...`)")
    else:
        lines.append("- None")

    lines.extend(["", "## Removed"])
    if result["removed"]:
        for item in result["removed"]:
            lines.append(f"- `{item['normalized_path']}` -> `{item['path']}` (`{item['sha256'][:8]}...`)")
    else:
        lines.append("- None")

    lines.extend(["", "## Changed"])
    if result["changed"]:
        for item in result["changed"]:
            lines.append(
                f"- `{item['normalized_path']}`: `{item['before']['sha256'][:8]}...`"
                f" -> `{item['after']['sha256'][:8]}...`"
            )
    else:
        lines.append("- None")

    lines.extend(["", "## Case Conflicts"])
    if result["case_conflicts"]:
        for item in result["case_conflicts"]:
            lines.append(f"- `{item['normalized_path']}`: `{item['before_path']}` -> `{item['after_path']}`")
    else:
        lines.append("- None")

    lines.extend(["", "## Profile and Required-Input Changes"])
    lines.append(f"- profile_changed: {changed_profile}")
    lines.extend([
        f"- required_files_added: `{', '.join(result['profile_required_input_changes']['required_files_added']) or 'none'}`",
        f"- required_files_removed: `{', '.join(result['profile_required_input_changes']['required_files_removed']) or 'none'}`",
        f"- required_missing_added: `{', '.join(result['profile_required_input_changes']['required_missing_added']) or 'none'}`",
        f"- required_missing_removed: `{', '.join(result['profile_required_input_changes']['required_missing_removed']) or 'none'}`",
    ])
    return "\n".join(lines) + "\n"


def compare_manifest_delta(before_path: Path, after_path: Path) -> dict[str, Any]:
    before_payload, before_files = validate_manifest(before_path)
    after_payload, after_files = validate_manifest(after_path)
    before_payload = dict(before_payload, manifest_path=str(before_path))
    after_payload = dict(after_payload, manifest_path=str(after_path))
    return compare_records((before_payload, before_files), (after_payload, after_files))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before_manifest", type=Path)
    parser.add_argument("after_manifest", type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    args = parser.parse_args()

    try:
        result = compare_manifest_delta(args.before_manifest, args.after_manifest)
    except ValueError as error:
        print(f"renegade_asset_manifest_delta: {error}", file=sys.stderr)
        return 2

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(format_markdown(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
