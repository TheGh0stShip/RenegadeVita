import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "renegade_vita_performance_ledger.py"


def run_tool(log_paths: list[Path], out_dir: Path) -> Path:
    json_output = out_dir / "report.json"
    csv_output = out_dir / "report.csv"
    markdown_output = out_dir / "report.md"
    command = [
        sys.executable,
        str(TOOL),
        *(str(path) for path in log_paths),
        "--json", str(json_output),
        "--csv", str(csv_output),
        "--markdown", str(markdown_output),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return out_dir


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RuntimeLogFieldCompareTests(unittest.TestCase):
    def test_mixed_ordering_and_recognized_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "runtime.log"
            log.write_text(
                "frame-time-percentile-p95=16.7 rendering=14.2 fps=55 slow-frame=0.0 "
                "memory=1024 simulation=3.2 mesh=9 triangle=81 indexed-submission=14 "
                "content_id=ctent config_id=cfgA camera_id=camMain texture-bind=5 "
                "state-change=8 instrumentation-overhead=0.9\n"
                "texture_bind=4 fps=57 frame_time_percentile_p99=22.3 configuration_id=cfgA "
                "camera=camMain content=ctent\n",
                encoding="utf-8",
            )

            out_dir = root / "out"
            out_dir.mkdir()
            run_tool([log], out_dir)
            parsed = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
            metrics = parsed["runs"][0]["metrics"]
            self.assertEqual(metrics["fps"]["samples"], 2)
            self.assertEqual(metrics["rendering"]["samples"], 1)
            self.assertEqual(metrics["memory"]["samples"], 1)
            self.assertEqual(metrics["mesh"]["samples"], 1)

    def test_duplicate_samples_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "runtime.log"
            log.write_text(
                "fps=48 fps=49 fps=50 simulation=1\n"
                "fps=48 frame_time_p95=15.2\n",
                encoding="utf-8",
            )
            out = root / "out"
            out.mkdir()
            run_tool([log], out)
            rows = (out / "report.csv").read_text(encoding="utf-8").splitlines()
            sample_count = sum(line.startswith("sample") for line in rows[1:])
            self.assertEqual(sample_count, 6)

    def test_incompatible_identity_prevents_state_comparison(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            before = root / "before.log"
            after = root / "after.log"
            before.write_text(
                "content_id=ct1 configuration_id=cfg1 camera_id=cam1 fps=60\n",
                encoding="utf-8",
            )
            after.write_text(
                "content_id=ct2 configuration_id=cfg1 camera_id=cam1 fps=58\n",
                encoding="utf-8",
            )

            out = root / "out"
            out.mkdir()
            run_tool([before, after], out)
            data = json.loads((out / "report.json").read_text(encoding="utf-8"))
            comparison = data["comparisons"][0]
            self.assertFalse(comparison["state_comparison_eligible"])
            self.assertIn("incompatible", comparison["ineligible_reason"].lower())

    def test_no_samples_or_identifiers_stay_raw(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "runtime.log"
            log.write_text("random noise and labels that do not match\n", encoding="utf-8")
            out = root / "out"
            out.mkdir()
            run_tool([log], out)
            run = json.loads((out / "report.json").read_text(encoding="utf-8"))["runs"][0]
            self.assertEqual(run["samples"], [])
            self.assertGreater(run["unknown_count"], 0)

    def test_byte_identical_reruns(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "runtime.log"
            log.write_text("fps=60 frame_time_p95=16.7 memory=2048\n", encoding="utf-8")
            out1 = root / "out1"
            out2 = root / "out2"
            out1.mkdir()
            out2.mkdir()
            run_tool([log], out1)
            run_tool([log], out2)
            for name in ["report.json", "report.csv", "report.md"]:
                self.assertEqual(sha256(out1 / name), sha256(out2 / name))


if __name__ == "__main__":
    unittest.main()
