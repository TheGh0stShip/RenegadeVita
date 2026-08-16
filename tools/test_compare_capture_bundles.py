#!/usr/bin/env python3

import csv
import json
import tempfile
import unittest
from pathlib import Path

from compare_capture_bundles import compare


class CaptureComparisonTest(unittest.TestCase):
    def write_bundle(self, root: Path, name: str, frame_us: int,
                     user_free: int, triangles: int) -> Path:
        bundle = root / name
        bundle.mkdir()
        state = {
            "schema_version": 1,
            "world": {"definitions": 2157, "static_objects": 495,
                      "dynamic_objects": 0, "lights": 192,
                      "render_object_nodes": 1615, "meshes": 1288,
                      "vertices": 38158, "polygons": 21537,
                      "prototypes": 1177, "visibility_objects": 1684,
                      "visibility_sectors": 347,
                      "definition_checksum": "90DB91BE",
                      "object_checksum": "4A930F8A",
                      "render_checksum": "BFA9C255",
                      "prototype_checksum": "E835A45F"},
            "player": {"present": False, "object_id": 0,
                       "definition": "", "type": ""},
            "renderer": {"draw_calls": 654, "mesh_submissions": 654,
                         "vertices": 30795, "triangles": triangles,
                         "indexed_draw_calls": 0, "indexed_triangles": 0,
                         "material_passes": 654, "textures_resident": 12,
                         "texture_bytes_resident": 1000, "texture_uploads": 0,
                         "texture_binds": 0, "state_changes": 5,
                         "rejected": 0, "unsupported": 0,
                         "backend_errors": 0, "geometry_checksum": "0C3D50E4",
                         "indexed_checksum": "00000000"},
            "memory": {"system_user_free": user_free,
                       "system_cdram_free": 1, "system_phycont_free": 2,
                       "vitagl_ram_free": 3, "vitagl_vram_free": 4,
                       "vitagl_slow_free": 5, "vitagl_all_free": 6},
        }
        (bundle / "state.json").write_text(json.dumps(state), encoding="utf-8")
        with (bundle / "frames.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["ordinary_frame_us",
                                                        "capture_readback_us",
                                                        "render_us", "present_us"])
            writer.writeheader()
            writer.writerow({"ordinary_frame_us": frame_us,
                             "capture_readback_us": 0,
                             "render_us": frame_us // 2,
                             "present_us": frame_us // 4})
        return bundle

    def test_reports_performance_memory_renderer_and_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = self.write_bundle(root, "before", 16000, 100, 17041)
            after = self.write_bundle(root, "after", 18000, 90, 17042)
            result = compare(before, after)
            self.assertEqual(result["performance"]["mean_ms"]["delta"], 2.0)
            self.assertEqual(result["performance"]["p99_ms"]["after"], 18.0)
            self.assertEqual(result["performance"]["slow_over_16_7ms"]["delta"], 1.0)
            self.assertEqual(result["stages"]["render_us.mean_ms"]["delta"], 1.0)
            self.assertEqual(result["memory"]["memory.system_user_free"]["delta"], -10)
            self.assertTrue(result["renderer"]["renderer.triangles"]["changed"])
            self.assertFalse(result["semantic"]["world.definitions"]["changed"])

    def test_accepts_schema_two_low_water_marks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = self.write_bundle(root, "before", 16000, 100, 17041)
            after = self.write_bundle(root, "after", 16000, 90, 17041)
            for bundle, low_water in ((before, 95), (after, 80)):
                state_path = bundle / "state.json"
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state["schema_version"] = 2
                state["memory"]["system_user_free_low_water"] = low_water
                state["memory"]["vitagl_ram_free_low_water"] = low_water - 1
                state_path.write_text(json.dumps(state), encoding="utf-8")
            result = compare(before, after)
            self.assertEqual(
                result["memory"]["memory.system_user_free_low_water"]["delta"], -15)


if __name__ == "__main__":
    unittest.main()
