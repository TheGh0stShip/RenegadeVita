"""Source-only control-file diagnostics contracts; no engine execution."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def remove_command_bounds_patch(path, args):
    if 'if ( len > 0 && len < MAX_COMMAND_LOAD_SIZE )' in path.read_text():
        patch = (ROOT / 'port/patches/scripts-a35-cinematic-command-load-bounds.patch').read_bytes()
        subprocess.run(args + ['--reverse'], input=patch, capture_output=True, check=True)


class CinematicFilenameDiagnosticsTests(unittest.TestCase):
    def test_primary_callback_buffer_covers_signed_32_bit_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Test_Cinematic.cpp'
            path.write_bytes((ROOT / 'staging/scripts/Test_Cinematic.cpp').read_bytes())
            args = ['patch', '--batch', '--fuzz=0', '--no-backup-if-mismatch', '-p1', '-d', directory]
            remove_command_bounds_patch(path, args)
            filename_patch = (ROOT / 'port/patches/scripts-a35-cinematic-filename-diagnostics.patch').read_bytes()
            primary_patch = (ROOT / 'port/patches/scripts-a35-cinematic-primary-id-buffer.patch').read_bytes()
            if 'char id[12]' in path.read_text():
                subprocess.run(args + ['--reverse'], input=primary_patch, capture_output=True, check=True)
            if 'Failed to open DATA\\\\%s' not in path.read_text():
                subprocess.run(args + ['--forward'], input=filename_patch, capture_output=True, check=True)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             '4196cdbae396e06dd4a5e1d5946509be01191f75735274763c223aea50c64d97')
            before = path.read_text()
            result = subprocess.run(args + ['--forward'], input=primary_patch, capture_output=True, check=True)
            self.assertNotIn(b'offset', result.stdout)
            self.assertEqual(path.read_text(), before.replace('char id[10];',
                             'char id[12]; // signed 32-bit decimal ID, sign and terminator', 1))
        for value in (-2147483648, -1, 0, 2147483647):
            self.assertLessEqual(len(str(value).encode('ascii')) + 1, 12)

    def test_replay_removes_unused_bounded_path_without_changing_parser(self):
        patch = (ROOT / 'port/patches/scripts-a35-cinematic-filename-diagnostics.patch').read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Test_Cinematic.cpp'
            path.write_bytes((ROOT / 'staging/scripts/Test_Cinematic.cpp').read_bytes())
            args = ['patch', '--batch', '--fuzz=0', '--no-backup-if-mismatch', '-p1', '-d', directory]
            remove_command_bounds_patch(path, args)
            if 'Failed to open DATA\\\\%s' in path.read_text():
                if 'char id[12]' in path.read_text():
                    primary = (ROOT / 'port/patches/scripts-a35-cinematic-primary-id-buffer.patch').read_bytes()
                    subprocess.run(args + ['--reverse'], input=primary, capture_output=True, check=True)
                reverse = subprocess.run(args + ['--reverse'], input=patch,
                                         capture_output=True, check=True)
                self.assertNotIn(b'offset', reverse.stdout)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             '32e962cf48da38f2c37afb05129fea3a9608e84ddd27bf037c7f2ad7d576b008')
            original = path.read_text()
            result = subprocess.run(args + ['--forward'], input=patch,
                                    capture_output=True, check=True)
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

    def test_null_controls_disposal_remains_original_failure_behavior(self):
        original = (ROOT / 'upstream/CnC_Renegade/Code/Scripts/Test_Cinematic.cpp').read_text()
        created = original.split('void Created', 1)[1] if 'void Created' in original else original
        self.assertIn('Load_Control_File( Get_Parameter( "ControlFilename" ) );', created)
        self.assertIn('Parse_Commands( obj );', created)
        self.assertIn('Controls = NULL;', original)
        self.assertIn('} else {\n\t\t\tCommands->Destroy_Object( obj );', original)


if __name__ == '__main__':
    unittest.main()
