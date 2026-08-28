#!/usr/bin/env python3
"""Compare two VitaDevBridge crash snapshots and report newly observed dumps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _snapshot_entries(document: dict) -> list[dict]:
    if isinstance(document.get("entries"), list):
        return document["entries"]
    result = document.get("result")
    if isinstance(result, dict):
        snapshot = result.get("snapshot")
        if isinstance(snapshot, dict) and isinstance(snapshot.get("entries"), list):
            return snapshot["entries"]
    raise ValueError("input does not contain a VDB crash snapshot entries array")


def _valid_entry(entry: dict) -> bool:
    return (
        isinstance(entry.get("path"), str)
        and isinstance(entry.get("sha256"), str)
        and len(entry["sha256"]) == 64
        and isinstance(entry.get("size"), int)
        and entry["size"] >= 0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline")
    parser.add_argument("current")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    current = json.loads(Path(args.current).read_text(encoding="utf-8"))
    baseline_entries = [entry for entry in _snapshot_entries(baseline) if _valid_entry(entry)]
    current_entries = [entry for entry in _snapshot_entries(current) if _valid_entry(entry)]
    baseline_hashes = {entry["sha256"] for entry in baseline_entries}
    new_entries = [entry for entry in current_entries if entry["sha256"] not in baseline_hashes]
    payload = {
        "schema_version": 1,
        "baseline_count": len(baseline_entries),
        "current_count": len(current_entries),
        "new_count": len(new_entries),
        "new_entries": new_entries,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
