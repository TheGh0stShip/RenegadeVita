#pragma once

#include "renegade_paths.h"

#include "bufffile.h"
#include "ffactory.h"

#include <stdint.h>

/*
** Bounded resource-boundary counters. These deliberately describe only the
** Vita rooted FileFactoryClass boundary; they do not replace or instrument
** original MixFileFactoryClass ownership, and they never retain file names or
** payload bytes. The 32-bit per-session counters are sufficient for a normal
** load/play/exit capture and keep the hot path allocation-free.
*/
struct RenegadeFileFactoryStatistics
{
	uint32_t get_file_calls;
	uint32_t return_file_calls;
	uint32_t resolution_attempts;
	uint32_t resolution_cache_hits;
	uint32_t read_resolution_attempts;
	uint32_t write_resolution_attempts;
	uint32_t resolution_failures;
	uint32_t open_attempts;
	uint32_t open_failures;
	uint32_t availability_attempts;
	uint32_t availability_failures;
	uint32_t create_attempts;
	uint32_t create_failures;
	uint32_t delete_attempts;
	uint32_t delete_failures;
	uint32_t read_calls;
	uint32_t read_bytes;
	uint32_t write_calls;
	uint32_t write_bytes;
	uint32_t readonly_availability_skips;
	uint32_t readonly_open_skips;
	uint32_t readonly_availability_hits;
	uint32_t staged_write_files;
	uint32_t staged_write_bytes;
	uint32_t staged_write_fallbacks;
	// RVIO1 (renegade_load_io.h): read-only retail streams switched to
	// unbuffered stdio, MIX member Bias calls that reused a measured archive
	// size, and archive sizes recorded from original Bias probes.
	uint32_t direct_read_streams;
	uint32_t archive_size_reuses;
	uint32_t archive_size_probes;
};

void Renegade_File_Factory_Reset_Statistics(void);
// Moves source over destination, also when the platform rename refuses an
// existing destination; on failure the previous destination is kept.
bool Renegade_Replace_File(const char *source, const char *destination);
// A save interrupted between Renegade_Replace_File's two renames leaves only
// "<destination>.previous". Moves it back; returns true when it restored it.
bool Renegade_Recover_Interrupted_Replace(const char *destination);
RenegadeFileFactoryStatistics Renegade_File_Factory_Get_Statistics(void);
// RVIO1 load-time I/O mask (renegade_load_io.h). 0, the default, keeps every
// original path; set once before the retail MIX factories are constructed.
void Renegade_File_Factory_Set_Load_Io_Mode(unsigned mode);
unsigned Renegade_File_Factory_Get_Load_Io_Mode(void);

class RenegadeRootedFileClass : public BufferedFileClass
{
public:
	RenegadeRootedFileClass(const RenegadePathRoots &roots, const char *logical_name);
	virtual ~RenegadeRootedFileClass(void);

	virtual char const *File_Name(void) const;
	virtual char const *Set_Name(char const *filename);
	virtual int Create(void);
	virtual int Delete(void);
	virtual bool Is_Available(int forced = false);
	virtual int Open(char const *filename, int rights = READ);
	virtual int Open(int rights = READ);
	virtual int Read(void *buffer, int size);
	virtual int Seek(int pos, int dir = SEEK_CUR);
	virtual int Size(void);
	virtual int Write(void const *buffer, int size);
	virtual void Close(void);
	virtual void Error(int error, int canretry = false, char const *filename = NULL);
	virtual void Bias(int start, int length = -1);

	const RenegadeResolvedPath &Get_Last_Resolution(void) const { return LastResolution; }
	bool Has_Write_Failed(void) const { return WriteFailed; }
	void Abort_Write(void) { WriteFailed = true; }

private:
	bool Resolve_And_Set_Physical_Name(int rights);
	bool Stage_Write(void const *buffer, int size);
	bool Flush_Staged_Writes(void);
	bool Is_Immutable_Retail_Read(void) const;
	void Apply_Direct_Reads(void);

	RenegadePathRoots Roots;
	char LogicalName[768];
	RenegadeResolvedPath LastResolution;
	bool PhysicalNamePrepared;
	RenegadePathAccess PreparedAccess;
	bool NativeProbeForced;
	// Write-only files (saves, configuration) are assembled in memory and
	// written to the card in one piece when they are closed.
	unsigned char *StagedData;
	int StagedSize;
	int StagedCapacity;
	int StagedPosition;
	bool Staging;
	bool WriteFailed;
	bool AtomicWrite;
	// Set while RawFileClass::Open runs its leading virtual Close().
	bool NativeOpening;
	// RVIO1 bit 0: switch the stream to unbuffered before its first operation.
	bool DirectReadPending;
	// RVIO1 bit 1: an original Bias is measuring this retail archive's size.
	bool ArchiveSizeProbe;
	unsigned long long AtomicStartUs;
	int AtomicBytes;
	char AtomicTarget[1024];
	char AtomicTemporary[1024];
};

// Called once per committed-or-failed atomic (write-only) session, e.g. each
// quicksave, manual save, autosave or config write. The platform runtime sets
// it to route the line into its log; NULL disables reporting.
typedef void (*RenegadeAtomicWriteReportHook)(const char *target_path, int bytes,
	unsigned long long elapsed_us, bool success);
void Renegade_File_Factory_Set_Atomic_Write_Report_Hook(RenegadeAtomicWriteReportHook hook);

class RenegadeRootedFileFactoryClass : public FileFactoryClass
{
public:
	explicit RenegadeRootedFileFactoryClass(const RenegadePathRoots &roots) : Roots(roots) {}
	virtual FileClass *Get_File(char const *filename);
	virtual void Return_File(FileClass *file);

private:
	RenegadePathRoots Roots;
};
