#pragma once

// Desktop console-window presentation is not instantiated by the Vita
// campaign runtime. Retain the original owner checks and message call sites
// without constructing a Win32 console.  The replicated cScTextObj itself is
// still original code; this is only its optional local display endpoint.
class WideStringClass;
class Vector3;
class ConsoleModeClass {
public:
	/* A native Vita application has no separate desktop console window.  An
	** exclusive console would make the original GameModeManager intentionally
	** skip its rendering path, including WWUI menus and BINKMovie::Render(). */
	ConsoleModeClass(void) : Exclusive(false) {}
	bool Is_Exclusive(void) const { return Exclusive; }
	void Set_Exclusive(bool set) { Exclusive = set; }
	void Print(char const *, ...) {}
	void Print_Maybe(char const *, ...) {}
	void Add_Message(WideStringClass *, Vector3 *, bool = false) {}
	void Log_To_Disk(const char *) {}
private:
	bool Exclusive;
};

inline ConsoleModeClass ConsoleBox;
