#pragma once

// Versioned user preferences only. No retail paths, device selectors, save
// state or serialized engine objects cross this platform boundary.
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

namespace RenegadeVitaUserSettings {
enum { Audio = 1, Performance = 2, Count = 13 };
struct Record { unsigned value[Count] = {}; };
struct Store { Record record; char path[1024] = {}; };
inline Store &State() { static Store state; return state; }

inline bool Valid(const Record &r)
{
	if (r.value[0] > 3) return false;
	for (int i = 1; i <= 4; ++i) if (r.value[i] > 100) return false;
	for (int i = 5; i <= 8; ++i) if (r.value[i] > 1) return false;
	return r.value[9] <= 1000000 && r.value[10] <= 1000000 &&
		r.value[11] <= 2 && r.value[12] <= 2;
}

inline bool Parse(const char *text, Record &result)
{
	if (text == NULL || strncmp(text, "RVOPT1 ", 7) != 0) return false;
	const char *cursor = text + 7;
	Record candidate;
	for (int i = 0; i < Count; ++i) {
		if (*cursor < '0' || *cursor > '9') return false;
		unsigned value = 0;
		do {
			if (value > 1000000U) return false;
			value = value * 10U + static_cast<unsigned>(*cursor++ - '0');
		} while (*cursor >= '0' && *cursor <= '9');
		candidate.value[i] = value;
		if (i + 1 < Count && *cursor++ != ' ') return false;
	}
	if (strcmp(cursor, "\n") != 0 || !Valid(candidate)) return false;
	result = candidate;
	return true;
}

// Called by the lifecycle with its own user/config path, never by UI text.
// Missing preferences preserve the candidate's existing defaults.
inline bool Configure(const char *path)
{
	Store &state = State();
	state = Store{};
	if (path == NULL || strlen(path) + 5 >= sizeof(state.path)) return false;
	strcpy(state.path, path);
	FILE *file = fopen(path, "rb");
	if (file == NULL) return errno == ENOENT;
	char text[256] = {};
	const size_t count = fread(text, 1, sizeof(text) - 1, file);
	const bool read_ok = !ferror(file) && feof(file) && count != 0 &&
		memchr(text, 0, count) == NULL;
	const bool closed = fclose(file) == 0;
	return read_ok && closed && Parse(text, state.record);
}

inline bool Save(const Record &record)
{
	Store &state = State();
	if (state.path[0] == 0 || !Valid(record)) return false;
	char temporary[sizeof(state.path) + 4];
	snprintf(temporary, sizeof(temporary), "%s.tmp", state.path);
	FILE *file = fopen(temporary, "wb");
	if (file == NULL) return false;
	bool ok = fputs("RVOPT1", file) >= 0;
	for (int i = 0; i < Count; ++i) ok = fprintf(file, " %u", record.value[i]) > 0 && ok;
	ok = fputc('\n', file) != EOF && ok;
	ok = fflush(file) == 0 && ok;
	ok = fsync(fileno(file)) == 0 && ok;
	ok = fclose(file) == 0 && ok;
	if (ok) ok = rename(temporary, state.path) == 0;
	if (!ok) { remove(temporary); return false; }
	state.record = record;
	return true;
}
} // namespace RenegadeVitaUserSettings
