"""Isolated production restore body with injected GL failures; no GPU/play test."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RestoreTests(unittest.TestCase):
    def test_prior_error_and_bind_failure_are_distinct(self):
        source = (ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp').read_text()
        start = source.index('bool Restore_Default_Render_Target()')
        body = source[start:source.index('\n}\n', start) + 3]
        harness = r'''
#include <cassert>
#define __vita__ 1
enum { GL_NO_ERROR=0, GL_FRAMEBUFFER=1, GL_CCW=2 };
struct { unsigned backend_errors=0; } g_statistics;
unsigned g_active_render_target_width=64, g_active_render_target_height=32;
int errors[2], error_index=0, invalidations=0, front_faces=0, binds=0;
void Opaque_Sort_Barrier() {}
int glGetError() { return errors[error_index++]; }
void glBindFramebuffer(int, unsigned) { ++binds; }
void glFrontFace(int) { ++front_faces; }
void Invalidate_Native_State_Cache() { ++invalidations; }
'''
        harness += body + r'''
int main() {
    errors[0]=9; errors[1]=0;
    assert(Restore_Default_Render_Target());
    assert(g_statistics.backend_errors==1 && binds==1 && front_faces==1);
    assert(g_active_render_target_width==0 && g_active_render_target_height==0);
    assert(invalidations==1);
    error_index=0; errors[0]=0; errors[1]=9;
    g_active_render_target_width=64; g_active_render_target_height=32;
    assert(!Restore_Default_Render_Target());
    assert(g_active_render_target_width==64 && g_active_render_target_height==32);
    assert(invalidations==1 && front_faces==1 && g_statistics.backend_errors==2);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            cpp = Path(directory) / 'restore.cpp'
            cpp.write_text(harness)
            exe = Path(directory) / 'restore'
            subprocess.run(['g++', '-fsanitize=address,undefined', str(cpp), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
