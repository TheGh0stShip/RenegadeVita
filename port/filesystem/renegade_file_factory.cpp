#include "renegade_file_factory.h"
#include "renegade_load_io.h"

#include <limits.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <atomic>
#include <chrono>
#include <string.h>
#include <sys/stat.h>

namespace {

std::atomic<RenegadeAtomicWriteReportHook> g_atomic_write_report_hook(NULL);

unsigned long long Monotonic_Us(void)
{
	return static_cast<unsigned long long>(std::chrono::duration_cast<std::chrono::microseconds>(
		std::chrono::steady_clock::now().time_since_epoch()).count());
}

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
	std::atomic<uint32_t> direct_read_streams;
	std::atomic<uint32_t> archive_size_reuses;
	std::atomic<uint32_t> archive_size_probes;
};

FileFactoryCounters g_file_factory_counters = {};
std::atomic<unsigned> g_load_io_mode(RENEGADE_LOAD_IO_DEFAULT);

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

// RVIO1 bit 1. Whole-archive sizes measured by an original RawFileClass::Bias
// probe of an immutable retail path (one entry per mounted MIX archive). Only
// positive sizes from a successful native open are kept.
enum { kRetailSizeCapacity = 32 };
struct RetailSizePath {
	uint32_t hash;
	int size;
	char *path;
};
RetailSizePath g_retail_sizes[kRetailSizeCapacity];
unsigned g_retail_size_count = 0;
pthread_mutex_t g_retail_size_mutex = PTHREAD_MUTEX_INITIALIZER;

bool Find_Retail_Size(const char *path, int *size)
{
	const uint32_t hash = Path_Hash(path);
	pthread_mutex_lock(&g_retail_size_mutex);
	bool found = false;
	for (unsigned index = 0; index < g_retail_size_count && !found; ++index) {
		if (g_retail_sizes[index].hash == hash &&
			strcmp(g_retail_sizes[index].path, path) == 0) {
			*size = g_retail_sizes[index].size;
			found = true;
		}
	}
	pthread_mutex_unlock(&g_retail_size_mutex);
	return found;
}

void Remember_Retail_Size(const char *path, int size)
{
	if (size <= 0) return;
	const uint32_t hash = Path_Hash(path);
	pthread_mutex_lock(&g_retail_size_mutex);
	bool found = false;
	for (unsigned index = 0; index < g_retail_size_count && !found; ++index) {
		found = g_retail_sizes[index].hash == hash &&
			strcmp(g_retail_sizes[index].path, path) == 0;
	}
	if (!found && g_retail_size_count < kRetailSizeCapacity) {
		char *copy = strdup(path);
		if (copy != NULL) {
			g_retail_sizes[g_retail_size_count].hash = hash;
			g_retail_sizes[g_retail_size_count].size = size;
			g_retail_sizes[g_retail_size_count].path = copy;
			++g_retail_size_count;
		}
	}
	pthread_mutex_unlock(&g_retail_size_mutex);
}

} // namespace

// Moves a completed sibling over the destination. POSIX rename replaces an
// existing file atomically, but the Vita's sceIoRename (behind newlib's
// rename) refuses an existing destination, so every save into an occupied
// slot was discarded. Then the previous file is moved aside first and
// restored if the final rename fails, so a failed save still leaves the
// previous valid file in place; the aside copy is removed only after the new
// file is in position.
#if defined(RENEGADE_TEST_REFUSING_RENAME)
#include <errno.h>
#include <sys/stat.h>
// Host contract tests model sceIoRename, which refuses an existing destination.
static int Platform_Rename(const char *source, const char *destination)
{
	struct stat status;
	if (stat(destination, &status) == 0) {
		errno = EEXIST;
		return -1;
	}
	return rename(source, destination);
}
#else
static int Platform_Rename(const char *source, const char *destination)
{
	return rename(source, destination);
}
#endif

