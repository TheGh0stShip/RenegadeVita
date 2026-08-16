#include "a30_world_runtime.h"
#include "world_render_callback.h"

#if defined(RENEGADE_VITA_A31)
#include "a31_audio_lifecycle.h"
#include "wwaudio.h"
#endif

#include <stdio.h>

extern "C" unsigned Renegade_A30_Host_Unsupported_GPU_Call_Count();
extern "C" unsigned Renegade_A30_Host_Default_Render_Target_Reset_Count();

namespace {

const char *Yes_No(bool value)
{
	return value ? "true" : "false";
}

void Print_Bool(const char *name, bool value)
{
	printf("world.%s=%s\n", name, Yes_No(value));
}

void Print_U32(const char *name, uint32_t value)
{
	printf("world.%s=%u\n", name, static_cast<unsigned>(value));
}

void Print_U64(const char *name, uint64_t value)
{
	printf("world.%s=%llu\n", name,
		static_cast<unsigned long long>(value));
}

void Check(A30WorldRuntimeResult &result, bool condition, const char *name)
{
	++result.checks;
	if (condition) {
		return;
	}

	++result.failures;
	if (result.first_failure[0] == 0) {
		snprintf(result.first_failure, sizeof(result.first_failure), "%s", name);
	}
}

} // namespace

