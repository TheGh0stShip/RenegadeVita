"""Execute original DX8 readiness accessors and the native lifecycle query."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TextReadinessTests(unittest.TestCase):
    def test_original_row_iteration_terminates_without_renderer(self):
        source = (ROOT / 'staging/ww3d2/render2dsentence.cpp').read_text()
        begin = source.index('const WCHAR *\nRender2DSentenceClass::Find_Row_Start(')
        end = source.index('\n////////////////////////////////////////////////////////////////////////////////////', begin)
        production = source[begin:end]
        program = r'''
#include <cassert>
#include <algorithm>
using WCHAR = char16_t;
using std::max;
#define IS_BREAK_CHAR(c) ((c) == u' ')
struct DX8Wrapper { static bool ready; static bool Is_Initted() { return ready; } };
bool DX8Wrapper::ready = false;
struct FontType { float Get_Char_Height() { return 12; } float Get_Char_Spacing(WCHAR) { return 5; } };
struct Render2DSentenceClass {
 FontType *Font; float WrapWidth;
 const WCHAR *Find_Row_Start(const WCHAR *, int);
};
''' + production + r'''
int main() {
 FontType font; Render2DSentenceClass text{&font, 26};
 const WCHAR *source = u"one two three";
 assert(text.Find_Row_Start(source, 0) == source);
 assert(text.Find_Row_Start(source, 1) == nullptr);
 DX8Wrapper::ready = true;
 assert(text.Find_Row_Start(source, 1) == source + 4);
 assert(text.Find_Row_Start(source, 2) == source + 8);
 assert(text.Find_Row_Start(source, 3) == nullptr);
 DX8Wrapper::ready = false;
 assert(text.Find_Row_Start(source + 4, 1) == nullptr);
}
'''
        with tempfile.TemporaryDirectory(prefix='renegade-row-ready-') as folder:
            cpp = Path(folder)/'test.cpp'
            cpp.write_text(program)
            executable = Path(folder)/'test'
            subprocess.run(['g++', '-std=c++17', '-O1', '-g',
                '-fsanitize=address,undefined', str(cpp), '-o', str(executable)], check=True)
            subprocess.run([str(executable)], check=True)

    @classmethod
    def setUpClass(cls):
        header = (ROOT / "staging/ww3d2/dx8wrapper.h").read_text()
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text()
        begin = header.index("#if defined(__vita__) && defined(RENEGADE_VITA_PORT)\n\tstatic bool Is_Device_Lost")
        cls.accessors = header[begin:header.index("#endif", begin) + len("#endif")]
        begin = boundary.index("bool DX8Wrapper::Is_Native_Device_Ready()")
        cls.query = boundary[begin:boundary.index("#endif", begin)]

    def run_variant(self, native):
        prefix = r'''
#include <cassert>
namespace RenegadeVitaRenderer {
struct Statistics { bool initialized; } state = {};
const Statistics &Get_Statistics() { return state; }
}
void Vita_Append_A22_Runtime_Breadcrumb(const char *, const char *, ...) {}
class DX8Wrapper {
public:
static bool IsInitted, IsDeviceLost;
'''
        source = prefix + self.accessors + r'''
};
bool DX8Wrapper::IsInitted = false;
bool DX8Wrapper::IsDeviceLost = false;
#if defined(__vita__) && defined(RENEGADE_VITA_PORT)
''' + self.query + r'''
#endif
int main() {
    assert(!DX8Wrapper::Is_Initted());
#if defined(__vita__)
    assert(DX8Wrapper::Is_Device_Lost());
    RenegadeVitaRenderer::state.initialized = true;
    assert(!DX8Wrapper::IsInitted); // Original lite initialization stays intact.
    assert(DX8Wrapper::Is_Initted());
    assert(!DX8Wrapper::Is_Device_Lost());
    DX8Wrapper::IsDeviceLost = true;
    assert(DX8Wrapper::Is_Initted() && DX8Wrapper::Is_Device_Lost());
    DX8Wrapper::IsDeviceLost = false;
    RenegadeVitaRenderer::state.initialized = false;
    assert(!DX8Wrapper::Is_Initted() && DX8Wrapper::Is_Device_Lost());
#else
    assert(!DX8Wrapper::Is_Device_Lost());
    RenegadeVitaRenderer::state.initialized = true;
    assert(!DX8Wrapper::Is_Initted()); // Desktop semantics must not change.
    DX8Wrapper::IsInitted = true;
    assert(DX8Wrapper::Is_Initted());
    DX8Wrapper::IsDeviceLost = true;
    assert(DX8Wrapper::Is_Device_Lost());
#endif
}
'''
        with tempfile.TemporaryDirectory(prefix="renegade-text-ready-") as temporary:
            cpp = Path(temporary) / "ready.cpp"
            executable = Path(temporary) / "ready"
            cpp.write_text(source, encoding="ascii")
            command = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror"]
            if native:
                command += ["-D__vita__=1", "-DRENEGADE_VITA_PORT=1"]
            subprocess.run(command + [str(cpp), "-o", str(executable)], check=True, capture_output=True)
            subprocess.run([str(executable)], check=True, capture_output=True)

    def test_native_ready_despite_original_lite_flag(self): self.run_variant(True)
    def test_desktop_lifecycle_unchanged(self): self.run_variant(False)


if __name__ == "__main__":
    unittest.main()
