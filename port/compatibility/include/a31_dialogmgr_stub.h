#pragma once

// Dialog ownership is a desktop menu boundary. The offline campaign does not
// create these dialogs, but cGameData clears them during session teardown.
class DialogBaseClass;
class DialogMgrClass {
public:
	static DialogBaseClass *Find_Dialog(int) { return 0; }
	static void Flush_Dialogs(void) {}
};
