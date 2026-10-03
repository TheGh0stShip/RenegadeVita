"""Source-only lifecycle checks; these do not execute the original engine."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CampaignDiscoveryHandoffTests(unittest.TestCase):
    def test_restore_follows_validated_campaign_load(self):
        source = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text()
        load = source.index("const bool loaded = CampaignManager::Load(state_reader);")
        restore = source.index("EncyclopediaMgrClass::Restore_Data();", load)
        initialize = source.index("EncyclopediaMgrClass::Initialize();", restore)
        region = source[load:initialize]
        self.assertIn("if (!loaded) break;", region)
        self.assertIn("#if !RENEGADE_VITA_M00_DEMO", region)
        self.assertIn("if (campaign_source != NULL)", region)
        self.assertIn("} else", region)
        validation = source[source.rfind("if (campaign_source != NULL)", 0, load):load]
        self.assertIn("campaign_state_size > 64U", validation)
        self.assertIn("|| is_save", validation)

    def test_original_initializer_overwrites_the_saved_copy(self):
        source = (ROOT / "staging/combat/encyclopediamgr.cpp").read_text()
        init = source.split("EncyclopediaMgrClass::Initialize (void)", 1)[1].split(
            "EncyclopediaMgrClass::Shutdown (void)", 1)[0]
        self.assertLess(init.index("Build_Bit_Vector"), init.index("Store_Data ();"))
        shutdown = source.split("EncyclopediaMgrClass::Shutdown (void)", 1)[1].split(
            "EncyclopediaMgrClass::Build_Bit_Vector", 1)[0]
        self.assertIn("KnownObjectVector[index].Clear ();", shutdown)
        self.assertNotIn("CopyOfKnownObjectVector", shutdown)
        self.assertIn("CopyOfKnownObjectVector[index] = KnownObjectVector[index];", source)
        self.assertIn("KnownObjectVector[index] = CopyOfKnownObjectVector[index];", source)

    def test_original_store_and_spawn_keep_discovery_owner(self):
        god = (ROOT / "staging/commando/god.cpp").read_text()
        store = god.split("void cGod::Store_Inventory", 1)[1].split("void cGod::Restore_Inventory", 1)[0]
        self.assertIn("EncyclopediaMgrClass::Store_Data();", store)
        restore = god.split("void cGod::Restore_Inventory", 1)[1].split("void cGod::Reset_Inventory", 1)[0]
        self.assertIn("EncyclopediaMgrClass::Restore_Data();", restore)
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text()
        self.assertIn("EncyclopediaMgrClass::Shutdown();", runtime)
        self.assertIn("local_player = cGod::Create_Player", runtime)


if __name__ == "__main__":
    unittest.main()
