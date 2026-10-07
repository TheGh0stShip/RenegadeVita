#!/usr/bin/env python3
"""Queue a developer save launch; native original code validates its campaign map.

Default: one-shot RVCP1 request (config/dev-checkpoint-launch-v1.txt), consumed
by a RENEGADE_DEVELOPMENT_CHECKPOINT=1 build at the next startup.
--sticky: RVTC1 request (config/tutorial-checkpoint-v1.flag) for an original
M00 save; the build re-enters it at every process start until it is cleared.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

ONE_SHOT = ("RVCP1", "dev-checkpoint-launch-v1.txt")
STICKY = ("RVTC1", "tutorial-checkpoint-v1.flag")


def tutorial_checkpoints():
    try:
        from . import tutorial_checkpoints as module
    except ImportError:
        import tutorial_checkpoints as module
    return module


def existing_sticky(request):
    """Return a prior RVTC1 flag's bytes; refuse to replace anything else."""
    if not (request.exists() or request.is_symlink()):
        return None
    if request.is_symlink() or not request.is_file() or request.stat().st_size > 76:
        raise ValueError("Refusing to replace a non-RVTC1 tutorial-checkpoint flag")
    previous = request.read_bytes()
    if not previous.startswith(b"RVTC1 "):
        raise ValueError("Refusing to replace a non-RVTC1 tutorial-checkpoint flag")
    return previous


def queue_request(user_dir, slot, receipt, sticky=False):
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
    if sticky:
        # The native RVTC1 route admits only original M00 saves; fail here first.
        tutorial_checkpoints().read_save(save)
    before = save.stat()
    digest = hashlib.sha256()
    with save.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    after = save.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Save changed while hashing")
    prefix, name = STICKY if sticky else ONE_SHOT
    payload = (prefix + " " + slot + "\n").encode("ascii")
    config_dir.mkdir(parents=True, exist_ok=True)
    request = config_dir / name
    previous = existing_sticky(request) if sticky else None
    # Publish a complete request. A one-shot request never replaces a pending
    # one; a sticky request replaces only a prior RVTC1 flag, atomically.
    fd, temporary = tempfile.mkstemp(prefix=".checkpoint-", dir=config_dir)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if sticky:
            os.replace(temporary, request)
        else:
            os.link(temporary, request)
    finally:
        Path(temporary).unlink(missing_ok=True)
    record = {
        "schema": 1, "status": "QUEUED_UNASSESSED", "slot": slot,
        "save_sha256": digest.hexdigest(), "save_bytes": after.st_size,
        "request": str(request), "request_sha256": hashlib.sha256(payload).hexdigest(),
        "request_kind": ("RVTC1 sticky: retained, first frontend entry of each process"
                         if sticky else "RVCP1 one-shot: consumed at next startup"),
        "game_stopped": "operator asserted", "save_contents_modified": False,
        "native_original_save_validation": "required at consumption",
        "reload_proven": False,
    }
    if previous is not None:
        record["replaced_request_sha256"] = hashlib.sha256(previous).hexdigest()
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    return record


def clear_sticky(user_dir):
    """Remove only an RVTC1 flag; returns whether one was removed."""
    request = user_dir.resolve(strict=True) / "config" / STICKY[1]
    if existing_sticky(request) is None:
        return False
    request.unlink()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user-dir", required=True, type=Path)
    parser.add_argument("--slot")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--sticky", action="store_true",
                        help="Write the retained RVTC1 tutorial-checkpoint-v1.flag instead")
    parser.add_argument("--clear-sticky", action="store_true",
                        help="Remove an RVTC1 flag and restore normal startup")
    parser.add_argument("--offline", action="store_true", required=True,
                        help="Assert the emulator/game is stopped before queuing")
    args = parser.parse_args()
    if args.clear_sticky:
        print(json.dumps({"sticky_flag_removed": clear_sticky(args.user_dir)}))
        return
    if not args.slot or not args.receipt:
        parser.error("--slot and --receipt are required unless --clear-sticky is given")
    print(json.dumps(queue_request(args.user_dir, args.slot, args.receipt, args.sticky),
                     sort_keys=True))


if __name__ == "__main__":
    main()
