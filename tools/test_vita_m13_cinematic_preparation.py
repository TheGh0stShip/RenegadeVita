from pathlib import Path
import unittest
import subprocess
import tempfile

from tools import renegade_cinematic_dependency_scan as scan_tool


ROOT = Path(__file__).resolve().parents[1]
A31_RUNTIME = ROOT / "port" / "platform" / "vita" / "a31_vita_runtime.cpp"
AGG_DEF = ROOT / "staging" / "ww3d2" / "agg_def.cpp"
HLOD = ROOT / "staging" / "ww3d2" / "hlod.cpp"
TEST_CINEMATIC = ROOT / "staging" / "scripts" / "Test_Cinematic.cpp"
SCAN_TOOL = ROOT / "tools" / "renegade_cinematic_dependency_scan.py"
GAMEOBJ_MANAGER = ROOT / "staging" / "combat" / "gameobjmanager.cpp"
PATH_ACTION = ROOT / "staging" / "combat" / "pathaction.cpp"
ANIM_COLLISION = ROOT / "staging" / "wwphys" / "animcollisionmanager.cpp"


def test_m13_intro_sniper_is_prepared_during_loading():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    prepare_block = text[text.index("const A35PreparedMissionModel prepare_models[]"):]
    assert '"ag_fiery_ex06"' in prepare_block


def test_m13_intro_real_object_render_models_are_prepared_during_loading():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    prepare_block = text[text.index("const A35PreparedMissionModel prepare_models[]"):]
    assert '"X00_AG_Explode"' in prepare_block
    assert '"X0F_AG_EFFECTS", true' in prepare_block
    assert '"X0D_AG_Explode", true' in prepare_block


def test_m13_intro_prepares_authored_rappel_and_engineer_animations():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    scan_text = SCAN_TOOL.read_text(encoding="utf-8")
    assert "runtime_preparation_scope" in scan_text
    assert '"X00_Havoc_Traj.X00_Havoc_Traj"' in text
    assert '"S_A_Human.H_A_X00_Havoc"' in text
    assert '"X00_Rope.X00_Rope"' in text
    assert '"S_A_Human.H_A_X00_ENG1"' in text
    assert '"S_A_Human.H_A_X00_ENG2"' in text
    assert '"S_A_Human.H_A_X00_Walk_02"' in text
    assert "Get_HAnim(intro_animations[i])" in text
    assert '"X00_CAMERA.X00_CAMERA"' not in text


def test_m13_intro_keeps_packageable_narrow_prepare_hook():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    assert "after_m13_model_prepare" in text
    assert "A4 M13 %s preparation" in text
    assert '"X0Z_Effects"' in text
    assert '"v_Nod_cplane"' in text


def test_m01_beach_aircraft_are_prepared_during_loading():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    m01_block = text[text.index('\tif (m01) {'):]
    assert "after_m01_model_prepare" in m01_block
    assert "A4 M01 %s preparation" in m01_block
    assert '"v_Nod_cplane"' in m01_block
    assert '"v_GDI_trnspt"' in m01_block
    assert '"v_nod_Apache"' in m01_block
    assert '"X1G_A-10_Traj"' in m01_block
    assert '"XG_EV5_rope"' in m01_block


def test_m01_finale_assets_are_prepared_during_loading():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    m01_block = text[text.index('\tif (m01) {'):]
    # Generic per-level preparation warms cinematic Create_Real_Object presets
    # and Play_Animation names (X1Z_Finale.txt included); the one finale
    # Create_Object model it cannot discover is listed explicitly.
    assert '"o_crate_sm"' in m01_block
    assert "Parse_Cinematic_Play_Animation_Name(line, animation)" in text
    assert "Warm_Level_Cinematic_Preset_Models(presenter, archive, root_factory);" in text


