// Prepared source probe; compiling/running it requires lifting the build hold.
#include "a35_script_lookup_telemetry.h"

#include <stdio.h>
#include <string>
#include <thread>
#include <vector>

static A35ScriptLookupSnapshot snapshot;

static bool Check(bool condition, const char *step)
{
	if (!condition) fprintf(stderr, "script lookup probe failed: %s\n", step);
	return condition;
}

int main()
{
	A35_Script_Lookup_Reset(false);
	A35_Script_Lookup_Record(A35_LOOKUP_OBJECT, NULL, 100389, false);
	if (!Check(A35_Script_Lookup_Try_Snapshot(snapshot) == 0 &&
		!snapshot.enabled && snapshot.kinds[A35_LOOKUP_OBJECT].attempts == 0U,
		"disabled fast path")) return 1;
	A35_Script_Lookup_Reset(true);
	std::vector<std::thread> workers;
	for (unsigned i = 0U; i < 4U; ++i) workers.emplace_back([] {
		for (unsigned j = 0U; j < 5000U; ++j) {
			A35_Script_Lookup_Record(A35_LOOKUP_OBJECT, NULL, 100389, false);
			A35_Script_Lookup_Record(A35_LOOKUP_SCRIPT_FACTORY, "present", 0, true);
		}
	});
	for (std::thread &worker : workers) worker.join();
	if (!Check(A35_Script_Lookup_Try_Snapshot(snapshot) == 0 &&
		snapshot.kinds[A35_LOOKUP_OBJECT].attempts == 20000U &&
		snapshot.kinds[A35_LOOKUP_OBJECT].sample_count == 1U &&
		snapshot.kinds[A35_LOOKUP_OBJECT].samples[0].count == 20000U &&
		snapshot.kinds[A35_LOOKUP_SCRIPT_FACTORY].returned == 20000U,
		"worker aggregation with isolated channels")) return 1;
	A35_Script_Lookup_Set_Context(A35_LOOKUP_GAMEPLAY, 1U);
	A35_Script_Lookup_Record(A35_LOOKUP_OBJECT, NULL, 100389, false);
	A35_Script_Lookup_Record(A35_LOOKUP_OBJECT, NULL, 0, false);
	A35_Script_Lookup_Record(A35_LOOKUP_CONVERSATION, "", 0, false);
	for (int32_t i = 1; i <= 20; ++i)
		A35_Script_Lookup_Record(A35_LOOKUP_OBJECT, NULL, i, false);
	const std::string long_name(100U, 'x');
	A35_Script_Lookup_Record(A35_LOOKUP_TEXT_FILE, long_name.c_str(), 0, false);
	A35_Script_Lookup_Record(A35_LOOKUP_TEXT_FILE, long_name.c_str(), 0, false);
	A35_Script_Lookup_Disable();
	A35_Script_Lookup_Record(A35_LOOKUP_OBJECT, NULL, -1, false);
	if (!Check(A35_Script_Lookup_Try_Snapshot(snapshot) == 0 && snapshot.enabled &&
		!snapshot.collection_active && snapshot.kinds[A35_LOOKUP_OBJECT].sample_count == 16U &&
		snapshot.kinds[A35_LOOKUP_OBJECT].unretained_absent == 5U &&
		snapshot.kinds[A35_LOOKUP_OBJECT].sentinel_absent == 1U &&
		snapshot.kinds[A35_LOOKUP_OBJECT].samples[0].first_phase == A35_LOOKUP_LEVEL_LOAD &&
		snapshot.kinds[A35_LOOKUP_OBJECT].samples[0].last_phase == A35_LOOKUP_GAMEPLAY &&
		snapshot.kinds[A35_LOOKUP_TEXT_FILE].sample_count == 2U &&
		snapshot.kinds[A35_LOOKUP_TEXT_FILE].samples[0].key_lossy &&
		snapshot.kinds[A35_LOOKUP_CONVERSATION].sentinel_absent == 1U,
		"capacity, sentinel, lossy identity, phase and disable")) return 1;
	A35_Script_Lookup_Reset(true);
	if (!Check(A35_Script_Lookup_Try_Snapshot(snapshot) == 0 && snapshot.frame == 0U &&
		snapshot.kinds[A35_LOOKUP_OBJECT].attempts == 0U,
		"next session resets all samples and counters")) return 1;
	A35_Script_Lookup_Disable();
	puts("script lookup probe: PASS");
	return 0;
}
