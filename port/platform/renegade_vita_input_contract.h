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

// Handheld Vita crouch: the right thumb cannot hold Circle and aim with the
// right stick at once, and there is no L3. Circle keeps the original
// hold-to-crouch key; a short solo tap additionally latches that key until
// the next Circle press, an Action press (vehicle entry, ladder, poke), a
// release condition from original player state (CrouchContextGate below), or
// loss of ordinary gameplay input. The original Input/Soldier code still owns
// what crouch does; this only decides whether the logical key is held.
class CrouchLatch
{
public:
	enum { TAP_MICROSECONDS = 250000U };
	CrouchLatch() : latched(false), pressed(false), consumed(false),
		was_latched(false), armed(false), press_us(0U) {}
	void Reset()
	{
		latched = pressed = consumed = was_latched = armed = false;
		press_us = 0U;
	}
	bool Latched() const { return latched; }
	// circle: Circle drives crouch this poll (chords already excluded).
	// other: another face/system button is down (e.g. Cross for a momentary
	// crouch-jump), so the press is not a solo tap. Triggers, D-pad and
	// sticks do not count: crouching while firing or moving still latches.
	// cancel: original Action key hit this poll.
	// enabled: ordinary gameplay input is active.
	// release: original player state says the crouch key must not stay
	// latched (vehicle, script control, cinematic, death, beacon fire...).
	// It clears any latch and keeps this press (and a tap) from latching, but
	// a Circle that is physically held still reports the momentary hold key.
	bool Sample(bool circle, bool other, bool cancel, bool enabled,
		uint32_t frame_us, bool release = false)
	{
		if (!enabled) { Reset(); return false; }
		if (cancel || release) latched = false;
		if (circle) {
			if (!pressed) {
				pressed = true;
				// A press that was already down when gameplay input returned
				// (closing the EVA/dialog with Circle) is a hold, never a tap.
				consumed = !armed;
				was_latched = latched;
				press_us = 0U;
			} else if (press_us < TAP_MICROSECONDS) {
				press_us += frame_us;
			}
			if (other || cancel || release) consumed = true;
			return true;
		}
		armed = true;
		if (pressed) {
			pressed = false;
			latched = !release && !was_latched && !consumed &&
				press_us < TAP_MICROSECONDS;
		}
		return latched;
	}
private:
	bool latched;
	bool pressed;
	bool consumed;
	bool was_latched;
	bool armed;
	uint32_t press_us;
};

// Snapshot of the original star (player) state that decides whether a latched
// crouch is still meaningful. A31_Interactive_Sample_Crouch_Player_Context()
// fills it below Combat; every flag is read-only original state, nothing here
// drives movement. A zero-initialized value (no star) always releases.
struct CrouchPlayerContext
{
	bool star_present;        // CombatManager::Get_The_Star() != NULL
	bool in_vehicle;          // Get_Vehicle() or HumanState IN_VEHICLE (any seat)
	bool control_disabled;    // script Control_Enable(star, false)
	bool cinematic;           // camera hosted on a cinematic model
	bool dead;                // HumanState DEATH or DESTROY
	bool scripted_animation;  // HumanState locked: beacon arming, C4 placement,
	                          // transitions, script animations
	bool beacon_weapon;       // current weapon hold style is Beacon
	uint32_t object_id;       // star game-object ID
	uintptr_t object_address; // star object identity (new object = new player)
};

// Why a latched crouch is released. Bits are stable: they are logged by name.
enum CrouchReleaseReason : uint32_t {
	CROUCH_RELEASE_NO_PLAYER = 1U << 0,
	CROUCH_RELEASE_NEW_PLAYER = 1U << 1,  // respawn, restart or load made a new star
	CROUCH_RELEASE_VEHICLE = 1U << 2,
	CROUCH_RELEASE_CONTROL_DISABLED = 1U << 3,
	CROUCH_RELEASE_CINEMATIC = 1U << 4,
	CROUCH_RELEASE_DEAD = 1U << 5,
	CROUCH_RELEASE_SCRIPTED_ANIMATION = 1U << 6,
	CROUCH_RELEASE_BEACON_FIRE = 1U << 7
};

