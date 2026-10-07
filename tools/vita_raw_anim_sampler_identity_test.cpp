// Bit-identity fixture for the raw-animation sampler and HTree pose builds.
// tools/test_vita_raw_anim_sampler_identity.py compiles it twice: against the
// staged sources and against private copies with the a36 sampler patches
// reversed.  Each build writes every sampled float/bool as raw bytes; the two
// streams must match byte for byte.
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <limits>
#include "always.h"
#include "hanim.h"
#include "lookuptable.h"

// Curve presets are outside this fixture; WWMath still initializes its trig tables.
void LookupTableMgrClass::Init() {}

#define private public
#define protected public
#include "hrawanim.h"
#include "motchan.h"
#include "htree.h"
#include "pivot.h"
#undef protected
#undef private
#ifndef RAW_ANIMATION_SOURCE
#define RAW_ANIMATION_SOURCE "../staging/ww3d2/hrawanim.cpp"
#endif
#include RAW_ANIMATION_SOURCE

static uint64_t g_state = 0x9E3779B97F4A7C15ull;
static uint32_t Next()
{
    g_state ^= g_state << 13;
    g_state ^= g_state >> 7;
    g_state ^= g_state << 17;
    return static_cast<uint32_t>(g_state >> 16);
}
static float Unit() { return (Next() & 0xFFFFFF) / 16777216.0f; }
static float Range(float lo, float hi) { return lo + (hi - lo) * Unit(); }
static int Pick(int n) { return static_cast<int>(Next() % static_cast<uint32_t>(n)); }

static FILE *g_out;
static unsigned long g_values;
static void Emit(const void *data, size_t size)
{
    std::fwrite(data, 1, size, g_out);
    g_values += size;
}
static void Emit(const Matrix3D &m) { Emit(&m, sizeof(m)); }
static void Emit(const Quaternion &q) { Emit(&q, sizeof(q)); }
static void Emit(const Vector3 &v) { Emit(&v, sizeof(v)); }
static void Emit(bool b) { const unsigned char c = b ? 1 : 0; Emit(&c, 1); }

static float Special_Float()
{
    static const float values[] = {
        0.0f, -0.0f, 1.0f, -1.0f, 1.0e-40f, -1.0e-40f, 1.0e30f, -1.0e30f,
        3.0e38f, std::numeric_limits<float>::infinity(),
        -std::numeric_limits<float>::infinity(),
        std::numeric_limits<float>::quiet_NaN()};
    return values[Pick(sizeof(values) / sizeof(values[0]))];
}

static void Random_Quaternion(float *q)
{
    float n = 0.0f;
    do {
        for (int i = 0; i < 4; ++i) q[i] = Range(-1.0f, 1.0f);
        n = q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3];
    } while (n < 0.01f);
    const float inv = 1.0f / std::sqrt(n);
    for (int i = 0; i < 4; ++i) q[i] *= inv;
}

static MotionChannelClass *Make_Channel(int type, int frames)
{
    MotionChannelClass *channel = new MotionChannelClass;
    channel->Type = type;
    channel->VectorLen = (type == ANIM_CHANNEL_Q) ? 4 : 1;
    int first = Pick(frames);
    int last = first + Pick(frames - first);
    if (Pick(8) == 0) last = frames + Pick(3);   // stored range beyond NumFrames
    channel->FirstFrame = first;
    channel->LastFrame = last;
    const int count = last - first + 1;
    channel->Data = new float[count * channel->VectorLen];
    for (int key = 0; key < count; ++key) {
        float *value = channel->Data + key * channel->VectorLen;
        if (type == ANIM_CHANNEL_Q) {
            const int mode = key == 0 ? 0 : Pick(6);
            if (mode == 0 || mode == 1) {
                Random_Quaternion(value);                      // far apart
            } else if (mode == 2) {
                std::memcpy(value, value - 4, 4 * sizeof(float));   // identical key
            } else if (mode == 3) {
                for (int i = 0; i < 4; ++i) value[i] = -value[i - 4];   // opposite hemisphere
            } else {
                float n = 0.0f;                                // near key: acos path
                for (int i = 0; i < 4; ++i) {
                    value[i] = value[i - 4] + Range(-0.05f, 0.05f);
                    n += value[i] * value[i];
                }
                const float inv = 1.0f / std::sqrt(n);
                for (int i = 0; i < 4; ++i) value[i] *= inv;
            }
        } else {
            value[0] = Pick(32) == 0 ? Special_Float() : Range(-20.0f, 20.0f);
        }
    }
    return channel;
}

static BitChannelClass *Make_Bits(int frames)
{
    BitChannelClass *channel = new BitChannelClass;
    channel->Type = BIT_CHANNEL_VIS;
    channel->DefaultVal = Pick(2);
    channel->FirstFrame = Pick(frames);
    channel->LastFrame = channel->FirstFrame + Pick(frames - channel->FirstFrame);
    const int bytes = (channel->LastFrame - channel->FirstFrame + 1 + 7) / 8;
    channel->Bits = new uint8[bytes];
    for (int i = 0; i < bytes; ++i) channel->Bits[i] = static_cast<uint8>(Next());
    return channel;
}

