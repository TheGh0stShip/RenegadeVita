#pragma once

#include <stdint.h>

/*
** Result from the native A3.1 continuation.  The session, player, scene,
** input actions, replication queues, and simulation all remain owned by the
** original Commando/Combat classes.  This records only lifecycle evidence at
** the Vita application boundary.
*/
struct A31VitaInteractiveResult
{
	bool attempted;
	bool initialized;
	bool transport_established;
	bool level_loaded;
	bool player_created;
	bool player_registered;
	bool commando_created;
	bool first_frame_completed;
	bool first_frame_geometry;
	bool clean_exit_requested;
	bool start_exit_requested;
	bool mission_completion_observed;
	bool mission_succeeded;
	bool star_killed_observed;
	bool render_error;
	bool teardown_completed;
	bool pause_observed;
	bool resume_observed;
	uint32_t frames;
	uint32_t paused_input_frames;
	uint32_t mesh_submissions;
	uint32_t vertex_submissions;
	uint32_t triangle_submissions;
	uint32_t average_fps_milli;
	uint32_t median_frame_us;
	uint32_t p95_frame_us;
	uint32_t worst_frame_us;
	uint32_t average_simulation_us;
	uint32_t average_render_us;
	uint32_t average_sync_us;
};

/* Runs the original M00 single-player session against the live Vita renderer.
** The function returns only after START or a durable diagnosed failure. */
A31VitaInteractiveResult A31_Vita_Run_Interactive_Runtime();
