#pragma once

// Retail CD-key challenge service was a retired public authentication endpoint.
// LAN/direct-IP session and replication teardown remain original; this only
// removes the unavailable remote-account notification during disconnect.
class CCDKeyAuth {
public:
	static void DisconnectUser(int) {}
};
