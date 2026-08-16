#pragma once

#ifndef RENEGADE_WIN32_COMPAT_H
#define RENEGADE_WIN32_COMPAT_H

#include <stddef.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>

// ABI-facing Win32 scalar types. The native Vita target is ILP32, matching the
// widths assumed by Renegade. Keep UINT and ULONG as distinct C++ types because
// original overload sets contain both.
typedef unsigned char BYTE;
typedef unsigned short WORD;
typedef unsigned short USHORT;
typedef int16_t SHORT;
typedef int32_t LONG;
#if defined(RENEGADE_HOST_ABI_TEST)
// x86-64 Linux has no two distinct 32-bit unsigned fundamental types matching
// Win32's unsigned int/unsigned long overload set. char32_t is a distinct
// 32-bit unsigned integral type and lets the host harness preserve both width
// and overload identity without affecting the Vita production ABI.
typedef char32_t UINT;
typedef unsigned int ULONG;
typedef unsigned int DWORD;
#else
typedef unsigned int UINT;
typedef unsigned long ULONG;
typedef unsigned long DWORD;
#endif
typedef int BOOL;
typedef float FLOAT;
typedef char *LPSTR;
typedef const char *LPCSTR;
typedef const char *LPCTSTR;
#if defined(RENEGADE_SHORT_WCHAR_ABI)
typedef wchar_t WCHAR;
#else
typedef uint16_t WCHAR;
#endif
typedef WCHAR *LPWSTR;
typedef void *HFONT;
typedef void *HBITMAP;
typedef void *HDC;
typedef void *HWND;
typedef void *HANDLE;
typedef void *HKEY;
typedef void *HINSTANCE;
typedef void *HRSRC;
typedef void *HGLOBAL;
typedef void *LPVOID;
typedef void *HACCEL;
typedef uintptr_t WPARAM;
typedef intptr_t LPARAM;
typedef intptr_t LRESULT;
typedef uint32_t MMRESULT;
typedef int64_t LARGE_INTEGER;
typedef struct _MSG MSG;
typedef struct _CRITICAL_SECTION { pthread_mutex_t mutex; } CRITICAL_SECTION;
typedef struct _FILETIME { DWORD dwLowDateTime; DWORD dwHighDateTime; } FILETIME, *LPFILETIME;
typedef struct _WIN32_FIND_DATA {
	DWORD dwFileAttributes;
	FILETIME ftLastWriteTime;
	char cFileName[260];
} WIN32_FIND_DATA;

#ifndef INVALID_HANDLE_VALUE
#define INVALID_HANDLE_VALUE reinterpret_cast<HANDLE>(static_cast<intptr_t>(-1))
#endif
#ifndef MAKELONG
#define MAKELONG(low, high) \
	(static_cast<DWORD>((static_cast<WORD>(low)) | (static_cast<DWORD>(static_cast<WORD>(high)) << 16U)))
#endif
#ifndef LOWORD
#define LOWORD(value) static_cast<WORD>(static_cast<DWORD>(value) & 0xffffU)
#endif
#ifndef HIWORD
#define HIWORD(value) static_cast<WORD>((static_cast<DWORD>(value) >> 16U) & 0xffffU)
#endif
#ifndef IDOK
#define IDOK 1
#endif
#ifndef IDYES
#define IDYES 6
#endif
#ifndef IDNO
#define IDNO 7
#endif
#ifndef FILE_ATTRIBUTE_DIRECTORY
#define FILE_ATTRIBUTE_DIRECTORY 0x10UL
#endif

// Native dialog templates are a serialized Win32 resource ABI, not host C++
// layout.  The original DialogParserClass reads these exact packed fields.
// Keep the two-byte packing explicit on both LP64 host validation and the
// ILP32 Vita target.
#pragma pack(push, 2)
typedef struct _DLGTEMPLATE {
	DWORD style;
	DWORD dwExtendedStyle;
	WORD cdit;
	int16_t x;
	int16_t y;
	int16_t cx;
	int16_t cy;
} DLGTEMPLATE;
typedef struct _DLGITEMTEMPLATE {
	DWORD style;
	DWORD dwExtendedStyle;
	int16_t x;
	int16_t y;
	int16_t cx;
	int16_t cy;
	WORD id;
} DLGITEMTEMPLATE;
#pragma pack(pop)

