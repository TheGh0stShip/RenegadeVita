#pragma once

#include <stdint.h>

enum A31CampaignHandoffFailure : uint32_t
{
	A31_CAMPAIGN_HANDOFF_NO_FAILURE = 0,
	A31_CAMPAIGN_HANDOFF_END_GAME_NOT_CONSUMED = 1,
	A31_CAMPAIGN_HANDOFF_SOURCE_REJECTED = 2,
	A31_CAMPAIGN_HANDOFF_STATE_OPEN_FAILED = 3,
	A31_CAMPAIGN_HANDOFF_STATE_SAVE_FAILED = 4,
	A31_CAMPAIGN_HANDOFF_STATE_SIZE_INVALID = 5,
	A31_CAMPAIGN_HANDOFF_CATALOG_RESTORE_FAILED = 6,
	A31_CAMPAIGN_HANDOFF_STATE_READ_FAILED = 7,
	A31_CAMPAIGN_HANDOFF_STATE_LOAD_FAILED = 8,
	A31_CAMPAIGN_HANDOFF_STATE_SOURCE_MISMATCH = 9,
	A31_CAMPAIGN_HANDOFF_PRESENTATION_OWNER_LOST = 10
};

#if defined(__vita__) && !RENEGADE_VITA_M00_DEMO
// Borrows the original Load_Level stack screen only while it remains alive.
// No screen ownership, saved state or gameplay lifecycle is transferred.
class A31VitaScopedOriginalLoadingScreenCallback
{
public:
	explicit A31VitaScopedOriginalLoadingScreenCallback(void *screen);
	~A31VitaScopedOriginalLoadingScreenCallback();
	A31VitaScopedOriginalLoadingScreenCallback(const A31VitaScopedOriginalLoadingScreenCallback &) = delete;
	A31VitaScopedOriginalLoadingScreenCallback &operator=(const A31VitaScopedOriginalLoadingScreenCallback &) = delete;

private:
	void *Previous;
};
#endif

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
	// Native lifecycle evidence only; never serialized into original saves.
	uint32_t level_load_failure;
	bool load_failure_cleanup_completed;
	bool teardown_completed;
	bool pause_observed;
	bool resume_observed;
	bool return_to_menu_requested;
	bool return_to_lan_menu_requested;
	bool frontend_exit_requested;
	char frontend_next_source[96];
	bool frontend_next_skirmish;
	bool frontend_selection_deferred;
	char reload_source[96];
	bool reload_is_replay;
	int reload_replay_difficulty;
	char campaign_next_source[96];
	uint8_t campaign_state[64];
	uint32_t campaign_state_size;
	bool campaign_handoff_completed;
	uint32_t campaign_handoff_failure;
	bool campaign_handoff_cleanup_completed;
	uint32_t world_generations_started;
	uint32_t world_generations_bound;
	uint32_t world_generations_rendered;
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
	bool start_at_lan_menu = false,
	const char *reload_source = nullptr, const char *campaign_source = nullptr,
	const uint8_t *campaign_state = nullptr, uint32_t campaign_state_size = 0,
	int reload_replay_difficulty = -1,
	const char *deferred_frontend_source = nullptr,
	bool deferred_frontend_skirmish = false);
