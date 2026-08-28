// Central controller boundary beneath the original DirectInputClass API.
// Combat/Input continues to own action bindings, acceleration, and update
// ordering; this file only converts host/Vita device state to DirectInput's
// established logical button and axis tables.

#include "directinput.h"
#include "dinput.h"
#include "renegade_vita_button_state_contract.h"
#include "renegade_vita_input_contract.h"
#include "renegade_vita_input_route.h"
#include "renegade_vita_input_telemetry.h"
#include "timemgr.h"

#if !defined(RENEGADE_HOST_ABI_TEST)
#include <psp2/ctrl.h>
#include <psp2/io/fcntl.h>
#include <psp2/io/stat.h>
#include "vita_runtime_log.h"
#endif

#include <new>
#include <string.h>

char DirectInput::DIKeyboardButtons[NUM_KEYBOARD_BUTTONS] = {};
char DirectInput::DIMouseButtons[NUM_MOUSE_BUTTONS] = {};
long DirectInput::DIMouseAxis[NUM_MOUSE_AXIS] = {};
char DirectInput::DIJoystickButtons[NUM_MOUSE_BUTTONS] = {};
float DirectInput::ButtonLastHitTime[NUM_KEYBOARD_BUTTONS] = {};
Vector3 DirectInput::CursorPos(0, 0, 0);
bool DirectInput::EatMouseHeld = false;
void *DirectInput::DirectInputLibrary = NULL;
int DirectInput::LastKeyPressed = 0;
bool DirectInput::Captured = false;

