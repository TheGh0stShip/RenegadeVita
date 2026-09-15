#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <vector>
#include "ww3d_vita_indexed_mesh_batch.h"
#define SKIP_ERROR_HANDLING
#define THREAD_SAFE()
#define TEXTURES_SPEEDHACK
#define vgl_fast_memcpy std::memcpy
#define LEGACY_VERTEX_STRIDE 24
#define LEGACY_MT_VERTEX_STRIDE 26
#define LEGACY_NT_VERTEX_STRIDE 22
#define FFP_VERTEX_ATTRIBS_NUM 10
#define FFP_ATTRIB_MASK_ALL 15
#define FFP_ATTRIB_POSITION 0
#define FFP_ATTRIB_TEX0 1
#define FFP_ATTRIB_COLOR 2
#define GL_FALSE false
#define GL_TRUE true
using GLfloat=float;
using GLsizei=int;
using GLushort=uint16_t;
enum {GL_TRIANGLES,GL_QUADS,GL_LINE_STRIP,GL_LINE_LOOP,
      SCE_GXM_INDEX_SOURCE_INDEX_16BIT,SCE_GXM_INDEX_FORMAT_U16,GL_OUT_OF_MEMORY};
int vgl_error=0;
bool fail_index_allocation=false;
struct V2 {float x,y;}; struct V3 {float x,y,z;}; struct V4 {float x,y,z,w;};
struct { V2 uv; V4 clr,amb,diff,spec,emiss; V3 nor; V2 uv2; } current_vtx;
float storage[2000000], *legacy_pool=storage, *legacy_pool_ptr=storage;
bool lighting_state=false, ffp_dirty_frag=false, ffp_dirty_vert=false;
struct { unsigned state,tex_id[2]; } texture_units[2];
struct texture {
    int gxm_tex,min_filter,mip_filter,u_mode,v_mode,mip_count;
    bool overridden,use_mips;
} texture_slots[2];
struct sampler {int min_filter,mip_filter,u_mode,v_mode; bool use_mips;};
sampler *samplers[2]={};
struct Attribute {int unused;}; struct Stream {unsigned stride;};
Attribute legacy_vertex_attrib_config[9],legacy_mt_vertex_attrib_config[10],legacy_nt_vertex_attrib_config[8];
Stream legacy_vertex_stream_config[9],legacy_mt_vertex_stream_config[10],legacy_nt_vertex_stream_config[8];
unsigned vertex_count=0,ffp_mode=GL_TRIANGLES,prim=0;
uint16_t ffp_vertex_attrib_state=0,default_indices[1000];
uint16_t *default_idx_ptr=default_indices,*default_quads_idx_ptr=default_indices,*default_line_strips_idx_ptr=default_indices;
int ffp_vertex_num_params=0,gxm_context=0;
unsigned observed_stride=0, draws=0;
std::vector<float> expected;
std::vector<float> expanded_expected;
std::vector<uint16_t> copied_indices;
unsigned populated() {return (texture_units[1].state ? 7 : texture_units[0].state ? 5 : 3)+(lighting_state ? 19 : 4);}
unsigned stride() {return (texture_units[1].state ? 26 : texture_units[0].state ? 24 : 22)-((COMPACT && !lighting_state) ? 15 : 0);}
void reload_ffp_shaders(Attribute*,Stream *streams,int) {
    ffp_vertex_num_params=2;
    observed_stride=streams[0].stride;
    assert(observed_stride==stride()*sizeof(float));
    assert(streams[1].stride==observed_stride);
}
void gl_primitive_to_gxm(unsigned,unsigned &primitive,unsigned) { primitive=0; }
template<class... T> void vglSetTexMinFilter(T...) {}
template<class... T> void vglSetTexMipFilter(T...) {}
template<class... T> void vglSetTexUMode(T...) {}
template<class... T> void vglSetTexVMode(T...) {}
template<class... T> void vglSetTexMipmapCount(T...) {}
template<class... T> void sceGxmSetFragmentTexture(T...) {}
void sceGxmSetVertexStream(int,int,const void *p) { assert(p==legacy_pool); }
uint16_t *gpu_alloc_mapped_temp(size_t bytes) {
    if(fail_index_allocation) return nullptr;
    assert(bytes <= VitaIndexedMeshBatch::IndexCapacity * sizeof(uint16_t));
    copied_indices.resize(bytes / sizeof(uint16_t));
    return copied_indices.data();
}
void restore_polygon_mode(unsigned) {}
void sceGxmDraw(int,unsigned,int,const uint16_t *indices,uint32_t count) {
    assert(observed_stride/4==stride());
    if (expanded_expected.empty()) assert(count==vertex_count);
    else {
        assert(indices == copied_indices.data());
        assert(count * populated() == expanded_expected.size());
        for(unsigned i=0;i<count;++i) {
            assert(indices[i] < vertex_count);
            for(unsigned c=0;c<populated();++c)
                assert(legacy_pool[indices[i]*stride()+c] == expanded_expected[i*populated()+c]);
        }
    }
    for (unsigned v=0;v<vertex_count;++v)
        for(unsigned c=0;c<populated();++c)
            assert(legacy_pool[v*stride()+c]==expected[v*populated()+c]);
    ++draws;
}
#include "production.inc"
#if INDEXED
static void test_indexed() {
    static VitaIndexedMeshBatch batch;
    uint64_t corners=0, unique=0;
    // Grid reuse, hash collisions, degenerate triangles, capacity flushes and
    // changed attributes on the same source indices in subsequent batches.
    for(unsigned lights=0;lights<2;++lights) for(unsigned textures=0;textures<3;++textures)
    for(unsigned round=0;round<3;++round) {
        lighting_state=lights; texture_units[0].state=textures>0; texture_units[1].state=textures>1;
        legacy_pool=legacy_pool_ptr=storage;
        batch.Reset(); vertex_count=0; expected.clear(); expanded_expected.clear();
        auto flush = [&]() {
            if (!batch.Count()) return;
            float *start=legacy_pool;
            corners+=batch.Count(); unique+=batch.Vertices();
            vglRenegadeEndIndexed(batch.Count(),batch.Indices());
            assert(legacy_pool-start == batch.Vertices()*stride());
            // The copied GPU index storage must not alias reusable CPU scratch.
            assert(copied_indices.data()!=batch.Indices());
            batch.Reset(); vertex_count=0; expected.clear(); expanded_expected.clear();
        };
        for(unsigned triangle=0;triangle<10000;++triangle) {
            if(batch.Full()) flush();
            for(unsigned c=0;c<3;++c) {
                unsigned id=(triangle/2+c+(triangle%2))*3%6000;
                if(round==1 && c==1) id+=8192; // deliberate direct-map collision
                if(round==2) id=triangle%7; // repeated/degenerate triangles
                current_vtx={{float(id)/7,float(round)},{.1f,.2f,.3f,float(id)/16000},
                    {1,2,3,4},{5,6,7,8},{9,10,11,12},{13,14,15,16},{17,18,19},{float(id)/9,4.5f}};
                std::vector<float> attributes={float(id),float(round),float(id+round)};
                if(textures) attributes.insert(attributes.end(),{current_vtx.uv.x,current_vtx.uv.y});
                if(textures>1) attributes.insert(attributes.end(),{current_vtx.uv2.x,current_vtx.uv2.y});
                const float *p=lights ? &current_vtx.amb.x : &current_vtx.clr.x;
                attributes.insert(attributes.end(),p,p+(lights ? 19 : 4));
                expanded_expected.insert(expanded_expected.end(),attributes.begin(),attributes.end());
                if(batch.Append(id)) {
                    expected.insert(expected.end(),attributes.begin(),attributes.end());
                    glVertex3f(float(id),float(round),float(id+round));
                }
                assert(batch.Last()==id);
            }
        }
        flush();
        // Alternate back to ordinary immediate submission after indexed draws.
        expected.assign(3*populated(),0); expanded_expected.clear();
        std::memset(&current_vtx,0,sizeof(current_vtx));
        glVertex3f(0,0,0); glVertex3f(0,0,0); glVertex3f(0,0,0); glEnd();
    }
    std::printf("indexed immediate equivalence PASS corners=%llu unique=%llu scratch_bytes=%zu\n",
        (unsigned long long)corners,(unsigned long long)unique,sizeof(batch));
    vertex_count=0; float *start=legacy_pool;
    glVertex3f(0,0,0);glVertex3f(1,0,0);glVertex3f(0,1,0);
    const uint16_t triangle[3]={0,1,2};
    unsigned previous_draws=draws;fail_index_allocation=true;
    vglRenegadeEndIndexed(3,triangle);
    assert(vgl_error==GL_OUT_OF_MEMORY && draws==previous_draws);
    assert(legacy_pool==legacy_pool_ptr && legacy_pool-start==3*stride());
    fail_index_allocation=false;
    std::puts("indexed GPU allocation failure PASS: error retained, no invalid draw");
}
#endif
int main() {
    for (auto &s:legacy_vertex_stream_config) s.stride=24*4;
    for (auto &s:legacy_mt_vertex_stream_config) s.stride=26*4;
    for (auto &s:legacy_nt_vertex_stream_config) s.stride=22*4;
    unsigned written_bytes=0;
    for(unsigned round=0;round<8;++round) for(unsigned lights=0;lights<2;++lights)
        for(unsigned textures=0;textures<3;++textures) {
            lighting_state=lights; texture_units[0].state=textures>0; texture_units[1].state=textures>1;
            vertex_count=0; expected.clear(); float *start=legacy_pool;
            for(unsigned v=0;v<99;++v) {
                current_vtx={{1.25f,2.75f},{.1f,.2f,.3f,.4f},
                    {1,2,3,4},{5,6,7,8},{9,10,11,12},{13,14,15,16},{17,18,19},{3.5f,4.5f}};
                expected.insert(expected.end(),{float(v),float(v+1),float(v+2)});
                if(textures) expected.insert(expected.end(),{current_vtx.uv.x,current_vtx.uv.y});
                if(textures>1) expected.insert(expected.end(),{current_vtx.uv2.x,current_vtx.uv2.y});
                const float *attributes=lights ? &current_vtx.amb.x : &current_vtx.clr.x;
                for(unsigned i=0;i<(lights ? 19U : 4U);++i) expected.push_back(attributes[i]);
                glVertex3f(float(v),float(v+1),float(v+2));
            }
            glEnd();
            assert(legacy_pool==legacy_pool_ptr && legacy_pool-start==99*stride());
            written_bytes+=99*stride()*sizeof(float);
        }
    std::printf("vitaGL stream PASS compact=%d draws=%u reserved_bytes=%u\n",COMPACT,draws,written_bytes);
#if INDEXED
    test_indexed();
#endif
}
