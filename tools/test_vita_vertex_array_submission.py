"""Prove vertex-array-v1 submits the same corners as the immediate mesh path.

Compiles the production per-frame pass loop of Submit_Mesh_Internal and the
production Vertex_Array_Batch_Eligible / Draw_Vertex_Array_Batch against a GL
shim, runs each fixture with vertex arrays off (immediate and indexed
immediate) and on, and requires byte-identical expanded corner streams, state
call sequences, current attributes and colour evaluations. Mutations of the
production text that break equivalence must make the harness fail.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp'
HARNESS = ROOT / 'tools/vita_vertex_array_submission_test.cpp'


def extract_function(source, signature):
    """One top-level definition, from its signature to its closing brace."""
    start = source.index(signature)
    return source[start:source.index('\n}\n', start) + 3]


def production_text():
    source = RENDERER.read_text()
    helpers = '\n'.join(extract_function(source, signature) for signature in (
        'static bool Vertex_Array_Batch_Eligible(',
        'static void Draw_Vertex_Array_Batch('))
    submit = source.index('static void Submit_Mesh_Internal(')
    anchor = source.index('Submit_Static_Mesh_Cache(mesh, model, render_info', submit)
    start = source.index('\tfor (int pass = 0; pass < draw_pass_count; ++pass) {', anchor)
    end = source.index('\n\tDisable_Texture_Stage(1U);\n\tApply_Original_Texture_Coordinate_State(NULL);',
                       start)
    return helpers, source[start:end]


def build_and_run(folder, helpers, loop, sanitize):
    p = Path(folder)
    (p / 'vertex-array-helpers.inc').write_text(helpers)
    (p / 'pass-loop-production.inc').write_text(loop)
    flags = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'] \
        if sanitize else ['-O0']
    subprocess.run(['g++', '-std=c++17', *flags, '-Wall', '-Wextra', '-Werror',
                    '-Wno-unused-parameter', '-Wno-unused-variable',
                    '-Wno-unused-but-set-variable',
                    '-I' + folder, '-I' + str(ROOT / 'port/renderer/vita'),
                    str(HARNESS), '-o', str(p / 'test')], check=True)
    env = dict(os.environ, UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    return subprocess.run([str(p / 'test')], env=env, capture_output=True, text=True)


# (description, old, new): each must break byte equivalence or a vitaGL contract.
MUTATIONS = (
    ('current colour not restored after the array draw',
     '\t\tglColor4f(color[0], color[1], color[2], color[3]);\n', '\n'),
    ('current stage-0 coordinate not restored after the array draw',
     '\t\tif (texture0) glMultiTexCoord2f(GL_TEXTURE0,', '\t\tif (false) glMultiTexCoord2f(GL_TEXTURE0,'),
    ('textured-skin white RGB rule dropped',
     'const Vector3 final_color = batch_skin_color_passthrough ?\n\t\t\t\tVector3(1.0f, 1.0f, 1.0f) : vertex_color.final_color;',
     'const Vector3 final_color = vertex_color.final_color;'),
    ('pass-through colour argument not forwarded',
     'normals, original_world_transform, render_info, light_directions,\n\t\t\t\tbatch_skin_color_passthrough);',
     'normals, original_world_transform, render_info, light_directions,\n\t\t\t\tfalse);'),
    ('detail stage reads stage-0 coordinates',
     'float *uv = g_vertex_array_batch.Uv1(slot);\n\t\t\t\tuv[0] = detail_uvs[vertex_index].X;',
     'float *uv = g_vertex_array_batch.Uv1(slot);\n\t\t\t\tuv[0] = current_uvs[0][vertex_index].X;'),
    ('texture-unit enable check removed',
     'if (!unit.enabled_known || unit.enabled != active[stage]) return false;',
     'if (!unit.enabled_known) return false;'),
    ('generated/transformed coordinates admitted',
     "if (active[stage] ? Texture_Coordinate_Mode(states[stage]) != D3DTSS_TCI_PASSTHRU ||\n\t\t\t\tflags != D3DTTFF_DISABLE :",
     "if (active[stage] ? false :"),
    ('attribute invalidation after the array draw removed',
     '\t\t// Later immediate draws must re-patch for their own layout.\n\t\tvglRenegadeInvalidateVertexAttributes();\n',
     '\n'),
    ('pending material-lighting breadcrumb ignored',
     'array_batch = array_pass && g_logged_first_material_lighting &&',
     'array_batch = array_pass &&'),
)


class VertexArraySubmissionTests(unittest.TestCase):
    def test_array_batches_match_immediate_corner_stream(self):
        helpers, loop = production_text()
        self.assertIn('array_append(vertex_indices[corner])', loop)
        self.assertIn('Draw_Vertex_Array_Batch(g_vertex_array_batch', loop)
        with tempfile.TemporaryDirectory(prefix='renegade-vertex-array-') as folder:
            result = build_and_run(folder, helpers, loop, sanitize=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('runs compared', result.stdout)

    def test_mutations_are_detected(self):
        helpers, loop = production_text()
        for description, old, new in MUTATIONS:
            with self.subTest(description):
                in_helpers = old in helpers
                self.assertTrue(in_helpers or old in loop, description)
                mutated_helpers = helpers.replace(old, new, 1) if in_helpers else helpers
                mutated_loop = loop if in_helpers else loop.replace(old, new, 1)
                with tempfile.TemporaryDirectory(prefix='renegade-vertex-array-mut-') as folder:
                    result = build_and_run(folder, mutated_helpers, mutated_loop, sanitize=False)
                self.assertNotEqual(result.returncode, 0,
                                    'mutation survived: ' + description + '\n' + result.stdout)

    def test_flag_contract(self):
        source = RENDERER.read_text()
        reader = extract_function(source, 'void Read_Vertex_Array_Mode(')
        self.assertIn('ux0:data/renegade/user/config/vertex-array-v1.flag', reader)
        self.assertIn('"RVVA1 "', reader)
        self.assertIn('Read_Vertex_Array_Mode();', source)
        self.assertRegex(source, r'#define RENEGADE_VITA_VERTEX_ARRAY_DEFAULT [01]\n')
        # The M00 demo never reads the flag, so it stays on the immediate path.
        self.assertIn('bool g_vertex_array_enabled = false;', source)


if __name__ == '__main__':
    unittest.main()
