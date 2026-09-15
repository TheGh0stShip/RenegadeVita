from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TutorialHelpTests(unittest.TestCase):
    def test_platform_hints_and_translation_fallback(self):
        program = r'''
#include "renegade_vita_tutorial_help.h"
#include <cassert>
#include <cstring>
int main() {
    const int weapons[] = {8275, 8276, 8380, 8382, 8383, 8384};
    for (int id : weapons) {
        const char *text = Renegade_Vita_Tutorial_Help(id, 0);
        assert(text && std::strstr(text, "D-pad Left/Right"));
        assert(!Renegade_Vita_Tutorial_Help(id, 1));
    }
    assert(std::strstr(Renegade_Vita_Tutorial_Help(8372, 0), "Circle"));
    assert(std::strstr(Renegade_Vita_Tutorial_Help(8374, 0), "Cross"));
    for (int id : {8373, 8375, 8287, 8290})
        assert(std::strstr(Renegade_Vita_Tutorial_Help(id, 0), "Triangle"));
    assert(std::strstr(Renegade_Vita_Tutorial_Help(8272, 0), "Start: EVA"));
    const char *ladder = Renegade_Vita_Tutorial_Help(IDS_MTUDSGN_DSGN0049I1GCLS_TXT, 0);
    assert(ladder && std::strstr(ladder, "climb a ladder") && std::strstr(ladder, "Triangle"));
    assert(!std::strstr(ladder, "keyboard") && !std::strstr(ladder, "Action key"));
    assert(std::strstr(Renegade_Vita_Tutorial_Help(IDS_MTUDSGN_DSGN0050I1GCLS_TXT, 0), "left stick"));
    assert(std::strstr(Renegade_Vita_Tutorial_Help(IDS_MTUDSGN_DSGN0060I1GCLS_TXT, 0), "Start"));
    assert(!Renegade_Vita_Tutorial_Help(IDS_MTUDSGN_DSGN0049I1GCLS_TXT, 1));
    for (int id : {0, -1, 8376, 8381, 999999})
        assert(!Renegade_Vita_Tutorial_Help(id, 0));
}
'''
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "test.cpp"
            exe = Path(folder) / "test"
            source.write_text(program)
            built = subprocess.run(["g++", "-std=c++11", "-include", "initializer_list",
                "-I", str(ROOT / "port/platform"), "-I", str(ROOT / "staging/combat"),
                str(source), "-o", str(exe)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    unittest.main()
