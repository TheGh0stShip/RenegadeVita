"""Execute the original loading animation-name expression with StringClass."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LoadingAnimationAbiTests(unittest.TestCase):
    def test_original_animation_name(self):
        source = (ROOT / "staging/commando/loadingscreen.cpp").read_text()
        expression = re.search(r'anim_name\.Format\([^;]+;', source).group()
        program = '''
#include "wwstring.h"
#include <cstring>
int main() {
    StringClass desc("IF_LVL94LOAD"), anim_name;
    EXPRESSION
    return std::strcmp(anim_name, "IF_LVL94LOAD.IF_LVL94LOAD") != 0;
}
'''.replace("EXPRESSION", expression)
        compat = ROOT / "port/compatibility/include"
        with tempfile.TemporaryDirectory(prefix="loading-animation-abi-") as folder:
            main, exe = Path(folder) / "main.cpp", Path(folder) / "probe"
            main.write_text(program)
            command = ["g++", "-std=c++17", "-O1", "-DNDEBUG=1", "-D_UNIX=1",
                       "-DRENEGADE_HOST_ABI_TEST=1", "-DRENEGADE_VITA_PORT=1",
                       "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
                       "-Werror=conditionally-supported", "-include", str(compat / "msvc_compat.h")]
            for directory in [compat, ROOT / "staging/wwlib", ROOT / "upstream/CnC_Renegade/Code/wwdebug",
                              ROOT / "upstream/CnC_Renegade/Code/wwlib", ROOT / "upstream/CnC_Renegade/Code/WWMath"]:
                command.extend(["-I", str(directory)])
            command.extend([str(main), str(ROOT / "staging/wwlib/wwstring.cpp"),
                            str(ROOT / "staging/wwlib/widestring.cpp"), "-pthread", "-o", str(exe)])
            compiled = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            subprocess.run([str(exe)], check=True)
        self.assertNotIn("progressBar", source)


if __name__ == "__main__":
    unittest.main()
