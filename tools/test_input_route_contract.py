import pathlib
import subprocess
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class InputRouteContractTests(unittest.TestCase):
    def test_versioned_bounded_route_header_and_checksum(self):
        source = textwrap.dedent(
            r"""
            #include "renegade_vita_input_route.h"
            #include <stddef.h>

            int main() {
                using namespace RenegadeVitaInputRoute;
                Sample samples[2] = {
                    {0x200U, 128U, 32U, 200U, 128U},
                    {0x8000U, 220U, 128U, 128U, 128U},
                };
                Header header = Build_Legacy_Header(samples, 2U, false);
                const size_t bytes = sizeof(Header) + sizeof(samples);
                if (!Validate_Header(header, bytes)) return 1;
                if (header.checksum != Checksum(samples, 2U)) return 2;
                if (header.flags != FLAG_COMPLETE) return 3;
                header.flags |= FLAG_TRUNCATED;
                if (!Validate_Header(header, bytes)) return 4;
                header.version++;
                if (Validate_Header(header, bytes)) return 5;
                header = Build_Legacy_Header(samples, 2U, false);
                if (Validate_Header(header, bytes + 1U)) return 6;
                header.sample_count = MAX_SAMPLES + 1U;
                if (Validate_Header(header, bytes)) return 7;
                TimedSample timed[2] = {
                    {0x200U, 128U, 32U, 200U, 128U, 0U},
                    {0x8000U, 220U, 128U, 128U, 128U, 16667U},
                };
                header = Build_Header(timed, 2U, false);
                const size_t timed_bytes = sizeof(Header) + sizeof(timed);
                if (!Validate_Header(header, timed_bytes)) return 8;
                if (header.version != VERSION) return 9;
                if (header.sample_size != sizeof(TimedSample)) return 10;
                return 0;
            }
            """
        )
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            cpp = root / "route_contract.cpp"
            binary = root / "route_contract"
            cpp.write_text(source, encoding="utf-8")
            subprocess.run(
                [
                    "g++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(ROOT / "port/platform"),
                    str(cpp),
                    "-o",
                    str(binary),
                ],
                check=True,
            )
            subprocess.run([str(binary)], check=True)

    def test_timed_routes_are_written_and_legacy_v1_stays_readable(self):
        source = (ROOT / "port/platform/renegade_directinput.cpp").read_text(encoding="utf-8")
        self.assertIn("TimedSample *g_route_samples", source)
        self.assertIn("activation=original-player-control", source)
        self.assertIn("RenegadeVitaInputRoute::LEGACY_VERSION", source)
        self.assertIn("timebase=recorded-delta-us", source)
        self.assertIn("kLegacyRouteV1SampleRate = 60.0f", source)
        self.assertIn("g_route_replay_elapsed_seconds", source)
        self.assertIn('"legacy60hz"', source)
        self.assertIn("Frame_Delta_Microseconds()", source)
        self.assertIn("g_route_replay_elapsed_us", source)
        self.assertIn("TimeManager::Get_Frame_Real_Seconds()", source)
        self.assertIn("kLegacyRouteV1MaximumFrameStep", source)
        self.assertIn("g_route_gameplay_active", source)
        self.assertIn("Renegade_Vita_Input_Route_Set_Gameplay_Active", source)
        self.assertIn("controller.buttons = live_abort;", source)
        self.assertIn("g_route_replay_exit_requested", source)
        self.assertIn("replay complete: injecting clean exit", source)
        self.assertIn("controller.buttons = live_abort | SCE_CTRL_START;", source)
        self.assertIn("Renegade_Vita_Input_Route_Replay_Exit_Requested", source)
        self.assertIn("gameplay activation: active=1", source)
        self.assertNotIn("const Sample &sample = g_route_samples[g_route_sample_index++];", source)

    def test_replay_complete_signal_reaches_runtime_exit_poll(self):
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text(encoding="utf-8")
        header = (ROOT / "port/platform/renegade_vita_input_telemetry.h").read_text(encoding="utf-8")
        self.assertIn("bool Renegade_Vita_Input_Route_Replay_Exit_Requested();", header)
        start_poll = runtime.split("bool Is_Start_Pressed()", 1)[1].split("} // namespace", 1)[0]
        self.assertIn("Renegade_Vita_Input_Route_Replay_Exit_Requested()", start_poll)
        self.assertIn("controller.buttons & SCE_CTRL_START", start_poll)


if __name__ == "__main__":
    unittest.main()