#ifndef MAKEINTRESOURCE
#define MAKEINTRESOURCE(identifier) \
	reinterpret_cast<LPCTSTR>(static_cast<uintptr_t>(static_cast<WORD>(identifier)))
#endif
#ifndef RT_DIALOG
#define RT_DIALOG MAKEINTRESOURCE(5)
#endif
#ifndef RT_STRING
#define RT_STRING MAKEINTRESOURCE(6)
#endif
#ifndef LANG_NEUTRAL
#define LANG_NEUTRAL 0x00
#endif
#ifndef SUBLANG_NEUTRAL
#define SUBLANG_NEUTRAL 0x00
#endif
#ifndef MAKELANGID
#define MAKELANGID(primary, sub) \
	static_cast<WORD>((static_cast<WORD>(sub) << 10U) | static_cast<WORD>(primary))
#endif

// Implemented by the narrow PE resource boundary.  It exposes only numeric
// RT_DIALOG records to the original DialogParserClass; no synthetic dialogs
// or general Win32 resource emulation are introduced.
HRSRC FindResource(HINSTANCE instance, LPCTSTR name, LPCTSTR type);
// The initial native frontend supplies canonical dialog records. String-table
// resources remain an explicit next boundary; callers preserve the original
// empty-string fallback when this returns NULL.
HRSRC FindResourceEx(HINSTANCE instance, LPCTSTR type, LPCTSTR name, WORD language);
HGLOBAL LoadResource(HINSTANCE instance, HRSRC resource);
LPVOID LockResource(HGLOBAL resource);
extern HINSTANCE ProgramInstance;

#ifndef DS_SETFONT
#define DS_SETFONT 0x00000040UL
#endif

// Serialized RC dialog styles are consumed directly by original WWUI. Keep
// these canonical Win32 values centralized rather than substituting controls.
#ifndef WS_VISIBLE
#define WS_VISIBLE 0x10000000UL
#define WS_DISABLED 0x08000000UL
#define WS_BORDER 0x00800000UL
#define WS_GROUP 0x00020000UL
#endif
#ifndef BS_CHECKBOX
#define BS_CHECKBOX 0x00000002UL
#define BS_AUTOCHECKBOX 0x00000003UL
#define BS_OWNERDRAW 0x0000000BUL
#define BS_BITMAP 0x00000080UL
#define BS_LEFT 0x00000100UL
#define BS_FLAT 0x00008000UL
#endif
#ifndef BN_CLICKED
#define BN_CLICKED 0U
#endif
#ifndef SS_TYPEMASK
#define SS_TYPEMASK 0x0000001FUL
#define SS_RIGHT 0x00000002UL
#define SS_CENTER 0x00000001UL
#define SS_BLACKFRAME 0x00000007UL
#define SS_LEFTNOWORDWRAP 0x0000000CUL
#define SS_BITMAP 0x0000000EUL
#define SS_ETCHEDHORZ 0x00000010UL
#define SS_CENTERIMAGE 0x00000200UL
#endif
#ifndef ES_MULTILINE
#define ES_CENTER 0x00000001UL
#define ES_MULTILINE 0x00000004UL
#define ES_PASSWORD 0x00000020UL
#define ES_AUTOVSCROLL 0x00000040UL
#define ES_OEMCONVERT 0x00000400UL
#define ES_NUMBER 0x00002000UL
#endif
#ifndef CBS_DROPDOWN
#define CBS_DROPDOWN 0x00000002UL
#define CBS_OEMCONVERT 0x00000080UL
#endif

#ifndef CALLBACK
#define CALLBACK
#endif
#ifndef WM_KEYDOWN
#define WM_KEYDOWN 0x0100U
#define WM_KEYUP 0x0101U
#define WM_CHAR 0x0102U
#endif
#ifndef VK_LBUTTON
#define VK_LBUTTON 0x01
#define VK_MBUTTON 0x04
#define VK_RBUTTON 0x02
#define VK_BACK 0x08
#define VK_TAB 0x09
#define VK_RETURN 0x0D
#define VK_SHIFT 0x10
#define VK_ESCAPE 0x1B
#define VK_SPACE 0x20
#define VK_CONTROL 0x11
#define VK_DELETE 0x2E
#define VK_PRIOR 0x21
#define VK_NEXT 0x22
#define VK_END 0x23
#define VK_HOME 0x24
#define VK_LEFT 0x25
#define VK_UP 0x26
#define VK_RIGHT 0x27
#define VK_DOWN 0x28
#endif

