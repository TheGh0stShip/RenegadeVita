// Original generator against fixed 32-bit two's-complement arithmetic vectors.
// These vectors establish arithmetic semantics, not retail gameplay acceptance.
#include "random.h"
#include <cstdint>
#include <cstdio>

int main()
{
    static_assert(sizeof(int) == 4, "original generator requires 32-bit int");
    const uint32_t seeds[][2] = {
        {0U, 0U}, {1234U, 0U}, {0xffffffffU, 0x7fffffffU},
        {0x80000000U, 0xfffffffcU}
    };
    // Evaluated with unbounded integer arithmetic, explicit modulo 2^32 and
    // arithmetic right shift at every original signed operation boundary.
    const uint32_t expected[][8] = {
        {0xad2eaa18U, 0x667051bbU, 0xbeb8385dU, 0x1293a6d6U, 0x9a1c341dU, 0x4868b99cU, 0x803d17d0U, 0x569b65afU},
        {0x29b13eecU, 0xd3f8c8d3U, 0x451aa367U, 0x62564db1U, 0x77b9ee17U, 0x483ba93cU, 0x4d7f3554U, 0x9ccd4b30U},
        {0xd3bd5cffU, 0x6a06e304U, 0x1853cc8bU, 0x987be73dU, 0x9b66a9a1U, 0x4af55d2dU, 0xe5e06792U, 0x2e0ab316U},
        {0x2ae0c7a9U, 0x38d1d572U, 0x605e0336U, 0x481df71aU, 0x0f0b2d83U, 0x903379e4U, 0x16a48576U, 0x61dffaa5U}
    };
    for (unsigned seed = 0; seed < 4; ++seed) {
        Random3Class generator(seeds[seed][0], seeds[seed][1]);
        for (unsigned sample = 0; sample < 8; ++sample) {
            if (static_cast<uint32_t>(generator()) != expected[seed][sample]) {
                std::fprintf(stderr, "original random wrap mismatch: seed=%u sample=%u\n", seed, sample);
                return 1;
            }
        }
    }
    std::puts("original Random3 32-bit wrap vectors PASS: 32 samples, signed index rollover");
    return 0;
}
