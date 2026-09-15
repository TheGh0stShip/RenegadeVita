#!/usr/bin/env python3
"""Optional Vita3K runner for emulator-only Renegade Vita smoke checks."""

from __future__ import annotations

import argparse
import datetime as _datetime
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = ROOT / "build" / "vita3k-evidence"


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_vita3k(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    env_value = os.environ.get("VITA3K_EXE")
    if env_value:
        return env_value
    for name in ("Vita3K", "vita3k", "Vita3K.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


def command_for(executable: str, vpk: pathlib.Path, console: bool) -> list[str]:
    command = [executable]
    if console:
        command.append("--console")
    content_path = str(vpk)
    if os.name != "nt" and executable.lower().endswith(".exe"):
        content_path = subprocess.check_output(["wslpath", "-w", content_path], text=True).strip()
    command.append(content_path)
    return command


def write_json(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vpk", type=pathlib.Path, required=True)
    parser.add_argument("--vita3k-exe")
    parser.add_argument("--title-id", default="RNEGA3101")
    parser.add_argument("--candidate", default="UNKNOWN")
    parser.add_argument("--evidence-root", type=pathlib.Path, default=DEFAULT_EVIDENCE_ROOT)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--no-console", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--installed", action="store_true",
                        help="Run a title installed by prepare_vita3k_demo.py instead of reinstalling the VPK")
    args = parser.parse_args(argv)

    executable = discover_vita3k(args.vita3k_exe)
    if not executable and not args.dry_run:
        raise SystemExit("Vita3K executable not found; set VITA3K_EXE or pass --vita3k-exe")

    vpk = args.vpk.resolve()
    if not vpk.is_file():
        raise SystemExit(f"candidate VPK not found: {vpk}")

    timestamp = _datetime.datetime.now(_datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence_dir = args.evidence_root / f"{args.candidate}-{timestamp}"
    command = command_for(executable or "VITA3K_EXE_NOT_FOUND", vpk, not args.no_console)
    if args.installed:
        command[-1:] = ["--installed-path", args.title_id]
    receipt = {
        "schema": 1,
        "generated_at_utc": _datetime.datetime.now(_datetime.UTC).replace(microsecond=0).isoformat(),
        "candidate": args.candidate,
        "title_id": args.title_id,
        "vpk": {
            "path": str(vpk),
            "sha256": sha256_file(vpk),
            "byte_count": vpk.stat().st_size,
        },
        "vita3k_executable": executable,
        "command": command,
        "dry_run": args.dry_run,
        "physical_acceptance": False,
        "notes": [
            "Vita3K is emulator-only evidence and cannot accept physical Vita controls, rendering, memory, suspend/resume, LiveArea, or soak gates."
        ],
    }

    if args.dry_run:
        write_json(evidence_dir / "vita3k-runner-receipt.json", receipt)
        print(json.dumps({"status": "DRY_RUN", "evidence": str(evidence_dir)}, sort_keys=True))
        return 0

    evidence_dir.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            command,
            cwd=pathlib.Path(executable).resolve().parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        def decoded(value):
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
        (evidence_dir / "stdout.log").write_text(decoded(error.stdout), encoding="utf-8")
        (evidence_dir / "stderr.log").write_text(decoded(error.stderr), encoding="utf-8")
        receipt["status"] = "TIMEOUT_UNASSESSED"
        receipt["notes"].append("A timeout does not distinguish running gameplay from a hang. On WSL, confirm Windows process termination separately.")
        write_json(evidence_dir / "vita3k-runner-receipt.json", receipt)
        print(json.dumps({"status": receipt["status"], "evidence": str(evidence_dir)}, sort_keys=True))
        return 124
    (evidence_dir / "stdout.log").write_text(completed.stdout, encoding="utf-8")
    (evidence_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    receipt["returncode"] = completed.returncode
    receipt["status"] = "PROCESS_EXITED_ZERO_UNASSESSED" if completed.returncode == 0 else "PROCESS_FAILED"
    write_json(evidence_dir / "vita3k-runner-receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "evidence": str(evidence_dir)}, sort_keys=True))
    return 0 if completed.returncode == 0 else completed.returncode


if __name__ == "__main__":
    sys.exit(main())
