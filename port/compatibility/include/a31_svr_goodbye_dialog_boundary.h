#pragma once

// The server-goodbye event preserves its original network/exit behavior on
// Vita. The retired connection-refusal presenter remains unavailable; round
// results and the normal message dialog use their original WWUI owners.
#include "win32_compat.h"
#include "a31_win_screen_stub.h"

class DlgMPConnectionRefused {
public:
	static void DoDialog(const WCHAR *, bool) {}
};
