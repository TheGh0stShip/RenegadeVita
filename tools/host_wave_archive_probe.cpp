// Host-only framed audit. Input lengths are explicit little-endian uint32;
// no decoded samples or retail bytes are written to output.
#include "renegade_wave_decoder.h"
#include <cstdio>
#include <cstdint>
#include <vector>

static_assert(sizeof(uint32_t) == 4, "framed length width");

int main()
{
    for (;;) {
        uint8_t header[4];
        const size_t count = std::fread(header, 1, 4, stdin);
        if (count == 0 && std::feof(stdin)) return 0;
        if (count != 4) return 2;
        const uint32_t bytes = uint32_t(header[0]) | (uint32_t(header[1]) << 8) |
            (uint32_t(header[2]) << 16) | (uint32_t(header[3]) << 24);
        if (bytes > 64U * 1024U * 1024U) return 3;
        std::vector<uint8_t> data(bytes);
        if (std::fread(data.data(), 1, bytes, stdin) != bytes) return 4;
        RenegadeVitaAudio::WaveInfo info;
        RenegadeVitaAudio::DecodedWave decoded;
        const char *error = nullptr;
        const bool passed = RenegadeVitaAudio::Decode_Wave_With_Info(
            data.data(), data.size(), &decoded, &info, &error);
        std::printf("%u\t%zu\t%s\n", passed ? 1U : 0U,
            passed ? decoded.Frame_Count() : 0U, error ? error : "none");
        if (std::fflush(stdout) != 0) return 5;
    }
}
