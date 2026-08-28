#pragma once

#include "a30_world_runtime.h"

#include <stdint.h>

struct A30VitaWorldRenderResult
{
	bool attempted;
	bool camera_initialized;
	bool first_frame_completed;
	bool clean_exit_requested;
	bool render_error;

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

	float camera_position[3];
	float camera_target[3];
	float near_clip;
	float far_clip;
};

/*
** Persistent A3.0 diagnostic output.  Every call opens, writes, synchronizes,
** and closes the log so the final completed world-load/render stage survives
** a crash or power-cycle on physical hardware.
*/
int A30_Vita_Log_Reset();
int A30_Vita_Log(const char *format, ...);

/*
** Bounded, candidate-only flight recorder for the original static-object
** loader.  The outer loader supplies object/factory context; nested original
** loaders report only phase and chunk identifiers.  The implementation
** samples outer objects and enables the deeper trace only around the physical
** hang window, keeping durable I/O bounded.
*/
void A35_Vita_Static_Load_Trace_Begin(uint32_t object_index,
	uint32_t factory_id);
void A35_Vita_Static_Load_Trace_Step(const char *phase, uint32_t detail_id);
void A35_Vita_Static_Load_Trace_Name(const char *phase, const char *name);
void A35_Vita_Static_Load_Trace_End();

/*
** Borrowed-world continuation passed to Run_A30_World_Runtime.  It preserves
** Westwood ownership and traversal and only bridges Vita controls to a
** temporary CameraClass development rig until the original player/input
** runtime becomes part of the same milestone.
*/
bool A30_Vita_Render_Loaded_World(void *context, PhysicsSceneClass &scene,
	WW3DAssetManager &asset_manager, const A30WorldRuntimeFingerprint &world);

void A30_Vita_Log_World_Result(const A30WorldRuntimeResult &world_result,
	const A30VitaWorldRenderResult &render_result);
