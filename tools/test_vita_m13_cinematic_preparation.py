from pathlib import Path

from tools import renegade_cinematic_dependency_scan as scan_tool


ROOT = Path(__file__).resolve().parents[1]
A31_RUNTIME = ROOT / "port" / "platform" / "vita" / "a31_vita_runtime.cpp"
AGG_DEF = ROOT / "staging" / "ww3d2" / "agg_def.cpp"
HLOD = ROOT / "staging" / "ww3d2" / "hlod.cpp"
TEST_CINEMATIC = ROOT / "staging" / "scripts" / "Test_Cinematic.cpp"
SCAN_TOOL = ROOT / "tools" / "renegade_cinematic_dependency_scan.py"
GAMEOBJ_MANAGER = ROOT / "staging" / "combat" / "gameobjmanager.cpp"


def test_m13_intro_sniper_is_prepared_during_loading():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    prepare_block = text[text.index("const char *const prepare_models[]"):]
    assert '"ag_fiery_ex06"' in prepare_block


def test_m13_intro_real_object_render_models_are_prepared_during_loading():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    prepare_block = text[text.index("const char *const prepare_models[]"):]
    assert '"X00_AG_Explode"' in prepare_block


def test_m13_intro_inventory_keeps_runtime_gap_honest():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    scan_text = SCAN_TOOL.read_text(encoding="utf-8")
    assert "runtime_preparation_scope" in scan_text
    assert "A31_Prepare_M13_HAnim" not in text
    assert '"S_A_Human.H_A_X00_Havoc"' not in text
    assert '"X00_CAMERA.X00_CAMERA"' not in text


def test_m13_intro_keeps_packageable_narrow_prepare_hook():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    assert "after_m13_model_prepare" in text
    assert "A4 M13 warmed preparation" in text
    assert '"X0Z_Effects"' in text
    assert '"v_Nod_cplane"' in text


def test_m01_beach_aircraft_are_prepared_during_loading():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    m01_block = text[text.index('stricmp(selected_archive, "M01.mix") == 0'):]
    assert "after_m01_model_prepare" in m01_block
    assert "A4 M01 warmed preparation" in m01_block
    assert '"v_Nod_cplane"' in m01_block
    assert '"v_GDI_trnspt"' in m01_block
    assert '"v_nod_Apache"' in m01_block
    assert '"X1G_A-10_Traj"' in m01_block
    assert '"XG_EV5_rope"' in m01_block


def test_campaign_prepare_does_not_reuse_live_volatile_render_objects():
    text = A31_RUNTIME.read_text(encoding="utf-8")
    surface = (ROOT / "staging" / "combat" / "surfaceeffects.cpp").read_text(encoding="utf-8")
    bullet = (ROOT / "staging" / "combat" / "bullet.cpp").read_text(encoding="utf-8")
    phys = (ROOT / "staging" / "wwphys" / "phys.cpp").read_text(encoding="utf-8")
    assert "A35_Vita_Warm_Render_Obj" in text
    assert "object->Release_Ref();" in text
    assert "A35_Vita_Take_Prepared_Render_Obj" not in surface
    assert "A35_Vita_Take_Prepared_Render_Obj" not in bullet
    assert "A35_Vita_Take_Prepared_Render_Obj(model_type_name)" not in phys


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
