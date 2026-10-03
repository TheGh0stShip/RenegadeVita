#pragma once

#include <stdint.h>

enum A35ScriptLookupKind : uint32_t {
	A35_LOOKUP_SCRIPT_FACTORY = 0U,
	A35_LOOKUP_OBJECT = 1U,
	A35_LOOKUP_CONVERSATION = 2U,
	A35_LOOKUP_TEXT_FILE = 3U,
	A35_LOOKUP_KIND_COUNT = 4U
};

enum A35ScriptLookupPhase : uint32_t {
	A35_LOOKUP_LEVEL_LOAD = 0U, // includes preload and post-load callbacks
	A35_LOOKUP_GAMEPLAY = 1U
};

enum : uint32_t {
	A35_SCRIPT_LOOKUP_SCHEMA = 1U,
	A35_SCRIPT_LOOKUP_SAMPLE_CAPACITY = 16U,
	A35_SCRIPT_LOOKUP_NAME_CAPACITY = 96U
};

struct A35ScriptLookupSample {
	int32_t object_id; // numeric game ID, never a pointer or a pointer token
	char name[A35_SCRIPT_LOOKUP_NAME_CAPACITY];
	uint32_t count;
	uint32_t first_frame;
	uint32_t last_frame;
	uint32_t first_phase;
	uint32_t last_phase;
	bool key_lossy; // truncated or sanitized keys are never deduplicated
};

struct A35ScriptLookupCounters {
	uint32_t attempts;
	uint32_t returned;
	uint32_t absent;
	uint32_t sentinel_absent; // ID0 or empty name; excluded from samples
	uint32_t unretained_absent; // count of attempts, not distinct keys
	uint32_t lossy_absent;
	uint32_t sample_count;
	bool saturated;
	A35ScriptLookupSample samples[A35_SCRIPT_LOOKUP_SAMPLE_CAPACITY];
};

struct A35ScriptLookupSnapshot {
	bool enabled; // session opted in; remains true after collection stops
	bool collection_active;
	uint32_t phase;
	uint32_t frame;
	A35ScriptLookupCounters kinds[A35_LOOKUP_KIND_COUNT];
};

// Reset only at the original session boundary, with old game/loader work
// quiescent. The epoch check also rejects a hook waiting across a reset.
void A35_Script_Lookup_Reset(bool enabled);
void A35_Script_Lookup_Disable(void);
void A35_Script_Lookup_Set_Context(A35ScriptLookupPhase phase, uint32_t frame);
void A35_Script_Lookup_Record(A35ScriptLookupKind kind, const char *name,
	int32_t object_id, bool returned);
// Returns pthread trylock status (0 = copied); never waits in fatal flushes.
int A35_Script_Lookup_Try_Snapshot(A35ScriptLookupSnapshot &snapshot);
const char *A35_Script_Lookup_Kind_Name(uint32_t kind);
const char *A35_Script_Lookup_Phase_Name(uint32_t phase);
