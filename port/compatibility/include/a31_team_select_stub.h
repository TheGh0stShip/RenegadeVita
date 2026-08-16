#pragma once

// The desktop team-selection dialog is presentation only. Original
// cChangeTeamEvent remains the authority for team changes and replication.
class DlgMPTeamSelect {
public:
	template <typename T> static void DoDialog(T &) {}
};
