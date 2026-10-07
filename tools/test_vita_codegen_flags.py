"""Code generation flags stay value-preserving.

The original sources pun float/int storage, so the game target must keep
-fno-strict-aliasing. Per-source -O3 (hot path, and the RENEGADE_VITA_SIM_O3
hardware A/B option) is appended after every per-source COMPILE_OPTIONS
override, keeps random.cpp -fwrapv and the -fpermissive script units, and
leaves the default build unchanged when the A/B option is OFF.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CMAKELISTS = ROOT / 'CMakeLists.txt'
VITA_GXX = Path('/usr/local/vitasdk/bin/arm-vita-eabi-g++')

HOT_BLOCK_START = '# Source COMPILE_OPTIONS follow the configuration flags'
SIM_BLOCK_END = 'message(STATUS "Simulation -O3 translation units (A/B)'

HARNESS = """cmake_minimum_required(VERSION 3.16)
project(RenegadeCodegenFlagsTest NONE)
set(RENEGADE_STAGE "${CMAKE_CURRENT_SOURCE_DIR}/staging")
set(PROJECT_NAME rv_codegen_flags)
add_custom_target(${PROJECT_NAME} SOURCES
  ${RENEGADE_STAGE}/combat/soldier.cpp ${RENEGADE_STAGE}/combat/scripts.cpp
  ${RENEGADE_STAGE}/wwlib/random.cpp ${RENEGADE_STAGE}/wwphys/pscene.cpp
  ${RENEGADE_STAGE}/commando/cnetwork.cpp)
set_property(SOURCE ${RENEGADE_STAGE}/wwlib/random.cpp APPEND PROPERTY COMPILE_OPTIONS -fwrapv)
set_source_files_properties(${RENEGADE_STAGE}/combat/scripts.cpp PROPERTIES COMPILE_OPTIONS "-fpermissive")
include(${CMAKE_CURRENT_SOURCE_DIR}/blocks.cmake)
foreach(s IN ITEMS combat/soldier.cpp combat/scripts.cpp wwlib/random.cpp wwphys/pscene.cpp commando/cnetwork.cpp)
  get_source_file_property(o ${RENEGADE_STAGE}/${s} COMPILE_OPTIONS)
  message(STATUS "OPTS ${s}=${o}")
endforeach()
"""


def extract_blocks(text):
    start = text.index(HOT_BLOCK_START)
    end = text.index('endif()', text.index(SIM_BLOCK_END)) + len('endif()')
    return text[start:end] + '\n'


class VitaCodegenFlagsTests(unittest.TestCase):
    def setUp(self):
        self.text = CMAKELISTS.read_text()

    def test_target_keeps_value_preserving_flags(self):
        options = self.text[self.text.index('target_compile_options(${PROJECT_NAME} PRIVATE'):]
        options = options[:options.index(')\n')]
        for flag in ('-fno-strict-aliasing', '-fno-math-errno', '-fno-trapping-math'):
            self.assertIn(flag, options)
        for unsafe in ('-ffast-math', '-Ofast', '-funsafe-math-optimizations',
                       '-ffinite-math-only', '-fno-signed-zeros', '-fstrict-enums'):
            self.assertNotIn(unsafe, self.text)

    def test_sim_o3_is_opt_in_and_after_every_source_override(self):
        self.assertRegex(self.text, re.compile(
            r'option\(RENEGADE_VITA_SIM_O3\s*\n\s*"[^"]*"\s*OFF\)'))
        sim_block = self.text.index(SIM_BLOCK_END)
        hot_block = self.text.index(HOT_BLOCK_START)
        self.assertLess(hot_block, sim_block)
        overrides = [m.start() for m in re.finditer(
            r'^\s*set_source_files_properties\(', self.text, re.M)]
        self.assertTrue(overrides)
        self.assertLess(max(overrides), hot_block)

    def configure(self, folder, *defines):
        build = folder / ('build' + ''.join(d.replace('=', '_') for d in defines))
        completed = subprocess.run(
            ['cmake', '-S', str(folder), '-B', str(build), *defines],
            check=True, capture_output=True, text=True)
        return dict(re.findall(r'OPTS (\S+)=(.*)', completed.stdout))

    @unittest.skipUnless(shutil.which('cmake'), 'cmake not installed')
    def test_option_matrix(self):
        with tempfile.TemporaryDirectory(prefix='rv-codegen-') as name:
            folder = Path(name)
            for rel in ('combat/soldier.cpp', 'combat/scripts.cpp', 'wwlib/random.cpp',
                        'wwphys/pscene.cpp', 'commando/cnetwork.cpp'):
                (folder / 'staging' / rel).parent.mkdir(parents=True, exist_ok=True)
                (folder / 'staging' / rel).write_text('')
            (folder / 'CMakeLists.txt').write_text(HARNESS)
            (folder / 'blocks.cmake').write_text(extract_blocks(self.text))
            default = self.configure(folder, '-DRENEGADE_VITA_HOT_PATH_O3=ON')
            self.assertEqual(default['combat/soldier.cpp'], 'NOTFOUND')
            self.assertEqual(default['combat/scripts.cpp'], '-fpermissive')
            self.assertEqual(default['wwlib/random.cpp'], '-fwrapv')
            self.assertEqual(default['wwphys/pscene.cpp'], '-O3')
            sim = self.configure(folder, '-DRENEGADE_VITA_HOT_PATH_O3=ON',
                                 '-DRENEGADE_VITA_SIM_O3=ON')
            self.assertEqual(sim['combat/soldier.cpp'], '-O3')
            self.assertEqual(sim['combat/scripts.cpp'], '-fpermissive;-O3')
            self.assertEqual(sim['wwlib/random.cpp'], '-fwrapv;-O3')
            self.assertEqual(sim['wwphys/pscene.cpp'], '-O3')
            self.assertEqual(sim['commando/cnetwork.cpp'], 'NOTFOUND')

    @unittest.skipUnless(VITA_GXX.exists(), 'VitaSDK compiler not installed')
    def test_trailing_o3_keeps_explicit_flags(self):
        completed = subprocess.run(
            [str(VITA_GXX), '-O2', '-fno-strict-aliasing', '-fno-math-errno',
             '-fno-trapping-math', '-fwrapv', '-O3', '-Q', '--help=optimizers'],
            check=True, capture_output=True, text=True)
        state = dict(re.findall(r'^\s+(-f[\w-]+)\s+\[(enabled|disabled)\]',
                                completed.stdout, re.M))
        self.assertEqual(state['-fstrict-aliasing'], 'disabled')
        self.assertEqual(state['-fmath-errno'], 'disabled')
        self.assertEqual(state['-ftrapping-math'], 'disabled')
        self.assertEqual(state['-fwrapv'], 'enabled')
        self.assertEqual(state['-funsafe-math-optimizations'], 'disabled')


if __name__ == '__main__':
    unittest.main()
