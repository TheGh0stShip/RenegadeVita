#!/usr/bin/env python3
"""Read-only, hash-verified pull of Renegade runtime diagnostics from a PSTV."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.validate_campaign_flight_bundle import BundleError, validate_bundle


def command(vdb_src: Path, profile: Path, *args: str) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(vdb_src) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    result = subprocess.run(
        [sys.executable, "-m", "vitadevbridge.cli", "--config", str(profile), "--json", *args],
        check=False, capture_output=True, text=True, timeout=45, env=env)
    if result.returncode:
        raise RuntimeError(f"VDB command failed ({result.returncode}): {result.stderr.strip()}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("VDB returned invalid JSON") from error
    if not payload.get("ok"):
        raise RuntimeError(f"VDB rejected command: {payload.get('error')}")
    return payload.get("result") or {}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pull_verified(vdb_src: Path, profile: Path, remote: str, local: Path) -> dict:
    before = command(vdb_src, profile, "fs", "hash", "--vdb1", remote)
    expected = before.get("sha256")
    size = before.get("size")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise RuntimeError(f"VDB did not return a valid remote SHA-256 for {remote}")
    if not isinstance(size, int) or size <= 0:
        raise RuntimeError(f"remote evidence is empty or has invalid size: {remote}")
    command(vdb_src, profile, "fs", "pull", "--vdb1", remote, str(local))
    actual = sha256_file(local)
    if actual != expected or local.stat().st_size != size:
        local.unlink(missing_ok=True)
        raise RuntimeError(f"pulled evidence differs from device-side hash or size: {remote}")
    return {"remote_path": remote, "local_path": str(local), "size": size, "sha256": expected}


def collect(vdb_src: Path, profile: Path, candidate: str, expected_eboot_sha256: str,
            output_dir: Path) -> dict:
    if not re.fullmatch(r"A[0-9]+\.[0-9]+-dev[0-9]+", candidate):
        raise ValueError("candidate must look like A3.5-dev197")
    if not profile.is_file() or not (vdb_src / "vitadevbridge" / "cli.py").is_file():
        raise ValueError("VDB profile or source directory does not exist")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_eboot_sha256):
        raise ValueError("expected eboot SHA-256 must be 64 lowercase hexadecimal characters")
    device = command(vdb_src, profile, "debug", "device-info")
    if str(device.get("model", "")).lower() != "pstv":
        raise ValueError(f"refusing non-PSTV target: model={device.get('model')!r}")
    device_candidate = candidate.lower().replace(".", "")
    installed = command(vdb_src, profile, "fs", "hash", "--vdb1", "ux0:/app/RNEGA3101/eboot.bin")
    if installed.get("sha256") != expected_eboot_sha256:
        raise RuntimeError("installed Renegade executable does not match the requested candidate hash")
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_paths = [
        (f"ux0:/data/renegade/user/logs/{device_candidate}-runtime.log",
         output_dir / f"{device_candidate}-runtime.log"),
        *[(f"ux0:/data/renegade/user/captures/{name}", output_dir / name)
          for name in ("campaign-flight-summary.json", "campaign-flight-events.jsonl",
                       "campaign-flight-frames.csv", "campaign-flight-log-tail.txt")],
    ]
    artifacts = [pull_verified(vdb_src, profile, remote, local)
                 for remote, local in evidence_paths]
    try:
        flight = validate_bundle(output_dir, candidate)
    except BundleError as error:
        raise RuntimeError(f"device flight sidecars rejected: {error}") from error
    summary = json.loads((output_dir / "campaign-flight-summary.json").read_text(encoding="utf-8"))
    if not summary.get("archive"):
        raise RuntimeError("device flight summary has no archive identity")
    receipt = {
        "schema_version": 1,
        "device_model": "pstv",
        "firmware_reported": device.get("reported_firmware"),
        "candidate": candidate,
        "installed_eboot_sha256": installed["sha256"],
        "flight_archive": summary["archive"],
        "flight_frames": flight["frames"],
        "flight_events": flight["events"],
        "artifacts": artifacts,
        "transport": "authenticated VDB1",
        "scope": "one title-owned runtime log and four flight sidecars; no application mutation",
    }
    receipt_path = output_dir / f"{candidate.lower()}-vdb-pull-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vdb-src", type=Path, required=True, help="VitaDevBridge src directory")
    parser.add_argument("--profile", type=Path, required=True, help="paired PSTV profile path; contents are never read here")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--expected-eboot-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = collect(args.vdb_src, args.profile, args.candidate,
                          args.expected_eboot_sha256, args.output_dir)
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"PSTV log collection failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