namespace {

RenegadeVitaInputTelemetry g_vita_input_telemetry = {};
long g_vita_joystick_axis[2] = {};

#if !defined(RENEGADE_HOST_ABI_TEST)
using RenegadeVitaInputRoute::Header;
using RenegadeVitaInputRoute::Sample;
using RenegadeVitaInputRoute::TimedSample;

const char *const kRecordMarker =
	"ux0:data/renegade/user/config/input-record-once.flag";
const char *const kReplayMarker =
	"ux0:data/renegade/user/config/input-replay-once.flag";
const char *const kRoutePath =
	"ux0:data/renegade/user/config/input-route-v1.bin";
const char *const kRouteTemporaryPath =
	"ux0:data/renegade/user/config/input-route-v1.tmp";

TimedSample *g_route_samples = NULL;
uint32_t g_route_sample_count = 0U;
uint32_t g_route_sample_index = 0U;
uint32_t g_route_mode = RenegadeVitaInputRoute::MODE_PASSTHROUGH;
uint32_t g_route_format_version = 0U;
bool g_route_truncated = false;
bool g_route_gameplay_active = false;
bool g_route_replay_exit_requested = false;
float g_route_replay_elapsed_seconds = 0.0f;
uint64_t g_route_replay_elapsed_us = 0U;
uint64_t g_route_current_sample_elapsed_us = 0U;
const float kLegacyRouteV1SampleRate = 60.0f;
const float kLegacyRouteV1FrameSeconds = 1.0f / kLegacyRouteV1SampleRate;
const float kLegacyRouteV1MaximumFrameStep = 0.25f;
const uint32_t kDefaultTimedRouteDeltaUs = 16667U;
const uint32_t kMaximumRecordedRouteDeltaUs = 1000000U;

bool Is_Regular_File(const char *path)
{
	SceIoStat status = {};
	return sceIoGetstat(path, &status) >= 0 && SCE_S_ISREG(status.st_mode);
}

bool Read_Exact(SceUID file, void *output, size_t byte_count)
{
	uint8_t *bytes = static_cast<uint8_t *>(output);
	size_t offset = 0U;
	while (offset < byte_count) {
		const int read_count = sceIoRead(file, bytes + offset, byte_count - offset);
		if (read_count <= 0) return false;
		offset += static_cast<size_t>(read_count);
	}
	return true;
}

bool Write_Exact(SceUID file, const void *input, size_t byte_count)
{
	const uint8_t *bytes = static_cast<const uint8_t *>(input);
	size_t offset = 0U;
	while (offset < byte_count) {
		const int write_count = sceIoWrite(file, bytes + offset, byte_count - offset);
		if (write_count <= 0) return false;
		offset += static_cast<size_t>(write_count);
	}
	return true;
}

void Reset_Route_State()
{
	delete[] g_route_samples;
	g_route_samples = NULL;
	g_route_sample_count = 0U;
	g_route_sample_index = 0U;
	g_route_mode = RenegadeVitaInputRoute::MODE_PASSTHROUGH;
	g_route_format_version = 0U;
	g_route_truncated = false;
	g_route_gameplay_active = false;
	g_route_replay_exit_requested = false;
	g_route_replay_elapsed_seconds = 0.0f;
	g_route_replay_elapsed_us = 0U;
	g_route_current_sample_elapsed_us = 0U;
}

uint32_t Frame_Delta_Microseconds()
{
	float frame_seconds = TimeManager::Get_Frame_Real_Seconds();
	if (frame_seconds <= 0.0f) frame_seconds = kLegacyRouteV1FrameSeconds;
	if (frame_seconds > static_cast<float>(kMaximumRecordedRouteDeltaUs) / 1000000.0f) {
		frame_seconds = static_cast<float>(kMaximumRecordedRouteDeltaUs) / 1000000.0f;
	}
	const uint32_t delta_us = static_cast<uint32_t>(frame_seconds * 1000000.0f + 0.5f);
	return delta_us != 0U ? delta_us : kDefaultTimedRouteDeltaUs;
}

bool Load_Replay_Route()
{
	SceIoStat status = {};
	if (sceIoGetstat(kRoutePath, &status) < 0 || !SCE_S_ISREG(status.st_mode) ||
		status.st_size < static_cast<SceOff>(sizeof(Header))) return false;
	const SceUID file = sceIoOpen(kRoutePath, SCE_O_RDONLY, 0);
	if (file < 0) return false;
	Header header = {};
	bool valid = Read_Exact(file, &header, sizeof(header)) &&
		RenegadeVitaInputRoute::Validate_Header(header,
			static_cast<size_t>(status.st_size));
	TimedSample *samples = NULL;
	if (valid) {
		samples = new (std::nothrow) TimedSample[header.sample_count];
		valid = samples != NULL;
		if (valid && header.version == RenegadeVitaInputRoute::LEGACY_VERSION) {
			Sample *legacy_samples = new (std::nothrow) Sample[header.sample_count];
			valid = legacy_samples != NULL && Read_Exact(file, legacy_samples,
				static_cast<size_t>(header.sample_count) * sizeof(Sample));
			valid = valid &&
				RenegadeVitaInputRoute::Checksum(legacy_samples, header.sample_count) ==
					header.checksum;
			if (valid) {
				for (uint32_t index = 0U; index < header.sample_count; ++index) {
					samples[index].buttons = legacy_samples[index].buttons;
					samples[index].lx = legacy_samples[index].lx;
					samples[index].ly = legacy_samples[index].ly;
					samples[index].rx = legacy_samples[index].rx;
					samples[index].ry = legacy_samples[index].ry;
					samples[index].delta_us = index == 0U ? 0U : kDefaultTimedRouteDeltaUs;
				}
			}
			delete[] legacy_samples;
		} else if (valid && header.version == RenegadeVitaInputRoute::VERSION) {
			valid = Read_Exact(file, samples,
				static_cast<size_t>(header.sample_count) * sizeof(TimedSample)) &&
				RenegadeVitaInputRoute::Checksum(samples, header.sample_count) ==
					header.checksum;
			if (valid) samples[0].delta_us = 0U;
		} else {
			valid = false;
		}
	}
	const int close_result = sceIoClose(file);
	valid = valid && close_result >= 0;
	if (!valid) {
		delete[] samples;
		return false;
	}
	g_route_samples = samples;
	g_route_sample_count = header.sample_count;
	g_route_sample_index = 0U;
	g_route_format_version = header.version;
	g_route_replay_elapsed_seconds = 0.0f;
	g_route_replay_elapsed_us = 0U;
	g_route_current_sample_elapsed_us = 0U;
	g_route_gameplay_active = false;
	g_route_replay_exit_requested = false;
	g_route_mode = RenegadeVitaInputRoute::MODE_REPLAY;
	g_route_truncated = (header.flags & RenegadeVitaInputRoute::FLAG_TRUNCATED) != 0U;
	sceIoRemove(kReplayMarker);
	return true;
}

void Initialize_Route_Mode()
{
	Reset_Route_State();
	const bool record_requested = Is_Regular_File(kRecordMarker);
	const bool replay_requested = Is_Regular_File(kReplayMarker);
	if (record_requested && replay_requested) {
		g_route_mode = RenegadeVitaInputRoute::MODE_REJECTED;
		Vita_Append_A22_Runtime_Breadcrumb("input-route",
			"record/replay conflict rejected; live input passthrough retained");
		return;
	}
	if (replay_requested) {
		if (Load_Replay_Route()) {
			Vita_Append_A22_Runtime_Breadcrumb("input-route",
				"replay admitted: version=%u samples=%u truncated=%d timebase=%s",
				g_route_format_version, g_route_sample_count,
				g_route_truncated ? 1 : 0,
				g_route_format_version == RenegadeVitaInputRoute::VERSION ?
					"recorded-delta-us" : "legacy60hz");
		} else {
			g_route_mode = RenegadeVitaInputRoute::MODE_REJECTED;
			Vita_Append_A22_Runtime_Breadcrumb("input-route",
				"replay rejected: missing, incomplete, invalid, or checksum mismatch");
		}
		return;
	}
	if (record_requested) {
		g_route_samples = new (std::nothrow)
			TimedSample[RenegadeVitaInputRoute::MAX_SAMPLES];
		if (g_route_samples == NULL) {
			g_route_mode = RenegadeVitaInputRoute::MODE_REJECTED;
			Vita_Append_A22_Runtime_Breadcrumb("input-route",
				"record rejected: bounded sample allocation failed");
			return;
		}
		g_route_mode = RenegadeVitaInputRoute::MODE_RECORD;
		Vita_Append_A22_Runtime_Breadcrumb("input-route",
			"record admitted: version=%u max_samples=%u timebase=recorded-delta-us activation=original-player-control",
			RenegadeVitaInputRoute::VERSION, RenegadeVitaInputRoute::MAX_SAMPLES);
	}
}

bool Commit_Recorded_Route()
{
	if (g_route_mode != RenegadeVitaInputRoute::MODE_RECORD ||
		g_route_sample_count == 0U) return false;
	const Header header = RenegadeVitaInputRoute::Build_Header(g_route_samples,
		g_route_sample_count, g_route_truncated);
	sceIoRemove(kRouteTemporaryPath);
	const SceUID file = sceIoOpen(kRouteTemporaryPath,
		SCE_O_WRONLY | SCE_O_CREAT | SCE_O_TRUNC, 0666);
	if (file < 0) return false;
	bool valid = Write_Exact(file, &header, sizeof(header)) &&
		Write_Exact(file, g_route_samples,
			static_cast<size_t>(g_route_sample_count) * sizeof(TimedSample)) &&
		sceIoSyncByFd(file, 0) >= 0;
	valid = sceIoClose(file) >= 0 && valid;
	if (!valid) {
		sceIoRemove(kRouteTemporaryPath);
		return false;
	}
	sceIoRemove(kRoutePath);
	if (sceIoRename(kRouteTemporaryPath, kRoutePath) < 0) {
		sceIoRemove(kRouteTemporaryPath);
		return false;
	}
	sceIoRemove(kRecordMarker);
	return true;
}

void Record_Sample(const SceCtrlData &controller)
{
	if (g_route_mode != RenegadeVitaInputRoute::MODE_RECORD ||
		!g_route_gameplay_active) return;
	if (g_route_sample_count >= RenegadeVitaInputRoute::MAX_SAMPLES) {
		g_route_truncated = true;
		return;
	}
	TimedSample &sample = g_route_samples[g_route_sample_count];
	sample.buttons = controller.buttons;
	sample.lx = controller.lx;
	sample.ly = controller.ly;
	sample.rx = controller.rx;
	sample.ry = controller.ry;
	sample.delta_us = g_route_sample_count == 0U ? 0U : Frame_Delta_Microseconds();
	++g_route_sample_count;
}

void Apply_Timed_Replay_Sample(SceCtrlData &controller, uint32_t live_abort)
{
	while (g_route_sample_index + 1U < g_route_sample_count) {
		const uint64_t next_elapsed = g_route_current_sample_elapsed_us +
			g_route_samples[g_route_sample_index + 1U].delta_us;
		if (next_elapsed > g_route_replay_elapsed_us) break;
		++g_route_sample_index;
		g_route_current_sample_elapsed_us = next_elapsed;
	}
	const TimedSample &sample = g_route_samples[g_route_sample_index];
	controller.buttons = sample.buttons | live_abort;
	controller.lx = sample.lx;
	controller.ly = sample.ly;
	controller.rx = sample.rx;
	controller.ry = sample.ry;
	if (g_route_sample_index + 1U >= g_route_sample_count &&
		g_route_replay_elapsed_us >= g_route_current_sample_elapsed_us) {
		g_route_sample_index = g_route_sample_count;
	}
	g_route_replay_elapsed_us += Frame_Delta_Microseconds();
}

void Apply_Legacy_Replay_Sample(SceCtrlData &controller, uint32_t live_abort)
{
	uint32_t selected_index = static_cast<uint32_t>(
		g_route_replay_elapsed_seconds * kLegacyRouteV1SampleRate);
	if (selected_index < g_route_sample_index) selected_index = g_route_sample_index;
	if (selected_index >= g_route_sample_count) selected_index = g_route_sample_count - 1U;
	const TimedSample &sample = g_route_samples[selected_index];
	controller.buttons = sample.buttons | live_abort;
	controller.lx = sample.lx;
	controller.ly = sample.ly;
	controller.rx = sample.rx;
	controller.ry = sample.ry;
	g_route_sample_index = selected_index + 1U;
	float frame_seconds = TimeManager::Get_Frame_Real_Seconds();
	if (frame_seconds <= 0.0f) frame_seconds = kLegacyRouteV1FrameSeconds;
	if (frame_seconds > kLegacyRouteV1MaximumFrameStep) {
		frame_seconds = kLegacyRouteV1MaximumFrameStep;
	}
	g_route_replay_elapsed_seconds += frame_seconds;
}

void Apply_Replay_Sample(SceCtrlData &controller)
{
	if (g_route_mode != RenegadeVitaInputRoute::MODE_REPLAY) return;
	const uint32_t live_abort = controller.buttons & SCE_CTRL_START;
	if (!g_route_gameplay_active) {
		controller.buttons = live_abort;
		controller.lx = 128U;
		controller.ly = 128U;
		controller.rx = 128U;
		controller.ry = 128U;
		return;
	}
	if (g_route_sample_count > 0U && g_route_sample_index < g_route_sample_count) {
		if (g_route_format_version == RenegadeVitaInputRoute::VERSION) {
			Apply_Timed_Replay_Sample(controller, live_abort);
		} else {
			Apply_Legacy_Replay_Sample(controller, live_abort);
		}
	} else {
		if (!g_route_replay_exit_requested) {
			Vita_Append_A22_Runtime_Breadcrumb("input-route",
				"replay complete: injecting clean exit sample=%u/%u",
				g_route_sample_index, g_route_sample_count);
			g_route_replay_exit_requested = true;
		}
		controller.buttons = live_abort | SCE_CTRL_START;
		controller.lx = 128U;
		controller.ly = 128U;
		controller.rx = 128U;
		controller.ry = 128U;
	}
}
#endif

void Set_Button(char *buttons, int index, bool pressed)
{
	buttons[index] = static_cast<char>(RenegadeVitaInput::Advance_Button_State(
		static_cast<uint8_t>(buttons[index]), pressed));
}

void Set_Virtual_Key(int key, bool pressed)
{
	if (key >= 0 && key < 256) RenegadeVitaWWUIKeyState[key] = pressed ? 0x80 : 0x00;
}

void Clear_Transitions(char *buttons, int count)
{
	for (int index = 0; index < count; ++index) buttons[index] &= DirectInput::DI_BUTTON_HELD;
}

} // namespace