// WWUI owns virtual-key interpretation.  The Vita controller adapter owns
// this snapshot; GetKeyboardState preserves the narrow Win32 query contract
// that DialogMgr expects without inventing a second UI input system.
extern BYTE RenegadeVitaWWUIKeyState[256];
static inline BOOL GetKeyboardState(BYTE *state)
{
	if (state == NULL) return 0;
	memcpy(state, RenegadeVitaWWUIKeyState, 256);
	return 1;
}

// The original map control uses the Win32 high-bit contract only for the
// control modifier. Its Vita authority remains the centralized WWUI key
// snapshot populated by the controller adapter.
static inline SHORT GetAsyncKeyState(int virtual_key)
{
	return virtual_key >= 0 && virtual_key < 256 &&
		(RenegadeVitaWWUIKeyState[virtual_key] & 0x80U) != 0U
		? static_cast<SHORT>(0x8000U) : 0;
}

#ifndef IDCANCEL
#define IDCANCEL 2
#endif

// cNetwork records the executable identity during one-time initialization.
// Its current key uses the build/version string, but preserve the Win32 API
// success contract for diagnostics on POSIX and Vita.
static inline DWORD GetModuleFileName(void *, char *name, DWORD capacity)
{
	if (name == NULL || capacity == 0) return 0;
	const char *fallback = "RenegadeVita";
	const size_t length = strlen(fallback);
	const size_t copied = length < (size_t)(capacity - 1) ? length : (size_t)(capacity - 1);
	memcpy(name, fallback, copied);
	name[copied] = '\0';
	return (DWORD)copied;
}

#if !defined(__vita__)
static inline char *itoa(int value, char *buffer, int radix)
{
	if (buffer == NULL || (radix != 10 && radix != 16)) return buffer;
	if (radix == 10) snprintf(buffer, 34, "%d", value);
	else snprintf(buffer, 34, "%x", (unsigned int)value);
	return buffer;
}
#endif

// cNetInterface uses this only to seed a local nickname.  Preserve that
// intent through POSIX host-name retrieval rather than importing a Win32 API.
#ifndef MAX_COMPUTERNAME_LENGTH
#define MAX_COMPUTERNAME_LENGTH 255
#endif
static inline BOOL GetComputerName(char *name, DWORD *size)
{
	if (name == NULL || size == NULL || *size == 0) return 0;
	const size_t capacity = (size_t)*size;
	if (gethostname(name, capacity) != 0) return 0;
	name[capacity - 1] = '\0';
	*size = (DWORD)strlen(name);
	return 1;
}

// Minimal GDI compatibility surface used only by the legacy runtime font
// rasterizer.  Vita rendering never exposes a Win32 DC; the values preserve
// object lifetime and bitmap-buffer ownership until that glyph path is
// replaced beneath FontCharsClass by the native text backend.
typedef struct _SIZE { LONG cx; LONG cy; } SIZE, *LPSIZE;
typedef struct _RECT { LONG left; LONG top; LONG right; LONG bottom; } RECT, *LPRECT;
typedef struct tagBITMAPINFOHEADER {
	DWORD biSize;
	LONG biWidth;
	LONG biHeight;
	WORD biPlanes;
	WORD biBitCount;
	DWORD biCompression;
	DWORD biSizeImage;
	LONG biXPelsPerMeter;
	LONG biYPelsPerMeter;
	DWORD biClrUsed;
	DWORD biClrImportant;
} BITMAPINFOHEADER;
typedef struct tagBITMAPINFO { BITMAPINFOHEADER bmiHeader; } BITMAPINFO;
typedef struct tagTEXTMETRIC { LONG tmHeight; } TEXTMETRIC;

typedef struct _SYSTEMTIME {
	WORD wYear;
	WORD wMonth;
	WORD wDayOfWeek;
	WORD wDay;
	WORD wHour;
	WORD wMinute;
	WORD wSecond;
	WORD wMilliseconds;
} SYSTEMTIME, *PSYSTEMTIME, *LPSYSTEMTIME;

