#pragma once

#include "input.h"

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
	case INPUT_FUNCTION_NEXT_WEAPON: return L"D-pad right";
	case INPUT_FUNCTION_ACTION: return L"Triangle";
	case INPUT_FUNCTION_SELECT_WEAPON_1:
	case INPUT_FUNCTION_SELECT_WEAPON_2:
	case INPUT_FUNCTION_SELECT_WEAPON_3:
	case INPUT_FUNCTION_SELECT_WEAPON_4:
	case INPUT_FUNCTION_SELECT_WEAPON_5: return L"D-pad L/R";
	default: return L"Unbound";
	}
}
