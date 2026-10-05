#include "renegade_file_factory.h"

#include <limits.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <atomic>
#include <string.h>

namespace {

struct FileFactoryCounters
{
	std::atomic<uint32_t> get_file_calls;
	std::atomic<uint32_t> return_file_calls;
	std::atomic<uint32_t> resolution_attempts;
	std::atomic<uint32_t> resolution_cache_hits;
	std::atomic<uint32_t> read_resolution_attempts;
	std::atomic<uint32_t> write_resolution_attempts;
	std::atomic<uint32_t> resolution_failures;
	std::atomic<uint32_t> open_attempts;
	std::atomic<uint32_t> open_failures;
	std::atomic<uint32_t> availability_attempts;
	std::atomic<uint32_t> availability_failures;
	std::atomic<uint32_t> create_attempts;
	std::atomic<uint32_t> create_failures;
	std::atomic<uint32_t> delete_attempts;
	std::atomic<uint32_t> delete_failures;
	std::atomic<uint32_t> read_calls;
	std::atomic<uint32_t> read_bytes;
	std::atomic<uint32_t> write_calls;
	std::atomic<uint32_t> write_bytes;
	std::atomic<uint32_t> readonly_availability_skips;
	std::atomic<uint32_t> readonly_open_skips;
	std::atomic<uint32_t> readonly_availability_hits;
	std::atomic<uint32_t> staged_write_files;
	std::atomic<uint32_t> staged_write_bytes;
	std::atomic<uint32_t> staged_write_fallbacks;
};

FileFactoryCounters g_file_factory_counters = {};

// The retail root is never written while the game runs. Once a native probe
// has opened a physical file there, later non-forced availability checks of
// the same path are answered without reopening it. The original factory list
// re-probes a MIX archive for every asset it serves, which otherwise costs a
// memory-card open and close per asset lookup. Only successes are kept;
// failures always reach native I/O again.
enum { kAvailableRetailCapacity = 256 };
struct AvailableRetailPath {
	uint32_t hash;
	char *path;
};
AvailableRetailPath g_available_retail[kAvailableRetailCapacity];
unsigned g_available_retail_count = 0;
pthread_mutex_t g_available_retail_mutex = PTHREAD_MUTEX_INITIALIZER;

uint32_t Path_Hash(const char *path)
{
	uint32_t hash = 2166136261U;
	for (; *path != 0; ++path) hash = (hash ^ static_cast<unsigned char>(*path)) * 16777619U;
	return hash;
}

bool Is_Known_Available(const char *path)
{
	const uint32_t hash = Path_Hash(path);
	pthread_mutex_lock(&g_available_retail_mutex);
	bool found = false;
	for (unsigned index = 0; index < g_available_retail_count && !found; ++index) {
		found = g_available_retail[index].hash == hash &&
			strcmp(g_available_retail[index].path, path) == 0;
	}
	pthread_mutex_unlock(&g_available_retail_mutex);
	return found;
}

void Remember_Available(const char *path)
{
	const uint32_t hash = Path_Hash(path);
	pthread_mutex_lock(&g_available_retail_mutex);
	bool found = false;
	for (unsigned index = 0; index < g_available_retail_count && !found; ++index) {
		found = g_available_retail[index].hash == hash &&
			strcmp(g_available_retail[index].path, path) == 0;
	}
	if (!found && g_available_retail_count < kAvailableRetailCapacity) {
		char *copy = strdup(path);
		if (copy != NULL) {
			g_available_retail[g_available_retail_count].hash = hash;
			g_available_retail[g_available_retail_count].path = copy;
			++g_available_retail_count;
		}
	}
	pthread_mutex_unlock(&g_available_retail_mutex);
}

void Reset(std::atomic<uint32_t> &counter)
{
	counter.store(0U, std::memory_order_relaxed);
}

uint32_t Snapshot(const std::atomic<uint32_t> &counter)
{
	return counter.load(std::memory_order_relaxed);
}

} // namespace

