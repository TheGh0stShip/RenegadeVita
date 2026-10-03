import json
import tempfile
import unittest
from pathlib import Path

from tools.validate_campaign_flight_bundle import BundleError, validate_bundle


class CampaignFlightBundleTests(unittest.TestCase):
    def test_export_uses_ring_sequence_not_frame_as_identity(self):
        source = Path(__file__).resolve().parents[1] / 'port/developer/a35_campaign_flight_recorder.cpp'
        body = source.read_text().split('void Write_Events(', 1)[1].split('void Write_Frames', 1)[0]
        self.assertIn('event_sequence', body)
        self.assertIn('sequence, event.frame, event.monotonic_us', body)

    def sequenced_events(self, values):
        records = [{'candidate': 'A3.5-dev188', **value} for value in values]
        (self.root / 'campaign-flight-events.jsonl').write_text(
            '\n'.join(json.dumps(row) for row in records) + '\n')
        (self.root / 'campaign-flight-summary.json').write_text(json.dumps(
            {'candidate': 'A3.5-dev188', 'frames_recorded': 2, 'events_recorded': len(records)}))

    def test_retained_sequence_may_start_after_eviction(self):
        self.sequenced_events([{'event_sequence': 900}, {'event_sequence': 901}])
        self.assertEqual(validate_bundle(self.root)['events'], 2)

    def test_rejects_sequence_holes_duplicates_and_reversal(self):
        for second in (9, 10, 12):
            with self.subTest(second=second):
                self.sequenced_events([{'event_sequence': 10}, {'event_sequence': second}])
                with self.assertRaisesRegex(BundleError, 'not contiguous'):
                    validate_bundle(self.root)

    def test_rejects_invalid_sequence_types_and_widths(self):
        for value in (True, -1, 2**64, '0', 0.0):
            with self.subTest(value=value):
                self.sequenced_events([{'event_sequence': value}])
                with self.assertRaisesRegex(BundleError, 'invalid event sequence'):
                    validate_bundle(self.root)

    def test_rejects_mixed_sequence_modes(self):
        self.sequenced_events([{'event_sequence': 0}, {}])
        with self.assertRaisesRegex(BundleError, 'mixed sequenced'):
            validate_bundle(self.root)

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
