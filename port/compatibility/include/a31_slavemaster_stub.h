#pragma once

// The PC dedicated-server supervisor launches and controls child processes.
// Vita hosts a single original cNetwork server instance; packet and replication
// ownership remains in cNetwork/WWNet.
class SlaveMasterClass {
public:
	bool Am_I_Slave(void) const { return false; }
	int Get_Num_Enabled_Slaves(void) const { return 0; }
	void Shutdown_Slaves(void) {}
};

inline SlaveMasterClass SlaveMaster;
