import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class MissionConversationDiagnosticsContractTests(unittest.TestCase):
    def test_diagnostics_observe_original_owner_without_advancing_it(self):
        patch = (ROOT / "port/patches/combat-a35-conversation-diagnostics.patch").read_text()
        policy = (ROOT / "port/platform/a31_gameplay_boundary.cpp").read_text()
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text()
        self.assertIn("Peek_Active_Conversation_For_Diagnostics", patch)
        self.assertIn("Get_Current_Remark_For_Diagnostics", patch)
        self.assertIn("Get_Next_Remark_Seconds_For_Diagnostics", patch)
        self.assertIn("Peek_Current_Sound_For_Diagnostics", patch)
        self.assertIn("Peek_Current_Speech_For_Diagnostics", patch)
        self.assertIn("Peek_Active_Conversation_For_Diagnostics(0)", policy)
        self.assertIn("active_conversation_current_remark", runtime)
        self.assertIn("active_conversation_text_id", runtime)
        self.assertIn("active_conversation_sound_id", runtime)
        self.assertIn("active_conversation_speech_culled", runtime)
        self.assertIn("active_conversation_speech_listener_distance", runtime)
        self.assertIn("DefinitionMgrClass::Find_Definition", policy)
        self.assertNotIn("Stop_Conversation", policy[policy.index("A31MissionProgressState A31_Interactive_Get_Mission_Progress_State"):])

    def test_mission_progress_logs_original_speech_culling_state(self):
        policy = (ROOT / "port/platform/a31_gameplay_boundary.cpp").read_text()
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text()
        shared_policy = (ROOT / "port/platform/a31_interactive_runtime_policy.h").read_text()
        progress = policy[
            policy.index("A31MissionProgressState A31_Interactive_Get_Mission_Progress_State"):
            policy.index("void A31_Interactive_Run_Simulation_Frame")
        ]
        helper = policy[
            policy.index("AudibleSoundClass *Find_Conversation_Speech_For_Diagnostics"):
            policy.index("class A31VitaCombatMiscHandler")
        ]
        log_start = runtime.index('A30_Vita_Log("A3.5 mission progress:')
        log_end = runtime.index("trace.player_x", log_start)
        log_block = runtime[log_start:log_end]

        for token in (
            "active_conversation_speech_source",
            "active_conversation_speech_class_id",
            "active_conversation_speech_state",
            "active_conversation_speech_duration_ms",
            "active_conversation_speaker_available",
            "active_conversation_speech_available",
            "active_conversation_speech_in_scene",
            "active_conversation_speech_culled",
            "active_conversation_speech_playing",
            "active_conversation_speech_dropoff_radius",
            "active_conversation_speech_listener_distance",
        ):
            self.assertIn(token, shared_policy)
            self.assertIn(token, policy)

        self.assertIn("Fill_Conversation_Speech_Diagnostics(active, &state)", progress)
        self.assertIn("Peek_Current_Speech_For_Diagnostics", helper)
        self.assertIn("Peek_Current_Sound_For_Diagnostics", helper)
        self.assertIn("Get_Listener_Position", helper)
        self.assertIn("Quick_Length", helper)
        self.assertIn(
            "speech=speaker:%d src:%d present/scene/culled/playing=%d/%d/%d/%d",
            log_block,
        )
        self.assertIn("dur/dropoff/dist=%u/%.3f/%.3f", log_block)
        self.assertNotIn("Play(", progress)

    def test_direct_render_restores_original_message_window_pass(self):
        policy = (ROOT / "port/platform/a31_gameplay_boundary.cpp").read_text()
        render = policy[
            policy.index("A31InteractiveRenderTrace A31_Interactive_Run_Render_Frame"):
            policy.index("// Text display is an optional presentation mode.")
        ]
        combat = render.index("CombatManager::Render();")
        message = render.index("message_window->Render();", combat)
        objective = render.index("ObjectiveManager::Render_Viewer();", message)
        end = render.index("WW3D::End_Render(true)", objective)
        self.assertLess(combat, message)
        self.assertLess(message, objective)
        self.assertLess(objective, end)

    def test_direct_m00_links_translate_db_object_factories(self):
        manifest = (ROOT / "cmake" / "A31OriginalSources.cmake").read_text()
        tdb_category = manifest.index("wwtranslatedb/tdbcategory.cpp")
        tdb_object = manifest.index("wwtranslatedb/translateobj.cpp", tdb_category)
        tdb_database = manifest.index("wwtranslatedb/translatedb.cpp", tdb_object)
        tdb_twiddler = manifest.index("wwtranslatedb/stringtwiddler.cpp", tdb_database)
        audio_events = manifest.index("wwaudio/AudioEvents.cpp", tdb_twiddler)
        self.assertLess(tdb_category, tdb_object)
        self.assertLess(tdb_object, tdb_database)
        self.assertLess(tdb_database, tdb_twiddler)
        self.assertLess(tdb_twiddler, audio_events)

    def test_world_render_availability_is_independent_from_deferred_hud(self):
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text()
        self.assertIn("CombatManager::Init(render_hud);", runtime)
        self.assertIn("CombatManager::Pre_Load_Level(true);", runtime)
        self.assertNotIn("CombatManager::Pre_Load_Level(false);", runtime)

    def test_deferred_dazzle_layer_does_not_reject_original_sky_scene(self):
        patch = (ROOT / "port/patches/ww3d2-a22-vita-boundaries.patch").read_text()
        dazzle_start = patch.index("void DazzleRenderObjClass::Render")
        dazzle_end = patch.index("void DazzleRenderObjClass::Render_Dazzle", dazzle_start)
        dazzle_render = patch[dazzle_start:dazzle_end]
        self.assertIn("absent optional presentation layer is a bounded", dazzle_render)
        self.assertNotIn("Submit_Unsupported", dazzle_render)

    def test_direct_m00_activates_and_services_original_wwaudio(self):
        entry = (ROOT / "port/platform/vita/a30_main.cpp").read_text()
        runtime = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text()

        chain = runtime.index("_TheFileFactory = &factory_list;")
        adapter = runtime.index("A31AudioFileFactoryClass audio_file_factory(&factory_list);", chain)
        construction = runtime.index("WWAudioClass application_audio(false);", adapter)
        initialization = runtime.index("application_audio.Initialize();", construction)
        file_factory = runtime.index(
            "application_audio.Set_File_Factory(&audio_file_factory);", initialization
        )
        engine = runtime.index("CombatManager::Init(render_hud);", file_factory)
        self.assertLess(chain, adapter)
        self.assertLess(adapter, construction)
        self.assertLess(construction, initialization)
        self.assertLess(initialization, file_factory)
        self.assertLess(file_factory, engine)
        self.assertIn(
            "class A31AudioFileFactoryClass final : public SimpleFileFactoryClass",
            runtime,
        )
        self.assertIn("Strip_Path_From_Filename(stripped, filename);", runtime)
        adapter_source = runtime[
            runtime.index("class A31AudioFileFactoryClass") : runtime.index(
                "bool Load_Strings_Database_For_Loading_Screen"
            )
        ]
        self.assertNotIn("Return_File", adapter_source)
        self.assertNotIn("WWAudioClass application_audio(true);", entry + runtime)
        self.assertIn("WWAudioClass::Get_Instance() == NULL", entry)
        audio_teardown = runtime.index(
            "application audio teardown complete singleton=%p", engine
        )
        asset_teardown = runtime.index(
            "if (asset_manager != NULL) WW3DAssetManager::Delete_This();",
            audio_teardown,
        )
        factory_restore = runtime.index(
            "_TheFileFactory = previous_read_factory;", asset_teardown
        )
        self.assertLess(audio_teardown, asset_teardown)
        self.assertLess(asset_teardown, factory_restore)

        simulation = runtime.index("A31_Interactive_Run_Simulation_Frame();")
        suspended = runtime.index("if (is_suspended) {", simulation)
        suspended_update = runtime.index("audio->On_Frame_Update(0);", suspended)
        suspended_continue = runtime.index("continue;", suspended_update)
        render = runtime.index("A31_Interactive_Run_Render_Frame();", suspended_continue)
        active_update = runtime.index("audio->On_Frame_Update(0);", render)
        self.assertLess(suspended_update, suspended_continue)
        self.assertLess(render, active_update)
        self.assertIn("audio->Get_2D_Driver() == NULL", runtime)
        self.assertIn("audio->Get_3D_Driver() == 0U", runtime)

    def test_vita_audio_constructor_initializes_dialogue_volumes_without_registry(self):
        staged = (ROOT / "staging" / "wwaudio" / "WWAudio.cpp").read_text()
        fallback = (ROOT / "port" / "platform" / "a31_gameplay_boundary.cpp").read_text()
        patch = (ROOT / "port" / "patches" / "wwaudio-a35-posix-runtime.patch").read_text()

        for source in (staged, fallback, patch):
            self.assertIn("m_DialogVolume", source)
            self.assertIn("DEF_DIALOG_VOL", source)
            self.assertIn("m_CinematicVolume", source)
            self.assertIn("DEF_CINEMATIC_VOL", source)

    def test_audio_runtime_diagnostics_include_dialogue_volume(self):
        runtime = (ROOT / "port" / "platform" / "vita" / "a31_vita_runtime.cpp").read_text()
        log_start = runtime.index('A30_Vita_Log("A3.5 audio:')
        log_end = runtime.index("stats.last_error[0]", log_start)
        log_block = runtime[log_start:log_end]

        self.assertIn("volumes_dialog/cinematic=%.3f/%.3f", log_block)
        self.assertIn("stream_mix=buffers:%llu frames:%llu nonzero:%llu peak:%u", log_block)
        self.assertIn("allocated/active/streams=%u/%u/%u", log_block)
        self.assertIn("audio->Get_Dialog_Volume()", runtime)
        self.assertIn("audio->Get_Cinematic_Volume()", runtime)
        self.assertIn("stats.stream_mixed_nonzero_buffers", log_block)
        self.assertIn("stats.active_streams", log_block)
        self.assertEqual(log_block.count("stats.sample_start_silent"), 1)

    def test_conversation_think_removes_same_pointer_after_script_callbacks(self):
        patch = (ROOT / "port/patches/combat-a35-conversation-reentrant-think.patch").read_text()
        staged = (ROOT / "staging" / "combat" / "conversationmgr.cpp").read_text()
        stage_sources = (ROOT / "tools" / "stage_sources.sh").read_text()

        for source in (patch, staged):
            self.assertIn("active_conversation->Add_Ref ();", source)
            self.assertIn("ActiveConversationList[remove_index] == active_conversation", source)
            self.assertIn("Do not delete a newly chained conversation by using a stale index.", source)
        self.assertIn("combat-a35-conversation-reentrant-think.patch", stage_sources)


if __name__ == "__main__":
    unittest.main()
