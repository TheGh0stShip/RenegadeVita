#pragma once

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && defined(RENEGADE_VITA_LAN_FRONTEND) && !RENEGADE_VITA_M00_DEMO

// The full Vita LAN/direct-IP graph links the released team-selection dialog
// with only its retired WWOnline service branch compiled out.
#include "DlgMPTeamSelect.h"

#else

// The desktop team-selection dialog is presentation only. Original
// cChangeTeamEvent remains the authority for team changes and replication.
class DlgMPTeamSelect {
public:
	template <typename T> static void DoDialog(T &) {}
};

#endif
