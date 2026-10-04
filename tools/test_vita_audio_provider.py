#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import os
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaAudioProviderTest(unittest.TestCase):
    def test_decoder_allocation_failure_preserves_previous_output(self) -> None:
        source = r'''
        #include "renegade_wave_decoder.h"
        #include <cstdlib>
        #include <new>
        #include <cstring>
        static bool fail_next = false;
        void *operator new(std::size_t n) {
            if (fail_next) { fail_next=false; throw std::bad_alloc(); }
            if (void *p=std::malloc(n ? n : 1)) return p;
            throw std::bad_alloc();
        }
        void operator delete(void *p) noexcept { std::free(p); }
        void operator delete(void *p, std::size_t) noexcept { std::free(p); }
        int main() {
            const unsigned char wave[] = {
                'R','I','F','F',38,0,0,0,'W','A','V','E',
                'f','m','t',' ',16,0,0,0,1,0,1,0,0x44,0xac,0,0,
                0x88,0x58,1,0,2,0,16,0,'d','a','t','a',2,0,0,0,1,0
            };
            RenegadeVitaAudio::DecodedWave decoded;
            decoded.channels=1; decoded.sample_rate=123; decoded.samples={77};
            RenegadeVitaAudio::WaveInfo info; info.sample_rate=456;
            const char *error=nullptr;
            fail_next=true;
            if (RenegadeVitaAudio::Decode_Wave_With_Info(wave,sizeof(wave),&decoded,&info,&error)) return 1;
            if (!error || std::strcmp(error,"WAVE decode allocation failed")) return 2;
            if (decoded.samples.size()!=1 || decoded.samples[0]!=77 || decoded.sample_rate!=123 || info.sample_rate!=456) return 3;
            if (!RenegadeVitaAudio::Decode_Wave_With_Info(wave,sizeof(wave),&decoded,&info,&error)) return 4;
            if (decoded.samples[0]!=1 || decoded.sample_rate!=44100) return 5;
        }
        '''
        with tempfile.TemporaryDirectory(prefix="renegade-wave-oom-") as temporary:
            cpp = pathlib.Path(temporary) / "oom.cpp"
            binary = pathlib.Path(temporary) / "oom"
            cpp.write_text(source)
            subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-I" + str(ROOT / "port/audio/vita"), str(cpp), str(ROOT / "port/audio/vita/renegade_wave_decoder.cpp"), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_decoder_and_manual_mixer(self) -> None:
        with tempfile.TemporaryDirectory(prefix="renegade-vita-audio-") as temporary:
            executable = pathlib.Path(temporary) / "vita-audio-provider-test"
            command = [
                "g++",
                "-std=c++17",
                "-O2",
                "-fsanitize=address,undefined",
                "-fno-omit-frame-pointer",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-pthread",
                "-D_UNIX=1",
                "-DRENEGADE_MILES_MANUAL_MIX=1",
                f"-I{ROOT / 'port/audio/miles'}",
                f"-I{ROOT / 'port/audio/vita'}",
                f"-I{ROOT / 'port/compatibility/include'}",
                str(ROOT / "tools/vita_audio_provider_test.cpp"),
                str(ROOT / "port/audio/vita/renegade_wave_decoder.cpp"),
                str(ROOT / "port/audio/vita/renegade_miles_provider.cpp"),
                "-o",
                str(executable),
            ]
            subprocess.run(command, cwd=ROOT, check=True)
            completed = subprocess.run(
                [str(executable)], cwd=ROOT, check=True, capture_output=True, text=True,
                env={**os.environ, "ASAN_OPTIONS": "detect_leaks=1:halt_on_error=1",
                     "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1"},
            )
            self.assertIn("vita_audio_provider=passed", completed.stdout)
            self.assertIn("vita_audio_continuous_lifecycle=passed", completed.stdout)
            self.assertIn("vita_audio_empty_pcm=passed", completed.stdout)


if __name__ == "__main__":
    unittest.main()
