#pragma once

// Durable provider for the original Commando Movies registry key. Campaign
// code still owns which movies are unlocked and which translated description
// key is associated with each original logical filename.
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <memory>
#include <new>
#include <pthread.h>

#ifdef __vita__
// sceIoRename does not replace an existing destination; use the rooted
// file-factory replace helper (renegade_file_factory.cpp).
bool Renegade_Replace_File(const char *source, const char *destination);
bool Renegade_Recover_Interrupted_Replace(const char *destination);
#define RENEGADE_STORE_REPLACE(source, destination) Renegade_Replace_File(source, destination)
#define RENEGADE_STORE_RECOVER(destination) ((void)Renegade_Recover_Interrupted_Replace(destination))
#else
#define RENEGADE_STORE_REPLACE(source, destination) (rename(source, destination) == 0)
#define RENEGADE_STORE_RECOVER(destination) ((void)0)
#endif

namespace RenegadeMovieUnlocks {
enum { MaxEntries = 64, NameBytes = 192, DescriptionBytes = 192, PathBytes = 1024 };
struct Entry { char name[NameBytes] = {}; char description[DescriptionBytes] = {}; };
struct Record { Entry entries[MaxEntries]; unsigned count = 0; };
struct Store {
	Record record;
	char path[PathBytes] = {};
	char key[192] = {};
	bool writable = false;
	bool last_write_ok = true;
	int error = 0;
};
inline Store &State() { static Store store; return store; }
inline pthread_mutex_t &Mutex() { static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER; return mutex; }
struct Lock {
	Lock() { pthread_mutex_lock(&Mutex()); }
	~Lock() { pthread_mutex_unlock(&Mutex()); }
	Lock(const Lock &) = delete;
	Lock &operator=(const Lock &) = delete;
};
inline unsigned char Lower(unsigned char c) { return c >= 'A' && c <= 'Z' ? c + ('a' - 'A') : c; }
inline bool Equal(const char *a, const char *b)
{
	if (a == NULL || b == NULL) return false;
	while (*a && Lower((unsigned char)*a) == Lower((unsigned char)*b)) { ++a; ++b; }
	return *a == 0 && *b == 0;
}
inline bool Copy(const char *source, char *destination, size_t capacity)
{
	if (source == NULL || destination == NULL || capacity == 0U) return false;
	const size_t length = strlen(source);
	if (length == 0U || length >= capacity) return false;
	memcpy(destination, source, length + 1U);
	return true;
}
inline bool Copy_Optional(const char *source, char *destination, size_t capacity)
{
	if (destination == NULL || capacity == 0U) return false;
	if (source == NULL) source = "";
	const size_t length = strlen(source);
	if (length >= capacity) return false;
	memcpy(destination, source, length + 1U);
	return true;
}
inline int Find(const Record &record, const char *name)
{
	for (unsigned index = 0; index < record.count; ++index)
		if (Equal(record.entries[index].name, name)) return (int)index;
	return -1;
}
inline char Hex(unsigned value) { return value < 10U ? (char)('0' + value) : (char)('A' + value - 10U); }
inline int Unhex(char value)
{
	if (value >= '0' && value <= '9') return value - '0';
	if (value >= 'A' && value <= 'F') return value - 'A' + 10;
	if (value >= 'a' && value <= 'f') return value - 'a' + 10;
	return -1;
}
inline bool Write_Hex(FILE *file, const char *value)
{
	for (const unsigned char *cursor = (const unsigned char *)value; *cursor; ++cursor)
		if (fputc(Hex(*cursor >> 4), file) == EOF || fputc(Hex(*cursor & 15U), file) == EOF) return false;
	return true;
}
inline bool Read_Hex(const char *text, char *value, size_t capacity)
{
	const size_t length = strlen(text);
	if (length == 0U || (length & 1U) != 0U || length / 2U >= capacity) return false;
	for (size_t index = 0; index < length; index += 2U) {
		const int high = Unhex(text[index]);
		const int low = Unhex(text[index + 1U]);
		if (high < 0 || low < 0) return false;
		value[index / 2U] = (char)((high << 4) | low);
		if (value[index / 2U] == 0) return false;
	}
	value[length / 2U] = 0;
	return true;
}
inline bool Read_Optional_Hex(const char *text, char *value, size_t capacity)
{
	if (text != NULL && strcmp(text, "-") == 0 && value != NULL && capacity != 0U) {
		value[0] = 0;
		return true;
	}
	return Read_Hex(text, value, capacity);
}
inline bool Read(FILE *file, Record &result)
{
	char line[(NameBytes + DescriptionBytes) * 2 + 4];
	if (fgets(line, sizeof(line), file) == NULL || strcmp(line, "RVMOV1\n") != 0) return false;
	if (fgets(line, sizeof(line), file) == NULL || strncmp(line, "COUNT ", 6) != 0) return false;
	char *end = NULL;
	errno = 0;
	const unsigned long count = strtoul(line + 6, &end, 10);
	if (errno != 0 || end == line + 6 || strcmp(end, "\n") != 0 || count > MaxEntries) return false;
	result.count = 0;
	for (unsigned index = 0; index < count; ++index) {
		if (fgets(line, sizeof(line), file) == NULL) return false;
		const size_t length = strlen(line);
		if (length == 0U || line[length - 1U] != '\n') return false;
		line[length - 1U] = 0;
		char *separator = strchr(line, ' ');
		if (separator == NULL) return false;
		*separator++ = 0;
		Entry entry;
		if (!Read_Hex(line, entry.name, sizeof(entry.name)) ||
			!Read_Optional_Hex(separator, entry.description, sizeof(entry.description)) ||
			Find(result, entry.name) >= 0) return false;
		result.entries[result.count++] = entry;
	}
	return fgets(line, sizeof(line), file) != NULL && strcmp(line, "END\n") == 0 &&
		fgetc(file) == EOF && !ferror(file);
}
inline bool Configure(const char *path, const char *key)
{
	Lock lock;
	Store &store = State();
	store.record.count = 0;
	store.path[0] = 0;
	store.key[0] = 0;
	store.writable = false;
	store.last_write_ok = true;
	store.error = 0;
	if (path == NULL || key == NULL || !Copy(path, store.path, sizeof(store.path)) ||
		!Copy(key, store.key, sizeof(store.key)) || strlen(path) + 5U >= sizeof(store.path)) {
		store.error = EINVAL;
		return false;
	}
	RENEGADE_STORE_RECOVER(path);
	FILE *file = fopen(path, "rb");
	if (file == NULL) {
		if (errno == ENOENT) { store.writable = true; return true; }
		store.error = errno;
		return false;
	}
	std::unique_ptr<Record> loaded(new (std::nothrow) Record);
	const bool valid = loaded && Read(file, *loaded);
	int error = valid ? 0 : (loaded ? EINVAL : ENOMEM);
	if (fclose(file) != 0 && error == 0) error = errno ? errno : EIO;
	if (error != 0) { store.error = error; return false; }
	store.record = *loaded;
	store.writable = true;
	return true;
}
inline bool Matches_Key(const char *key)
{
	Lock lock;
	return State().key[0] != 0 && Equal(State().key, key);
}
inline void Check_IO(bool ok, int &error) { if (!ok && error == 0) error = errno ? errno : EIO; }
// Caller holds Mutex. Publish the new record only after same-directory replace.
inline bool Save(const Record &record)
{
	Store &store = State();
	if (!store.writable) { store.last_write_ok = false; return false; }
	char temporary[PathBytes];
	const int length = snprintf(temporary, sizeof(temporary), "%s.tmp", store.path);
	if (length < 0 || (size_t)length >= sizeof(temporary)) {
		store.error = ENAMETOOLONG; store.last_write_ok = false; return false;
	}
	FILE *file = fopen(temporary, "wb");
	if (file == NULL) { store.error = errno; store.last_write_ok = false; return false; }
	int error = 0;
	Check_IO(fputs("RVMOV1\n", file) >= 0, error);
	Check_IO(fprintf(file, "COUNT %u\n", record.count) > 0, error);
	for (unsigned index = 0; index < record.count; ++index) {
		Check_IO(Write_Hex(file, record.entries[index].name), error);
		Check_IO(fputc(' ', file) != EOF, error);
		if (record.entries[index].description[0] == 0)
			Check_IO(fputc('-', file) != EOF, error);
		else
			Check_IO(Write_Hex(file, record.entries[index].description), error);
		Check_IO(fputc('\n', file) != EOF, error);
	}
	Check_IO(fputs("END\n", file) >= 0, error);
	Check_IO(fflush(file) == 0, error);
	Check_IO(fsync(fileno(file)) == 0, error);
	Check_IO(fclose(file) == 0, error);
	if (error == 0) Check_IO(RENEGADE_STORE_REPLACE(temporary, store.path), error);
	if (error != 0) remove(temporary);
	store.error = error;
	store.last_write_ok = error == 0;
	if (error == 0) store.record = record;
	return error == 0;
}
inline bool Set(const char *name, const char *description)
{
	Lock lock;
	Store &store = State();
	Entry checked;
	if (!store.writable || !Copy(name, checked.name, sizeof(checked.name)) ||
		!Copy_Optional(description, checked.description, sizeof(checked.description))) {
		store.error = EINVAL; store.last_write_ok = false; return false;
	}
	const int found = Find(store.record, checked.name);
	if (found >= 0 && strcmp(store.record.entries[found].description, checked.description) == 0) {
		store.error = 0; store.last_write_ok = true; return true;
	}
	std::unique_ptr<Record> next(new (std::nothrow) Record(store.record));
	if (!next) { store.error = ENOMEM; store.last_write_ok = false; return false; }
	if (found < 0 && next->count == MaxEntries) { store.error = ENOSPC; store.last_write_ok = false; return false; }
	const unsigned slot = found >= 0 ? (unsigned)found : next->count++;
	next->entries[slot] = checked;
	return Save(*next);
}
inline bool Get(const char *name, char *value, size_t capacity)
{
	Lock lock;
	const int found = Find(State().record, name);
	if (found < 0 || value == NULL || capacity == 0U) return false;
	strncpy(value, State().record.entries[found].description, capacity - 1U);
	value[capacity - 1U] = 0;
	return true;
}
inline bool Get_Name(unsigned index, char *value, size_t capacity)
{
	Lock lock;
	if (index >= State().record.count || value == NULL || capacity == 0U) return false;
	strncpy(value, State().record.entries[index].name, capacity - 1U);
	value[capacity - 1U] = 0;
	return true;
}
inline bool Delete(const char *name)
{
	Lock lock;
	const int found = Find(State().record, name);
	if (found < 0) return true;
	std::unique_ptr<Record> next(new (std::nothrow) Record(State().record));
	if (!next) { State().error = ENOMEM; State().last_write_ok = false; return false; }
	next->entries[found] = next->entries[--next->count];
	return Save(*next);
}
inline bool Clear()
{
	Lock lock;
	std::unique_ptr<Record> empty(new (std::nothrow) Record);
	if (!empty) { State().error = ENOMEM; State().last_write_ok = false; return false; }
	return Save(*empty);
}
struct Status { bool ready; bool last_write_ok; int error; unsigned count; };
inline Status Get_Status()
{
	Lock lock;
	return {State().writable, State().last_write_ok, State().error, State().record.count};
}
} // namespace RenegadeMovieUnlocks