void Renegade_File_Factory_Reset_Statistics(void)
{
	Reset(g_file_factory_counters.get_file_calls);
	Reset(g_file_factory_counters.return_file_calls);
	Reset(g_file_factory_counters.resolution_attempts);
	Reset(g_file_factory_counters.resolution_cache_hits);
	Reset(g_file_factory_counters.read_resolution_attempts);
	Reset(g_file_factory_counters.write_resolution_attempts);
	Reset(g_file_factory_counters.resolution_failures);
	Reset(g_file_factory_counters.open_attempts);
	Reset(g_file_factory_counters.open_failures);
	Reset(g_file_factory_counters.availability_attempts);
	Reset(g_file_factory_counters.availability_failures);
	Reset(g_file_factory_counters.create_attempts);
	Reset(g_file_factory_counters.create_failures);
	Reset(g_file_factory_counters.delete_attempts);
	Reset(g_file_factory_counters.delete_failures);
	Reset(g_file_factory_counters.read_calls);
	Reset(g_file_factory_counters.read_bytes);
	Reset(g_file_factory_counters.write_calls);
	Reset(g_file_factory_counters.write_bytes);
	Reset(g_file_factory_counters.readonly_availability_skips);
	Reset(g_file_factory_counters.readonly_open_skips);
	Reset(g_file_factory_counters.readonly_availability_hits);
	Reset(g_file_factory_counters.staged_write_files);
	Reset(g_file_factory_counters.staged_write_bytes);
	Reset(g_file_factory_counters.staged_write_fallbacks);
}

RenegadeFileFactoryStatistics Renegade_File_Factory_Get_Statistics(void)
{
	RenegadeFileFactoryStatistics result = {};
	result.get_file_calls = Snapshot(g_file_factory_counters.get_file_calls);
	result.return_file_calls = Snapshot(g_file_factory_counters.return_file_calls);
	result.resolution_attempts = Snapshot(g_file_factory_counters.resolution_attempts);
	result.resolution_cache_hits = Snapshot(g_file_factory_counters.resolution_cache_hits);
	result.read_resolution_attempts = Snapshot(g_file_factory_counters.read_resolution_attempts);
	result.write_resolution_attempts = Snapshot(g_file_factory_counters.write_resolution_attempts);
	result.resolution_failures = Snapshot(g_file_factory_counters.resolution_failures);
	result.open_attempts = Snapshot(g_file_factory_counters.open_attempts);
	result.open_failures = Snapshot(g_file_factory_counters.open_failures);
	result.availability_attempts = Snapshot(g_file_factory_counters.availability_attempts);
	result.availability_failures = Snapshot(g_file_factory_counters.availability_failures);
	result.create_attempts = Snapshot(g_file_factory_counters.create_attempts);
	result.create_failures = Snapshot(g_file_factory_counters.create_failures);
	result.delete_attempts = Snapshot(g_file_factory_counters.delete_attempts);
	result.delete_failures = Snapshot(g_file_factory_counters.delete_failures);
	result.read_calls = Snapshot(g_file_factory_counters.read_calls);
	result.read_bytes = Snapshot(g_file_factory_counters.read_bytes);
	result.write_calls = Snapshot(g_file_factory_counters.write_calls);
	result.write_bytes = Snapshot(g_file_factory_counters.write_bytes);
	result.readonly_availability_skips = Snapshot(g_file_factory_counters.readonly_availability_skips);
	result.readonly_open_skips = Snapshot(g_file_factory_counters.readonly_open_skips);
	result.readonly_availability_hits = Snapshot(g_file_factory_counters.readonly_availability_hits);
	result.staged_write_files = Snapshot(g_file_factory_counters.staged_write_files);
	result.staged_write_bytes = Snapshot(g_file_factory_counters.staged_write_bytes);
	result.staged_write_fallbacks = Snapshot(g_file_factory_counters.staged_write_fallbacks);
	return result;
}

RenegadeRootedFileClass::RenegadeRootedFileClass(const RenegadePathRoots &roots,
	const char *logical_name) : Roots(roots), LastResolution(),
	PhysicalNamePrepared(false), PreparedAccess(RENEGADE_PATH_READ),
	NativeProbeForced(false), StagedData(NULL), StagedSize(0), StagedCapacity(0),
	StagedPosition(0), Staging(false), WriteFailed(false), AtomicWrite(false)
{
	LogicalName[0] = 0;
	AtomicTarget[0] = 0;
	AtomicTemporary[0] = 0;
	Set_Name(logical_name);
	// Original MixFileFactoryClass applies RawFileClass::Bias immediately after
	// Get_File and before Open. Prepare the physical read name here so a later
	// Open/Is_Available never calls RawFileClass::Set_Name and clears that bias.
	Resolve_And_Set_Physical_Name(FileClass::READ);
}

RenegadeRootedFileClass::~RenegadeRootedFileClass(void)
{
	// The base destructor closes the handle without reaching this class's
	// Close, so staged bytes are written here.
	if (Staging) Close();
	free(StagedData);
}

