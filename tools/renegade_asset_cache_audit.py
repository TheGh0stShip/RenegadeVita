#!/usr/bin/env python3
"""Audit Renegade Vita cache consistency across schema, key, manifest/options, and artifact content.

The auditor is read-only for cache content:
- it never builds or writes cache artifacts,
- it does not open retail archives,
- it only inspects the cache metadata sidecar, verification report, manifest,
  options, and declared artifact path.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from renegade_asset_cache_key import CACHE_FORMAT_VERSION, TOOL_VERSION, build_key
from renegade_asset_cache_verify import (
    CACHE_METADATA_NAME,
    CACHE_METADATA_SCHEMA,
    safe_artifact_path,
    sha256,
    verify_cache,
)


def _canonical_hex_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{label} must be a 64-char hex digest")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(f"{label} must be valid hexadecimal: {error}") from None
    return value.lower()


def _validate_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise ValueError("manifest payload must be an object")
    required = {"valid", "schema_version", "content_digest", "file_count"}
    missing = required - set(manifest)
    if missing:
        raise ValueError(f"manifest missing keys: {', '.join(sorted(missing))}")
    if not isinstance(manifest["valid"], bool):
        raise ValueError("manifest valid must be a boolean")
    if not manifest["valid"]:
        raise ValueError("manifest valid must be true")
    if not isinstance(manifest["schema_version"], int):
        raise ValueError("manifest schema_version must be an integer")
    if not isinstance(manifest["content_digest"], str):
        raise ValueError("manifest content_digest must be a string")
    if not isinstance(manifest["file_count"], int) or manifest["file_count"] < 0:
        raise ValueError("manifest file_count must be a non-negative integer")
    return {
        "schema_version": manifest["schema_version"],
        "content_digest": _canonical_hex_digest(manifest["content_digest"], "manifest content_digest"),
        "file_count": manifest["file_count"],
    }


def _validate_options(options: Any) -> dict[str, Any]:
    if not isinstance(options, dict):
        raise ValueError("options payload must be an object")
    return options


def _raise_state(current: str, next_state: str) -> str:
    order = {"valid": 0, "stale": 1, "corrupt": 2, "missing": 3, "unsafe": 4}
    return next_state if order[next_state] > order[current] else current


def _load_metadata(root: Path) -> dict[str, Any]:
    metadata_path = root / CACHE_METADATA_NAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("cache metadata must be an object")
    if metadata.get("schema_version") != CACHE_METADATA_SCHEMA:
        raise ValueError("cache metadata schema_version does not match expected")
    entries = metadata.get("entries")
    if not isinstance(entries, list):
        raise ValueError("cache metadata entries must be a list")
    if not entries:
        raise ValueError("cache metadata has no entries")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"cache metadata entry #{index} must be an object")
    return metadata


def _sorted_unique(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted((dict(sorted(item.items())) for item in findings), key=lambda item: (item.get("state", ""), item.get("code", "")))


def _artifact_entry(metadata: dict[str, Any], artifact: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    matches = [entry for entry in metadata.get("entries", []) if entry.get("artifact") == artifact]
    if not matches:
        return None, []
    duplicate_artifact = len(matches) > 1
    matches.sort(key=lambda item: (item.get("logical_path", ""), item.get("artifact", "")))
    return matches[0], ([
        {"code": "metadata.artifact.duplicate", "state": "corrupt", "message": "multiple metadata entries share the declared artifact"}
    ] if duplicate_artifact else [])


def audit_cache(cache_root: Path, manifest: dict[str, Any], options: dict[str, Any], index_artifact: str) -> dict[str, Any]:
    root = cache_root.resolve()
    manifest_validated = _validate_manifest(manifest)
    _ = _validate_options(options)
    expected = build_key(manifest, options)
    verification = verify_cache(root, manifest, options)

    result: dict[str, Any] = {
        "state": verification["state"],
        "cache_root": str(root),
        "schema": {
            "manifest": manifest_validated["schema_version"],
            "metadata": CACHE_METADATA_SCHEMA,
            "cache_format_version": expected["cache_format_version"],
            "tool_version": expected["tool_version"],
        },
        "source": {
            "manifest_schema": expected["source"]["manifest_schema"],
            "content_digest": expected["source"]["content_digest"],
            "file_count": expected["source"]["file_count"],
        },
        "cache_key": {
            "expected": expected["cache_key"],
            "metadata": expected["cache_key"],
            "verification_expected": verification.get("cache_key_expected"),
        },
        "artifact": {
            "declared": index_artifact,
            "status": "missing",
            "size": None,
            "sha256": None,
            "expected_sha256": None,
            "safe": False,
        },
        "verification": verification,
        "findings": [],
    }

    metadata: dict[str, Any] | None = None
    try:
        metadata = _load_metadata(root)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        message = str(error).lower()
        next_state = "stale" if "schema_version" in message else "corrupt"
        result["state"] = _raise_state(result["state"], next_state)
        result["findings"].append({
            "code": "metadata.unreadable",
            "state": "corrupt",
            "message": f"cache metadata could not be read: {error}",
        })
    else:
        result["cache_key"]["metadata"] = metadata.get("cache_key", expected["cache_key"])
        if metadata.get("cache_key") != expected["cache_key"]:
            result["state"] = _raise_state(result["state"], "stale")
            result["findings"].append({
                "code": "cache_key.mismatch",
                "state": "stale",
                "message": "metadata cache_key does not match manifest/options",
            })
        if verification.get("cache_key_expected") != expected["cache_key"]:
            result["state"] = _raise_state(result["state"], "stale")
            result["findings"].append({
                "code": "verification.key_mismatch",
                "state": "stale",
                "message": "verification cache key expectation does not match manifest/options",
            })
        if expected["source"]["content_digest"] != manifest_validated["content_digest"]:
            result["state"] = _raise_state(result["state"], "stale")
            result["findings"].append({
                "code": "manifest.content_digest.mismatch",
                "state": "stale",
                "message": "source content digest changed",
            })
        if expected["cache_format_version"] != CACHE_FORMAT_VERSION:
            result["state"] = _raise_state(result["state"], "corrupt")
            result["findings"].append({
                "code": "tool.cache_format_version.mismatch",
                "state": "corrupt",
                "message": "cache format version does not match expected schema",
            })
        if expected["tool_version"] != TOOL_VERSION:
            result["state"] = _raise_state(result["state"], "corrupt")
            result["findings"].append({
                "code": "tool.tool_version.mismatch",
                "state": "corrupt",
                "message": "tool version does not match runtime contract",
            })
        if not safe_artifact_path(root, index_artifact):
            result["state"] = _raise_state(result["state"], "unsafe")
            result["findings"].append({
                "code": "artifact.unsafe_path",
                "state": "unsafe",
                "message": "declared index artifact is outside cache root or not POSIX-safe",
            })
            result["artifact"]["safe"] = False
        else:
            result["artifact"]["safe"] = True
        entry, duplicate_findings = _artifact_entry(metadata, index_artifact)
        result["findings"].extend(duplicate_findings)
        for finding in duplicate_findings:
            result["state"] = _raise_state(result["state"], finding["state"])

        if entry is None:
            result["state"] = _raise_state(result["state"], "missing")
            result["findings"].append({
                "code": "artifact.missing",
                "state": "missing",
                "message": "declared index artifact is not recorded in metadata",
            })
            result["artifact"]["status"] = "missing"
        else:
            result["artifact"]["expected_sha256"] = entry.get("sha256")
            declared_hash = entry.get("sha256")
            if not isinstance(declared_hash, str):
                result["state"] = _raise_state(result["state"], "corrupt")
                result["findings"].append({
                    "code": "artifact.sha256.invalid_type",
                    "state": "corrupt",
                    "message": "metadata artifact SHA-256 is not a string",
                })
            else:
                declared_hash = declared_hash.lower()
                if len(declared_hash) != 64 or any(char not in "0123456789abcdef" for char in declared_hash):
                    result["state"] = _raise_state(result["state"], "corrupt")
                    result["findings"].append({
                        "code": "artifact.sha256.invalid_format",
                        "state": "corrupt",
                        "message": "metadata artifact SHA-256 is malformed",
                    })
                else:
                    result["artifact"]["expected_sha256"] = declared_hash
            artifact_path = safe_artifact_path(root, index_artifact)
            if artifact_path is None:
                result["state"] = _raise_state(result["state"], "unsafe")
                result["artifact"]["status"] = "unsafe"
            else:
                if not artifact_path.is_file():
                    result["state"] = _raise_state(result["state"], "missing")
                    result["artifact"]["status"] = "missing"
                else:
                    result["artifact"]["size"] = artifact_path.stat().st_size
                    result["artifact"]["sha256"] = sha256(artifact_path)
                    if result["artifact"]["expected_sha256"] and result["artifact"]["sha256"] != result["artifact"]["expected_sha256"]:
                        result["state"] = _raise_state(result["state"], "corrupt")
                        result["artifact"]["status"] = "corrupt"
                        result["findings"].append({
                            "code": "artifact.sha256.mismatch",
                            "state": "corrupt",
                            "message": f"cache artifact SHA-256 mismatch: {index_artifact}",
                        })
                    else:
                        result["artifact"]["status"] = "valid"
            if result["artifact"]["status"] != "unsafe" and isinstance(entry.get("size"), int):
                if result["artifact"]["size"] is None:
                    result["artifact"]["status"] = "missing"
                    result["state"] = _raise_state(result["state"], "missing")
                    result["findings"].append({
                        "code": "artifact.size.missing",
                        "state": "missing",
                        "message": f"declared artifact size exists but artifact path is missing: {index_artifact}",
                    })
                elif entry["size"] != result["artifact"]["size"]:
                    result["state"] = _raise_state(result["state"], "corrupt")
                    result["findings"].append({
                        "code": "artifact.size.mismatch",
                        "state": "corrupt",
                        "message": "declared artifact size does not match filesystem size",
                    })
                else:
                    result["findings"].append({
                        "code": "artifact.size.match",
                        "state": "valid",
                        "message": "artifact size matches declared metadata",
                    })

            logical_path = entry.get("logical_path")
            if not isinstance(logical_path, str) or not logical_path or logical_path != logical_path.lower():
                result["state"] = _raise_state(result["state"], "corrupt")
                result["findings"].append({
                    "code": "artifact.logical_path.invalid",
                    "state": "corrupt",
                    "message": "metadata logical_path is not normalized",
                })

    result["findings"] = _sorted_unique(result["findings"])
    if result["state"] == "valid" and not result["findings"]:
        result["findings"].append({
            "code": "audit.ok",
            "state": "valid",
            "message": "cache metadata, verification, manifest/options, and declared artifact are consistent",
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache_root", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--options", type=Path, required=True)
    parser.add_argument("--index-artifact", "--artifact", "--declared-index-artifact", dest="index_artifact", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        options = json.loads(args.options.read_text(encoding="utf-8"))
        result = audit_cache(args.cache_root, manifest, options, args.index_artifact)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"asset cache audit: {error}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"asset cache audit: state={result['state']} artifact={args.index_artifact}")
    return 0 if result["state"] == "valid" else 3


if __name__ == "__main__":
    raise SystemExit(main())
