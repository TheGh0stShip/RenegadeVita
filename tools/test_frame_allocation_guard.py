"""Static guard: port-owned per-frame and per-draw paths stay heap-allocation free.

Pure Python. Nothing is compiled or executed. Each guarded function is
extracted by its exact signature text (a missing signature fails, so a rename
forces this list to be reviewed) and scanned, with comments and string
literals removed, for constructs that take newlib's global malloc lock:
by-value STL containers, new/malloc family calls, container growth calls,
shrinking Delete_All(), and non-temporary StringClass/WideStringClass locals.
The only exceptions are grow-only scratch sites whose capacity guard must
precede the allocation.

It also checks the RVAL1 (frame-alloc-v1.flag) changes from tutorial round 1:
the bounded texture-creation RGBA scratch and the HUD target-name temp hint.
See reports/tutorial/TUT_R1_FRAME_ALLOCATIONS.md.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RENDERER = "port/renderer/vita/ww3d_vita_renderer.cpp"
BOUNDARY = "port/renderer/vita/ww3d_dx8_boundary.cpp"
GAMEPLAY = "port/platform/a31_gameplay_boundary.cpp"
RUNTIME = "port/platform/vita/a31_vita_runtime.cpp"
FRAME_ALLOC = "port/compatibility/include/renegade_vita_frame_alloc.h"
HUD = "staging/combat/hud.cpp"
HUD_PATCH = "port/patches/combat-tut1-hud-target-name-temp.patch"

# (file, exact signature text). Every function here runs at least once per
# rendered frame, per mesh/batch/draw, or per log line on the tutorial route.
HOT_FUNCTIONS = [
    (RENDERER, "static void Submit_Mesh_Internal(MeshClass &mesh, RenderInfoClass &render_info,"),
    (RENDERER, "void Submit_Mesh(MeshClass &mesh, RenderInfoClass &render_info)\n{"),
    (RENDERER, "IndexedSubmissionResult Submit_Indexed_Triangles(\n"),
    (RENDERER, "static void Draw_Vertex_Array_Batch(VitaVertexArrayBatch &batch, bool texture0,"),
    (RENDERER, "void Replay_Static_Mesh_Entry(const StaticMeshEntry &entry)\n{"),
    (RENDERER, "void End_Frame(bool present)\n{"),
    (RENDERER, "bool Begin_Material_Color_Pass(int vertex_count)\n{"),
    (RENDERER, "bool Ensure_Deformed_Skin_Scratch(int vertex_count)\n{"),
    (RENDERER, "MaterialVertexColor Evaluate_Original_Material_Vertex_Color("),
    (RENDERER, "void Apply_Original_Shader_State(const ShaderClass &shader)\n{"),
    (RENDERER, "bool Bind_Texture_Stage(uint32_t stage, uint32_t native_texture, bool valid)\n{"),
    (RENDERER, "void Apply_Platform_Texture_Stage(TextureClass &texture, unsigned stage)\n{"),
    (RENDERER, "bool Apply_DX8_Render_State(uint32_t state, uint32_t value)\n{"),
    (RENDERER, "void Sample_VitaGL_Transient_Pools(uint32_t frame)\n{"),
    (BOUNDARY, "void Submit_Bound_Triangles(const RenderStateStruct &state,"),
    (BOUNDARY, "void DX8Wrapper::Apply_Render_State_Changes()\n{"),
    (BOUNDARY, "void DX8Wrapper::Set_Vertex_Buffer(const VertexBufferClass *vertex_buffer)\n{"),
    (BOUNDARY, "void DX8Wrapper::Set_Index_Buffer(const IndexBufferClass *index_buffer,"),
    (BOUNDARY, "void DX8Wrapper::Set_Vertex_Buffer(const DynamicVBAccessClass &access_const)\n{"),
    (BOUNDARY, "void DX8Wrapper::Set_Index_Buffer(const DynamicIBAccessClass &access_const,"),
    (BOUNDARY, "void DX8Wrapper::Draw_Sorting_IB_VB(unsigned primitive_type,"),
    (BOUNDARY, "void DX8Wrapper::Draw_Triangles(unsigned buffer_type,"),
    (BOUNDARY, "void DX8Wrapper::Draw_Triangles(unsigned short start_index,"),
    (BOUNDARY, "void DX8Wrapper::Draw_Strip(unsigned short start_index,"),
    (BOUNDARY, "bool Upload_Texture_Level_From_Surface(IDirect3DTexture8 *texture, UINT level)\n{"),
    (GAMEPLAY, "void A31_Interactive_Run_Simulation_Frame()\n{"),
    (GAMEPLAY, "A31InteractiveRenderTrace A31_Interactive_Run_Render_Frame(bool present)\n{"),
    (GAMEPLAY, "A31MissionProgressState A31_Interactive_Get_Mission_Progress_State()\n{"),
    (GAMEPLAY, "void Fill_Conversation_Speech_Diagnostics("),
    (GAMEPLAY, "AudibleSoundClass *Find_Conversation_Speech_For_Diagnostics("),
    (GAMEPLAY, "void A31_Interactive_Apply_Render_Capabilities()\n{"),
    (GAMEPLAY, "static void Sample_Original_Visibility_Census(PhysicsSceneClass &scene,"),
    (RUNTIME, "void Copy_Flight_Memory(A31MemoryTelemetry &output)\n{"),
    (RUNTIME, "void Copy_Renderer_Statistics(A31RendererTelemetry &telemetry)\n{"),
    ("port/platform/vita/a30_vita_runtime.cpp", "int A30_Vita_Log(const char *format, ...)\n{"),
    ("port/platform/vita/vita_platform.cpp", "int Vita_Append_A22_Runtime_Breadcrumb(const char *subsystem,"),
    ("port/platform/vita/vita_platform.cpp", "bool Renegade_Runtime_Log_Enqueue(const char *line, unsigned length)\n{"),
    ("port/platform/renegade_async_log.h", "bool Enqueue(const char *data, unsigned length) {"),
    ("port/platform/vita/renegade_vita_frame_profile.cpp", "ProfileSlot *Find_Slot(const char *name)\n{"),
    ("port/platform/vita/renegade_vita_frame_profile.cpp", "uint64_t Renegade_Frame_Profile_Begin(const char *name)\n{"),
    ("port/platform/vita/renegade_vita_frame_profile.cpp", "void Renegade_Frame_Profile_End(uint64_t token)\n{"),
    ("port/platform/vita/renegade_vita_frame_profile.cpp", "void Renegade_Frame_Profile_End_Frame(uint32_t frame_us)\n{"),
    ("port/developer/a35_campaign_flight_recorder.cpp", "void A35_Campaign_Flight_Record_Frame(const A31FrameTelemetry &frame,"),
    ("port/developer/a35_script_lookup_telemetry.cpp", "void A35_Script_Lookup_Set_Context(A35ScriptLookupPhase phase, uint32_t frame)\n{"),
    ("port/developer/a35_script_lookup_telemetry.cpp", "void A35_Script_Lookup_Record(A35ScriptLookupKind kind, const char *name,"),
    ("port/platform/renegade_directinput.cpp", "void DirectInput::Read(void)\n{"),
    ("port/platform/renegade_directinput.cpp", "void Record_Sample(const SceCtrlData &controller)\n{"),
    ("port/platform/renegade_directinput.cpp", "VitaTouchSample Sample_Touch_Port(int port, bool &sampling_initialized)\n{"),
    ("port/audio/vita/renegade_miles_provider.cpp", "void Apply_Pending_Positions_Locked()\n{"),
    ("port/audio/vita/renegade_miles_provider.cpp", "bool Publish_Pending_Position(RenegadeMilesSample *sample, F32 x, F32 y, F32 z)\n{"),
]

# Grow-only scratch: (signature, allocation text, guard regex). The guard must
# appear in the function before the allocation, so steady state never allocates.
GROW_ONLY = [
    ("bool Ensure_Deformed_Skin_Scratch(int vertex_count)\n{",
     "new (std::nothrow) Vector3[capacity]",
     r"if \(vertex_count <= g_deformed_skin_capacity\) return true;"),
    ("bool Begin_Material_Color_Pass(int vertex_count)\n{",
     "new (std::nothrow) CachedMaterialVertexColor[entry_count]",
     r"if \(entry_count > g_material_color_capacity\) \{"),
    ("void Submit_Bound_Triangles(const RenderStateStruct &state,",
     "expanded_indices.reset(new (std::nothrow) uint16_t[expanded_count]);",
     r"if \(expanded_count > expanded_capacity\) \{"),
]

STL_VALUE = re.compile(
    r"\bstd::(?:vector|basic_string|string|wstring|map|multimap|unordered_map|set|"
    r"unordered_set|list|forward_list|deque|function|ostringstream|stringstream)\b"
    r"(?:\s*<[^;{}]*?>)?\s+(?!&)[A-Za-z_]\w*\s*[({;=]")
FORBIDDEN = [
    ("by-value STL container", STL_VALUE),
    ("new expression", re.compile(r"\bnew\b")),
    ("malloc family", re.compile(r"\b(?:malloc|calloc|realloc|memalign|strdup|strndup)\s*\(")),
    ("container growth", re.compile(
        r"\.(?:push_back|emplace_back|emplace|insert|resize|reserve|assign)\s*\(")),
    ("STL string/owner helper", re.compile(r"\bstd::(?:to_string|make_shared|make_unique)\b")),
    ("shrinking Delete_All", re.compile(r"\bDelete_All\s*\(\s*\)")),
]
STRING_LOCAL = re.compile(r"(?P<prefix>\bstatic\s+)?\b(?:Wide)?StringClass\s+(?!&)(?P<name>[A-Za-z_]\w*)\s*(?P<open>[(=;])")
# Engine value types that own heap storage (a StringClass member or a growable
# array); a per-call local of one allocates on first use every call.
OWNER_LOCAL = re.compile(
    r"(?P<prefix>\bstatic\s+)?\b(?:ConversationRemarkClass|"
    r"(?:DynamicVectorClass|SimpleDynVecClass|VectorClass|SimpleVecClass)\s*<[^;{}]*?>)"
    r"\s+(?!&)[A-Za-z_]\w*\s*[({;=]")


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8", errors="replace")


def strip_comments_and_strings(text):
    """Blank comments and string/char literals, keeping newlines and offsets."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif c == "/" and nxt == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(ch if ch == "\n" else " " for ch in text[i:j]))
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(c + " " * max(0, j - i - 2) + (c if j - i >= 2 else ""))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def function_body(relative, signature):
    """Return (raw, stripped) text of the function starting at signature."""
    text = read(relative)
    start = text.find(signature)
    if start < 0:
        raise AssertionError(f"{relative}: signature not found: {signature!r}")
    if text.find(signature, start + 1) >= 0:
        raise AssertionError(f"{relative}: signature is ambiguous: {signature!r}")
    stripped = strip_comments_and_strings(text)
    brace = stripped.find("{", start + len(signature.rstrip("{")) - 1)
    depth = 0
    for index in range(brace, len(stripped)):
        if stripped[index] == "{":
            depth += 1
        elif stripped[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1], stripped[start:index + 1]
    raise AssertionError(f"{relative}: unterminated body for {signature!r}")