BYTE RenegadeVitaWWUIKeyState[256] = {};

const RenegadeVitaInputTelemetry &Renegade_Vita_Last_Input_Telemetry()
{
	return g_vita_input_telemetry;
}

bool Renegade_Vita_Input_Route_Replay_Exit_Requested()
{
#if !defined(RENEGADE_HOST_ABI_TEST)
	return g_route_mode == RenegadeVitaInputRoute::MODE_REPLAY &&
		g_route_replay_exit_requested;
#else
	return false;
#endif
}

void Renegade_Vita_Input_Route_Set_Gameplay_Active(bool active, uint32_t frame_index)
{
#if !defined(RENEGADE_HOST_ABI_TEST)
	if (g_route_gameplay_active == active) return;
	g_route_gameplay_active = active;
	if (active) {
		if (g_route_mode == RenegadeVitaInputRoute::MODE_RECORD) {
			g_route_sample_count = 0U;
			g_route_truncated = false;
		}
		if (g_route_mode == RenegadeVitaInputRoute::MODE_REPLAY) {
			g_route_sample_index = 0U;
			g_route_replay_exit_requested = false;
			g_route_replay_elapsed_seconds = 0.0f;
			g_route_replay_elapsed_us = 0U;
			g_route_current_sample_elapsed_us = 0U;
		}
		Vita_Append_A22_Runtime_Breadcrumb("input-route",
			"gameplay activation: active=1 frame=%u mode=%u start_sample=%u/%u",
			frame_index, g_route_mode, g_route_sample_index, g_route_sample_count);
	} else {
		Vita_Append_A22_Runtime_Breadcrumb("input-route",
			"gameplay activation: active=0 frame=%u mode=%u sample=%u/%u",
			frame_index, g_route_mode, g_route_sample_index, g_route_sample_count);
	}
#else
	(void)active;
	(void)frame_index;
#endif
}

