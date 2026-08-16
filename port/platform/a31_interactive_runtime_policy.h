#pragma once

#include <stdint.h>

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
	float near_clip;
	float far_clip;
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
