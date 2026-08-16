#include "renegade_cache_health.h"

#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>

namespace {

const char *const kIndexSchema = "renegade-vita-mix-index-v1";
const uint32_t kMaximumEntries = 65536U;
const size_t kMaximumLineBytes = 512U;

void Set_Detail(RenegadeCacheHealth &result, const char *detail)
{
	strncpy(result.detail, detail, sizeof(result.detail) - 1U);
	result.detail[sizeof(result.detail) - 1U] = 0;
}

bool Read_Line(FILE *input, char line[kMaximumLineBytes])
{
	if (fgets(line, static_cast<int>(kMaximumLineBytes), input) == NULL) {
		return false;
	}
	const size_t length = strlen(line);
	if (length == 0U || line[length - 1U] != '\n') {
		return false;
	}
	line[length - 1U] = 0;
	return true;
}

bool Has_Prefix(const char *line, const char *prefix, const char **value)
{
	const size_t length = strlen(prefix);
	if (strncmp(line, prefix, length) != 0 || line[length] == 0) {
		return false;
	}
	*value = line + length;
	return true;
}

bool Parse_Count(const char *value, uint32_t &count)
{
	if (value == NULL || value[0] == 0) return false;
	uint64_t parsed = 0U;
	for (const char *cursor = value; *cursor != 0; ++cursor) {
		if (!isdigit(static_cast<unsigned char>(*cursor))) return false;
		parsed = parsed * 10U + static_cast<unsigned>(*cursor - '0');
		if (parsed > kMaximumEntries) return false;
	}
	count = static_cast<uint32_t>(parsed);
	return count != 0U;
}

bool Is_Cache_Namespace(const char *logical)
{
	const char prefix[] = "cache/";
	return logical != NULL && strncasecmp(logical, prefix, sizeof(prefix) - 1U) == 0;
}

} // namespace

const char *Renegade_Cache_Health_Name(RenegadeCacheHealthState state)
{
	switch (state) {
	case RENEGADE_CACHE_HEALTH_MISSING: return "missing";
	case RENEGADE_CACHE_HEALTH_VALID: return "valid";
	case RENEGADE_CACHE_HEALTH_CORRUPT: return "corrupt";
	case RENEGADE_CACHE_HEALTH_UNSAFE_PATH: return "unsafe-path";
	}
	return "unknown";
}

RenegadeCacheHealth Renegade_Inspect_Mix_Index_Cache(
	const RenegadePathRoots &roots, const char *archive_name,
	const char *cache_logical)
{
	RenegadeCacheHealth result = {};
	result.state = RENEGADE_CACHE_HEALTH_UNSAFE_PATH;
	if (archive_name == NULL || archive_name[0] == 0 ||
		strlen(archive_name) >= sizeof(result.archive) ||
		!Is_Cache_Namespace(cache_logical)) {
		Set_Detail(result, "invalid archive or cache logical path");
		return result;
	}
	strcpy(result.archive, archive_name);

	const RenegadeResolvedPath resolved = Renegade_Resolve_Path(roots,
		cache_logical, RENEGADE_PATH_READ);
	if (!resolved.success || !resolved.writable_namespace ||
		strncasecmp(resolved.normalized_logical, "cache/", 6U) != 0) {
		Set_Detail(result, "cache path rejected by platform boundary");
		return result;
	}
	strncpy(result.physical_path, resolved.physical,
		sizeof(result.physical_path) - 1U);
	result.physical_path[sizeof(result.physical_path) - 1U] = 0;

	FILE *input = fopen(result.physical_path, "rb");
	if (input == NULL) {
		result.state = RENEGADE_CACHE_HEALTH_MISSING;
		Set_Detail(result, "optional cache index is absent");
		return result;
	}

	char line[kMaximumLineBytes] = {};
	const char *value = NULL;
	bool valid = Read_Line(input, line) && Has_Prefix(line, "schema=", &value) &&
		strcmp(value, kIndexSchema) == 0;
	if (!valid) {
		Set_Detail(result, "cache index schema is invalid");
	} else if (!Read_Line(input, line) || !Has_Prefix(line, "archive=", &value) ||
		strcasecmp(value, archive_name) != 0) {
		valid = false;
		Set_Detail(result, "cache index archive does not match");
	}

	uint32_t declared_count = 0U;
	if (valid && (!Read_Line(input, line) || !Has_Prefix(line, "entry_count=", &value) ||
		!Parse_Count(value, declared_count))) {
		valid = false;
		Set_Detail(result, "cache index entry count is invalid");
	}

	char prior[kMaximumLineBytes] = {};
	for (uint32_t index = 0U; valid && index < declared_count; ++index) {
		if (!Read_Line(input, line) || !Has_Prefix(line, "entry=", &value) ||
			strlen(value) >= sizeof(prior) || (index != 0U && strcmp(prior, value) > 0)) {
			valid = false;
			Set_Detail(result, "cache index entries are invalid or unordered");
			break;
		}
		strcpy(prior, value);
	}
	if (valid && fgets(line, static_cast<int>(sizeof(line)), input) != NULL) {
		valid = false;
		Set_Detail(result, "cache index has trailing data");
	}
	const bool closed = fclose(input) == 0;
	if (!closed) {
		valid = false;
		Set_Detail(result, "cache index close failed");
	}
	result.entry_count = declared_count;
	result.state = valid ? RENEGADE_CACHE_HEALTH_VALID : RENEGADE_CACHE_HEALTH_CORRUPT;
	if (valid) Set_Detail(result, "optional cache index is structurally valid");
	return result;
}
