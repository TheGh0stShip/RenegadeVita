#pragma once

#include "win32_compat.h"

#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

// Vita is always foreground while this native application owns LiveArea.
// The platform runtime updates this boundary if an explicit focus transition
// becomes observable, preserving the original Combat input guard.
extern HINSTANCE ProgramInstance;
extern HWND MainWindow;
extern bool GameInFocus;

HANDLE Renegade_Find_First(const char *logical_pattern, WIN32_FIND_DATA *result);
BOOL Renegade_Find_Next(HANDLE handle, WIN32_FIND_DATA *result);
BOOL Renegade_Find_Close(HANDLE handle);

static inline HANDLE FindFirstFile(const char *pattern, WIN32_FIND_DATA *result)
{
	return Renegade_Find_First(pattern, result);
}

static inline BOOL FindNextFile(HANDLE handle, WIN32_FIND_DATA *result)
{
	return Renegade_Find_Next(handle, result);
}

static inline BOOL FindClose(HANDLE handle)
{
	return Renegade_Find_Close(handle);
}

#ifndef CP_ACP
#define CP_ACP 0
#endif
#ifndef _MAX_DRIVE
#define _MAX_DRIVE 8
#endif
#ifndef _MAX_DIR
#define _MAX_DIR 1024
#endif
#ifndef FILE_ATTRIBUTE_DIRECTORY
#define FILE_ATTRIBUTE_DIRECTORY 0x10UL
#endif
#ifndef INVALID_FILE_ATTRIBUTES
#define INVALID_FILE_ATTRIBUTES 0xFFFFFFFFUL
#endif

static inline DWORD GetLastError(void)
{
	return (DWORD)errno;
}

static inline int DeleteFile(const char *path)
{
	return remove(path) == 0;
}

static inline int MoveFile(const char *source, const char *destination)
{
	return rename(source, destination) == 0;
}

static inline DWORD GetFileAttributes(const char *path)
{
	struct stat info;
	if (stat(path, &info) != 0) {
		return INVALID_FILE_ATTRIBUTES;
	}
	return S_ISDIR(info.st_mode) ? FILE_ATTRIBUTE_DIRECTORY : 0;
}

static inline void _splitpath(const char *path, char *drive, char *directory,
	char *filename, char *extension)
{
	if (drive != NULL) {
		drive[0] = 0;
	}
	if (directory != NULL) {
		directory[0] = 0;
	}
	if (filename != NULL) {
		filename[0] = 0;
	}
	if (extension != NULL) {
		extension[0] = 0;
	}
	if (path == NULL) {
		return;
	}

	const char *last_slash = strrchr(path, '/');
	const char *last_backslash = strrchr(path, '\\');
	if (last_backslash != NULL &&
		(last_slash == NULL || last_backslash > last_slash)) {
		last_slash = last_backslash;
	}
	if (directory != NULL && last_slash != NULL) {
		const size_t length = (size_t)(last_slash - path) + 1;
		memcpy(directory, path, length);
		directory[length] = 0;
	}

	const char *base = last_slash == NULL ? path : last_slash + 1;
	const char *dot = strrchr(base, '.');
	if (filename != NULL) {
		const size_t length = dot == NULL ? strlen(base) : (size_t)(dot - base);
		memcpy(filename, base, length);
		filename[length] = 0;
	}
	if (extension != NULL && dot != NULL) {
		strcpy(extension, dot);
	}
}

static inline int WideCharToMultiByte(unsigned, DWORD, const WCHAR *source,
	int source_length, char *destination, int destination_length,
	const char *default_character, BOOL *used_default_character)
{
	if (source == NULL) {
		return 0;
	}
	const char replacement =
		default_character != NULL ? *default_character : '?';
	int required = 0;
	BOOL used_default = FALSE;
	while (source_length < 0 ? source[required] != 0 : required < source_length) {
		++required;
	}
	if (source_length < 0) {
		++required;
	}
	if (destination == NULL || destination_length == 0) {
		return required;
	}
	if (destination_length < required) {
		return 0;
	}
	for (int index = 0; index < required; ++index) {
		const WCHAR value = source[index];
		if (value <= 0xFFU) {
			destination[index] = (char)value;
		} else {
			destination[index] = replacement;
			used_default = TRUE;
		}
	}
	if (used_default_character != NULL) {
		*used_default_character = used_default;
	}
	return required;
}
