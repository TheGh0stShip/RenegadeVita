#!/usr/bin/env python3
"""Write deterministic metadata for local generated Renegade Vita cache files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from renegade_asset_cache_key import build_key
from renegade_asset_cache_verify import (CACHE_METADATA_NAME, CACHE_METADATA_SCHEMA,
                                         safe_artifact_path, sha256)


def build_metadata(cache_root: Path, manifest: dict[str, Any], options: dict[str, Any],
                   entries: list[tuple[str, str]]) -> dict[str, Any]:
    root = cache_root.resolve()
    seen: set[tuple[str, str]] = set()
    prepared: list[dict[str, str]] = []
    for logical, artifact_name in entries:
        if not logical or logical != logical.lower():
            raise ValueError("cache logical path must be normalized lowercase")
        artifact = safe_artifact_path(root, artifact_name)
        if artifact is None or not artifact.is_file():
            raise ValueError("cache artifact is missing or unsafe: " + artifact_name)
        order = (logical, artifact_name)
        if order in seen:
            raise ValueError("duplicate cache metadata entry: " + logical)
        seen.add(order)
        prepared.append({"logical_path": logical, "artifact": artifact_name,
                         "sha256": sha256(artifact)})
    if not prepared:
        raise ValueError("cache metadata requires at least one artifact")
    prepared.sort(key=lambda entry: (entry["logical_path"], entry["artifact"]))
    return {"schema_version": CACHE_METADATA_SCHEMA,
            "cache_key": build_key(manifest, options)["cache_key"],
            "entries": prepared}


def parse_entry(value: str) -> tuple[str, str]:
    logical, separator, artifact = value.partition("=")
    if not separator or not logical or not artifact:
        raise argparse.ArgumentTypeError("entry must be NORMALIZED_LOGICAL_PATH=RELATIVE_ARTIFACT")
    return logical, artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache_root", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--options", type=Path, required=True)
    parser.add_argument("--entry", type=parse_entry, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        options = json.loads(args.options.read_text(encoding="utf-8"))
        result = build_metadata(args.cache_root, manifest, options, args.entry)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"asset cache metadata: {error}")
    expected_output = args.cache_root.resolve() / CACHE_METADATA_NAME
    if args.output.resolve() != expected_output:
        raise SystemExit("asset cache metadata: output must be " + str(expected_output))
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"asset cache metadata: entries={len(result['entries'])} key={result['cache_key']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
