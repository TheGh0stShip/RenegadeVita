#pragma once

#include "a31_dialogmgr_stub.h"

class DialogBaseClass {
public:
	void On_Command(int, int, int) {}
};
class cGameData;
class DlgMPConnect : public DialogBaseClass {
public:
	void Connected(cGameData *) {}
	void Failed_To_Connect(void) {}
};
class DlgMPConnectionRefused {
public:
	static void DoDialog(const wchar_t *, bool) {}
};

#ifndef IDD_MULTIPLAY_CONNECTING
#define IDD_MULTIPLAY_CONNECTING 0
#endif
