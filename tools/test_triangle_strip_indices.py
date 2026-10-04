from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TriangleStripIndicesTest(unittest.TestCase):
    def test_winding_degenerates_offsets_and_bounds(self):
        cpp = r'''
#include "triangle_strip_indices.h"
#include <algorithm>
#include <cassert>
#include <limits>
#include <vector>
using RenegadeVitaRenderer::Expand_Triangle_Strip;
int main() {
    const uint16_t strip[] = {99,99,0,1,2,3,4};
    uint16_t output[12];
    std::fill(output, output+12, 0xbeef);
    assert(Expand_Triangle_Strip(strip, 7, 2, 3, output, 12));
    const uint16_t expected[] = {0,1,2,2,1,3,2,3,4};
    assert(std::equal(output, output+9, expected));
    assert(output[9] == 0xbeef && strip[0] == 99 && strip[6] == 4);
    const uint16_t degenerate[] = {0,1,1,2};
    assert(Expand_Triangle_Strip(degenerate, 4, 0, 2, output, 12));
    const uint16_t degenerate_expected[] = {0,1,1,1,1,2};
    assert(std::equal(output, output+6, degenerate_expected));
    // The maximum original 16-bit index-buffer capacity stays bounded.
    std::vector<uint16_t> large(65535), triangles(65533 * 3);
    for (size_t i=0; i<large.size(); ++i) large[i]=static_cast<uint16_t>(i);
    assert(Expand_Triangle_Strip(large.data(), large.size(), 0, 65533,
                                 triangles.data(), triangles.size()));
    assert(triangles[0] == 0 && triangles[2] == 2 && triangles.back() == 65534);
    // Every invalid request must leave the destination untouched.
    std::fill(output, output+12, 0xbeef);
    assert(!Expand_Triangle_Strip(strip, 7, 8, 1, output, 12));
    assert(!Expand_Triangle_Strip(strip, 7, 5, 1, output, 12));
    assert(!Expand_Triangle_Strip(strip, 7, 2, 3, output, 8));
    assert(!Expand_Triangle_Strip(nullptr, 7, 0, 1, output, 12));
    assert(!Expand_Triangle_Strip(strip, 7, 0, 1, nullptr, 12));
    assert(!Expand_Triangle_Strip(strip, 7, 0, std::numeric_limits<size_t>::max(), output, 12));
    assert(std::all_of(output, output+12, [](uint16_t x){return x==0xbeef;}));
    assert(Expand_Triangle_Strip(nullptr, 0, 0, 0, nullptr, 0));
}
'''
        with tempfile.TemporaryDirectory(prefix='renegade-strip-') as folder:
            p = Path(folder)
            (p / 'strip.cpp').write_text(cpp)
            include = '-I' + str(ROOT / 'port/renderer/vita')
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer', include,
                            str(p / 'strip.cpp'), '-o', str(p / 'strip')], check=True)
            subprocess.run([str(p / 'strip')], check=True, env={**os.environ,
                           'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1',
                           'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'})
            arm = Path('/usr/local/vitasdk/bin/arm-vita-eabi-g++')
            if arm.exists():
                subprocess.run([str(arm), '-std=c++17', '-O1', '-Wall', '-Wextra', '-Werror',
                                '-mcpu=cortex-a9', '-mfpu=neon', '-mfloat-abi=hard', include,
                                '-include', str(ROOT / 'port/compatibility/include/renegade_target_abi.h'),
                                '-c', str(p / 'strip.cpp'), '-o', str(p / 'strip.arm.o')], check=True)


if __name__ == '__main__':
    unittest.main()