void DirectInput::Init(void)
{
	Flush();
	memset(&g_vita_input_telemetry, 0, sizeof(g_vita_input_telemetry));
#if !defined(RENEGADE_HOST_ABI_TEST)
	Initialize_Route_Mode();
#endif
	Captured = true;
}

void DirectInput::Shutdown(void)
{
#if !defined(RENEGADE_HOST_ABI_TEST)
	if (g_route_mode == RenegadeVitaInputRoute::MODE_RECORD) {
		const bool committed = Commit_Recorded_Route();
		Vita_Append_A22_Runtime_Breadcrumb("input-route",
			"record shutdown: committed=%d samples=%u truncated=%d",
			committed ? 1 : 0, g_route_sample_count,
			g_route_truncated ? 1 : 0);
	}
	Reset_Route_State();
#endif
	Flush();
	Captured = false;
}
void DirectInput::Acquire(void) { Captured = true; }
void DirectInput::Unacquire(void) { Captured = false; }

void DirectInput::Flush(void)
{
	memset(DIKeyboardButtons, 0, sizeof(DIKeyboardButtons));
	memset(DIMouseButtons, 0, sizeof(DIMouseButtons));
	memset(DIJoystickButtons, 0, sizeof(DIJoystickButtons));
	memset(DIMouseAxis, 0, sizeof(DIMouseAxis));
	memset(RenegadeVitaWWUIKeyState, 0, sizeof(RenegadeVitaWWUIKeyState));
	memset(g_vita_joystick_axis, 0, sizeof(g_vita_joystick_axis));
	LastKeyPressed = 0;
}

