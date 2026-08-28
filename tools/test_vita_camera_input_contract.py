#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import subprocess
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaCameraInputContractTests(unittest.TestCase):
    def test_default_camera_y_sign_matches_latest_physical_feedback(self) -> None:
        source = textwrap.dedent(
            r"""
            #include "renegade_vita_input_contract.h"

            int main() {
                using namespace RenegadeVitaInput;
	                if (!DEFAULT_CAMERA_RESPONSE.invert_y) return 1;
                const StickSample physical_up = Sample_Device_Stick(128U, 0U);
                const StickSample physical_down = Sample_Device_Stick(128U, 255U);
                const int up_dy = To_Camera_Mouse_Delta(
                    physical_up.y.normalized,
                    1.0f / 60.0f,
                    DEFAULT_CAMERA_RESPONSE.vertical_scale,
                    DEFAULT_CAMERA_RESPONSE.invert_y);
                const int down_dy = To_Camera_Mouse_Delta(
                    physical_down.y.normalized,
                    1.0f / 60.0f,
                    DEFAULT_CAMERA_RESPONSE.vertical_scale,
                    DEFAULT_CAMERA_RESPONSE.invert_y);
	                if (up_dy <= 0) return 2;
	                if (down_dy >= 0) return 3;
                if (To_Camera_Mouse_Delta(0.6f, 1.0f / 60.0f, 1.0f, true) !=
                    -To_Camera_Mouse_Delta(0.6f, 1.0f / 60.0f)) return 4;
                return 0;
            }
            """
        )
        with tempfile.TemporaryDirectory(prefix="renegade-vita-camera-") as temporary:
            root = pathlib.Path(temporary)
            cpp = root / "camera_input_contract.cpp"
            binary = root / "camera_input_contract"
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
                cwd=ROOT,
                check=True,
            )
            subprocess.run([str(binary)], cwd=ROOT, check=True)

    def test_directinput_boundary_uses_the_default_camera_response(self) -> None:
        source = (ROOT / "port/platform/renegade_directinput.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "RenegadeVitaInput::DEFAULT_CAMERA_RESPONSE.horizontal_scale", source
        )
        self.assertIn(
            "RenegadeVitaInput::DEFAULT_CAMERA_RESPONSE.vertical_scale", source
        )
        self.assertIn("RenegadeVitaInput::DEFAULT_CAMERA_RESPONSE.invert_y", source)
        self.assertNotIn("To_Camera_Mouse_Delta(\n\t\tright.y.normalized, frame_seconds,\n\t\t1.0f, true", source)


if __name__ == "__main__":
    unittest.main()
