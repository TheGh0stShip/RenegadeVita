#pragma once

#include <stdint.h>
#include <stdio.h>
#include <strings.h>
#include <unistd.h>
#include <wchar.h>

#ifndef _MAX_FNAME
#define _MAX_FNAME 256
#endif
#ifndef _MAX_EXT
#define _MAX_EXT 256
#endif

#ifndef _stricmp
#define _stricmp strcasecmp
#endif
#ifndef _strnicmp
#define _strnicmp strncasecmp
#endif
#ifndef _vsnprintf
#define _vsnprintf vsnprintf
#endif
#ifndef _vsnwprintf
#define _vsnwprintf vswprintf
#endif

static inline uint32_t _lrotl(uint32_t value, int shift)
{
	const unsigned amount = ((unsigned)shift) & 31U;
	return amount == 0 ? value : (value << amount) | (value >> (32U - amount));
}
