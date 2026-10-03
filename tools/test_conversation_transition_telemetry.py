"""Source-only telemetry ownership checks; no compiler or game execution."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ConversationTransitions(unittest.TestCase):
    def test_zero_fuzz_owner_hooks_preserve_callback_order(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'activeconversation.cpp'
            path.write_bytes((ROOT / 'staging/combat/activeconversation.cpp').read_bytes())
            (Path(directory) / 'activeconversation.h').write_bytes(
                (ROOT / 'staging/combat/activeconversation.h').read_bytes())
            result = subprocess.run(['patch', '--batch', '--forward', '--fuzz=0',
                                     '--no-backup-if-mismatch', '-p1', '-d', directory],
                                    input=(ROOT / 'port/patches/combat-a35-conversation-transition-telemetry.patch').read_bytes(),
                                    capture_output=True, check=True)
            self.assertNotIn(b'offset', result.stdout)
            text = path.read_text()
            header = (Path(directory) / 'activeconversation.h').read_text()
        self.assertEqual(text.count('A35_Campaign_Flight_Conversation_Transition('), 2)
        self.assertEqual(text.count('static_cast<int32_t>(Get_ID())'), 4)
        notify = text.split('ActiveConversationClass::Notify_Monitors_On_End', 1)[1].split(
            'ActiveConversationClass::Notify_Monitors (', 1)[0]
        self.assertLess(notify.index('A35_Campaign_Flight_Conversation_Monitor(3U'),
                        notify.index('->Action_Complete (game_obj, ActionID, reason);'))
        self.assertIn('uint64_t DiagnosticInstance;', header)
        self.assertEqual(text.count('DiagnosticInstance ='), 1)
        save_load = text.split('ActiveConversationClass::Save', 1)[1].split('ActiveConversationClass::Register_Monitor', 1)[0]
        self.assertNotIn('DiagnosticInstance', save_load)
        original = (ROOT / 'staging/combat/activeconversation.cpp').read_text()
        for signature in ('ActiveConversationClass::Save (', 'ActiveConversationClass::Load (',
                          'ActiveConversationClass::Load_Variables ('):
            original_body = original.split(signature, 1)[1].split('\n}\n', 1)[0]
            patched_body = text.split(signature, 1)[1].split('\n}\n', 1)[0]
            self.assertEqual(patched_body, original_body, signature)
        self.assertLess(text.index('NextRemarkTimer = duration;'), text.index('Transition(false,'))
        stop = text.split('ActiveConversationClass::Stop_Conversation (ActionCompleteReason reason)', 1)[1]
        self.assertLess(stop.index('State = STATE_FINISHED;'), stop.index('Transition(true,'))
        self.assertLess(stop.index('Transition(true,'), stop.index('Notify_Monitors_On_End (reason);'))
        self.assertIn('static_cast<int32_t>(reason)', stop)

    def test_recorder_has_fixed_numeric_payload_and_existing_ring(self):
        text = (ROOT / 'port/developer/a35_campaign_flight_recorder.cpp').read_text()
        body = text.split('void A35_Campaign_Flight_Conversation_Transition(', 1)[1].split(
            'void A35_Campaign_Flight_Record_Frame', 1)[0]
        self.assertNotIn('gRecorder', body)
        self.assertIn('pthread_mutex_lock(&gConversationMutex)', body)
        self.assertIn('pthread_mutex_unlock(&gConversationMutex)', body)
        self.assertIn('gConversationCount < 128U', body)
        self.assertIn('gConversationDropped != UINT32_MAX', body)
        self.assertNotIn('Get_String', body)
        self.assertNotIn('new ', body)
        self.assertNotIn('Push_Event(', body)

    def test_only_owner_thread_drains_with_nonblocking_queue_lock(self):
        text = (ROOT / 'port/developer/a35_campaign_flight_recorder.cpp').read_text()
        body = text.split('void Drain_Conversation_Queue()', 1)[1].split('uint64_t Ring_First_Sequence', 1)[0]
        self.assertIn('pthread_equal(pthread_self(), gRecorder.main_thread)', body)
        self.assertIn('pthread_mutex_trylock(&gConversationMutex)', body)
        self.assertIn('queue_overflow', body)
        self.assertIn('0U, event.monotonic_us, detail', body)
        self.assertIn('gConversationCount = 0U;', body)

    def test_export_uses_ring_sequence_not_frame_as_identity(self):
        text = (ROOT / 'port/developer/a35_campaign_flight_recorder.cpp').read_text()
        body = text.split('void Write_Events(', 1)[1].split('void Write_Frames', 1)[0]
        self.assertIn('event_sequence', body)
        self.assertIn('sequence, event.frame, event.monotonic_us', body)

    def test_instance_counter_survives_resets_and_never_wraps(self):
        text = (ROOT / 'port/developer/a35_campaign_flight_recorder.cpp').read_text()
        body = text.split('uint64_t A35_Campaign_Flight_Allocate_Conversation_Instance', 1)[1].split(
            'void A35_Campaign_Flight_Conversation_Transition', 1)[0]
        self.assertIn('gNextConversationInstance != UINT64_MAX', body)
        self.assertIn('? ++gNextConversationInstance : 0U', body)
        reset = text.split('void Reset_Conversation_Queue', 1)[1].split('uint64_t Monotonic_Us', 1)[0]
        self.assertNotIn('gNextConversationInstance', reset)

    def test_collection_requires_opt_in_and_drains_each_frame(self):
        text = (ROOT / 'port/developer/a35_campaign_flight_recorder.cpp').read_text()
        self.assertIn('Reset_Conversation_Queue(script_lookup_enabled);', text)
        self.assertNotIn('Reset_Conversation_Queue(true);', text)
        frame = text.split('void A35_Campaign_Flight_Record_Frame', 1)[1].split(
            'void A35_Campaign_Flight_Record_Mission', 1)[0]
        self.assertIn('Drain_Conversation_Queue();', frame)

    def test_monitor_producer_rejects_invalid_kinds_and_has_no_recorder_access(self):
        text = (ROOT / 'port/developer/a35_campaign_flight_recorder.cpp').read_text()
        body = text.split('void A35_Campaign_Flight_Conversation_Monitor', 1)[1].split(
            'void A35_Campaign_Flight_Record_Frame', 1)[0]
        self.assertIn('if (outcome > 3U) return;', body)
        self.assertNotIn('gRecorder', body)
        self.assertIn('pthread_mutex_lock(&gConversationMutex)', body)
        self.assertIn('gConversationCount < 128U', body)


if __name__ == '__main__':
    unittest.main()
