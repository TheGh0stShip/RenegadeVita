#include "a35_script_lookup_telemetry.h"

#include <atomic>
#include <pthread.h>
#include <string.h>

static_assert(sizeof(int32_t) == 4U && sizeof(uint32_t) == 4U,
	"Lookup IDs and counters retain explicit 32-bit semantics");
static_assert(sizeof(unsigned int) == 4U && ATOMIC_INT_LOCK_FREE == 2,
	"The disabled lookup gate requires a lock-free 32-bit atomic");
static_assert(sizeof(A35ScriptLookupSnapshot) <= 10240U,
	"Lookup storage must remain bounded below 10 KiB");

namespace {
pthread_mutex_t gLookupMutex = PTHREAD_MUTEX_INITIALIZER;
std::atomic<uint32_t> gLookupEpoch(0U);
uint32_t gNextEpoch = 0U; // under the mutex; exhaustion leaves collection off
A35ScriptLookupSnapshot gLookups = {};

void Increment(uint32_t &value, bool &saturated)
{
	if (value != UINT32_MAX) ++value;
	else saturated = true;
}

bool Copy_Key(char *output, const char *input)
{
	bool lossy = false;
	uint32_t i = 0U;
	if (input != NULL) {
		for (; i + 1U < A35_SCRIPT_LOOKUP_NAME_CAPACITY && input[i] != '\0'; ++i) {
			const unsigned char ch = static_cast<unsigned char>(input[i]);
			output[i] = ch >= 32U && ch < 127U ? static_cast<char>(ch) : '?';
			if (output[i] != input[i]) lossy = true;
		}
		if (input[i] != '\0') lossy = true;
	}
	output[i] = '\0';
	return lossy;
}
} // namespace

void A35_Script_Lookup_Reset(bool enabled)
{
	gLookupEpoch.store(0U);
	pthread_mutex_lock(&gLookupMutex);
	memset(&gLookups, 0, sizeof(gLookups));
	gLookups.enabled = enabled && gNextEpoch != UINT32_MAX;
	gLookups.collection_active = gLookups.enabled;
	gLookups.phase = A35_LOOKUP_LEVEL_LOAD;
	if (gLookups.enabled) gLookupEpoch.store(++gNextEpoch);
	pthread_mutex_unlock(&gLookupMutex);
}

void A35_Script_Lookup_Disable(void)
{
	gLookupEpoch.store(0U);
	pthread_mutex_lock(&gLookupMutex);
	gLookups.collection_active = false;
	pthread_mutex_unlock(&gLookupMutex);
}

void A35_Script_Lookup_Set_Context(A35ScriptLookupPhase phase, uint32_t frame)
{
	const uint32_t epoch = gLookupEpoch.load();
	if (epoch == 0U) return;
	pthread_mutex_lock(&gLookupMutex);
	if (epoch == gLookupEpoch.load()) {
		gLookups.phase = phase;
		gLookups.frame = frame;
	}
	pthread_mutex_unlock(&gLookupMutex);
}

void A35_Script_Lookup_Record(A35ScriptLookupKind kind, const char *name,
	int32_t object_id, bool returned)
{
	const uint32_t epoch = gLookupEpoch.load();
	if (epoch == 0U || kind >= A35_LOOKUP_KIND_COUNT) return;
	pthread_mutex_lock(&gLookupMutex);
	if (epoch != gLookupEpoch.load()) {
		pthread_mutex_unlock(&gLookupMutex);
		return;
	}
	A35ScriptLookupCounters &counter = gLookups.kinds[kind];
	Increment(counter.attempts, counter.saturated);
	if (returned) {
		Increment(counter.returned, counter.saturated);
	} else {
		Increment(counter.absent, counter.saturated);
		if ((kind == A35_LOOKUP_OBJECT && object_id == 0) ||
			(kind != A35_LOOKUP_OBJECT && (name == NULL || *name == '\0'))) {
			Increment(counter.sentinel_absent, counter.saturated);
		} else {
			A35ScriptLookupSample key = {};
			key.object_id = kind == A35_LOOKUP_OBJECT ? object_id : 0;
			key.key_lossy = Copy_Key(key.name, kind == A35_LOOKUP_OBJECT ? NULL : name);
			if (key.key_lossy) Increment(counter.lossy_absent, counter.saturated);
			uint32_t index = counter.sample_count;
			if (!key.key_lossy) {
				for (uint32_t i = 0U; i < counter.sample_count; ++i) {
					const A35ScriptLookupSample &sample = counter.samples[i];
					if (!sample.key_lossy && sample.object_id == key.object_id &&
						strcmp(sample.name, key.name) == 0) { index = i; break; }
				}
			}
			if (index == A35_SCRIPT_LOOKUP_SAMPLE_CAPACITY) {
				Increment(counter.unretained_absent, counter.saturated);
			} else {
				if (index == counter.sample_count) {
					counter.samples[index] = key;
					counter.samples[index].first_frame = gLookups.frame;
					counter.samples[index].first_phase = gLookups.phase;
					++counter.sample_count;
				}
				A35ScriptLookupSample &sample = counter.samples[index];
				Increment(sample.count, counter.saturated);
				sample.last_frame = gLookups.frame;
				sample.last_phase = gLookups.phase;
			}
		}
	}
	pthread_mutex_unlock(&gLookupMutex);
}

int A35_Script_Lookup_Try_Snapshot(A35ScriptLookupSnapshot &snapshot)
{
	const int status = pthread_mutex_trylock(&gLookupMutex);
	if (status == 0) {
		snapshot = gLookups;
		pthread_mutex_unlock(&gLookupMutex);
	}
	return status;
}

const char *A35_Script_Lookup_Kind_Name(uint32_t kind)
{
	static const char *const names[] = {
		"script_factory", "object", "conversation_name", "text_file_available"
	};
	return kind < A35_LOOKUP_KIND_COUNT ? names[kind] : "unknown";
}

const char *A35_Script_Lookup_Phase_Name(uint32_t phase)
{
	return phase == A35_LOOKUP_LEVEL_LOAD ? "level_load" :
		phase == A35_LOOKUP_GAMEPLAY ? "gameplay" : "unknown";
}
