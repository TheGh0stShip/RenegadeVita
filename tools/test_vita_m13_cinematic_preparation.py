from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
A31_RUNTIME = ROOT / "port" / "platform" / "vita" / "a31_vita_runtime.cpp"
AGG_DEF = ROOT / "staging" / "ww3d2" / "agg_def.cpp"
HLOD = ROOT / "staging" / "ww3d2" / "hlod.cpp"
TEST_CINEMATIC = ROOT / "staging" / "scripts" / "Test_Cinematic.cpp"
SCAN_TOOL = ROOT / "tools" / "renegade_cinematic_dependency_scan.py"


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
    assert "A4 M13 retained preparation" in text


def test_m13_dependency_scanner_has_mission_inventory_mode():
    text = SCAN_TOOL.read_text(encoding="utf-8")
    assert "def mission_inventory" in text
    assert "def chunk_inventory" in text
    assert "def walk_chunks" in text
    assert "binary_inventory" in text
    assert "--mission-inventory" in text
    assert "data_scripts_without_source_declare_name_match" in text
    assert "LDD/LSD binary inventory records chunk structure only" in text
    assert "--quiet" in text


def test_m13_intro_slow_unmapped_slots_are_traced():
    text = TEST_CINEMATIC.read_text(encoding="utf-8")
    assert "slot == 18" in text
    assert "slot == 37" in text
    assert "A4 M13 real object create" in text
    assert "A4 M13 cinematic object model" in text


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