static inline uint64_t Renegade_FileTime_Value(const FILETIME *file_time)
{
	return file_time == NULL ? 0U :
		(static_cast<uint64_t>(file_time->dwHighDateTime) << 32U) |
		static_cast<uint64_t>(file_time->dwLowDateTime);
}

static inline BOOL FileTimeToLocalFileTime(const FILETIME *source, LPFILETIME destination)
{
	if (source == NULL || destination == NULL) return 0;
	// The Vita runtime presents local calendar fields below; retaining the UTC
	// stamp here keeps ordering stable and avoids inventing a mutable timezone.
	*destination = *source;
	return 1;
}

static inline BOOL FileTimeToSystemTime(const FILETIME *file_time, LPSYSTEMTIME system_time)
{
	if (file_time == NULL || system_time == NULL) return 0;
	const uint64_t stamp = Renegade_FileTime_Value(file_time);
	const uint64_t windows_epoch_ticks = 116444736000000000ULL;
	if (stamp < windows_epoch_ticks) {
		memset(system_time, 0, sizeof(*system_time));
		return 0;
	}
	const time_t seconds = static_cast<time_t>((stamp - windows_epoch_ticks) / 10000000ULL);
	struct tm calendar;
	if (localtime_r(&seconds, &calendar) == NULL) {
		memset(system_time, 0, sizeof(*system_time));
		return 0;
	}
	system_time->wYear = static_cast<WORD>(calendar.tm_year + 1900);
	system_time->wMonth = static_cast<WORD>(calendar.tm_mon + 1);
	system_time->wDayOfWeek = static_cast<WORD>(calendar.tm_wday);
	system_time->wDay = static_cast<WORD>(calendar.tm_mday);
	system_time->wHour = static_cast<WORD>(calendar.tm_hour);
	system_time->wMinute = static_cast<WORD>(calendar.tm_min);
	system_time->wSecond = static_cast<WORD>(calendar.tm_sec);
	system_time->wMilliseconds = static_cast<WORD>((stamp / 10000ULL) % 1000ULL);
	return 1;
}

static inline LONG CompareFileTime(const FILETIME *left, const FILETIME *right)
{
	const uint64_t left_value = Renegade_FileTime_Value(left);
	const uint64_t right_value = Renegade_FileTime_Value(right);
	return left_value < right_value ? -1 : (left_value > right_value ? 1 : 0);
}

// Preserve the Win32 UTC calendar contract at the platform seam.  The game
// uses this for diagnostic and save metadata; simulation timing remains the
// separate monotonic TimeManager path.
static inline void GetSystemTime(LPSYSTEMTIME system_time)
{
	if (system_time == NULL) {
		return;
	}
	struct timespec now;
	if (clock_gettime(CLOCK_REALTIME, &now) != 0) {
		memset(system_time, 0, sizeof(*system_time));
		return;
	}
	struct tm calendar;
	if (gmtime_r(&now.tv_sec, &calendar) == NULL) {
		memset(system_time, 0, sizeof(*system_time));
		return;
	}
	system_time->wYear = (WORD)(calendar.tm_year + 1900);
	system_time->wMonth = (WORD)(calendar.tm_mon + 1);
	system_time->wDayOfWeek = (WORD)calendar.tm_wday;
	system_time->wDay = (WORD)calendar.tm_mday;
	system_time->wHour = (WORD)calendar.tm_hour;
	system_time->wMinute = (WORD)calendar.tm_min;
	system_time->wSecond = (WORD)calendar.tm_sec;
	system_time->wMilliseconds = (WORD)(now.tv_nsec / 1000000L);
}

// Win32 thread IDs are runtime-only opaque 32-bit tokens.  Hash the complete
// POSIX pthread_t object representation so the result is stable for the life
// of a thread without assuming pthread_t is an integer or pointer on either
// the LP64 host harness or the ILP32 Vita target.
static inline DWORD GetCurrentThreadId(void)
{
	const pthread_t native_thread = pthread_self();
	const unsigned char *bytes =
		reinterpret_cast<const unsigned char *>(&native_thread);
	uint32_t token = UINT32_C(2166136261);
	for (size_t index = 0; index < sizeof(native_thread); ++index) {
		token ^= bytes[index];
		token *= UINT32_C(16777619);
	}
	return (DWORD)(token != 0U ? token : 1U);
}

