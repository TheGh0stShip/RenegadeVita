#!/usr/bin/env python3
"""Opt-in local controller commands; native acknowledgment is not gameplay proof."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time

DEFAULT_USER = Path("/mnt/c/Users/steve/AppData/Roaming/Vita3K/Vita3K/ux0/data/renegade/user")
BUTTONS = {"Select": 0x1, "Start": 0x8, "Up": 0x10, "Right": 0x20,
           "Down": 0x40, "Left": 0x80, "L": 0x100, "R": 0x200,
           "Triangle": 0x1000, "Circle": 0x2000, "Cross": 0x4000, "Square": 0x8000}


def atomic_command(path, text):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="ascii", dir=path.parent,
                                         prefix=".dev-input-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        deadline = time.monotonic() + 2.0
        while True:
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.02)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def session_token(config):
    fields = (config / "dev-input-session.txt").read_text(encoding="ascii").split()
    if len(fields) != 2 or fields[0] != "RVDEV1" or len(fields[1]) != 16:
        raise ValueError("No valid native development-input session; enable and restart the candidate")
    int(fields[1], 16)
    return fields[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("enable", "disable", "step"))
    parser.add_argument("--user-dir", type=Path, default=DEFAULT_USER)
    parser.add_argument("--buttons", nargs="*", choices=sorted(BUTTONS), default=[])
    parser.add_argument("--hold-ms", type=int, default=150)
    for axis in ("lx", "ly", "rx", "ry"):
        parser.add_argument("--" + axis, type=int, default=128)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    user = args.user_dir
    if user.is_symlink() or not user.is_dir() or user.parts[-4:] != ("ux0", "data", "renegade", "user"):
        raise ValueError("Use the actual local Vita3K ux0/data/renegade/user directory")
    if not any(part.casefold() == "vita3k" for part in user.parts):
        raise ValueError("This sender is restricted to a local Vita3K data tree")
    config = user / "config"
    if config.is_symlink() or not config.is_dir():
        raise ValueError("Native user/config directory is missing or symlinked")
    for name in ("enable.flag", "session.txt", "command.txt", "ack.txt", "sender.lock"):
        if (config / ("dev-input-" + name)).is_symlink():
            raise ValueError("Refusing a symlink in the development-input namespace")
    axes = [args.lx, args.ly, args.rx, args.ry]
    if not 0 <= args.hold_ms <= 3000 or any(not 0 <= axis <= 255 for axis in axes):
        raise ValueError("Hold must be 0..3000 ms and controller axes must be 0..255")
    record = {"schema": 1, "evidence_class": "Vita3K", "action": args.action,
              "foreground_required": False, "os_input_injection": False,
              "original_gameplay_effect": "UNASSESSED", "native_override_released": False}
    marker = config / "dev-input-enable.flag"
    if args.action == "enable":
        if marker.exists():
            if marker.read_bytes() != b"RVDEV1\n":
                raise ValueError("Existing enable marker has unexpected contents; preserving it")
        else:
            with marker.open("xb") as stream:
                stream.write(b"RVDEV1\n")
        record["status"] = "ENABLED_FOR_NEXT_NATIVE_INPUT_INITIALIZATION"
    elif args.action == "disable":
        if marker.exists() and marker.read_bytes() != b"RVDEV1\n":
            raise ValueError("Unexpected enable marker; preserving it")
        marker.unlink(missing_ok=True)
        record["status"] = "DISABLE_REQUESTED_NATIVE_POLL_REQUIRED"
    else:
        with (config / "dev-input-sender.lock").open("a") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            token = session_token(config)
            sequence = 0
            for name in ("dev-input-command.txt", "dev-input-ack.txt"):
                fields = (config / name).read_text(encoding="ascii").split()
                if len(fields) >= 3 and fields[:2] == ["RVDEV1", token]:
                    sequence = max(sequence, int(fields[2]))
            sequence += 1
            if sequence >= 0xffffffff:
                raise ValueError("Session sequence exhausted; restart native input session")
            buttons = 0
            for name in args.buttons:
                buttons |= BUTTONS[name]
            command = config / "dev-input-command.txt"
            payload = f"RVDEV1 {token} {sequence} {buttons} {' '.join(map(str, axes))} {args.hold_ms}\n"
            record.update(token=token, sequence=sequence, buttons=buttons, axes=axes, hold_ms=args.hold_ms)
            complete = False
            try:
                atomic_command(command, payload)
                deadline = time.monotonic() + args.hold_ms / 1000.0 + 5.0
                while time.monotonic() < deadline:
                    if session_token(config) != token:
                        raise ValueError("Native input session changed while the command was pending")
                    fields = (config / "dev-input-ack.txt").read_text(encoding="ascii").split()
                    if fields == ["RVDEV1", token, str(sequence), "RELEASED"]:
                        complete = True
                        record["native_override_released"] = True
                        record["status"] = "NATIVE_COMMAND_ACCEPTED_AND_RELEASED_GAMEPLAY_UNASSESSED"
                        break
                    time.sleep(0.02)
                if not complete:
                    raise TimeoutError("No native release acknowledgment; gameplay consumption is unproven")
            finally:
                if not complete:
                    try:
                        if session_token(config) == token:
                            atomic_command(command, f"RVDEV1 {token} {sequence + 1} 0 128 128 128 128 0\n")
                    except (OSError, ValueError):
                        pass  # Native holds independently expire within three seconds.
    output = json.dumps(record, indent=2) + "\n"
    if args.receipt is not None:
        with args.receipt.open("x", encoding="utf-8") as stream:
            stream.write(output)
    print(output, end="")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TimeoutError) as error:
        raise SystemExit(str(error))
