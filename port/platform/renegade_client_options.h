#pragma once

#include "bitstream.h"
#include <stdint.h>

struct RenegadeClientOptionsLayout {
    uint32_t MapCRC = 0, ModCRC = 0;
    bool ModernFlag = false;
};

// Validate without mutating the packet or game. Original tier importers remain
// the owners of settings; modern TT only changes the final event suffix.
inline bool Renegade_Inspect_Client_Options(const BitStreamClass &packet,
    bool modern, RenegadeClientOptionsLayout &result)
{
    result = {};
    BitStreamClass scan;
    scan = packet;
    const unsigned end = scan.Get_Bit_Write_Position();
    if (end > scan.Get_Buffer_Size() * 8) return false;
    auto read = [&](unsigned count, uint32_t &value) {
        const unsigned start = scan.Get_Bit_Read_Position();
        if (start > end || count > end - start) return false;
        ULONG word = 0;
        scan.Get_Bits(word, count);
        value = word;
        return true;
    };
    uint32_t ignored = 0;
    auto wide = [&](unsigned capacity, bool empty) {
        uint32_t length = 0, value = 0;
        if (!read(16, length) || length >= capacity || (!empty && !length)) return false;
        for (uint32_t i = 0; i < length; ++i)
            if (!read(16, value) || !value) return false;
        return true;
    };
    if (!read(32, ignored) || !wide(256, true) || !wide(256, true)) return false;
    for (unsigned i = 0; i < 6; ++i) if (!read(32, ignored)) return false;
    for (unsigned i = 0; i < 5; ++i) if (!read(1, ignored)) return false;
    RenegadeClientOptionsLayout pending;
    if (!read(32, pending.MapCRC) || !read(32, pending.ModCRC)) return false;
    for (unsigned i = 0; i < 4; ++i) if (!read(32, ignored)) return false;
    for (unsigned i = 0; i < 7; ++i) if (!read(1, ignored)) return false;
    if (!wide(100, true) || !read(1, ignored) || !read(1, ignored) ||
        !read(32, ignored) || !read(32, ignored) || !read(32, ignored)) return false;
    if (modern) {
        if (!read(1, ignored)) return false;
        pending.ModernFlag = ignored != 0;
    } else {
        uint32_t mod = 0, map = 0;
        if (!read(32, mod) || !read(32, map) ||
            mod != pending.ModCRC || map != pending.MapCRC) return false;
    }
    if (!scan.Is_Flushed()) return false;
    result = pending;
    return true;
}
