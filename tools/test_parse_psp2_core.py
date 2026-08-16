import gzip
import hashlib
import json
import tempfile
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("parse_psp2_core.py")
FIXTURE_ROOT = Path(__file__).with_name("fixtures") / "psp2_core"


def run_parser(dump_file: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(dump_file), "--output", str(output)],
        capture_output=True,
        text=True,
    )


class ParsePsp2CoreTests(unittest.TestCase):
    def fixture(self, name: str) -> Path:
        return FIXTURE_ROOT / name

    def read_json(self, output: Path) -> dict:
        return json.loads(output.read_text(encoding="utf-8"))

    def test_malformed_gzip_payload(self):
        dump = self.fixture("malformed-gzip.psp2dmp")
        with self.assertRaises(gzip.BadGzipFile):
            with gzip.open(dump, "rb") as _stream:
                _stream.read()

    def test_non_elf_payload(self):
        dump = self.fixture("non-elf-payload.psp2dmp")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "notes.json"
            result = run_parser(dump, output)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(
                "not an ELF payload" in result.stderr
                or "truncated ELF header" in result.stderr
            )
            self.assertFalse(output.exists())

    def test_truncated_note_payload(self):
        dump = self.fixture("truncated-thread-header.psp2dmp")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "notes.json"
            result = run_parser(dump, output)
            self.assertEqual(result.returncode, 0)
            payload = self.read_json(output)
            self.assertEqual(payload["notes"], [])
            self.assertIsNone(payload["thread_info"])

    def test_unknown_note_type_is_retained(self):
        dump = self.fixture("unknown-note.psp2dmp")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "notes.json"
            result = run_parser(dump, output)
            self.assertEqual(result.returncode, 0)
            payload = self.read_json(output)
            self.assertEqual(payload["notes"][0]["owner"], "CUSTOM_NOTE")
            self.assertEqual(payload["notes"][0]["type"], "0xDEADBEEF")
            self.assertEqual(payload["notes"][0]["size"], 1)
            self.assertIsNone(payload["thread_info"])

    def test_multiple_notes(self):
        dump = self.fixture("multiple-notes.psp2dmp")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "notes.json"
            result = run_parser(dump, output)
            self.assertEqual(result.returncode, 0)
            payload = self.read_json(output)
            self.assertEqual([entry["owner"] for entry in payload["notes"]], ["COREFILE_INFO", "THREAD_INFO"])
            self.assertEqual(payload["notes_inventory"]["count"], 2)
            self.assertEqual(payload["notes_inventory"]["types"], ["0x00001000", "0x00001003"])
            self.assertEqual(payload["thread_info"]["schema_version"], 4)
            self.assertEqual(payload["thread_info"]["record_size"], 200)
            self.assertEqual(payload["thread_info"]["threads"][0]["thread_id"], "0x40010003")
            self.assertEqual(payload["thread_info"]["threads"][0]["thread_name"], "RNEGA3101")
            self.assertEqual(payload["thread_info"]["threads"][0]["pc"], "0x810DACB6")
            self.assertEqual(payload["thread_info"]["thread_reg_info"]["available"], False)

    def test_deterministic_syntax_free_output(self):
        dump = self.fixture("deterministic-output.psp2dmp")
        with tempfile.TemporaryDirectory() as temporary:
            first_output = Path(temporary) / "notes-a.json"
            second_output = Path(temporary) / "notes-b.json"

            first_result = run_parser(dump, first_output)
            second_result = run_parser(dump, second_output)

            self.assertEqual(first_result.returncode, 0)
            self.assertEqual(second_result.returncode, 0)
            self.assertEqual(first_output.read_bytes(), second_output.read_bytes())

            first_payload = self.read_json(first_output)
            self.assertEqual(first_payload["schema"], 2)
            self.assertEqual(first_payload["parser_version"], "1.1.0")
            self.assertIn("input_identity", first_payload)
            identity = first_payload["input_identity"]
            self.assertEqual(identity["byte_count"], len(dump.read_bytes()))
            self.assertEqual(len(identity["sha256"]), 64)

            # The input identity must match the supplied gzip-wrapped dump,
            # not only its decompressed ELF payload.
            expected_identity = hashlib.sha256(dump.read_bytes()).hexdigest()
            self.assertEqual(identity["sha256"], expected_identity)
            self.assertIn("payload_identity", first_payload)
            self.assertEqual(
                first_payload["payload_identity"]["sha256"],
                hashlib.sha256(gzip.open(dump, "rb").read()).hexdigest(),
            )
