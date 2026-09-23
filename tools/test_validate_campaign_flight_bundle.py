import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_campaign_flight_bundle import BundleError, validate_bundle


class CampaignFlightBundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "campaign-flight-summary.json").write_text(
            json.dumps({"candidate": "A3.5-dev188", "frames_recorded": 2,
                        "events_recorded": 1}), encoding="utf-8")
        (self.root / "campaign-flight-frames.csv").write_text(
            "candidate,frame,monotonic_us,frame_us,render_us,simulation_us\n"
            "A3.5-dev188,1,100,20000,12000,7000\n"
            "A3.5-dev188,2,200,30000,18000,10000\n", encoding="utf-8")
        (self.root / "campaign-flight-events.jsonl").write_text(
            json.dumps({"candidate": "A3.5-dev188", "frame": 2}) + "\n",
            encoding="utf-8")
        (self.root / "campaign-flight-log-tail.txt").write_text(
            "Runtime identity: candidate=A3.5-dev188\n", encoding="utf-8")

    def test_valid_bundle_reports_candidate_scoped_timings(self):
        report = validate_bundle(self.root, "A3.5-dev188")
        self.assertEqual(report["frames"], 2)
        self.assertEqual(report["mean_render_us"], 15000)
        self.assertEqual(report["last_frame"], 2)

    def test_rejects_mixed_frame_candidate(self):
        path = self.root / "campaign-flight-frames.csv"
        path.write_text(path.read_text().replace("A3.5-dev188,2", "A3.5-dev187,2"),
                        encoding="utf-8")
        with self.assertRaisesRegex(BundleError, "candidate"):
            validate_bundle(self.root)

    def test_rejects_trailing_corruption_in_summary(self):
        path = self.root / "campaign-flight-summary.json"
        path.write_text(path.read_text() + "\n{}\n", encoding="utf-8")
        with self.assertRaisesRegex(BundleError, "invalid JSON"):
            validate_bundle(self.root)

    def test_rejects_nonmonotonic_frame_order(self):
        path = self.root / "campaign-flight-frames.csv"
        path.write_text(path.read_text().replace("A3.5-dev188,2,200", "A3.5-dev188,1,200"),
                        encoding="utf-8")
        with self.assertRaisesRegex(BundleError, "strictly increasing"):
            validate_bundle(self.root)

    def test_rejects_conflicting_identity_in_log_tail(self):
        (self.root / "campaign-flight-log-tail.txt").write_text(
            "Runtime identity: candidate=A3.5-dev187\n", encoding="utf-8")
        with self.assertRaisesRegex(BundleError, "conflicting runtime identity"):
            validate_bundle(self.root)


if __name__ == "__main__":
    unittest.main()
