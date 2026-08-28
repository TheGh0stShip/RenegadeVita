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
    command.append(str(vpk))
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
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=args.timeout,
        check=False,
    )
    (evidence_dir / "stdout.log").write_text(completed.stdout, encoding="utf-8")
    (evidence_dir / "stderr.log").write_text(completed.stderr, encoding="utf-8")
    receipt["returncode"] = completed.returncode
    receipt["status"] = "PASSED" if completed.returncode == 0 else "FAILED"
    write_json(evidence_dir / "vita3k-runner-receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "evidence": str(evidence_dir)}, sort_keys=True))
    return 0 if completed.returncode == 0 else completed.returncode


if __name__ == "__main__":
    sys.exit(main())
