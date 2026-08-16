// Central controller boundary beneath the original DirectInputClass API.
// Combat/Input continues to own action bindings, acceleration, and update
// ordering; this file only converts host/Vita device state to DirectInput's
// established logical button and axis tables.

#include "directinput.h"
#include "dinput.h"
#include "renegade_vita_button_state_contract.h"
#include "renegade_vita_input_contract.h"
#include "renegade_vita_input_telemetry.h"
#include "timemgr.h"

#if !defined(RENEGADE_HOST_ABI_TEST)
#include <psp2/ctrl.h>
#endif

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

void DirectInput::Init(void) { Flush(); Captured = true; }
void DirectInput::Shutdown(void) { Flush(); Captured = false; }
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
	Set_Button(DIKeyboardButtons, DIK_ESCAPE, (buttons & SCE_CTRL_START) != 0);
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
#endif
}

void DirectInput::Eat_Mouse_Held_States(void) { EatMouseHeld = true; }
long DirectInput::Get_Joystick_Axis_State(JoystickAxis axis) { return g_vita_joystick_axis[(int)axis]; }
void DirectInput::ReadKeyboard(void) {}
void DirectInput::ReadMouse(void) {}
void DirectInput::ReadJoystick(void) {}
void DirectInput::Update_Double_Clicks(void) {}