int main(int argc, char **argv)
{
	if (argc != 5) {
		fprintf(stderr,
			"usage: %s RETAIL_ROOT USER_ROOT CACHE_ROOT MODS_ROOT\n", argv[0]);
		return 2;
	}

	const RenegadePathRoots roots = { argv[1], argv[2], argv[3], argv[4] };
	A30HostWorldRenderResult render = {};
	const A30WorldRuntimeOptions options = {
		&A30_Render_Loaded_World,
		&render,
		NULL,
		NULL,
	};
	A30WorldRuntimeResult result = {};
#if defined(RENEGADE_VITA_A31)
	/* Match original Commando ordering: a silent but valid WWAudio owner exists
	** before the static M00 stream can dispatch StaticAudioSaveLoadClass. */
	bool audio_lifecycle_passed = true;
	A31AudioLifecycleTrace audio_trace = {};
	for (unsigned cycle = 0U; cycle != 2U; ++cycle) {
		audio_lifecycle_passed &= WWAudioClass::Get_Instance() == NULL;
		A31_Audio_Lifecycle_Reset_Trace();
		{
			WWAudioClass audio(true);
			A30WorldRuntimeResult cycle_result =
				Run_A30_World_Runtime(roots, &options);
			audio_trace = A31_Audio_Lifecycle_Get_Trace();
			audio_lifecycle_passed &= cycle_result.passed &&
				WWAudioClass::Get_Instance() == &audio &&
				audio_trace.static_audio_load_entries > 0U &&
				audio_trace.singleton_present_at_static_load &&
				!audio_trace.sound_scene_present_at_static_load;
			result = cycle_result;
		}
		audio_lifecycle_passed &= WWAudioClass::Get_Instance() == NULL;
	}
	if (!audio_lifecycle_passed) {
		++result.failures;
		if (result.first_failure[0] == 0) {
			snprintf(result.first_failure, sizeof(result.first_failure),
				"A3.1 WWAudio/M00 lifecycle regression");
		}
		result.passed = false;
	}
	printf("audio.initial_singleton_null=%s\n",
		audio_lifecycle_passed ? "true" : "false");
	printf("audio.static_load_entries=%u\n",
		audio_trace.static_audio_load_entries);
	printf("audio.static_load_singleton_present=%s\n",
		audio_trace.singleton_present_at_static_load ? "true" : "false");
	printf("audio.static_load_sound_scene_present=%s\n",
		audio_trace.sound_scene_present_at_static_load ? "true" : "false");
	printf("audio.repeated_teardown_singleton_null=%s\n",
		WWAudioClass::Get_Instance() == NULL ? "true" : "false");
#else
	result = Run_A30_World_Runtime(roots, &options);
#endif
	const A30WorldRuntimeFingerprint &world = result.world;
	const unsigned unsupported_gpu_calls =
		Renegade_A30_Host_Unsupported_GPU_Call_Count();
	const unsigned default_render_target_resets =
		Renegade_A30_Host_Default_Render_Target_Reset_Count();

	/* These exact values were recorded only after the first successful
	** unchanged-retail traversal through the original PhysicsScene, Camera and
	** WW3D render path. They are regression assertions, never construction
	** inputs for the scene or renderer. */
	Check(result, render.frames == 1U,
		"original M00 render frame count");
	Check(result, render.mesh_submissions == 652U,
		"original M00 MeshClass submission count");
	Check(result, render.vertex_submissions == 30603U,
		"original M00 submitted-vertex count");
	Check(result, render.triangle_submissions == 16939U,
		"original M00 submitted-triangle count");
	Check(result, render.geometry_checksum == 0x34FFAD42U,
		"original M00 submitted-geometry checksum");
	Check(result,
		render.indexed_submissions == 0U &&
		render.indexed_vertex_references == 0U &&
		render.indexed_triangle_submissions == 0U &&
		render.indexed_geometry_checksum == 0U,
		"original M00 indexed-submission fingerprint");
	Check(result,
		render.rejected_indexed_submissions == 0U &&
		render.unsupported_submissions == 0U,
		"original M00 accepted-submission fingerprint");
#if defined(RENEGADE_VITA_A31)
	/* The A3.1 lifecycle regression intentionally loads/tears down M00 twice
	** in one process. Each original projector pass restores the default target
	** exactly once, so this cumulative host-only counter must be two. */
	Check(result, default_render_target_resets == 2U,
		"two-cycle original projector default-target restore count");
#else
	Check(result, default_render_target_resets == 1U,
		"original projector pass default-target restore count");
#endif
	Check(result, unsupported_gpu_calls == 0U,
		"host renderer boundary remained within supported operations");
	result.passed = result.failures == 0U;

	printf("A3.0 original M00 world runtime\n");
	printf("runtime.checks=%u\n", result.checks);
	printf("runtime.failures=%u\n", result.failures);
	printf("runtime.first_failure=%s\n", result.first_failure);

	Print_Bool("attempted", world.attempted);
	Print_Bool("clean_engine_entry_state", world.clean_engine_entry_state);
	Print_Bool("audio_boundary_ready", world.audio_boundary_ready);
	Print_Bool("audio_sound_scene_available", world.audio_sound_scene_available);
	Print_Bool("factory_chain_ready", world.factory_chain_ready);
	Print_Bool("required_subsystems_registered",
		world.required_subsystems_registered);
	Print_Bool("required_persist_factories_registered",
		world.required_persist_factories_registered);
	Print_Bool("ww3d_initialized", world.ww3d_initialized);
	Print_Bool("wwphys_initialized", world.wwphys_initialized);
	Print_Bool("wwsaveload_initialized", world.wwsaveload_initialized);
	Print_Bool("armor_warhead_initialized", world.armor_warhead_initialized);
	Print_Bool("asset_manager_load_on_demand",
		world.asset_manager_load_on_demand);
	Print_Bool("physics_scene_initialized", world.physics_scene_initialized);
	Print_Bool("objects_ddb_loaded", world.objects_ddb_loaded);
	Print_Bool("optional_level_ddb_missing", world.optional_level_ddb_missing);
	Print_Bool("optional_level_ddb_noop", world.optional_level_ddb_noop);
	Print_Bool("m00_static_world_loaded", world.m00_static_world_loaded);
	Print_Bool("post_load_completed", world.post_load_completed);
	Print_Bool("pathfind_data_loaded", world.pathfind_data_loaded);
	Print_Bool("render_graph_complete", world.render_graph_complete);
	Print_Bool("world_callback_invoked", world.world_callback_invoked);
	Print_Bool("world_callback_completed", world.world_callback_completed);
	Print_Bool("teardown_completed", world.teardown_completed);

	Print_U32("required_subsystem_count", world.required_subsystem_count);
	Print_U32("registered_subsystem_count", world.registered_subsystem_count);
	Print_U32("required_persist_factory_count",
		world.required_persist_factory_count);
	Print_U32("registered_persist_factory_count",
		world.registered_persist_factory_count);
	printf("world.first_missing_persist_factory=%08X\n",
		static_cast<unsigned>(world.first_missing_persist_factory));

	Print_U32("definition_count", world.definition_count);
	Print_U32("twiddler_definition_count", world.twiddler_definition_count);
	Print_U32("definition_count_after_optional_ddb",
		world.definition_count_after_optional_ddb);
	printf("world.definition_checksum=%08X\n",
		static_cast<unsigned>(world.definition_checksum));
	printf("world.definition_checksum_after_optional_ddb=%08X\n",
		static_cast<unsigned>(world.definition_checksum_after_optional_ddb));
	Print_U32("static_phys_definition_count",
		world.static_phys_definition_count);
	Print_U32("static_anim_phys_definition_count",
		world.static_anim_phys_definition_count);
	Print_U32("accessible_phys_definition_count",
		world.accessible_phys_definition_count);
	Print_U32("door_phys_definition_count", world.door_phys_definition_count);
	Print_U32("elevator_phys_definition_count",
		world.elevator_phys_definition_count);
	Print_U32("damageable_static_phys_definition_count",
		world.damageable_static_phys_definition_count);
	Print_U32("building_aggregate_definition_count",
		world.building_aggregate_definition_count);
	Print_U32("m00_required_definition_count",
		world.m00_required_definition_count);
	Print_U32("armor_type_count", world.armor_type_count);
	Print_U32("warhead_type_count", world.warhead_type_count);

	Print_U32("static_object_count", world.static_object_count);
	Print_U32("static_light_count", world.static_light_count);
	Print_U32("static_anim_iterator_count", world.static_anim_iterator_count);
	Print_U32("dynamic_object_count", world.dynamic_object_count);
	Print_U32("definition_backed_object_count",
		world.definition_backed_object_count);
	Print_U32("definitionless_object_count", world.definitionless_object_count);
	Print_U32("render_model_count", world.render_model_count);
	Print_U32("null_render_model_count", world.null_render_model_count);
	Print_U32("static_phys_count", world.static_phys_count);
	Print_U32("static_anim_phys_count", world.static_anim_phys_count);
	Print_U32("door_phys_count", world.door_phys_count);
	Print_U32("elevator_phys_count", world.elevator_phys_count);
	Print_U32("damageable_static_phys_count",
		world.damageable_static_phys_count);
	Print_U32("building_aggregate_count", world.building_aggregate_count);
	Print_U32("unclassified_static_object_count",
		world.unclassified_static_object_count);

	Print_U32("render_object_node_count", world.render_object_node_count);
	Print_U32("mesh_count", world.mesh_count);
	Print_U64("mesh_vertex_count", world.mesh_vertex_count);
	Print_U64("mesh_polygon_count", world.mesh_polygon_count);
	Print_U32("terrain_patch_count", world.terrain_patch_count);
	Print_U64("terrain_vertex_count", world.terrain_vertex_count);
	Print_U64("terrain_material_count", world.terrain_material_count);
	Print_U32("loaded_prototype_count", world.loaded_prototype_count);
	printf("world.object_identity_checksum=%08X\n",
		static_cast<unsigned>(world.object_identity_checksum));
	printf("world.render_graph_checksum=%08X\n",
		static_cast<unsigned>(world.render_graph_checksum));
	printf("world.prototype_checksum=%08X\n",
		static_cast<unsigned>(world.prototype_checksum));
	Print_U32("vis_object_count", world.vis_object_count);
	Print_U32("vis_sector_count", world.vis_sector_count);
	printf("world.level_min=(%.6f,%.6f,%.6f)\n", world.level_min[0],
		world.level_min[1], world.level_min[2]);
	printf("world.level_max=(%.6f,%.6f,%.6f)\n", world.level_max[0],
		world.level_max[1], world.level_max[2]);
	Print_Bool("render.attempted", render.attempted);
	Print_Bool("render.camera_initialized", render.camera_initialized);
	Print_Bool("render.pre_render_completed", render.pre_render_completed);
	Print_Bool("render.begin_render_completed", render.begin_render_completed);
	Print_Bool("render.scene_render_completed", render.scene_render_completed);
	Print_Bool("render.end_render_completed", render.end_render_completed);
	Print_Bool("render.post_render_completed", render.post_render_completed);
	Print_Bool("render.frame_path_completed", render.frame_path_completed);
	printf("world.render.camera_position=(%.6f,%.6f,%.6f)\n",
		render.camera_position[0], render.camera_position[1],
		render.camera_position[2]);
	printf("world.render.camera_target=(%.6f,%.6f,%.6f)\n",
		render.camera_target[0], render.camera_target[1],
		render.camera_target[2]);
	printf("world.render.clip=(%.6f,%.6f)\n", render.near_clip,
		render.far_clip);
	Print_U32("render.frames", render.frames);
	Print_U32("render.mesh_submissions", render.mesh_submissions);
	Print_U32("render.vertex_submissions", render.vertex_submissions);
	Print_U32("render.triangle_submissions", render.triangle_submissions);
	printf("world.render.geometry_checksum=%08X\n",
		static_cast<unsigned>(render.geometry_checksum));
	Print_U32("render.indexed_submissions", render.indexed_submissions);
	Print_U32("render.indexed_vertex_references",
		render.indexed_vertex_references);
	Print_U32("render.indexed_triangle_submissions",
		render.indexed_triangle_submissions);
	printf("world.render.indexed_geometry_checksum=%08X\n",
		static_cast<unsigned>(render.indexed_geometry_checksum));
	Print_U32("render.rejected_indexed_submissions",
		render.rejected_indexed_submissions);
	Print_U32("render.unsupported_submissions",
		render.unsupported_submissions);

	printf("world.default_render_target_resets=%u\n",
		default_render_target_resets);
	printf("world.unsupported_gpu_calls=%u\n", unsupported_gpu_calls);
	printf("A3.0 original M00 world runtime: %s\n",
		result.passed ? "PASS" : "FAIL");
	return result.passed ? 0 : 1;
}
