#pragma once

// WOL is retired for the Vita single-player checkpoint. CombatGameMode keeps
// this declaration solely for a dedicated-server timer reset path that cannot
// run in an offline campaign; preserving its ABI here avoids importing the
// Windows/WWOnline provider graph.
class WolGameModeClass {
public:
	void System_Timer_Reset(void) {}
};

class A31WolNatBoundaryClass {
public:
	bool Is_NAT_Thread_Busy(void) const { return false; }
};

inline A31WolNatBoundaryClass WOLNATInterface;
