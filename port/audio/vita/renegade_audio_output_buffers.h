#ifndef RENEGADE_AUDIO_OUTPUT_BUFFERS_H
#define RENEGADE_AUDIO_OUTPUT_BUFFERS_H

#include <array>
#include <cstddef>
#include <cstdint>

// Native output can retain the newly submitted pointer while the previous
// buffer finishes. Keep each submitted block intact until the next submit.
// The owner must drain its port before destroying this storage.
template <std::size_t Samples> struct RenegadeAudioOutputBuffers {
    static_assert((Samples * sizeof(int16_t)) % 64 == 0, "Vita audio block alignment");
    alignas(64) std::array<int16_t, Samples> blocks[2] = {};
    unsigned next = 0;
    std::array<int16_t, Samples> &Next() {
        auto &block = blocks[next];
        next ^= 1U;
        return block;
    }
};

#endif
