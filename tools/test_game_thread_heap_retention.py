"""Host checks for retained per-frame heap storage on the Vita game thread.

* The native material-pass queue recycles task storage (bounded) while taking
  and dropping the same pass/mesh references as the former new/delete.
* WWAudio's completed-sound list empties in place on Vita (pointer entries),
  leaving the same count and capacity as the original Delete_All.
* The per-frame conversation-remark diagnostic keeps one retained copy.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY = ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp"
GAMEPLAY = ROOT / "port/platform/a31_gameplay_boundary.cpp"
WWAUDIO = ROOT / "staging/wwaudio/WWAudio.cpp"
PATCH = ROOT / "port/patches/wwaudio-a36-completed-sounds-retain.patch"
VECTOR_H = ROOT / "staging/wwlib/vector.h"


def _between(text, start, end):
    begin = text.index(start)
    return text[begin:text.index(end, begin)]


MATERIAL_HARNESS = r'''
#include <cassert>
#include <cstdio>
#include <new>
#include <set>
struct RefCounted {
    int refs = 1;
    void Add_Ref() { ++refs; }
    void Release_Ref() { --refs; assert(refs >= 1); }
};
struct MaterialPassClass : RefCounted {};
struct MeshClass : RefCounted {};
namespace {
@TASK@
@QUEUE@
@POOL@
}
int main() {
    MaterialPassClass pass;
    MeshClass mesh;
    std::set<void *> first_frame;
    NativeMaterialPassQueue queue;
    for (int frame = 0; frame < 3; ++frame) {
        for (int i = 0; i < 300; ++i) {
            NativeMaterialPassTask *task = New_Native_Material_Pass_Task(&pass, &mesh);
            assert(task != NULL && task->Pass == &pass && task->Mesh == &mesh && task->Next == NULL);
            if (frame == 0) first_frame.insert(task);
            else if (i < 256) assert(first_frame.count(task) == 1);
            if (queue.Tail != NULL) queue.Tail->Next = task; else queue.Head = task;
            queue.Tail = task;
        }
        assert(pass.refs == 301 && mesh.refs == 301);
        unsigned drained = 0;
        while (queue.Head != NULL) {
            NativeMaterialPassTask *task = queue.Head;
            queue.Head = task->Next;
            Delete_Native_Material_Pass_Task(task);
            ++drained;
        }
        queue.Tail = NULL;
        assert(drained == 300);
        assert(pass.refs == 1 && mesh.refs == 1);
        assert(g_free_material_pass_slot_count == kMaxFreeMaterialPassSlots);
    }
    while (g_free_material_pass_slots != NULL) {
        NativeMaterialPassSlot *slot = g_free_material_pass_slots;
        g_free_material_pass_slots = slot->NextFree;
        ::operator delete(static_cast<void *>(slot));
    }
    puts("material pass recycling ok");
}
'''

VECTOR_HARNESS = r'''
#include <cassert>
#include <cstdio>
#include "vector.h"
int main() {
    DynamicVectorClass<int *> original;
    DynamicVectorClass<int *> retained;
    int values[40];
    for (int round = 0; round < 5; ++round) {
        for (int i = 0; i < 13 + round * 7; ++i) {
            assert(original.Add(&values[i]));
            assert(retained.Add(&values[i]));
        }
        for (int i = 0; i < original.Count(); ++i) assert(original[i] == retained[i]);
        original.Delete_All();
        retained.Reset_Active();
        assert(original.Count() == 0 && retained.Count() == 0);
        assert(original.Length() == retained.Length());
    }
    puts("completed-sound list equivalence ok");
}
'''


class GameThreadHeapRetentionTests(unittest.TestCase):
    def _compile_and_run(self, source, includes=()):
        compiler = shutil.which("g++")
        if compiler is None:
            self.skipTest("g++ unavailable")
        with tempfile.TemporaryDirectory(prefix="heap-retention-") as folder:
            folder = Path(folder)
            harness = folder / "harness.cpp"
            harness.write_text(source)
            binary = folder / "harness"
            command = [compiler, "-std=c++17", "-O1", "-g", "-w",
                "-fsanitize=address,undefined", "-fno-sanitize-recover=all"]
            for include in includes:
                command += ["-I", str(include)]
            subprocess.run(command + [str(harness), "-o", str(binary)], check=True)
            return subprocess.run([str(binary)], check=True, capture_output=True,
                text=True).stdout

    def test_material_pass_storage_is_recycled_with_balanced_references(self):
        source = BOUNDARY.read_text()
        task = _between(source, "struct NativeMaterialPassTask {", "struct NativeMaterialPassQueue")
        queue = _between(source, "struct NativeMaterialPassQueue {", "NativeMaterialPassQueue g_rigid")
        pool = _between(source, "union NativeMaterialPassSlot {", "void Drain_Native_Material_Pass_Queue")
        self.assertNotIn("delete task;", source)
        self.assertNotIn("new (std::nothrow) NativeMaterialPassTask", source)
        program = MATERIAL_HARNESS.replace("@TASK@", task).replace(
            "@QUEUE@", queue).replace("@POOL@", pool)
        self.assertIn("material pass recycling ok", self._compile_and_run(program))

    def test_completed_sounds_reset_matches_delete_all(self):
        stage = WWAUDIO.read_text()
        self.assertIn("m_CompletedSounds.Reset_Active ();", stage)
        self.assertRegex(stage, r"DynamicVectorClass<AudibleSoundClass \*>|m_CompletedSounds")
        header = (ROOT / "staging/wwaudio/WWAudio.h").read_text()
        self.assertIn("DynamicVectorClass<AudibleSoundClass *>\tm_CompletedSounds;", header)
        patch = PATCH.read_text()
        self.assertIn("+\t\tm_CompletedSounds.Reset_Active ();", patch)
        self.assertIn("wwaudio-a36-completed-sounds-retain.patch",
            (ROOT / "tools/stage_sources.sh").read_text())
        upstream_vector = VECTOR_H
        if not upstream_vector.exists():
            self.skipTest("staged wwlib vector.h unavailable")
        output = self._compile_and_run(VECTOR_HARNESS, includes=(ROOT / "staging/wwlib",
            ROOT / "port/compatibility/include"))
        self.assertIn("completed-sound list equivalence ok", output)

    def test_conversation_remark_poll_retains_one_copy(self):
        source = GAMEPLAY.read_text()
        self.assertIn("static ConversationRemarkClass remark;", source)
        self.assertNotRegex(source, r"\n\s*ConversationRemarkClass remark;")


if __name__ == "__main__":
    unittest.main()
