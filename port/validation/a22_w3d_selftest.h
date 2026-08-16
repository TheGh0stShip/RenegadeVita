#pragma once

#include "renegade_paths.h"

#include <stdint.h>

struct A22W3DSelfTestResult {
	bool passed;
	bool original_chunk_loader;
	bool hierarchy_found;
	bool hierarchy_header_read;
	bool asset_manager_loaded;
	bool render_object_created;
	bool renderer_initialized;
	bool original_scene_rendered;
	bool render_loop_exit_requested;
	unsigned checks;
	unsigned failures;
	unsigned top_level_chunk_count;
	uint32_t top_level_ids[16];
	uint32_t top_level_lengths[16];
	unsigned hierarchy_pivots;
	char hierarchy_name[32];
	unsigned prototype_count;
	char prototype_names[16][64];
	int prototype_class_ids[16];
	char render_object_name[64];
	int render_object_class_id;
	unsigned render_object_subobjects;
	unsigned mesh_count;
	unsigned vertex_count;
	unsigned polygon_count;
	unsigned material_count;
	unsigned texture_count;
	unsigned render_hierarchy_pivots;
	char render_hierarchy_name[32];
	float bounding_sphere_center[3];
	float bounding_sphere_radius;
	float bounding_box_center[3];
	float bounding_box_extent[3];
	uint32_t rendered_frames;
	uint32_t rendered_meshes;
	uint32_t rendered_vertices;
	uint32_t rendered_triangles;
	uint32_t unsupported_render_objects;
	uint32_t rendered_geometry_checksum;
	char first_failure[96];
};

struct A22CameraControlState {
	float yaw;
	float pitch;
	float distance;
};

typedef bool (*A22CameraUpdateCallback)(void *context,
	A22CameraControlState &camera);

struct A22W3DRenderOptions {
	bool present_frames;
	unsigned maximum_frames;
	A22CameraUpdateCallback update_camera;
	void *context;
};

A22W3DSelfTestResult Run_A22_W3D_Self_Test(const RenegadePathRoots &roots,
	const A22W3DRenderOptions *render_options = NULL);
