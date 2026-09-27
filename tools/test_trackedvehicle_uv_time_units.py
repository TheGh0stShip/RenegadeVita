import pathlib
import unittest
import subprocess
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]


class TrackedVehicleUVTimeUnitTests(unittest.TestCase):
    def test_original_render_preserves_rate_on_repeated_timestamp(self):
        source = (ROOT / "staging/wwphys/trackedvehicle.cpp").read_text()
        begin = source.index("void TrackedVehicleClass::Render(RenderInfoClass & rinfo)")
        end = source.index("\nvoid TrackedVehicleClass::Set_Model", begin)
        fixture = (ROOT / "tools/host_trackedvehicle_repeat_render_test.cpp").read_text()
        with tempfile.TemporaryDirectory(prefix="renegade-track-render-") as directory:
            probe = pathlib.Path(directory) / "probe.cpp"
            executable = pathlib.Path(directory) / "probe"
            probe.write_text(fixture.replace("// ORIGINAL_RENDER_METHOD", source[begin:end]))
            subprocess.run(["c++", "-std=c++17", "-fsanitize=address,undefined",
                            str(probe), "-o", str(executable)], check=True)
            subprocess.run([str(executable)], check=True)

    def test_distance_per_render_is_converted_to_mapper_rate(self):
        patch = (ROOT / "port/patches/wwphys-a35-trackedvehicle-delta-time.patch").read_text()
        mapper_header = (ROOT / "upstream/CnC_Renegade/Code/ww3d2/mapper.h").read_text()
        mapper_source = (ROOT / "upstream/CnC_Renegade/Code/ww3d2/mapper.cpp").read_text()

        self.assertIn("movement * 1000.0f / static_cast<float>(elapsed_ms)", patch)
        self.assertIn("LastTrackSyncTime = sync_time", patch)
        self.assertIn("TrackPositionsInitialized = false", patch)
        self.assertIn("UVOffsetDeltaPerMS *= -0.001f", mapper_header)
        self.assertIn("UVOffsetDeltaPerMS.X * del", mapper_source)
        self.assertIn("UVOffsetDeltaPerMS.Y * del", mapper_source)

    def test_uninitialized_model_does_not_apply_origin_to_world_displacement(self):
        patch = (ROOT / "port/patches/wwphys-a35-trackedvehicle-delta-time.patch").read_text()
        self.assertIn("if (!TrackPositionsInitialized)", patch)
        self.assertIn("LeftTrackMovement = 0.0f", patch)
        self.assertIn("RightTrackMovement = 0.0f", patch)


if __name__ == "__main__":
    unittest.main()
