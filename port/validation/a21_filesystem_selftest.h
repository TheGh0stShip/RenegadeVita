#pragma once

#include "renegade_paths.h"

struct A21FilesystemSelfTestResult
{
	bool passed;
	bool path_translation;
	bool traversal_rejected;
	bool write_routed_outside_retail;
	bool original_file_available;
	bool original_file_read;
	bool archive_valid;
	bool archive_enumerated;
	bool known_entry_found;
	bool known_entry_read;
	bool factory_list_read;
	unsigned checks;
	unsigned failures;
	unsigned archive_entries;
	unsigned known_entry_size;
	unsigned known_entry_bytes_read;
	unsigned known_entry_prefix;
	char resolved_archive_path[1024];
	char first_failure[128];
};

A21FilesystemSelfTestResult Run_A21_Filesystem_Self_Test(
	const RenegadePathRoots &roots);