def allocation_findings(raw, stripped, allowed=()):
    findings = []
    for label, pattern in FORBIDDEN:
        for match in pattern.finditer(stripped):
            line_start = stripped.rfind("\n", 0, match.start()) + 1
            line_end = stripped.find("\n", match.start())
            raw_line = raw[line_start:line_end if line_end >= 0 else len(raw)].strip()
            if any(text in raw_line for text in allowed):
                continue
            findings.append(f"{label}: {raw_line}")
    for match in STRING_LOCAL.finditer(stripped):
        if match.group("prefix"):
            continue
        tail = stripped[match.end() - 1:stripped.find(";", match.end() - 1) + 1]
        if match.group("open") == "(" and re.search(r",\s*true\s*\)\s*;$|^\(\s*true\s*\)\s*;$", tail):
            continue
        line_start = stripped.rfind("\n", 0, match.start()) + 1
        line_end = stripped.find("\n", match.start())
        findings.append("non-temporary string local: " +
                        raw[line_start:line_end if line_end >= 0 else len(raw)].strip())
    for match in OWNER_LOCAL.finditer(stripped):
        if match.group("prefix"):
            continue
        line_start = stripped.rfind("\n", 0, match.start()) + 1
        line_end = stripped.find("\n", match.start())
        findings.append("heap-owning engine local: " +
                        raw[line_start:line_end if line_end >= 0 else len(raw)].strip())
    return findings


