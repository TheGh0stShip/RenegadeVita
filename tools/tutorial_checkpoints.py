#!/usr/bin/env python3
"""Archive original M00 saves locally; restore only into a new, unused save slot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
from datetime import datetime, timezone

MAX_SAVE = 64 * 1024 * 1024
LEVEL_INFO = 1011991648
LEVEL_DATA = LEVEL_INFO + 1
DEFAULT_VAULT = Path(__file__).resolve().parents[1] / "build/tutorial-checkpoints"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,47}", value):
        raise ValueError("Checkpoint IDs must be 1-48 letters, digits, hyphens or underscores")
    return value


def read_save(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Save must be a regular file, not a symlink")
    before = path.stat()
    if not 16 <= before.st_size <= MAX_SAVE:
        raise ValueError("Save size is outside the bounded native-save range")
    data = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Save changed while being captured; wait for saving to finish")
    offset, map_name, have_data = 0, None, False
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("Truncated original save chunk header")
        chunk, size_flags = struct.unpack_from("<II", data, offset)
        size = size_flags & 0x7fffffff
        start, end = offset + 8, offset + 8 + size
        if end > len(data):
            raise ValueError("Original save chunk exceeds file bounds")
        if chunk == LEVEL_DATA:
            have_data = size > 0
        if chunk == LEVEL_INFO:
            cursor = start
            while cursor < end:
                if cursor + 2 > end:
                    raise ValueError("Truncated original save microchunk")
                kind, length = data[cursor:cursor + 2]
                cursor += 2
                if cursor + length > end:
                    raise ValueError("Original save microchunk exceeds level-info bounds")
                if kind == 1:
                    if map_name is not None:
                        raise ValueError("Ambiguous map identity")
                    map_name = data[cursor:cursor + length].rstrip(b"\0").decode("ascii")
                cursor += length
        offset = end
    if not have_data or map_name is None or map_name.lower() not in ("m00_tutorial.lsd", "m00_tutorial.mix"):
        raise ValueError("Not an original M00 tutorial save with level data")
    return data, map_name


def write_new(path, data):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "restore"))
    parser.add_argument("--id", required=True, type=safe_name)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--user-dir", type=Path, required=True)
    parser.add_argument("--content-id", required=True, help="Operator-supplied SHA256 identity of unchanged retail content")
    parser.add_argument("--compatibility", default="original-m00-save-v1", help="Save compatibility epoch, not a dev build number")
    parser.add_argument("--slot", help="Existing basename in user/save for capture; unused basename for restore")
    parser.add_argument("--build", help="Creating build, recorded as provenance only")
    evidence_group = parser.add_mutually_exclusive_group()
    evidence_group.add_argument("--passed-evidence", type=Path, help="Retained evidence for the operator-confirmed passed segment")
    evidence_group.add_argument("--evidence", type=Path, help="Retained checkpoint receipt; does not claim segment completion")
    parser.add_argument("--offline", action="store_true", help="Confirm the game is stopped before restoring")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-fA-F]{64}", args.content_id):
        raise ValueError("content-id must be a SHA256 hex identity")
    if args.user_dir.is_symlink() or args.user_dir.name.lower() != "user":
        raise ValueError("Use the actual Renegade user directory, not retail or a symlink")
    user = args.user_dir.resolve(strict=True)
    saves = user / "save"
    if saves.is_symlink():
        raise ValueError("Save directory cannot be a symlink")
    vault = args.vault.resolve()
    if vault == user or user in vault.parents:
        raise ValueError("Keep immutable checkpoint masters outside the live user tree")
    checkpoint = vault / args.id
    content_id = args.content_id.lower()
    if args.action == "capture":
        if not args.slot or not args.build or not (args.passed_evidence or args.evidence):
            raise ValueError("Capture requires slot, build, and evidence or passed-evidence")
        slot = args.slot
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.sav", slot, re.IGNORECASE):
            raise ValueError("slot must be a simple .sav basename")
        data, map_name = read_save(saves / slot)
        evidence = (args.passed_evidence or args.evidence).resolve(strict=True)
        if not evidence.is_file() or evidence.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("Use a bounded evidence receipt, not an arbitrary directory or dump")
        metadata = {
            "schema": 1, "id": args.id, "map": map_name, "save_sha256": digest(data),
            "content_id": content_id, "content_id_source": "OPERATOR_SUPPLIED",
            "compatibility": args.compatibility, "created_by_build": args.build,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "segment_status": "OPERATOR_ATTESTED_PASSED" if args.passed_evidence else "UNASSESSED",
            "source_slot": slot,
            "evidence_path": str(evidence), "evidence_sha256": digest(evidence.read_bytes()),
            "cross_build_load_validated": False,
        }
        vault.mkdir(parents=True, exist_ok=True)
        checkpoint.mkdir()  # Never replace an existing master.
        write_new(checkpoint / "checkpoint.sav", data)
        write_new(checkpoint / "manifest.json", (json.dumps(metadata, indent=2) + "\n").encode("ascii"))
        (checkpoint / "checkpoint.sav").chmod(0o444)
        (checkpoint / "manifest.json").chmod(0o444)
        print(json.dumps({"status": "ARCHIVED_UNCHANGED_NATIVE_SAVE", "checkpoint": str(checkpoint), "save_sha256": digest(data)}))
    else:
        if not args.offline:
            raise ValueError("Restore requires --offline; stop the game first")
        if checkpoint.is_symlink() or (checkpoint / "manifest.json").is_symlink():
            raise ValueError("Checkpoint master cannot be a symlink")
        metadata = json.loads((checkpoint / "manifest.json").read_text(encoding="ascii"))
        if metadata.get("schema") != 1 or metadata.get("id") != args.id:
            raise ValueError("Checkpoint manifest identity mismatch")
        if metadata.get("content_id") != content_id or metadata.get("compatibility") != args.compatibility:
            raise ValueError("Retail content or save compatibility epoch differs; do not reuse this checkpoint")
        data, map_name = read_save(checkpoint / "checkpoint.sav")
        if digest(data) != metadata.get("save_sha256") or map_name != metadata.get("map"):
            raise ValueError("Checkpoint master integrity mismatch")
        slot = args.slot or ("rv_cp_" + args.id + ".sav")
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.sav", slot, re.IGNORECASE) or len(slot) > 85:
            raise ValueError("Use a simple .sav basename under 86 characters")
        saves.mkdir(exist_ok=True)
        destination = saves / slot
        write_new(destination, data)  # Exclusive create: never overwrite live slots.
        print(json.dumps({"status": "RESTORED_NEW_SLOT_NOT_LOAD_VALIDATION", "slot": str(destination), "save_sha256": digest(data)}))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, UnicodeError) as error:
        raise SystemExit(str(error))
