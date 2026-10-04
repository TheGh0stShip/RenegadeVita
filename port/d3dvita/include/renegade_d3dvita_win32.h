// Win32 window, module and message-box calls made by the original WW3D DX8
// sources, for the VitaD3D graphics variant. The Vita has one full-screen
// 960 x 544 display and no windows, so window styles and positions are
// accepted and ignored and the screen metrics report the display. The only
// loadable module is "D3D8.DLL", whose Direct3DCreate8 export is VitaD3D's.
#pragma once

#include "win32_compat.h"

typedef void *HMODULE;
typedef void (*FARPROC)(void);

HMODULE LoadLibrary(const char *name);
FARPROC GetProcAddress(HMODULE module, const char *name);
BOOL FreeLibrary(HMODULE module);

enum {
	GWL_STYLE = -16,
	SM_CXSCREEN = 0,
	SM_CYSCREEN = 1,
	MB_OK = 0x00000000
};
static const LONG WS_POPUP = (LONG)0x80000000UL;
static const LONG WS_CHILD = 0x40000000L;
static const LONG WS_CAPTION = 0x00C00000L;
static const LONG WS_SYSMENU = 0x00080000L;
static const LONG WS_MINIMIZEBOX = 0x00020000L;
static const LONG WS_CLIPCHILDREN = 0x02000000L;
static const UINT SWP_NOCOPYBITS = 0x0100u;
static const UINT SWP_SHOWWINDOW = 0x0040u;
#define HWND_TOPMOST ((HWND)(intptr_t)-1)

LONG GetWindowLong(HWND window, int index);
LONG SetWindowLong(HWND window, int index, LONG value);
BOOL SetWindowPos(HWND window, HWND insert_after, int x, int y, int cx, int cy, UINT flags);
BOOL GetWindowRect(HWND window, RECT *rect);
HWND GetDesktopWindow(void);
int GetSystemMetrics(int index);
BOOL SetDeviceGammaRamp(HDC dc, void *ramp);
int MessageBox(HWND window, const char *text, const char *caption, UINT type);
BOOL SetCurrentDirectory(const char *path);

// Critical sections over the compatibility layer's pthread-backed
// CRITICAL_SECTION, for original WW3D/wwdebug units the default build omits.
static inline void InitializeCriticalSection(CRITICAL_SECTION *section)
{
	pthread_mutexattr_t attributes;
	pthread_mutexattr_init(&attributes);
	pthread_mutexattr_settype(&attributes, PTHREAD_MUTEX_RECURSIVE);
	pthread_mutex_init(&section->mutex, &attributes);
	pthread_mutexattr_destroy(&attributes);
}
static inline void DeleteCriticalSection(CRITICAL_SECTION *section) { pthread_mutex_destroy(&section->mutex); }
static inline void EnterCriticalSection(CRITICAL_SECTION *section) { pthread_mutex_lock(&section->mutex); }
static inline void LeaveCriticalSection(CRITICAL_SECTION *section) { pthread_mutex_unlock(&section->mutex); }
