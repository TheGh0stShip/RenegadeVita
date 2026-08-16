#pragma once

#include "renegade_paths.h"

#include <stdint.h>

class PhysicsSceneClass;
class WW3DAssetManager;
struct A30WorldRuntimeFingerprint;

/*
** Optional platform/application continuation invoked while the genuine loaded
** PhysicsScene and its original WW3DAssetManager are still alive.  This is the
** intended seam for the A3 render/input loop; it does not replace either
** Westwood object ownership or scene traversal.  Both references are borrowed
** for the duration of the callback and must not be retained after it returns.
*/
typedef bool (*A30WorldLoadedCallback)(void *context,
	PhysicsSceneClass &scene, WW3DAssetManager &asset_manager,
	const A30WorldRuntimeFingerprint &world);

/* Called at durable load boundaries without changing original world ownership.
** The application uses this to persist physical-hardware crash breadcrumbs. */
typedef void (*A30WorldStageCallback)(void *context, const char *stage);

struct A30WorldRuntimeOptions
{
	A30WorldLoadedCallback world_loaded_callback;
	void *callback_context;
	A30WorldStageCallback stage_callback;
	void *stage_context;
};

/*
** Semantic evidence collected exclusively through original Westwood managers,
** factories, persisted objects and PhysicsScene iterators.  No retail format is
** parsed by this validation layer.
*/
struct A30WorldRuntimeFingerprint
{
	bool attempted;
	bool clean_engine_entry_state;
	bool audio_boundary_ready;
	bool audio_sound_scene_available;
	bool factory_chain_ready;
	bool required_subsystems_registered;
	bool required_persist_factories_registered;
	bool ww3d_initialized;
	bool wwphys_initialized;
	bool wwsaveload_initialized;
	bool armor_warhead_initialized;
	bool asset_manager_load_on_demand;
	bool physics_scene_initialized;
	bool objects_ddb_loaded;
	bool optional_level_ddb_missing;
	bool optional_level_ddb_noop;
	bool m00_static_world_loaded;
	bool post_load_completed;
	bool pathfind_data_loaded;
	bool render_graph_complete;
	bool world_callback_invoked;
	bool world_callback_completed;
	bool teardown_completed;

	uint32_t required_subsystem_count;
	uint32_t registered_subsystem_count;
	uint32_t required_persist_factory_count;
	uint32_t registered_persist_factory_count;
	uint32_t first_missing_persist_factory;

	uint32_t definition_count;
	uint32_t twiddler_definition_count;
	uint32_t definition_count_after_optional_ddb;
	uint32_t definition_checksum;
	uint32_t definition_checksum_after_optional_ddb;
	uint32_t static_phys_definition_count;
	uint32_t static_anim_phys_definition_count;
	uint32_t accessible_phys_definition_count;
	uint32_t door_phys_definition_count;
	uint32_t elevator_phys_definition_count;
	uint32_t damageable_static_phys_definition_count;
	uint32_t building_aggregate_definition_count;
	uint32_t m00_required_definition_count;
	uint32_t armor_type_count;
	uint32_t warhead_type_count;

	uint32_t static_object_count;
	uint32_t static_light_count;
	uint32_t static_anim_iterator_count;
	uint32_t dynamic_object_count;
	uint32_t definition_backed_object_count;
	uint32_t definitionless_object_count;
	uint32_t render_model_count;
	uint32_t null_render_model_count;

	uint32_t static_phys_count;
	uint32_t static_anim_phys_count;
	uint32_t door_phys_count;
	uint32_t elevator_phys_count;
	uint32_t damageable_static_phys_count;
	uint32_t building_aggregate_count;
	uint32_t unclassified_static_object_count;

	uint32_t render_object_node_count;
	uint32_t mesh_count;
	uint64_t mesh_vertex_count;
	uint64_t mesh_polygon_count;
	uint32_t terrain_patch_count;
	uint64_t terrain_vertex_count;
	uint64_t terrain_material_count;
	uint32_t loaded_prototype_count;
	uint32_t object_identity_checksum;
	uint32_t render_graph_checksum;
	uint32_t prototype_checksum;

	uint32_t vis_object_count;
	uint32_t vis_sector_count;
	float level_min[3];
	float level_max[3];
};

struct A30WorldRuntimeResult
{
	bool passed;
	unsigned checks;
	unsigned failures;
	A30WorldRuntimeFingerprint world;
	char first_failure[128];
};

/*
** Standalone coherent M00 runtime proof.  The call requires a clean singleton
** entry state, performs the original initialization/load sequence, invokes the
** optional continuation with the live world, then tears ownership down in the
** original subsystem order.  A missing factory is a hard failure and prevents
** persisted world loading rather than silently manufacturing replacement data.
*/
A30WorldRuntimeResult Run_A30_World_Runtime(
	const RenegadePathRoots &roots,
	const A30WorldRuntimeOptions *options = NULL);
