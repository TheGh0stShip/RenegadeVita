#!/usr/bin/env python3
"""Host build of the RVAU1 audio cost equivalence test (needs g++).

Mixes the same stream/3D-sample sequence under every audio-cost-v1.flag mask
and requires output identical to mask 0, under ASan/UBSan. The pure-Python
contract lives in tools/test_vita_audio_cost_contract.py.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaAudioCostEquivalenceTest(unittest.TestCase):
    @unittest.skipIf(shutil.which("g++") is None, "g++ not available")
    def test_every_mask_mixes_identically(self) -> None:
        with tempfile.TemporaryDirectory(prefix="renegade-audio-cost-") as temporary:
            executable = pathlib.Path(temporary) / "vita-audio-cost-equivalence"
            command = [
                "g++", "-std=c++17", "-O2", "-fsanitize=address,undefined",
                "-fno-omit-frame-pointer", "-Wall", "-Wextra", "-Werror", "-pthread",
                "-D_UNIX=1", "-DRENEGADE_MILES_MANUAL_MIX=1",
                f"-I{ROOT / 'port/audio/miles'}",
                f"-I{ROOT / 'port/audio/vita'}",
                f"-I{ROOT / 'port/compatibility/include'}",
                str(ROOT / "tools/vita_audio_cost_equivalence_test.cpp"),
                str(ROOT / "port/audio/vita/renegade_wave_decoder.cpp"),
                str(ROOT / "port/audio/vita/renegade_miles_provider.cpp"),
                "-o", str(executable),
            ]
            subprocess.run(command, cwd=ROOT, check=True)
            completed = subprocess.run(
                [str(executable)], cwd=ROOT, check=True, capture_output=True, text=True,
                env={**os.environ, "ASAN_OPTIONS": "detect_leaks=1:halt_on_error=1",
                     "UBSAN_OPTIONS": "halt_on_error=1:print_stacktrace=1"},
            )
            self.assertIn("vita_audio_cost_equivalence=passed", completed.stdout)


if __name__ == "__main__":
    unittest.main()
