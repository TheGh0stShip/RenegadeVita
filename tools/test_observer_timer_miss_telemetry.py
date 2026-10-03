"""Source-only original timer failure telemetry contracts."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ObserverTimerMiss(unittest.TestCase):
    def test_patch_replays_and_records_only_failed_lookup_before_removal(self):
        original = (ROOT / 'staging/combat/scriptablegameobj.cpp').read_text()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'scriptablegameobj.cpp'
            path.write_text(original)
            result = subprocess.run(['patch', '--batch', '--forward', '--fuzz=0',
                                     '--no-backup-if-mismatch', '-p1', '-d', directory],
                                    input=(ROOT / 'port/patches/combat-a35-observer-timer-miss-telemetry.patch').read_bytes(),
                                    capture_output=True, check=True)
            self.assertNotIn(b'offset', result.stdout)
            text = path.read_text()
        self.assertEqual(text.count('A35_Campaign_Flight_Observer_Timer_Miss('), 1)
        failure = text.split('if ( !found ) {', 1)[1]
        self.assertLess(failure.index('A35_Campaign_Flight_Observer_Timer_Miss('),
                        failure.index('delete ObserverTimerList[i];'))
        self.assertIn('static_cast<int32_t>(ObserverTimerList[i]->ObserverID)', failure)
        self.assertIn('static_cast<int32_t>(ObserverTimerList[i]->TimerID)', failure)
        original_timers = original.split('class\tGameObjObserverTimerClass', 1)[1].split('ScriptableGameObj::ScriptableGameObj', 1)[0]
        patched_timers = text.split('class\tGameObjObserverTimerClass', 1)[1].split('ScriptableGameObj::ScriptableGameObj', 1)[0]
        self.assertEqual(original_timers, patched_timers)

    def test_queue_producer_has_no_flight_recorder_access(self):
        text = (ROOT / 'port/developer/a35_campaign_flight_recorder.cpp').read_text()
        body = text.split('void A35_Campaign_Flight_Observer_Timer_Miss', 1)[1].split(
            'void A35_Campaign_Flight_Record_Frame', 1)[0]
        self.assertNotIn('gRecorder', body)
        self.assertIn('pthread_mutex_lock(&gConversationMutex)', body)
        self.assertIn('pthread_mutex_unlock(&gConversationMutex)', body)
        self.assertIn('gConversationCount < 128U', body)


if __name__ == '__main__':
    unittest.main()
