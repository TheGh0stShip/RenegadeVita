"""Execute the production native mesh pass loop in baseline/indexed modes."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MeshBatchTests(unittest.TestCase):
    def test_production_batch_order_and_state(self):
        source = (ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp').read_text()
        start = source.index('\tfor (int pass = 0; pass < base_pass_count;',
                             source.index('const Matrix4 world_transform', source.index('void Submit_Mesh(')))
        end = source.index('\n\tDisable_Texture_Stage(1U);', start)
        with tempfile.TemporaryDirectory(prefix='renegade-mesh-batch-') as folder:
            p = Path(folder)
            (p / 'production.inc').write_text(source[start:end])
            start = source.index('\tconst uint32_t diffuse_offset = 24U;',
                                 source.index('OriginalTextureCoordinateState texture_coordinates[MAX_TEXTURE_STAGES]'))
            end = source.index('\n\tconst uint32_t emitted_triangles', start)
            (p / 'indexed-production.inc').write_text(source[start:end])
            flags = ['-O2']
            if os.environ.get('RENEGADE_MESH_SANITIZE') == '1':
                flags = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
            subprocess.run(['g++', '-std=c++17', *flags, '-Wall', '-Wextra', '-Werror',
                '-I'+folder, '-I'+str(ROOT/'port/renderer/vita'),
                str(ROOT/'tools/vita_mesh_batch_test.cpp'), '-o', str(p/'test')], check=True)
            subprocess.run([str(p/'test')], check=True)


if __name__ == '__main__':
    unittest.main()