void DirectInput::Read(void)
{
	Clear_Transitions(DIKeyboardButtons, NUM_KEYBOARD_BUTTONS);
	Clear_Transitions(DIMouseButtons, NUM_MOUSE_BUTTONS);
	Clear_Transitions(DIJoystickButtons, NUM_JOYSTICK_BUTTONS);
	memset(DIMouseAxis, 0, sizeof(DIMouseAxis));
#if !defined(RENEGADE_HOST_ABI_TEST)
	SceCtrlData controller = {};
	if (!Captured || sceCtrlPeekBufferPositive(0, &controller, 1) <= 0) {
		// A lost controller/focus must not leave an original action logically
		// held. Flush also clears UI virtual keys and analog deltas.
		Flush();
		return;
	}
	Apply_Replay_Sample(controller);
	Record_Sample(controller);
	const unsigned int buttons = controller.buttons;
	Set_Virtual_Key(VK_UP, (buttons & SCE_CTRL_UP) != 0);
	Set_Virtual_Key(VK_DOWN, (buttons & SCE_CTRL_DOWN) != 0);
	Set_Virtual_Key(VK_LEFT, (buttons & SCE_CTRL_LEFT) != 0);
	Set_Virtual_Key(VK_RIGHT, (buttons & SCE_CTRL_RIGHT) != 0);
	Set_Virtual_Key(VK_RETURN, (buttons & SCE_CTRL_CROSS) != 0);
	Set_Virtual_Key(VK_ESCAPE, (buttons & SCE_CTRL_CIRCLE) != 0);
	Set_Virtual_Key(VK_TAB, (buttons & SCE_CTRL_SQUARE) != 0);
	Set_Button(DIKeyboardButtons, DIK_W, (buttons & SCE_CTRL_UP) != 0);
	Set_Button(DIKeyboardButtons, DIK_S, (buttons & SCE_CTRL_DOWN) != 0);
	Set_Button(DIKeyboardButtons, DIK_A, (buttons & SCE_CTRL_LEFT) != 0);
	Set_Button(DIKeyboardButtons, DIK_D, (buttons & SCE_CTRL_RIGHT) != 0);
	Set_Button(DIKeyboardButtons, DIK_SPACE, (buttons & SCE_CTRL_CROSS) != 0);
	Set_Button(DIKeyboardButtons, DIK_LCONTROL, (buttons & SCE_CTRL_CIRCLE) != 0);
	Set_Button(DIKeyboardButtons, DIK_R, (buttons & SCE_CTRL_SQUARE) != 0);
	/* START remains the native direct-route clean-exit control and is sampled
	** before Input::Update. Triangle supplies the original menu-toggle key so
	** Combat's existing suspend/resume state machine remains the pause owner. */
	Set_Button(DIKeyboardButtons, DIK_ESCAPE,
		(buttons & (SCE_CTRL_START | SCE_CTRL_TRIANGLE)) != 0);
	Set_Button(DIKeyboardButtons, DIK_TAB, (buttons & SCE_CTRL_SELECT) != 0);
	Set_Button(DIJoystickButtons, 0, (buttons & SCE_CTRL_LTRIGGER) != 0);
	Set_Button(DIJoystickButtons, 1, (buttons & SCE_CTRL_RTRIGGER) != 0);
	// Keep the two physical sticks independent.  The old boundary reused the
	// mouse array for joystick storage, so mapping the camera overwrote movement
	// input.  Left stick is an original joystick slider; right stick becomes an
	// original mouse delta, which is the route CCamera actually consumes.
	const RenegadeVitaInput::StickSample left =
		RenegadeVitaInput::Sample_Device_Stick(controller.lx, controller.ly);
	const RenegadeVitaInput::StickSample right =
		RenegadeVitaInput::Sample_Device_Stick(controller.rx, controller.ry);
	g_vita_joystick_axis[JOYSTICK_X_AXIS] = left.x.logical;
	// Preserve the raw DirectInput slider orientation.  Input's original
	// SLIDER_JOYSTICK_UP/DOWN bindings interpret a negative Y axis as up; an
	// extra negation here reverses physical forward/backward movement.
	g_vita_joystick_axis[JOYSTICK_Y_AXIS] = left.y.logical;
	const float frame_seconds = TimeManager::Get_Frame_Real_Seconds();
	DIMouseAxis[MOUSE_X_AXIS] = RenegadeVitaInput::To_Camera_Mouse_Delta(
		right.x.normalized, frame_seconds,
		RenegadeVitaInput::DEFAULT_CAMERA_RESPONSE.horizontal_scale);
	DIMouseAxis[MOUSE_Y_AXIS] = RenegadeVitaInput::To_Camera_Mouse_Delta(
		right.y.normalized, frame_seconds,
		RenegadeVitaInput::DEFAULT_CAMERA_RESPONSE.vertical_scale,
		RenegadeVitaInput::DEFAULT_CAMERA_RESPONSE.invert_y);
	g_vita_input_telemetry.lx = left.x.raw;
	g_vita_input_telemetry.ly = left.y.raw;
	g_vita_input_telemetry.rx = right.x.raw;
	g_vita_input_telemetry.ry = right.y.raw;
	g_vita_input_telemetry.normalized_lx = left.x.normalized;
	g_vita_input_telemetry.normalized_ly = left.y.normalized;
	g_vita_input_telemetry.normalized_rx = right.x.normalized;
	g_vita_input_telemetry.normalized_ry = right.y.normalized;
	g_vita_input_telemetry.logical_lx = left.x.logical;
	g_vita_input_telemetry.logical_ly = left.y.logical;
	g_vita_input_telemetry.logical_rx = right.x.logical;
	g_vita_input_telemetry.logical_ry = right.y.logical;
	g_vita_input_telemetry.mouse_dx = static_cast<int32_t>(DIMouseAxis[MOUSE_X_AXIS]);
	g_vita_input_telemetry.mouse_dy = static_cast<int32_t>(DIMouseAxis[MOUSE_Y_AXIS]);
	g_vita_input_telemetry.frame_seconds = frame_seconds;
	g_vita_input_telemetry.buttons = buttons;
	++g_vita_input_telemetry.sample_count;
	g_vita_input_telemetry.route_mode = g_route_mode;
	g_vita_input_telemetry.route_gameplay_active = g_route_gameplay_active ? 1U : 0U;
	g_vita_input_telemetry.route_sample_index = g_route_sample_index;
	g_vita_input_telemetry.route_sample_count = g_route_sample_count;
	g_vita_input_telemetry.route_truncated = g_route_truncated ? 1U : 0U;
#endif
}

void DirectInput::Eat_Mouse_Held_States(void) { EatMouseHeld = true; }
long DirectInput::Get_Joystick_Axis_State(JoystickAxis axis) { return g_vita_joystick_axis[(int)axis]; }
void DirectInput::ReadKeyboard(void) {}
void DirectInput::ReadMouse(void) {}
void DirectInput::ReadJoystick(void) {}
void DirectInput::Update_Double_Clicks(void) {}