char const *RenegadeRootedFileClass::File_Name(void) const
{
	return LogicalName;
}

char const *RenegadeRootedFileClass::Set_Name(char const *filename)
{
	if (filename == NULL || strlen(filename) >= sizeof(LogicalName)) {
		LogicalName[0] = 0;
		PhysicalNamePrepared = false;
		return LogicalName;
	}
	strcpy(LogicalName, filename);
	PhysicalNamePrepared = false;
	return LogicalName;
}

bool RenegadeRootedFileClass::Resolve_And_Set_Physical_Name(int rights)
{
	const RenegadePathAccess access =
		(rights & FileClass::WRITE) != 0 ? RENEGADE_PATH_WRITE : RENEGADE_PATH_READ;
	if (PhysicalNamePrepared && PreparedAccess == access) {
		g_file_factory_counters.resolution_cache_hits.fetch_add(1U,
			std::memory_order_relaxed);
		return true;
	}
	g_file_factory_counters.resolution_attempts.fetch_add(1U,
		std::memory_order_relaxed);
	if (access == RENEGADE_PATH_WRITE) {
		g_file_factory_counters.write_resolution_attempts.fetch_add(1U,
			std::memory_order_relaxed);
	} else {
		g_file_factory_counters.read_resolution_attempts.fetch_add(1U,
			std::memory_order_relaxed);
	}
	LastResolution = Renegade_Resolve_Path(Roots, LogicalName, access);
	if (!LastResolution.success) {
		g_file_factory_counters.resolution_failures.fetch_add(1U,
			std::memory_order_relaxed);
		PhysicalNamePrepared = false;
		return false;
	}
	BufferedFileClass::Set_Name(LastResolution.physical);
	PhysicalNamePrepared = true;
	PreparedAccess = access;
	return true;
}

int RenegadeRootedFileClass::Open(char const *filename, int rights)
{
	Set_Name(filename);
	return Open(rights);
}

int RenegadeRootedFileClass::Open(int rights)
{
	g_file_factory_counters.open_attempts.fetch_add(1U, std::memory_order_relaxed);
	// Commit or close a prior use of this reusable FileClass before replacing
	// its atomic target metadata for the new logical open.
	if (Staging || AtomicWrite || Is_Open()) Close();
	if (!Resolve_And_Set_Physical_Name(rights)) {
		g_file_factory_counters.open_failures.fetch_add(1U, std::memory_order_relaxed);
		return false;
	}
	// Retail is immutable during a running candidate. The case-resolution
	// scan already proved this loose path absent; preserve failure/fallback
	// without asking the OS to fail the same lookup again. Writable namespaces
	// and original forced availability checks must still reach native I/O.
	if (PreparedAccess == RENEGADE_PATH_READ && !NativeProbeForced &&
		LastResolution.confirmed_missing && !LastResolution.writable_namespace) {
		g_file_factory_counters.readonly_open_skips.fetch_add(1U, std::memory_order_relaxed);
		g_file_factory_counters.open_failures.fetch_add(1U, std::memory_order_relaxed);
		return false;
	}
	AtomicWrite = false;
	AtomicTarget[0] = 0;
	AtomicTemporary[0] = 0;
	if ((rights & FileClass::WRITE) != 0) {
		// Keep an existing save/configuration intact until the complete staged
		// stream has reached a sibling file and closed successfully. The sibling
		// path stays on the same Vita filesystem so rename is an atomic replace.
		const int target_length = snprintf(AtomicTarget, sizeof(AtomicTarget), "%s",
			LastResolution.physical);
		const int temporary_length = snprintf(AtomicTemporary, sizeof(AtomicTemporary),
			"%s.pending", LastResolution.physical);
		if (target_length <= 0 || target_length >= static_cast<int>(sizeof(AtomicTarget)) ||
			temporary_length <= 0 || temporary_length >= static_cast<int>(sizeof(AtomicTemporary))) {
			WriteFailed = true;
			g_file_factory_counters.open_failures.fetch_add(1U, std::memory_order_relaxed);
			return false;
		}
		BufferedFileClass::Set_Name(AtomicTemporary);
		AtomicWrite = true;
	}
	// RawFileClass::Open closes (and so commits) any previous staged file.
	const int opened = BufferedFileClass::Open(rights);
	if (opened) WriteFailed = false;
	if (!opened) {
		if (AtomicWrite) BufferedFileClass::Set_Name(AtomicTarget);
		AtomicWrite = false;
		g_file_factory_counters.open_failures.fetch_add(1U, std::memory_order_relaxed);
	} else if ((rights & FileClass::WRITE) != 0) {
		// Each ChunkSaveClass chunk seeks back to patch its header, and every
		// seek flushes stdio: a save became thousands of small card writes and
		// seeks on the game thread. The file is created and truncated now, as
		// before, and its bytes are written in one piece by Close.
		Staging = true;
		StagedSize = 0;
		StagedPosition = 0;
		g_file_factory_counters.staged_write_files.fetch_add(1U, std::memory_order_relaxed);
	}
	return opened;
}