// Preserve Win32 Sleep's millisecond contract at the POSIX platform boundary.
// Retry only when an interrupt shortened the requested interval.
static inline void Sleep(DWORD milliseconds)
{
	struct timespec remaining;
	remaining.tv_sec = (time_t)(milliseconds / 1000U);
	remaining.tv_nsec = (long)(milliseconds % 1000U) * 1000000L;
	while (nanosleep(&remaining, &remaining) != 0 && errno == EINTR) {
	}
}

// RawFileClass exposes its native stream through FileClass's opaque handle.
// On the POSIX/Vita path that handle is a FILE*. Preserve the Win32-style
// ReadFile/WriteFile contract used by legacy WWPhys handle overloads at this
// centralized platform boundary rather than teaching WWPhys about stdio.
#ifndef INVALID_HANDLE_VALUE
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#endif

static inline BOOL ReadFile(HANDLE handle, void *buffer, uint32_t byte_count,
	uint32_t *bytes_read, void *)
{
	if (bytes_read != NULL) {
		*bytes_read = 0;
	}
	if (handle == NULL || handle == INVALID_HANDLE_VALUE || buffer == NULL) {
		return 0;
	}
	FILE *stream = static_cast<FILE *>(handle);
	const size_t count = fread(buffer, 1, (size_t)byte_count, stream);
	if (bytes_read != NULL) {
		*bytes_read = (uint32_t)count;
	}
	return ferror(stream) == 0 ? 1 : 0;
}

static inline BOOL WriteFile(HANDLE handle, const void *buffer, uint32_t byte_count,
	uint32_t *bytes_written, void *)
{
	if (bytes_written != NULL) {
		*bytes_written = 0;
	}
	if (handle == NULL || handle == INVALID_HANDLE_VALUE || buffer == NULL) {
		return 0;
	}
	FILE *stream = static_cast<FILE *>(handle);
	const size_t count = fwrite(buffer, 1, (size_t)byte_count, stream);
	if (bytes_written != NULL) {
		*bytes_written = (uint32_t)count;
	}
	return count == (size_t)byte_count && ferror(stream) == 0 ? 1 : 0;
}

// Win32's high-resolution performance counter is a monotonic tick source.
// Expose the same contract over POSIX nanoseconds; callers divide the reported
// frequency exactly as they did on Windows, so engine timing semantics remain
// unchanged on both the LP64 host harness and ILP32 Vita target.
static inline BOOL QueryPerformanceFrequency(LARGE_INTEGER *frequency)
{
	if (frequency == NULL) {
		return 0;
	}
	*frequency = INT64_C(1000000000);
	return 1;
}

static inline BOOL QueryPerformanceCounter(LARGE_INTEGER *counter)
{
	if (counter == NULL) {
		return 0;
	}
	struct timespec now;
	if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
		*counter = 0;
		return 0;
	}
	*counter = (LARGE_INTEGER)now.tv_sec * INT64_C(1000000000) + now.tv_nsec;
	return 1;
}

#ifndef TIMERR_NOERROR
#define TIMERR_NOERROR ((MMRESULT)0)
#endif

static inline MMRESULT timeBeginPeriod(unsigned int)
{
	return TIMERR_NOERROR;
}

#ifndef MAX_PATH
#define MAX_PATH 260
#endif
#ifndef _MAX_PATH
#define _MAX_PATH MAX_PATH
#endif

#ifndef ETO_OPAQUE
#define ETO_OPAQUE 0x0002U
#define LOGPIXELSY 90
#define FW_NORMAL 400
#define FW_BOLD 700
#define CHINESEBIG5_CHARSET 136
#define SHIFTJIS_CHARSET 128
#define HANGUL_CHARSET 129
#define DEFAULT_CHARSET 1
#define OUT_DEFAULT_PRECIS 0
#define CLIP_DEFAULT_PRECIS 0
#define ANTIALIASED_QUALITY 4
#define VARIABLE_PITCH 2
#define BI_RGB 0
#define DIB_RGB_COLORS 0
#define RGB(red, green, blue) ((DWORD)(((BYTE)(red)) | ((WORD)((BYTE)(green)) << 8)) | (((DWORD)(BYTE)(blue)) << 16))
#endif

