import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.collect_pstv_runtime_log import collect


class CollectPstvRuntimeLogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "src"
        (self.src / "vitadevbridge").mkdir(parents=True)
        (self.src / "vitadevbridge" / "cli.py").write_text("")
        self.profile = self.root / "paired.toml"
        self.profile.write_text("secret must not be read by collector")

    def test_refuses_non_pstv_before_file_access(self):
        with patch("tools.collect_pstv_runtime_log.command",
                   return_value={"model": "vita", "reported_firmware": "3.74"}) as call:
            with self.assertRaisesRegex(ValueError, "non-PSTV"):
                collect(self.src, self.profile, "A3.5-dev197", "0" * 64, self.root / "out")
        self.assertEqual(call.call_count, 1)

    def test_pull_hash_matches_and_writes_receipt(self):
        evidence = {
            "ux0:/data/renegade/user/logs/a35-dev197-runtime.log": b"Runtime identity: candidate=A3.5-dev197\n",
            "ux0:/data/renegade/user/captures/campaign-flight-summary.json": json.dumps({
                "candidate": "A3.5-dev197", "archive": "M01.mix", "frames_recorded": 1,
                "events_recorded": 1}).encode(),
            "ux0:/data/renegade/user/captures/campaign-flight-events.jsonl": (json.dumps({
                "candidate": "A3.5-dev197", "archive": "M01.mix", "frame": 1}) + "\n").encode(),
            "ux0:/data/renegade/user/captures/campaign-flight-frames.csv": (
                "candidate,archive,frame,monotonic_us,frame_us,render_us,simulation_us\n"
                "A3.5-dev197,M01.mix,1,100,20000,10000,9000\n").encode(),
            "ux0:/data/renegade/user/captures/campaign-flight-log-tail.txt":
                b"Runtime identity: candidate=A3.5-dev197\n",
        }
        hashes = {path: (hashlib.sha256(payload).hexdigest(), len(payload))
                  for path, payload in evidence.items()}
        def mocked(_src, _profile, *args):
            if args == ("debug", "device-info"):
                return {"model": "pstv", "reported_firmware": "3.74"}
            if args[:3] == ("fs", "hash", "--vdb1"):
                if args[3] == "ux0:/app/RNEGA3101/eboot.bin":
                    return {"sha256": "1" * 64}
                digest, size = hashes[args[3]]
                return {"sha256": digest, "size": size}
            if args[:3] == ("fs", "pull", "--vdb1"):
                payload = evidence[args[3]]
                Path(args[-1]).write_bytes(payload)
                return {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
            raise AssertionError(args)
        with patch("tools.collect_pstv_runtime_log.command", side_effect=mocked):
            receipt = collect(self.src, self.profile, "A3.5-dev197", "1" * 64,
                              self.root / "out")
        self.assertEqual(receipt["installed_eboot_sha256"], "1" * 64)
        self.assertEqual(receipt["flight_archive"], "M01.mix")
        self.assertEqual(len(receipt["artifacts"]), 5)
        saved = json.loads((self.root / "out" / "a3.5-dev197-vdb-pull-receipt.json").read_text())
        self.assertEqual(saved["device_model"], "pstv")

    def test_refuses_installed_executable_hash_mismatch(self):
        def mocked(_src, _profile, *args):
            if args == ("debug", "device-info"):
                return {"model": "pstv", "reported_firmware": "3.74"}
            if args[:3] == ("fs", "hash", "--vdb1"):
                return {"sha256": "1" * 64}
            raise AssertionError(args)
        with patch("tools.collect_pstv_runtime_log.command", side_effect=mocked):
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                collect(self.src, self.profile, "A3.5-dev197", "2" * 64,
                        self.root / "out")


if __name__ == "__main__":
    unittest.main()
