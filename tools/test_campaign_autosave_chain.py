"""Source-only checks for the campaign autosave chain; no engine code runs."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(relative):
    return (ROOT / relative).read_text()


def body(source, start, end):
    return source.split(start, 1)[1].split(end, 1)[0]


class CampaignAutosaveChainTests(unittest.TestCase):
    def test_level_directive_requests_autosave_except_m13(self):
        level = body(read("staging/commando/campaign.cpp"),
            'StringMatch( state_description, "Level " )',
            'StringMatch( state_description, "Movie " )')
        end_game = level.index("GameInitMgrClass::End_Game();")
        mark = level.index("A4_Frontend_Mark_Next_Start_Game_As_Campaign_Level();")
        start = level.index("GameInitMgrClass::Start_Game ( state_description")
        request = level.index("CombatManager::Request_Autosave();")
        self.assertLess(end_game, mark)
        self.assertLess(mark, start)
        self.assertLess(start, request)
        self.assertIn('::strnicmp( state_description, "M13", 3 ) != 0', level)

    def test_request_is_consumed_only_by_running_single_player_god(self):
        source = read("staging/commando/combatgmode.cpp")
        process = body(source, "void CombatGameModeClass::Process_Autosave_Request()",
            "void 	CombatGameModeClass::Render()")
        gate = process.index("cGod::Can_Save_Current_State()")
        clear = process.index("CombatManager::Request_Autosave( false );")
        save = process.index('SaveGameManager::Save_Game( "save\\\\autosave.sav", &_CommandoSaveLoad, NULL );')
        self.assertLess(gate, clear)
        self.assertLess(clear, save)
        self.assertIn("Last_Save_Write_Succeeded()", process)
        god = read("staging/commando/god.cpp")
        self.assertIn("return State == GOD_STATE_SINGLE_RUNNING;", god)
        think = body(god, "void cGod::Think(void)", "void cGod::Create_Ai_Player(void)")
        self.assertLess(think.index("Create_Commando("), think.index("State = GOD_STATE_SINGLE_RUNNING;"))

    def test_vita_frame_consumes_after_combat_think_and_pause_returns_first(self):
        frame = body(read("port/platform/a31_gameplay_boundary.cpp"),
            "void A31_Interactive_Run_Simulation_Frame()", "A31_Interactive_Apply_Render_Capabilities();")
        pause = frame.index("A31_Vita_Request_Gameplay_Pause();")
        early_return = frame.index("return;", pause)
        think = frame.index("CombatManager::Think();")
        autosave = frame.index("CombatGameModeClass::Process_Autosave_Request();")
        self.assertLess(early_return, think)
        self.assertLess(think, autosave)

    def test_request_crosses_only_the_campaign_handoff(self):
        runtime = read("port/platform/vita/a31_vita_runtime.cpp")
        tail = runtime[runtime.rindex("result.campaign_handoff_cleanup_completed ? 1 : 0);"):]
        clear = tail.index("CombatManager::Request_Autosave(false);")
        guard = tail.rindex("if (", 0, clear)
        self.assertIn("CombatManager::Is_Autosave_Requested() && !result.campaign_handoff_completed",
            tail[guard:clear])
        self.assertLess(clear, tail.index("return result;"))
        failure = body(runtime, "void Queue_Campaign_Handoff_Failure(",
            "bool Run_Original_Campaign_Intermission(")
        self.assertIn("CombatManager::Request_Autosave(false);", failure)
        recovery = body(runtime, "void Queue_Local_Load_Failure_Recovery(",
            "bool Run_Original_Gameplay_Pause_Menu(")
        self.assertIn("CombatManager::Request_Autosave(false);", recovery)

    def test_autosave_uses_rooted_atomic_writer(self):
        runtime = read("port/platform/vita/a31_vita_runtime.cpp")
        self.assertIn("RenegadeRootedFileFactoryClass root_factory(kVitaRoots);", runtime)
        self.assertIn("_TheWritingFileFactory = &root_factory;", runtime)
        save = body(read("staging/combat/savegame.cpp"),
            "void _cdecl SaveGameManager::Save_Game( const char * filename, ... )",
            "void	SaveGameManager::Pre_Load_Game")
        self.assertIn("_TheWritingFileFactory->Get_File( filename );", save)
        self.assertIn("file->Abort_Write();", save)
        factory = read("port/filesystem/renegade_file_factory.cpp")
        self.assertIn('"%s.pending", LastResolution.physical', factory)
        self.assertIn("const bool write_only = rights == FileClass::WRITE;", factory)
        paths = read("port/filesystem/renegade_paths.cpp")
        self.assertIn('memcpy(normalized, "save/", 5U);', paths)

    def test_save_carries_campaign_position_and_restored_inventory(self):
        saveload = body(read("staging/commando/commandosaveload.cpp"),
            "bool	CommandoSaveLoadClass::Save", "bool	CommandoSaveLoadClass::Load")
        self.assertIn("cGod::Save(csave)", saveload)
        self.assertIn("CampaignManager::Save(csave)", saveload)
        end_game = body(read("staging/commando/gameinitmgr.cpp"),
            "GameInitMgrClass::End_Game (void)", "ModPackageMgrClass::Unload_Current_Mod ();")
        self.assertLess(end_game.index("cGod::Store_Inventory( COMBAT_STAR );"),
            end_game.index("cGod::Reset();"))
        god = read("staging/commando/god.cpp")
        self.assertIn("if ( The_Game()->Remember_Inventory() ) {", god)
        self.assertIn("cGod::Restore_Inventory( p_soldier );", god)
        self.assertIn("Remember_Inventory( void )	const				{ return true; }",
            read("staging/commando/gdsingleplayer.h"))
        runtime = read("port/platform/vita/a31_vita_runtime.cpp")
        self.assertIn("if (!multiplayer_client) cGod::Think();", runtime)
        self.assertIn("GameInitMgrClass::Initialize_SP();", runtime)

    def test_loaded_autosave_validates_campaign_position(self):
        runtime = read("port/platform/vita/a31_vita_runtime.cpp")
        self.assertIn("!CampaignManager::Loaded_Save_State_Matches_Archive(selected_archive)", runtime)
        campaign = read("staging/commando/campaign.cpp")
        matches = body(campaign, "bool CampaignManager::Loaded_Save_State_Matches_Archive",
            "void	CampaignManager::Shutdown")
        self.assertIn("return Current_Level_Matches_Archive(archive);", matches)
        load = body(read("staging/commando/dlgloadspgame.cpp"),
            "LoadSPGameMenuClass::Load_Game (void)", "LoadSPGameMenuClass::On_ListCtrl_Sel_Change")
        self.assertLess(load.index("GameInitMgrClass::Start_Game (save_name, -1, 0);"),
            load.rindex("cGod::Reset_Inventory();"))


if __name__ == "__main__":
    unittest.main()