bool Renegade_Replace_File(const char *source, const char *destination)
{
	if (Platform_Rename(source, destination) == 0) return true;
	char previous[1024 + 16];
	const int length = snprintf(previous, sizeof(previous), "%s.previous", destination);
	if (length <= 0 || length >= static_cast<int>(sizeof(previous))) return false;
	remove(previous);
	if (Platform_Rename(destination, previous) != 0) return false;
	if (Platform_Rename(source, destination) != 0) {
		(void)Platform_Rename(previous, destination);
		return false;
	}
	remove(previous);
	return true;
}

bool Renegade_Recover_Interrupted_Replace(const char *destination)
{
	char previous[1024 + 16];
	const int length = snprintf(previous, sizeof(previous), "%s.previous", destination);
	if (length <= 0 || length >= static_cast<int>(sizeof(previous))) return false;
	struct stat status;
	if (stat(previous, &status) != 0) return false;
	if (stat(destination, &status) == 0) {
		// The new file reached its slot; only the cleanup was interrupted.
		remove(previous);
		return false;
	}
	return Platform_Rename(previous, destination) == 0;
}

namespace {

bool Replace_File(const char *source, const char *destination)
{
	return Renegade_Replace_File(source, destination);
}

}  // namespace

void Renegade_File_Factory_Set_Atomic_Write_Report_Hook(RenegadeAtomicWriteReportHook hook)
{
	g_atomic_write_report_hook.store(hook, std::memory_order_release);
}

void Renegade_File_Factory_Set_Load_Io_Mode(unsigned mode)
{
	g_load_io_mode.store(mode & RENEGADE_LOAD_IO_ALL, std::memory_order_relaxed);
}

unsigned Renegade_File_Factory_Get_Load_Io_Mode(void)
{
	return g_load_io_mode.load(std::memory_order_relaxed);
}

namespace {

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
	Reset(g_file_factory_counters.direct_read_streams);
	Reset(g_file_factory_counters.archive_size_reuses);
	Reset(g_file_factory_counters.archive_size_probes);
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
	result.direct_read_streams = Snapshot(g_file_factory_counters.direct_read_streams);
	result.archive_size_reuses = Snapshot(g_file_factory_counters.archive_size_reuses);
	result.archive_size_probes = Snapshot(g_file_factory_counters.archive_size_probes);
	return result;
}

