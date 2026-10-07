// Host-only link stubs for tools/host_rejected_load_discard_test.cpp.
// saveload.cpp force-links the Twiddler definition factory, which pulls in the
// whole definition system; the rejected-load probe never loads definitions.
void _Force_Link_Twiddler(void) {}

// pointerremap.cpp references Add_Ref for ref-counted remaps; the probe issues
// none, and refcount.cpp's debug path needs Win32 DebugBreak.
#include "refcount.h"
#include <cstdlib>
void RefCountClass::Add_Ref(void) { std::abort(); }

// Loading-screen status text (saveloadstatus.cpp needs the full StringClass).
#include "saveloadstatus.h"
void SaveLoadStatus::Inc_Status_Count(void) {}
void SaveLoadStatus::Set_Status_Text(const char *, int) {}
