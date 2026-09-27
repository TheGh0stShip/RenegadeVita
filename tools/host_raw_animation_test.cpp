#include <cmath>
#include <cstdio>
#include <cstdlib>
#include "always.h"
#include "hanim.h"
#include "lookuptable.h"

// Curve presets are outside this fixture; WWMath still initializes its trig tables.
void LookupTableMgrClass::Init() {}

// Populate synthetic channels without retail assets; execute original samplers.
#define private public
#include "hrawanim.h"
#include "motchan.h"
#undef private
#ifndef RAW_ANIMATION_SOURCE
#define RAW_ANIMATION_SOURCE "../staging/ww3d2/hrawanim.cpp"
#endif
#include RAW_ANIMATION_SOURCE

static void Check(bool condition)
{
    if (!condition) {
        std::fputs("Raw animation output mismatch\n", stderr);
        std::exit(1);
    }
}

int main()
{
    WWMath::Init();
    HRawAnimClass animation;
    animation.NumFrames = 4;
    animation.NumNodes = 1;
    animation.NodeMotion = new NodeMotionStruct[1];
    MotionChannelClass *channel = new MotionChannelClass;
    channel->Type = ANIM_CHANNEL_X;
    channel->VectorLen = 1;
    channel->FirstFrame = 0;
    channel->LastFrame = 3;
    channel->Data = new float[4]{0.0f, 8.0f, -4.0f, 16.0f};
    animation.NodeMotion[0].X = channel;
    MotionChannelClass *rotation_channel = new MotionChannelClass;
    rotation_channel->Type = ANIM_CHANNEL_Q;
    rotation_channel->VectorLen = 4;
    rotation_channel->FirstFrame = 0;
    rotation_channel->LastFrame = 3;
    const float half = std::sqrt(0.5f);
    rotation_channel->Data = new float[16]{
        0, 0, 0, 1, 0, 0, half, half,
        0, 0, 0, 1, 0, 0, -half, half};
    animation.NodeMotion[0].Q = rotation_channel;
    unsigned samples = 0;
    for (int key = 0; key < 4; ++key) {
        for (int fraction = 0; fraction < 8; ++fraction) {
            const float ratio = fraction / 8.0f;
            const float frame = key + ratio;
            const float expected = channel->Data[key] * (1.0f - ratio) +
                channel->Data[(key + 1) % 4] * ratio;
            Vector3 translation;
            Quaternion rotation;
            Matrix3D transform;
            animation.Get_Translation(translation, 0, frame);
            animation.Get_Orientation(rotation, 0, frame);
            animation.Get_Transform(transform, 0, frame);
            const float *a = rotation_channel->Data + key * 4;
            const float *b = rotation_channel->Data + ((key + 1) % 4) * 4;
            Quaternion expected_rotation;
            Fast_Slerp(expected_rotation, Quaternion(a[0], a[1], a[2], a[3]),
                Quaternion(b[0], b[1], b[2], b[3]), ratio);
            Check(std::fabs(translation.X - expected) < 0.0001f);
            Check(translation.Y == 0.0f && translation.Z == 0.0f);
            Check(std::fabs(transform.Get_Translation().X - expected) < 0.0001f);
            Check(std::fabs(rotation.Z - expected_rotation.Z) < 0.0001f);
            Check(std::fabs(rotation.W - expected_rotation.W) < 0.0001f);
            const Matrix3D expected_transform = Build_Matrix3D(expected_rotation);
            for (int row = 0; row < 3; ++row)
                for (int column = 0; column < 3; ++column)
                    Check(std::fabs(transform[row][column] -
                        expected_transform[row][column]) < 0.0001f);
            ++samples;
        }
    }
    printf("Original raw animation output PASS samples=%u including wrap\n", samples);
}
