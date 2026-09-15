"""Check actual renderer diagnostic guards without a GPU or full build."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DiagnosticHotpathTests(unittest.TestCase):
    def test_latched_diagnostics_do_not_scan_each_vertex_texture(self):
        source = (ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp").read_text()
        guards = re.findall(r'if \((!g_logged_first_passthrough_texture_v_preserved\s*&&[\s\S]*?)\) \{', source)
        self.assertEqual(len(guards), 2)  # mesh and indexed paths
        for guard in guards:
            program = r'''
#include <cstring>
#include <cassert>
static unsigned scans;
bool Has_Loadscreen_Texture_Prefix(const char *name) {
    ++scans;
    return name && std::strncmp(name, "loadscreen_", 11) == 0;
}
int main() {
    const unsigned D3DTSS_TCI_PASSTHRU = 0;
    const char *names[] = {nullptr, "weapon.dds", "loadscreen_m00.dds"};
    for (bool logged : {false, true}) {
        for (unsigned mode : {0U, 1U}) {
            for (const char *texture_name : names) {
                bool g_logged_first_passthrough_texture_v_preserved = logged;
                scans = 0;
                const bool actual = GUARD;
                const bool expected = !logged && mode == 0 &&
                    (!texture_name || std::strncmp(texture_name, "loadscreen_", 11) != 0);
                assert(actual == expected);
                assert(scans == ((!logged && mode == 0) ? 1U : 0U));
            }
        }
    }
    bool g_logged_first_passthrough_texture_v_preserved = true;
    unsigned mode = 0;
    const char *texture_name = "weapon.dds";
    scans = 0;
    for (unsigned vertex = 0; vertex != 1000000; ++vertex) {
        assert(!(GUARD));
    }
    assert(scans == 0);
}
'''.replace("GUARD", guard)
            with tempfile.TemporaryDirectory(prefix="diagnostic-hotpath-") as folder:
                main = Path(folder) / "main.cpp"
                exe = Path(folder) / "probe"
                main.write_text(program)
                built = subprocess.run(["g++", "-std=c++17", "-O1", "-include", "initializer_list",
                                        str(main), "-o", str(exe)], capture_output=True, text=True, timeout=60)
                self.assertEqual(built.returncode, 0, built.stderr)
                subprocess.run([str(exe)], check=True, timeout=5)

    def test_targa_layout_cannot_follow_upstream_include_order(self):
        compat = ROOT / "port/compatibility/include"
        upstream = ROOT / "upstream/CnC_Renegade/Code"
        program = '#include "targa.h"\nstatic_assert(sizeof(TGA2Extension) == 495);\n'
        with tempfile.TemporaryDirectory(prefix="targa-layout-") as folder:
            main = Path(folder) / "layout.cpp"
            main.write_text(program)
            command = ["g++", "-std=c++17", "-fsyntax-only", "-D_UNIX=1", "-DNDEBUG=1",
                       "-DRENEGADE_HOST_ABI_TEST=1", "-DRENEGADE_VITA_PORT=1",
                       "-include", str(compat / "msvc_compat.h")]
            # Deliberately prefer pristine upstream headers: the forwarding
            # compatibility header must still select the patched disk layout.
            for directory in [compat, upstream / "wwlib", ROOT / "staging/wwlib",
                              upstream / "wwdebug", upstream / "WWMath"]:
                command.extend(["-I", str(directory)])
            checked = subprocess.run(command + [str(main)], capture_output=True, text=True, timeout=60)
            self.assertEqual(checked.returncode, 0, checked.stderr)


if __name__ == "__main__":
    unittest.main()