def test_m01_referenced_textures_prepare_before_first_world_frame():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    m01_block = text[text.index('\tif (m01) {'):]
    assert 'Warm_Original_Campaign_Referenced_Textures(presenter, label)' in m01_block
    prepare_call = text.index('Prepare_Original_Level_Loading_Resources(loading_presenter,\n\t\t\t\tselected_archive')
    assert prepare_call < text.index('A3.1 breadcrumb: original M00 level loaded', prepare_call)
    # The 48 MiB budget is now the retained minimum of a pool-headroom-scaled
    # budget (Select_Campaign_Texture_Prepare_Budget, clamped 48..96 MiB).
    assert 'const uint64_t base_budget = 48ULL * 1024ULL * 1024ULL;' in text
    assert 'Select_Campaign_Texture_Prepare_Budget(' in text
    assert 'if (budget < base_budget) budget = base_budget;' in text


def test_saved_path_action_remaps_borrowed_pointers_without_new_references():
    text = PATH_ACTION.read_text(encoding="utf-8")
    load = text[text.index('PathActionClass::Load_Variables'):text.index('PathActionClass::Set_Ladder_Occupant')]
    assert 'REQUEST_POINTER_REMAP ((void **)&Mechanism)' in load
    assert 'REQUEST_POINTER_REMAP ((void **)&Path)' in load
    assert 'REQUEST_REF_COUNTED_POINTER_REMAP' not in load
    driver = (ROOT / "staging/combat/vehicledriver.cpp").read_text(encoding="utf-8")
    assert 'REQUEST_POINTER_REMAP ((void **)&m_CurrentPath)' in driver
    assert 'REQUEST_REF_COUNTED_POINTER_REMAP ((RefCountClass **)&m_CurrentPath)' not in driver


def test_loaded_previous_animation_releases_lookup_reference():
    text = ANIM_COLLISION.read_text(encoding="utf-8")
    load = text[text.index('bool AnimCollisionManagerClass::Load('):]
    previous = load[load.index('Get_HAnim(prev_anim_name)'):load.index('return true;')]
    assert previous.index('REF_PTR_SET(PrevAnimation,anim)') < previous.index('REF_PTR_RELEASE(anim)')


def test_decal_removal_releases_the_complete_offset_range():
    text = (ROOT / "staging/ww3d2/decalmsh.cpp").read_text(encoding="utf-8")
    assert text.count('fi<decal->FaceStartIndex + decal->FaceCount') == 1
    assert text.count('fi < decal->FaceStartIndex + decal->FaceCount') == 1
    assert text.count('vi<decal->VertexStartIndex + decal->VertexCount') == 2


