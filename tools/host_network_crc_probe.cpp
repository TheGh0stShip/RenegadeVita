#include "crc.h"
#include <stdint.h>

extern "C" uint32_t network_crc(const unsigned char *data, int length,
    uint32_t initial, int split)
{
    CRCEngine engine(static_cast<int32_t>(initial));
    if (split < 0) {
        for (int index = 0; index < length; ++index) engine(static_cast<char>(data[index]));
    } else {
        engine(data, split);
        engine(data + split, length - split);
    }
    return static_cast<uint32_t>(engine());
}
