#pragma once

// WWUI only asks this narrow boundary for the configured mouse-wheel line
// count. Vita has no wheel, so expose the documented Windows default rather
// than making the control depend on a host-only user-settings API.
#include "windows.h"

#ifndef SPI_GETWHEELSCROLLLINES
#define SPI_GETWHEELSCROLLLINES 104U
#endif
#ifndef WHEEL_DELTA
#define WHEEL_DELTA 120
#endif

static inline BOOL SystemParametersInfo(UINT action, UINT, void *value, UINT)
{
	if (action != SPI_GETWHEELSCROLLLINES || value == NULL) return 0;
	*static_cast<UINT *>(value) = 3U;
	return 1;
}
