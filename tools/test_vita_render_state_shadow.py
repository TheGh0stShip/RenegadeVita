"""The renderer's GL-state shadow must leave vitaGL in exactly the state the
unshadowed call sequence produces, while issuing fewer calls.

The real shadow block, Reset_Texture_Matrix_Stage, the DX8 translators and the
Apply_DX8_Render_State switch are extracted from ww3d_vita_renderer.cpp and
compiled twice (shadow on / off) over a GL shim; randomized call sequences that
follow the renderer's protocol run in lockstep (tools/vita_render_state_shadow_test.cpp).
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp'
BOUNDARY = ROOT / 'port/renderer/vita/ww3d_dx8_boundary.cpp'
HARNESS = ROOT / 'tools/vita_render_state_shadow_test.cpp'

RAW_STATE_CALL = re.compile(
    r'\bgl(BlendFunc|AlphaFunc|DepthFunc|DepthMask|ColorMask|CullFace|PolygonOffset|'
    r'PolygonMode|LoadMatrixf|LoadIdentity)\(|'
    r'\bgl(Enable|Disable)\(GL_(BLEND|ALPHA_TEST|CULL_FACE|POLYGON_OFFSET_FILL)\)')


def function_body(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise ValueError(signature)


def shadow_block(source):
    start = source.index('// Exact GL-level shadow of the fixed-function raster state')
    end = source.index('void Invalidate_Native_State_Cache()')
    return source[start:end]


def extract(source):
    translators = '\n'.join(function_body(source, signature) for signature in (
        'GLenum To_GL_DX8_Compare(uint32_t function)',
        'GLenum To_GL_DX8_Blend(uint32_t function)',
        'GLenum To_GL_DX8_Fill_Mode(uint32_t mode)'))
    apply_state = function_body(source, 'bool Apply_DX8_Render_State(uint32_t state, uint32_t value)')
    switch_start = apply_state.index('\tswitch (state) {')
    switch_end = apply_state.index('\n\tif (!handled) {')
    return {
        'shadow_block.inc': shadow_block(source),
        'reset_texture_matrix_stage.inc': function_body(source, 'void Reset_Texture_Matrix_Stage(unsigned stage)'),
        'dx8_translators.inc': translators,
        'dx8_render_state_switch.inc': apply_state[switch_start:switch_end],
    }


class VitaRenderStateShadowTests(unittest.TestCase):
    def build_and_run(self, flags, sequences, length):
        source = RENDERER.read_text()
        with tempfile.TemporaryDirectory(prefix='renegade-render-state-shadow-') as folder:
            folder = Path(folder)
            for name, text in extract(source).items():
                (folder / name).write_text(text)
            binary = folder / 'test'
            subprocess.run(['g++', '-std=c++17', *flags, '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-function', '-I' + str(folder), '-I' + str(ROOT / 'tools'),
                            str(HARNESS), '-o', str(binary)], check=True)
            completed = subprocess.run(
                [str(binary), str(sequences), str(length)], check=True, capture_output=True,
                text=True, timeout=600,
                env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1',
                     'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'})
        self.assertIn('render state shadow PASS sequences=%d length=%d' % (sequences, length),
                      completed.stdout)
        self.assertIn('render state shadow negative control PASS', completed.stdout)
        print(completed.stdout.strip())

    def test_sanitized_equivalence(self):
        self.build_and_run(['-O1', '-g', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer'], 600, 400)

    def test_optimized_equivalence(self):
        self.build_and_run(['-O3', '-fno-math-errno', '-fno-trapping-math'], 3000, 600)

    def test_per_batch_paths_use_the_shadow(self):
        source = RENDERER.read_text()
        block = shadow_block(source)
        outside = source.replace(block, '')
        # Raw raster/transform calls outside the shadow are confined to paths
        # that invalidate the shadow (initialization and reactivation) and the
        # texture-matrix reset, whose identity load is the shadowed one.
        allowed = {
            'bool Reactivate_Native_Backend_State()': 'Invalidate_GL_State_Shadow();',
            'bool Initialize()': 'Invalidate_Native_State_Cache();',
        }
        allowed_spans = []
        for signature, invalidation in allowed.items():
            body = function_body(outside, signature)
            first_raw = RAW_STATE_CALL.search(body)
            self.assertIsNotNone(first_raw, signature)
            self.assertLess(body.index(invalidation), first_raw.start(), signature)
            start = outside.index(body)
            allowed_spans.append((start, start + len(body)))
        for match in RAW_STATE_CALL.finditer(outside):
            self.assertTrue(any(start <= match.start() < end for start, end in allowed_spans),
                            'raw GL state call bypasses the shadow: ' +
                            outside[max(0, match.start() - 120):match.end() + 40])
        for signature in ('void Apply_Original_Shader_State(const ShaderClass &shader)',
                          'bool Apply_DX8_Render_State(uint32_t state, uint32_t value)',
                          'void Begin_Frame(bool clear_color, bool clear_depth, float red, float green,',
                          'IndexedSubmissionResult Submit_Indexed_Triangles('):
            self.assertIsNone(RAW_STATE_CALL.search(function_body(source, signature)), signature)
        indexed = function_body(source, 'IndexedSubmissionResult Submit_Indexed_Triangles(')
        self.assertIn('Shadow_Load_Transforms(transform_matrices.projection, transform_matrices.modelview);', indexed)
        self.assertIn('Release_Submission_Transforms();', indexed)
        mesh = source[source.index('static void Submit_Mesh_Internal('):source.index('void Submit_Mesh(MeshClass &mesh')]
        self.assertIn('Shadow_Load_Transforms(transform_matrices.projection, transform_matrices.modelview);', mesh)
        self.assertIn('Release_Submission_Transforms();', mesh)
        self.assertIn('Shadow_Load_Transforms(NULL, NULL);',
                      function_body(source, 'void Begin_Frame(bool clear_color, bool clear_depth, float red, float green,'))
        # Invalidation points and the runtime switch/telemetry.
        self.assertIn('Invalidate_GL_State_Shadow();', function_body(source, 'void Invalidate_Native_State_Cache()'))
        apply_state = function_body(source, 'bool Apply_DX8_Render_State(uint32_t state, uint32_t value)')
        error_path = apply_state[apply_state.index('const GLenum error = glGetError();'):]
        self.assertIn('Invalidate_GL_State_Shadow();', error_path[:error_path.index('return false;')])
        initialize = function_body(source, 'bool Initialize()')
        self.assertLess(initialize.index('Read_GL_State_Shadow_Mode();'),
                        initialize.index('Invalidate_Native_State_Cache();'))
        self.assertIn('Log_GL_State_Shadow_Window(g_statistics.frames);', function_body(source, 'void End_Frame(bool present)'))
        self.assertIn('gl-state-shadow-v1.flag', block)
        self.assertIn('"RVGS1 "', block)

    def test_boundary_texture_matrix_load_invalidates_identity_shadow(self):
        boundary = BOUNDARY.read_text()
        transform = function_body(boundary, 'bool Apply_Texture_Stage_Transform(DWORD stage)')
        load = transform.index('glLoadMatrixf(&transform.m[0][0]);')
        hook = transform.index('RenegadeVitaRenderer::Invalidate_Texture_Matrix_Shadow(stage);')
        self.assertLess(load, hook)
        self.assertLess(hook, transform.index('glGetError()'))
        # Only the boundary and the renderer load GL_TEXTURE matrices.
        for path in (ROOT / 'port').rglob('*.cpp'):
            if path in (RENDERER, BOUNDARY):
                continue
            self.assertNotIn('glMatrixMode(GL_TEXTURE)', path.read_text(errors='replace'), str(path))


if __name__ == '__main__':
    unittest.main()