RenegadeRootedFileClass::RenegadeRootedFileClass(const RenegadePathRoots &roots,
	const char *logical_name) : Roots(roots), LastResolution(),
	PhysicalNamePrepared(false), PreparedAccess(RENEGADE_PATH_READ),
	NativeProbeForced(false), StagedData(NULL), StagedSize(0), StagedCapacity(0),
	StagedPosition(0), Staging(false), WriteFailed(false), AtomicWrite(false),
	NativeOpening(false), DirectReadPending(false), ArchiveSizeProbe(false),
	AtomicStartUs(0), AtomicBytes(0)
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
	if (LastResolution.success && LastResolution.writable_namespace &&
		Renegade_Recover_Interrupted_Replace(LastResolution.physical)) {
		// The slot reappeared; resolve again so case/miss state is current.
		LastResolution = Renegade_Resolve_Path(Roots, LogicalName, access);
	}
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
	// Only pure write sessions are staged and replaced atomically. A
	// READ|WRITE session must see the existing bytes, so it keeps the
	// original direct file semantics.
	const bool write_only = rights == FileClass::WRITE;
	if (write_only) {
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
		AtomicStartUs = Monotonic_Us();
		AtomicBytes = 0;
	}
	// Any previous use was committed above. RawFileClass::Open begins with a
	// virtual Close(); without this guard that Close would treat the session
	// being opened as finished, drop AtomicWrite and restore the target name,
	// so the open landed directly on (and truncated) the destination.
	NativeOpening = true;
	// RVIO1 bit 0: retail data is read through BufferedFileClass, which
	// already buffers small reads; switch its stdio stream to unbuffered so
	// newlib does not split every refill into 1 KiB sceIoRead calls.
	DirectReadPending = rights == FileClass::READ && Is_Immutable_Retail_Read() &&
		(g_load_io_mode.load(std::memory_order_relaxed) &
			RENEGADE_LOAD_IO_DIRECT_READS) != 0U;
	const int opened = BufferedFileClass::Open(rights);
	if (opened && DirectReadPending) Apply_Direct_Reads();
	DirectReadPending = false;
	NativeOpening = false;
	if (opened) WriteFailed = false;
	if (!opened) {
		if (AtomicWrite) BufferedFileClass::Set_Name(AtomicTarget);
		AtomicWrite = false;
		g_file_factory_counters.open_failures.fetch_add(1U, std::memory_order_relaxed);
	} else if (write_only) {
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

bool RenegadeRootedFileClass::Is_Immutable_Retail_Read(void) const
{
	return PhysicalNamePrepared && PreparedAccess == RENEGADE_PATH_READ &&
		!LastResolution.writable_namespace;
}

// setvbuf must precede every other operation on the stream. RawFileClass::Open
// seeks a biased file before returning, so the switch also happens here.
void RenegadeRootedFileClass::Apply_Direct_Reads(void)
{
	DirectReadPending = false;
#if defined(_UNIX)
	FILE *handle = static_cast<FILE *>(Get_File_Handle());
	if (handle != NULL && setvbuf(handle, NULL, _IONBF, 0) == 0) {
		g_file_factory_counters.direct_read_streams.fetch_add(1U,
			std::memory_order_relaxed);
	}
#endif
}

void RenegadeRootedFileClass::Bias(int start, int length)
{
	// RVIO1 bit 1. Original RawFileClass::Bias calls RawFileClass::Size(),
	// which opens, measures and closes this closed archive file before every
	// MIX member open. For a fresh immutable retail archive whose size an
	// earlier probe measured, apply the same arithmetic without that open.
	const bool eligible = start != 0 && BiasStart == 0 && BiasLength == -1 &&
		!Is_Open() && Is_Immutable_Retail_Read() && !LastResolution.confirmed_missing &&
		(g_load_io_mode.load(std::memory_order_relaxed) &
			RENEGADE_LOAD_IO_ARCHIVE_SIZE_REUSE) != 0U;
	int archive_size = 0;
	if (eligible && Find_Retail_Size(LastResolution.physical, &archive_size)) {
		// RawFileClass::Bias with Size() == archive_size and BiasStart 0; the
		// file is closed, so no repositioning seek follows.
		BiasStart = start;
		int bias_length = archive_size;
		if (length != -1) bias_length = bias_length < length ? bias_length : length;
		BiasLength = bias_length > 0 ? bias_length : 0;
		g_file_factory_counters.archive_size_reuses.fetch_add(1U,
			std::memory_order_relaxed);
		return;
	}
	ArchiveSizeProbe = eligible;
	BufferedFileClass::Bias(start, length);
	ArchiveSizeProbe = false;
}

int RenegadeRootedFileClass::Seek(int pos, int dir)
{
	if (DirectReadPending) Apply_Direct_Reads();
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
	if (Staging) return StagedSize;
	const int size = BufferedFileClass::Size();
	// Within an original Bias probe, RawFileClass::Size has just opened the
	// unbiased archive and measured the whole file; keep that size.
	if (ArchiveSizeProbe && size > 0 && BiasStart == 0 && Is_Open()) {
		Remember_Retail_Size(LastResolution.physical, size);
		g_file_factory_counters.archive_size_probes.fetch_add(1U,
			std::memory_order_relaxed);
	}
	return size;
}

void RenegadeRootedFileClass::Close(void)
{
	if (NativeOpening) {
		BufferedFileClass::Close();
		return;
	}
	if (Staging) {
		if (AtomicWrite) AtomicBytes = StagedSize;
		(void)Flush_Staged_Writes();
	}
	BufferedFileClass::Close();
	if (AtomicWrite) {
		if (!WriteFailed && !Replace_File(AtomicTemporary, AtomicTarget)) {
			WriteFailed = true;
		}
		if (WriteFailed) remove(AtomicTemporary);
		const RenegadeAtomicWriteReportHook hook =
			g_atomic_write_report_hook.load(std::memory_order_acquire);
		if (hook != NULL) {
			hook(AtomicTarget, AtomicBytes, Monotonic_Us() - AtomicStartUs, !WriteFailed);
		}
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
