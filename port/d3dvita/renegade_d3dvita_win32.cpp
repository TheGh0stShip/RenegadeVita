// Win32 window, module and message-box boundary for the VitaD3D graphics
// variant. See renegade_d3dvita_win32.h.

#include "renegade_d3dvita_win32.h"

#include <d3d8.h>

#include <string.h>
#include <strings.h>

#include "a30_vita_runtime.h"

namespace {

const int kDisplayWidth = 960;
const int kDisplayHeight = 544;
// Any non-null token identifies the one module.
char g_d3d8_module;

} // namespace

HMODULE LoadLibrary(const char *name)
{
	if (name != NULL && strcasecmp(name, "D3D8.DLL") == 0) {
		return &g_d3d8_module;
	}
	A30_Vita_Log("[d3dvita] LoadLibrary unavailable: %s\n", name ? name : "(null)");
	return NULL;
}

FARPROC GetProcAddress(HMODULE module, const char *name)
{
	if (module == &g_d3d8_module && name != NULL && strcmp(name, "Direct3DCreate8") == 0) {
		return reinterpret_cast<FARPROC>(&Direct3DCreate8);
	}
	return NULL;
}

BOOL FreeLibrary(HMODULE module)
{
	return module == &g_d3d8_module ? TRUE : FALSE;
}

LONG GetWindowLong(HWND, int)
{
	return WS_POPUP;
}

LONG SetWindowLong(HWND, int, LONG)
{
	return WS_POPUP;
}

BOOL SetWindowPos(HWND, HWND, int, int, int, int, UINT)
{
	return TRUE;
}

BOOL GetWindowRect(HWND, RECT *rect)
{
	if (rect == NULL) {
		return FALSE;
	}
	rect->left = 0;
	rect->top = 0;
	rect->right = kDisplayWidth;
	rect->bottom = kDisplayHeight;
	return TRUE;
}

HWND GetDesktopWindow(void)
{
	return NULL;
}

int GetSystemMetrics(int index)
{
	switch (index) {
		case SM_CXSCREEN: return kDisplayWidth;
		case SM_CYSCREEN: return kDisplayHeight;
		default: return 0;
	}
}

BOOL SetDeviceGammaRamp(HDC, void *)
{
	// The display has no gamma ramp; DX8Wrapper falls back to its own path.
	return FALSE;
}

int MessageBox(HWND, const char *text, const char *caption, UINT)
{
	A30_Vita_Log("[d3dvita] MessageBox %s: %s\n", caption ? caption : "", text ? text : "");
	return IDOK;
}

BOOL SetCurrentDirectory(const char *)
{
	return FALSE;
}
