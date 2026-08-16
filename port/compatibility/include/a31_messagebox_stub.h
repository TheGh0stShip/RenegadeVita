#pragma once

// Desktop message boxes are presentation only.  cScTextObj remains the
// original replicated message owner; this boundary simply makes its optional
// local popup a no-op until the Vita dialog layer supplies it.
class DlgMsgBox {
public:
	enum Type { Okay = 0, YesNo };
	static bool DoDialog(const wchar_t *, const wchar_t *, Type = Okay, void * = 0,
		unsigned long = 0) { return false; }
	static int Get_Current_Count(void) { return 0; }
};
