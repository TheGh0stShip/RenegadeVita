"""Exercise production readback with distinct presented and pending buffers."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FrameCaptureSourceTests(unittest.TestCase):
    def test_presented_pending_and_failed_readback(self):
        source = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        function = source.split("bool Capture_Resolved_Frame_RGBA(", 1)[1]
        function = "bool Capture_Resolved_Frame_RGBA(" + function.split("bool Query_Backend_Memory", 1)[0]
        program = r'''
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cassert>
#define __vita__ 1
using GLenum = unsigned; using GLsizei = int;
constexpr unsigned GL_FRONT=1, GL_BACK=2, GL_RGBA=3, GL_UNSIGNED_BYTE=4, GL_NO_ERROR=0;
constexpr unsigned DISPLAY_WIDTH=2, DISPLAY_HEIGHT=1;
struct { bool initialized=true; unsigned backend_errors=0; } g_statistics;
unsigned selected=GL_BACK, error=0; bool fail=false;
unsigned reads=0;
void glReadBuffer(unsigned value) { selected=value; }
unsigned glGetError() { unsigned result=error; error=0; return result; }
void glReadPixels(int,int,int,int,unsigned,unsigned,void* out) {
    ++reads;
    if (fail) { error=99; return; }
    // The previous presentation has pixels; the new back buffer is empty.
    std::memset(out, selected == GL_FRONT ? 123 : 0, 8);
}
FUNCTION
int main() {
    uint8_t pixels[8] = {};
    assert(Capture_Resolved_Frame_RGBA(pixels, sizeof(pixels), true));
    for (auto p: pixels) assert(p == 123);
    assert(selected == GL_BACK);
    assert(Capture_Resolved_Frame_RGBA(pixels, sizeof(pixels), false));
    for (auto p: pixels) assert(p == 0);
    fail=true;
    assert(!Capture_Resolved_Frame_RGBA(pixels, sizeof(pixels), true));
    assert(selected == GL_BACK && g_statistics.backend_errors == 1);
    assert(!Capture_Resolved_Frame_RGBA(nullptr, 8, true));
    assert(!Capture_Resolved_Frame_RGBA(pixels, 7, true));
    assert(reads == 3);
    g_statistics.initialized=false;
    assert(!Capture_Resolved_Frame_RGBA(pixels, 8, true));
    assert(reads==3 && selected==GL_BACK);
}
'''.replace("FUNCTION", function)
        with tempfile.TemporaryDirectory(prefix="frame-source-") as directory:
            main, exe = Path(directory) / "main.cpp", Path(directory) / "probe"
            main.write_text(program)
            subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                            str(main), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    unittest.main()
