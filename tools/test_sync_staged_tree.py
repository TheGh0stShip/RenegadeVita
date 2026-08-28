import json
import os
import pathlib
import subprocess
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SYNC = ROOT / "tools" / "sync_staged_tree.py"


class SyncStagedTreeTests(unittest.TestCase):
    def test_sync_preserves_unchanged_mtime_updates_changed_and_removes_stale(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source = root / "source"
            target = root / "target"
            (source / "combat").mkdir(parents=True)
            (target / "combat").mkdir(parents=True)
            (target / "unmanaged").mkdir()

            unchanged_source = source / "combat" / "same.cpp"
            unchanged_target = target / "combat" / "same.cpp"
            unchanged_source.write_text("same\n", encoding="utf-8")
            unchanged_target.write_text("same\n", encoding="utf-8")
            old_time = time.time() - 3600
            os.utime(unchanged_target, (old_time, old_time))

            (source / "combat" / "changed.cpp").write_text("new\n", encoding="utf-8")
            (target / "combat" / "changed.cpp").write_text("old\n", encoding="utf-8")
            (target / "combat" / "stale.cpp").write_text("stale\n", encoding="utf-8")
            (target / "unmanaged" / "keep.txt").write_text("keep\n", encoding="utf-8")

            output = subprocess.check_output(
                [
                    "python3",
                    str(SYNC),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--managed-dir",
                    "combat",
                ],
                text=True,
            )
            result = json.loads(output)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual((target / "combat" / "changed.cpp").read_text(encoding="utf-8"), "new\n")
            self.assertFalse((target / "combat" / "stale.cpp").exists())
            self.assertEqual((target / "unmanaged" / "keep.txt").read_text(encoding="utf-8"), "keep\n")
            self.assertEqual(unchanged_target.stat().st_mtime, old_time)
            self.assertGreaterEqual(result["totals"]["unchanged"], 1)
            self.assertGreaterEqual(result["totals"]["copied"], 1)
            self.assertGreaterEqual(result["totals"]["removed"], 1)

    def test_managed_dir_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            proc = subprocess.run(
                [
                    "python3",
                    str(SYNC),
                    "--source",
                    str(source),
                    "--target",
                    str(target),
                    "--managed-dir",
                    "../outside",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("managed directory must be a safe relative path", proc.stderr)


if __name__ == "__main__":
    unittest.main()
