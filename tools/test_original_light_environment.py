"""Keep the shared light-state method aligned with its original engine owner."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OriginalLightEnvironmentTest(unittest.TestCase):
    def test_original_method_with_only_standard_for_scope_fix(self):
        source = (ROOT / 'staging/ww3d2/dx8wrapper.cpp').read_text()
        start = source.index('void DX8Wrapper::Set_Light_Environment(')
        original = source[start:source.index('IDirect3DSurface8 * DX8Wrapper::_Get_DX8_Front_Buffer()', start)]
        native = (ROOT / 'port/renderer/vita/original_dx8_light_environment.inc').read_text()

        def tokens(text):
            text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
            return re.sub(r'\s+', '', text)

        expected = tokens(original).replace('for(intl=0;', 'intl;for(l=0;')
        self.assertEqual(expected, tokens(native))

    def test_full_native_and_host_use_same_owner(self):
        for path in ('port/platform/a31_gameplay_boundary.cpp',
                     'tools/host_a30_definitions/wwphys_definition_dx8_boundary.cpp'):
            source = (ROOT / path).read_text()
            self.assertIn('#include "original_dx8_light_environment.inc"', source)
            self.assertNotIn('void DX8Wrapper::Set_Light_Environment(', source)


if __name__ == '__main__':
    unittest.main()
