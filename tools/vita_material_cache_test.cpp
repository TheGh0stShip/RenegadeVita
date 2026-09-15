// Execute production lighting and cache code with observable engine inputs.
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <new>
#include <vector>
#include <chrono>
#include <algorithm>
#include <cstdlib>
bool fail_scratch_allocation = false;
void *operator new[](std::size_t bytes, const std::nothrow_t &) noexcept {
    if (fail_scratch_allocation) return nullptr;
    try { return ::operator new[](bytes); } catch (...) { return nullptr; }
}
struct Vector3 {
    float X, Y, Z;
    Vector3(float x=0, float y=0, float z=0): X(x), Y(y), Z(z) {}
    float Length2() const { return X*X + Y*Y + Z*Z; }
    void Normalize() { float r=1.0f/std::sqrt(Length2()); X*=r; Y*=r; Z*=r; }
    static float Dot_Product(Vector3 a, Vector3 b) { return a.X*b.X+a.Y*b.Y+a.Z*b.Z; }
    Vector3 operator+(Vector3 b) const { return {X+b.X,Y+b.Y,Z+b.Z}; }
    Vector3 &operator+=(Vector3 b) { *this=*this+b; return *this; }
};
struct Matrix3D {
    float m[9] = {0,-2,0, 1,0,0, 0,0,0.5f};
    static void Rotate_Vector(const Matrix3D &a, Vector3 v, Vector3 *o) {
        *o={a.m[0]*v.X+a.m[1]*v.Y+a.m[2]*v.Z,
            a.m[3]*v.X+a.m[4]*v.Y+a.m[5]*v.Z,
            a.m[6]*v.X+a.m[7]*v.Y+a.m[8]*v.Z};
    }
};
struct VertexMaterialClass {
    enum ColorSourceType { MATERIAL, COLOR1, COLOR2 };
    Vector3 diffuse{0.3f,0.7f,1.1f}, ambient{0.2f,0.1f,0.8f}, emissive{-0.1f,0.2f,0};
    float alpha=0.7f; bool lighting=true;
    ColorSourceType ds=MATERIAL, as=COLOR1, es=COLOR2;
    void Get_Diffuse(Vector3 *v) const { *v=diffuse; }
    void Get_Ambient(Vector3 *v) const { *v=ambient; }
    void Get_Emissive(Vector3 *v) const { *v=emissive; }
    float Get_Opacity() const { return alpha; }
    bool Get_Lighting() const { return lighting; }
    ColorSourceType Get_Diffuse_Color_Source() const { return ds; }
    ColorSourceType Get_Ambient_Color_Source() const { return as; }
    ColorSourceType Get_Emissive_Color_Source() const { return es; }
};
struct LightEnvironmentClass {
    int count=4;
    Vector3 directions[5]={{1,2,3},{0,0,0},{-2,4,-1},{2,-3,7},{1,1,1}};
    int Get_Light_Count() const { return count; }
    Vector3 Get_Light_Direction(int i) const { return directions[i]; }
    Vector3 Get_Light_Diffuse(int i) const { return {0.2f*i,0.8f,0.1f}; }
    Vector3 Get_Equivalent_Ambient() const { return {0.3f,0.4f,0.5f}; }
};
struct RenderInfoClass { const LightEnvironmentClass *light_environment; };
struct {
    uint64_t material_light_normalizations=0, material_color_cache_fallback_passes=0;
    uint64_t material_color_cache_bytes=0, material_color_evaluations=0, material_color_cache_hits=0;
} g_statistics;
unsigned g_render_work_cache_mode=2, g_dx8_ambient_color=0xff102030;
#include "material-production.inc"
void equal(Vector3 a, Vector3 b) { assert(a.X==b.X && a.Y==b.Y && a.Z==b.Z); }
void equal(const MaterialVertexColor &a, const MaterialVertexColor &b) {
    equal(a.diffuse,b.diffuse); equal(a.ambient,b.ambient); equal(a.emissive,b.emissive);
    equal(a.final_color,b.final_color); assert(a.alpha==b.alpha);
    assert(a.lighting==b.lighting && a.light_count==b.light_count);
}
int main() {
    fail_scratch_allocation=true;
    assert(!Begin_Material_Color_Pass(17));
    assert(g_material_color_scratch==nullptr && g_material_color_capacity==0);
    fail_scratch_allocation=false;
    constexpr unsigned count=16385;
    std::vector<unsigned> c1(count), c2(count);
    std::vector<Vector3> normals(count);
    for (unsigned i=0;i<count;++i) {
        c1[i]=i*3779; c2[i]=~c1[i]; normals[i]={float(i%7)-3,float(i%11)-5,float(i%13)-6};
    }
    Matrix3D world; LightEnvironmentClass lights; RenderInfoClass info{&lights};
    VertexMaterialClass materials[2]; materials[1].alpha=0.25f;
    uint64_t comparisons=0;
    for (int pass=0;pass<192;++pass) {
        lights.count=pass%6; info.light_environment=pass%7 ? &lights : nullptr;
        materials[0].lighting=pass%2;
        materials[0].ds=static_cast<VertexMaterialClass::ColorSourceType>(pass%3);
        materials[0].as=static_cast<VertexMaterialClass::ColorSourceType>((pass/3)%3);
        materials[0].es=static_cast<VertexMaterialClass::ColorSourceType>((pass/9)%3);
        const unsigned *a=pass%4 ? c1.data() : nullptr, *b=pass%5 ? c2.data() : nullptr;
        const Vector3 *n=pass%8 ? normals.data() : nullptr;
        const unsigned vertices=pass%2 ? count : 17;
        if (pass==100) g_material_color_generation=UINT32_MAX;
        assert(Begin_Material_Color_Pass(vertices));
        MaterialLightDirections directions; Prepare_Material_Light_Directions(info,directions);
        for (unsigned j=0;j<500;++j) {
            unsigned i=(j%2 ? j*8192U : j)%vertices;
            VertexMaterialClass *m=j%11 ? &materials[j%2] : nullptr;
            auto reference=Evaluate_Original_Material_Vertex_Color(m,a,b,i,n,world,info,nullptr);
            equal(reference,Evaluate_Material_Vertex_Color(true,m,a,b,i,n,world,info,directions));
            equal(reference,Evaluate_Material_Vertex_Color(true,m,a,b,i,n,world,info,directions));
            auto submitted=Evaluate_Material_Vertex_Color(true,m,a,b,i,n,world,info,directions,true);
            equal(submitted.final_color,Vector3(1,1,1));
            assert(submitted.alpha==reference.alpha);
            // A passthrough draw must not poison the full-color cache.
            equal(reference,Evaluate_Material_Vertex_Color(true,m,a,b,i,n,world,info,directions));
            comparisons+=2;
        }
    }
    assert(!Begin_Material_Color_Pass(0));
    uint64_t alpha_comparisons=0;
    for (unsigned alpha=0;alpha<256;++alpha) {
        c1[0]=(alpha<<24)|0x00ABCDEFU;
        c2[0]=((255-alpha)<<24)|0x00123456U;
        for (int source=0;source<3;++source) for (unsigned mask=0;mask<4;++mask) {
            materials[0].ds=static_cast<VertexMaterialClass::ColorSourceType>(source);
            for (float opacity : {-0.25f,0.0f,0.3f,1.0f,1.25f}) {
                materials[0].alpha=opacity;
                const unsigned *a=mask&1 ? c1.data() : nullptr;
                const unsigned *b=mask&2 ? c2.data() : nullptr;
                auto reference=Evaluate_Original_Material_Vertex_Color(&materials[0],a,b,0,
                    normals.data(),world,info,nullptr);
                assert(Evaluate_Original_Diffuse_Alpha(&materials[0],a,b,0)==reference.alpha);
                ++alpha_comparisons;
            }
        }
    }
    g_render_work_cache_mode=0; assert(!Begin_Material_Color_Pass(count));
    MaterialLightDirections disabled_directions;
    equal(Evaluate_Original_Material_Vertex_Color(&materials[0],c1.data(),c2.data(),0,
        normals.data(),world,info,nullptr), Evaluate_Material_Vertex_Color(false,
        &materials[0],c1.data(),c2.data(),0,normals.data(),world,info,disabled_directions,true));
    // Fixed CPU fixture: repeated indexed corners, same inputs in both modes.
    lights.count=4; info.light_environment=&lights; materials[0].lighting=true;
    volatile float sink=0;
    for (unsigned mode : {0U,2U}) {
        g_render_work_cache_mode=mode; std::vector<double> timings;
        auto before=g_statistics;
        for (int trial=0;trial<40;++trial) {
            auto start=std::chrono::steady_clock::now();
            bool cached=Begin_Material_Color_Pass(4096);
            MaterialLightDirections directions;
            if (cached) Prepare_Material_Light_Directions(info,directions);
            for (unsigned j=0;j<65536;++j) {
                auto v=Evaluate_Material_Vertex_Color(cached,&materials[0],c1.data(),c2.data(),
                    j%4096,normals.data(),world,info,directions);
                sink+=v.final_color.X;
            }
            timings.push_back(std::chrono::duration<double,std::micro>(
                std::chrono::steady_clock::now()-start).count());
        }
        std::sort(timings.begin(),timings.end());
        std::printf("host fixture mode=%u median/p95/p99/worst_us=%.1f/%.1f/%.1f/%.1f evaluations=%llu normalizations=%llu scratch=%llu\n",
            mode,timings[20],timings[37],timings[39],timings[39],
            (unsigned long long)(g_statistics.material_color_evaluations-before.material_color_evaluations),
            (unsigned long long)(g_statistics.material_light_normalizations-before.material_light_normalizations),
            (unsigned long long)g_statistics.material_color_cache_bytes);
    }
    // Fixed submitted-skin fixture: same 4096 vertices/material/light inputs,
    // indexed unique vertices plus the inherited final attribute. Both modes
    // submit white RGB and the original diffuse alpha. No GPU/FPS inference.
    g_render_work_cache_mode=2;
    materials[0].alpha=0.7f;
    for (bool bypass : {false,true}) {
        std::vector<double> timings;
        auto before=g_statistics;
        auto skips_before=g_material_skin_rgb_skips;
        for (int trial=0;trial<80;++trial) {
            auto start=std::chrono::steady_clock::now();
            bool cached=Begin_Material_Color_Pass(4096);
            MaterialLightDirections directions; Prepare_Material_Light_Directions(info,directions);
            for (unsigned j=0;j<4097;++j) {
                auto v=Evaluate_Material_Vertex_Color(cached,&materials[0],c1.data(),c2.data(),
                    j%4096,normals.data(),world,info,directions,bypass);
                sink+=Clamp01(v.alpha);
            }
            timings.push_back(std::chrono::duration<double,std::micro>(
                std::chrono::steady_clock::now()-start).count());
        }
        std::sort(timings.begin(),timings.end());
        std::printf("host submitted-skin bypass=%d median/p95/p99/worst_us=%.1f/%.1f/%.1f/%.1f evaluations=%llu rgb_skips=%llu scratch=%llu\n",
            bypass,timings[40],timings[75],timings[79],timings[79],
            (unsigned long long)(g_statistics.material_color_evaluations-before.material_color_evaluations),
            (unsigned long long)(g_material_skin_rgb_skips-skips_before),
            (unsigned long long)g_statistics.material_color_cache_bytes);
    }
    std::printf("submitted-skin alpha equivalence PASS comparisons=%llu\n",(unsigned long long)alpha_comparisons);
    delete[] g_material_color_scratch;
    std::printf("material equivalence PASS comparisons=%llu sink=%.1f\n",(unsigned long long)comparisons,sink);
}
