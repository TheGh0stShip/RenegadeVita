#pragma once

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
#include "dialogtests.h"
#include "renegadedialogmgr.h"
#else
// The original cGod state machine owns these menu transitions. Keep gameplay
// state ownership in cGod while deferring desktop dialog presentation.
class DeathOptionsPopupClass {
public:
	void Start_Dialog(void) {}
	void Release_Ref(void) { delete this; }
};
class FailedOptionsPopupClass {
public:
	void Start_Dialog(void) {}
	void Release_Ref(void) { delete this; }
};
class RenegadeDialogMgrClass {
public:
	enum LOCATION { LOC_LOAD_GAME };
	static void Goto_Location(LOCATION) {}
};
#endif
