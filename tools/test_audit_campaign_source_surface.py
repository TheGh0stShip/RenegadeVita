import unittest
from pathlib import Path

from tools.audit_campaign_source_surface import EXPECTED_DECLARATIONS, ROOT, audit


class CampaignSourceSurfaceTests(unittest.TestCase):
    def test_user_source_map_matches_all_thirteen_upstream_units(self):
        result = audit(ROOT)
        self.assertTrue(result["static_source_gate_passed"])
        self.assertEqual(result["campaign_mission_source_count"], 13)
        self.assertEqual(result["campaign_source_lines"], 101508)
        self.assertEqual(result["declared_script_count"], sum(EXPECTED_DECLARATIONS.values()))
        self.assertEqual(result["distinct_script_command_methods_used"], 143)
        self.assertEqual(result["script_command_table_entries"], 202)
        self.assertEqual(result["original_dsp_source_count"], 45)
        self.assertEqual(result["static_original_dsp_source_count"], 44)
        self.assertEqual(result["all_script_directory_cpp_count"], 54)
        self.assertEqual(result["cpp_source_names_outside_dsp"], [
            "Common.cpp", "Group.cpp", "GroupControl.cpp", "GroupScript.cpp",
            "MissionS04.cpp", "PRDemo.cpp", "Test_DEL.cpp", "Test_DLS_M03.cpp",
            "unitcombat.cpp",
        ])
        self.assertEqual(result["missing_command_table_methods"], [])
        self.assertEqual(result["staged_dsp_source_missing"], [])
        self.assertEqual(result["missing_mission_source_units"], [])

    def test_each_mission_declaration_count_is_pinned_to_source_inventory(self):
        result = audit(ROOT)
        actual = {row["source"]: row["declared_scripts"] for row in result["missions"]}
        self.assertEqual(actual, EXPECTED_DECLARATIONS)

    def test_mission_twelve_and_thirteen_sources_are_not_fabricated(self):
        source_root = ROOT / "upstream/CnC_Renegade/Code/Scripts"
        self.assertFalse((source_root / "Mission12.cpp").exists())
        self.assertFalse((source_root / "Mission13.cpp").exists())
        self.assertTrue((source_root / "Mission12.h").exists())


if __name__ == "__main__":
    unittest.main()
