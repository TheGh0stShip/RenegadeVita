#pragma once

// The Windows dedicated-server configuration carries WOL server-list state.
// A Vita LAN/direct-IP host has no master-bandwidth override.
class ServerSettingsClass {
public:
	static unsigned long Get_Master_Bandwidth(void) { return 0; }
};
