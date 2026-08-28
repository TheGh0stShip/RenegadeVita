#!/usr/bin/env python3
"""Content-preserving sync for deterministic staged source trees.

The canonical staging script deliberately creates a fresh tree.  Fast iteration
builds need the same deterministic staged contents without touching every
unchanged file and invalidating Ninja's dependency graph.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import tempfile
from pathlib import Path


def _relative_files(root: Path) -> set[Path]:
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }


def _copy_replacing(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".stage-sync", dir=target.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        if source.is_symlink():
            temporary.unlink()
            os.symlink(os.readlink(source), temporary)
        else:
            shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()


def sync_managed_dir(source_root: Path, target_root: Path, managed_dir: str) -> dict[str, int]:
    relative = Path(managed_dir)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"managed directory must be a safe relative path: {managed_dir}")

    source = source_root / relative
    target = target_root / relative
    if not source.is_dir():
        raise FileNotFoundError(f"source managed directory is absent: {source}")
    target.mkdir(parents=True, exist_ok=True)

    counts = {
        "copied": 0,
        "unchanged": 0,
        "metadata_updated": 0,
        "removed": 0,
        "directories_created": 0,
        "directories_removed": 0,
    }

    source_files = _relative_files(source)
    target_files = _relative_files(target)

    for stale in sorted(target_files - source_files, reverse=True):
        stale_target = target / stale
        stale_target.unlink()
        counts["removed"] += 1

    for item in sorted(source.rglob("*")):
        if item.is_dir():
            destination = target / item.relative_to(source)
            if not destination.exists():
                destination.mkdir(parents=True, exist_ok=True)
                counts["directories_created"] += 1

    for relative_file in sorted(source_files):
        source_file = source / relative_file
        target_file = target / relative_file
        if target_file.exists() or target_file.is_symlink():
            same_kind = source_file.is_symlink() == target_file.is_symlink()
            if same_kind and source_file.is_symlink():
                if os.readlink(source_file) == os.readlink(target_file):
                    counts["unchanged"] += 1
                    continue
            elif same_kind and filecmp.cmp(source_file, target_file, shallow=False):
                source_mode = source_file.stat().st_mode & 0o777
                target_mode = target_file.stat().st_mode & 0o777
                if source_mode != target_mode:
                    os.chmod(target_file, source_mode)
                    counts["metadata_updated"] += 1
                counts["unchanged"] += 1
                continue
        _copy_replacing(source_file, target_file)
        counts["copied"] += 1

    for directory, _, _ in os.walk(target, topdown=False):
        directory_path = Path(directory)
        if directory_path == target:
            continue
        try:
            directory_path.rmdir()
            counts["directories_removed"] += 1
        except OSError:
            pass

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--managed-dir", action="append", required=True)
    parser.add_argument("--summary-json", type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    target = args.target.resolve()
    if not source.is_dir():
        parser.error(f"--source is not a directory: {source}")
    target.mkdir(parents=True, exist_ok=True)

    totals = {
        "managed_dirs": len(args.managed_dir),
        "copied": 0,
        "unchanged": 0,
        "metadata_updated": 0,
        "removed": 0,
        "directories_created": 0,
        "directories_removed": 0,
    }
    per_dir = {}
    for managed_dir in args.managed_dir:
        counts = sync_managed_dir(source, target, managed_dir)
        per_dir[managed_dir] = counts
        for key, value in counts.items():
            totals[key] += value

    result = {"status": "PASS", "source": str(source), "target": str(target), "totals": totals, "managed_dirs": per_dir}
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
