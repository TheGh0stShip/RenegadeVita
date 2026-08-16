#pragma once

#include <stdint.h>

class PhysicsSceneClass;
class WW3DAssetManager;
struct A30WorldRuntimeFingerprint;

struct A30HostWorldRenderResult
{
	bool attempted;
	bool camera_initialized;
	bool pre_render_completed;
	bool begin_render_completed;
	bool scene_render_completed;
	bool end_render_completed;
	bool post_render_completed;
	bool frame_path_completed;

	float camera_position[3];
	float camera_target[3];
	float near_clip;
	float far_clip;

	uint32_t frames;
	uint32_t mesh_submissions;
	uint32_t vertex_submissions;
	uint32_t triangle_submissions;
	uint32_t geometry_checksum;
	uint32_t indexed_submissions;
	uint32_t indexed_vertex_references;
	uint32_t indexed_triangle_submissions;
	uint32_t indexed_geometry_checksum;
	uint32_t rejected_indexed_submissions;
	uint32_t unsupported_submissions;
};

bool A30_Render_Loaded_World(void *context, PhysicsSceneClass &scene,
	WW3DAssetManager &asset_manager, const A30WorldRuntimeFingerprint &world);
