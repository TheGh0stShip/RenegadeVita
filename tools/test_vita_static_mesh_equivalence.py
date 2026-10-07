"""Prove the static mesh cache builder reproduces the immediate mesh pass loop.

Compiles the production Build_Static_Mesh_Streams (with its snapshot and
pass-through helpers) and the production Submit_Mesh immediate pass loop
against host mocks, then compares the expanded cached streams, an independent
walk of each fixture, and the recorded immediate stream corner by corner.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp'


def extract(source, start_marker, end_marker, anchor=0):
    start = source.index(start_marker, anchor)
    return source[start:source.index(end_marker, start)]


def extract_function(source, signature):
    """One top-level definition, from its signature to its closing brace."""
    start = source.index(signature)
    return source[start:source.index('\n}\n', start) + 3]


class StaticMeshEquivalenceTests(unittest.TestCase):
    def test_cached_streams_match_immediate_pass_loop(self):
        source = RENDERER.read_text()
        build = extract(source, 'bool Build_Static_Mesh_Streams(',
                        'StaticMeshRebuildReason Static_Mesh_Entry_Current(')
        # Extracted one by one so unrelated neighbours (the per-frame lighting
        # signature capture) stay out of this builder-only harness.
        helpers = '\n'.join(extract_function(source, signature) for signature in (
            'StaticMeshMaterialSnapshot Snapshot_Static_Mesh_Material(',
            'bool Static_Mesh_Passthrough_Stage('))
        # The Vita immediate pass loop of Submit_Mesh_Internal (after the
        # host-only loop and the transform setup).
        immediate = extract(source, '\tfor (int pass = 0; pass < draw_pass_count;',
                            '\n\tDisable_Texture_Stage(1U);',
                            source.index('const Matrix4 world_transform',
                                         source.index('static void Submit_Mesh_Internal(')))
        self.assertNotIn('Capture_Static_Mesh_Lighting', helpers)
        self.assertIn('Evaluate_Original_Material_Vertex_Color(', build)
        self.assertIn('bool &uses_lighting', build)
        self.assertIn('Evaluate_Material_Vertex_Color(', immediate)
        with tempfile.TemporaryDirectory(prefix='renegade-static-mesh-equivalence-') as folder:
            p = Path(folder)
            (p / 'static-mesh-helpers.inc').write_text(helpers)
            (p / 'static-mesh-build.inc').write_text(build)
            (p / 'immediate-production.inc').write_text(immediate)
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror',
                            '-I' + folder, '-I' + str(ROOT / 'port/renderer/vita'),
                            str(ROOT / 'tools/vita_static_mesh_equivalence_test.cpp'),
                            '-o', str(p / 'test')], check=True)
            # Undefined behaviour fails the run instead of only printing.
            env = dict(os.environ, UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            subprocess.run([str(p / 'test')], check=True, env=env)


if __name__ == '__main__':
    unittest.main()
