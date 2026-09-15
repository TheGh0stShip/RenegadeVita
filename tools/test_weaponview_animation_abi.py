"""Execute production animation-name expressions against original StringClass."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WeaponAnimationAbiTests(unittest.TestCase):
    def test_original_stringclass_weapon_and_hand_names(self):
        source = (ROOT / "staging/combat/weaponview.cpp").read_text()
        expressions = re.findall(r'anim_name\.Format\(\s*"(?:%s\.F_GA_|F_SKELETON\.F_HA_)[\s\S]*?\);', source)
        self.assertEqual(len(expressions), 2)
        # Exercise the production expressions, not a reimplementation of them.
        # Original non-trivial StringClass exposes the same varargs pitfall on
        # the host. Invalid class-valued arguments are rejected by the compiler.
        program = r'''
#include "wwstring.h"
#include <cstdio>
#include <cstring>
int main() {
    const char *WeaponActionNames[] = {"IDLE", "FIRE", "RELOD", "ENTER", "EXIT"};
    const char *weapons[] = {"PIST", "RIFL", "SNIP", "SHOT", "CHNG", "FLAM", "LAZR", "RCKT"};
    for (const char *name : weapons) {
        StringClass weapon_name(name), weapon_htree_name;
        weapon_htree_name.Format("F_GM_%s", name);
        for (int i = 0; i != 5; ++i) {
            const int state = i >= 3 ? 0 : i;
            StringClass anim_name;
            char expected[128];
            WEAPON_EXPRESSION
            std::snprintf(expected, sizeof(expected), "F_GM_%s.F_GA_%s_%s", name, name, WeaponActionNames[state]);
            if (std::strcmp((const char *)anim_name, expected)) return 1;
            HAND_EXPRESSION
            std::snprintf(expected, sizeof(expected), "F_SKELETON.F_HA_%s_%s", name, WeaponActionNames[i]);
            if (std::strcmp((const char *)anim_name, expected)) return 2;
        }
    }
    std::puts("PASS: 80 original StringClass weapon/hand animation names");
}
'''.replace("WEAPON_EXPRESSION", expressions[0]).replace("HAND_EXPRESSION", expressions[1])
        compat = ROOT / "port/compatibility/include"
        with tempfile.TemporaryDirectory(prefix="weapon-animation-abi-") as folder:
            main = Path(folder) / "main.cpp"
            exe = Path(folder) / "probe"
            main.write_text(program)
            command = ["g++", "-std=c++17", "-O1", "-g", "-DNDEBUG=1", "-D_UNIX=1",
                       "-DRENEGADE_HOST_ABI_TEST=1", "-DRENEGADE_VITA_PORT=1",
                       "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
                       "-Wno-unknown-pragmas", "-Werror=conditionally-supported",
                       "-include", str(compat / "msvc_compat.h")]
            for directory in [compat, ROOT / "staging/wwlib", ROOT / "upstream/CnC_Renegade/Code/wwdebug",
                              ROOT / "upstream/CnC_Renegade/Code/wwlib", ROOT / "upstream/CnC_Renegade/Code/WWMath"]:
                command.extend(["-I", str(directory)])
            command.extend([str(main), str(ROOT / "staging/wwlib/wwstring.cpp"), "-pthread", "-o", str(exe)])
            compiled = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run([str(exe)], text=True, capture_output=True)
            self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)


if __name__ == "__main__":
    unittest.main()
