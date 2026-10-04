// Win32 base types shared by Renegade and VitaD3D in the VitaD3D graphics
// variant. VitaD3D is compiled with this header as VITAD3D_WIN32_TYPES_HEADER
// so the library and the original WW3D sources agree on every D3D8 type.
// Renegade's compatibility layer supplies the scalar and handle types; the
// COM names it does not need elsewhere are added here.
#pragma once

#include "win32_compat.h"

#include <stdint.h>

typedef int INT;
typedef int32_t HRESULT;
typedef void *HMONITOR;
typedef const void *LPCVOID;

struct POINT { LONG x, y; };
struct GUID {
	uint32_t Data1;
	uint16_t Data2, Data3;
	uint8_t Data4[8];
};
typedef GUID IID;
typedef const GUID &REFIID;
typedef const GUID &REFGUID;
