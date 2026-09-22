#ifndef RENEGADE_A31_DEVELOPMENT_CHECKPOINT_H
#define RENEGADE_A31_DEVELOPMENT_CHECKPOINT_H

#include <stddef.h>
#include <string.h>

// Development launch metadata only. Original SaveGameManager owns save data.
namespace A31DevelopmentCheckpoint {
inline bool Alphanumeric(char value)
{
	return (value >= 'a' && value <= 'z') ||
		(value >= 'A' && value <= 'Z') || (value >= '0' && value <= '9');
}

inline bool Parse(const char *data, size_t bytes, char *source, size_t capacity)
{
	if (source == NULL || capacity == 0U) return false;
	source[0] = '\0';
	if (data == NULL || bytes < 12U || bytes > 76U ||
		memcmp(data, "RVCP1 ", 6U) != 0 || data[bytes - 1U] != '\n') return false;
	size_t end = bytes - 1U;
	if (data[end - 1U] == '\r') --end;
	const size_t length = end - 6U;
	if (length < 5U || length > 68U || !Alphanumeric(data[6])) return false;
	const size_t extension = end - 4U;
	if (data[extension] != '.' ||
		(data[extension + 1U] != 's' && data[extension + 1U] != 'S') ||
		(data[extension + 2U] != 'a' && data[extension + 2U] != 'A') ||
		(data[extension + 3U] != 'v' && data[extension + 3U] != 'V')) return false;
	for (size_t index = 6U; index < extension; ++index) {
		if (!Alphanumeric(data[index]) && data[index] != '_' && data[index] != '-') return false;
	}
	if (capacity < 5U + length + 1U) return false;
	memcpy(source, "save/", 5U);
	memcpy(source + 5U, data + 6U, length);
	source[5U + length] = '\0';
	return true;
}

inline bool Parse_Mission(const char *data, size_t bytes, char *source,
	size_t capacity)
{
	if (source == NULL || capacity == 0U) return false;
	source[0] = '\0';
	if (data == NULL || (bytes != 14U && bytes != 15U) ||
		memcmp(data, "RVMS1 ", 6U) != 0 || data[bytes - 1U] != '\n' ||
		(bytes == 15U && data[13U] != '\r')) return false;
	const char *map = data + 6U;
	if (map[0] != 'M' || map[1] < '0' || map[1] > '9' ||
		map[2] < '0' || map[2] > '9' ||
		memcmp(map + 3U, ".mix", 4U) != 0 || capacity < 8U) return false;
	memcpy(source, map, 7U);
	source[7U] = '\0';
	return true;
}

inline bool Parse_M13_Completion(const char *data, size_t bytes)
{
	static const char request[] = "RVMC1 M13.mix\n";
	return data != NULL && bytes == sizeof(request) - 1U &&
		memcmp(data, request, sizeof(request) - 1U) == 0;
}
} // namespace A31DevelopmentCheckpoint

#endif
