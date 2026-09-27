#pragma once

#include "win32_compat.h"

#include <sys/time.h>

#if defined(RENEGADE_HOST_ABI_TEST) && defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
#ifdef __cplusplus
extern "C" int Renegade_Host_Audio_Clock(DWORD *milliseconds);
#else
int Renegade_Host_Audio_Clock(DWORD *milliseconds);
#endif
#endif

// POSIX/Vita replacement for the one WinMM service used by Westwood's
// SysTimeClass. The 32-bit millisecond wrap behavior matches timeGetTime.
static inline DWORD timeGetTime(void)
{
#if defined(RENEGADE_HOST_ABI_TEST) && defined(RENEGADE_A35_ORIGINAL_WWAUDIO)
	DWORD replay_time;
	if (Renegade_Host_Audio_Clock(&replay_time)) return replay_time;
#endif
	struct timeval now = {};
	gettimeofday(&now, NULL);
	const uint64_t milliseconds = (uint64_t)now.tv_sec * 1000ULL +
		(uint64_t)now.tv_usec / 1000ULL;
	return (DWORD)(milliseconds & UINT64_C(0xffffffff));
}
