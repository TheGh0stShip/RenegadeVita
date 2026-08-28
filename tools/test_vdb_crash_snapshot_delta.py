#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "vdb_crash_snapshot_delta.py"


def wrapped(entries):
    return {"ok": True, "result": {"snapshot": {"entries": entries}}}


class VdbCrashSnapshotDeltaTests(unittest.TestCase):
    def test_reports_only_new_hashes_from_wrapped_vdb_snapshots(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            baseline = root / "baseline.json"
            current = root / "current.json"
            output = root / "delta.json"
            baseline.write_text(json.dumps(wrapped([
                {"path": "ux0:/data/a.psp2dmp", "sha256": "a" * 64, "size": 10},
            ])), encoding="utf-8")
            current.write_text(json.dumps(wrapped([
                {"path": "ux0:/data/a-copy.psp2dmp", "sha256": "a" * 64, "size": 10},
                {"path": "ux0:/data/b.psp2dmp", "sha256": "b" * 64, "size": 20},
            ])), encoding="utf-8")

            subprocess.run(
                [sys.executable, str(SCRIPT), str(baseline), str(current), "--output", str(output)],
                check=True,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                text=True,
            )
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["baseline_count"], 1)
            self.assertEqual(result["current_count"], 2)
            self.assertEqual(result["new_count"], 1)
            self.assertEqual(result["new_entries"][0]["path"], "ux0:/data/b.psp2dmp")


if __name__ == "__main__":
    unittest.main()