bool RenegadeRootedFileClass::Stage_Write(void const *buffer, int size)
{
	if (size < 0 || size > INT_MAX - StagedPosition) return false;
	// A zero-length write changes nothing, even past the end.
	if (size == 0) return true;
	const int end = StagedPosition + size;
	if (end > StagedCapacity) {
		int capacity = StagedCapacity != 0 ? StagedCapacity : 64 * 1024;
		while (capacity < end) capacity = capacity > INT_MAX / 2 ? INT_MAX : capacity * 2;
		unsigned char *grown = static_cast<unsigned char *>(realloc(StagedData,
			static_cast<size_t>(capacity)));
		if (grown == NULL) return false;
		StagedData = grown;
		StagedCapacity = capacity;
	}
	// Writing past the end leaves a zero-filled gap, as a seek past the end
	// followed by a write does on the card.
	if (StagedPosition > StagedSize) {
		memset(StagedData + StagedSize, 0, static_cast<size_t>(StagedPosition - StagedSize));
	}
	memcpy(StagedData + StagedPosition, buffer, static_cast<size_t>(size));
	StagedPosition = end;
	if (end > StagedSize) StagedSize = end;
	return true;
}

// Writes the staged bytes to the open file, leaves its cursor where the staged
// cursor was, and continues without staging.
bool RenegadeRootedFileClass::Flush_Staged_Writes(void)
{
	Staging = false;
	bool written = true;
	if (StagedSize > 0) {
		written = BufferedFileClass::Write(StagedData, StagedSize) == StagedSize;
		g_file_factory_counters.staged_write_bytes.fetch_add(static_cast<uint32_t>(StagedSize),
			std::memory_order_relaxed);
	}
	if (written && StagedPosition != StagedSize) {
		written = BufferedFileClass::Seek(StagedPosition, SEEK_SET) == StagedPosition;
	}
	free(StagedData);
	StagedData = NULL;
	StagedSize = 0;
	StagedCapacity = 0;
	StagedPosition = 0;
	if (!written) WriteFailed = true;
	return written;
}

int RenegadeRootedFileClass::Seek(int pos, int dir)
{
	if (!Staging) return BufferedFileClass::Seek(pos, dir);
	long long base = -1;
	if (dir == SEEK_SET) base = 0;
	else if (dir == SEEK_CUR) base = StagedPosition;
	else if (dir == SEEK_END) base = StagedSize;
	const long long target = base + pos;
	if (base < 0 || target < 0 || target > INT_MAX) return -1;
	StagedPosition = static_cast<int>(target);
	return StagedPosition;
}

int RenegadeRootedFileClass::Size(void)
{
	return Staging ? StagedSize : BufferedFileClass::Size();
}

void RenegadeRootedFileClass::Close(void)
{
	if (Staging) (void)Flush_Staged_Writes();
	BufferedFileClass::Close();
	if (AtomicWrite) {
		if (!WriteFailed && rename(AtomicTemporary, AtomicTarget) != 0) {
			WriteFailed = true;
		}
		if (WriteFailed) remove(AtomicTemporary);
		BufferedFileClass::Set_Name(AtomicTarget);
		AtomicWrite = false;
	}
}

void RenegadeRootedFileClass::Error(int error, int canretry, char const *filename)
{
	// RawFileClass reports short writes, seek errors and fclose failure through
	// this virtual callback. Retain them through Close for the save owner.
	if (PreparedAccess == RENEGADE_PATH_WRITE) WriteFailed = true;
	BufferedFileClass::Error(error, canretry, filename);
}

int RenegadeRootedFileClass::Read(void *buffer, int size)
{
	g_file_factory_counters.read_calls.fetch_add(1U, std::memory_order_relaxed);
	const int bytes_read = BufferedFileClass::Read(buffer, size);
	if (bytes_read > 0) {
		g_file_factory_counters.read_bytes.fetch_add(static_cast<uint32_t>(bytes_read),
			std::memory_order_relaxed);
	}
	return bytes_read;
}