def test_campaign_cinematic_dispatch_completes_authored_due_batch():
    text = TEST_CINEMATIC.read_text(encoding="utf-8")
    assert 'vita_budget_command_count' not in text
    assert 'Vita_Is_Budgeted_Campaign_Cinematic' not in text
    start = text.index('\tvoid\tParse_Commands( GameObject* obj ) {')
    end = text.index('\n\t/*', start)
    method = text[start:end]
    fixture = r'''
    #include <cstdlib>
    struct GameObject {};
    struct Provider {
        unsigned tick=0; int timers=0, destroyed=0, freeze=0; float delay=0;
        unsigned Get_Sync_Time() { return tick; }
        int Get_ID(GameObject*) { return 1; }
        template<class T> void Start_Timer(GameObject*,T*,float d,int) { ++timers; delay=d; }
        void Destroy_Object(GameObject*) { ++destroyed; }
        void Enable_Cinematic_Freeze(GameObject*,bool on) { if(on) std::abort(); ++freeze; }
    } provider;
    Provider *Commands=&provider;
    struct Cinematic {
        struct ControlLine { float Time; const char *Command; ControlLine *Next; };
        static constexpr float LAST_VALID_TIMESTAMP=999999;
        unsigned LastSyncTime=0; float Time=0, FrameSync=0;
        int MyID=0, executed=0; bool PrimaryKilled=false, IsCameraCinematic=false;
        ControlLine *Controls=nullptr;
        void Remove_Head_Control_Line() { Controls=Controls->Next; }
        void Parse_Command(const char *command) {
            if (command[0] != '0'+executed) std::abort();
            ++executed; if(executed==3) IsCameraCinematic=true;
        }
    ''' + method + r'''
    };
    int main() {
        GameObject obj; Cinematic c;
        Cinematic::ControlLine lines[]={{0,"0",nullptr},{0,"1",nullptr},{0,"2",nullptr},{0,"3",nullptr},{1,"4",nullptr}};
        for(int i=0;i<4;++i) lines[i].Next=&lines[i+1];
        c.Controls=lines; c.Parse_Commands(&obj);
        if(c.executed!=4 || provider.timers!=1 || provider.delay!=1 || !c.IsCameraCinematic || provider.freeze!=1) return 1;
        provider.tick=1500; c.Parse_Commands(&obj);
        if(c.executed!=5 || provider.destroyed!=1 || c.Controls || c.FrameSync!=15) return 2;
    }
    '''
    with tempfile.TemporaryDirectory(prefix="renegade-cinematic-dispatch-") as temporary:
        cpp=Path(temporary)/"dispatch.cpp"; binary=Path(temporary)/"dispatch"
        cpp.write_text(fixture)
        subprocess.run(["g++","-std=c++17","-Wall","-Wextra","-Werror",str(cpp),"-o",str(binary)],check=True)
        subprocess.run([str(binary)],check=True)


def test_campaign_prepare_does_not_reuse_live_volatile_render_objects():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    surface = (ROOT / "staging" / "combat" / "surfaceeffects.cpp").read_text(encoding="utf-8")
    bullet = (ROOT / "staging" / "combat" / "bullet.cpp").read_text(encoding="utf-8")
    phys = (ROOT / "staging" / "wwphys" / "phys.cpp").read_text(encoding="utf-8")
    assert "A35_Vita_Warm_Render_Obj" in text
    assert "object->Release_Ref();" in text
    assert "A35_Vita_Retain_Prepared_Render_Obj(name)" in text
    assert "A35_Vita_Take_Prepared_Render_Obj(model_type_name)" in phys
    assert "source=%s create_us" in phys
    assert "A35_Vita_Take_Prepared_Render_Obj" not in surface
    assert "A35_Vita_Take_Prepared_Render_Obj" not in bullet


def test_retained_cinematic_models_allow_duplicate_pool_slots():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    retain_body = text[
        text.index("bool A35_Vita_Retain_Prepared_Render_Obj") :
        text.index("bool A35_Vita_Warm_Render_Obj")
    ]
    assert "stricmp" not in retain_body
    assert "g_A35PreparedRenderObjects[i].object == NULL" in retain_body
    assert "break;" in retain_body
    assert '"X0F_AG_EFFECTS", true, 2U' in text
    assert '"X0D_AG_Explode", true, 2U' in text


def test_m13_dependency_scanner_has_mission_inventory_mode():
    text = SCAN_TOOL.read_text(encoding="utf-8")
    assert "def mission_inventory" in text
    assert "def chunk_inventory" in text
    assert "def source_chunk_inventory" in text
    assert "def walk_chunks" in text
    assert "binary_inventory" in text
    assert "source_chunk_inventory" in text
    assert "SimplePersistFactoryClass" in text
    assert "--mission-inventory" in text
    assert "data_scripts_without_source_declare_name_match" in text
    assert "LDD/LSD binary inventory records chunk structure only" in text
    assert "--quiet" in text


