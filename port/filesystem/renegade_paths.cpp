#include "renegade_paths.h"

#include <dirent.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

namespace {

// Case resolution used to re-read every directory on the path (one
// sceIoDread per entry on the memory card) for every asset open, sound play
// and texture load. The retail data root is never written while the game
// runs, so its complete listings are cached for the process lifetime, in
// readdir order, and resolved with the same exact-then-insensitive rule.
struct DirectoryListing {
	char *path;
	char **names;
	unsigned count;
	bool exists;
};

enum { kDirectoryListingCapacity = 128 };
DirectoryListing g_directory_listings[kDirectoryListingCapacity];
unsigned g_directory_listing_count = 0;
pthread_mutex_t g_directory_listing_mutex = PTHREAD_MUTEX_INITIALIZER;

void Free_Listing(DirectoryListing &listing)
{
	for (unsigned index = 0; index < listing.count; ++index) free(listing.names[index]);
	free(listing.names);
	free(listing.path);
	memset(&listing, 0, sizeof(listing));
}

// Reads a complete listing. Returns false (nothing cached) on any error other
// than a missing directory, so an unreadable card never pins a wrong answer.
bool Read_Listing(const char *path, DirectoryListing &listing)
{
	memset(&listing, 0, sizeof(listing));
	DIR *directory = opendir(path);
	if (directory == NULL) {
		if (errno != ENOENT && errno != ENOTDIR) return false;
		listing.exists = false;
	} else {
		listing.exists = true;
		unsigned capacity = 0;
		bool truncated = false;
		errno = 0;
		for (dirent *entry = readdir(directory); entry != NULL; entry = readdir(directory)) {
			if (listing.count == capacity) {
				const unsigned grown = capacity != 0 ? capacity * 2U : 64U;
				char **names = static_cast<char **>(realloc(listing.names, sizeof(char *) * grown));
				if (names == NULL) {
					truncated = true;
					break;
				}
				listing.names = names;
				capacity = grown;
			}
			char *name = strdup(entry->d_name);
			if (name == NULL) {
				truncated = true;
				break;
			}
			listing.names[listing.count++] = name;
			errno = 0;
		}
		const bool complete = !truncated && errno == 0;
		closedir(directory);
		if (!complete) {
			Free_Listing(listing);
			return false;
		}
	}
	listing.path = strdup(path);
	if (listing.path == NULL) {
		Free_Listing(listing);
		return false;
	}
	return true;
}

// Resolves one component against a cached listing. Returns false when the
// directory could not be listed; the caller then scans directly.
bool Select_From_Cached_Listing(const char *directory, const char *component,
	char *selected, size_t capacity, bool &scan_complete)
{
	pthread_mutex_lock(&g_directory_listing_mutex);
	DirectoryListing *listing = NULL;
	for (unsigned index = 0; index < g_directory_listing_count; ++index) {
		if (strcmp(g_directory_listings[index].path, directory) == 0) {
			listing = &g_directory_listings[index];
			break;
		}
	}
	if (listing == NULL && g_directory_listing_count < kDirectoryListingCapacity &&
		Read_Listing(directory, g_directory_listings[g_directory_listing_count])) {
		listing = &g_directory_listings[g_directory_listing_count++];
	}
	if (listing == NULL) {
		pthread_mutex_unlock(&g_directory_listing_mutex);
		return false;
	}
	const char *insensitive = NULL;
	const char *exact = NULL;
	for (unsigned index = 0; index < listing->count; ++index) {
		if (strcmp(listing->names[index], component) == 0) {
			exact = listing->names[index];
			break;
		}
		if (insensitive == NULL && strcasecmp(listing->names[index], component) == 0)
			insensitive = listing->names[index];
	}
	const char *match = exact != NULL ? exact : insensitive;
	if (match != NULL) {
		strncpy(selected, match, capacity - 1);
		selected[capacity - 1] = 0;
	}
	scan_complete = true;
	pthread_mutex_unlock(&g_directory_listing_mutex);
	return true;
}

void Set_Error(RenegadeResolvedPath &result, const char *message)
{
	result.success = false;
	strncpy(result.error, message, sizeof(result.error) - 1);
	result.error[sizeof(result.error) - 1] = 0;
}

bool Append_Component(char *path, size_t capacity, const char *component)
{
	const size_t path_length = strlen(path);
	const size_t component_length = strlen(component);
	const bool need_slash = path_length != 0 && path[path_length - 1] != '/';
	if (path_length + (need_slash ? 1U : 0U) + component_length + 1U > capacity) {
		return false;
	}
	if (need_slash) {
		path[path_length] = '/';
		path[path_length + (need_slash ? 1U : 0U)] = 0;
	}
	strcat(path, component);
	return true;
}

bool Has_Namespace(const char *path, const char *name, const char **remainder)
{
	const size_t length = strlen(name);
	if (strncasecmp(path, name, length) != 0) {
		return false;
	}
	if (path[length] == 0) {
		*remainder = path + length;
		return true;
	}
	if (path[length] != '/') {
		return false;
	}
	*remainder = path + length + 1;
	return true;
}

bool Normalize(const char *logical, char *normalized, size_t capacity)
{
	if (logical == NULL || logical[0] == 0 || logical[0] == '/' || logical[0] == '\\') {
		return false;
	}
	if (strchr(logical, ':') != NULL) {
		return false;
	}

	size_t output = 0;
	bool previous_slash = false;
	for (size_t index = 0; logical[index] != 0; ++index) {
		char value = logical[index] == '\\' ? '/' : logical[index];
		if (value == '/') {
			if (previous_slash) {
				continue;
			}
			previous_slash = true;
		} else {
			previous_slash = false;
		}
		if (output + 1 >= capacity) {
			return false;
		}
		normalized[output++] = value;
	}
	while (output != 0 && normalized[output - 1] == '/') {
		--output;
	}
	normalized[output] = 0;
	if (output == 0) {
		return false;
	}

	const char *component = normalized;
	while (*component != 0) {
		const char *slash = strchr(component, '/');
		const size_t length = slash == NULL ? strlen(component) : (size_t)(slash - component);
		if ((length == 1 && component[0] == '.') ||
			(length == 2 && component[0] == '.' && component[1] == '.')) {
			return false;
		}
		component = slash == NULL ? component + length : slash + 1;
	}
	return true;
}

bool Append_With_Existing_Case(char *physical, size_t capacity,
	const char *relative, bool &all_components_matched, bool &confirmed_missing,
	bool immutable_root)
{
	char remaining[768];
	strncpy(remaining, relative, sizeof(remaining) - 1);
	remaining[sizeof(remaining) - 1] = 0;

	char *component = remaining;
	while (*component != 0) {
		char *slash = strchr(component, '/');
		if (slash != NULL) {
			*slash = 0;
		}

		char selected[256];
		selected[0] = 0;
		bool scan_complete = false;
		DIR *directory = NULL;
		if (immutable_root && Select_From_Cached_Listing(physical, component,
				selected, sizeof(selected), scan_complete)) {
			// Resolved from the process-lifetime listing.
		} else if ((directory = opendir(physical)) != NULL) {
			char insensitive[256];
			insensitive[0] = 0;
			errno = 0;
			for (dirent *entry = readdir(directory); entry != NULL; entry = readdir(directory)) {
				if (strcmp(entry->d_name, component) == 0) {
					strncpy(selected, entry->d_name, sizeof(selected) - 1);
					selected[sizeof(selected) - 1] = 0;
					break;
				}
				if (insensitive[0] == 0 && strcasecmp(entry->d_name, component) == 0) {
					strncpy(insensitive, entry->d_name, sizeof(insensitive) - 1);
					insensitive[sizeof(insensitive) - 1] = 0;
				}
			}
			scan_complete = errno == 0;
			closedir(directory);
			if (selected[0] == 0 && insensitive[0] != 0) {
				strcpy(selected, insensitive);
			}
		} else {
			scan_complete = errno == ENOENT || errno == ENOTDIR;
		}

		if (selected[0] == 0) {
			all_components_matched = false;
			confirmed_missing = scan_complete;
			strncpy(selected, component, sizeof(selected) - 1);
			selected[sizeof(selected) - 1] = 0;
		}
		if (!Append_Component(physical, capacity, selected)) {
			return false;
		}
		if (!all_components_matched) {
			// Descendants of an absent/unsearchable component cannot improve
			// case resolution. Preserve the remaining logical path, but avoid
			// repeated opendir/stat failures for every descendant.
			return slash == NULL ||
				Append_Component(physical, capacity, slash + 1);
		}
		component = slash == NULL ? component + strlen(component) : slash + 1;
	}
	return true;
}

} // namespace

