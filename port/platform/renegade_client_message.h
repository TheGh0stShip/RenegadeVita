#pragma once

#include <stddef.h>
#include <string.h>

// Pre-join diagnostics only. Suppress key/hash-shaped spans and control bytes;
// ordinary multiplayer chat is not captured by this boundary.
inline void Renegade_Redact_Admission_Message(char *text)
{
    const size_t length = strlen(text);
    for (size_t i = 0; i < length;) {
        const size_t begin = i;
        while (i < length && ((text[i] >= '0' && text[i] <= '9') ||
            (text[i] >= 'a' && text[i] <= 'f') || (text[i] >= 'A' && text[i] <= 'F') ||
            text[i] == '-')) ++i;
        if (i - begin >= 22) memset(text + begin, '*', i - begin);
        if (i == begin) ++i;
    }
    for (size_t i = 0; i < length; ++i)
        if (static_cast<unsigned char>(text[i]) < 32 || text[i] == 127) text[i] = ' ';
}
