"""Execute both original new-objective expressions through WideStringClass."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ObjectiveMessageAbiTests(unittest.TestCase):
    def test_new_and_unhidden_objective_text(self):
        source = (ROOT / "staging/combat/objectives.cpp").read_text()
        expressions = re.findall(r'message\.Format\( TRANSLATE \(IDS_OBJ_NEW_OBJ\)[^;]+;', source)
        self.assertEqual(len(expressions), 2)
        program = r'''
#include "widestring.h"
#include <cstring>
#define IDS_OBJ_NEW_OBJ 1
#define TRANSLATE(id) format.Peek_Buffer()
struct Objective {
    WideStringClass type;
    const WCHAR *Type_To_Name() { return type.Peek_Buffer(); }
};
int main() {
    WideStringClass format, description, message, expected;
    format.Convert_From("New %s Objective: %s");
    description.Convert_From("Go to the Weapons Factory to speak with Logan.");
    expected.Convert_From("New Primary Objective: Go to the Weapons Factory to speak with Logan.");
    Objective value;
    value.type.Convert_From("Primary");
    Objective *objective = &value;
    EXPRESSIONS
    return 0;
}
'''.replace("EXPRESSIONS", "\n".join(e + '\nif (message != expected) return 1;' for e in expressions))
        compat = ROOT / "port/compatibility/include"
        with tempfile.TemporaryDirectory(prefix="objective-message-abi-") as folder:
            main, exe = Path(folder) / "main.cpp", Path(folder) / "probe"
            main.write_text(program)
            command = ["g++", "-std=c++17", "-O1", "-g", "-DNDEBUG=1", "-D_UNIX=1",
                       "-DRENEGADE_HOST_ABI_TEST=1", "-DRENEGADE_VITA_PORT=1",
                       "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
                       "-Wno-unknown-pragmas", "-Werror=conditionally-supported",
                       "-include", str(compat / "msvc_compat.h")]
            for directory in [compat, ROOT / "staging/wwlib", ROOT / "upstream/CnC_Renegade/Code/wwdebug",
                              ROOT / "upstream/CnC_Renegade/Code/wwlib", ROOT / "upstream/CnC_Renegade/Code/WWMath"]:
                command.extend(["-I", str(directory)])
            command.extend([str(main), str(ROOT / "staging/wwlib/wwstring.cpp"),
                            str(ROOT / "staging/wwlib/widestring.cpp"), "-pthread", "-o", str(exe)])
            compiled = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run([str(exe)], text=True, capture_output=True)
            self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)


if __name__ == "__main__":
    unittest.main()
