"""Packed immediate records for DX8-boundary indexed draws match per-vertex calls.

1. The production Submit_Indexed_Triangles emission slice, run through a GL
   sink, gives the same unlit vertex stream, batches and post-draw current
   attributes with records, without them, and when vitaGL refuses a run.
2. The patched pinned vitaGL vglRenegadeImmediateVertices fills the immediate
   pool exactly as glColor4ub/glColor4f, glNormal3f, glMultiTexCoord2f and
   glVertex3f do, for the untextured, single and multitexture layouts.
3. Production Record_Indexed_Texture_Coordinate returns the (s, t) that
   Emit_Indexed_Texture_Coordinate passes to GL for every mode and flag.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VITA = ROOT / 'port/renderer/vita'


def _section(source, start, end):
    offset = source.index(start)
    return source[offset:source.index(end, offset)]


def _tarball():
    candidates = [os.environ.get('RENEGADE_VITAGL_SOURCE_TARBALL', ''),
                  str(ROOT / 'build/deps/vitagl-demo/source.tar.gz')]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def _ordered_vitagl_patches():
    script = (ROOT / 'tools/build_vitagl_demo.sh').read_text()
    variables = dict(re.findall(
        r'^(\w+_patch)="\$root/(port/renderer/vita/dependency-patches/[\w.-]+\.patch)"$',
        script, re.M))
    order = re.findall(r'^patch --batch --fuzz=0 --no-backup-if-mismatch '
                       r'-d "\$work/source" -p1 < "\$(\w+_patch)"$', script, re.M)
    return script, variables, order


class IndexedVertexRecordsTest(unittest.TestCase):
    def test_build_script_applies_records_patch_last(self):
        script, variables, order = _ordered_vitagl_patches()
        self.assertEqual(variables.get('records_patch'),
                         'port/renderer/vita/dependency-patches/vitagl-immediate-vertex-records.patch')
        self.assertEqual(order[-1], 'records_patch')
        self.assertEqual(sorted(order), sorted(variables))
        identity = next(line for line in script.splitlines() if line.startswith('identity='))
        self.assertIn('"$records_patch"', identity)
        self.assertIn('"$attribute_patch" "$records_patch" "$work/source/source/ffp.c"', script)

    def test_production_indexed_records_stream(self):
        source = (VITA / 'ww3d_vita_renderer.cpp').read_text()
        start = source.index('\tconst uint32_t diffuse_offset = category_layout.diffuse_offset;',
                             source.index('OriginalTextureCoordinateState texture_coordinates[MAX_TEXTURE_STAGES]'))
        end = source.index('\n\tconst uint32_t emitted_triangles', start)
        with tempfile.TemporaryDirectory(prefix='renegade-records-') as folder:
            path = Path(folder)
            (path / 'indexed-production.inc').write_text(source[start:end])
            for name, flags in [('plain', ['-O2']),
                                ('sanitized', ['-O1', '-g', '-fsanitize=address,undefined',
                                               '-fno-omit-frame-pointer'])]:
                subprocess.run(['g++', '-std=c++17', *flags, '-Wall', '-Wextra', '-Werror',
                                '-Wno-unused-variable', '-Wno-unused-function',
                                '-DGENERIC_INDEXED_ONLY', '-I' + folder, '-I' + str(VITA),
                                str(ROOT / 'tools/vita_mesh_batch_test.cpp'),
                                '-o', str(path / name)], check=True)
                result = subprocess.run([str(path / name)], check=True,
                                        capture_output=True, text=True)
                self.assertIn('production generic indexed equivalence PASS', result.stdout)
                self.assertNotIn('record_runs=0', result.stdout)

    def test_vitagl_records_and_coordinates(self):
        tarball = _tarball()
        if tarball is None:
            self.skipTest('pinned vitaGL source.tar.gz unavailable '
                          '(set RENEGADE_VITAGL_SOURCE_TARBALL)')
        _, variables, order = _ordered_vitagl_patches()
        renderer = (VITA / 'ww3d_vita_renderer.cpp').read_text()
        with tempfile.TemporaryDirectory(prefix='renegade-vitagl-records-') as folder:
            path = Path(folder)
            subprocess.run(['tar', '-xzf', str(tarball), '--strip-components=1', '-C', folder],
                           check=True)
            for name in order:
                subprocess.run(['patch', '--batch', '--fuzz=0', '--no-backup-if-mismatch',
                                '-p1', '-i', str(ROOT / variables[name])],
                               cwd=path, check=True, capture_output=True)
            ffp = (path / 'source/ffp.c').read_text()
            (path / 'vitagl.inc').write_text('\n'.join(_section(ffp, start, end) for start, end in [
                ('inline void glVertex3f(', 'void glClientActiveTexture('),
                ('void glColor4f(', 'void glColor4fv('),
                ('void glColor4ub(', 'void glColor4us('),
                ('void glNormal3f(', 'void glNormal3s('),
                ('void glMultiTexCoord2f(', 'void glMultiTexCoord2fv('),
                ('GLboolean vglRenegadeImmediateVertices(', 'void glTexEnvfv(')]))
            (path / 'coords.inc').write_text('\n'.join(_section(renderer, start, end) for start, end in [
                ('DWORD Texture_Coordinate_Mode(', 'const Vector2 *Resolve_UV_Array_For_Texture_State('),
                ('void Apply_DX8_Texture_Transform(', 'void Begin_Texture_Coordinate_Primitive('),
                ('const float *Select_Indexed_UV_Array(', 'void Apply_Original_Shader_State(')]))
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            '-I' + folder, '-I' + str(VITA),
                            str(ROOT / 'tools/vitagl_immediate_records_test.cpp'),
                            '-o', str(path / 'records')], check=True)
            result = subprocess.run([str(path / 'records')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('vitaGL immediate records stream equivalence PASS layouts=3', result.stdout)
            self.assertIn('production record/emit texture coordinate equivalence PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
