#pragma once
#include <stddef.h>

namespace RenegadeVitaTextEntry {
#if defined(__vita__)
bool Begin(const void *owner, const wchar_t *text, int limit);
bool Take_Result(const void *owner, wchar_t *text, size_t capacity);
void Cancel(const void *owner);
bool Active();
bool Block_Input(bool neutral);
void Shutdown();
#else
inline bool Begin(const void *, const wchar_t *, int) { return false; }
inline bool Take_Result(const void *, wchar_t *, size_t) { return false; }
inline void Cancel(const void *) {}
inline bool Active() { return false; }
inline bool Block_Input(bool) { return false; }
inline void Shutdown() {}
#endif
}
