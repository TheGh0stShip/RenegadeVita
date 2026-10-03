"""Source-only checks; no compiler, staging entrypoint or audio execution."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BoundedAudioContract(unittest.TestCase):
    def test_original_owner_patch_replays_without_fuzz(self):
        original = ROOT / 'staging/wwaudio/sound3dhandle.cpp'
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / original.name
            target.write_bytes(original.read_bytes())
            result = subprocess.run(
                ['patch', '--batch', '--forward', '--fuzz=0',
                 '--no-backup-if-mismatch', '-p1', '-d', directory],
                input=(ROOT / 'port/patches/wwaudio-a35-bounded-3d-sample.patch').read_bytes(),
                capture_output=True, check=True)
            self.assertNotIn(b'offset', result.stdout)
            text = target.read_text()
            self.assertIn('::AIL_set_3D_sample_file_bounded', text)
            self.assertIn('static_cast<size_t>(Buffer->Get_Length ())', text)
            self.assertNotIn('::AIL_set_3D_sample_file (', text)
            self.assertEqual(list(Path(directory).glob('*.rej')), [])

    def test_bounded_provider_uses_actual_size(self):
        text = (ROOT / 'port/audio/vita/renegade_miles_provider.cpp').read_text()
        body = text.split('U32 AIL_set_3D_sample_file_bounded(', 1)[1].split(
            'void AIL_start_3D_sample', 1)[0]
        self.assertNotIn('Declared_Wave_Bytes', body)
        self.assertIn('Decode_Into_Sample(sample, data, bytes)', body)
        self.assertEqual(body.count('++g_stats.sample_3d_file_load_attempts'), 1)

    def test_length_type_and_patch_registration(self):
        header = (ROOT / 'port/audio/miles/mss.h').read_text()
        self.assertIn('const void *data, size_t bytes);', header)
        stage = (ROOT / 'tools/stage_sources.sh').read_text()
        self.assertEqual(stage.count('wwaudio-a35-bounded-3d-sample.patch'), 1)
        self.assertIn('11b6c2b0edc90c897083bd8241b08264dd9b8cbf9375171b53af2ce79720df97', stage)


if __name__ == '__main__':
    unittest.main()
