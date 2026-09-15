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
};

void Renegade_File_Factory_Reset_Statistics(void);
RenegadeFileFactoryStatistics Renegade_File_Factory_Get_Statistics(void);

class RenegadeRootedFileClass : public BufferedFileClass
{
public:
	RenegadeRootedFileClass(const RenegadePathRoots &roots, const char *logical_name);

	virtual char const *File_Name(void) const;
	virtual char const *Set_Name(char const *filename);
	virtual int Create(void);
	virtual int Delete(void);
	virtual bool Is_Available(int forced = false);
	virtual int Open(char const *filename, int rights = READ);
	virtual int Open(int rights = READ);
	virtual int Read(void *buffer, int size);
	virtual int Write(void const *buffer, int size);

	const RenegadeResolvedPath &Get_Last_Resolution(void) const { return LastResolution; }

private:
	bool Resolve_And_Set_Physical_Name(int rights);

	RenegadePathRoots Roots;
	char LogicalName[768];
	RenegadeResolvedPath LastResolution;
	bool PhysicalNamePrepared;
	RenegadePathAccess PreparedAccess;
	bool NativeProbeForced;
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
