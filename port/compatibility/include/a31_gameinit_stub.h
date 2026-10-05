#pragma once

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO

// Full frontend builds link the original lifecycle owner.  Network failure,
// death and reload paths must therefore set its real deferred-exit state.
#include "gameinitmgr.h"

#else

// cGod's dead-player menu transition is retained as state logic while the
// desktop game-init/menu owner is deferred.
class GameInitMgrClass {
public:
	static void End_Game(void) {}
	static void Set_Needs_Game_Exit(bool) {}
	static void Set_Needs_Game_Exit_All(bool) {}
};

#endif
