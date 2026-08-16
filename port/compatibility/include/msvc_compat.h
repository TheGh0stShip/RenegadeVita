#pragma once

// Centralized spellings for Microsoft compiler extensions used by the 2002
// Westwood code. Calling-convention attributes are irrelevant on ARM EABI.
#ifndef _MSC_VER
#ifndef __cdecl
#define __cdecl
#endif
#ifndef _cdecl
#define _cdecl
#endif
#ifndef __stdcall
#define __stdcall
#endif
#ifndef _stdcall
#define _stdcall
#endif
#ifndef __fastcall
#define __fastcall
#endif
#ifndef __forceinline
#define __forceinline inline __attribute__((always_inline))
#endif
#ifndef __declspec
#define __declspec(x) __attribute__((x))
#endif
#ifndef _declspec
#define _declspec(x) __attribute__((x))
#endif
#ifndef __int64
typedef signed long long __int64;
#endif
#endif

#if !defined(_MSC_VER)
#include <strings.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
#include <alloca.h>
#include <stdio.h>
#ifndef stricmp
#define stricmp strcasecmp
#endif
#ifndef _stricmp
#define _stricmp strcasecmp
#endif
#ifndef strcmpi
#define strcmpi strcasecmp
#endif
#ifndef strnicmp
#define strnicmp strncasecmp
#endif
#ifndef _strnicmp
#define _strnicmp strncasecmp
#endif
#ifndef _strdup
#define _strdup strdup
#endif
#ifndef _isnan
#define _isnan isnan
#endif
#ifndef _alloca
#define _alloca alloca
#endif
#ifndef _snprintf
#define _snprintf snprintf
#endif
static inline void OutputDebugString(const char *text)
{
	if (text != NULL) {
		fputs(text, stderr);
	}
}
// Vita newlib exports strlwr(), but the original sources also use the MSVC
// spelling _strlwr().  Keep exactly one implementation per platform: defining
// strlwr locally on Vita collides with the libc declaration in C++.
#if defined(__vita__)
static inline char *_strlwr(char *text)
{
	return strlwr(text);
}
#else
static inline char *_strlwr(char *text)
{
	for (char *cursor = text; *cursor != '\0'; ++cursor) {
		*cursor = (char)tolower((unsigned char)*cursor);
	}
	return text;
}
static inline char *strlwr(char *text)
{
	return _strlwr(text);
}
#endif
// newlib as shipped by VitaSDK already declares strupr().  Keep the
// compatibility implementation for host builds only, otherwise C++ rejects a
// later static declaration of the libc function.
#if !defined(__vita__)
static inline char *strupr(char *text)
{
	for (char *cursor = text; *cursor != '\0'; ++cursor) {
		*cursor = (char)toupper((unsigned char)*cursor);
	}
	return text;
}
#endif
#endif

#include "win32_compat.h"

// Renegade passes the original SEH callback into ThreadClass constructors.
// The POSIX/Vita thread implementation does not execute an SEH wrapper, but
// the callback type must remain available to the original Combat call path.
struct _EXCEPTION_POINTERS;
int Exception_Handler(int exception_code, struct _EXCEPTION_POINTERS *e_info);
