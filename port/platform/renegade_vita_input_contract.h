#pragma once

#include <stdint.h>

#include <math.h>

// Device-to-DirectInput contract for the Vita controller boundary.  Renegade's
// original joystick consumers divide this logical value by 1000.0f before
// applying their own dead-zone and slider processing.  Keep that historic
// contract here; device values must never leak directly into gameplay code.
namespace RenegadeVitaInput {

// Select is a gameplay tap as well as a modifier. Emit its action on release
// only when no chord consumed the press, and require release after focus loss.
class SelectTap
{
public:
	SelectTap() : state(Blocked) {}
	void Reset() { state = Blocked; }
	bool Sample(bool select, bool chord, bool enabled)
	{
		if (!enabled) { Reset(); return false; }
		if (!select) {
			const bool action = state == Pressed && !chord;
			state = Ready;
			return action;
		}
		if (state == Ready) state = Pressed;
		if (chord && state == Pressed) state = Consumed;
		return false;
	}
private:
	enum State { Blocked, Ready, Pressed, Consumed } state;
};

enum : int32_t {
	DIRECTINPUT_AXIS_MIN = -1000,
	DIRECTINPUT_AXIS_MAX = 1000,
	DEVICE_CENTER = 128,
	DEVICE_NEGATIVE_RANGE = 128,
	DEVICE_POSITIVE_RANGE = 127
};

// These constants describe the Vita device boundary, not a replacement
// gameplay-control policy.  The original Input and CCamera classes continue
// to own bindings, action accumulation, sensitivity application and camera
// integration above this adapter.
static const float DEVICE_DEAD_ZONE = 0.15f;
static const float CAMERA_RESPONSE_EXPONENT = 1.35f;
static const float CAMERA_MOUSE_UNITS_PER_SECOND = 800.0f;
static const float DEFAULT_CAMERA_SENSITIVITY = 0.50f;
static const float MAX_INPUT_FRAME_SECONDS = 0.050f;

// These values are deliberately applied below the original Input action map.
// They describe only how a velocity-style Vita stick becomes an old mouse
// delta.  Input::Set_Mouse_Sensitivity and CCamera remain the authoritative
// game-facing sensitivity and rotation owners.
struct CameraResponseConfiguration
{
	float horizontal_scale;
	float vertical_scale;
	bool invert_y;
};

static const CameraResponseConfiguration DEFAULT_CAMERA_RESPONSE = {
	// Physical dev78 evidence showed CCamera still inverted for look up/down.
	// Keep the sign decision at this Vita mouse-delta boundary; original Input
	// and CCamera still own action mapping and integration.
	1.0f, 0.85f, true
};

inline float Clamp(float value, float minimum, float maximum)
{
	return value < minimum ? minimum : (value > maximum ? maximum : value);
}

inline float Normalize_Raw_Device_Axis(uint8_t value)
{
	const int32_t offset = static_cast<int32_t>(value) - DEVICE_CENTER;
	return static_cast<float>(offset) /
		static_cast<float>(offset < 0 ? DEVICE_NEGATIVE_RANGE : DEVICE_POSITIVE_RANGE);
}

inline float Apply_Dead_Zone(float normalized)
{
	const float magnitude = fabsf(normalized);
	if (magnitude <= DEVICE_DEAD_ZONE) return 0.0f;
	const float remapped = Clamp((magnitude - DEVICE_DEAD_ZONE) /
		(1.0f - DEVICE_DEAD_ZONE), 0.0f, 1.0f);
	return normalized < 0.0f ? -remapped : remapped;
}

inline float Normalize_Device_Axis(uint8_t value)
{
	return Apply_Dead_Zone(Normalize_Raw_Device_Axis(value));
}

inline int32_t To_DirectInput_Logical(float normalized)
{
	const float scaled = Clamp(normalized, -1.0f, 1.0f) *
		static_cast<float>(DIRECTINPUT_AXIS_MAX);
	return static_cast<int32_t>(scaled + (scaled >= 0.0f ? 0.5f : -0.5f));
}

inline int32_t To_DirectInput_Axis(uint8_t value)
{
	return To_DirectInput_Logical(Normalize_Device_Axis(value));
}

struct AxisSample
{
	uint8_t raw;
	float normalized;
	int32_t logical;
};

inline AxisSample Sample_Device_Axis(uint8_t value)
{
	AxisSample sample = {};
	sample.raw = value;
	sample.normalized = Normalize_Device_Axis(value);
	sample.logical = To_DirectInput_Axis(value);
	return sample;
}

struct StickSample
{
	AxisSample x;
	AxisSample y;
};

// Apply the dead zone radially, then restore the original direction. This
// prevents a diagonal full tilt from producing more input than either cardinal
// direction while retaining smooth, continuous motion immediately outside the
// neutral region.
inline StickSample Sample_Device_Stick(uint8_t x_value, uint8_t y_value)
{
	const float raw_x = Normalize_Raw_Device_Axis(x_value);
	const float raw_y = Normalize_Raw_Device_Axis(y_value);
	const float magnitude = sqrtf(raw_x * raw_x + raw_y * raw_y);
	float filtered_x = 0.0f;
	float filtered_y = 0.0f;
	if (magnitude > DEVICE_DEAD_ZONE) {
		const float filtered_magnitude = Clamp((magnitude - DEVICE_DEAD_ZONE) /
			(1.0f - DEVICE_DEAD_ZONE), 0.0f, 1.0f);
		filtered_x = raw_x * filtered_magnitude / magnitude;
		filtered_y = raw_y * filtered_magnitude / magnitude;
	}
	StickSample sample = {};
	sample.x.raw = x_value;
	sample.x.normalized = filtered_x;
	sample.x.logical = To_DirectInput_Logical(filtered_x);
	sample.y.raw = y_value;
	sample.y.normalized = filtered_y;
	sample.y.logical = To_DirectInput_Logical(filtered_y);
	return sample;
}

inline float Apply_Camera_Response(float normalized)
{
	const float magnitude = powf(fabsf(Clamp(normalized, -1.0f, 1.0f)),
		CAMERA_RESPONSE_EXPONENT);
	return normalized < 0.0f ? -magnitude : magnitude;
}

// The original Input::Update_Sliders divides mouse deltas by the frame time,
// and CCamera then integrates the resulting action amount by the same frame
// time. Supplying a rate multiplied by this bounded elapsed time preserves a
// stable angular response at 30, 60, and variable frame rates.
inline int32_t To_Camera_Mouse_Delta(float normalized, float frame_seconds,
	float axis_scale = 1.0f, bool invert = false)
{
	const float bounded_seconds = Clamp(frame_seconds, 0.0f,
		MAX_INPUT_FRAME_SECONDS);
	float response = Apply_Camera_Response(normalized) *
		Clamp(axis_scale, 0.0f, 2.0f);
	if (invert) response = -response;
	const float delta = response * CAMERA_MOUSE_UNITS_PER_SECOND * bounded_seconds;
	return static_cast<int32_t>(delta + (delta >= 0.0f ? 0.5f : -0.5f));
}

} // namespace RenegadeVitaInput
