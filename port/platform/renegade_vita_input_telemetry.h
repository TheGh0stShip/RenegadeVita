#pragma once

#include <stdint.h>

// Bounded snapshot emitted by the sole Vita device-to-DirectInput boundary.
// It records delivery only; original Input/Combat retains action and camera
// ownership. Consumers sample it at durable checkpoints, never per-frame log.
struct RenegadeVitaInputTelemetry
{
	uint8_t lx;
	uint8_t ly;
	uint8_t rx;
	uint8_t ry;
	float normalized_lx;
	float normalized_ly;
	float normalized_rx;
	float normalized_ry;
	int32_t logical_lx;
	int32_t logical_ly;
	int32_t logical_rx;
	int32_t logical_ry;
	int32_t mouse_dx;
	int32_t mouse_dy;
	float frame_seconds;
	uint32_t buttons;
	uint64_t sample_count;
	uint32_t route_mode;
	uint32_t route_gameplay_active;
	uint32_t route_sample_index;
	uint32_t route_sample_count;
	uint32_t route_truncated;
	uint32_t square_down;
	uint32_t triangle_down;
	uint32_t select_down;
	uint32_t circle_down;
	uint32_t cross_down;
	uint32_t left_shoulder_down;
	uint32_t right_shoulder_down;
	uint32_t front_touch_down;
	uint32_t dpad_up_down;
	uint32_t dpad_down_down;
	uint32_t dpad_left_down;
	uint32_t dpad_right_down;
	uint32_t action_key_state;
	uint32_t reload_key_state;
	uint32_t camera_toggle_key_state;
	uint32_t previous_weapon_key_state;
	uint32_t next_weapon_key_state;
	uint32_t zoom_in_key_state;
	uint32_t zoom_out_key_state;
	uint32_t objectives_toggle_key_state;
};

const RenegadeVitaInputTelemetry &Renegade_Vita_Last_Input_Telemetry();
void Renegade_Vita_Input_Route_Set_Gameplay_Active(bool active, uint32_t frame_index);
bool Renegade_Vita_Input_Route_Replay_Exit_Requested();
