#pragma once

#include "bitstream.h"
#include <string.h>

// TT b9000 connection extension, independently verified against the pinned PC
// serializer. This wire version is diagnostic, not a gameplay capability claim.
inline bool Renegade_Write_TT_Client_Greeting(BitStreamClass &packet,
    const char *serial_hash, const char *hardware_identifier)
{
    if (!serial_hash || strnlen(serial_hash, 33) != 32 || !hardware_identifier)
        return false;
    for (unsigned i = 0; i < 32; ++i)
        if (!(serial_hash[i] >= '0' && serial_hash[i] <= '9') &&
            !(serial_hash[i] >= 'a' && serial_hash[i] <= 'f')) return false;
    size_t hardware_length = 0;
    while (hardware_length < 65 && hardware_identifier[hardware_length]) ++hardware_length;
    if (hardware_length > 64) return false;
    for (size_t i = 0; i < hardware_length; ++i)
        if (static_cast<unsigned char>(hardware_identifier[i]) < 32 ||
            static_cast<unsigned char>(hardware_identifier[i]) > 126) return false;
    const unsigned required_bits = (12 + 2 + 32 + 2 + hardware_length) * 8;
    const unsigned position = packet.Get_Bit_Write_Position();
    const unsigned capacity = packet.Get_Buffer_Size() * 8;
    if (position > capacity || required_bits > capacity - position) return false;
    packet.Add(static_cast<ULONG>(0x21545421u));
    packet.Add(static_cast<ULONG>(0x4099999au)); // IEEE-754 4.8, fixed wire bits.
    packet.Add_Terminated_String(serial_hash);
    packet.Add(static_cast<ULONG>(9000));
    packet.Add_Terminated_String(hardware_identifier, true);
    return true;
}
