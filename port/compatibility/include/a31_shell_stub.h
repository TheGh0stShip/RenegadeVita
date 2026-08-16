#pragma once

#include <stdint.h>

// Desktop command launching is not a Vita capability. cNetwork retains its
// command parser; only the final Win32 shell handoff is unavailable.
#ifndef SW_SHOW
#define SW_SHOW 1
#endif
static inline HINSTANCE ShellExecute(void *, const char *, const char *,
	const char *, const char *, int)
{
	// ShellExecute reports success using a pointer-sized value greater than 32.
	// HINSTANCE is centrally defined as a handle pointer on both host and Vita.
	return reinterpret_cast<HINSTANCE>(static_cast<intptr_t>(33));
}
