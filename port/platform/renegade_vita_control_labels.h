#pragma once

#include "input.h"
#include "directinput.h"

inline const WCHAR *Renegade_Vita_Key_Label(int key)
{
	switch (key) {
	case Input::SLIDER_JOYSTICK_UP: return L"Left stick up";
	case Input::SLIDER_JOYSTICK_DOWN: return L"Left stick down";
	case Input::SLIDER_JOYSTICK_LEFT: return L"Left stick left";
	case Input::SLIDER_JOYSTICK_RIGHT: return L"Left stick right";
	case Input::SLIDER_MOUSE_UP: return L"Right stick up";
	case Input::SLIDER_MOUSE_DOWN: return L"Right stick down";
	case Input::SLIDER_MOUSE_LEFT: return L"Right stick left";
	case Input::SLIDER_MOUSE_RIGHT: return L"Right stick right";
	case DirectInput::BUTTON_JOYSTICK_A: return L"L";
	case DirectInput::BUTTON_JOYSTICK_B: return L"R";
	case DirectInput::BUTTON_MOUSE_LEFT: return L"Front touch";
	case DIK_SPACE: return L"Cross";
	case DIK_LCONTROL: return L"Circle";
	case DIK_E: return L"Triangle";
	case DIK_R: return L"Square";
	case DIK_UP: return L"D-pad up";
	case DIK_DOWN: return L"D-pad down";
	case DIK_LEFT: return L"D-pad left";
	case DIK_RIGHT: return L"D-pad right";
	case DIK_BACK: return L"Select";
	case DIK_ESCAPE: return L"Start";
	case DIK_F: return L"Rear touch / SELECT+Circle";
	case DIK_F5: return L"SELECT+Square";
	case DIK_F7: return L"SELECT+Square (multiplayer)";
	case DIK_F8: return L"SELECT+Cross (multiplayer)";
	case DIK_F9: return L"SELECT+D-pad up (multiplayer)";
	default: return NULL;
	}
}

// Labels for the physical mappings installed by Configure_Vita_Controls.
// The original help dialog continues to own its controls and presentation.
inline const WCHAR *Renegade_Vita_Control_Label(int function)
{
	switch (function) {
	case INPUT_FUNCTION_MOVE_FORWARD: return L"L stick up";
	case INPUT_FUNCTION_MOVE_BACKWARD: return L"L stick down";
	case INPUT_FUNCTION_MOVE_LEFT: return L"L stick left";
	case INPUT_FUNCTION_MOVE_RIGHT: return L"L stick right";
	case INPUT_FUNCTION_MENU_TOGGLE:
	case INPUT_FUNCTION_EVA_MISSION_OBJECTIVES_TOGGLE: return L"START";
	case INPUT_FUNCTION_WALK_MODE: return L"Tilt L stick";
	case INPUT_FUNCTION_CYCLE_POG: return L"SELECT";
	case INPUT_FUNCTION_CROUCH: return L"Circle";
	case INPUT_FUNCTION_JUMP: return L"Cross";
	case INPUT_FUNCTION_FIRE_WEAPON_PRIMARY: return L"R";
	case INPUT_FUNCTION_FIRE_WEAPON_SECONDARY:
	case INPUT_FUNCTION_USE_WEAPON: return L"L";
	case INPUT_FUNCTION_RELOAD_WEAPON: return L"Square";
	case INPUT_FUNCTION_PREV_WEAPON: return L"D-pad left";
	case INPUT_FUNCTION_NEXT_WEAPON: return L"D-pad right";
	case INPUT_FUNCTION_ZOOM_IN: return L"D-pad up";
	case INPUT_FUNCTION_ZOOM_OUT: return L"D-pad down";
	case INPUT_FUNCTION_FIRST_PERSON_TOGGLE: return L"Rear touch / SELECT+Circle";
	case INPUT_FUNCTION_ACTION: return L"Triangle";
	case INPUT_FUNCTION_TEAM_INFO_TOGGLE: return L"SELECT+Square";
	case INPUT_FUNCTION_BATTLE_INFO_TOGGLE: return L"SELECT+Cross";
	case INPUT_FUNCTION_SERVER_INFO_TOGGLE: return L"SELECT+D-pad up";
	case INPUT_FUNCTION_SELECT_WEAPON_1:
	case INPUT_FUNCTION_SELECT_WEAPON_2:
	case INPUT_FUNCTION_SELECT_WEAPON_3:
	case INPUT_FUNCTION_SELECT_WEAPON_4:
	case INPUT_FUNCTION_SELECT_WEAPON_5: return L"D-pad L/R";
	default: return L"Unbound";
	}
}
