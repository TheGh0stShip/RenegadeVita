"""The specialised audio mixer must match the original mixer bit for bit, and
the shared decoded-PCM cache must keep ownership and memory bounded."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / 'port/audio/vita/renegade_miles_provider.cpp'


class AudioMixerEquivalenceTests(unittest.TestCase):
    def build_and_run(self, flags, scenarios):
        with tempfile.TemporaryDirectory(prefix='renegade-audio-mixer-') as folder:
            binary = Path(folder) / 'test'
            subprocess.run(['g++', '-std=c++17', *flags, '-Wall', '-Wextra', '-Werror', '-pthread',
                            '-D_UNIX=1', '-DRENEGADE_MILES_MANUAL_MIX=1',
                            '-I' + str(ROOT / 'port/audio/miles'),
                            '-I' + str(ROOT / 'port/audio/vita'),
                            '-I' + str(ROOT / 'port/compatibility/include'),
                            str(ROOT / 'tools/vita_audio_mixer_equivalence_test.cpp'),
                            str(ROOT / 'port/audio/vita/renegade_wave_decoder.cpp'),
                            '-o', str(binary)], check=True)
            completed = subprocess.run(
                [str(binary), str(scenarios)], check=True, capture_output=True, text=True,
                timeout=600, env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1',
                                  'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'})
            self.assertIn('audio mixer equivalence PASS scenarios=%d' % scenarios, completed.stdout)
            self.assertIn('audio pcm cache PASS', completed.stdout)

    def test_sanitized(self):
        self.build_and_run(['-O1', '-g', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer'], 1500)

    def test_optimized_like_the_hot_path(self):
        self.build_and_run(['-O3', '-fno-math-errno', '-fno-trapping-math'], 3000)

    def test_wiring(self):
        source = PROVIDER.read_text()
        mix = source[source.index('void Mix_Locked('):source.index('void *Output_Thread(')]
        # Silent voices skip interpolation; compressed music keeps its exact
        # decode request order; PCM voices read the shared image.
        self.assertIn('Advance_Silent_Voice(sample, source_frames, step, frames);', mix)
        self.assertLess(mix.index('if (sample->mpeg) {'),
                        mix.index('if (gains[0] == 0.0F && gains[1] == 0.0F) {'))
        self.assertIn('sample->pcm->wave.samples.data()', mix)
        decode = source[source.index('bool Decode_Into_Sample('):source.index('void Reset_Sample(')]
        self.assertIn('Find_Cached_Pcm(hash, bytes)', decode)
        self.assertIn('bytes <= kPcmCacheMaximumSourceBytes', decode)
        self.assertIn('Clear_Pcm_Cache();', source[source.index('void AIL_shutdown(void)'):])
        thread = source[source.index('void *Output_Thread(void *)'):]
        self.assertIn('SCE_KERNEL_CPU_MASK_USER_1', thread[:thread.index('buffers;')])
        main = (ROOT / 'port/platform/vita/a30_main.cpp').read_text()
        self.assertIn('SCE_KERNEL_THREAD_ID_SELF, SCE_KERNEL_CPU_MASK_USER_0);', main)
        renderer = (ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp').read_text()
        self.assertLess(renderer.index('vglSetupGarbageCollector(0x10000100, SCE_KERNEL_CPU_MASK_USER_2);'),
                        renderer.index('vglInitExtended('))


if __name__ == '__main__':
    unittest.main()