class FrameAllocationGuardTests(unittest.TestCase):
    def test_scanner_detects_each_forbidden_construct(self):
        sample = "\n".join([
            "void F() {",
            "\tstd::vector<int> values(4);",
            "\tint *p = new int[3];",
            "\tchar *q = (char *)malloc(8);",
            "\tlist.push_back(1);",
            "\tStringClass name;",
            "\tWideStringClass wide = other;",
            "\tvector.Delete_All();",
            "\tStringClass temp(0, true);",
            "\tstatic StringClass kept;",
            "\tstd::vector<unsigned char> &scratch = g_scratch;",
            "\t// new std::vector<int> in a comment",
            "\tLog(\"new malloc( push_back(\");",
            "\tConversationRemarkClass remark;",
            "\tstatic ConversationRemarkClass retained;",
            "\tSimpleDynVecClass<uint32> &apt = g_apt;",
            "\tDynamicVectorClass<int> local_list;",
            "\tint new_hold_style = 0;",
            "}",
        ])
        stripped = strip_comments_and_strings(sample)
        findings = allocation_findings(sample, stripped)
        self.assertEqual(len(findings), 9, findings)

    def test_hot_functions_do_not_allocate(self):
        allowed = {}
        for signature, text, _guard in GROW_ONLY:
            allowed.setdefault(signature, []).append(text)
        failures = []
        for relative, signature in HOT_FUNCTIONS:
            raw, stripped = function_body(relative, signature)
            for finding in allocation_findings(raw, stripped, allowed.get(signature, ())):
                failures.append(f"{relative} [{signature.splitlines()[0]}] {finding}")
        self.assertEqual(failures, [], "\n".join(failures))

    def test_grow_only_scratch_guards_precede_allocation(self):
        files = {signature: relative for relative, signature in HOT_FUNCTIONS}
        for signature, text, guard in GROW_ONLY:
            raw, _ = function_body(files[signature], signature)
            allocation = raw.find(text)
            self.assertGreaterEqual(allocation, 0, text)
            match = re.search(guard, raw)
            self.assertIsNotNone(match, guard)
            self.assertLess(match.start(), allocation, signature)

    def test_rval1_flag_contract(self):
        header = read(FRAME_ALLOC)
        self.assertIn('"ux0:data/renegade/user/config/frame-alloc-v1.flag"', header)
        self.assertIn('memcmp(value, "RVAL1 ", 6U) != 0', header)
        self.assertIn("size != 8U", header)
        self.assertIn("value[7] != '\\n'", header)
        values = dict(re.findall(r"\b([A-Z_]+) = ([0-9]+)U", header))
        self.assertEqual(int(values["TEXTURE_RGBA_SCRATCH"]), 1)
        self.assertEqual(int(values["HUD_TARGET_NAME_TEMP"]), 2)
        self.assertEqual(int(values["DEFAULT_MODE"]), 3)
        self.assertIn("MAX_SCRATCH_GROWTH_BYTES = 256U * 1024U", header)
        self.assertIn("static const unsigned mode = Read_Mode();", header)
        # No other port flag reuses the prefix or the file name.
        for path in (ROOT / "port").rglob("*"):
            if path.suffix not in (".cpp", ".h", ".c", ".inc") or path.name == Path(FRAME_ALLOC).name:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertFalse('"RVAL1' in text, str(path))
            self.assertFalse('config/frame-alloc-v1.flag"' in text, str(path))
        # The renderer primes the one-time read at initialization.
        init = read(RENDERER)
        start = init.index("\tRead_Vertex_Array_Mode();\n#endif\n")
        end = init.index('"vglInit entry"', start)
        self.assertIn("RenegadeVitaFrameAlloc::Mode()", init[start:end])

    def test_texture_creation_reuses_bounded_scratch_without_observable_state(self):
        boundary = read(BOUNDARY)
        create = boundary[boundary.index("IDirect3DTexture8 *Create_Texture_From_Surface("):
                          boundary.index("IDirect3DTexture8 *Create_Checkerboard_Fallback()\n{")]
        self.assertNotIn("std::vector<unsigned char> rgba(", create)
        self.assertIn("std::vector<unsigned char> transient_rgba;", create)
        self.assertIn("RenegadeVitaFrameAlloc::Use_Texture_Scratch(\n\t\trgba_bytes, "
                      "g_surface_upload_rgba.capacity()) ? g_surface_upload_rgba : transient_rgba;",
                      create)
        self.assertIn("rgba.resize(rgba_bytes);", create)
        self.assertIn("texture->ResidentBytes = rgba.size();", create)
        # Every pixel of the image is converted before checksum and upload.
        self.assertIn("for (unsigned y = 0U; y < description.Height; ++y) {", create)
        self.assertIn("for (unsigned x = 0U; x < description.Width; ++x) {", create)
        self.assertIn("(static_cast<size_t>(y) * description.Width + x) * 4U;", create)
        self.assertIn("return Create_Checkerboard_Fallback();", create)
        # Nothing between the resize and the upload can reuse the same scratch.
        window = create[create.index("rgba.resize(rgba_bytes);"):create.index("glTexImage2D(")]
        for forbidden in ("Upload_Texture_Level_From_Surface", "Convert_Surface_To_RGBA",
                          "g_surface_upload_rgba"):
            self.assertNotIn(forbidden, window)
        # A successful conversion writes all four destination bytes for every format.
        convert = boundary[boundary.index("bool Convert_Surface_Pixel_To_RGBA("):
                           boundary.index("bool Surface_Format_Can_Convert_To_RGBA(")]
        cases = re.split(r"\n\tcase ", convert)[1:]
        self.assertGreaterEqual(len(cases), 8)
        for case in cases:
            if "return true;" not in case:
                continue
            for byte in range(4):
                self.assertRegex(case, rf"rgba\[{byte}\] =", case.splitlines()[0])
        self.assertIn("\tdefault:\n\t\treturn false;", convert)
        # The scratch is still released with the WW3D session.
        release = boundary[boundary.index("void RenegadeVita_Release_DX8_Scratch()"):]
        self.assertIn("std::vector<unsigned char>().swap(g_surface_upload_rgba);",
                      release[:release.index("}")])

    def test_hud_target_name_copy_uses_temporary_hint(self):
        hud = read(HUD)
        self.assertIn('#include "renegade_vita_frame_alloc.h"', hud)
        port_branch = ("WideStringClass translate_string( bot_named ? tt_name->BotTag : "
                       "translate_obj->Get_String(),\n\t\t\t\t\t\tRenegadeVitaFrameAlloc::Enabled( "
                       "RenegadeVitaFrameAlloc::HUD_TARGET_NAME_TEMP ) );\n#else\n\t\t\t\t\t"
                       "WideStringClass translate_string = bot_named ? tt_name->BotTag : "
                       "translate_obj->Get_String();\n#endif")
        self.assertIn(port_branch, hud)
        self.assertEqual(hud.count("WideStringClass translate_string"), 2)
        stage = read("tools/stage_sources.sh")
        self.assertIn('port/patches/combat-tut1-hud-target-name-temp.patch"', stage)
        # Registered after every other combat patch, so no anchor moves.
        self.assertGreater(stage.index("combat-tut1-hud-target-name-temp.patch"),
                           stage.rindex("combat-a37-"))
        patch = read(HUD_PATCH)
        self.assertTrue(patch.startswith("--- a/hud.cpp\n+++ b/hud.cpp\n"))
        tool = shutil.which("patch")
        if tool is None:
            self.skipTest("patch unavailable")
        with tempfile.TemporaryDirectory(prefix="rval1-hud-") as folder:
            target = Path(folder) / "hud.cpp"
            target.write_text(hud, encoding="utf-8")
            # Reversing the patch from the tracked staging file must succeed at
            # fuzz 0, i.e. staging equals the previous staging plus this patch.
            subprocess.run([tool, "--batch", "--reverse", "--fuzz=0", "--dry-run",
                            "-d", folder, "-p1"], input=patch.encode("utf-8"),
                           check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
