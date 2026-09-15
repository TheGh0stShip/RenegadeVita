#pragma once

#include "renegade_paths.h"
#include "win32_compat.h"

// Narrow Win32 directory-enumeration replacement used by original menu code.
// Patterns are logical Renegade read paths and are resolved beneath the retail
// root; callers never receive an arbitrary host directory handle.
void Renegade_Set_Find_Roots(const RenegadePathRoots &roots);
HANDLE Renegade_Find_First(const char *logical_pattern, WIN32_FIND_DATA *result);
BOOL Renegade_Find_Next(HANDLE handle, WIN32_FIND_DATA *result);
BOOL Renegade_Find_Close(HANDLE handle);
// Available bytes on the user save volume; failure must not mean enough space.
bool Renegade_Get_User_Free_Space(uint64_t &bytes);
bool Renegade_Delete_User_Save(const char *logical_path);
