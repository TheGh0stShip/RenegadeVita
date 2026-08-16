#pragma once

#include "renegade_paths.h"

#include <stdint.h>

/*
** Read-only evidence that the original file-factory and ChunkLoad path can
** reach the retail tutorial-world inputs.  This is an A3 preflight regression,
** not evidence that the original definition or WWPhys world loaders ran.
*/
struct A30WorldPreflightFingerprint
{
	bool m00_archive_file_available;
	bool m00_archive_file_opened;
	bool m00_mix_valid;
	bool m00_mix_enumerated;
	bool m00_entry_count_exact;
	bool ldd_name_enumerated;
	bool lsd_name_enumerated;
	bool dep_name_enumerated;

	bool always_dbs_mix_valid;
	bool objects_ddb_enumerated_in_always_dbs;
	bool objects_ddb_source_is_always_dbs;
	bool objects_ddb_available;
	bool objects_ddb_opened;
	bool objects_ddb_size_exact;

	bool ldd_available;
	bool ldd_opened;
	bool ldd_size_exact;
	bool lsd_available;
	bool lsd_opened;
	bool lsd_size_exact;
	bool dep_available;
	bool dep_opened;
	bool dep_size_exact;

	bool original_chunk_loader;
	bool level_info_chunk_found;
	bool level_data_chunk_found;
	bool map_filename_read;
	bool map_filename_exact;

	uint32_t m00_archive_size;
	uint32_t m00_archive_entries;
	uint32_t always_dbs_entries;
	uint32_t objects_ddb_size;
	uint32_t ldd_size;
	uint32_t lsd_size;
	uint32_t dep_size;
	uint32_t ldd_top_level_chunk_count;
	uint32_t ldd_top_level_ids[4];
	uint32_t ldd_top_level_lengths[4];
	char objects_ddb_provider[32];
	char map_filename[64];
};

/*
** Reserved result surface for the next coherent step: genuine original
** definition, SaveLoad and WWPhys/PhysicsScene execution.  The preflight
** leaves attempted false and all counts zero.
*/
struct A30WorldRuntimeFingerprint
{
	bool attempted;
	bool definitions_initialized;
	bool physics_scene_initialized;
	bool static_world_loaded;
	bool post_load_completed;
	bool first_render_traversal;
	uint32_t definition_count;
	uint32_t static_object_count;
	uint32_t static_light_count;
	uint32_t render_object_count;
	uint32_t mesh_count;
	uint32_t vertex_count;
	uint32_t polygon_count;
	uint32_t missing_factory_requests;
	uint32_t missing_asset_requests;
};

struct A30WorldSelfTestResult
{
	bool passed;
	bool preflight_passed;
	unsigned checks;
	unsigned failures;
	A30WorldPreflightFingerprint preflight;
	A30WorldRuntimeFingerprint world;
	char first_failure[128];
};

A30WorldSelfTestResult Run_A30_World_Self_Test(
	const RenegadePathRoots &roots);
