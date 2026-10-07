"""Host execution test for the early objective status fix.

Compiles the staged combat/objectives.cpp (and its pre-patch form, recovered by
reverse-applying port/patches/combat-a38-objective-early-status.patch) on the
host with the real wwlib chunk/string code and small stubs for the HUD, radar,
message window and game objects, then drives ObjectiveManager through the
mission orderings in reports/campaign/OBJECTIVE_EARLY_STATUS.md, a quicksave
round trip, malformed-save admission, and cross-version save loads.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "port/patches/combat-a38-objective-early-status.patch"

STUBS = {
    "debug.h": '#include "wwdebug.h"\n#define Debug_Say(x)\n',
    "diaglog.h": "void Diag_Log_Stub(const char *code, const char *format, ...);\n"
                 "#define DIAG_LOG(args) Diag_Log_Stub args\n",
    "radar.h": "class RadarManager { public: enum { BLIP_SHAPE_TYPE_OBJECTIVE = 1, "
               "BLIP_COLOR_TYPE_PRIMARY_OBJECTIVE = 5 }; };\n",
    "translatedb.h": '#include "widestring.h"\n'
                     "class TranslateDBClass { public: static const WCHAR *Get_String(int id); };\n"
                     "#define TRANSLATE(id) TranslateDBClass::Get_String(id)\n",
    "string_ids.h": "enum { IDS_OBJ_NEW_OBJ = 1, IDS_OBJ_STATUS_CHANGED, IDS_OBJ_CANCELLED, IDS_MENU_TEXT145,"
                    " IDS_MENU_TEXT113, IDS_MENU_TERTIARY, IDS_LOCALE_UNKNOWN, IDS_MENU_OBJ_ACCOMPLISHED,"
                    " IDS_MENU_OBJ_FAILED, IDS_MENU_OBJ_HIDDEN, IDS_MENU_OBJ_PENDING, IDS_STUB_COUNT };\n",
    "messagewindow.h": '#include "widestring.h"\n#include "vector3.h"\n'
                       "class MessageWindowClass { public: void Add_Message(const WideStringClass &message, "
                       "const Vector3 &color); };\n",
    "combat.h": '#include "messagewindow.h"\n'
                "class CombatManager { public: static MessageWindowClass *Get_Message_Window(); };\n",
    "globalsettings.h": '#include "vector3.h"\n'
                        "class HUDGlobalSettingsDef { public: static HUDGlobalSettingsDef *Get_Instance() { return 0; }\n"
                        "  const Vector3 &Get_Primary_Objective_Color() { return Color; }\n"
                        "  const Vector3 &Get_Secondary_Objective_Color() { return Color; }\n"
                        "  const Vector3 &Get_Tertiary_Objective_Color() { return Color; }\n"
                        "  Vector3 Color; };\n",
    "scriptablegameobj.h": '#include "vector3.h"\n'
                           "class ScriptableGameObj { public: virtual ~ScriptableGameObj() {}\n"
                           "  void Get_Position(Vector3 *pos) const { *pos = Vector3(0, 0, 0); } };\n",
    "physicalgameobj.h": '#include "scriptablegameobj.h"\n'
                         "class PhysicalGameObj : public ScriptableGameObj { public:\n"
                         "  void Reset_Radar_Blip_Shape_Type() {} void Reset_Radar_Blip_Color_Type() {}\n"
                         "  void Set_Radar_Blip_Shape_Type(int) {} void Set_Radar_Blip_Color_Type(int) {} };\n",
    "wwaudio.h": "",
    "hud.h": "class HUDClass { public: static void Add_Objective(int type); };\n",
    "a30_vita_runtime.h": "int A30_Vita_Log(const char *format, ...);\n",
    "objectivesviewer.h": "class ObjectivesViewerClass { public: void Initialize() {} void Shutdown() {}\n"
                          "  void Update() {} bool Is_Displayed() { return false; } void Display(bool) {}\n"
                          "  void Page_Down() {} void Render() {} };\n",
    "gameobjref.h": '#include "chunkio.h"\n#include "physicalgameobj.h"\n'
                    "class GameObjReference { public: GameObjReference() : Ptr(0) {}\n"
                    "  ScriptableGameObj *Get_Ptr() const { return Ptr; }\n"
                    "  GameObjReference &operator=(ScriptableGameObj *obj) { Ptr = obj; return *this; }\n"
                    "  bool Save(ChunkSaveClass &) { return true; } bool Load(ChunkLoadClass &) { return true; }\n"
                    "  ScriptableGameObj *Ptr; };\n",
}

DRIVER = r'''
#include "objectives.h"
#include "ramfile.h"
#include "chunkio.h"
#include "string_ids.h"
#include "hud.h"
#include "combat.h"
#include "translatedb.h"
#include <cstdarg>
#include <cstdio>
#include <cstring>

static int Messages, NewObjectives, Completed, Failed, Logs;
static int Failures;
#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL line %d: %s\n", __LINE__, #cond); ++Failures; } } while (0)

void Diag_Log_Stub(const char *code, const char *, ...) {
    if (!std::strcmp(code, "OBCO")) ++Completed;
    if (!std::strcmp(code, "OBFA")) ++Failed;
}
int A30_Vita_Log(const char *, ...) { return ++Logs; }
void HUDClass::Add_Objective(int) { ++NewObjectives; }
void MessageWindowClass::Add_Message(const WideStringClass &, const Vector3 &) { ++Messages; }
static MessageWindowClass Window;
MessageWindowClass *CombatManager::Get_Message_Window() { return &Window; }
const WCHAR *TranslateDBClass::Get_String(int id) {
    static WideStringClass text[IDS_STUB_COUNT + 1];
    if (id < 0 || id > IDS_STUB_COUNT) id = IDS_STUB_COUNT;
    if (text[id].Is_Empty()) {
        const char *value = id == IDS_OBJ_NEW_OBJ ? "New %s Objective: %s" :
                            id == IDS_OBJ_STATUS_CHANGED ? "%s Objective %s" : "Text";
        text[id].Convert_From(value);
    }
    return text[id].Peek_Buffer();
}

enum { PRIMARY = ObjectiveManager::TYPE_PRIMARY, SECONDARY = ObjectiveManager::TYPE_SECONDARY,
       TERTIARY = ObjectiveManager::TYPE_TERTIARY, PENDING = ObjectiveManager::STATUS_IS_PENDING,
       ACCOMPLISHED = ObjectiveManager::STATUS_ACCOMPLISHED, FAILED = ObjectiveManager::STATUS_FAILED,
       HIDDEN = ObjectiveManager::STATUS_HIDDEN };
static char Sound[] = "";

static void Add(int id, int status = PENDING, int type = PRIMARY) {
    ObjectiveManager::Add_Objective(id, type, status, 1, 1, Sound);
}
static int Status(int id) {
    for (int i = 0; i < ObjectiveManager::Get_Objective_Count(); ++i)
        if (ObjectiveManager::Get_Objective(i)->ID == id) return ObjectiveManager::Get_Objective(i)->Status;
    return -1;
}

static char Buffer[1 << 16];
static int Save_Manager() {
    RAMFileClass file(Buffer, sizeof(Buffer));
    file.Open(FileClass::WRITE);
    ChunkSaveClass csave(&file);
    bool ok = ObjectiveManager::Save(csave);
    int size = file.Seek(0, SEEK_CUR);
    file.Close();
    return ok ? size : -1;
}
static bool Load_Manager(int size) {
    RAMFileClass file(Buffer, size);
    file.Open(FileClass::READ);
    ChunkLoadClass cload(&file);
    bool ok = ObjectiveManager::Load(cload);
    file.Close();
    return ok;
}
// Early-status micro-chunks (id 2) in the manager variables chunk of the save.
static int Early_Entries(int size, int *ids = 0) {
    RAMFileClass file(Buffer, size);
    file.Open(FileClass::READ);
    ChunkLoadClass cload(&file);
    int count = 0;
    while (cload.Open_Chunk()) {
        if (cload.Cur_Chunk_ID() == 629001433U) {
            while (cload.Open_Micro_Chunk()) {
                if (cload.Cur_Micro_Chunk_ID() == 2U) {
                    int entry[2];
                    cload.Read(entry, sizeof(entry));
                    if (ids) ids[count] = entry[0];
                    ++count;
                }
                cload.Close_Micro_Chunk();
            }
        }
        cload.Close_Chunk();
    }
    file.Close();
    return count;
}
// A manager chunk written by hand: tertiary count plus raw early entries.
static int Craft(const int (*entries)[2], int count) {
    RAMFileClass file(Buffer, sizeof(Buffer));
    file.Open(FileClass::WRITE);
    ChunkSaveClass csave(&file);
    int tertiary = 0;
    csave.Begin_Chunk(629001433U);
    WRITE_MICRO_CHUNK(csave, 1, tertiary);
    for (int i = 0; i < count; ++i) {
        int entry[2] = { entries[i][0], entries[i][1] };
        WRITE_MICRO_CHUNK(csave, 2, entry);
    }
    csave.End_Chunk();
    int size = file.Seek(0, SEEK_CUR);
    file.Close();
    return size;
}

static void Run_New() {
    ObjectiveManager::Init();

    // Added first (original order): no table involvement, repeats still announce.
    Add(10);
    CHECK(Messages == 1 && NewObjectives == 1);
    ObjectiveManager::Set_Objective_Status(10, ACCOMPLISHED);
    CHECK(Status(10) == ACCOMPLISHED && Messages == 2 && Completed == 1);
    ObjectiveManager::Set_Objective_Status(10, ACCOMPLISHED);
    CHECK(Messages == 3 && Completed == 2);
    CHECK(Early_Entries(Save_Manager()) == 0);
    CHECK(Logs == 0);

    // Completed before it was added (M02 203, M06 609, M07 704-708 ...).
    ObjectiveManager::Set_Objective_Status(20, ACCOMPLISHED);
    CHECK(Status(20) == -1 && Messages == 3 && Completed == 2);
    Add(20, PENDING, SECONDARY);
    CHECK(Status(20) == ACCOMPLISHED && NewObjectives == 2 && Messages == 5 && Completed == 3);
    // A script that credits the late add itself (M03 late-add, M04 torpedo) is absorbed once.
    ObjectiveManager::Set_Objective_Status(20, ACCOMPLISHED);
    CHECK(Messages == 5 && Completed == 3);
    ObjectiveManager::Update(0.1f);
    ObjectiveManager::Set_Objective_Status(20, ACCOMPLISHED);
    CHECK(Messages == 6 && Completed == 4);
    // A different status after the replay is never absorbed.
    ObjectiveManager::Set_Objective_Status(21, ACCOMPLISHED);
    Add(21);
    ObjectiveManager::Set_Objective_Status(21, FAILED);
    CHECK(Status(21) == FAILED && Failed == 1);

    // Failure before activation, latest status wins, pending/hidden clear it.
    ObjectiveManager::Set_Objective_Status(30, FAILED);
    Add(30);
    CHECK(Status(30) == FAILED && Failed == 2);
    ObjectiveManager::Set_Objective_Status(40, ACCOMPLISHED);
    ObjectiveManager::Set_Objective_Status(40, FAILED);
    Add(40);
    CHECK(Status(40) == FAILED);
    ObjectiveManager::Set_Objective_Status(41, ACCOMPLISHED);
    ObjectiveManager::Set_Objective_Status(41, PENDING);
    Add(41);
    CHECK(Status(41) == PENDING);
    ObjectiveManager::Set_Objective_Status(42, ACCOMPLISHED);
    ObjectiveManager::Set_Objective_Status(42, HIDDEN);
    Add(42);
    CHECK(Status(42) == PENDING);

    // A non-pending add consumes the entry without applying it; removal forgets it.
    ObjectiveManager::Set_Objective_Status(50, ACCOMPLISHED);
    Add(50, HIDDEN, TERTIARY);
    CHECK(Status(50) == HIDDEN);
    ObjectiveManager::Set_Objective_Status(60, ACCOMPLISHED);
    ObjectiveManager::Remove_Objective(60);
    Add(60);
    CHECK(Status(60) == PENDING);
    // Duplicate adds stay no-ops.
    ObjectiveManager::Set_Objective_Status(61, ACCOMPLISHED);
    Add(61);
    Add(61);
    CHECK(Status(61) == ACCOMPLISHED);

    // Non-positive ids are never remembered (Objective::Load rejects them).
    ObjectiveManager::Set_Objective_Status(-1, ACCOMPLISHED);
    ObjectiveManager::Set_Objective_Status(0, ACCOMPLISHED);
    ObjectiveManager::Update(0.1f);
    CHECK(Early_Entries(Save_Manager()) == 0);

    // Quicksave round trip; Reset (level unload) clears the table; markers are not saved.
    ObjectiveManager::Reset();
    ObjectiveManager::Set_Objective_Status(70, ACCOMPLISHED);
    ObjectiveManager::Set_Objective_Status(71, FAILED);
    ObjectiveManager::Set_Objective_Status(73, ACCOMPLISHED);
    Add(73);
    Add(72);
    int size = Save_Manager();
    int ids[8] = { 0 };
    CHECK(size > 0 && Early_Entries(size, ids) == 2 && ids[0] == 70 && ids[1] == 71);
    ObjectiveManager::Reset();
    Add(70);
    CHECK(Status(70) == PENDING);
    ObjectiveManager::Reset();
    CHECK(Load_Manager(size));
    CHECK(Status(72) == PENDING && Status(73) == ACCOMPLISHED);
    Add(70);
    Add(71);
    CHECK(Status(70) == ACCOMPLISHED && Status(71) == FAILED);
    // The loaded entries are consumed by those adds.
    ObjectiveManager::Update(0.1f);
    CHECK(Early_Entries(Save_Manager()) == 0);

    // Bounded: the oldest of 33 entries is evicted.
    ObjectiveManager::Reset();
    for (int id = 100; id <= 132; ++id) ObjectiveManager::Set_Objective_Status(id, ACCOMPLISHED);
    size = Save_Manager();
    CHECK(Early_Entries(size) == 32);
    Add(100);
    Add(132);
    CHECK(Status(100) == PENDING && Status(132) == ACCOMPLISHED);

    // Admission: the loader accepts only what the saver can write.
    const int good[2][2] = { { 5, ACCOMPLISHED }, { 6, FAILED } };
    const int pending[1][2] = { { 5, PENDING } };
    const int negative[1][2] = { { -3, ACCOMPLISHED } };
    const int duplicate[2][2] = { { 5, ACCOMPLISHED }, { 5, FAILED } };
    int many[33][2];
    for (int i = 0; i < 33; ++i) { many[i][0] = 200 + i; many[i][1] = ACCOMPLISHED; }
    ObjectiveManager::Reset();
    CHECK(Load_Manager(Craft(good, 2)));
    Add(5); Add(6);
    CHECK(Status(5) == ACCOMPLISHED && Status(6) == FAILED);
    ObjectiveManager::Reset();
    CHECK(!Load_Manager(Craft(pending, 1)));
    ObjectiveManager::Reset();
    CHECK(!Load_Manager(Craft(negative, 1)));
    ObjectiveManager::Reset();
    CHECK(!Load_Manager(Craft(duplicate, 2)));
    ObjectiveManager::Reset();
    CHECK(!Load_Manager(Craft(many, 33)));
    ObjectiveManager::Reset();
    // A rejected load leaves the table empty after the owner's Reset.
    Add(5);
    CHECK(Status(5) == PENDING);
    ObjectiveManager::Reset();
}

// Writes a save with two early entries for the cross-version check.
static void Write_Save(const char *path) {
    ObjectiveManager::Init();
    ObjectiveManager::Set_Objective_Status(70, ACCOMPLISHED);
    ObjectiveManager::Set_Objective_Status(71, FAILED);
    Add(72);
    int size = Save_Manager();
    FILE *out = std::fopen(path, "wb");
    std::fwrite(Buffer, 1, size, out);
    std::fclose(out);
}
static void Load_Save(const char *path, bool new_loader) {
    ObjectiveManager::Init();
    FILE *in = std::fopen(path, "rb");
    int size = (int)std::fread(Buffer, 1, sizeof(Buffer), in);
    std::fclose(in);
    CHECK(Load_Manager(size));
    CHECK(Status(72) == PENDING);
    Add(70);
    CHECK(Status(70) == (new_loader ? ACCOMPLISHED : PENDING));
}

int main(int argc, char **argv) {
    const char *mode = argc > 1 ? argv[1] : "new";
    if (!std::strcmp(mode, "new")) Run_New();
    else if (!std::strcmp(mode, "write")) Write_Save(argv[2]);
    else if (!std::strcmp(mode, "load-new")) Load_Save(argv[2], true);
    else if (!std::strcmp(mode, "load-old")) Load_Save(argv[2], false);
    std::printf("%s failures=%d\n", mode, Failures);
    return Failures == 0 ? 0 : 1;
}
'''


def compile_probe(folder, objectives_cpp, name):
    work = Path(folder) / name
    work.mkdir()
    for header, text in STUBS.items():
        (work / header).write_text("#pragma once\n" + text)
    shutil.copy(ROOT / "staging/combat/objectives.h", work / "objectives.h")
    (work / "objectives.cpp").write_text(objectives_cpp)
    (work / "driver.cpp").write_text(DRIVER)
    compat = ROOT / "port/compatibility/include"
    command = ["g++", "-std=c++17", "-O1", "-g", "-DNDEBUG=1", "-D_UNIX=1",
               "-DRENEGADE_HOST_ABI_TEST=1", "-DRENEGADE_VITA_PORT=1",
               "-Wno-unknown-pragmas", "-w", "-include", str(compat / "msvc_compat.h")]
    for directory in [work, compat, ROOT / "staging/wwlib", ROOT / "staging/wwmath", ROOT / "staging/wwdebug",
                      ROOT / "upstream/CnC_Renegade/Code/wwdebug", ROOT / "upstream/CnC_Renegade/Code/wwlib",
                      ROOT / "upstream/CnC_Renegade/Code/WWMath"]:
        command.extend(["-I", str(directory)])
    exe = work / "probe"
    command.extend([str(work / "driver.cpp"), str(work / "objectives.cpp")])
    command.extend(str(ROOT / "staging/wwlib" / source) for source in
                   ("chunkio.cpp", "ramfile.cpp", "wwstring.cpp", "widestring.cpp"))
    command.extend(["-pthread", "-o", str(exe)])
    compiled = subprocess.run(command, text=True, capture_output=True)
    if compiled.returncode != 0:
        raise AssertionError(compiled.stderr[-6000:])
    return exe


def run(exe, *args):
    return subprocess.run([str(exe), *args], text=True, capture_output=True)


class ObjectiveEarlyStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix="objective-early-status-")
        staged = (ROOT / "staging/combat/objectives.cpp").read_text()
        cls.new_exe = compile_probe(cls.folder.name, staged, "new")
        old_dir = Path(cls.folder.name) / "pre-patch"
        old_dir.mkdir()
        (old_dir / "objectives.cpp").write_text(staged)
        reverted = subprocess.run(["patch", "--batch", "--fuzz=0", "-R", "-p1", "-d", str(old_dir),
                                   "-i", str(PATCH)], text=True, capture_output=True)
        if reverted.returncode != 0:
            raise AssertionError(reverted.stdout + reverted.stderr)
        cls.old_exe = compile_probe(cls.folder.name, (old_dir / "objectives.cpp").read_text(), "old")

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_mission_orderings_save_round_trip_and_admission(self):
        result = run(self.new_exe, "new")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_new_save_loads_in_old_and_new_loaders(self):
        save = Path(self.folder.name) / "new.sav"
        self.assertEqual(run(self.new_exe, "write", str(save)).returncode, 0)
        for exe, mode in ((self.new_exe, "load-new"), (self.old_exe, "load-old")):
            result = run(exe, mode, str(save))
            self.assertEqual(result.returncode, 0, mode + ": " + result.stdout + result.stderr)

    def test_old_save_loads_in_new_loader_with_empty_table(self):
        save = Path(self.folder.name) / "old.sav"
        written = run(self.old_exe, "write", str(save))
        self.assertEqual(written.returncode, 0, written.stdout)
        # The pre-patch manager drops the early statuses, so the new loader
        # sees no entries and the late add stays pending, as before the fix.
        result = run(self.new_exe, "load-old", str(save))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_patch_is_registered_once_after_the_objective_lifecycle_patches(self):
        script = (ROOT / "tools/stage_sources.sh").read_text()
        inventory = (ROOT / "staging/PATCH_INVENTORY.json").read_text()
        name = "port/patches/combat-a38-objective-early-status.patch"
        self.assertEqual(script.count(name), 1)
        self.assertEqual(inventory.count(name), 1)
        self.assertGreater(script.index(name),
                           script.index("port/patches/combat-a37-encyclopedia-save-bit-cache-flush.patch"))


if __name__ == "__main__":
    unittest.main()
