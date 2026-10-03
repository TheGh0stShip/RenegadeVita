"""Source-only action miss checks; no C++ compilation or execution."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.original_owner_source_replay import replay_to_patch

ROOT = Path(__file__).resolve().parents[1]


class ActionObserverMissTests(unittest.TestCase):
    def test_zero_fuzz_hook_only_when_no_callback_matched(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'action.cpp'
            before, result = replay_to_patch(directory, 'combat', ('action.cpp',),
                'combat-a35-action-observer-miss-telemetry.patch')
            original = before['action.cpp']
            self.assertNotIn(b'offset', result.stdout)
            patched = path.read_text()
        body = patched.split('void\tActionClass::Notify_Completed', 1)[1].split('bool\tActionClass::Request_Action', 1)[0]
        self.assertLess(body.index('observer_found = true;'), body.index('->Action_Complete('))
        self.assertIn('if (!observer_found)', body)
        self.assertIn('if ( observer_id != 0 )', body)
        self.assertEqual(original.split('bool\tActionClass::Request_Action', 1)[1],
                         patched.split('bool\tActionClass::Request_Action', 1)[1])

    def test_producer_is_bounded_and_drain_is_typed(self):
        source = (ROOT / 'port/developer/a35_campaign_flight_recorder.cpp').read_text()
        body = source.split('void A35_Campaign_Flight_Action_Observer_Miss', 1)[1].split(
            'void A35_Campaign_Flight_Record_Frame', 1)[0]
        self.assertNotIn('gRecorder', body)
        for token in ('pthread_mutex_lock', 'pthread_mutex_unlock', 'gConversationEnabled',
                      'gConversationCount < 128U', 'UINT32_MAX'):
            self.assertIn(token, body)
        self.assertLess(source.index('event.monitor_kind == 6U'), source.index('names[event.monitor_kind - 1U]'))
        self.assertIn('Push_Event("script_action", "observer_absent_at_completion"', source)


if __name__ == '__main__':
    unittest.main()
