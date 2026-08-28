#pragma once

#include <stdint.h>

#include "a31_mission_completion_latch.h"

/*
** Shared A3.1 interactive-runtime policy.  Platform adapters may provide
** clocks, controller samples, presentation, and logging; they do not choose
** Combat/HUD lifecycle arguments or the original simulation order.
*/
struct A31InteractiveHUDState
{
	bool serialized_enabled;
	bool render_resources_available;
	bool effectively_displayable;
};

/* Original GameModeManager rendering collects PhysicsScene visibility before
** CombatManager::Render and releases the visible lists after the frame. */
struct A31InteractiveRenderTrace
{
	bool scene_available;
	bool camera_available;
	bool star_available;
	bool pre_render_completed;
	bool begin_render_completed;
	bool combat_render_called;
	bool end_render_completed;
	bool post_render_completed;
	bool message_window_available;
	bool message_window_render_called;
	bool objective_viewer_render_called;
	uint64_t mesh_submissions;
	uint64_t vertex_submissions;
	uint64_t triangle_submissions;
	uint64_t rejected_submissions;
	uint64_t unsupported_submissions;
	uintptr_t scene_pointer;
	uintptr_t camera_pointer;
	uintptr_t star_pointer;
	uint32_t static_object_count;
	uint32_t dynamic_object_count;
	uint32_t static_light_count;
	uint32_t visibility_table_size;
	uint32_t visibility_table_count;
	float camera_x;
	float camera_y;
	float camera_z;
	float player_x;
	float player_y;
	float player_z;
	uint32_t player_object_id;
	char player_definition[96];
	char player_state[32];
	float player_orientation[4];
	float player_velocity[3];
	float player_health;
	bool player_physics_registered;
	bool player_grounded;
	bool weapon_present;
	uint32_t weapon_definition_id;
	char weapon_definition[96];
	int32_t weapon_total_rounds;
	int32_t weapon_clip_rounds;
	uint32_t weapon_total_rounds_fired;
	int32_t weapon_state;
	bool weapon_triggered;
	bool weapon_fired_this_frame;
	uint32_t action_act_count;
	bool action_active;
	bool action_busy;
	float near_clip;
	float far_clip;
};

/* Bounded read-only M00 flight-recorder state. Objective IDs 1..6 are the
** official Mission00 primary objectives. Missing entries remain -1. */
struct A31MissionProgressState
{
	bool star_available;
	bool player_control_enabled;
	uint32_t objective_count;
	int32_t objective_status[6];
	uint32_t active_conversation_count;
	int32_t active_conversation_id;
	int32_t active_conversation_state;
	int32_t active_conversation_action_id;
	int32_t active_conversation_current_remark;
	int32_t active_conversation_remark_count;
	int32_t active_conversation_text_id;
	int32_t active_conversation_sound_id;
	bool active_conversation_string_available;
	bool active_conversation_sound_definition_available;
	float active_conversation_next_remark_seconds;
	char active_conversation_name[96];
	int32_t active_conversation_speech_source;
	int32_t active_conversation_speech_class_id;
	int32_t active_conversation_speech_type;
	int32_t active_conversation_speech_state;
	uint32_t active_conversation_speech_duration_ms;
	bool active_conversation_speaker_available;
	bool active_conversation_speech_available;
	bool active_conversation_speech_in_scene;
	bool active_conversation_speech_culled;
	bool active_conversation_speech_playing;
	float active_conversation_speech_dropoff_radius;
	float active_conversation_speech_listener_distance;
};

bool A31_Interactive_Render_HUD_Available();
A31InteractiveHUDState A31_Interactive_Get_HUD_State();
/* Render-to-texture projectors create additional material passes.  The Vita
** backend has no render-target projector implementation at this milestone;
** retain original scene traversal while centrally selecting its original
** no-projector performance mode. */
void A31_Interactive_Apply_Render_Capabilities();
// Bind the Vita controller only through original Input functions and slider
// identifiers.  Player, camera, action, and simulation ownership remains in
// Commando/Combat.
void A31_Interactive_Configure_Vita_Controls();
void A31_Interactive_Run_Simulation_Frame();
A31InteractiveRenderTrace A31_Interactive_Run_Render_Frame();
/* Install a presentation/lifecycle observer at CombatManager's original misc
** handler seam. Mission00 and Combat remain the sole owners of completion. */
void A31_Interactive_Begin_Mission_Completion_Observation();
A31MissionCompletionState A31_Interactive_Get_Mission_Completion_State();
void A31_Interactive_End_Mission_Completion_Observation();
/* Observe only original ObjectiveManager, ConversationMgr, and Star state.
** This API cannot advance scripts, objectives, or player control. */
A31MissionProgressState A31_Interactive_Get_Mission_Progress_State();
