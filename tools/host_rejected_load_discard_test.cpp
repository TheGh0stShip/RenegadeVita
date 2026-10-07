// Host fault-injection test for OBJECTIVE_STATE_LIFECYCLE F4.
//
// Drives the real staged SaveLoadSystemClass::Load, PointerRemapClass,
// ChunkSave/ChunkLoad and ReferencerClass (GameObjReference) code: save a
// linked referencer, load it into fresh objects, force the load to be
// rejected after the pointer remap, then destroy the partial state in both
// orders. A forked negative control rebuilds the pre-fix state (remapped
// target, never linked) and must crash, proving the hazard is real.
#include "always.h"
#include "chunkio.h"
#include "ramfile.h"
#include "saveload.h"
#include "saveloadsubsystem.h"
#include "scriptablegameobj.h"
#include "reflist.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sys/wait.h>
#include <unistd.h>

namespace {

enum { TEST_SUBSYSTEM_CHUNK = 0x46344634, TEST_TARGET_CHUNK = 1, TEST_REF_CHUNK = 2 };

class ProbeReferencer : public ReferencerClass {
public:
	const void *Raw_Target() const { return ReferenceTarget; }
	const void *Raw_Next() const { return TargetReferencerListNext; }
	void Force_Unlinked_Target(ScriptableGameObj *target)
	{
		ReferenceTarget = target;  // pre-fix state: remapped but never linked
		TargetReferencerListNext = NULL;
	}
};

bool g_force_reject = false;
ScriptableGameObj *g_save_target = NULL;
ProbeReferencer *g_save_ref = NULL;
ScriptableGameObj *g_loaded_target = NULL;
ProbeReferencer *g_loaded_ref = NULL;
ProbeReferencer *g_anchor = NULL;

class ProbeSubSystem : public SaveLoadSubSystemClass {
public:
	uint32 Chunk_ID() const override { return TEST_SUBSYSTEM_CHUNK; }
	const char *Name() const override { return "F4ProbeSubSystem"; }
	bool Save(ChunkSaveClass &csave) override
	{
		csave.Begin_Chunk(TEST_TARGET_CHUNK);
		bool ok = g_save_target->ReferenceableClass<ScriptableGameObj>::Save(csave);
		csave.End_Chunk();
		csave.Begin_Chunk(TEST_REF_CHUNK);
		ok = g_save_ref->Save(csave) && ok;
		csave.End_Chunk();
		return ok;
	}
	bool Load(ChunkLoadClass &cload) override
	{
		bool ok = true;
		while (cload.Open_Chunk()) {
			if (cload.Cur_Chunk_ID() == TEST_TARGET_CHUNK) {
				g_loaded_target = new ScriptableGameObj();
				ok = g_loaded_target->ReferenceableClass<ScriptableGameObj>::Load(cload) && ok;
				// An already-linked referencer so the target list is non-empty.
				g_anchor = new ProbeReferencer();
				g_anchor->Set_Ptr(g_loaded_target);
			} else if (cload.Cur_Chunk_ID() == TEST_REF_CHUNK) {
				g_loaded_ref = new ProbeReferencer();
				ok = g_loaded_ref->Load(cload) && ok;
			}
			cload.Close_Chunk();
		}
		// Fault injection: reject after every pointer request was made, so the
		// remap still runs and only post-load linking is discarded.
		return ok && !g_force_reject;
	}
};

ProbeSubSystem g_subsystem;
int g_failures = 0;

#define CHECK(cond) do { if (!(cond)) { std::printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #cond); ++g_failures; } } while (0)

bool Round_Trip(bool reject)
{
	g_save_target = new ScriptableGameObj();
	g_save_ref = new ProbeReferencer();
	g_save_ref->Set_Ptr(g_save_target);

	static unsigned char buffer[4096];
	std::memset(buffer, 0, sizeof(buffer));
	RAMFileClass ram(buffer, sizeof(buffer));
	ram.Open(FileClass::WRITE);
	{
		ChunkSaveClass csave(&ram);
		CHECK(SaveLoadSystemClass::Save(csave, g_subsystem));
	}
	ram.Close();

	delete g_save_ref;      // unlink from the original target
	delete g_save_target;   // original target gone, like a level unload
	g_save_ref = NULL;
	g_save_target = NULL;

	g_force_reject = reject;
	ram.Open(FileClass::READ);
	bool ok;
	{
		ChunkLoadClass cload(&ram);
		ok = SaveLoadSystemClass::Load(cload, true);
	}
	ram.Close();
	return ok;
}

void Expect_Crash_Without_Fix()
{
	std::fflush(stdout);
	pid_t child = fork();
	if (child == 0) {
		ScriptableGameObj *target = new ScriptableGameObj();
		ProbeReferencer *anchor = new ProbeReferencer();
		anchor->Set_Ptr(target);
		ProbeReferencer *unlinked = new ProbeReferencer();
		unlinked->Force_Unlinked_Target(target);
		delete unlinked;  // pre-fix: walks target's list past its end
		std::printf("negative control survived\n");
		_exit(0);
	}
	int status = 0;
	waitpid(child, &status, 0);
	const bool crashed = WIFSIGNALED(status) || (WIFEXITED(status) && WEXITSTATUS(status) != 0);
	CHECK(crashed);
	if (crashed) std::printf("negative control: unlinked referencer destruction crashed as expected\n");
}

}  // namespace

int main()
{
	// g_subsystem registered itself in the SaveLoadSubSystemClass constructor.
	// 1. Accepted load: post-load relinks, target destruction clears the ref.
	CHECK(Round_Trip(false));
	CHECK(g_loaded_ref != NULL && g_loaded_ref->Get_Ptr() == g_loaded_target);
	delete g_loaded_target;
	CHECK(g_loaded_ref->Get_Ptr() == NULL);
	CHECK(g_anchor->Get_Ptr() == NULL);
	delete g_loaded_ref;
	delete g_anchor;

	// 2. Rejected load, target destroyed first (use-after-free order pre-fix).
	CHECK(!Round_Trip(true));
	CHECK(g_loaded_ref->Raw_Target() == NULL && g_loaded_ref->Raw_Next() == NULL);
	CHECK(!g_loaded_ref->Is_Post_Load_Registered());
	delete g_loaded_target;
	delete g_loaded_ref;
	delete g_anchor;

	// 3. Rejected load, referencer destroyed while its target is alive
	//    (NULL list walk pre-fix); the anchor link must stay intact.
	CHECK(!Round_Trip(true));
	CHECK(g_loaded_ref->Get_Ptr() == NULL);
	delete g_loaded_ref;
	CHECK(g_anchor->Get_Ptr() == g_loaded_target);
	delete g_loaded_target;
	CHECK(g_anchor->Get_Ptr() == NULL);
	delete g_anchor;

	// 4. A later accepted load is unaffected by the earlier discard.
	CHECK(Round_Trip(false));
	CHECK(g_loaded_ref->Get_Ptr() == g_loaded_target);
	delete g_loaded_ref;
	delete g_anchor;
	delete g_loaded_target;

	Expect_Crash_Without_Fix();

	if (g_failures != 0) {
		std::printf("FAILED %d checks\n", g_failures);
		return 1;
	}
	std::printf("PASS rejected_load_discard accepted=2 rejected=2 negative_control=crash\n");
	return 0;
}
