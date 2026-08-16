#!/usr/bin/env python3
"""Verify a local Renegade Vita cache without extracting retail assets.

The verifier accepts only versioned metadata and relative generated artifacts.
It never opens a retail archive, converts content, or rebuilds a cache.  A
future Vita cache writer can use the same metadata contract to distinguish a
missing cache from a stale source/options key and a corrupt generated entry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from renegade_asset_cache_key import build_key

CACHE_METADATA_NAME = "cache-metadata-v1.json"
CACHE_METADATA_SCHEMA = 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_artifact_path(cache_root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    root = cache_root.resolve()
    candidate = root.joinpath(*relative.parts)
    try:
        candidate.resolve().relative_to(root)
    except ValueError:
        return None
    return candidate


def verify_cache(cache_root: Path, manifest: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    expected = build_key(manifest, options)["cache_key"]
    root = cache_root.resolve()
    metadata_path = root / CACHE_METADATA_NAME
    result: dict[str, Any] = {
        "schema_version": 1,
        "cache_key_expected": expected,
        "state": "valid",
        "reasons": [],
        "entries": [],
    }
    if not metadata_path.is_file():
        result["state"] = "missing"
        result["reasons"] = ["cache metadata is missing"]
        return result
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        result["state"] = "corrupt"
        result["reasons"] = [f"cache metadata is unreadable: {error}"]
        return result
    if not isinstance(metadata, dict):
        result["state"] = "corrupt"
        result["reasons"] = ["cache metadata root is not an object"]
        return result
    if metadata.get("schema_version") != CACHE_METADATA_SCHEMA:
        result["state"] = "stale"
        result["reasons"].append("cache metadata schema does not match")
    if metadata.get("cache_key") != expected:
        result["state"] = "stale"
        result["reasons"].append("cache key does not match manifest/options")
    entries = metadata.get("entries")
    if not isinstance(entries, list):
        result["state"] = "corrupt"
        result["reasons"].append("cache entries are missing or not a list")
        result["reasons"].sort()
        return result
    previous: tuple[str, str] | None = None
    for entry in entries:
        if not isinstance(entry, dict):
            result["state"] = "corrupt"
            result["reasons"].append("cache entry is not an object")
            continue
        logical = entry.get("logical_path")
        artifact_name = entry.get("artifact")
        declared_hash = entry.get("sha256")
        if not isinstance(logical, str) or not logical or logical != logical.lower():
            result["state"] = "corrupt"
            result["reasons"].append("cache entry logical_path is not normalized")
            continue
        artifact_path = safe_artifact_path(root, artifact_name)
        if artifact_path is None:
            result["state"] = "corrupt"
            result["reasons"].append("cache entry artifact path is unsafe")
            continue
        if not isinstance(declared_hash, str) or len(declared_hash) != 64 or \
                any(character not in "0123456789abcdef" for character in declared_hash):
            result["state"] = "corrupt"
            result["reasons"].append("cache entry SHA-256 is invalid")
            continue
        order = (logical, artifact_name)
        if previous is not None and order <= previous:
            result["state"] = "corrupt"
            result["reasons"].append("cache entries are not strictly sorted")
        previous = order
        item = {"artifact": artifact_name, "logical_path": logical,
                "sha256": declared_hash, "status": "valid"}
        if not artifact_path.is_file():
            item["status"] = "missing"
            result["state"] = "corrupt"
            result["reasons"].append(f"cache artifact is missing: {artifact_name}")
        elif sha256(artifact_path) != declared_hash:
            item["status"] = "hash_mismatch"
            result["state"] = "corrupt"
            result["reasons"].append(f"cache artifact hash mismatch: {artifact_name}")
        result["entries"].append(item)
    result["entries"].sort(key=lambda entry: (entry["logical_path"], entry["artifact"]))
    result["reasons"] = sorted(set(result["reasons"]))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache_root", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--options", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        options = json.loads(args.options.read_text(encoding="utf-8"))
        result = verify_cache(args.cache_root, manifest, options)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"asset cache verify: {error}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"asset cache verify: state={result['state']} entries={len(result['entries'])}")
    return 0 if result["state"] == "valid" else 3


if __name__ == "__main__":
    raise SystemExit(main())
