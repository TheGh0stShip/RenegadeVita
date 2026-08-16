#pragma once

// Declaration-only Input Method Manager ABI surface.  Existing WWUI edit
// headers retain their original ownership and event types; IME implementation
// remains disabled at the Vita input boundary until a real text-composition
// service exists.
#include "windows.h"

typedef void *HIMC;
typedef void *HKL;
typedef struct tagCANDIDATELIST CANDIDATELIST;
typedef struct tagLOGFONT { LONG lfHeight; } LOGFONT, *LPLOGFONT;
