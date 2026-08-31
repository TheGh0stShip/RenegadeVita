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

    def test_current_runtime_perf_summary_forms_are_parsed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            log = root / "runtime.log"
            log.write_text(
                "A3.5 perf: frames=2400 rolling_samples=240 avg_fps=39.418 "
                "frame_us min/p50/p95/p99/max=18000/21874/24446/35000/50000 "
                "slow_over_20ms=1200 slow_over_33ms=231 "
                "stage_us sync/sim/render=200/6427/18938 draws meshes=249616 "
                "triangles=14009711 texture_binds=216621 "
                "texture_sampler_updates=100 texture_bind_skips=200 "
                "texture_sampler_skips=300 texture_stage_enable_skips=400 "
                "texture_combiner_skips=500 texture_unsupported_stages=2 "
                "state_changes=16800 "
                "render_state_skips=900\n"
                "A3.1 interactive: complete perf_fps=41.250 "
                "p50/p95/worst_us=20000/30000/60000\n",
                encoding="utf-8",
            )

            out_dir = root / "out"
            out_dir.mkdir()
            run_tool([log], out_dir)
            metrics = json.loads(
                (out_dir / "report.json").read_text(encoding="utf-8")
            )["runs"][0]["metrics"]
            self.assertEqual(metrics["fps"]["samples"], 2)
            self.assertEqual(metrics["fps"]["min"], 39.418)
            self.assertEqual(metrics["frame_time_min"]["mean"], 18000)
            self.assertEqual(metrics["frame_time_percentile_p50"]["samples"], 2)
            self.assertEqual(metrics["frame_time_percentile_p95"]["max"], 30000)
            self.assertEqual(metrics["frame_time_percentile_p99"]["mean"], 35000)
            self.assertEqual(metrics["frame_time_max"]["max"], 60000)
            self.assertEqual(metrics["slow_over_20_0ms"]["mean"], 1200)
            self.assertEqual(metrics["slow_over_33_3ms"]["mean"], 231)
            self.assertEqual(metrics["sync"]["mean"], 200)
            self.assertEqual(metrics["simulation"]["mean"], 6427)
            self.assertEqual(metrics["rendering"]["mean"], 18938)
            self.assertEqual(metrics["texture_bind"]["mean"], 216621)
            self.assertEqual(metrics["texture_sampler_update"]["mean"], 100)
            self.assertEqual(metrics["texture_bind_skip"]["mean"], 200)
            self.assertEqual(metrics["texture_sampler_skip"]["mean"], 300)
            self.assertEqual(metrics["texture_stage_enable_skip"]["mean"], 400)
            self.assertEqual(metrics["texture_combiner_skip"]["mean"], 500)
            self.assertEqual(metrics["texture_unsupported_stage"]["mean"], 2)
            self.assertEqual(metrics["state_change"]["mean"], 16800)
            self.assertEqual(metrics["render_state_skip"]["mean"], 900)

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