// Turns CrouchPlayerContext into CrouchLatch's release input. Beacon fire is
// the R trigger (original FireWeaponPrimary) while a Beacon weapon is held.
// Original WeaponClass only requires HumanState UPRIGHT (the crouch flag is
// not tested), so this is a conservative guarantee that the M13 ion beacon is
// never deployed from a latched crouch, not a reproduction of a game rule.
// C4 placement and beacon arming both lock the human state with a scripted
// animation, which CROUCH_RELEASE_SCRIPTED_ANIMATION covers.
class CrouchContextGate
{
public:
	CrouchContextGate() : seen(false), object_id(0U), object_address(0U) {}
	void Reset() { seen = false; object_id = 0U; object_address = 0U; }
	// Returns a CrouchReleaseReason mask; non-zero means release this poll.
	uint32_t Evaluate(const CrouchPlayerContext &context, bool fire_primary)
	{
		if (!context.star_present) {
			Reset();
			return CROUCH_RELEASE_NO_PLAYER;
		}
		uint32_t reasons = 0U;
		// First sight of a star is not a change: the latch is reset whenever
		// this gate is (Flush, dialog, loss of gameplay input).
		if (seen && (context.object_id != object_id ||
				context.object_address != object_address)) {
			reasons |= CROUCH_RELEASE_NEW_PLAYER;
		}
		seen = true;
		object_id = context.object_id;
		object_address = context.object_address;
		if (context.in_vehicle) reasons |= CROUCH_RELEASE_VEHICLE;
		if (context.control_disabled) reasons |= CROUCH_RELEASE_CONTROL_DISABLED;
		if (context.cinematic) reasons |= CROUCH_RELEASE_CINEMATIC;
		if (context.dead) reasons |= CROUCH_RELEASE_DEAD;
		if (context.scripted_animation) reasons |= CROUCH_RELEASE_SCRIPTED_ANIMATION;
		if (context.beacon_weapon && fire_primary) reasons |= CROUCH_RELEASE_BEACON_FIRE;
		return reasons;
	}
private:
	bool seen;
	uint32_t object_id;
	uintptr_t object_address;
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

// Integer mouse deltas truncate small per-frame camera motion: at 60 Hz a
// light right-stick tilt yields <0.5 units and rounds to zero every frame,
// while the same tilt at 30 Hz produces motion. Carry the sub-unit remainder
// across frames so slow aiming is continuous and frame-rate independent.
inline int32_t To_Camera_Mouse_Delta(float normalized, float frame_seconds,
	float axis_scale, bool invert, float &residual)
{
	const float bounded_seconds = Clamp(frame_seconds, 0.0f,
		MAX_INPUT_FRAME_SECONDS);
	float response = Apply_Camera_Response(normalized) *
		Clamp(axis_scale, 0.0f, 2.0f);
	if (invert) response = -response;
	if (response == 0.0f) { residual = 0.0f; return 0; }
	const float delta = residual +
		response * CAMERA_MOUSE_UNITS_PER_SECOND * bounded_seconds;
	const int32_t whole = static_cast<int32_t>(delta);
	residual = Clamp(delta - static_cast<float>(whole), -1.0f, 1.0f);
	return whole;
}

} // namespace RenegadeVitaInput

// Implemented by the Combat-aware A3.1 boundary (a31_gameplay_boundary.cpp),
// which is linked wherever renegade_directinput.cpp is. Reads original star
// state only; returns false (context zeroed, star_present false) without a
// star. renegade_directinput.cpp calls it on device while gameplay input is
// active and never from the host ABI contract tests.
bool A31_Interactive_Sample_Crouch_Player_Context(
	RenegadeVitaInput::CrouchPlayerContext &context);
