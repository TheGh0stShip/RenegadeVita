#!/usr/bin/env python3
"""Create a deterministic cache identity for locally generated Vita assets.

No asset bytes are converted or copied. A future importer must require this
identity before accepting a cache entry, preventing stale source/options use.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib

CACHE_FORMAT_VERSION = 1
TOOL_VERSION = "1.0"

def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")

def build_key(manifest: dict, options: dict) -> dict:
    if not manifest.get("valid", False):
        raise ValueError("refusing cache identity for an invalid retail manifest")
    source = {"manifest_schema": manifest.get("schema_version"),
              "content_digest": manifest.get("content_digest"),
              "file_count": manifest.get("file_count")}
    key_input = {"cache_format_version": CACHE_FORMAT_VERSION, "tool_version": TOOL_VERSION,
                 "source": source, "options": options}
    return {**key_input, "cache_key": hashlib.sha256(canonical(key_input)).hexdigest()}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=pathlib.Path)
    parser.add_argument("--options", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        options = json.loads(args.options.read_text(encoding="utf-8"))
        result = build_key(manifest, options)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"asset cache key: {error}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"asset cache key: {result['cache_key']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
