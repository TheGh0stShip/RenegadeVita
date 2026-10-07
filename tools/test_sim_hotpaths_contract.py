"""SIM_HOTPATHS: per-wheel profiler opt-out and Combat scene-cast counters."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROFILE_H = ROOT / 'staging/wwdebug/wwprofile.h'
COLLISION = ROOT / 'staging/wwphys/pscene_collision.cpp'
BOUNDARY = ROOT / 'port/platform/a31_gameplay_boundary.cpp'
RUNTIME = ROOT / 'port/platform/vita/a31_vita_runtime.cpp'
PATCHES = {
    'wwdebug-a36-frame-profile-tu-opt-out.patch': (PROFILE_H, 'wwdebug'),
    'wwphys-a36-scene-cast-counters.patch': (COLLISION, 'wwphys'),
}


def preprocess(text):
    result = subprocess.run(['g++', '-E', '-P', '-x', 'c++', '-'], input=text,
                            text=True, capture_output=True, check=True)
    return ' '.join(result.stdout.split())


class FrameProfileTuOptOutTests(unittest.TestCase):
    def macro_block(self):
        source = PROFILE_H.read_text()
        start = source.index('#ifdef ENABLE_WWPROFILE')
        end = source.index('#endif', start) + len('#endif')
        # The scope class header is irrelevant to macro selection.
        return source[start:end].replace('#include "renegade_vita_frame_profile.h"', '')

    def test_skip_tu_compiles_scopes_out_only_when_defined(self):
        block = self.macro_block()
        probe = '\nvoid f() { WWPROFILE("Intersect_Spring"); WWROOTPROFILE("Root"); }\n'
        profiled = preprocess('#define RENEGADE_VITA_FRAME_PROFILE 1\n' + block + probe)
        self.assertIn('RenegadeVitaFrameProfileScope _wwprofile( "Intersect_Spring" )', profiled)
        self.assertIn('RenegadeVitaFrameProfileScope _wwprofile( "Root" )', profiled)
        skipped = preprocess('#define RENEGADE_VITA_FRAME_PROFILE 1\n'
                             '#define RENEGADE_VITA_FRAME_PROFILE_SKIP_TU 1\n' + block + probe)
        self.assertNotIn('RenegadeVitaFrameProfileScope', skipped)
        self.assertIn('void f() { ; ; }', skipped)

    def test_engine_tus_resolve_staged_wwprofile_header(self):
        cmake = (ROOT / 'CMakeLists.txt').read_text()
        includes = cmake[cmake.index('target_include_directories(${PROJECT_NAME} PRIVATE'):]
        includes = includes[:includes.index('\n)')]
        entries = [line.strip() for line in includes.splitlines()
                   if line.strip().startswith('${')]
        # Quote includes from staging/<module>/*.cpp search the -I list in
        # order; the staged (Vita-routed) header must win over the pristine one.
        self.assertIn('${RENEGADE_STAGE}/wwdebug', entries)
        self.assertLess(entries.index('${RENEGADE_STAGE}/wwdebug'),
                        entries.index('${RENEGADE_UPSTREAM}/Code/wwdebug'))
        staged = sorted(p.name.lower() for p in (ROOT / 'staging/wwdebug').glob('*.h'))
        self.assertEqual(staged, ['wwdebug.h', 'wwhack.h', 'wwmemlog.h', 'wwprofile.h'])

    def test_only_wheel_tu_opts_out(self):
        cmake = (ROOT / 'CMakeLists.txt').read_text()
        uses = re.findall(r'set_property\(SOURCE ([^\s]+) APPEND PROPERTY\s+'
                          r'COMPILE_DEFINITIONS RENEGADE_VITA_FRAME_PROFILE_SKIP_TU=1\)', cmake)
        self.assertEqual(uses, ['${RENEGADE_STAGE}/wwphys/wheel.cpp'])
        # The enclosing per-vehicle scope that still times the wheel loop.
        vehicle = (ROOT / 'staging/wwphys/vehiclephys.cpp').read_text()
        body = vehicle[vehicle.index('void VehiclePhysClass::Compute_Force_And_Torque'):]
        body = body[:body.index('LastGoodPosition.Set')]
        self.assertIn('WWPROFILE("VehiclePhysClass::Compute_Force_And_Torque");', body)
        self.assertIn('Wheels[iwheel]->Compute_Force_And_Torque(force,torque);', body)


class SceneCastCounterTests(unittest.TestCase):
    def function(self, source, signature):
        start = source.index(signature)
        return source[start:source.index('\n}\n', start)]

    def test_each_cast_counts_once_before_any_return(self):
        source = COLLISION.read_text()
        for kind, name in enumerate(('Cast_Ray', 'Cast_AABox', 'Cast_OBBox')):
            body = self.function(source, 'bool PhysicsSceneClass::%s(' % name)
            self.assertEqual(body.count('RENEGADE_COUNT_PHYS_CAST('), 1, name)
            self.assertIn('RENEGADE_COUNT_PHYS_CAST(%d, use_collision_region);' % kind, body)
            self.assertLess(body.index('RENEGADE_COUNT_PHYS_CAST('), body.index('return'))
        self.assertIn('#define RENEGADE_COUNT_PHYS_CAST(kind, region) ((void)0)', source)

    def test_boundary_windows_combat_stage_deltas(self):
        boundary = BOUNDARY.read_text()
        frame = boundary.split('void A31_Interactive_Run_Simulation_Frame()', 1)[1]
        frame = frame.split('A31SimulationStageTotals A31_Interactive_Get_Simulation_Stage_Totals', 1)[0]
        snapshot = frame.index('casts_before[kind] = g_renegade_phys_cast_counts[kind];')
        think = frame.index('CombatManager::Think();')
        accumulate = frame.index('g_renegade_phys_cast_counts[kind] - casts_before[kind];')
        self.assertLess(frame.index('network_end_us = sceKernelGetProcessTimeWide();'), snapshot)
        self.assertLess(snapshot, think)
        self.assertLess(think, accumulate)
        self.assertLess(frame.index('combat_end_us = sceKernelGetProcessTimeWide();'), accumulate)
        runtime = RUNTIME.read_text()
        log = runtime[runtime.index('void Log_Campaign_Simulation_Stages()'):]
        log = log[:log.index('\n}\n')]
        self.assertIn('A4 combat casts: frames=%u window=%u combat_avg_us=%llu', log)
        self.assertIn('if (stages.frames < previous.frames) previous = A31SimulationStageTotals();', log)


class PatchRegistrationTests(unittest.TestCase):
    def test_patches_registered_once_and_match_staging(self):
        stage = (ROOT / 'tools/stage_sources.sh').read_text()
        for patch, (staged, module) in PATCHES.items():
            path = ROOT / 'port/patches' / patch
            self.assertTrue(path.is_file(), patch)
            self.assertEqual(stage.count('-d "$rv_stage/%s" -p1 < "$rv_root/port/patches/%s"'
                                         % (module, patch)), 1, patch)
            # The staged file is exactly the patch result: reverse applies cleanly.
            result = subprocess.run(['patch', '--dry-run', '-R', '-F0', '-p1', '-d',
                                     str(staged.parent), '-i', str(path)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
