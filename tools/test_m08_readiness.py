"""Source contracts for the Mission 08 completion route and mobile-vehicle slot.

These checks inspect staged/original source only. They do not prove native
mission progression, which still requires a physical Vita run.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / "staging/scripts/mission08.cpp"
PATCH = ROOT / "port/patches/scripts-a36-m08-mobile-vehicle-attack-slot.patch"
STAGE_SCRIPT = ROOT / "tools/stage_sources.sh"
RAVESHAW = ROOT / "staging/combat/raveshawbossgameobj.cpp"


def script_body(source, name):
    start = re.search(r"DECLARE_SCRIPT\s*\(\s*%s\s*," % re.escape(name), source).start()
    following = source.find("DECLARE_SCRIPT", start + 1)
    return source[start:following if following != -1 else len(source)]


class MobileVehicleAttackSlot(unittest.TestCase):
    def setUp(self):
        self.body = script_body(STAGED.read_text(encoding="latin-1"), "M08_Mobile_Vehicle")

    def test_created_sentinel_is_retained(self):
        self.assertIn("loc = 100;", self.body)

    def test_every_slot_read_is_bounded(self):
        unguarded = re.findall(r"attack_loc\s*\[\s*loc\s*\]", self.body)
        self.assertEqual(len(unguarded), 1, "only the guarded accessor may index by loc")
        accessor = self.body[self.body.index("int Current_Attack_Location_ID"):]
        accessor = accessor[:accessor.index("}\n\n") + 1]
        self.assertIn("if (loc < 0 || loc > 10)", accessor)
        self.assertIn("return 0;", accessor)
        self.assertEqual(self.body.count("Find_Object (Current_Attack_Location_ID())"), 2)

    def test_patch_is_applied_after_apache_bounds(self):
        text = STAGE_SCRIPT.read_text()
        apache = text.index("scripts-a35-apache-controller-bounds.patch")
        mobile = text.index(PATCH.name)
        self.assertLess(apache, mobile)
        self.assertTrue(PATCH.exists())


class CompletionRoute(unittest.TestCase):
    def test_original_raveshaw_boss_reports_success(self):
        text = RAVESHAW.read_text(encoding="latin-1")
        landing = text[text.index("STATE_IMPL_THINK(RAVESHAW_STATE_DEATH_LANDING)"):]
        self.assertIn("CombatManager::Mission_Complete (true);", landing[:1200])

    def test_relocation_creates_raveshaw_and_objective_805(self):
        source = STAGED.read_text(encoding="latin-1")
        havoc = script_body(source, "M08_Havoc_DLS")
        self.assertIn("Commands->Create_Object (\"Raveshaw\"", havoc)
        self.assertIn("805, 3", havoc)
        controller = script_body(source, "M08_Objective_Controller")
        self.assertIn("type == M08_RELOCATE", controller)
        self.assertIn("Commands->Mission_Complete ( true );", controller)


if __name__ == "__main__":
    unittest.main()
