"""Prevent a cinematic-only census from accepting a missing mission segment."""
import tempfile
import unittest
from pathlib import Path

from tools.check_m13_script_coverage import ROOT, audit, check_symbols, script_dependencies
from tools.check_m13_mission_inventory import require_linked_scripts


class M13ScriptCoverageTests(unittest.TestCase):
    def test_tutorial_roots_do_not_import_campaign_or_skirmish_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Scripts.cpp").write_text('''
                DECLARE_SCRIPT(MTU_Start, "") { Commands->Attach_Script(obj, "Helper", ""); };
                DECLARE_SCRIPT(Helper, "") {};
                DECLARE_SCRIPT(MX0_Start, "") {};
                DECLARE_SCRIPT(MSK_Start, "") {};
            ''')
            result = script_dependencies(root, prefixes=("mtu_",))
            self.assertEqual({r["name"] for r in result["required_scripts"]}, {"MTU_Start", "Helper"})

    def test_dependency_walk_reaches_helpers_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Mission.cpp").write_text('''
                // DECLARE_SCRIPT(MX0_Comment, "") {}
                DECLARE_SCRIPT(MX0_Start, "") {
                    Commands->Attach_Script(obj, "Helper", "");
                    /* Commands->Attach_Script(obj, "Comment", ""); */
                };
                DECLARE_SCRIPT(Unrelated, "") {
                    Commands->Attach_Script(obj, "UnrelatedMissing", "");
                };
            ''')
            (root / "Helper.cpp").write_text('''
                DECLARE_SCRIPT(Helper, "") {
                    Commands->Attach_Script(obj, "MX0_Start", "");
                    Commands->Attach_Script(obj, script_name, parameters);
                    Other("NotAnAttachment");
                };
            ''')
            result = script_dependencies(root)
            self.assertEqual(result["required_owners"], ["Helper.cpp", "Mission.cpp"])
            self.assertEqual(result["unresolved_literal_scripts"], [])
            self.assertEqual({r["name"] for r in result["required_scripts"]},
                             {"MX0_Start", "Helper"})

    def test_unresolved_dependency_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Mission.cpp").write_text('''
                DECLARE_SCRIPT(MX0_Start, "") {
                    Commands->Attach_Script(obj, "Missing", "");
                };
            ''')
            self.assertEqual(script_dependencies(root)["unresolved_literal_scripts"], ["missing"])

    def test_original_mission_requires_area2_and_helper_owners_in_both_targets(self):
        result = audit(ROOT)
        self.assertTrue(result["source_selection_passed"], result["missing_owners"])
        self.assertTrue({"Test_RAD.cpp", "Toolkit.cpp", "Toolkit_Objects.cpp"}
                        <= set(result["required_owners"]))
        required = {row["name"] for row in result["required_scripts"]}
        self.assertTrue({"MX0_A02_Controller", "MX0_A02_ACTOR", "MX0_A02_GDI_MEDTANK",
                         "M00_Send_Object_ID", "M00_Damage_Modifier_DME"} <= required)

    def test_runtime_census_rejects_old_intro_only_registration_set(self):
        dependencies = script_dependencies(ROOT / "upstream/CnC_Renegade/Code/Scripts")
        scan = {"script_dependency_inventory": dependencies,
                "text_inventory": {"referenced_scripts": ["Test_Cinematic"]}}
        linked = {r["name"] for r in dependencies["required_scripts"]}
        self.assertEqual(len(require_linked_scripts(scan, linked)), len(linked))
        for owner in ("Test_RAD.cpp", "Toolkit.cpp", "Toolkit_Objects.cpp"):
            with self.subTest(owner=owner):
                incomplete = {r["name"] for r in dependencies["required_scripts"] if r["owner"] != owner}
                with self.assertRaisesRegex(ValueError, "factories absent"):
                    require_linked_scripts(scan, incomplete)

    def test_old_scan_cannot_silently_pass(self):
        with self.assertRaisesRegex(ValueError, "dependency inventory"):
            require_linked_scripts({"text_inventory": {"referenced_scripts": []}},
                                   {"MX0_MissionStart_DME"})

    def test_link_check_rejects_undefined_factory_and_string_only_name(self):
        result = {"required_scripts": [{"name": "MX0_A02_Controller"}]}
        for symbols in ("MX0_A02_Controller\n",
                        "                 U ScriptRegistrant<MX0_A02_Controller>::Create()\n"):
            check_symbols(result, symbols)
            self.assertFalse(result["linked_factories_passed"])
        check_symbols(result, "81001000 W ScriptRegistrant<MX0_A02_Controller>::Create()\n")
        self.assertTrue(result["linked_factories_passed"])


if __name__ == "__main__":
    unittest.main()
