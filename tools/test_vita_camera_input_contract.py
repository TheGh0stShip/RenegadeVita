#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import subprocess
import tempfile
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaCameraInputContractTests(unittest.TestCase):
    def test_original_secondary_fire_coupling_survives_vita_bindings(self) -> None:
        original = (ROOT / "staging/combat/input.cpp").read_text()
        boundary = (ROOT / "port/platform/a31_gameplay_boundary.cpp").read_text()
        start = boundary.index("Input::Set_Primary_Key_For_Function(INPUT_FUNCTION_ACTION, DIK_E)")
        bindings = boundary[start:boundary.index("\n}", start)]
        setter_start = original.index("Input::Set_Primary_Key_For_Function (int function_id, int key_id)")
        setter = original[setter_start:original.index("\n}", setter_start) + 2]
        tokens = sorted(set(re.findall(r"\b(?:INPUT_FUNCTION_\w+|DIK_\w+)\b", bindings + setter)))
        declarations = ",".join(tokens)
        source = f"""
        enum {{ {declarations}, KEY_COUNT }};
        struct DirectInput {{ enum {{ BUTTON_JOYSTICK_A=1001, BUTTON_JOYSTICK_B=1002 }}; }};
        int FunctionPrimaryKeys[KEY_COUNT]={{}}, secondary[KEY_COUNT]={{}};
        struct Input {{
            static void Set_Primary_Key_For_Function(int,int);
            static void Set_Secondary_Key_For_Function(int f,int k) {{ secondary[f]=k; }}
        }};
        void {setter}
        int main() {{
            {bindings}
            if (FunctionPrimaryKeys[INPUT_FUNCTION_USE_WEAPON] != DirectInput::BUTTON_JOYSTICK_A) return 1;
            if (FunctionPrimaryKeys[INPUT_FUNCTION_ACTION] != DIK_E) return 2;
            if (secondary[INPUT_FUNCTION_USE_WEAPON] != 0) return 3;
            if (FunctionPrimaryKeys[INPUT_FUNCTION_ZOOM_IN] != DIK_UP) return 4;
            if (FunctionPrimaryKeys[INPUT_FUNCTION_ZOOM_OUT] != DIK_DOWN) return 5;
            return 0;
        }}
        """
        with tempfile.TemporaryDirectory(prefix="renegade-scope-binding-") as temporary:
            cpp = pathlib.Path(temporary) / "binding.cpp"
            binary = pathlib.Path(temporary) / "binding"
            cpp.write_text(source)
            subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", str(cpp), "-o", str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

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
