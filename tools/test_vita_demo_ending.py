"""Execute the demo presentation policy without fabricating engine mission events."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DemoEndingTests(unittest.TestCase):
    def test_m00_gate_and_success_timeline(self):
        with tempfile.TemporaryDirectory(prefix="renegade-demo-") as temp:
            source = Path(temp) / "policy.cpp"
            executable = Path(temp) / "policy"
            source.write_text(r'''
#include "a31_demo_ending.h"
#include <cassert>
#include <cstring>
int main() {
    using namespace A31Demo;
    assert(IsTutorialMap("M00_Tutorial.mix"));
    assert(IsTutorialMap("m00_tutorial.MIX"));
    for (const char *name : {"M01.mix", "M00_Tutorial.mix.bak", "../M00_Tutorial.mix", "", "M00_Tutorial"})
        assert(!IsTutorialMap(name));
    assert(!IsTutorialMap(nullptr));
    Ending untouched;
    untouched.Update(100000000);
    assert(!untouched.Active() && untouched.GetPhase() == Ending::Playing);
    Ending ending;
    ending.Start(100);
    ending.Update(100);
    assert(ending.Active() && ending.GetPhase() == Ending::Fade && ending.Alpha() == 0.0f);
    float previous = 0;
    for (uint64_t step = 0; step < 3000000; step += 1000) {
        ending.Update(100 + step);
        assert(ending.GetPhase() == Ending::Fade);
        assert(ending.Alpha() >= previous && ending.Alpha() <= 1.0f);
        previous = ending.Alpha();
    }
    ending.Start(9000000); // Completion notifications cannot restart the ending.
    ending.Update(3000100);
    assert(ending.GetPhase() == Ending::Thanks && ending.Alpha() == 1.0f);
    ending.Update(13000099);
    assert(ending.GetPhase() == Ending::Thanks);
    ending.Update(13000100);
    assert(ending.GetPhase() == Ending::CreditScene);
    ending.Update(33000099);
    assert(ending.GetPhase() == Ending::CreditScene);
    ending.Update(33000100);
    assert(ending.GetPhase() == Ending::Done);
    assert(std::strcmp(ThankYou, "Thank you for playing the Renegade Vita Demo! There is still more work to be done before this is a complete title. Stay tuned!") == 0);
    assert(std::strstr(Credits, "vitaGL") && std::strstr(Credits, "FFmpeg"));
}
''', encoding="ascii")
            subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                            "-include", "initializer_list", f"-I{ROOT / 'port/platform'}",
                            str(source), "-o", str(executable)], check=True, capture_output=True)
            subprocess.run([str(executable)], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
