#pragma once

// Durable replacement for the original Win32 mission-rank registry key.
// This is user configuration, never a retail file or an engine save format.
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <memory>
#include <new>
#include <pthread.h>

namespace RenegadeMissionRanks {
enum { MaxEntries = 128, NameBytes = 96, PathBytes = 1024 };
static_assert(sizeof(int) == sizeof(int32_t), "Original registry integers are 32-bit");
struct Entry { char name[NameBytes] = {}; int32_t value = 0; };
struct Record { Entry entries[MaxEntries]; unsigned count = 0; };
struct Store {
    Record record;
    char path[PathBytes] = {};
    char key[NameBytes] = {};
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
    while (*a && Lower(static_cast<unsigned char>(*a)) == Lower(static_cast<unsigned char>(*b))) { ++a; ++b; }
    return *a == 0 && *b == 0;
}
inline bool Name(const char *source, char *result)
{
    if (source == NULL || *source == 0) return false;
    unsigned i = 0;
    for (; source[i] != 0; ++i) {
        const unsigned char c = static_cast<unsigned char>(source[i]);
        if (i + 1 >= NameBytes || !((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') || c == '_' || c == '-' || c == '.')) return false;
        result[i] = static_cast<char>(c);
    }
    result[i] = 0;
    return true;
}
inline int Find(const Record &record, const char *name)
{
    for (unsigned i = 0; i < record.count; ++i) if (Equal(record.entries[i].name, name)) return static_cast<int>(i);
    return -1;
}
inline bool Read(FILE *file, Record &result)
{
    char line[NameBytes + 32];
    if (fgets(line, sizeof(line), file) == NULL || strcmp(line, "RVRANK1\n") != 0) return false;
    if (fgets(line, sizeof(line), file) == NULL || strncmp(line, "COUNT ", 6) != 0) return false;
    unsigned expected = 0;
    const char *digits = line + 6;
    if (*digits < '0' || *digits > '9') return false;
    for (; *digits >= '0' && *digits <= '9'; ++digits) {
        expected = expected * 10 + static_cast<unsigned>(*digits - '0');
        if (expected > MaxEntries) return false;
    }
    if (strcmp(digits, "\n") != 0) return false;
    result.count = 0;
    for (unsigned i = 0; i < expected; ++i) {
        if (fgets(line, sizeof(line), file) == NULL) return false;
        const size_t length = strlen(line);
        if (length == 0 || line[length - 1] != '\n' || result.count == MaxEntries) return false;
        line[length - 1] = 0;
        char *number = strchr(line, ' ');
        if (number == NULL) return false;
        *number++ = 0;
        char *digits = number + (*number == '-' ? 1 : 0);
        if (*digits < '0' || *digits > '9') return false;
        for (char *p = digits; *p; ++p) if (*p < '0' || *p > '9') return false;
        Entry entry;
        if (!Name(line, entry.name) || Find(result, entry.name) >= 0) return false;
        char *end = NULL;
        errno = 0;
        const long value = strtol(number, &end, 10);
        if (errno == ERANGE || *end != 0 || value < INT32_MIN || value > INT32_MAX) return false;
        entry.value = static_cast<int32_t>(value);
        result.entries[result.count++] = entry;
    }
    // A count and mandatory trailer also reject truncation at row boundaries.
    return fgets(line, sizeof(line), file) != NULL && strcmp(line, "END\n") == 0 &&
        fgetc(file) == EOF && !ferror(file);
}

// Only the lifecycle supplies the rooted path and original registry key.
// A corrupt/unreadable existing file disables writes rather than resetting it.
inline bool Configure(const char *path, const char *key)
{
    Lock lock;
    Store &store = State();
    store.record.count = 0;
    store.path[0] = store.key[0] = 0;
    store.writable = false;
    store.last_write_ok = true;
    store.error = 0;
    if (path == NULL || key == NULL || *path == 0 || *key == 0 ||
        strlen(path) + 5 >= sizeof(store.path) || strlen(key) >= sizeof(store.key)) {
        store.error = EINVAL;
        return false;
    }
    strcpy(store.path, path);
    strcpy(store.key, key);
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
inline int Get(const char *name, int fallback = 0)
{
    Lock lock;
    const int index = Find(State().record, name);
    return index < 0 ? fallback : State().record.entries[index].value;
}
inline void Check_IO(bool ok, int &error)
{
    if (!ok && error == 0) error = errno ? errno : EIO;
}
// Caller holds Mutex. Only successful replacement publishes the in-memory data.
inline bool Save(const Record &record)
{
    Store &store = State();
    if (!store.writable) { store.last_write_ok = false; return false; }
    char temporary[PathBytes];
    const int length = snprintf(temporary, sizeof(temporary), "%s.tmp", store.path);
    if (length < 0 || static_cast<size_t>(length) >= sizeof(temporary)) {
        store.error = ENAMETOOLONG;
        store.last_write_ok = false;
        return false;
    }
    FILE *file = fopen(temporary, "wb");
    if (file == NULL) { store.error = errno; store.last_write_ok = false; return false; }
    int error = 0;
    Check_IO(fputs("RVRANK1\n", file) >= 0, error);
    Check_IO(fprintf(file, "COUNT %u\n", record.count) > 0, error);
    for (unsigned i = 0; i < record.count; ++i)
        Check_IO(fprintf(file, "%s %d\n", record.entries[i].name, static_cast<int>(record.entries[i].value)) > 0, error);
    Check_IO(fputs("END\n", file) >= 0, error);
    Check_IO(fflush(file) == 0, error);
    Check_IO(fsync(fileno(file)) == 0, error);
    Check_IO(fclose(file) == 0, error);
    if (error == 0) Check_IO(rename(temporary, store.path) == 0, error);
    if (error != 0) remove(temporary);
    store.error = error;
    store.last_write_ok = error == 0;
    if (error == 0) store.record = record;
    return error == 0;
}
inline bool Set(const char *name, int value)
{
    Lock lock;
    Store &store = State();
    char checked_name[NameBytes];
    if (!store.writable) { store.last_write_ok = false; return false; }
    if (!Name(name, checked_name)) { store.error = EINVAL; store.last_write_ok = false; return false; }
    const int index = Find(store.record, checked_name);
    if (index >= 0 && store.record.entries[index].value == value) {
        store.error = 0;
        store.last_write_ok = true;
        return true;
    }
    std::unique_ptr<Record> record(new (std::nothrow) Record(store.record));
    if (!record) { store.error = ENOMEM; store.last_write_ok = false; return false; }
    if (index < 0 && record->count == MaxEntries) { store.error = ENOSPC; store.last_write_ok = false; return false; }
    const unsigned slot = index >= 0 ? static_cast<unsigned>(index) : record->count++;
    // Windows lookup ignores case but enumeration retains the stored spelling.
    if (index < 0) strcpy(record->entries[slot].name, checked_name);
    record->entries[slot].value = static_cast<int32_t>(value);
    return Save(*record);
}
inline bool Delete(const char *name)
{
    Lock lock;
    Store &store = State();
    if (!store.writable) { store.last_write_ok = false; return false; }
    const int index = Find(store.record, name);
    if (index < 0) { store.error = 0; store.last_write_ok = true; return true; }
    std::unique_ptr<Record> record(new (std::nothrow) Record(store.record));
    if (!record) { store.error = ENOMEM; store.last_write_ok = false; return false; }
    record->entries[index] = record->entries[--record->count];
    return Save(*record);
}
inline bool Clear()
{
    Lock lock;
    std::unique_ptr<Record> record(new (std::nothrow) Record);
    if (!record) { State().error = ENOMEM; State().last_write_ok = false; return false; }
    return Save(*record);
}
inline bool Get_Name(unsigned index, char *result, size_t capacity)
{
    Lock lock;
    if (result == NULL || capacity < NameBytes || index >= State().record.count) return false;
    strcpy(result, State().record.entries[index].name);
    return true;
}
struct Status { bool ready; bool last_write_ok; int error; unsigned count; };
inline Status Get_Status()
{
    Lock lock;
    const Store &store = State();
    return {store.writable, store.last_write_ok, store.error, store.record.count};
}
} // namespace RenegadeMissionRanks