static inline int MulDiv(int value, int numerator, int denominator)
{
	return denominator == 0 ? 0 : (int)(((int64_t)value * numerator) / denominator);
}

static inline HDC GetDC(void *) { return (HDC)(intptr_t)1; }
static inline int ReleaseDC(void *, HDC) { return 1; }
static inline int GetDeviceCaps(HDC, int) { return 96; }
static inline unsigned GetACP(void) { return 0; }
static inline HFONT CreateFont(int, int, int, int, int, DWORD, DWORD, DWORD,
	DWORD, DWORD, DWORD, DWORD, DWORD, const char *) { return calloc(1, 1); }
static inline HBITMAP CreateDIBSection(HDC, const BITMAPINFO *info, unsigned,
	void **bits, void *, DWORD)
{
	if (bits != NULL) {
		size_t bytes = info != NULL && info->bmiHeader.biSizeImage != 0
			? (size_t)info->bmiHeader.biSizeImage : 1U;
		*bits = calloc(1, bytes);
		return *bits;
	}
	return NULL;
}
static inline HDC CreateCompatibleDC(HDC) { return calloc(1, 1); }
static inline void *SelectObject(HDC, void *) { return NULL; }
static inline DWORD SetBkColor(HDC, DWORD) { return 0; }
static inline DWORD SetTextColor(HDC, DWORD) { return 0; }
static inline BOOL GetTextMetrics(HDC, TEXTMETRIC *metric)
{
	if (metric != NULL) metric->tmHeight = 1;
	return 1;
}
static inline BOOL GetTextExtentPoint32W(HDC, const WCHAR *, int count, SIZE *size)
{
	if (size != NULL) { size->cx = count > 0 ? count : 1; size->cy = 1; }
	return 1;
}
static inline BOOL ExtTextOutW(HDC, int, int, unsigned, const RECT *, const WCHAR *,
	unsigned, const int *) { return 1; }
static inline BOOL DeleteObject(void *object) { free(object); return 1; }
static inline BOOL DeleteDC(HDC dc) { free(dc); return 1; }

static inline char *lstrcpyn(char *destination, const char *source, int count)
{
	if (count <= 0) {
		return destination;
	}
	strncpy(destination, source, (size_t)count - 1U);
	destination[count - 1] = '\0';
	return destination;
}

static inline char *lstrcpy(char *destination, const char *source)
{
	return strcpy(destination, source);
}

static inline char *lstrcat(char *destination, const char *source)
{
	return strcat(destination, source);
}

static inline int lstrlen(const char *text)
{
	return (int)strlen(text);
}

static inline int lstrcmpi(const char *left, const char *right)
{
	return strcasecmp(left, right);
}

static inline DWORD GetCurrentDirectory(DWORD size, char *buffer)
{
	if (size == 0 || buffer == NULL || getcwd(buffer, (size_t)size) == NULL) {
		return 0;
	}
	return (DWORD)strlen(buffer);
}

#ifndef ZeroMemory
#define ZeroMemory(destination, size) memset((destination), 0, (size))
#endif

static inline size_t rv_utf16_length(const WCHAR *text)
{
	size_t length = 0;
	while (text[length] != 0) {
		++length;
	}
	return length;
}

// Host builds use -fshort-wchar to match the Vita ABI, while glibc's wide
// string functions retain the host's native wchar_t ABI. Keep all original
// WideStringClass storage operations inside this 16-bit-safe boundary.
static inline int rv_utf16_compare(const WCHAR *left, const WCHAR *right)
{
	while (*left != 0 && *left == *right) {
		++left;
		++right;
	}
	return *left < *right ? -1 : (*left > *right ? 1 : 0);
}

static inline WCHAR *rv_utf16_copy(WCHAR *destination, const WCHAR *source)
{
	WCHAR *result = destination;
	do {
		*destination++ = *source;
	} while (*source++ != 0);
	return result;
}

static inline WCHAR *rv_utf16_rchr(WCHAR *text, WCHAR character)
{
	WCHAR *match = NULL;
	for (; *text != 0; ++text) {
		if (*text == character) {
			match = text;
		}
	}
	return character == 0 ? text : match;
}

static inline const WCHAR *rv_utf16_rchr(const WCHAR *text, WCHAR character)
{
	const WCHAR *match = NULL;
	for (; *text != 0; ++text) {
		if (*text == character) {
			match = text;
		}
	}
	return character == 0 ? text : match;
}

