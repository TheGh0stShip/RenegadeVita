"""Exercise the production inverse presentation used by Vita front touch."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class TouchPresentationTests(unittest.TestCase):
    def test_frontend_and_gameplay_touch_coordinates(self):
        text = (ROOT/'port/renderer/vita/ww3d_vita_renderer.cpp').read_text()
        start = text.index('bool Map_Native_Pixel_To_Logical(')
        production = text[start:text.index('\nbool Build_Native_Viewport(', start)]
        code = r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <limits>
#include <initializer_list>
struct NativePresentationRect { uint32_t x, y, width, height; };
NativePresentationRect g_native_presentation_rect{118, 0, 724, 544};
''' + production + r'''
int main() {
 float x = -1, y = -1;
 assert(Map_Native_Pixel_To_Logical(480, 272, 800, 600, x, y));
 assert(x == 400 && y == 300);
 // Original RC bottom button centers must round-trip across pillarboxing.
 for (float lx : {77.0f, 226.0f, 352.0f, 478.0f, 604.0f, 730.0f}) {
  assert(Map_Native_Pixel_To_Logical(118 + lx * 724 / 800,
      568.0f * 544 / 600, 800, 600, x, y));
  assert(fabs(x-lx) < 0.001f && fabs(y-568) < 0.001f);
 }
 for (float px : {0.0f, 117.9f, 842.0f, 959.0f}) {
  x = -1; y = -1;
  assert(!Map_Native_Pixel_To_Logical(px, 500, 800, 600, x, y));
  assert(x == -1 && y == -1);
 }
 assert(!Map_Native_Pixel_To_Logical(480, 544, 800, 600, x, y));
 assert(!Map_Native_Pixel_To_Logical(480, -1, 800, 600, x, y));
 assert(!Map_Native_Pixel_To_Logical(std::numeric_limits<float>::quiet_NaN(), 1, 800, 600, x, y));
 assert(!Map_Native_Pixel_To_Logical(480, 200, 0, 600, x, y));
 g_native_presentation_rect = {0, 0, 960, 544};
 assert(Map_Native_Pixel_To_Logical(959, 543, 960, 544, x, y));
 assert(x == 959 && y == 543);
}
'''
        with tempfile.TemporaryDirectory(prefix='renegade-touch-') as folder:
            path = Path(folder)
            (path/'test.cpp').write_text(code)
            subprocess.run(['g++', '-std=c++17', '-O1', '-g',
                '-fsanitize=address,undefined', str(path/'test.cpp'), '-o', str(path/'test')], check=True)
            subprocess.run([str(path/'test')], check=True)

if __name__ == '__main__':
    unittest.main()
