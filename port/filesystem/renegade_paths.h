#pragma once

#include <stddef.h>

enum RenegadePathAccess
{
	RENEGADE_PATH_READ,
	RENEGADE_PATH_WRITE
};

struct RenegadePathRoots
{
	const char *retail;
	const char *user;
	const char *cache;
	const char *mods;
};

struct RenegadeResolvedPath
{
	bool success;
	bool existing_case_matched;
	bool writable_namespace;
	char physical[1024];
	char normalized_logical[768];
	char error[128];
};

// Translate a logical Renegade path at the platform boundary. Read-only game
// data defaults to retail; writes default to user. Explicit user/, cache/, and
// mods/ namespaces select their corresponding writable roots. Traversal,
// absolute host paths, and drive/device paths are rejected.
RenegadeResolvedPath Renegade_Resolve_Path(const RenegadePathRoots &roots,
	const char *logical_path, RenegadePathAccess access);

