#pragma once

#include "bitstream.h"
#include <stdint.h>

// Observed TT b9000 accept extension, not a claim of client TT capabilities.
// Owned by one cConnection; never retained across disconnects or auto-fetched.
struct RenegadeTTServerInfo {
    bool Present = false;
    uint32_t VersionBits = 0;
    uint32_t Revision = 0;
    char Repository[384] = {};
};

inline bool Renegade_Read_TT_Server_Info(BitStreamClass &packet, RenegadeTTServerInfo &result)
{
    result = RenegadeTTServerInfo();
    const unsigned start = packet.Get_Bit_Read_Position();
    const unsigned end = packet.Get_Bit_Write_Position();
    if (start > end || end > packet.Get_Buffer_Size() * 8U) return false;
    if (start == end) return true; // Original retail server, no TT extension.
    auto read = [&](unsigned count, uint32_t &value) {
        if (packet.Get_Bit_Read_Position() > end ||
            count > end - packet.Get_Bit_Read_Position()) return false;
        ULONG word = 0;
        packet.Get_Bits(word, count);
        value = static_cast<uint32_t>(word);
        return true;
    };
    uint32_t marker = 0, length = 0;
    RenegadeTTServerInfo pending;
    if (!read(32, marker) || marker != 0x21545421U ||
        !read(32, pending.VersionBits) || pending.VersionBits != 0x4099999aU ||
        !read(16, length) || length >= sizeof(pending.Repository)) return false;
    for (uint32_t index = 0; index < length; ++index) {
        uint32_t value = 0;
        if (!read(8, value) || value < 33 || value > 126 || value == '\\' || value == '@') return false;
        pending.Repository[index] = static_cast<char>(value);
    }
    if (length && strncmp(pending.Repository, "https://", 8) != 0 &&
        strncmp(pending.Repository, "http://", 7) != 0) return false;
    if (!read(32, pending.Revision) || !packet.Is_Flushed()) return false;
    pending.Present = true;
    result = pending;
    return true;
}
