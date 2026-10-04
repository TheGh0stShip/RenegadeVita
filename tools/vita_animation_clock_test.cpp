#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>

struct WW3D {
    static uint32_t time;
    static uint32_t Get_Sync_Time() { return time; }
};
uint32_t WW3D::time = 0;
struct Motion {
    float Get_Frame_Rate() const { return 30.f; }
    int Get_Num_Frames() const { return 61; }
};
struct Animatable3DObjClass {
    enum { SINGLE_ANIM, ANIM_MODE_MANUAL, ANIM_MODE_ONCE, ANIM_MODE_LOOP };
    int CurMotionMode = SINGLE_ANIM;
    struct State {
        float Frame = 7.f;
        int32_t LastSyncTime = 0;
        int AnimMode = ANIM_MODE_LOOP;
        struct Motion *Motion;
    } ModeAnim;
    float Compute_Current_Frame() const;
};
#include "production.inc"

int main() {
    Motion motion;
    Animatable3DObjClass old_clock, original_clock;
    old_clock.ModeAnim.Motion = original_clock.ModeAnim.Motion = &motion;
    uint32_t wall = 0, engine = 0;
    unsigned backward = 0, resets = 0;
    const uint32_t durations[] = {40, 10, 18, 45, 12, 240, 8, 16};
    float expected = 7.f;
    for (unsigned i = 0; i < 4096; ++i) {
        const uint32_t elapsed = durations[i % 8];
        const uint32_t ticks = std::min(elapsed, uint32_t(200)); // Original five-FPS clamp.
        wall += elapsed;
        const uint32_t old_time = wall + ticks; // Superseded native wall overwrite + original advance.
        if (old_time < uint32_t(old_clock.ModeAnim.LastSyncTime)) ++backward;
        WW3D::time = old_time;
        const float old_frame = old_clock.Compute_Current_Frame();
        if (old_frame == 0.f && old_clock.ModeAnim.Frame != 0.f) ++resets;
        old_clock.ModeAnim.Frame = old_frame;
        old_clock.ModeAnim.LastSyncTime = int32_t(old_time);
        engine += ticks;
        WW3D::time = engine;
        const float frame = original_clock.Compute_Current_Frame();
        expected += 30.f * float(ticks) * 0.001f;
        if (expected >= 60.f) expected -= 60.f;
        assert(std::fabs(frame - expected) < 0.0001f);
        original_clock.ModeAnim.Frame = frame;
        original_clock.ModeAnim.LastSyncTime = int32_t(engine);
        assert(original_clock.Compute_Current_Frame() == frame); // Original paused/zero-tick behavior.
    }
    assert(backward > 0 && resets > 0);
    // Preserve original unsigned millisecond rollover with an explicit ILP32 token.
    original_clock.ModeAnim.LastSyncTime = -16;
    original_clock.ModeAnim.Frame = 7.f;
    WW3D::time = 16;
    assert(std::fabs(original_clock.Compute_Current_Frame() - 7.96f) < 0.0001f);
    std::printf("original animation clock PASS frames=4096 old_backward=%u old_resets=%u pause/wrap=PASS\n", backward, resets);
}