static HRawAnimClass *Make_Animation(int nodes)
{
    HRawAnimClass *animation = new HRawAnimClass;
    animation->NumFrames = 1 + Pick(40);
    animation->NumNodes = nodes;
    animation->NodeMotion = new NodeMotionStruct[nodes];
    for (int node = 0; node < nodes; ++node) {
        NodeMotionStruct &motion = animation->NodeMotion[node];
        if (Pick(2)) motion.X = Make_Channel(ANIM_CHANNEL_X, animation->NumFrames);
        if (Pick(2)) motion.Y = Make_Channel(ANIM_CHANNEL_Y, animation->NumFrames);
        if (Pick(2)) motion.Z = Make_Channel(ANIM_CHANNEL_Z, animation->NumFrames);
        if (Pick(5)) motion.Q = Make_Channel(ANIM_CHANNEL_Q, animation->NumFrames);
        if (Pick(5) == 0) motion.Vis = Make_Bits(animation->NumFrames);
    }
    return animation;
}

static float Random_Frame(int frames)
{
    switch (Pick(12)) {
    case 0: return static_cast<float>(Pick(frames));                 // exact key
    case 1: return frames - 1 + Unit();                              // wraps to key 0
    case 2: return -Range(0.0f, 3.0f);                               // negative
    case 3: return Pick(2) ? -0.0f : 0.0f;
    case 4: return frames + Range(0.0f, 1000.0f);                    // beyond the anim
    case 5: {
        // Conversion edges.  NaN/inf frames are excluded: the original
        // Fast_Acos indexes its table with NaN once a NaN quaternion is blended.
        static const float edges[] = {2.5e9f, 2147483648.0f, 2147483520.0f,
            -2147483648.0f, -3.0e9f, 1.0e30f, -1.0e30f, 1.0e-40f, -1.0e-40f,
            8388607.5f, 16777216.0f};
        return edges[Pick(sizeof(edges) / sizeof(edges[0]))];
    }
    default: return Range(0.0f, static_cast<float>(frames));
    }
}

static HTreeClass *Make_Tree(int pivots)
{
    HTreeClass *tree = new HTreeClass;
    tree->NumPivots = pivots;
    tree->Pivot = new PivotClass[pivots];
    tree->ScaleFactor = Pick(4) ? 1.0f : Range(0.5f, 2.0f);
    for (int i = 0; i < pivots; ++i) {
        PivotClass &pivot = tree->Pivot[i];
        pivot.Index = i;
        pivot.Parent = i == 0 ? NULL : &tree->Pivot[Pick(i)];
        float q[4];
        Random_Quaternion(q);
        pivot.BaseTransform = ::Build_Matrix3D(Quaternion(q[0], q[1], q[2], q[3]));
        pivot.BaseTransform.Set_Translation(Vector3(Range(-2, 2), Range(-2, 2), Range(-2, 2)));
    }
    return tree;
}

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    g_out = std::fopen(argv[1], "wb");
    if (g_out == NULL) return 2;
    WWMath::Init();

    // Build_Matrix3D over random, near-axis and special-valued quaternions.
    for (int i = 0; i < 100000; ++i) {
        float q[4];
        Random_Quaternion(q);
        for (int c = 0; c < 4; ++c) {
            const int mode = Pick(16);
            if (mode == 0) q[c] = Special_Float();
            else if (mode == 1) q[c] *= 1.0e-20f;
            else if (mode == 2) q[c] = Range(-1.0e19f, 1.0e19f);
        }
        Emit(::Build_Matrix3D(Quaternion(q[0], q[1], q[2], q[3])));
    }

    unsigned long samples = 0;
    for (int round = 0; round < 120; ++round) {
        const int pivots = 2 + Pick(30);
        HTreeClass *tree = Make_Tree(pivots);
        HRawAnimClass *a = Make_Animation(1 + Pick(pivots + 2));
        HRawAnimClass *b = Make_Animation(1 + Pick(pivots + 2));
        Matrix3D root(true);
        for (int step = 0; step < 200; ++step) {
            const float fa = Random_Frame(a->NumFrames);
            const float fb = Random_Frame(b->NumFrames);
            const int node = Pick(a->NumNodes);
            Vector3 translation;
            Quaternion orientation;
            Matrix3D transform;
            a->Get_Translation(translation, node, fa);
            a->Get_Orientation(orientation, node, fa);
            a->Get_Transform(transform, node, fa);
            Emit(translation);
            Emit(orientation);
            Emit(transform);
            Emit(a->Get_Visibility(node, fa));

            root.Set_Translation(Vector3(Range(-50, 50), Range(-50, 50), Range(-5, 5)));
            tree->Anim_Update(root, a, fa);
            for (int p = 0; p < pivots; ++p) {
                Emit(tree->Get_Transform(p));
                Emit(tree->Get_Visibility(p));
            }
            const float percentage = Pick(4) == 0 ? static_cast<float>(Pick(2)) : Unit();
            tree->Blend_Update(root, a, fa, b, fb, percentage);
            for (int p = 0; p < pivots; ++p) {
                Emit(tree->Get_Transform(p));
                Emit(tree->Get_Visibility(p));
            }
            ++samples;
        }
        a->Release_Ref();
        b->Release_Ref();
        delete tree;
    }
    std::fclose(g_out);
    std::printf("PASS samples=%lu bytes=%lu\n", samples, g_values);
    return 0;
}