/* Host ABI probes retain the host compiler's four-byte wchar_t while the
** source's Windows WCHAR remains uint16.  Supply overloads only in that
** configuration; Vita uses wchar_t itself as the UTF-16 element and links to
** the C-linkage wrappers in a31_miscutil_boundary.cpp. */
#if !defined(RENEGADE_SHORT_WCHAR_ABI)
static inline size_t wcslen(const WCHAR *text)
{
	return rv_utf16_length(text);
}

static inline int wcscmp(const WCHAR *left, const WCHAR *right)
{
	return rv_utf16_compare(left, right);
}

static inline WCHAR *wcsrchr(WCHAR *text, WCHAR character)
{
	return rv_utf16_rchr(text, character);
}

static inline const WCHAR *wcsrchr(const WCHAR *text, WCHAR character)
{
	return rv_utf16_rchr(text, character);
}

static inline WCHAR *wcscpy(WCHAR *destination, const WCHAR *source)
{
	return rv_utf16_copy(destination, source);
}
#endif


static inline int rv_utf16_case_compare(const WCHAR *left, const WCHAR *right)
{
	while (*left != 0 && *right != 0) {
		const uint32_t left_folded = *left >= 'A' && *left <= 'Z' ? *left + 32U : *left;
		const uint32_t right_folded = *right >= 'A' && *right <= 'Z' ? *right + 32U : *right;
		if (left_folded != right_folded) {
			return left_folded < right_folded ? -1 : 1;
		}
		++left;
		++right;
	}
	return *left < *right ? -1 : (*left > *right ? 1 : 0);
}

// The original WWUI tag parser compares a fixed-length ASCII tag embedded in
// UTF-16 storage. Keep that bounded comparison within the same 16-bit string
// boundary as _wcsicmp: libc wide-string functions are not ABI-safe for the
// host's -fshort-wchar validation configuration.
static inline int rv_utf16_case_n_compare(const WCHAR *left, const WCHAR *right,
	size_t count)
{
	for (size_t index = 0; index < count; ++index) {
		uint32_t left_char = left[index];
		uint32_t right_char = right[index];
		if (left_char >= 'A' && left_char <= 'Z') left_char += 'a' - 'A';
		if (right_char >= 'A' && right_char <= 'Z') right_char += 'a' - 'A';
		if (left_char != right_char) return left_char < right_char ? -1 : 1;
		if (left_char == 0) return 0;
	}
	return 0;
}

static inline int rv_utf16_to_int(const WCHAR *text)
{
	if (text == NULL) return 0;
	while (*text == ' ' || *text == '\t') ++text;
	bool negative = false;
	if (*text == '-' || *text == '+') {
		negative = *text == '-';
		++text;
	}
	int64_t value = 0;
	while (*text >= '0' && *text <= '9') {
		value = value * 10 + (*text - '0');
		if ((!negative && value > INT_MAX) ||
			(negative && value >= -(int64_t)INT_MIN)) return negative ? INT_MIN : INT_MAX;
		++text;
	}
	return negative ? -(int)value : (int)value;
}

#ifndef _wtoi
#define _wtoi rv_utf16_to_int
#endif

#ifndef LOCALE_USER_DEFAULT
#define LOCALE_USER_DEFAULT 0x0400U
#endif
#ifndef NORM_IGNORECASE
#define NORM_IGNORECASE 0x00000001U
#endif
#ifndef CSTR_LESS_THAN
#define CSTR_LESS_THAN 1
#define CSTR_EQUAL 2
#define CSTR_GREATER_THAN 3
#endif

// Preserve the three-way Win32 result contract used by ListCtrl sorting.
// This remains inside the existing 16-bit WCHAR boundary rather than routing
// Vita/short-wchar strings through host libc wide-character functions.
static inline int CompareStringW(DWORD, DWORD flags, const WCHAR *left,
	int left_count, const WCHAR *right, int right_count)
{
	if (left == NULL || right == NULL) return 0;
	const size_t left_length = left_count < 0 ? rv_utf16_length(left) : (size_t)left_count;
	const size_t right_length = right_count < 0 ? rv_utf16_length(right) : (size_t)right_count;
	const size_t shared = left_length < right_length ? left_length : right_length;
	for (size_t index = 0; index < shared; ++index) {
		uint32_t left_char = left[index];
		uint32_t right_char = right[index];
		if ((flags & NORM_IGNORECASE) != 0U) {
			if (left_char >= 'A' && left_char <= 'Z') left_char += 'a' - 'A';
			if (right_char >= 'A' && right_char <= 'Z') right_char += 'a' - 'A';
		}
		if (left_char < right_char) return 1;
		if (left_char > right_char) return 3;
	}
	return left_length < right_length ? 1 : (left_length > right_length ? 3 : 2);
}

