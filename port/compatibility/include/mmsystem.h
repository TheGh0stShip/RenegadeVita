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
#if defined(__vita__)
	// Win32 timeGetTime is monotonic and TimeManager::Update derives every
	// simulated frame step from it (elevator/door timers, animation targets,
	// conversation timers). VitaSDK gettimeofday and CLOCK_REALTIME read the
	// RTC, which can step backward on a user or network clock change and would
	// make one frame step hugely negative (TimeManager only clamps the upper
	// bound). CLOCK_MONOTONIC is sceKernelGetProcessTimeWide in VitaSDK newlib.
	struct timespec monotonic_now = {};
	if (clock_gettime(CLOCK_MONOTONIC, &monotonic_now) == 0) {
		const uint64_t monotonic_ms = (uint64_t)monotonic_now.tv_sec * 1000ULL +
			(uint64_t)monotonic_now.tv_nsec / 1000000ULL;
		return (DWORD)(monotonic_ms & UINT64_C(0xffffffff));
	}
#endif
	struct timeval now = {};
	gettimeofday(&now, NULL);
	const uint64_t milliseconds = (uint64_t)now.tv_sec * 1000ULL +
		(uint64_t)now.tv_usec / 1000ULL;
	return (DWORD)(milliseconds & UINT64_C(0xffffffff));
}
