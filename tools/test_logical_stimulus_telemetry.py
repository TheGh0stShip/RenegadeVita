"""Source-only logical stimulus diagnostics; no engine build or execution."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LogicalStimulusTelemetryTests(unittest.TestCase):
    def test_hooks_replay_before_original_scene_and_observer_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = {}
            args = ['patch', '--batch', '--fuzz=0', '--no-backup-if-mismatch', '-p1', '-d', directory]
            patch = (ROOT / 'port/patches/combat-a35-logical-stimulus-telemetry.patch').read_bytes()
            for name in ('scriptcommands.cpp', 'smartgameobj.cpp'):
                paths[name] = Path(directory) / name
                paths[name].write_bytes((ROOT / 'staging/combat' / name).read_bytes())
            if 'A35_Campaign_Flight_Logical_Stimulus' in paths['smartgameobj.cpp'].read_text():
                subprocess.run(args + ['--reverse'], input=patch, capture_output=True, check=True)
            if 'a35_script_lookup_telemetry.h' not in paths['scriptcommands.cpp'].read_text():
                subprocess.run(args + ['--forward'], input=(ROOT / 'port/patches/combat-a35-script-lookup-telemetry.patch').read_bytes(), capture_output=True, check=True)
            result = subprocess.run(args + ['--forward'], input=patch, capture_output=True, check=True)
            self.assertNotIn(b'offset', result.stdout)
            commands = paths['scriptcommands.cpp'].read_text().split('int Create_Logical_Sound(', 1)[1].split('void Monitor_Sound(', 1)[0]
            self.assertLess(commands.index('A35_Campaign_Flight_Logical_Stimulus'), commands.index('sound->Add_To_Scene'))
            smart = paths['smartgameobj.cpp'].read_text().split('void\tSmartGameObj::On_Logical_Heard', 1)[1].split('\n}\n', 1)[0]
            self.assertLess(smart.index('A35_Campaign_Flight_Logical_Stimulus'), smart.index('observer_list[ index ]->Sound_Heard'))
            self.assertEqual(smart.count('A35_Campaign_Flight_Logical_Stimulus'), 1)

    def test_recorder_is_numeric_bounded_opt_in_and_type_focused(self):
        text = (ROOT / 'port/developer/a35_campaign_flight_recorder.cpp').read_text()
        body = text.split('void A35_Campaign_Flight_Logical_Stimulus(', 1)[1].split('void A35_Campaign_Flight_Record_Frame(', 1)[0]
        self.assertIn('type != 400004 && type != 400005', body)
        self.assertIn('gConversationEnabled', body)
        self.assertIn('gConversationCount < 128U', body)
        self.assertIn('gConversationDropped != UINT32_MAX', body)
        self.assertNotIn('new ', body)
        self.assertNotIn('Push_Event(', body)
        self.assertNotIn('gRecorder', body)
        self.assertIn('hearing_callback_entry', text)
        header = (ROOT / 'upstream/CnC_Renegade/Code/Scripts/Mission1.h').read_text()
        self.assertRegex(header, r'M01_DETENTION_GATE_IS_DOWN_JDG\s+400004')
        self.assertRegex(header, r'M01_DETENTION_GATE_DOWN_SAM_DEAD_JDG\s+400005')


if __name__ == '__main__':
    unittest.main()
