#include "renegade_find_files.h"

#include <dirent.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>
#if defined(__vita__)
#include <psp2/io/devctl.h>
#include <psp2/io/stat.h>
#include <psp2/rtc.h>
#else
#include <sys/statvfs.h>
#endif

namespace {

RenegadePathRoots Roots = {};

struct FindContext
{
	DIR *directory;
	char physical_directory[1024];
	char pattern[256];
};

void Set_Last_Write_Time(const FindContext *context, const char *name,
	WIN32_FIND_DATA *result)
{
	if (context == NULL || name == NULL || result == NULL) return;
	char physical_name[1536];
	const int length = snprintf(physical_name, sizeof(physical_name), "%s/%s",
		context->physical_directory, name);
	if (length < 0 || static_cast<size_t>(length) >= sizeof(physical_name)) return;
#if defined(__vita__)
	SceIoStat info = {};
	SceUInt64 ticks = 0;
	if (sceIoGetstat(physical_name, &info) < 0 ||
		sceRtcGetWin32FileTime(&info.st_mtime, &ticks) < 0) return;
	if (SCE_S_ISDIR(info.st_mode)) result->dwFileAttributes |= FILE_ATTRIBUTE_DIRECTORY;
#else
	struct stat info;
	if (stat(physical_name, &info) != 0 || info.st_mtime < 0) return;
	if (S_ISDIR(info.st_mode)) result->dwFileAttributes |= FILE_ATTRIBUTE_DIRECTORY;
	const uint64_t ticks = (static_cast<uint64_t>(info.st_mtime) + 11644473600ULL) * 10000000ULL;
#endif
	result->ftLastWriteTime.dwLowDateTime = static_cast<DWORD>(ticks & 0xffffffffULL);
	result->ftLastWriteTime.dwHighDateTime = static_cast<DWORD>(ticks >> 32U);
}

char Fold_Ascii(char value)
{
	return value >= 'A' && value <= 'Z' ? (char)(value + ('a' - 'A')) : value;
}

// The original menu asks only for DOS-style filename globs.  Keep matching
// local and ASCII case-insensitive so the Vita path never relies on a host
// extension such as FNM_CASEFOLD, which Vita's libc intentionally omits.
bool Match_Pattern(const char *pattern, const char *name)
{
	const char *star = NULL;
	const char *retry = NULL;
	while (*name != 0) {
		if (*pattern == '?' || Fold_Ascii(*pattern) == Fold_Ascii(*name)) {
			++pattern;
			++name;
			continue;
		}
		if (*pattern == '*') {
			star = ++pattern;
			retry = name;
			continue;
		}
		if (star != NULL) {
			pattern = star;
			name = ++retry;
			continue;
		}
		return false;
	}
	while (*pattern == '*') ++pattern;
	return *pattern == 0;
}

bool Normalize_Pattern(const char *logical_pattern, char *directory,
	size_t directory_capacity, char *pattern, size_t pattern_capacity)
{
	if (logical_pattern == NULL || directory == NULL || pattern == NULL) return false;
	char normalized[768];
	const size_t length = strlen(logical_pattern);
	if (length == 0U || length >= sizeof(normalized)) return false;
	for (size_t index = 0U; index <= length; ++index) {
		normalized[index] = logical_pattern[index] == '\\' ? '/' : logical_pattern[index];
	}
	char *slash = strrchr(normalized, '/');
	if (slash == NULL || slash == normalized || slash[1] == 0) return false;
	*slash = 0;
	if (strlen(normalized) >= directory_capacity || strlen(slash + 1) >= pattern_capacity) {
		return false;
	}
	strcpy(directory, normalized);
	strcpy(pattern, slash + 1);
	return true;
}

BOOL Next_Match(FindContext *context, WIN32_FIND_DATA *result)
{
	if (context == NULL || context->directory == NULL || result == NULL) return 0;
	for (dirent *entry = readdir(context->directory); entry != NULL;
		entry = readdir(context->directory)) {
		if (!Match_Pattern(context->pattern, entry->d_name)) continue;
		if (strlen(entry->d_name) >= sizeof(result->cFileName)) continue;
		memset(result, 0, sizeof(*result));
		strcpy(result->cFileName, entry->d_name);
		Set_Last_Write_Time(context, entry->d_name, result);
		return 1;
	}
	return 0;
}

} // namespace

bool Renegade_Get_User_Free_Space(uint64_t &bytes)
{
	bytes = 0;
	if (Roots.user == NULL || Roots.user[0] == '\0') return false;
#if defined(__vita__)
	// Writable game state is restricted to the user's ux0 volume.
	if (strncmp(Roots.user, "ux0:", 4) != 0) return false;
	SceIoDevInfo info = {};
	if (sceIoDevctl("ux0:", 0x3001, NULL, 0, &info, sizeof(info)) < 0 ||
		info.free_size < 0) return false;
	bytes = static_cast<uint64_t>(info.free_size);
#else
	struct statvfs info = {};
	if (statvfs(Roots.user, &info) != 0 || info.f_frsize == 0 ||
		static_cast<uint64_t>(info.f_bavail) > UINT64_MAX / info.f_frsize) return false;
	bytes = static_cast<uint64_t>(info.f_bavail) * info.f_frsize;
#endif
	return true;
}

bool Renegade_Delete_User_Save(const char *logical_path)
{
	const RenegadeResolvedPath resolved = Renegade_Resolve_Path(Roots,
		logical_path, RENEGADE_PATH_READ);
	return resolved.success && resolved.writable_namespace &&
		strncasecmp(resolved.normalized_logical, "save/", 5) == 0 &&
		remove(resolved.physical) == 0;
}

void Renegade_Set_Find_Roots(const RenegadePathRoots &roots)
{
	Roots = roots;
}

HANDLE Renegade_Find_First(const char *logical_pattern, WIN32_FIND_DATA *result)
{
	char logical_directory[768];
	char pattern[256];
	if (!Normalize_Pattern(logical_pattern, logical_directory, sizeof(logical_directory),
		pattern, sizeof(pattern))) return INVALID_HANDLE_VALUE;
	const RenegadeResolvedPath resolved = Renegade_Resolve_Path(Roots,
		logical_directory, RENEGADE_PATH_READ);
	if (!resolved.success) return INVALID_HANDLE_VALUE;
	FindContext *context = static_cast<FindContext *>(calloc(1U, sizeof(FindContext)));
	if (context == NULL) return INVALID_HANDLE_VALUE;
	context->directory = opendir(resolved.physical);
	if (context->directory == NULL) {
		free(context);
		return INVALID_HANDLE_VALUE;
	}
	strcpy(context->physical_directory, resolved.physical);
	strcpy(context->pattern, pattern);
	if (!Next_Match(context, result)) {
		closedir(context->directory);
		free(context);
		return INVALID_HANDLE_VALUE;
	}
	return context;
}

BOOL Renegade_Find_Next(HANDLE handle, WIN32_FIND_DATA *result)
{
	return Next_Match(static_cast<FindContext *>(handle), result);
}

BOOL Renegade_Find_Close(HANDLE handle)
{
	FindContext *context = static_cast<FindContext *>(handle);
	if (context == NULL || context == INVALID_HANDLE_VALUE) return 0;
	const int status = context->directory == NULL ? 0 : closedir(context->directory);
	free(context);
	return status == 0 ? 1 : 0;
}
