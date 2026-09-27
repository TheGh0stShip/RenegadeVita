#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import os
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaAudioProviderTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
