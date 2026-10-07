"""AIL_set_3D_position must not wait for the mixer, and a published position
must be applied in call order before anything can observe it (ASan/UBSan with
deterministic interleavings; TSan is unavailable on this WSL kernel)."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / 'port/audio/vita/renegade_miles_provider.cpp'


class DeferredPositionTests(unittest.TestCase):
    def build_and_run(self, flags):
        with tempfile.TemporaryDirectory(prefix='renegade-audio-position-') as folder:
            binary = Path(folder) / 'test'
            subprocess.run(['g++', '-std=c++17', *flags, '-Wall', '-Wextra', '-Werror', '-pthread',
                            '-D_UNIX=1', '-DRENEGADE_MILES_MANUAL_MIX=1',
                            '-I' + str(ROOT / 'port/audio/miles'),
                            '-I' + str(ROOT / 'port/audio/vita'),
                            '-I' + str(ROOT / 'port/compatibility/include'),
                            str(ROOT / 'tools/vita_audio_deferred_position_test.cpp'),
                            str(ROOT / 'port/audio/vita/renegade_wave_decoder.cpp'),
                            '-o', str(binary)], check=True)
            completed = subprocess.run(
                [str(binary)], check=True, capture_output=True, text=True, timeout=600,
                env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1',
                     'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'})
            for name in ('non-blocking', 'ordering', 'mix', 'release', 'full queue', 'concurrent'):
                self.assertIn('deferred position %s PASS' % name, completed.stdout)

    def test_sanitized(self):
        self.build_and_run(['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'])

    def test_optimized(self):
        self.build_and_run(['-O3', '-fno-math-errno', '-fno-trapping-math'])

    def test_wiring(self):
        source = PROVIDER.read_text()
        lock = source[source.index('void AIL_lock(void)'):source.index('void AIL_unlock(void)')]
        self.assertIn('Apply_Pending_Positions_Locked();', lock)
        thread = source[source.index('void *Output_Thread(void *)'):source.index('bool Start_Output()')]
        self.assertLess(thread.index('Apply_Pending_Positions_Locked();'),
                        thread.index('Mix_Locked(output.data(), kOutputFrames, &mix_summary);'))
        release = source[source.index('void Release_Sample('):source.index('bool Read_Stream_Image(')]
        self.assertIn('Forget_Pending_Position_Locked(sample);', release)
        position = source[source.index('void AIL_set_3D_position('):
                          source.index('void AIL_set_3D_orientation(')]
        self.assertIn('pthread_mutex_trylock(&g_mutex)', position)
        self.assertLess(position.index('Apply_Pending_Positions_Locked();'),
                        position.index('Apply_3D_Position_Locked(sample, x, y, z);'))


if __name__ == '__main__':
    unittest.main()
