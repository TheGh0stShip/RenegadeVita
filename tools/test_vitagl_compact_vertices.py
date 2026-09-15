"""Exercise patched pinned vitaGL emit/draw bodies with a recording GXM sink."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VitaGLCompactVerticesTest(unittest.TestCase):
    def test_original_and_compact_vertex_streams(self):
        with tempfile.TemporaryDirectory(prefix='renegade-vitagl-') as folder:
            directory = Path(folder)
            subprocess.run(['tar', '-xzf', str(ROOT / 'build/deps/vitagl-demo/source.tar.gz'),
                            '--strip-components=1', '-C', folder], check=True)
            pristine = (directory / 'source/ffp.c').read_text()
            subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i', str(ROOT /
                'port/renderer/vita/dependency-patches/vitagl-compact-unlit.patch')],
                cwd=directory, check=True, capture_output=True)
            patched = (directory / 'source/ffp.c').read_text()
            subprocess.run(['patch', '--batch', '--fuzz=0', '-p1', '-i', str(ROOT /
                'port/renderer/vita/dependency-patches/vitagl-indexed-immediate.patch')],
                cwd=directory, check=True, capture_output=True)
            indexed = (directory / 'source/ffp.c').read_text()
            for variant, source in [('baseline', pristine), ('compact', patched),
                                    ('indexed', indexed)]:
                parts = []
                for start, end in [('inline void glVertex3f(', 'void glClientActiveTexture('),
                                   ('static const uint16_t *renegade_immediate_indices' if variant == 'indexed'
                                    else 'void glEnd(void)', 'void glTexEnvfv(')]:
                    offset = source.index(start)
                    parts.append(source[offset:source.index(end, offset)])
                (directory / 'production.inc').write_text('\n'.join(parts))
                subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra',
                    '-Werror', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-DCOMPACT=' + ('0' if variant == 'baseline' else '1'),
                    '-DINDEXED=' + ('1' if variant == 'indexed' else '0'),
                    '-I'+str(ROOT / 'port/renderer/vita'), '-I'+folder,
                    str(ROOT / 'tools/vitagl_compact_vertices_test.cpp'),
                    '-o', str(directory / variant)], check=True)
                subprocess.run([str(directory / variant)], check=True)


if __name__ == '__main__':
    unittest.main()
