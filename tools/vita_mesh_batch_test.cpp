#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <vector>
#include "ww3d_vita_indexed_mesh_batch.h"
#define __vita__ 1
struct Vector2 { float X,Y; };
struct Vector3 { float X,Y,Z; Vector3(float x=0,float y=0,float z=0):X(x),Y(y),Z(z){} };
struct Matrix3D { float offset; };
struct RenderInfoClass {};
struct MaterialLightDirections {};
struct Name { const char *Peek_Buffer() const { return "fixture"; } };
struct VertexMaterialClass { enum { COLOR1=1, COLOR2=2 }; unsigned id; };
struct MeshMatDescClass { enum { MAX_TEX_STAGES=2 }; };
struct OriginalTextureCoordinateState { unsigned texcoord_index=0,texture_transform_flags=0; };
enum { GL_TEXTURE0=0, GL_TEXTURE1=1, GL_TRIANGLES=4, D3DTSS_TCI_PASSTHRU=0 };
struct ShaderClass {
    enum { TEXTURING_ENABLE=1 };
    unsigned bits;
    unsigned Get_Bits() const { return bits; }
    bool Uses_Post_Detail_Texture() const { return bits&2; }
    unsigned Get_Texturing() const { return bits&1; }
    int Get_Post_Detail_Color_Func() const { return 0; }
    int Get_Post_Detail_Alpha_Func() const { return 0; }
};
using TriIndex=std::array<uint16_t,3>;
using Attributes=std::array<float,14>;
using GLubyte=uint8_t;
using State=std::array<unsigned,4>;
struct Recorded {
    Attributes attributes; State state;
    bool operator==(const Recorded &r) const { return attributes==r.attributes && state==r.state; }
};
static Attributes current{};
static State state{};
static std::vector<Attributes> emitted;
static std::vector<Recorded> recorded;
static bool capture=true,open=false;
static uint64_t calls=0,draws=0;
struct TextureClass {
    unsigned id;
    Name Get_Texture_Name() const { return {}; }
    void Apply_For_Platform_Boundary(unsigned stage) { assert(!open); state[stage]=id; }
};
static TextureClass textures[3]={{1},{2},{3}};
static VertexMaterialClass materials[3]={{1},{2},{3}};
struct MeshModelClass {
    std::vector<Vector2> uv[2];
    std::vector<unsigned> colors;
    unsigned variant=0,group=37;
    const Vector2 *Get_UV_Array(int pass,int stage) const {
        return variant==2 && stage==(pass%2) ? nullptr : uv[stage].data();
    }
    const unsigned *Get_DCG_Array(int) const { return colors.data(); }
    const unsigned *Get_Color_Array(int,bool) const { return colors.data(); }
    unsigned Get_DCG_Source(int) const { return VertexMaterialClass::COLOR1; }
    TextureClass *Peek_Texture(int triangle,int pass,int stage) const {
        if(variant==0 || (variant==3 && stage==1)) return nullptr;
        return &textures[(triangle/group+pass+stage)%3];
    }
    VertexMaterialClass *Peek_Material(int vertex,int pass) const {
        return &materials[(variant==4 ? vertex : pass)%3];
    }
    ShaderClass Get_Shader(int triangle,int pass) const {
        return {unsigned((triangle/group+pass)%4)};
    }
};
struct MeshClass {
    Name name;
    const char *Get_Name() const { return "fixture"; }
    const unsigned *Get_User_Lighting_Array(bool) const { return nullptr; }
};
static unsigned g_render_work_cache_mode=0;
static VitaIndexedMeshBatch g_indexed_mesh_batch;
static uint64_t g_mesh_expanded_corners=0,g_mesh_unique_vertices=0,g_mesh_indexed_batches=0;
struct MeshBoundaryTiming {
    uint64_t mesh_total_us=0,mesh_sampled_us=0,mesh_max_us=0;
    uint64_t draw_end_total_us=0,draw_end_sampled_us=0,draw_end_max_us=0;
    uint32_t mesh_count=0,mesh_sample_count=0,draw_end_count=0,draw_end_sample_count=0;
    char slowest_mesh[64]={};
};
static MeshBoundaryTiming g_mesh_boundary_timing;
enum { MESH_BOUNDARY_TIMING_SAMPLE_STRIDE=16U };
static uint32_t g_draw_end_timing_sequence=0;
static uint64_t fake_process_time_us=0;
uint64_t sceKernelGetProcessTimeWide() { return ++fake_process_time_us; }
static bool g_logged_first_user_lighting=true,g_logged_first_skin_passthrough_texture_v_preserved=true;
static bool g_logged_first_stage1_mesh=true,g_logged_first_skin_texture_color=true,g_logged_first_material_lighting=true;
template<class... Args> void Vita_Append_A22_Runtime_Breadcrumb(Args...) {}
bool Is_Loading_Screen_Diagnostic_Name(const char*) { return false; }
bool Begin_Material_Color_Pass(int) { return false; }
void Prepare_Material_Light_Directions(RenderInfoClass&,MaterialLightDirections&) {}
void Apply_Original_Shader_State(ShaderClass s) { assert(!open);state[2]=s.bits; }
void Apply_Original_Texture_Stage_State(ShaderClass,bool,bool) { assert(!open); }
void Bind_Texture(unsigned,bool) { assert(!open);state[0]=0; }
void Disable_Texture_Stage(unsigned stage) { assert(!open);state[stage]=0; }
void Apply_Original_Texture_Coordinate_State(VertexMaterialClass *m) { assert(!open);state[3]=m?m->id:0; }
void Capture_Original_Texture_Coordinate_State(unsigned stage,OriginalTextureCoordinateState *s) {
    s->texcoord_index=stage; s->texture_transform_flags=state[3];
}
const Vector2 *Resolve_UV_Array_For_Texture_State(MeshModelClass*,const OriginalTextureCoordinateState&,const Vector2 *uv) { return uv; }
unsigned Texture_Coordinate_Mode(const OriginalTextureCoordinateState&) { return 0; }
bool Emit_Original_Texture_Coordinate(unsigned stage,unsigned,const OriginalTextureCoordinateState &s,
    const Vector2 *uv,const Vector3 *p,const Vector3 *n,unsigned i,
    const Matrix3D &world,const Matrix3D &view,const char*) {
    if(!uv) return false;
    current[3+stage*2]=uv[i].X + world.offset + float(s.texture_transform_flags)*p[i].X;
    current[4+stage*2]=uv[i].Y + view.offset + (n ? n[i].Y : 0);
    return true;
}
struct MaterialVertexColor { Vector3 final_color; float alpha; bool lighting; unsigned light_count; };
MaterialVertexColor Evaluate_Material_Vertex_Color(bool,VertexMaterialClass *m,
    const unsigned*,const unsigned*,unsigned i,const Vector3*,const Matrix3D &w,
    RenderInfoClass&,MaterialLightDirections&,bool discarded_skin_rgb) {
    if (discarded_skin_rgb) {
        assert(g_logged_first_material_lighting && g_logged_first_skin_texture_color);
        return {Vector3(1,1,1),float(i%7)/7,false,0};
    }
    return {Vector3(float(i%13)/13,float(m->id)/3,w.offset),float(i%7)/7,false,0};
}
float Clamp01(float x) { return std::max(0.f,std::min(1.f,x)); }
void glColor4f(float r,float g,float b,float a) { current[7]=r;current[8]=g;current[9]=b;current[10]=a; }
void glColor4ub(GLubyte r,GLubyte g,GLubyte b,GLubyte a) { glColor4f(r/255.f,g/255.f,b/255.f,a/255.f); }
void glNormal3f(float x,float y,float z) { current[11]=x;current[12]=y;current[13]=z; }
bool Emit_Indexed_Texture_Coordinate(unsigned stage,unsigned,const OriginalTextureCoordinateState &s,
    const float *uv0,const float *uv1,const float *position,const float *normal,
    const float *world,const float *view,const char*) {
    const float *uv=s.texcoord_index ? uv1 : uv0;
    current[3+stage*2]=uv[0]+position[0]*world[0]+float(s.texture_transform_flags);
    current[4+stage*2]=uv[1]+normal[1]*view[0];
    return true;
}
void glVertex3f(float x,float y,float z) {
    assert(open);current[0]=x;current[1]=y;current[2]=z;emitted.push_back(current);++calls;
}
void glBegin(unsigned mode) { assert(mode==GL_TRIANGLES && !open);open=true;emitted.clear(); }
void glEnd() {
    assert(open);open=false;++draws;
    if(capture) for(const auto &a:emitted) recorded.push_back({a,state});
}
void vglRenegadeEndIndexed(int count,const uint16_t *indices) {
    assert(open && count%3==0);open=false;++draws;
    for(int i=0;i<count;++i) {
        assert(indices[i]<emitted.size());
        if(capture) recorded.push_back({emitted[indices[i]],state});
    }
}
static void run(MeshModelClass *model,MeshClass &mesh,RenderInfoClass &render_info,
    const std::vector<Vector3> &points,const std::vector<Vector3> &ns,
    const std::vector<TriIndex> &ts,bool is_skin,int base_pass_count) {
    const Vector3 *vertices=points.data(),*normals=ns.empty()?nullptr:ns.data();
    const TriIndex *triangles=ts.data();
    const int vertex_count=points.size(),triangle_count=ts.size();
    const Matrix3D original_world_transform={.25f},original_view_transform={-.5f};
    #include "production.inc"
}
struct Submission {
    const unsigned char *vertex_data;
    const uint16_t *index_data;
    uint32_t vertex_stride,triangle_count,first_index,base_vertex_index;
    const float *world_transform,*view_transform;
    const char *texture_names[2];
};
static void run_indexed(const Submission &submission,bool dynamic_two_uv_layout,bool fused_index_preparation) {
    const bool mesh_layout=!dynamic_two_uv_layout;
    OriginalTextureCoordinateState texture_coordinates[2]={{0,2},{1,3}};
    #include "indexed-production.inc"
}
static void test_generic_indexed() {
    size_t compared=0;
    std::vector<unsigned char> bytes(17000*44+1);
    std::vector<uint16_t> indices={9,8,7};
    for(unsigned i=0;i<18000;++i) indices.push_back((i%29==0 ? 8192 : 0)+((i/3+i%3)%2000));
    const float world[1]={.5f},view[1]={-.25f};
    for(unsigned stride:{36,44}) for(unsigned base:{0,7}) {
        for(unsigned i=0;i<17000;++i) {
            float p[6]={float(i)/7,float(i%11),float(i%13),1,float(i%3)/3,0};
            uint32_t color=(i*13371337U)^0xffa012efU;
            float uv[4]={float(i%19)/19,float(i%23)/23,float(i%29)/29,float(i%31)/31};
            auto *vertex=bytes.data()+1+i*stride;
            std::memcpy(vertex,p,sizeof(p));std::memcpy(vertex+24,&color,4);
            std::memcpy(vertex+28,uv,stride-28);
        }
        Submission s={bytes.data()+1,indices.data(),stride,6000,3,base,world,view,{"a","b"}};
        std::vector<Recorded> baseline; Attributes last{};
        for(bool indexed:{false,true}) {
            current={};state={1,2,3,4};recorded.clear();
            run_indexed(s,stride==44,indexed); assert(!open);
            if(!indexed) {baseline=recorded;last=current;}
            else {
                assert(recorded==baseline);compared+=recorded.size();
                for(unsigned a=3;a<current.size();++a) assert(current[a]==last[a]);
            }
        }
    }
    std::printf("production generic indexed equivalence PASS corners=%zu layouts=36/44 offsets=unaligned base=0/7\n",compared);
}
int main() {
    MeshModelClass model; MeshClass mesh; RenderInfoClass info;
    std::vector<Vector3> points(17000),normals(17000);
    model.colors.resize(points.size());
    for(auto &uv:model.uv) uv.resize(points.size());
    for(unsigned i=0;i<points.size();++i) {
        points[i]=Vector3(float(i)/9,float(i%19),float(i%11)); normals[i]=Vector3(1,float(i%3),0);
        model.uv[0][i]={float(i%7)/7,float(i%13)/13};model.uv[1][i]={float(i%5)/5,float(i%17)/17};
    }
    std::vector<TriIndex> triangles;
    for(unsigned i=0;i<6000;++i) {
        unsigned a=(i/2)%2000;
        triangles.push_back({uint16_t(a),uint16_t(a+1),uint16_t(a+2)});
        if(i%19==0) triangles.back()={uint16_t(a),uint16_t(a+8192),uint16_t(a)};
        if(i%97==0) triangles.back()[1]=20000; // invalid whole triangle discarded
    }
    size_t compared=0;
    for(unsigned variant=0;variant<5;++variant) for(bool skin:{false,true}) for(unsigned group:{37,9000}) {
        model.variant=variant;model.group=group;
        std::vector<Recorded> baseline; Attributes last{};
        for(unsigned mode:{0,8,10}) {
            g_render_work_cache_mode=mode;current={};state={};recorded.clear();
            g_logged_first_skin_texture_color=false;
            g_logged_first_material_lighting=false;
            run(&model,mesh,info,points,normals,triangles,skin,2);
            assert(!open);
            if(!mode) {baseline=recorded;last=current;}
            else {
                assert(recorded==baseline);compared+=recorded.size();
                for(unsigned a=3;a<11;++a) assert(current[a]==last[a]);
            }
        }
    }
    std::printf("production mesh batch equivalence PASS corners=%zu cases=40\n",compared);
    test_generic_indexed();
    // Fixed input benchmark, no logging/capture allocation or simulated GPU.
    capture=false;model.variant=1;model.group=9000;triangles.resize(4000);
    for(unsigned mode:{0,8}) {
        g_render_work_cache_mode=mode;calls=draws=0;
        std::vector<long long> samples;
        for(unsigned sample=0;sample<41;++sample) {
            auto start=std::chrono::steady_clock::now();
            run(&model,mesh,info,points,normals,triangles,false,1);
            auto end=std::chrono::steady_clock::now();
            if(sample) samples.push_back(std::chrono::duration_cast<std::chrono::nanoseconds>(end-start).count());
        }
        std::sort(samples.begin(),samples.end());
        std::printf("HOST fixture mode=%u median_ns=%lld p95_ns=%lld p99_ns=%lld worst_ns=%lld emitted=%llu draws=%llu\n",
            mode,samples[20],samples[37],samples[39],samples[39],(unsigned long long)calls,(unsigned long long)draws);
    }
}
