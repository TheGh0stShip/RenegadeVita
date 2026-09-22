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
	bool return_to_menu_requested;
	bool frontend_exit_requested;
	char reload_source[96];
	char campaign_next_source[96];
	uint8_t campaign_state[64];
	uint32_t campaign_state_size;
	bool campaign_handoff_completed;
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

/* Runs an original frontend/session lifecycle against the live Vita renderer.
** Credits request frontend reentry only after complete owned teardown. */
A31VitaInteractiveResult A31_Vita_Run_Interactive_Runtime(
	int startup_screen_result = -1, bool start_at_main_menu = false,
	const char *reload_source = nullptr, const char *campaign_source = nullptr,
	const uint8_t *campaign_state = nullptr, uint32_t campaign_state_size = 0);
