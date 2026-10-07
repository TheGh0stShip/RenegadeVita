"""The specialised audio mixer must match the original mixer bit for bit, and
the shared decoded-PCM cache must keep ownership and memory bounded."""
from pathlib import Path
import os
import shutil
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
            self.assertIn('audio inverse distance rolloff PASS', completed.stdout)

    def test_sanitized(self):
        self.build_and_run(['-O1', '-g', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer'], 1500)

    def test_optimized_like_the_hot_path(self):
        self.build_and_run(['-O3', '-fno-math-errno', '-fno-trapping-math'], 3000)

    def test_real_mpg123_window_matches_original_mixer(self):
        # The windowed MPEG mixer against the original per-frame mixer on
        # production mpg123 playbacks (sequential play, seeks, loop wraps).
        sdk = Path(os.environ.get('VITASDK', '/usr/local/vitasdk')) / 'arm-vita-eabi/include'
        if shutil.which('ffmpeg') is None or not (sdk / 'mpg123.h').exists():
            self.skipTest('ffmpeg or mpg123 headers unavailable')
        with tempfile.TemporaryDirectory(prefix='renegade-audio-mpeg-') as folder:
            work = Path(folder)
            for header in ('mpg123.h', 'fmt123.h'):
                shutil.copy2(sdk / header, work / header)
            fixtures = []
            for name, source, channels, extra in [
                    ('stereo.mp3', 'sine=frequency=440:duration=3:sample_rate=44100', 2, []),
                    ('mono.mp3', 'anoisesrc=d=2:c=pink:r=22050:a=0.5', 1, ['-b:a', '32k'])]:
                fixture = work / name
                subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', source,
                                '-ac', str(channels), '-codec:a', 'libmp3lame', *extra,
                                str(fixture)], check=True)
                fixtures.append(str(fixture))
            binary = work / 'test'
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror', '-pthread',
                            '-D_UNIX=1', '-DRENEGADE_MILES_MANUAL_MIX=1', '-DRENEGADE_AUDIO_MPG123=1',
                            '-I' + str(work), '-I' + str(ROOT / 'port/audio/miles'),
                            '-I' + str(ROOT / 'port/audio/vita'),
                            '-I' + str(ROOT / 'port/compatibility/include'),
                            str(ROOT / 'tools/vita_audio_mixer_equivalence_test.cpp'),
                            str(ROOT / 'port/audio/vita/renegade_wave_decoder.cpp'),
                            '-l:libmpg123.so.0', '-o', str(binary)], check=True)
            completed = subprocess.run([str(binary), '0', *fixtures], check=True,
                                       capture_output=True, text=True, timeout=600)
            self.assertEqual(completed.stdout.count('audio real mpeg window PASS'), 2)

    def test_wiring(self):
        source = PROVIDER.read_text()
        mix = source[source.index('void Mix_Locked('):source.index('void *Output_Thread(')]
        # Silent voices skip interpolation; compressed music keeps its exact
        # decode request order; PCM voices read the shared image.
        self.assertIn('Advance_Silent_Voice(sample, source_frames, step, frames);', mix)
        self.assertLess(mix.index('if (sample->mpeg) {'),
                        mix.index('if (gains[0] == 0.0F && gains[1] == 0.0F) {'))
        self.assertIn('sample->pcm->wave.samples.data()', mix)
        # MPEG voices read resident decoded frames in place and fall back to
        # Sample() in the original request order only outside the window.
        mpeg = source[source.index('void Mix_Mpeg_Voice('):source.index('void Mix_Locked(')]
        self.assertIn('mpeg.Resident_Window(&window_first, &window_frames)', mpeg)
        self.assertLess(mpeg.index('values[0] = mpeg.Sample(first, 0U);'),
                        mpeg.index('values[3] = mpeg.Sample(second, right_channel);'))
        # MPEG sample files are opened before the provider lock is taken.
        for entry in ('S32 AIL_set_named_sample_file(', 'U32 AIL_set_3D_sample_file_bounded('):
            body = source[source.index(entry):]
            self.assertLess(body.index('Prepare_Sample_Mpeg(sample, data, bytes);'),
                            body.index('AIL_lock();'))
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
