"""Exercise retained original DX8 frame-counter snapshots independently of GPU work."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OriginalDX8StatisticsTest(unittest.TestCase):
    def test_original_lifecycle_and_snapshots(self):
        retained = (ROOT / 'port/renderer/vita/original_dx8_statistics.inc').read_text()
        original = (ROOT / 'staging/ww3d2/dx8wrapper.cpp').read_text()
        begin = original.index('void DX8Wrapper::Reset_Statistics()')
        end = original.index('unsigned long DX8Wrapper::Get_FrameCount', begin)
        self.assertIn(original[begin:end], retained)
        counters = ['matrix_changes', 'material_changes', 'vertex_buffer_changes',
                    'index_buffer_changes', 'light_changes', 'texture_changes',
                    'render_state_changes', 'texture_stage_state_changes']
        getters = re.findall(r'unsigned DX8Wrapper::(Get_Last_Frame_\w+)\(\)', retained)
        self.assertEqual(len(getters), 9)
        prefix = '#include <cassert>\nunsigned number_of_DX8_calls;\nstruct DX8Wrapper {\n'
        prefix += ''.join('static unsigned ' + name + ';\n' for name in counters)
        prefix += 'static void Reset_Statistics(); static void Begin_Statistics(); static void End_Statistics();\n'
        prefix += ''.join('static unsigned ' + name + '();\n' for name in getters) + '};\n'
        prefix += ''.join('unsigned DX8Wrapper::' + name + ';\n' for name in counters
                          if name not in ['material_changes', 'vertex_buffer_changes', 'index_buffer_changes', 'light_changes'])
        checks = 'int main() { DX8Wrapper::Reset_Statistics();\n'
        checks += ''.join('assert(DX8Wrapper::' + name + '()==0);\n' for name in getters)
        checks += 'for(unsigned cycle=1;cycle<=3;++cycle) { DX8Wrapper::Begin_Statistics();\n'
        checks += ''.join('assert(DX8Wrapper::' + name + '==0); DX8Wrapper::' + name + '=cycle*' + str(i+1) + ';\n'
                          for i, name in enumerate(counters))
        checks += 'assert(number_of_DX8_calls==0);number_of_DX8_calls=cycle*9;DX8Wrapper::End_Statistics();\n'
        checks += ''.join('assert(DX8Wrapper::' + name + '()==cycle*' + str(i+1) + ');\n'
                          for i, name in enumerate(getters))
        checks += '} DX8Wrapper::Reset_Statistics();\n'
        checks += ''.join('assert(DX8Wrapper::' + name + '()==0);\n' for name in getters) + '}\n'
        with tempfile.TemporaryDirectory() as folder:
            cpp = Path(folder) / 'statistics.cpp'
            binary = Path(folder) / 'statistics'
            cpp.write_text(prefix + retained + checks)
            subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', str(cpp), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, env={**os.environ,
                           'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1',
                           'UBSAN_OPTIONS': 'halt_on_error=1'})


if __name__ == '__main__':
    unittest.main()
