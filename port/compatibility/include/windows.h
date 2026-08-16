#pragma once

// Narrow Win32 source-compatibility surface for original engine code. Runtime
// OS behavior belongs in the Vita platform layer; these helpers only preserve
// the documented string semantics used at this boundary.

#include "win32_compat.h"

#include <stdlib.h>
#include <string.h>

#ifndef _strdup
#define _strdup strdup
#endif
