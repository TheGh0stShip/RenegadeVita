"""Compare production per-pass material reuse with its uncached evaluator."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MaterialCacheTests(unittest.TestCase):
    def test_production_material_equivalence(self):
        source = (ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp').read_text()
        def section(start, end):
            offset = source.index(start)
            return source[offset:source.index(end, offset)]
        with tempfile.TemporaryDirectory(prefix='renegade-material-') as temporary:
            directory = Path(temporary)
            (directory / 'material-production.inc').write_text('\n'.join([
                section('Vector3 Normalize_Or_Default(', 'Vector3 Compute_Camera_Space_Position('),
                section('Vector3 Compute_World_Space_Normal(', 'Vector3 Compute_Camera_Space_Reflection('),
                section('float Clamp01(', 'void Log_System_Memory(')]))
            command = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                       '-I' + temporary, str(ROOT / 'tools/vita_material_cache_test.cpp'),
                       '-o', str(directory / 'material')]
            if os.environ.get('RENEGADE_MATERIAL_SANITIZE') == '1':
                command[2:3] = ['-O1', '-g', '-fsanitize=address,undefined',
                                '-fno-omit-frame-pointer']
            subprocess.run(command, check=True)
            result = subprocess.run([str(directory / 'material')], check=True,
                                    capture_output=True, text=True)
            self.assertIn('material equivalence PASS', result.stdout)
            print(result.stdout, end='')


if __name__ == '__main__':
    unittest.main()