def test_m13_chunk_scanner_resolves_original_save_load_owners():
    inventory = scan_tool.source_chunk_inventory(ROOT)
    by_value = inventory["symbol_inventory"]["by_value"]
    assert inventory["level_chunks"]["0x3c51c460"] == "CHUNKID_LEVEL_INFO"
    assert inventory["level_chunks"]["0x3c51c461"] == "CHUNKID_LEVEL_DATA"
    assert "PHYSICS_CHUNKID_STATIC_DATA_SUBSYSTEM" in by_value["0x00020000"]
    assert "PHYSICS_CHUNKID_STATIC_OBJECTS_SUBSYSTEM" in by_value["0x00020001"]
    assert "CHUNKID_DYNAMIC_SAVELOAD" in by_value["0x00030006"]
    assert "CHUNKID_COMBAT" in by_value["0x00040000"]
    assert inventory["simple_factory_internal_chunks"]["0x00100101"] == "SIMPLEFACTORY_CHUNKID_OBJDATA"
    factories = inventory["persist_factories"]["by_chunk_id"]["0x0004010e"]
    assert any(factory["class"] == "SoldierGameObj" for factory in factories)


def test_m13_chunk_inventory_records_persist_factory_counts():
    text = SCAN_TOOL.read_text(encoding="utf-8")
    assert "persist_factory_chunk_counts" in text
    assert "persist_factory_counts" in text


def test_m13_runtime_object_summary_is_bounded_at_original_loader():
    text = GAMEOBJ_MANAGER.read_text(encoding="utf-8")
    assert "Vita_Log_GameObj_Load_Summary" in text
    assert "GameObjManager::Load" in text
    assert "A4 mission object summary" in text
    assert "A4 mission object sample" in text
    assert "samples < 24U" in text
    assert "Get_Observers().Count()" in text
    assert "observer_objects" not in text


def test_m13_intro_slow_unmapped_slots_are_traced():
    text = TEST_CINEMATIC.read_text(encoding="utf-8")
    assert "slot == 18" in text
    assert "slot == 37" in text
    assert "A4 M13 real object create" in text
    assert "A4 M13 cinematic object model" in text
    assert "A4 slow campaign cinematic command" in text
    assert 'strnicmp(vita_control_filename, "X1", 2) == 0' in text


def test_m13_real_object_library_phases_are_traced():
    text = (ROOT / "staging" / "combat" / "objlibrary.cpp").read_text(encoding="utf-8")
    assert "A4 M13 object library create" in text
    assert 'stricmp(name, "gdi_rocketsoldier_0") == 0' in text
    assert 'stricmp(name, "gdi_transport_helicopter_NoAudio") == 0' in text
    assert 'stricmp(name, "GDI_ENGINEER_0") == 0' in text
    assert 'stricmp(name, "GDI_Engineer_0_B") == 0' in text


def test_m13_intro_sniper_aggregate_is_retained():
    text = AGG_DEF.read_text(encoding="utf-8")
    assert '{"c_ag_nod_sniper", NULL, NULL}' in text
    assert "A4 M13 aggregate template clone" in text


def test_generic_slow_asset_logger_is_not_in_runtime_candidate():
    text = (ROOT / "staging" / "ww3d2" / "assetmgr.cpp").read_text(encoding="utf-8")
    assert "A4 slow WW3D create" not in text


def test_existing_m13_fiery_hlod_template_is_preserved():
    text = HLOD.read_text(encoding="utf-8")
    assert 'stricmp(Definition->Get_Name(), "ag_fiery_ex06") == 0' in text
    assert "s_vita_m13_fiery_hlod_model->Clone();" in text


def test_tracked_vehicle_accepts_direct_track_mesh_names():
    text = (ROOT / "staging" / "wwphys" / "trackedvehicle.cpp").read_text(encoding="utf-8")
    stage = (ROOT / "tools" / "stage_sources.sh").read_text(encoding="utf-8")
    assert "Some retail W3D hierarchies expose the track mesh name directly" in text
    assert text.count("sub_name = name;") == 2
    assert "TRACKL" in text and "TRACKR" in text
    assert "wwphys-a35-trackedvehicle-mesh-names.patch" in stage


