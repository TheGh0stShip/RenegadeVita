#!/usr/bin/env python3
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MissionTeardownContractTests(unittest.TestCase):
    def test_destroy_all_drains_scripts_queued_by_object_detach(self):
        patch = (
            ROOT / "port" / "patches" / "combat-a35-teardown-lifecycle.patch"
        ).read_text(encoding="utf-8")
        self.assertIn("NetworkObjectMgrClass::Delete_Pending", patch)
        self.assertIn("ScriptManager::Destroy_Pending();", patch)
        self.assertLess(
            patch.index("NetworkObjectMgrClass::Delete_Pending"),
            patch.index("ScriptManager::Destroy_Pending();"),
        )

    def test_headless_hud_does_not_allocate_presentation_notifications(self):
        patch = (
            ROOT / "port" / "patches" / "combat-a35-teardown-lifecycle.patch"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "PowerupBoxRenderer == NULL || PowerupTextRenderer == NULL", patch
        )
        self.assertLess(
            patch.index("PowerupBoxRenderer == NULL"),
            patch.index("PowerupIconStruct * data = new PowerupIconStruct()"),
        )

    def test_teardown_patch_is_deterministically_staged(self):
        stage = (ROOT / "tools" / "stage_sources.sh").read_text(encoding="utf-8")
        self.assertIn("combat-a35-teardown-lifecycle.patch", stage)


if __name__ == "__main__":
    unittest.main()