static inline WCHAR *rv_utf16_upper(WCHAR *text)
{
	if (text == NULL) return NULL;
	for (WCHAR *cursor = text; *cursor != 0; ++cursor) {
		if (*cursor >= 'a' && *cursor <= 'z') {
			*cursor = static_cast<WCHAR>(*cursor - ('a' - 'A'));
		}
	}
	return text;
}

static inline WCHAR *rv_utf16_trim(WCHAR *text)
{
	WCHAR *begin = text;
	while (*begin != 0 && *begin <= 32) {
		++begin;
	}
	WCHAR *end = begin + rv_utf16_length(begin);
	while (end > begin && end[-1] <= 32) {
		--end;
	}
	*end = 0;
	if (begin != text) {
		memmove(text, begin, (rv_utf16_length(begin) + 1U) * sizeof(WCHAR));
	}
	return text;
}

// VC6's wide formatter operated on 16-bit WCHAR. A complete UTF-16 formatter
// is supplied before UI integration; the current asset path only requires the
// original storage/conversion behavior and never calls this function.
static inline int rv_utf16_vsnprintf(WCHAR *destination, size_t count,
	const WCHAR *format, const va_list &)
{
	if (destination == NULL || count == 0 || format == NULL) {
		return -1;
	}
	size_t index = 0;
	while (index + 1U < count && format[index] != 0 && format[index] != '%') {
		destination[index] = format[index];
		++index;
	}
	destination[index] = 0;
	return format[index] == 0 ? (int)index : -1;
}

#ifndef _wcsicmp
#define _wcsicmp rv_utf16_case_compare
#endif
#ifndef _wcsnicmp
#define _wcsnicmp rv_utf16_case_n_compare
#endif
#ifndef wcsicmp
#define wcsicmp rv_utf16_case_compare
#endif
#ifndef _wcsupr
#define _wcsupr rv_utf16_upper
#endif
#if !defined(RENEGADE_SHORT_WCHAR_ABI) && !defined(wcstrim)
#define wcstrim rv_utf16_trim
#endif
#ifndef _vsnwprintf
#define _vsnwprintf rv_utf16_vsnprintf
#endif

#ifndef CP_ACP
#define CP_ACP 0
#endif
static inline int MultiByteToWideChar(unsigned int, DWORD, const char *source,
	int source_count, WCHAR *destination, int destination_count)
{
	if (source == NULL) {
		return 0;
	}
	const int required = source_count < 0 ? (int)strlen(source) + 1 : source_count;
	if (destination == NULL || destination_count == 0) {
		return required;
	}
	if (destination_count < required) {
		return 0;
	}
	for (int index = 0; index < required; ++index) {
		destination[index] = (WCHAR)(unsigned char)source[index];
	}
	return required;
}

#if defined(__vita__) || defined(RENEGADE_HOST_ABI_TEST)
static_assert(sizeof(BYTE) == 1, "Win32 BYTE must be 8-bit");
static_assert(sizeof(WORD) == 2, "Win32 WORD must be 16-bit");
static_assert(sizeof(LONG) == 4, "Win32 LONG must be 32-bit");
static_assert(sizeof(UINT) == 4, "Win32 UINT must be 32-bit");
static_assert(sizeof(ULONG) == 4, "Win32 ULONG must be 32-bit");
static_assert(sizeof(DWORD) == 4, "Win32 DWORD must be 32-bit");
static_assert(sizeof(WCHAR) == 2, "Win32 WCHAR must be UTF-16 code-unit sized");
#endif

#ifndef TRUE
#define TRUE 1
#endif
#ifndef FALSE
#define FALSE 0
#endif

#endif // RENEGADE_WIN32_COMPAT_H
