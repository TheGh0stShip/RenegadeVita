#pragma once

#include "gamemode.h"

// WOL/NAT matchmaking is outside the single-player Vita runtime. Keep the
// declaration surface needed while compiling original cGameData intact; every
// value is deliberately offline/disabled.
class cGameData;

class WolGameModeClass : public GameModeClass {
public:
	// GameInitMgr retains these calls in its original mode-dispatch code.  The
	// Vita build never registers a WOL mode, so they are only a type-safe
	// offline boundary if a caller reaches the retired public-service branch.
	void Leave_Game(void) {}
	void Start_Game(cGameData *) {}
	void End_Game(void) {}
	void Init_WOL_Player(void *) {}
	void Accept_Actions(void) {}
	void Refusal_Actions(void) {}
	bool Post_Game_Check(void) { return false; }
	void System_Timer_Reset(void) {}
};

class A31WolNatBoundaryClass {
public:
	int Get_Force_Port(void) const { return 0; }
	int Get_Port_As_Server(void) const { return 0; }
	int Get_Port_As_Server_Client(void) const { return 0; }
	bool Is_NAT_Thread_Busy(void) const { return false; }
};

class A31FirewallBoundaryClass {
public:
	unsigned long Get_Local_Address(void) const { return 0; }
};

inline A31WolNatBoundaryClass WOLNATInterface;
inline A31FirewallBoundaryClass FirewallHelper;

class WOLGameInfo {
public:
	const char *MapName(void) const { return ""; }
	const char *ModName(void) const { return ""; }
	const char *Title(void) const { return ""; }
	int MaxPlayers(void) const { return 1; }
	int NumPlayers(void) const { return 0; }
	bool IsDedicated(void) const { return false; }
	bool IsPassworded(void) const { return false; }
	bool IsLaddered(void) const { return false; }
	bool IsFriendlyFire(void) const { return true; }
	bool IsFreeWeapons(void) const { return false; }
	bool IsTeamRemix(void) const { return false; }
	bool IsTeamChange(void) const { return false; }
	bool IsClanGame(void) const { return false; }
	bool IsQuickmatch(void) const { return false; }
	bool IsRepairBuildings(void) const { return true; }
	bool IsDriverGunner(void) const { return false; }
	bool IsSpawnWeapons(void) const { return true; }
	unsigned long ClanID1(void) const { return 0; }
	unsigned long ClanID2(void) const { return 0; }
};
