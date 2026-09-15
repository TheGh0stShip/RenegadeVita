#!/usr/bin/env python3
"""Queue a one-shot developer save launch; native original code must validate M00."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile


def queue_request(user_dir, slot, receipt):
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.[sS][aA][vV]", slot) is None:
        raise ValueError("Expected a simple original .sav basename, maximum 64-character stem")
    user_dir = user_dir.resolve(strict=True)
    save_dir = user_dir / "save"
    config_dir = user_dir / "config"
    if save_dir.is_symlink() or config_dir.is_symlink():
        raise ValueError("Save/config directory symlinks are not accepted")
    save = save_dir / slot
    if save.is_symlink() or not save.is_file() or save.stat().st_size == 0:
        raise ValueError("Original save must exist, be nonempty and not be a symlink")
    if receipt.exists() or receipt.is_symlink():
        raise ValueError("Evidence receipt must be a new path")
    before = save.stat()
    digest = hashlib.sha256()
    with save.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    after = save.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Save changed while hashing")
    payload = ("RVCP1 " + slot + "\n").encode("ascii")
    config_dir.mkdir(parents=True, exist_ok=True)
    request = config_dir / "dev-checkpoint-launch-v1.txt"
    # Publish a complete request without replacing an existing request.
    fd, temporary = tempfile.mkstemp(prefix=".checkpoint-", dir=config_dir)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, request)
    finally:
        Path(temporary).unlink(missing_ok=True)
    record = {
        "schema": 1, "status": "QUEUED_UNASSESSED", "slot": slot,
        "save_sha256": digest.hexdigest(), "save_bytes": after.st_size,
        "request": str(request), "request_sha256": hashlib.sha256(payload).hexdigest(),
        "game_stopped": "operator asserted", "save_contents_modified": False,
        "native_m00_validation": "required at consumption", "reload_proven": False,
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-dir", required=True, type=Path)
    parser.add_argument("--slot", required=True)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--offline", action="store_true", required=True,
                        help="Assert the emulator/game is stopped before queuing")
    args = parser.parse_args()
    print(json.dumps(queue_request(args.user_dir, args.slot, args.receipt), sort_keys=True))


if __name__ == "__main__":
    main()
