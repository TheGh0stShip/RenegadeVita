#pragma once

#include "win32_compat.h"

#include <sys/time.h>

// POSIX/Vita replacement for the one WinMM service used by Westwood's
// SysTimeClass. The 32-bit millisecond wrap behavior matches timeGetTime.
static inline DWORD timeGetTime(void)
{
	struct timeval now = {};
	gettimeofday(&now, NULL);
	const uint64_t milliseconds = (uint64_t)now.tv_sec * 1000ULL +
		(uint64_t)now.tv_usec / 1000ULL;
	return (DWORD)(milliseconds & UINT64_C(0xffffffff));
}
