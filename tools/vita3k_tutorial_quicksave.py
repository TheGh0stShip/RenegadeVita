#!/usr/bin/env python3
"""Request an original M00 quicksave and retain separate input/file evidence.

Requires an already running, native-input-enabled candidate in gameplay.
Does not prove segment completion, save validity, or a successful load.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def snapshot(directory):
    result = {}
    for path in directory.iterdir():
        if path.name.lower() not in {"quicksavea.sav", "quicksaveb.sav"}:
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Refusing non-regular save: {path}")
        before = path.stat()
        payload = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            continue
        result[path.name] = {
            "bytes": len(payload),
            "mtime_ns": after.st_mtime_ns,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-dir", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True,
                        help="New, candidate-scoped directory; must not exist")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=30, choices=range(5, 121))
    args = parser.parse_args()
    user = args.user_dir.absolute()
    if user.is_symlink() or not user.is_dir():
        raise ValueError("User directory must be a real existing directory")
    resolved = user.resolve()
    if ([part.lower() for part in resolved.parts[-4:]] !=
            ["ux0", "data", "renegade", "user"] or
            "vita3k" not in [part.lower() for part in resolved.parts]):
        raise ValueError("Only the local Vita3K Renegade user directory is admitted")
    saves = user / "save"
    if saves.is_symlink() or not saves.is_dir():
        raise ValueError("Original user/save directory is missing or unsafe")
    evidence = args.evidence_dir.absolute()
    if evidence.resolve() == resolved or resolved in evidence.resolve().parents:
        raise ValueError("Evidence must remain outside the emulated user tree")
    evidence.mkdir(parents=True, exist_ok=False)
    record = {
        "schema": 1,
        "candidate_operator_label": args.candidate,
        "evidence_class": "Vita3K",
        "status": "REQUEST_NOT_SENT",
        "native_input_accepted_and_released": False,
        "original_save_validity": "UNASSESSED",
        "original_save_load": "UNASSESSED",
        "tutorial_segment_completion": "UNASSESSED",
        "benchmark_eligible": False,
    }
    try:
        baseline = snapshot(saves)
        record["before"] = baseline
        sender = Path(__file__).with_name("vita3k_native_input.py")
        command = [sys.executable, str(sender), "step", "--user-dir", str(user),
                   "--buttons", "Select", "Square", "--hold-ms", "150",
                   "--receipt", str(evidence / "native-input.json")]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=15)
        (evidence / "sender.stdout.txt").write_text(completed.stdout, encoding="utf-8")
        (evidence / "sender.stderr.txt").write_text(completed.stderr, encoding="utf-8")
        record["sender_exit_code"] = completed.returncode
        if completed.returncode != 0:
            raise RuntimeError("Native input sender failed; see retained output")
        acknowledgment = json.loads((evidence / "native-input.json").read_text(encoding="utf-8"))
        if not acknowledgment.get("native_override_released"):
            raise RuntimeError("Sender did not establish native acceptance and release")
        record["native_input_accepted_and_released"] = True
        record["status"] = "INPUT_ACCEPTED_SAVE_CHANGE_PENDING"
        deadline = time.monotonic() + args.timeout_seconds
        previous = None
        stable_since = None
        while time.monotonic() < deadline:
            current = snapshot(saves)
            changed = {name: value for name, value in current.items()
                       if value["bytes"] > 0 and baseline.get(name) != value}
            now = time.monotonic()
            if changed and changed == previous:
                if stable_since is not None and now - stable_since >= 2:
                    record["after"] = current
                    record["changed_save_files"] = changed
                    record["status"] = "SAVE_FILE_CHANGE_OBSERVED_LOAD_UNASSESSED"
                    return
            else:
                stable_since = now if changed else None
            previous = changed
            time.sleep(0.2)
        raise TimeoutError("Input released, but no stable nonempty quicksave change observed")
    except Exception as error:
        record["status"] = "FAILED_OR_UNASSESSED"
        record["error"] = str(error)
        raise
    finally:
        (evidence / "quicksave-result.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.TimeoutExpired) as error:
        raise SystemExit(str(error))