def test_vita_hud_rejects_invalid_target_projection():
    text = (ROOT / "staging" / "combat" / "hud.cpp").read_text(encoding="utf-8")
    stage = (ROOT / "tools" / "stage_sources.sh").read_text(encoding="utf-8")
    assert "if (!projected_top.Is_Valid() || !projected_bottom.Is_Valid())" in text
    assert "combat-a35-hud-target-box-nan-guard.patch" in stage


def test_preservation_patch_cannot_restore_per_object_postthink_timing():
    stage = (ROOT / "tools" / "stage_sources.sh").read_text(encoding="utf-8")
    restore = (ROOT / "tools" / "restore_postthink_sampler.py").read_text(encoding="utf-8")
    preserve = stage.index('a35-dev190-staging-preserve.patch"')
    sampler = stage.index("restore_postthink_sampler.py")
    receipt = stage.index("--write-staging-receipt", sampler)
    staged = GAMEOBJ_MANAGER.read_text(encoding="utf-8")
    assert preserve < sampler < receipt
    assert "def replace_once" in restore
    assert 'text.count(before) != 1' in restore
    assert "vita_sampled_object_count" in staged
    assert "(vita_object_count++ & 15U) == vita_sample_offset" in staged
    assert "sampled=%u stride=16" in staged
    post_think = staged[staged.index("int\tGameObjManager::Post_Think()"):]
    post_think = post_think[:post_think.index("\n}")]
    assert "const uint64_t vita_object_start_us = sceKernelGetProcessTimeWide();" not in post_think
    assert "const uint64_t vita_object_start_us = vita_sample_object ?" in post_think


def test_m01_first_beach_cinematic_uses_fresh_volatile_render_objects():
    runtime = A31_RUNTIME.read_text(encoding="utf-8")
    for model in ("vxag_nod_heli", "VxAG_X1Borca", "X1c_AG_xplosion", "X1C_AG_Missile"):
        assert f'{{ "{model}", false, 2U }}' in runtime


class RuntimeInstrumentationContracts(unittest.TestCase):
    def test_raw_animation_samplers_use_portable_lower_key(self):
        text = (ROOT / "staging" / "ww3d2" / "hrawanim.cpp").read_text(encoding="utf-8")
        self.assertEqual(text.count("int frame0 = static_cast<int>(WWMath::Floor(frame));"), 3)
        self.assertNotIn("WWMath::Float_To_Long(frame-0.499999f)", text)

    def test_preservation_patch_cannot_restore_per_object_postthink_timing(self):
        test_preservation_patch_cannot_restore_per_object_postthink_timing()

    def test_m01_first_beach_cinematic_uses_fresh_volatile_render_objects(self):
        test_m01_first_beach_cinematic_uses_fresh_volatile_render_objects()

    def test_m01_referenced_textures_prepare_before_first_world_frame(self):
        test_m01_referenced_textures_prepare_before_first_world_frame()

    def test_saved_path_action_remaps_borrowed_pointers_without_new_references(self):
        test_saved_path_action_remaps_borrowed_pointers_without_new_references()

    def test_loaded_previous_animation_releases_lookup_reference(self):
        test_loaded_previous_animation_releases_lookup_reference()

    def test_decal_removal_releases_the_complete_offset_range(self):
        test_decal_removal_releases_the_complete_offset_range()

    def test_campaign_cinematic_dispatch_completes_authored_due_batch(self):
        test_campaign_cinematic_dispatch_completes_authored_due_batch()


def test_vita_texture_transform_boundary_caches_identical_mapper_state():
    text = (ROOT / "port" / "renderer" / "vita" / "ww3d_dx8_boundary.cpp").read_text(encoding="utf-8")
    assert "g_applied_texture_transform_valid" in text
    assert "memcmp(&g_applied_texture_transforms[stage]" in text
    assert "g_applied_texture_transform_flags[stage]" in text
