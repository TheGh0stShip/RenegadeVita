"""Guard required original mission and W3D owners in native/host manifests."""
import re
import unittest
from pathlib import Path

from tools.check_m13_script_coverage import selected_owners

ROOT = Path(__file__).resolve().parents[1]


class RequestedMissionOwnerContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = (ROOT / 'CMakeLists.txt').read_text(encoding='utf-8')
        cls.host = (ROOT / 'tools/host_a30_definitions/CMakeLists.txt').read_text(encoding='utf-8')
        cls.runtime = (ROOT / 'port/platform/vita/a31_vita_runtime.cpp').read_text(encoding='utf-8')

    def test_required_original_scripts_selected_for_vita_and_host(self):
        scripts = ('Mission03.cpp', 'Mission11.cpp', 'Test_DAK.cpp',
                   'Test_RMV_Toolkit.cpp', 'Toolkit_Sounds.cpp')
        for target, owners in selected_owners(ROOT).items():
            self.assertTrue(set(scripts) <= owners, (target, set(scripts) - owners))

    def test_unselected_script_call_defaults_are_scoped(self):
        for cmake, prefix in ((self.native, 'RENEGADE'), (self.host, 'RV')):
            blocks = re.findall(r'set_property\(SOURCE\s+([^)]*)\)', cmake, re.S)
            shared = [b for b in blocks if f'${{{prefix}_COMPAT}}/renegade_script_call_defaults.h' in b]
            m01 = [b for b in blocks if f'${{{prefix}_COMPAT}}/renegade_m01_script_defaults.h' in b]
            production = [b for b in shared if '${RENEGADE_SCRIPT_DSP_SOURCES}' in b]
            self.assertEqual(len(production), 1)
            if prefix == 'RV':
                probes = [b for b in shared if b not in production]
                self.assertEqual(len(probes), 1)
                self.assertIn('host_original_script_vector_parser_test.cpp', probes[0])
                self.assertIn('host_cinematic_save_test.cpp', probes[0])
                self.assertNotIn('trim.cpp', probes[0])
            else:
                self.assertEqual(len(shared), 1)
            self.assertEqual(len(m01), 2)
            self.assertEqual(sum('Mission11.cpp' in block for block in m01), 1)

    def test_original_w3d_loader_owners_are_selected(self):
        for source in ('sphereobj.cpp', 'ringobj.cpp', 'soundrobj.cpp'):
            self.assertIn('${RENEGADE_STAGE}/ww3d2/' + source, self.native)
            self.assertIn('${RV_STAGE}/ww3d2/' + source, self.host)

    def test_original_loader_registration_and_particle_defaults(self):
        tokens = ('&_ParticleEmitterLoader', '&_SphereLoader', '&_RingLoader', '&_SoundRenderObjLoader')
        for token in tokens:
            self.assertEqual(self.runtime.count('Register_Prototype_Loader(' + token + ')'), 1)
        self.assertIn('ParticleEmitterClass::Set_Default_Remove_On_Complete(false)', self.runtime)
        values = re.search(r'particle_lod_max_screen_sizes\[17\]\s*=\s*\{(.*?)\}', self.runtime, re.S).group(1)
        self.assertEqual(len(re.findall(r'(?<![A-Za-z_])(?:\d+\.\d+f|WWMATH_FLOAT_MAX)', values)), 17)
        self.assertIn('lod < 17U', self.runtime)


if __name__ == '__main__':
    unittest.main()
