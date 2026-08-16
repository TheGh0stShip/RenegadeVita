#pragma once

// DialogParserClass only needs the progress-control class spelling while it
// translates the original serialized dialog records into WWUI controls.
#include "windows.h"

#ifndef PROGRESS_CLASSW
#define PROGRESS_CLASSW L"msctls_progress32"
#endif

// The original ListCtrl uses this list-view style only to suppress header
// rendering. Keep the Win32 value so serialized dialog style bits retain
// their original meaning.
#ifndef LVS_NOCOLUMNHEADER
#define LVS_NOCOLUMNHEADER 0x4000U
#endif
