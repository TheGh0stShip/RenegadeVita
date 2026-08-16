#pragma once

// The server-goodbye event preserves its original network/exit behavior on
// Vita.  Only its two retired multiplayer desktop presenters are unavailable;
// the normal in-engine message dialog remains the original DlgMsgBox owner.
#include "win32_compat.h"

class DlgMPConnectionRefused {
public:
	static void DoDialog(const WCHAR *, bool) {}
};

class CNCWinScreenMenuClass {
public:
	static void Close_Dialog(void) {}
};
