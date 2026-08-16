import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "summarize_warning_signatures.py"


def run_tool(logs: list[Path], output: Path, baseline: Path | None = None) -> dict:
    command = [sys.executable, str(TOOL), "--output", str(output)]
    if baseline is not None:
        command += ["--baseline", str(baseline)]
    command += [str(path) for path in logs]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(output.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


class WarningSignatureSummaryTests(unittest.TestCase):
    def test_gcc_clang_warning_signature_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "build.log"
            log.write_bytes(
                b"/src/one.cpp:10:3: warning: comparison between signed and unsigned integer expressions [-Wsign-compare]\n"
                b"/src/two.cpp:42:7: warning: comparison between signed and unsigned integer expressions [-Wsign-compare]\n"
            )

            data = run_tool([log], root / "out.json")
            section = data["sections"]["warning"]

            self.assertEqual(len(section), 1)
            entry = section[0]
            self.assertEqual(entry["count"], 2)
            self.assertEqual(entry["signature"], "comparison between signed and unsigned integer expressions [-Wsign-compare]")
            self.assertEqual(entry["source_provenance"][0]["source_file"], "/src/one.cpp")
            self.assertEqual(entry["source_provenance"][1]["source_file"], "/src/two.cpp")
            self.assertEqual(entry["representative"]["source_file"], "/src/one.cpp")
            self.assertIn("warning:", entry["representative"]["raw"])

    def test_linker_warning_and_error_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "link.log"
            log.write_text(
                "/usr/bin/ld: /tmp/main.o: in function `main': warning: relocation target '/tmp/main.o' not found\n"
                "/usr/bin/ld: error: cannot find -lmissing\n",
                encoding="utf-8",
            )

            data = run_tool([log], root / "out.json")
            self.assertEqual(len(data["sections"]["linker_warning"]), 1)
            self.assertEqual(len(data["sections"]["linker_error"]), 1)
            self.assertEqual(data["sections"]["linker_warning"][0]["count"], 1)
            self.assertEqual(data["sections"]["linker_error"][0]["count"], 1)

    def test_errors_are_not_downgraded_to_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "mixed.log"
            log.write_text(
                "/src/error.cpp:10:2: error: undefined reference to `x'\n"
                "/src/warn.cpp:11:4: warning: unknown pragma\n",
                encoding="utf-8",
            )

            data = run_tool([log], root / "out.json")
            self.assertGreater(data["totals"]["error"], 0)
            self.assertGreater(data["totals"]["warning"], 0)
            self.assertEqual(data["totals"]["warning"], 1)
            self.assertEqual(data["totals"]["error"], 1)
            self.assertEqual(len(data["sections"]["warning"]), 1)
            self.assertEqual(len(data["sections"]["error"]), 1)

    def test_summary_is_sorted_deterministically(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "unordered.log"
            log.write_text(
                "/src/omega.cpp:7:1: warning: zed warning\n"
                "/src/alpha.cpp:3:1: warning: alpha warning\n"
                "/src/mid.cpp:9:1: warning: middle warning\n",
                encoding="utf-8",
            )

            data = run_tool([log], root / "out.json")
            warnings = data["sections"]["warning"]
            signatures = [entry["signature"] for entry in warnings]
            self.assertEqual(signatures, sorted(signatures))

    def test_baseline_candidate_comparison_statuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = root / "baseline.log"
            baseline.write_text(
                "/src/a.cpp:1:1: warning: baseline warning one\n"
                "/src/a.cpp:2:1: warning: baseline warning two\n",
                encoding="utf-8",
            )
            candidate = root / "candidate.log"
            candidate.write_text(
                "/src/a.cpp:3:1: warning: baseline warning one\n"
                "/src/a.cpp:4:1: warning: candidate only warning\n",
                encoding="utf-8",
            )

            data = run_tool([candidate], root / "out.json", baseline=baseline)
            comparison = {entry["signature"]: entry for entry in data["comparison"]["diff"]}
            self.assertEqual(comparison["baseline warning one"]["status"], "persisting")
            self.assertEqual(comparison["baseline warning two"]["status"], "resolved")
            self.assertEqual(comparison["candidate only warning"]["status"], "new")
            self.assertEqual(comparison["baseline warning one"]["counts"], {"baseline": 1, "candidate": 1})
            self.assertEqual(comparison["baseline warning two"]["counts"], {"baseline": 1, "candidate": 0})
            self.assertEqual(comparison["candidate only warning"]["counts"], {"baseline": 0, "candidate": 1})

    def test_malformed_utf8_is_recovered_with_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "malformed.log"
            log.write_bytes(
                b"/src/bad.cpp:1:1: warning: malformed byte \xff sequence\n"
            )

            data = run_tool([log], root / "out.json")
            entry = data["sections"]["warning"][0]
            self.assertEqual(entry["count"], 1)
            self.assertIn("�", entry["representative"]["raw"])

    def test_byte_identical_output_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log = root / "stable.log"
            log.write_text("src/stable.cpp:1:1: warning: stable message\n", encoding="utf-8")
            out1 = root / "out1.json"
            out2 = root / "out2.json"

            run_tool([log], out1)
            run_tool([log], out2)
            self.assertEqual(sha256(out1), sha256(out2))


if __name__ == "__main__":
    unittest.main()
