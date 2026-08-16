#include "renegade_file_factory.h"

#include <stdio.h>
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
};

FileFactoryCounters g_file_factory_counters = {};

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
	return result;
}

RenegadeRootedFileClass::RenegadeRootedFileClass(const RenegadePathRoots &roots,
	const char *logical_name) : Roots(roots), LastResolution(),
	PhysicalNamePrepared(false), PreparedAccess(RENEGADE_PATH_READ)
{
	LogicalName[0] = 0;
	Set_Name(logical_name);
	// Original MixFileFactoryClass applies RawFileClass::Bias immediately after
	// Get_File and before Open. Prepare the physical read name here so a later
	// Open/Is_Available never calls RawFileClass::Set_Name and clears that bias.
	Resolve_And_Set_Physical_Name(FileClass::READ);
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
	if (!Resolve_And_Set_Physical_Name(rights)) {
		g_file_factory_counters.open_failures.fetch_add(1U, std::memory_order_relaxed);
		return false;
	}
	const int opened = BufferedFileClass::Open(rights);
	if (!opened) {
		g_file_factory_counters.open_failures.fetch_add(1U, std::memory_order_relaxed);
	}
	return opened;
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
	const int bytes_written = BufferedFileClass::Write(buffer, size);
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
	const bool available = BufferedFileClass::Is_Available(forced);
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
