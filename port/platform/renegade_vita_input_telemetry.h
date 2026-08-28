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
};

const RenegadeVitaInputTelemetry &Renegade_Vita_Last_Input_Telemetry();
void Renegade_Vita_Input_Route_Set_Gameplay_Active(bool active, uint32_t frame_index);
bool Renegade_Vita_Input_Route_Replay_Exit_Requested();
