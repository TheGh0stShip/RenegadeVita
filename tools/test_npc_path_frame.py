"""Execute the production frame boundary with observable engine-owner doubles."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NpcPathFrameTests(unittest.TestCase):
    def test_path_service_order_and_pause(self):
        source = (ROOT / "port/platform/a31_gameplay_boundary.cpp").read_text()
        frame = source.split("void A31_Interactive_Run_Simulation_Frame()", 1)[1]
        frame = frame.split("uint32_t Count_Physics_Objects", 1)[0]
        program = r'''
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <string>
#define RENEGADE_A4_ORIGINAL_GAMEMODE 1
#define RENEGADE_HOST_ABI_TEST 1
std::string events;
bool toggle = false;
enum { INPUT_FUNCTION_MENU_TOGGLE };
struct Vector3 { int marker; };
struct Camera { Vector3 Get_Position() { return {73}; } } camera;
Camera *COMBAT_CAMERA = &camera;
struct TimeManager { static void Update() { events += 'T'; } };
struct Input {
    static void Update() { events += 'I'; }
    static bool Get_State(int) { return toggle; }
};
struct GameModeClass {
    bool active = true;
    bool Is_Active() { return active; }
    bool Is_Suspended() { return !active; }
    void Suspend() { active = false; }
    void Resume() { active = true; }
} mode;
struct GameModeManager { static GameModeClass *Find(const char*) { return &mode; } };
struct PathMgrClass {
    static void Resolve_Paths(const Vector3 &p) {
        assert(p.marker == 73); events += 'P';
    }
};
struct CombatManager {
    static void Generate_Control() { events += 'C'; }
    static void Think() { events += 'S'; }
};
struct cNetwork { static void Update() { events += 'N'; } };
struct A31SimulationStageTotals {
    uint32_t frames;
    uint64_t time_manager_us;
    uint64_t input_us;
    uint64_t path_us;
    uint64_t control_us;
    uint64_t network_us;
    uint64_t combat_us;
    uint64_t other_us;
    uint64_t simulated_us;
    uint64_t real_us;
};
void A31_Interactive_Apply_Render_Capabilities() { events += 'R'; }
void A31_Interactive_Run_Simulation_Frame() FRAME
int main() {
    A31_Interactive_Run_Simulation_Frame();
    assert(events == "TIPCNSR");
    events.clear(); mode.active = false;
    A31_Interactive_Run_Simulation_Frame();
    assert(events == "TIN");
    events.clear(); mode.active = true; COMBAT_CAMERA = nullptr;
    A31_Interactive_Run_Simulation_Frame();
    assert(events == "TICNSR");
    events.clear(); COMBAT_CAMERA = &camera; toggle = true;
    A31_Interactive_Run_Simulation_Frame();
    assert(events == "TIN");
}
'''.replace("FRAME", frame)
        with tempfile.TemporaryDirectory(prefix="npc-path-frame-") as folder:
            cpp, exe = Path(folder) / "test.cpp", Path(folder) / "test"
            cpp.write_text(program)
            result = subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra",
                                     "-Werror", str(cpp), "-o", str(exe)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    unittest.main()
