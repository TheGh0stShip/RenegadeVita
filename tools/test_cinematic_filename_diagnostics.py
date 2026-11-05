"""Source-only control-file diagnostics contracts; no engine execution."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from tools.original_owner_source_replay import replay_to_patch

ROOT = Path(__file__).resolve().parents[1]


class CinematicFilenameDiagnosticsTests(unittest.TestCase):
    def test_primary_callback_buffer_covers_signed_32_bit_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Test_Cinematic.cpp'
            before_files, result = replay_to_patch(directory, 'scripts', ('Test_Cinematic.cpp',),
                'scripts-a35-cinematic-primary-id-buffer.patch')
            before = before_files['Test_Cinematic.cpp']
            self.assertEqual(hashlib.sha256(before.encode('latin1')).hexdigest(),
                             '4196cdbae396e06dd4a5e1d5946509be01191f75735274763c223aea50c64d97')
            self.assertNotIn(b'offset', result.stdout)
            self.assertEqual(path.read_text(), before.replace('char id[10];',
                             'char id[12]; // signed 32-bit decimal ID, sign and terminator', 1))
        for value in (-2147483648, -1, 0, 2147483647):
            self.assertLessEqual(len(str(value).encode('ascii')) + 1, 12)

    def test_replay_removes_unused_bounded_path_without_changing_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Test_Cinematic.cpp'
            before_files, result = replay_to_patch(directory, 'scripts', ('Test_Cinematic.cpp',),
                'scripts-a35-cinematic-filename-diagnostics.patch')
            original = before_files['Test_Cinematic.cpp']
            self.assertEqual(hashlib.sha256(original.encode('latin1')).hexdigest(),
                             '32e962cf48da38f2c37afb05129fea3a9608e84ddd27bf037c7f2ad7d576b008')
            self.assertNotIn(b'offset', result.stdout)
            updated = path.read_text()
        start = original.index('\tvoid\tLoad_Control_File(')
        end = original.index('\n\t}', start) + len('\n\t}')
        updated_end = updated.index('\n\t}', start) + len('\n\t}')
        self.assertEqual(original[:start], updated[:start])
        self.assertEqual(original[end:], updated[updated_end:])
        body = updated[start:updated_end]
        self.assertNotIn('full_filename', body)
        self.assertNotIn('(int)filename', body)
        self.assertIn('Text_File_Open( filename )', body)
        self.assertIn('if ( handle == 0 )', body)
        self.assertIn('Failed to open DATA\\\\%s', body)
        self.assertIn('Text_File_Close( handle )', body)

    def test_current_staged_owner_retains_diagnostics_and_id_capacity(self):
        current = (ROOT / 'staging/scripts/Test_Cinematic.cpp').read_text()
        self.assertIn('char id[12]; // signed 32-bit decimal ID, sign and terminator', current)
        self.assertIn('Failed to open DATA\\\\%s', current)
        self.assertIn('Debug_Message( "Loading Control File %s\\n", filename )', current)

    def test_null_controls_disposal_remains_original_failure_behavior(self):
        original = (ROOT / 'upstream/CnC_Renegade/Code/Scripts/Test_Cinematic.cpp').read_text()
        created = original.split('void Created', 1)[1] if 'void Created' in original else original
        self.assertIn('Load_Control_File( Get_Parameter( "ControlFilename" ) );', created)
        self.assertIn('Parse_Commands( obj );', created)
        self.assertIn('Controls = NULL;', original)
        self.assertIn('} else {\n\t\t\tCommands->Destroy_Object( obj );', original)


if __name__ == '__main__':
    unittest.main()
