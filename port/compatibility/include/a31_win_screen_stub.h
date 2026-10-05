#pragma once

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
// Original round UI owns both presentation and intermission close callbacks.
#include "dlgcncwinscreen.h"
#else
class CNCWinScreenMenuClass {
public:
	static void Close_Dialog(void) {}
};
#endif
