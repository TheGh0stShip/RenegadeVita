#pragma once

// GameInitMgr keeps the original call ordering for campaign launch and exit.
// These three services solely publish/control PC multiplayer sessions, so the
// Vita single-player build makes each endpoint inert without changing its
// original Combat, audio, or GameMode ownership.
class A4AutoRestartBoundaryClass {
public:
	void Set_Restart_Flag(bool) {}
};

class A4GameSpyQnRBoundaryClass {
public:
	void Init(void) {}
	bool IsEnabled(void) const { return false; }
	void Shutdown(void) {}
};

class GameSideServerControlClass {
public:
	static void Init(void) {}
	static void Shutdown(void) {}
};

inline A4AutoRestartBoundaryClass AutoRestart;
inline A4GameSpyQnRBoundaryClass GameSpyQnR;
