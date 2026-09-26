"""Exercise the actual staged getter without assuming host unsigned-long width."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildStampTests(unittest.TestCase):
    def test_little_endian_four_byte_stamp(self):
        source = (ROOT / 'staging/commando/buildnum.cpp').read_text()
        methods = []
        for signature in ('unsigned long BuildInfoClass::Get_Build_Number(void)',
                          'char *BuildInfoClass::Get_Build_Number_String(void)'):
            start = source.index(signature)
            end = source.index('\n}', start) + 2
            methods.append(source[start:end])
        harness = r'''
#include <cstdio>
#include <cstring>
#include <cstdint>
struct BuildInfoClass {
    static char BuildNumber[64];
    static unsigned long Get_Build_Number();
    static char *Get_Build_Number_String();
};
char BuildInfoClass::BuildNumber[64];
'''
        harness += '\n'.join(methods)
        harness += r'''
int main() {
    const uint32_t vectors[] = {0, 838, 0x7fffffff, 0xffffffff};
    for (uint32_t value : vectors) {
        memset(BuildInfoClass::BuildNumber, 0xa5, 64);
        for (int byte = 0; byte < 4; ++byte)
            BuildInfoClass::BuildNumber[28 + byte] = (value >> (8 * byte)) & 255;
        if (BuildInfoClass::Get_Build_Number() != value) return 1;
        char expected[16];
        snprintf(expected, sizeof(expected), "%lu", static_cast<unsigned long>(value));
        if (strcmp(expected, BuildInfoClass::Get_Build_Number_String())) return 2;
    }
}
'''
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            cpp, binary = directory / 'test.cpp', directory / 'test'
            cpp.write_text(harness)
            subprocess.run(['c++', '-std=c++17', '-fsanitize=address,undefined',
                            '-fno-sanitize-recover=all', str(cpp), '-o', str(binary)],
                           check=True, timeout=30)
            subprocess.run([str(binary)], check=True, timeout=5)


if __name__ == '__main__':
    unittest.main()
