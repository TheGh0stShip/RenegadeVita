"""Original animation-frame regression and native clock-owner boundary."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class AnimationClock(unittest.TestCase):
    def test_original_frame_progress_under_irregular_ticks(self):
        text = (ROOT / 'staging/ww3d2/animobj.cpp').read_text()
        begin = text.index('float Animatable3DObjClass::Compute_Current_Frame() const')
        end = text.index('/***********************************************************************************************', begin + 1)
        with tempfile.TemporaryDirectory(prefix='renegade-animation-clock-') as folder:
            p = Path(folder)
            (p / 'production.inc').write_text(text[begin:end])
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-I' + folder,
                str(ROOT / 'tools/vita_animation_clock_test.cpp'), '-o', str(p / 'test')], check=True)
            subprocess.run([str(p / 'test')], check=True)

    def test_native_gameplay_and_pause_have_one_original_clock_owner(self):
        text = (ROOT / 'port/platform/vita/a31_vita_runtime.cpp').read_text()
        pause = text.split('bool Run_Original_Gameplay_Pause_Menu(', 1)[1].split(
            'bool Try_Latch_Development_Save()', 1)[0]
        self.assertNotIn('WW3D::Sync(', pause)
        self.assertIn('TimeManager::Update();', pause)
        loop = text.split('const uint64_t frame_begin = sceKernelGetProcessTimeWide();', 1)[1].split(
            'A31_Interactive_Run_Simulation_Frame();', 1)[0]
        self.assertNotIn('WW3D::Sync(', loop)
        simulation = (ROOT / 'port/platform/a31_gameplay_boundary.cpp').read_text().split(
            'void A31_Interactive_Run_Simulation_Frame()', 1)[1]
        self.assertLess(simulation.index('TimeManager::Update();'), simulation.index('Input::Update();'))
        original = (ROOT / 'staging/combat/timemgr.cpp').read_text()
        self.assertIn('WW3D::Sync( WW3D::Get_Sync_Time() + FrameTicks );', original)
