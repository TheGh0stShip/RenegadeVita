#!/usr/bin/env python3

import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools.validate_vita_loading_capture import validate


def write_bmp(
    path: Path,
    width: int = 960,
    height: int = 544,
    *,
    black: bool = False,
    content_rect: tuple[int, int, int, int] | None = None,
) -> None:
    row_bytes = ((width * 3 + 3) // 4) * 4
    pixel_bytes = row_bytes * height
    with path.open("wb") as handle:
        handle.write(struct.pack("<2sIHHI", b"BM", 54 + pixel_bytes, 0, 0, 54))
        handle.write(struct.pack("<IiiHHI", 40, width, height, 1, 24, 0))
        handle.write(struct.pack("<IiiII", pixel_bytes, 0, 0, 0, 0))
        for y in range(height):
            row = bytearray(row_bytes)
            for x in range(width):
                in_content = (
                    content_rect is None
                    or (content_rect[0] <= x < content_rect[2] and content_rect[1] <= y < content_rect[3])
                )
                if black or not in_content:
                    blue = green = red = 0
                else:
                    red = (x * 3 + y) & 0xFF
                    green = (x + y * 5) & 0xFF
                    blue = (x * 7 + y * 11) & 0xFF
                row[x * 3 : x * 3 + 3] = bytes((blue, green, red))
            handle.write(row)


def state(candidate: str = "A3.5-dev38") -> dict:
    return {
        "schema_version": 4,
        "milestone": candidate,
        "build_label": f"Renegade Vita {candidate}",
        "runtime_log_path": "ux0:data/renegade/user/logs/a35-dev38-runtime.log",
        "reason": "level-ready",
        "phase": "original-loading-screen",
        "loading_visual_gate": {
            "active": True,
            "framebuffer_width": 960,
            "framebuffer_height": 544,
            "original_logical_width": 640,
            "original_logical_height": 480,
            "native_display_width": 960,
            "native_display_height": 544,
            "logical_to_native_fullscreen": True,
            "original_loading_screen_owner": True,
            "direct_vitagl_overlay_disabled": True,
            "loading_texture_v_flip_enabled": False,
            "gameplay_texture_v_unchanged": True,
        },
    }


class LoadingCaptureValidatorTests(unittest.TestCase):
    def write_state(self, root: Path, payload: dict) -> Path:
        path = root / "state.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_accepts_candidate_matched_schema_four_native_nonblank_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = root / "frame.bmp"
            write_bmp(frame)
            result = validate("A3.5-dev38", frame, self.write_state(root, state()))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["frame_info"]["width"], 960)
        self.assertEqual(result["frame_info"]["height"], 544)
        self.assertGreater(result["frame_info"]["nonblack_ratio"], 0.10)
        self.assertGreaterEqual(result["frame_info"]["content_width_ratio"], 0.80)
        self.assertGreaterEqual(result["frame_info"]["content_height_ratio"], 0.70)

    def test_rejects_schema_three_or_missing_visual_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = root / "frame.bmp"
            write_bmp(frame)
            payload = state()
            payload["schema_version"] = 3
            payload.pop("loading_visual_gate")
            result = validate("A3.5-dev38", frame, self.write_state(root, payload))
        failed = {item["name"] for item in result["checks"] if not item["passed"]}
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("state_schema_v4", failed)
        self.assertIn("visual_gate_present", failed)

    def test_rejects_wrong_size_or_black_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = root / "frame.bmp"
            write_bmp(frame, 960, 544, black=True)
            result = validate("A3.5-dev38", frame, self.write_state(root, state()))
        failed = {item["name"] for item in result["checks"] if not item["passed"]}
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("bmp_not_blank_black", failed)
        self.assertIn("bmp_content_width_extent", failed)
        self.assertIn("bmp_content_height_extent", failed)

    def test_rejects_small_loading_bar_as_fullscreen_visual_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = root / "frame.bmp"
            write_bmp(frame, content_rect=(80, 420, 880, 470))
            result = validate("A3.5-dev38", frame, self.write_state(root, state()))
        failed = {item["name"] for item in result["checks"] if not item["passed"]}
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("bmp_content_height_extent", failed)
        self.assertLess(result["frame_info"]["content_height_ratio"], 0.70)

    def test_rejects_runtime_log_from_stale_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = root / "frame.bmp"
            write_bmp(frame)
            payload = state()
            payload["runtime_log_path"] = "ux0:data/renegade/user/logs/a35-dev37-runtime.log"
            result = validate("A3.5-dev38", frame, self.write_state(root, payload))
        failed = {item["name"] for item in result["checks"] if not item["passed"]}
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("state_runtime_log", failed)


if __name__ == "__main__":
    unittest.main()
