"""Checkpoint archives preserve native bytes without inventing progression evidence."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from tools.tutorial_checkpoints import LEVEL_INFO, LEVEL_DATA, read_save


class CheckpointArchiveTests(unittest.TestCase):
    def test_unassessed_archive_and_original_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            user = root / "user"
            (user / "save").mkdir(parents=True)
            name = b"M00_Tutorial.mix\0"
            info = bytes((1, len(name))) + name
            data = struct.pack("<II", LEVEL_INFO, len(info)) + info
            data += struct.pack("<II", LEVEL_DATA, 4) + b"test"
            save = user / "save/source.sav"
            save.write_bytes(data)
            evidence = root / "receipt.json"
            evidence.write_text('{"state": "test position, mission unassessed"}')
            vault = root / "vault"
            command = [sys.executable, str(Path(__file__).with_name("tutorial_checkpoints.py")),
                       "capture", "--id", "test-position", "--vault", str(vault),
                       "--user-dir", str(user), "--content-id", "a" * 64,
                       "--slot", save.name, "--build", "A3.5-dev117",
                       "--evidence", str(evidence)]
            captured = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(captured.returncode, 0, captured.stderr)
            master = vault / "test-position/checkpoint.sav"
            metadata = json.loads((master.parent / "manifest.json").read_text())
            self.assertEqual(metadata["segment_status"], "UNASSESSED")
            self.assertFalse(metadata["cross_build_load_validated"])
            self.assertEqual(master.read_bytes(), data)
            self.assertEqual(save.read_bytes(), data)
            self.assertFalse(master.stat().st_mode & 0o222)
            repeated = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            restored = subprocess.run(command[:2] + ["restore", "--id", "test-position",
                "--vault", str(vault), "--user-dir", str(user), "--content-id", "a" * 64,
                "--slot", "fresh.sav", "--offline"], capture_output=True, text=True)
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertEqual((user / "save/fresh.sav").read_bytes(), data)
            save.write_bytes(data + b"tail")
            with self.assertRaisesRegex(ValueError, "Truncated"):
                read_save(save)


if __name__ == "__main__":
    unittest.main()