int RenegadeRootedFileClass::Write(void const *buffer, int size)
{
	g_file_factory_counters.write_calls.fetch_add(1U, std::memory_order_relaxed);
	int bytes_written = 0;
	// A failed staged flush lost previously accepted bytes. Only a successful
	// reopen starts a new write session; later chunk writes cannot repair it.
	if (WriteFailed) return 0;
	if (Staging && Stage_Write(buffer, size)) {
		bytes_written = size;
	} else {
		if (Staging) {
			// Out of memory: write what is staged and continue directly.
			g_file_factory_counters.staged_write_fallbacks.fetch_add(1U,
				std::memory_order_relaxed);
			// Do not report the next write as successful after losing part of
			// the already-accepted save or failing to restore its cursor.
			if (!Flush_Staged_Writes()) return 0;
		}
		bytes_written = BufferedFileClass::Write(buffer, size);
	}
	if (bytes_written > 0) {
		g_file_factory_counters.write_bytes.fetch_add(static_cast<uint32_t>(bytes_written),
			std::memory_order_relaxed);
	}
	return bytes_written;
}

bool RenegadeRootedFileClass::Is_Available(int forced)
{
	g_file_factory_counters.availability_attempts.fetch_add(1U,
		std::memory_order_relaxed);
	if (!Resolve_And_Set_Physical_Name(FileClass::READ)) {
		g_file_factory_counters.availability_failures.fetch_add(1U,
			std::memory_order_relaxed);
		return false;
	}
	if (!forced && LastResolution.confirmed_missing &&
		!LastResolution.writable_namespace) {
		g_file_factory_counters.readonly_availability_skips.fetch_add(1U, std::memory_order_relaxed);
		g_file_factory_counters.availability_failures.fetch_add(1U, std::memory_order_relaxed);
		return false;
	}
	const bool immutable_retail = !forced && !LastResolution.writable_namespace;
	if (immutable_retail && !Is_Open() && Is_Known_Available(LastResolution.physical)) {
		g_file_factory_counters.readonly_availability_hits.fetch_add(1U, std::memory_order_relaxed);
		LastResolution.confirmed_missing = false;
		return true;
	}
	// RawFileClass::Is_Available(forced) calls virtual Open. Carry the forced
	// request through that nested call instead of accidentally short-circuiting it.
	const bool previous_forced = NativeProbeForced;
	NativeProbeForced = previous_forced || forced != 0;
	const bool available = BufferedFileClass::Is_Available(forced);
	NativeProbeForced = previous_forced;
	if (available) {
		LastResolution.confirmed_missing = false;
		if (immutable_retail) Remember_Available(LastResolution.physical);
	}
	if (!available) {
		g_file_factory_counters.availability_failures.fetch_add(1U,
			std::memory_order_relaxed);
	}
	return available;
}

int RenegadeRootedFileClass::Create(void)
{
	g_file_factory_counters.create_attempts.fetch_add(1U, std::memory_order_relaxed);
	if (!Resolve_And_Set_Physical_Name(FileClass::WRITE)) {
		g_file_factory_counters.create_failures.fetch_add(1U, std::memory_order_relaxed);
		return false;
	}
	const int created = BufferedFileClass::Create();
	if (!created) {
		g_file_factory_counters.create_failures.fetch_add(1U, std::memory_order_relaxed);
	}
	return created;
}

int RenegadeRootedFileClass::Delete(void)
{
	g_file_factory_counters.delete_attempts.fetch_add(1U, std::memory_order_relaxed);
	if (!Resolve_And_Set_Physical_Name(FileClass::WRITE)) {
		g_file_factory_counters.delete_failures.fetch_add(1U, std::memory_order_relaxed);
		return false;
	}
	const int deleted = BufferedFileClass::Delete();
	if (!deleted) {
		g_file_factory_counters.delete_failures.fetch_add(1U, std::memory_order_relaxed);
	}
	return deleted;
}

FileClass *RenegadeRootedFileFactoryClass::Get_File(char const *filename)
{
	g_file_factory_counters.get_file_calls.fetch_add(1U, std::memory_order_relaxed);
	return new RenegadeRootedFileClass(Roots, filename);
}

void RenegadeRootedFileFactoryClass::Return_File(FileClass *file)
{
	g_file_factory_counters.return_file_calls.fetch_add(1U, std::memory_order_relaxed);
	delete file;
}
