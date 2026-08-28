#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


TOOL = Path(__file__).with_name("verify_candidate_identity.py")
CANDIDATE = "A3.5-dev9"
LOG_PATH = "ux0:data/renegade/user/logs/a35-dev9-runtime.log"


class CandidateIdentityTests(unittest.TestCase):
    def run_tool(
        self,
        elf_bytes: bytes,
        mutate_vpk: bool = False,
        candidate: str = CANDIDATE,
    ) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            elf = root / "candidate.elf"
            self_file = root / "eboot.bin"
            vpk = root / "candidate.vpk"
            output = root / "identity.json"
            elf.write_bytes(elf_bytes)
            self_file.write_bytes(b"self-payload")
            with zipfile.ZipFile(vpk, "w") as archive:
                archive.writestr("eboot.bin", b"wrong" if mutate_vpk else b"self-payload")
                archive.writestr("sce_sys/param.sfo", b"sfo")
            command = ["python3", str(TOOL), "--elf", str(elf), "--self", str(self_file),
                       "--vpk", str(vpk), "--candidate", candidate,
                       "--runtime-log", f"ux0:data/renegade/user/logs/{candidate.lower().replace('.', '')}-runtime.log",
                       "--output", str(output)]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            return result.returncode, json.loads(output.read_text(encoding="utf-8"))

    def test_accepts_coherent_identity(self) -> None:
        log_path = f"ux0:data/renegade/user/logs/{CANDIDATE.lower().replace('.', '')}-runtime.log"
        code, report = self.run_tool(
            f"x Renegade Vita {CANDIDATE} x {log_path} x {CANDIDATE} CAPTURE".encode())
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "PASS")

    def test_dev10_identity_does_not_alias_frozen_dev1(self) -> None:
        candidate = "A3.5-dev10"
        log_path = "ux0:data/renegade/user/logs/a35-dev10-runtime.log"
        code, report = self.run_tool(
            f"Renegade Vita {candidate} {log_path} {candidate} CAPTURE".encode(),
            candidate=candidate,
        )
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "PASS")

    def test_rejects_stale_identity_or_packaging_mismatch(self) -> None:
        log_path = f"ux0:data/renegade/user/logs/{CANDIDATE.lower().replace('.', '')}-runtime.log"
        code, report = self.run_tool(
            f"Renegade Vita {CANDIDATE} {log_path} {CANDIDATE} CAPTURE A3.5-dev1".encode(),
            mutate_vpk=True)
        self.assertEqual(code, 1)
        self.assertEqual(report["status"], "FAIL")
        names = {check["name"] for check in report["checks"] if check["status"] == "FAIL"}
        self.assertIn("packaged_eboot_matches_self", names)
        self.assertIn("elf_no_stale_A3.5-dev1", names)


if __name__ == "__main__":
    unittest.main()
