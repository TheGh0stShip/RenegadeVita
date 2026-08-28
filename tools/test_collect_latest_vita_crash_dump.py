#!/usr/bin/env python3

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "collect_latest_vita_crash_dump.sh"


class CollectLatestVitaCrashDumpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_shell_syntax(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], cwd=ROOT, check=True)

    def test_uses_read_only_snapshot_delta_and_pull(self):
        self.assertIn("debug crash collect", self.source)
        self.assertIn('--crash-root "$crash_root"', self.source)
        self.assertIn("--snapshot-only", self.source)
        self.assertIn("vdb_crash_snapshot_delta.py", self.source)
        self.assertIn('fs pull --vdb1 "$remote_path" "$local_dump"', self.source)
        self.assertIn('actual_sha=$(sha256sum "$local_dump"', self.source)
        self.assertIn('[[ "$actual_sha" != "$dump_sha" ]]', self.source)
        self.assertIn('--arg candidate "$candidate"', self.source)
        self.assertIn('--arg crash_root "$crash_root"', self.source)
        self.assertIn('--arg baseline "$baseline_snapshot"', self.source)

    def test_runs_project_parser_and_vdb_psp2_report_with_matching_elf(self):
        self.assertIn("parse_psp2_core.py", self.source)
        self.assertIn("debug crash report", self.source)
        self.assertIn('--core-sha256 "$dump_sha"', self.source)
        self.assertIn('--elf "$candidate_elf"', self.source)
        self.assertIn('--elf-sha256 "$expected_elf"', self.source)
        self.assertIn("--module-name RenegadeVitaA31", self.source)

    def test_manual_crash_collector_contains_no_device_mutation_commands(self):
        forbidden = [
            "fs push",
            "fs remove",
            "fs touch",
            "app launch",
            "app kill",
            "input press",
            "package install",
            "package verify",
        ]
        for token in forbidden:
            self.assertNotIn(token, self.source)


if __name__ == "__main__":
    unittest.main()
