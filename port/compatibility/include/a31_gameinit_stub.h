#pragma once

// cGod's dead-player menu transition is retained as state logic while the
// desktop game-init/menu owner is deferred.
class GameInitMgrClass {
public:
	static void End_Game(void) {}
	static void Set_Needs_Game_Exit(bool) {}
	static void Set_Needs_Game_Exit_All(bool) {}
};
