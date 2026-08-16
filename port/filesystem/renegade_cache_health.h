#pragma once

#include "renegade_paths.h"

#include <stdint.h>

/*
** A deliberately narrow, optional cache boundary.  The original filesystem
** and MixFileFactoryClass remain the only retail-asset owners.  This helper
** only validates the header/count/order of a generated filename index before
** a future consumer may elect to use it.  Missing or invalid cache data never
** changes the original load route.
*/
enum RenegadeCacheHealthState
{
	RENEGADE_CACHE_HEALTH_MISSING,
	RENEGADE_CACHE_HEALTH_VALID,
	RENEGADE_CACHE_HEALTH_CORRUPT,
	RENEGADE_CACHE_HEALTH_UNSAFE_PATH
};

struct RenegadeCacheHealth
{
	RenegadeCacheHealthState state;
	uint32_t entry_count;
	char archive[128];
	char physical_path[1024];
	char detail[128];
};

/* Validate a `renegade-vita-mix-index-v1` cache artifact. `cache_logical`
** must resolve through the existing `cache/` namespace; absolute, retail, and
** traversing paths are rejected. The probe is bounded and performs no archive
** read, conversion, extraction, allocation, or cache rebuild. */
RenegadeCacheHealth Renegade_Inspect_Mix_Index_Cache(
	const RenegadePathRoots &roots, const char *archive_name,
	const char *cache_logical);

const char *Renegade_Cache_Health_Name(RenegadeCacheHealthState state);
