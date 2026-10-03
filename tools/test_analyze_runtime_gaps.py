import json
import tempfile
import unittest
from pathlib import Path

from tools.analyze_runtime_gaps import make_report


class RuntimeGapAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "campaign-flight-summary.json").write_text(json.dumps({
            "candidate": "A3.5-dev999", "archive": "M13.mix", "reason": "shutdown",
            "load_source": "checkpoint.sav", "frames_recorded": 1, "events_recorded": 1,
            "mission": {"conversation": "", "objective_count": 0}}))
        (self.root / "campaign-flight-frames.csv").write_text(
            "candidate,archive,load_source,frame,monotonic_us,frame_us,render_us,simulation_us\n"
            "A3.5-dev999,M13.mix,checkpoint.sav,1,100,20000,10000,9000\n")
        (self.root / "campaign-flight-events.jsonl").write_text(json.dumps({
            "candidate": "A3.5-dev999", "archive": "M13.mix", "category": "lifecycle",
            "name": "interactive_session_ready", "frame": 0}) + "\n")
        (self.root / "campaign-flight-log-tail.txt").write_text(
            "Runtime identity: candidate=A3.5-dev999\n")
        self.reference = self.root / "route.json"
        self.reference.write_text(json.dumps({"segments": [
            {"id": "intro", "behavior": "intro", "owners": ["MissionX0.cpp"]},
            {"id": "ending", "behavior": "ending", "owners": ["Test_DLS.cpp"]}]}))

    def test_bounded_checkpoint_trace_does_not_claim_unobserved_route(self):
        report = make_report(self.root, expected_candidate="A3.5-dev999", archive="M13.mix",
                             reference=self.reference)
        self.assertEqual(report["route_milestones"][0]["status"], "not_observed")
        self.assertEqual(report["unobserved_route_milestones"], ["intro", "ending"])
        self.assertIn("does not prove the feature is missing", report["limits"][0])

    def test_explicit_route_marker_is_required_to_observe_segment(self):
        path = self.root / "campaign-flight-events.jsonl"
        event = {"candidate": "A3.5-dev999", "archive": "M13.mix", "category": "route",
                 "name": "intro", "frame": 1}
        path.write_text(path.read_text() + json.dumps(event) + "\n")
        summary_path = self.root / "campaign-flight-summary.json"
        summary = json.loads(summary_path.read_text())
        summary["events_recorded"] = 2
        summary_path.write_text(json.dumps(summary))
        report = make_report(self.root, expected_candidate="A3.5-dev999", archive="M13.mix",
                             reference=self.reference)
        self.assertEqual(report["route_milestones"][0]["status"], "observed")
        self.assertEqual(report["route_milestones"][0]["evidence_frames"], [1])


if __name__ == "__main__":
    unittest.main()
