"""Source-contract checks for objective/HUD/radar/encyclopedia lifecycle state.

Host-only text checks over the staged tree; they do not execute the engine.
See reports/campaign/OBJECTIVE_STATE_LIFECYCLE.md for the traced paths.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return (ROOT / relative).read_text()


def body(source, start, end):
    head = source.index(start)
    return source[head:source.index(end, head)]


class ObjectiveStateLifecycleTests(unittest.TestCase):
    def test_hud_index_guard_precedes_every_list_index_use(self):
        hud = read("staging/combat/hud.cpp")
        update = body(hud, "static\tvoid\tObjective_Update( void )", "static\tvoid\tObjective_Render( void )")
        guard = update.index("CurrentObjectiveIndex >= objective_count")
        first_index = update.index("Get_Objective( CurrentObjectiveIndex )")
        self.assertLess(guard, first_index)
        self.assertLess(guard, update.index("Get_HUD_Objectives_Location( CurrentObjectiveIndex )"))
        guarded = update[guard:update.index("// maintain the index")]
        self.assertIn("CurrentObjectiveIndex = 0;", guarded)
        self.assertIn("CurrentObjective = NULL;", guarded)
        self.assertIn("rebuild = true;", guarded)

    def test_encyclopedia_save_flushes_bit_cache_before_raw_read(self):
        source = read("staging/combat/encyclopediamgr.cpp")
        helper = body(source, "Flush_Bit_Cache (BooleanVectorClass &known_objects)", "//\tSave")
        self.assertIn("known_objects.Length () > 1", helper)
        self.assertIn("known_objects[0]", helper)
        self.assertIn("known_objects[1]", helper)
        save = body(source, "EncyclopediaMgrClass::Save (ChunkSaveClass &csave)", "EncyclopediaMgrClass::Load")
        self.assertLess(save.index("Flush_Bit_Cache (KnownObjectVector[index]);"),
                        save.index("Get_Bit_Array()"))
        # The raw accessor must stay unflushed in the shared header; the flush
        # lives in the one saver so the copied wwaudio/Vector.H stays identical.
        header = read("staging/wwlib/vector.h")
        self.assertIn("Get_Bit_Array(void)	{ return BitArray; }", header)
        self.assertEqual(header, read("staging/wwaudio/Vector.H"))

    def test_boolean_vector_assignment_carries_the_write_back_cache(self):
        # Store_Data / Restore_Data copy the cached bit together with the array,
        # so a dirty bit survives a handoff only until the next raw read.
        vector = read("staging/wwlib/vector.cpp")
        assign = body(vector, "BooleanVectorClass & BooleanVectorClass::operator =(", "return(*this);")
        for field in ("Copy = vector.Copy;", "LastIndex = vector.LastIndex;", "BitArray = vector.BitArray;"):
            self.assertIn(field, assign)

    def test_new_patches_are_registered_once_in_order_and_in_inventory(self):
        script = read("tools/stage_sources.sh")
        inventory = read("staging/PATCH_INVENTORY.json")
        names = ("combat-a37-hud-objective-index-bounds.patch",
                 "combat-a37-encyclopedia-save-bit-cache-flush.patch")
        last = script.index("combat-a37-screen-overlay-opacity-clamp.patch")
        for name in names:
            self.assertEqual(script.count("port/patches/" + name), 1)
            self.assertEqual(inventory.count("port/patches/" + name), 1)
            self.assertTrue((ROOT / "port/patches" / name).is_file())
            position = script.index("port/patches/" + name)
            self.assertGreater(position, last)
            last = position

    def test_level_unload_resets_objective_and_radar_state(self):
        combat = read("staging/combat/combat.cpp")
        unload = body(combat, "void\tCombatManager::Unload_Level( void )", "PhysicsSceneClass\t*\tCombatManager::Get_Scene")
        self.assertIn("ObjectiveManager::Reset();", unload)
        self.assertLess(unload.index("GameObjManager::Shutdown();"), unload.index("ObjectiveManager::Reset();"))
        init = body(read("staging/combat/objectives.cpp"), "void\tObjectiveManager::Init( void )", "void\tObjectiveManager::Shutdown")
        self.assertIn("HUDUpdate = true;", init)
        self.assertIn("NumSpecifiedTertiaryObjectives = 0;", init)
        shutdown = read("staging/commando/combatgmode.cpp")
        core = body(shutdown, "void \tCombatGameModeClass::Core_Shutdown()", "Post_Load_Id_Uniqueness_Check")
        self.assertLess(core.index("CombatManager::Unload_Level();"), core.index("RadarManager::Shutdown();"))
        restart = body(shutdown, "bool CombatGameModeClass::Core_Restart(", "bool CombatGameModeClass::Process_Core_Restart_Request")
        self.assertLess(restart.index("Core_Shutdown();"), restart.index("Load_Level();"))

    def test_objective_save_requires_every_field_and_load_never_toasts(self):
        objectives = read("staging/combat/objectives.cpp")
        load = body(objectives, "bool\tObjectiveManager::Load( ChunkLoadClass &cload )", "void\tObjectiveManager::Add_Objective")
        self.assertNotIn("Add_Message", load)
        self.assertNotIn("HUDClass::Add_Objective", load)
        self.assertIn("Viewer.Update ();", load)
        self.assertIn("HUDUpdate = true;", load)
        entry = body(objectives, "bool\tObjective::Load( ChunkLoadClass &cload )", "Objective * ObjectiveManager::Add_Loadable_Objective")
        self.assertIn("(1U << 13) - 1U", entry)
        add = body(objectives, "void\tObjectiveManager::Add_Objective(", "void\tObjectiveManager::Remove_Objective")
        self.assertIn("Find_Objective( id ) != NULL", add)  # duplicate ids never double-add

    def test_hud_saves_only_its_enable_flag(self):
        hud = read("staging/combat/hud.cpp")
        save = body(hud, "bool\tHUDClass::Save( ChunkSaveClass &csave )", "bool\tHUDClass::Load")
        self.assertIn("MICROCHUNKID_ENABLED", save)
        self.assertNotIn("Objective", save)
        # Pog/arrow state is rebuilt from ObjectiveManager every HUD frame.
        self.assertIn("CurrentObjectiveIndex=0;", body(hud, "static\tvoid\tObjective_Init( void )", "static\tvoid\tObjective_Release_Pogs"))

    def test_session_handoff_restores_discoveries_without_initialize(self):
        runtime = read("port/platform/vita/a31_vita_runtime.cpp")
        restore = runtime.index("EncyclopediaMgrClass::Restore_Data();")
        initialize = runtime.index("EncyclopediaMgrClass::Initialize();", restore)
        self.assertIn("} else", runtime[restore:initialize])
        self.assertRegex(runtime, re.compile(r"EncyclopediaMgrClass::Shutdown\(\);\s+CampaignManager::Shutdown\(\);"))

    def test_eva_objectives_tab_and_viewer_rebuild_from_manager(self):
        tab = read("staging/commando/dlgevaobjectivestab.cpp")
        init = body(tab, "EvaObjectivesTabClass::On_Init_Dialog", "EvaObjectivesTabClass::On_Command")
        self.assertIn("Fill_Objectives_List ();", init)
        settings = read("staging/combat/evasettings.cpp")
        post = body(settings, "EvaSettingsDefClass::On_Post_Load (void)", "return;")
        self.assertIn("ObjectiveManager::Reload_Viewer ();", post)
        load_defs = read("staging/combat/savegame.cpp")
        self.assertIn("return Load_Save_Load_System(filename, true, required_file);", load_defs)


if __name__ == "__main__":
    unittest.main()
