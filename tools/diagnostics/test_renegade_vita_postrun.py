import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from typing import Any


TOOL = Path(__file__).resolve().parent / "renegade_vita_postrun.py"


def run_tool(candidate: str, dist: Path, output: Path, runtime_log: Path | None = None,
             user_observation: str = "") -> None:
    command = [sys.executable, str(TOOL), candidate, str(dist), str(output)]
    if runtime_log is not None:
        command.extend(["--runtime-log", str(runtime_log)])
    if user_observation:
        command.extend(["--user-observation", user_observation])
    subprocess.run(command, check=True, capture_output=True, text=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("z/second.log", "[PERF] marker=FRAME frame=11 render_ms=14.0\n")
        zf.writestr("a/first.log", "[LIFECYCLE] event=START\n")
        zf.writestr("b/mid.log", "[LIFECYCLE] event=END\n")


class PostrunTests(unittest.TestCase):
    def setUp(self):
        self.candidate = "A3.5-dev2-test"

    def make_output(self, tmp: Path) -> Path:
        output = tmp / "out"
        output.mkdir(parents=True)
        return output

    def test_candidate_scoped_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            expected = dist / f"RenegadeVita-{self.candidate}.vpk"
            expected.write_bytes(b"A")
            (dist / "RenegadeVita-A3.0.vpk").write_bytes(b"B")
            (dist / "README.txt").write_text("ignore", encoding="utf-8")
            output = self.make_output(root)

            run_tool(self.candidate, dist, output)
            manifest = read_json(output / "artifact_manifest.json")

            discovered = [entry["path"] for entry in manifest["discovered_files"]]
            self.assertEqual(discovered, [f"RenegadeVita-{self.candidate}.vpk"])

    def test_hash_declaration_mismatch_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            artifact = dist / f"{self.candidate}.vpk"
            artifact.write_bytes(b"payload")
            declared = hashlib.sha256(artifact.read_bytes()).hexdigest()
            wrong = "0" * 64 if declared != "0" * 64 else "1" * 64
            (dist / f"{self.candidate}.sha256").write_text(
                f"{wrong} {artifact.name}\n",
                encoding="utf-8"
            )

            output = self.make_output(root)
            run_tool(self.candidate, dist, output)

            manifest = read_json(output / "artifact_manifest.json")
            self.assertEqual(len(manifest["hash_mismatches"]), 1)
            self.assertEqual(manifest["hash_mismatches"][0]["declared"], wrong)
            artifact_entry = next(entry for entry in manifest["discovered_files"] if entry["path"] == artifact.name)
            self.assertEqual(artifact_entry["declared_sha256"], wrong)

    def test_sha256sums_text_manifest_is_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            artifact = dist / f"{self.candidate}.elf"
            artifact.write_bytes(b"matching-elf")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            (dist / f"{self.candidate}-SHA256SUMS.txt").write_text(
                f"{digest}  {artifact.name}\n", encoding="utf-8"
            )

            output = self.make_output(root)
            run_tool(self.candidate, dist, output)

            manifest = read_json(output / "artifact_manifest.json")
            entry = next(item for item in manifest["discovered_files"] if item["path"] == artifact.name)
            self.assertTrue(entry["hash_matches"])
            self.assertEqual(entry["declared_sha256"], digest)
            self.assertEqual(manifest["hash_mismatches"], [])

    def test_termination_classifications(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            (dist / f"{self.candidate}.vpk").write_bytes(b"vpk")
            output = self.make_output(root)

            clean_log = root / "runtime_clean.log"
            clean_log.write_text("[LIFECYCLE] event=START\n[LIFECYCLE] event=END status=clean\n", encoding="utf-8")
            run_tool(self.candidate, dist, output / "clean", runtime_log=clean_log)
            self.assertEqual(read_json(output / "clean/session_summary.json")["termination"]["classification"], "clean")

            crash_log = root / "runtime_crash.log"
            crash_log.write_text("[LIFECYCLE] event=END status=crash\n", encoding="utf-8")
            run_tool(self.candidate, dist, output / "crash", runtime_log=crash_log)
            self.assertEqual(read_json(output / "crash/session_summary.json")["termination"]["classification"], "crash")

            unknown_log_output = self.make_output(root / "unknown")
            run_tool(self.candidate, dist, unknown_log_output)
            self.assertEqual(read_json(unknown_log_output / "session_summary.json")["termination"]["classification"], "unknown")

    def test_expected_vs_actual_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            (dist / f"{self.candidate}.vpk").write_bytes(b"vpk")
            log = root / "runtime.log"
            log.write_text("[LIFECYCLE] event=START\n", encoding="utf-8")
            output = self.make_output(root)

            run_tool(self.candidate, dist, output, runtime_log=log)
            summary = read_json(output / "session_summary.json")
            self.assertEqual(summary["marker_summary"]["missing_lifecycle_markers"], ["END"])
            self.assertEqual(summary["marker_summary"]["missing_performance_markers"], ["FRAME"])

    def test_repeated_normalized_messages_are_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            (dist / f"{self.candidate}.vpk").write_bytes(b"vpk")
            log = root / "runtime.log"
            log.write_text("[LIFECYCLE] event=REPEAT code=1\n[LIFECYCLE] event=REPEAT code=2\n", encoding="utf-8")
            output = self.make_output(root)

            run_tool(self.candidate, dist, output, runtime_log=log)
            anomalies = read_json(output / "anomalies.json")
            repeat = [entry for entry in anomalies if entry["type"] == "repeated_normalized_message"]
            self.assertEqual(len(repeat), 1)
            self.assertEqual(repeat[0]["count"], 2)

    def test_performance_csv_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            (dist / f"{self.candidate}.vpk").write_bytes(b"vpk")
            log = root / "runtime.log"
            log.write_text("[PERF] marker=FRAME frame=10 render_ms=16.7 simulation_ms=5.0\n"
                           "[PERF] marker=FRAME frame=11 render_ms=17.2 simulation_ms=5.1\n",
                           encoding="utf-8")
            output = self.make_output(root)

            run_tool(self.candidate, dist, output, runtime_log=log)
            with (output / "performance_metrics.csv").open(encoding="utf-8", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["frame"], "10")
            self.assertEqual(rows[1]["render_ms"], "17.2")

    def test_missing_optional_runtime_log_is_not_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            (dist / f"{self.candidate}.vpk").write_bytes(b"vpk")
            output = self.make_output(root)
            missing_log = root / "missing-runtime.log"

            run_tool(self.candidate, dist, output, runtime_log=missing_log)
            summary = read_json(output / "session_summary.json")
            anomalies = read_json(output / "anomalies.json")
            missing = [entry for entry in anomalies if entry["type"] == "missing_optional_file"]
            self.assertTrue(summary["runtime_log"]["present"] is False)
            self.assertEqual(len(missing), 1)
            self.assertEqual(missing[0]["path"], str(missing_log.resolve()))

    def test_discovery_and_zip_members_are_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            for name in ["zzz.bin", "aaa.bin", "mid.bin"]:
                (dist / f"{self.candidate}-{name}").write_bytes(name.encode("utf-8"))
            write_zip(dist / f"{self.candidate}-bundle.zip")
            output = self.make_output(root)

            run_tool(self.candidate, dist, output)
            manifest = read_json(output / "artifact_manifest.json")
            paths = [entry["path"] for entry in manifest["discovered_files"]]
            self.assertEqual(paths, sorted(paths))

            zip_entry = next(entry for entry in manifest["discovered_files"] if entry["kind"] == "diagnostic_zip")
            member_names = [member["name"] for member in zip_entry["zip_members"]["members"]]
            self.assertEqual(member_names, sorted(member_names))

    def test_user_observation_is_separate_from_machine_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            (dist / f"{self.candidate}.vpk").write_bytes(b"vpk")
            log = root / "runtime.log"
            log.write_text("[LIFECYCLE] event=START\n[LIFECYCLE] event=END status=clean\n", encoding="utf-8")
            output = self.make_output(root)
            message = "manual check notes"

            run_tool(self.candidate, dist, output, runtime_log=log, user_observation=message)
            summary = read_json(output / "session_summary.json")
            completion = read_json(output / "completion.json")
            self.assertEqual(summary["user_observation"]["text"], message)
            self.assertNotIn("manual check notes", completion["artifact_manifest"])

    def test_two_run_output_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist"
            dist.mkdir()
            (dist / f"{self.candidate}.vpk").write_bytes(b"vpk")
            log = root / "runtime.log"
            log.write_text("[LIFECYCLE] event=START\n[LIFECYCLE] event=END status=clean\n", encoding="utf-8")
            out1 = root / "out1"
            out2 = root / "out2"

            run_tool(self.candidate, dist, out1, runtime_log=log)
            run_tool(self.candidate, dist, out2, runtime_log=log)
            hashes1 = {p.relative_to(out1).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(out1.rglob("*")) if p.is_file()}
            hashes2 = {p.relative_to(out2).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(out2.rglob("*")) if p.is_file()}
            self.assertEqual(hashes1, hashes2)


if __name__ == "__main__":
    unittest.main()