RenegadeResolvedPath Renegade_Resolve_Path(const RenegadePathRoots &roots,
	const char *logical_path, RenegadePathAccess access)
{
	RenegadeResolvedPath result = {};
	if (!Normalize(logical_path, result.normalized_logical,
			sizeof(result.normalized_logical))) {
		Set_Error(result, "invalid, absolute, overlong, or traversing logical path");
		return result;
	}

	// Original save menus enumerate data/save but pass bare .sav names to
	// SaveGameManager. Both refer to the writable save namespace on Vita.
	char *normalized = result.normalized_logical;
	const char *data_tail = NULL;
	const char *save_tail = NULL;
	if (Has_Namespace(normalized, "data", &data_tail) &&
		Has_Namespace(data_tail, "save", &save_tail)) {
		memmove(normalized, data_tail, strlen(data_tail) + 1U);
	}
	const size_t name_length = strlen(normalized);
	if (strchr(normalized, '/') == NULL && name_length > 4U &&
		strcasecmp(normalized + name_length - 4U, ".sav") == 0) {
		if (name_length + 6U > sizeof(result.normalized_logical)) {
			Set_Error(result, "save filename exceeds logical path capacity");
			return result;
		}
		memmove(normalized + 5, normalized, name_length + 1U);
		memcpy(normalized, "save/", 5U);
	}
	const char *relative = result.normalized_logical;
	const char *root = access == RENEGADE_PATH_WRITE ? roots.user : roots.retail;
	const char *namespace_remainder = NULL;
	if (Has_Namespace(relative, "user", &namespace_remainder)) {
		root = roots.user;
		relative = namespace_remainder;
		result.writable_namespace = true;
	} else if (Has_Namespace(relative, "cache", &namespace_remainder)) {
		root = roots.cache;
		relative = namespace_remainder;
		result.writable_namespace = true;
	} else if (Has_Namespace(relative, "save", &namespace_remainder)) {
		// Original SaveGameManager uses save\*.sav for both directions.
		// Keep the save/ component, but never resolve reads into retail.
		root = roots.user;
		result.writable_namespace = true;
	} else if (Has_Namespace(relative, "mods", &namespace_remainder)) {
		root = roots.mods;
		relative = namespace_remainder;
		result.writable_namespace = true;
	} else if (Has_Namespace(relative, "retail", &namespace_remainder)) {
		if (access == RENEGADE_PATH_WRITE) {
			Set_Error(result, "write access to the retail namespace is forbidden");
			return result;
		}
		root = roots.retail;
		relative = namespace_remainder;
	} else {
		result.writable_namespace = access == RENEGADE_PATH_WRITE;
	}

	if (root == NULL || root[0] == 0 || relative[0] == 0) {
		Set_Error(result, "empty root or logical path namespace");
		return result;
	}
	if (strlen(root) + 1 >= sizeof(result.physical)) {
		Set_Error(result, "platform root is too long");
		return result;
	}
	strcpy(result.physical, root);
	while (strlen(result.physical) > 1 &&
		result.physical[strlen(result.physical) - 1] == '/') {
		result.physical[strlen(result.physical) - 1] = 0;
	}

	result.existing_case_matched = true;
	if (access == RENEGADE_PATH_READ) {
		if (!Append_With_Existing_Case(result.physical, sizeof(result.physical),
				relative, result.existing_case_matched, result.confirmed_missing,
				!result.writable_namespace)) {
			Set_Error(result, "translated read path is too long");
			return result;
		}
	} else if (!Append_Component(result.physical, sizeof(result.physical), relative)) {
		Set_Error(result, "translated write path is too long");
		return result;
	}

	result.success = true;
	return result;
}
