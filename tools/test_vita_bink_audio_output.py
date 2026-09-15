"""Retain native output pointers to catch reuse/clear before playback completes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BinkAudioOutputTest(unittest.TestCase):
    def test_native_queue_and_buffer_lifetime(self):
        source = (ROOT / 'port/platform/a4_binkmovie_boundary.cpp').read_text()
        start = source.index('void Queue_Audio(')
        end = source.index('bool Start_Audio_Output_Thread()\n{', start)
        with tempfile.TemporaryDirectory(prefix='renegade-bink-output-') as folder:
            directory = Path(folder)
            (directory / 'bink-audio-production.inc').write_text(source[start:end])
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra',
                '-Werror', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                '-pthread', '-I'+folder, '-I'+str(ROOT / 'port/audio/vita'),
                str(ROOT / 'tools/vita_bink_audio_output_test.cpp'),
                '-o', str(directory / 'test')], check=True)
            subprocess.run([str(directory / 'test')], check=True)


if __name__ == '__main__':
    unittest.main()
