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
};

void Renegade_File_Factory_Reset_Statistics(void);
// Moves source over destination, also when the platform rename refuses an
// existing destination; on failure the previous destination is kept.
bool Renegade_Replace_File(const char *source, const char *destination);
RenegadeFileFactoryStatistics Renegade_File_Factory_Get_Statistics(void);

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

	const RenegadeResolvedPath &Get_Last_Resolution(void) const { return LastResolution; }
	bool Has_Write_Failed(void) const { return WriteFailed; }
	void Abort_Write(void) { WriteFailed = true; }

private:
	bool Resolve_And_Set_Physical_Name(int rights);
	bool Stage_Write(void const *buffer, int size);
	bool Flush_Staged_Writes(void);

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
	char AtomicTarget[1024];
	char AtomicTemporary[1024];
};

class RenegadeRootedFileFactoryClass : public FileFactoryClass
{
public:
	explicit RenegadeRootedFileFactoryClass(const RenegadePathRoots &roots) : Roots(roots) {}
	virtual FileClass *Get_File(char const *filename);
	virtual void Return_File(FileClass *file);

private:
	RenegadePathRoots Roots;
};
