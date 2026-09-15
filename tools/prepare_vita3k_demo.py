#!/usr/bin/env python3
"""Back up and install only RNEGA3101 into an existing local Vita3K VFS."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile

from renegade_asset_manifest import build_manifest


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vpk", type=Path, required=True)
    parser.add_argument("--vfs", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--retail-source", type=Path,
                        default=Path(__file__).resolve().parents[1] / "retail-pc/Data")
    args = parser.parse_args()
    if not args.candidate or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for c in args.candidate):
        raise SystemExit("Unsafe candidate label")
    vfs = args.vfs.resolve(strict=True)
    retail = vfs / "ux0/data/renegade/retail/Data"
    requirements = ["always.dat", "always.dbs", "always2.dat", "m00_tutorial.mix"]
    entries = {p.name.lower(): p for p in retail.iterdir() if p.is_file()}
    missing = [name for name in requirements if name not in entries]
    movies = next((p for p in retail.iterdir() if p.is_dir() and p.name.lower() == "movies"), None)
    movie_entries = {} if movies is None else {p.name.lower(): p for p in movies.iterdir() if p.is_file()}
    missing += [name for name in ("ea_ww.bik", "r_intro.bik") if name not in movie_entries]
    shader_module = vfs / "ur0/data/libshacccg.suprx"
    if missing or not shader_module.is_file():
        raise SystemExit(f"Existing emulator prerequisites missing: retail={missing}; shader_module={shader_module.is_file()}")
    # Prerequisite checks alone never establish complete source coverage.
    source_manifest = build_manifest(args.retail_source)
    installed_manifest = build_manifest(retail)
    source_files = {p["normalized_path"]: p for p in source_manifest["files"]}
    installed_files = {p["normalized_path"]: p for p in installed_manifest["files"]}
    unmatched = [name for name, entry in source_files.items() if name not in installed_files or
                 (entry["size"], entry["sha256"]) !=
                 (installed_files[name]["size"], installed_files[name]["sha256"])]
    if not source_manifest["valid"] or not installed_manifest["valid"] or unmatched:
        raise SystemExit(f"Retail source coverage failed; repair before installing title: {unmatched}")
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%S%fZ")
    evidence = args.evidence_root.resolve() / f"{args.candidate}-setup-{timestamp}"
    evidence.mkdir(parents=True, exist_ok=False)
    target = vfs / "ux0/app/RNEGA3101"
    receipt = {
        "schema": 1, "candidate": args.candidate, "title_id": "RNEGA3101",
        "evidence_class": "vita3k_setup", "physical_acceptance": False,
        "vpk_sha256": digest(args.vpk), "retail_modified": False,
        "vfs": str(vfs), "status": "PREPARING", "files": [],
        "retail_files": [],
        "retail_source_coverage": {
            "source_root": str(args.retail_source.resolve()),
            "source_files": len(source_files), "installed_files": len(installed_files),
            "source_content_digest": source_manifest["content_digest"],
            "installed_content_digest": installed_manifest["content_digest"],
            "unmatched_source_files": unmatched,
            "extra_files_preserved": sorted(installed_files.keys() - source_files.keys()),
            "runtime_consumption_proven": False,
        },
    }
    receipt_path = evidence / "setup-receipt.json"

    def save() -> None:
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    # Record metadata rather than copying any retail bytes into diagnostics.
    for name in requirements:
        path = entries[name]
        receipt["retail_files"].append({"path": str(path), "bytes": path.stat().st_size, "sha256": digest(path)})
    for name in ("ea_ww.bik", "r_intro.bik"):
        path = movie_entries[name]
        receipt["retail_files"].append({"path": str(path), "bytes": path.stat().st_size, "sha256": digest(path)})
    save()
    try:
        with zipfile.ZipFile(args.vpk) as archive:
            files = [item for item in archive.infolist() if not item.is_dir()]
            names = set()
            for item in files:
                path = PurePosixPath(item.filename)
                key = item.filename.casefold()
                if (path.is_absolute() or ".." in path.parts or "\\" in item.filename or
                        ":" in item.filename or key in names or
                        stat.S_ISLNK(item.external_attr >> 16) or
                        not (item.filename == "eboot.bin" or path.parts[0] == "sce_sys") or
                        item.file_size > 128 * 1024 * 1024):
                    raise ValueError(f"Refusing non-title or unsafe VPK member: {item.filename}")
                names.add(key)
            if "eboot.bin" not in names or "sce_sys/param.sfo" not in names:
                raise ValueError("VPK lacks required title members")
            # Never follow a title-tree symlink into another app or user data.
            for item in files:
                destination = target / item.filename
                for component in (destination, *destination.parents):
                    if component == vfs:
                        break
                    if component.is_symlink():
                        raise ValueError(f"Refusing symlink in title path: {component}")
            for item in files:
                destination = target / item.filename
                backup = evidence / "title-backup" / item.filename
                before = None
                if destination.exists():
                    before = digest(destination)
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(destination, backup)
                receipt["files"].append({"name": item.filename, "before_sha256": before})
                save()
            for item, entry in zip(files, receipt["files"]):
                destination = target / item.filename
                destination.parent.mkdir(parents=True, exist_ok=True)
                # ZIP CRC is checked while reading, before replacing this file.
                payload = archive.read(item)
                destination.write_bytes(payload)
                entry["installed_sha256"] = hashlib.sha256(payload).hexdigest()
                save()
        receipt["status"] = "INSTALLED_NOT_LAUNCHED"
    except Exception as error:
        receipt["status"] = "FAILED_ROLLED_BACK"
        receipt["error"] = str(error)
        for entry in receipt["files"]:
            destination = target / entry["name"]
            backup = evidence / "title-backup" / entry["name"]
            if entry["before_sha256"] is not None:
                shutil.copy2(backup, destination)
            elif destination.exists():
                destination.unlink()
        raise
    finally:
        save()
    print(json.dumps({"status": receipt["status"], "receipt": str(receipt_path)}))


if __name__ == "__main__":
    main()
