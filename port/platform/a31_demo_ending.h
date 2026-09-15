#ifndef A31_DEMO_ENDING_H
#define A31_DEMO_ENDING_H

#include <stdint.h>

// Presentation policy only. Original Combat owns mission success.
namespace A31Demo {
static const char ThankYou[] =
    "Thank you for playing the Renegade Vita Demo! There is still more work "
    "to be done before this is a complete title. Stay tuned!";
static const char Credits[] =
    "RENEGADE VITA DEMO\n\n"
    "Native port: Renegade Vita project\n"
    "Original game: Westwood Studios / Electronic Arts\n"
    "Native platform: VitaSDK contributors\n"
    "Graphics: vitaGL / vitaShaRK / SceShaccCgExt\n"
    "Movie decoding: FFmpeg contributors\n"
    "Fonts: FreeType contributors\n"
    "Libraries: zlib / libpng / bzip2 / minizip\n"
    "Platform support: taiHEN / math-neon\n\n"
    "With thanks to the PlayStation Vita homebrew community.\n"
    "Original authors and license notices remain in the source distribution.";

inline bool IsTutorialMap(const char *name)
{
    const char *expected = "m00_tutorial.mix";
    if (!name) return false;
    for (; *name && *expected; ++name, ++expected) {
        const char lower = *name >= 'A' && *name <= 'Z' ? *name + ('a' - 'A') : *name;
        if (lower != *expected) return false;
    }
    return *name == '\0' && *expected == '\0';
}

class Ending {
public:
    enum Phase { Playing, Fade, Thanks, CreditScene, Done };
    Ending() : Started(false), StartUs(0), Current(Playing), Opacity(0.0f) {}
    void Start(uint64_t now) {
        if (Started) return;
        Started = true;
        StartUs = now;
        Current = Fade;
    }
    void Update(uint64_t now) {
        if (!Started) return;
        const uint64_t elapsed = now >= StartUs ? now - StartUs : 0;
        if (elapsed < 3000000ULL) {
            Current = Fade;
            const float t = static_cast<float>(elapsed) / 3000000.0f;
            Opacity = t * t * (3.0f - 2.0f * t);
        } else {
            Opacity = 1.0f;
            Current = elapsed < 13000000ULL ? Thanks :
                (elapsed < 33000000ULL ? CreditScene : Done);
        }
    }
    bool Active() const { return Started; }
    Phase GetPhase() const { return Current; }
    float Alpha() const { return Opacity; }
private:
    bool Started;
    uint64_t StartUs;
    Phase Current;
    float Opacity;
};
}

#endif
