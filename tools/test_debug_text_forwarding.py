"""Isolated callback behavior using the actual boundary function body.

This does not compile the full engine or establish target layout correctness.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DebugTextForwardingTests(unittest.TestCase):
    def test_installed_handler_receives_original_text_and_opaque_rgb(self):
        source = (ROOT / 'port/platform/a31_gameplay_boundary.cpp').read_text()
        start = source.index('void DebugManager::Display_Text(const WideStringClass &text,')
        end = source.index('\n}\n', start) + 3
        function = source[start:end]
        shim = r'''
#include <cassert>
struct WideStringClass {};
struct Vector3 { float v[3]; float operator[](int i) const { return v[i]; } };
struct Vector4 { float v[4]; Vector4(float a,float b,float c,float d):v{a,b,c,d}{} };
struct Handler {
    const WideStringClass *text = nullptr;
    Vector4 color{0,0,0,0};
    int calls = 0;
    void Display_Text(const WideStringClass &t, const Vector4 &c) {
        text = &t; color = c; ++calls;
    }
};
struct DebugManager {
    static inline Handler *DisplayHandler = nullptr;
    static void Display_Text(const WideStringClass &, const Vector3 &);
};
'''
        shim += function + r'''
int main() {
    WideStringClass text;
    Vector3 rgb{{0.25f,0.5f,0.75f}};
    DebugManager::Display_Text(text, rgb);
    Handler handler;
    DebugManager::DisplayHandler = &handler;
    DebugManager::Display_Text(text, rgb);
    assert(handler.calls == 1 && handler.text == &text);
    for (int i=0;i<3;++i) assert(handler.color.v[i] == rgb.v[i]);
    assert(handler.color.v[3] == 1.0f);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            cpp = Path(directory) / 'callback.cpp'
            cpp.write_text(shim)
            exe = Path(directory) / 'callback'
            subprocess.run(['g++', '-std=c++17', '-include', 'cstddef',
                            '-fsanitize=address,undefined', str(cpp), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
