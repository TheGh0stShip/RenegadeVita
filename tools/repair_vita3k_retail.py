#!/usr/bin/env python3
"""Reconcile local Vita3K Data with user-owned retail; retain metadata/backups only locally."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import tempfile
import zlib

from renegade_asset_manifest import build_manifest, sha256


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def archive_inventory(path: Path) -> list[str]:
    size = path.stat().st_size
    with path.open("rb") as stream:
        magic, index, names = struct.unpack("<4sII", stream.read(12))
        if magic != b"MIX1" or not (12 <= index <= size - 4 and 12 <= names <= size - 4):
            raise ValueError(f"Invalid MIX1 header: {path.name}")
        stream.seek(index)
        count = struct.unpack("<I", stream.read(4))[0]
        if count > 1000000 or index + 4 + count * 12 > size:
            raise ValueError(f"Invalid MIX1 index bounds: {path.name}")
        entries = [struct.unpack("<III", stream.read(12)) for _ in range(count)]
        keys = [entry[0] for entry in entries]
        if keys != sorted(keys) or len(set(keys)) != len(keys):
            raise ValueError(f"Invalid MIX1 lookup ordering: {path.name}")
        if any(offset < 12 or offset + length > size for _, offset, length in entries):
            raise ValueError(f"Invalid MIX1 payload bounds: {path.name}")
        stream.seek(names)
        name_count = struct.unpack("<I", stream.read(4))[0]
        if name_count != count:
            raise ValueError(f"MIX1 name/index count mismatch: {path.name}")
        known = set(keys)
        result = []
        for _ in range(name_count):
            length = stream.read(1)
            if not length or length[0] == 0:
                raise ValueError(f"Invalid MIX1 name length: {path.name}")
            raw = stream.read(length[0])
            if len(raw) != length[0] or raw[-1:] != b"\0":
                raise ValueError(f"Truncated MIX1 name: {path.name}")
            name = raw[:-1].decode("ascii")
            if zlib.crc32(name.upper().encode("ascii")) not in known:
                raise ValueError(f"MIX1 name has no indexed payload: {path.name}: {name}")
            result.append(name)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--runtime-log", type=Path)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    destination = args.destination.resolve(strict=True)
    if source.name.lower() != "data" or not destination.as_posix().lower().endswith(
            "/ux0/data/renegade/retail/data"):
        raise SystemExit("Expected source Data and title-scoped Vita3K retail/Data")
    if source == destination or source in destination.parents or destination in source.parents:
        raise SystemExit("Source and destination must be separate")
    for root in (source, destination):
        if any(p.is_symlink() for p in root.rglob("*")):
            raise SystemExit("Refusing symlinks inside retail Data")
    evidence = args.evidence.resolve()
    if any(evidence == root or root in evidence.parents for root in (source, destination)):
        raise SystemExit("Evidence must be outside retail")
    evidence.mkdir(parents=True, exist_ok=False)
    original = build_manifest(source)
    before = build_manifest(destination)
    save(evidence / "source.json", original)
    save(evidence / "before.json", before)
    if not original["valid"] or original["case_conflicts"] or before["case_conflicts"]:
        raise SystemExit("Source prerequisites or case-identity audit failed")
    source_files = {p["normalized_path"]: p for p in original["files"]}
    target_files = {p["normalized_path"]: p for p in before["files"]}
    changes = []
    for key, entry in source_files.items():
        old = target_files.get(key)
        if old is None or (old["size"], old["sha256"]) != (entry["size"], entry["sha256"]):
            changes.append({"source": entry["path"], "target": old["path"] if old else entry["path"],
                            "before_sha256": old["sha256"] if old else None,
                            "source_sha256": entry["sha256"], "status": "PLANNED"})
    receipt = {"schema": 1, "source_root": str(source), "destination_root": str(destination),
               "status": "PLANNED", "changes": changes, "extra_files_preserved": sorted(target_files.keys() - source_files.keys()),
               "physical_access": False, "retail_distributed": False}
    save(evidence / "receipt.json", receipt)
    # Back up every existing changed file before the first retail mutation.
    for change in changes:
        if change["before_sha256"] is not None:
            backup = evidence / "backups" / change["target"]
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination / change["target"], backup)
            if sha256(backup) != change["before_sha256"]:
                raise SystemExit("Backup hash mismatch; retail has not been changed")
    for change in changes:
        target = destination / change["target"]
        current = sha256(target) if target.exists() else None
        if current != change["before_sha256"]:
            raise SystemExit("Destination changed after audit; refusing overwrite")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".rv-retail-", delete=False) as output:
                temporary = Path(output.name)
                with (source / change["source"]).open("rb") as incoming:
                    shutil.copyfileobj(incoming, output, 1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
            if sha256(temporary) != change["source_sha256"]:
                raise SystemExit("Source changed during copy; refusing replacement")
            if change["before_sha256"] is None:
                # Exclusive creation also protects against newly appeared files.
                with target.open("xb") as output, temporary.open("rb") as incoming:
                    shutil.copyfileobj(incoming, output, 1024 * 1024)
                    output.flush()
                    os.fsync(output.fileno())
            else:
                os.replace(temporary, target)
                temporary = None
            change["installed_sha256"] = sha256(target)
            change["status"] = "COPIED" if change["installed_sha256"] == change["source_sha256"] else "HASH_FAILED"
            save(evidence / "receipt.json", receipt)
            if change["status"] != "COPIED":
                raise SystemExit("Installed content failed hash verification")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    after = build_manifest(destination)
    save(evidence / "after.json", after)
    installed = {p["normalized_path"]: p for p in after["files"]}
    unmatched = [key for key, entry in source_files.items() if key not in installed or
                 (entry["size"], entry["sha256"]) != (installed[key]["size"], installed[key]["sha256"])]
    archive_entries: dict[str, list[str]] = {}
    archive_results = []
    archive_errors = []
    for entry in after["files"]:
        path = destination / entry["path"]
        if path.suffix.lower() not in (".dat", ".dbs", ".mix"):
            continue
        try:
            names = archive_inventory(path)
            archive_results.append({"archive": entry["path"], "entries": len(names), "status": "INDEX_AND_BOUNDS_VALID"})
            for name in names:
                archive_entries.setdefault(name.replace("\\", "/").lower(), []).append(entry["path"])
        except (ValueError, OSError, struct.error) as error:
            archive_errors.append(str(error))
    save(evidence / "archives.json", {"archives": archive_results, "errors": archive_errors,
                                      "reticle_archives": archive_entries.get("hd_reticle.dds", [])})
    unresolved = []
    if args.runtime_log:
        requests = set()
        with args.runtime_log.open(errors="replace") as log:
            for line in log:
                if "Missing file at" in line:
                    match = re.search(r'retail/([^"\r\n]+)', line)
                    if match:
                        requests.add(match.group(1).replace("\\", "/").lower())
        resolved = []
        for name in sorted(requests):
            relative = name[5:] if name.startswith("data/") else name
            if relative in installed:
                resolved.append({"request": name, "available_as": "loose_Data", "path": installed[relative]["path"]})
            elif relative in archive_entries:
                resolved.append({"request": name, "available_in_archives": archive_entries[relative]})
            elif relative.endswith(".tga") and relative[:-4] + ".dds" in archive_entries:
                resolved.append({"request": name, "dds_alias_in_archives": archive_entries[relative[:-4] + ".dds"]})
            else:
                unresolved.append(name)
        save(evidence / "logged-lookups.json", {"unique_loose_misses": len(requests), "available": resolved,
                                               "not_found_in_retail": unresolved, "runtime_consumption_proven": False})
    receipt.update(status="SOURCE_COVERAGE_AND_ARCHIVE_INDEX_PASS" if not unmatched and not archive_errors else "AUDIT_FAILED",
                   source_files=len(source_files), installed_files=len(installed), unmatched_source_files=unmatched,
                   archive_count=len(archive_results), archive_errors=archive_errors,
                   unresolved_logged_retail_probes=unresolved, runtime_consumption_proven=False,
                   source_content_digest=original["content_digest"], installed_content_digest=after["content_digest"])
    save(evidence / "receipt.json", receipt)
    print(json.dumps(receipt, indent=2))
    if unmatched or archive_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
