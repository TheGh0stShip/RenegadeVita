"""First-run Vita Performance defaults come from the original option system.

The C++ table in port/platform/renegade_vita_performance_defaults.h is checked
against an independent Python transcription of WWConfig AutoConfigSettings,
the saved-record override is checked, and build overrides are limited to the
original option values.
"""
from itertools import product
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = Path(os.environ.get('RENEGADE_UPSTREAM_CODE', ROOT / 'upstream/CnC_Renegade/Code'))
AUTOCONFIG = UPSTREAM / 'Tools/WWConfig/PerformanceConfigDialog.cpp'


def original_auto_config(dxtc, tnl, high_end, rtt):
    """Independent transcription of PerformanceConfigDialog.cpp AutoConfigSettings."""
    texture = 0 if dxtc else 1
    lod = 10000 if tnl else (5000 if high_end else 0)
    if rtt:
        shadow, static_shadows = (3, 1) if tnl else (2, 0)
    else:
        shadow, static_shadows = (1 if high_end else 0), 0
    surface = 2 if tnl else (1 if high_end else 0)
    particle = 2 if (tnl and high_end) else (1 if (tnl or high_end) else 0)
    return (texture, lod, lod, shadow, static_shadows, surface, particle)


HARNESS = r'''
#include "renegade_vita_performance_defaults.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
using namespace RenegadeVitaPerformanceDefaults;
int main() {
 for (int bits = 0; bits < 16; ++bits) {
  const OriginalAutoConfigInputs in = {(bits & 1) != 0, (bits & 2) != 0, (bits & 4) != 0, (bits & 8) != 0};
  const OriginalAutoConfig o = Original_Auto_Config(in);
  printf("%d %d %d %d %d %d %d %d\n", bits, o.texture_resolution, o.dynamic_lod_budget,
   o.static_lod_budget, o.shadow_mode, o.static_shadows, o.surface_effect, o.particle_detail);
 }
 const Performance d = Vita_Default();
 printf("default %u %u %u %u\n", d.static_budget, d.dynamic_budget, d.texture_reduction, d.surface_effect_mode);
 // No Performance record (fresh install or audio-only record) -> defaults.
 RenegadeVitaUserSettings::Record r;
 Performance e = Effective(r);
 assert(memcmp(&e, &d, sizeof(e)) == 0);
 r.value[0] = RenegadeVitaUserSettings::Audio;
 r.value[9] = 12345; r.value[10] = 6789; r.value[11] = 1; r.value[12] = 0;
 e = Effective(r);
 assert(memcmp(&e, &d, sizeof(e)) == 0);
 // A record saved by the original Performance tab always wins, exactly.
 r.value[0] |= RenegadeVitaUserSettings::Performance;
 e = Effective(r);
 assert(e.static_budget == 12345 && e.dynamic_budget == 6789 &&
  e.texture_reduction == 1 && e.surface_effect_mode == 0);
 // Defaults must be storable unchanged by the existing record validator.
 RenegadeVitaUserSettings::Record stored;
 stored.value[0] = RenegadeVitaUserSettings::Performance;
 stored.value[9] = d.static_budget; stored.value[10] = d.dynamic_budget;
 stored.value[11] = d.texture_reduction; stored.value[12] = d.surface_effect_mode;
 assert(RenegadeVitaUserSettings::Valid(stored));
 for (int g = 0; g <= 2; ++g) printf("geometry %d %d\n", g, Original_Geometry_Detail_Budget(g));
 return 0;
}
'''


class VitaPerformanceDefaultsTests(unittest.TestCase):
    def build_and_run(self, defines=()):
        with tempfile.TemporaryDirectory(prefix='vita-perf-defaults-') as folder:
            directory = Path(folder)
            (directory / 'main.cpp').write_text(HARNESS)
            subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror', *defines,
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            '-I' + str(ROOT / 'port/platform'), str(directory / 'main.cpp'),
                            '-o', str(directory / 'test')], check=True)
            result = subprocess.run([str(directory / 'test')], check=True, capture_output=True, text=True,
                                    env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1',
                                         'UBSAN_OPTIONS': 'halt_on_error=1'})
            return result.stdout.splitlines()

    def test_decision_table_matches_original_auto_config(self):
        lines = self.build_and_run()
        for bits, line in zip(range(16), lines[:16]):
            dxtc, tnl, high_end, rtt = (bits & 1) != 0, (bits & 2) != 0, (bits & 4) != 0, (bits & 8) != 0
            got = tuple(int(v) for v in line.split()[1:])
            self.assertEqual(got, original_auto_config(dxtc, tnl, high_end, rtt), line)
        self.assertEqual(lines[-3:], ['geometry 0 0', 'geometry 1 5000', 'geometry 2 10000'])

    def test_vita_default_is_original_slow_pc_geometry_and_full_texture(self):
        lines = self.build_and_run()
        # Vita inputs: DXTC yes, T&L no, SSE-class CPU no, render target yes.
        expected = original_auto_config(True, False, False, True)
        self.assertEqual(lines[16], f'default {expected[2]} {expected[1]} {expected[0]} 2')
        self.assertEqual(lines[16], 'default 0 0 0 2')
        # The original Performance tab shows budgets below 1000 as Geometry "Low".
        self.assertLess(expected[1], 1000)

    def test_build_overrides_are_original_option_values(self):
        self.assertEqual(self.build_and_run(['-DRENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL=1'])[16],
                         'default 5000 5000 0 2')
        self.assertEqual(self.build_and_run(['-DRENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL=2',
                                             '-DRENEGADE_VITA_DEFAULT_SURFACE_EFFECT_DETAIL=1'])[16],
                         'default 10000 10000 0 1')
        for bad in ('-DRENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL=3', '-DRENEGADE_VITA_DEFAULT_SURFACE_EFFECT_DETAIL=3'):
            with self.assertRaises(subprocess.CalledProcessError):
                with open(os.devnull, 'w') as sink:
                    with tempfile.TemporaryDirectory(prefix='vita-perf-defaults-bad-') as folder:
                        source = Path(folder) / 'main.cpp'
                        source.write_text(HARNESS)
                        subprocess.run(['g++', '-std=c++17', '-fsyntax-only', bad,
                                        '-I' + str(ROOT / 'port/platform'), str(source)],
                                       check=True, stderr=sink)

    @unittest.skipUnless(AUTOCONFIG.is_file(), 'upstream WWConfig source not present')
    def test_upstream_auto_config_constants_unchanged(self):
        text = AUTOCONFIG.read_text(encoding='latin1').replace('\r', '')
        body = text[text.index('void AutoConfigSettings() \n{'):]
        for needle in ('registry.Set_Int (VALUE_NAME_DYN_LOD, 10000);',
                       'registry.Set_Int (VALUE_NAME_DYN_LOD, 5000);',
                       'registry.Set_Int (VALUE_NAME_DYN_LOD, 0);',
                       'registry.Set_Int (VALUE_NAME_TEXTURE_RES, 0);',
                       'registry.Set_Int (VALUE_NAME_SURFACE_EFFECT, 0);',
                       'bool high_end_processor=CPUDetectClass::Has_SSE_Instruction_Set();'):
            self.assertIn(needle, body)
        dialog = (UPSTREAM / 'Commando/dlgconfigperformancetab.cpp').read_text(encoding='latin1')
        for needle in ('const int MAX_LOD_HIGH\t= 10000;', 'const int MAX_LOD_MED\t= 5000;',
                       'const int MAX_LOD_LOW\t= 0;'):
            self.assertIn(needle, dialog)


if __name__ == '__main__':
    unittest.main()
