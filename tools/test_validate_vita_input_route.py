#!/usr/bin/env python3

import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate_vita_input_route.py"
HEADER = struct.Struct("<8s6I")
SAMPLE = struct.Struct("<IBBBB")
TIMED_SAMPLE = struct.Struct("<IBBBBI")


def fnv1a32(payload: bytes) -> int:
    value = 2_166_136_261
    for byte in payload:
        value ^= byte
        value = (value * 16_777_619) & 0xFFFFFFFF
    return value


def route_bytes(*, flags: int = 1, corrupt_checksum: bool = False) -> bytes:
    payload = b"".join(
        [
            SAMPLE.pack(0, 128, 128, 128, 128),
            SAMPLE.pack(0x200, 128, 32, 192, 128),
            SAMPLE.pack(0x8, 128, 128, 128, 128),
        ]
    )
    checksum = fnv1a32(payload) ^ (1 if corrupt_checksum else 0)
    return HEADER.pack(b"RVINPUT1", 1, SAMPLE.size, 3, flags, checksum, 0) + payload


def timed_route_bytes() -> bytes:
    payload = b"".join(
        [
            TIMED_SAMPLE.pack(0, 128, 128, 128, 128, 0),
            TIMED_SAMPLE.pack(0x200, 128, 32, 192, 128, 16667),
            TIMED_SAMPLE.pack(0x8, 128, 128, 128, 128, 500000),
        ]
    )
    checksum = fnv1a32(payload)
    return HEADER.pack(b"RVINPUT1", 2, TIMED_SAMPLE.size, 3, 1, checksum, 0) + payload


class InputRouteValidatorTests(unittest.TestCase):
    def run_route(self, data: bytes, *extra: str) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as directory:
            route = Path(directory) / "route.bin"
            route.write_bytes(data)
            result = subprocess.run(
                ["python3", str(VALIDATOR), str(route), *extra],
                check=False,
                capture_output=True,
                text=True,
            )
            return result.returncode, json.loads(result.stdout)

    def test_valid_complete_route_passes(self):
        code, result = self.run_route(route_bytes(), "--reject-truncated")
        self.assertEqual(0, code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual(3, result["sample_count"])
        self.assertEqual("legacy60hz", result["timebase"])
        self.assertFalse(result["truncated"])

    def test_valid_timed_route_passes(self):
        code, result = self.run_route(timed_route_bytes(), "--reject-truncated")
        self.assertEqual(0, code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual(2, result["format_version"])
        self.assertEqual(TIMED_SAMPLE.size, result["sample_size"])
        self.assertEqual("recorded-delta-us", result["timebase"])

    def test_checksum_mismatch_fails(self):
        code, result = self.run_route(route_bytes(corrupt_checksum=True))
        self.assertNotEqual(0, code)
        self.assertEqual("FAIL", result["status"])
        checksum = next(item for item in result["checks"] if item["name"] == "payload_checksum")
        self.assertFalse(checksum["passed"])

    def test_truncated_route_is_valid_but_can_be_rejected_for_replay_gate(self):
        code, result = self.run_route(route_bytes(flags=3))
        self.assertEqual(0, code)
        self.assertEqual("PASS", result["status"])
        self.assertTrue(result["truncated"])
        code, result = self.run_route(route_bytes(flags=3), "--reject-truncated")
        self.assertNotEqual(0, code)
        self.assertEqual("FAIL", result["status"])

    def test_size_mismatch_fails(self):
        code, result = self.run_route(route_bytes()[:-1])
        self.assertNotEqual(0, code)
        size = next(item for item in result["checks"] if item["name"] == "exact_file_size")
        self.assertFalse(size["passed"])


if __name__ == "__main__":
    unittest.main()
