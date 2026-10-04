#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include "ww3d_vita_texture_transform.h"
using DWORD=uint32_t;
enum { D3DTTFF_DISABLE=0, D3DTTFF_COUNT1=1, D3DTTFF_COUNT2=2,
       D3DTTFF_COUNT3=3, D3DTTFF_COUNT4=4, D3DTTFF_PROJECTED=256,
       D3DTSS_TCI_PASSTHRU=0, D3DTSS_TCI_CAMERASPACEPOSITION=0x20000,
       MAX_TEXTURE_STAGES=2, GL_TRIANGLES=4 };
struct D3DMATRIX { float m[4][4]; };
struct OriginalTextureCoordinateState { DWORD texcoord_index,texture_transform_flags; D3DMATRIX texture_transform; };
using RenegadeVitaRenderer::Build_DX8_Texture_Source;
DWORD Texture_Coordinate_Mode(const OriginalTextureCoordinateState &s) { return s.texcoord_index & 0xffff0000U; }
unsigned plain_begins=0,projective_begins=0;
void glBegin(unsigned m) { assert(m==GL_TRIANGLES);++plain_begins; }
void vglRenegadeBeginProjective(unsigned m) { assert(m==GL_TRIANGLES);++projective_begins; }
#include "projective-production.inc"
static bool close(float a,float b) { return std::fabs(a-b)<0.0001f; }
int main() {
    OriginalTextureCoordinateState state={};
    state.texcoord_index=D3DTSS_TCI_CAMERASPACEPOSITION;
    for(unsigned i=0;i<4;++i) state.texture_transform.m[i][i]=1;
    float s,t,q;
    state.texture_transform_flags=0;
    Apply_DX8_Texture_Transform(state,2,3,4,1,&s,&t,&q);
    assert(s==2 && t==3 && q==1);
    state.texture_transform_flags=D3DTTFF_COUNT3|D3DTTFF_PROJECTED;
    Apply_DX8_Texture_Transform(state,2,3,0,1,&s,&t,&q);
    assert(s==2 && t==3 && q==0); // zero endpoint retained for interpolation
    Apply_DX8_Texture_Transform(state,2,3,-4,1,&s,&t,&q);
    assert(s==2 && t==3 && q==-4);
    state.texture_transform_flags=D3DTTFF_COUNT2|D3DTTFF_PROJECTED;
    Apply_DX8_Texture_Transform(state,2,3,4,1,&s,&t,&q);
    assert(s==2 && t==0 && q==3);
    state.texture_transform_flags=D3DTTFF_COUNT4|D3DTTFF_PROJECTED;
    Apply_DX8_Texture_Transform(state,2,3,4,5,&s,&t,&q);
    assert(s==2 && t==3 && q==5);
    state.texture_transform_flags=D3DTTFF_COUNT1;
    Apply_DX8_Texture_Transform(state,2,3,4,5,&s,&t,&q);
    assert(s==2 && t==0 && q==1);
    // A 2D source is extended by homogeneous coordinate one, independently
    // of the output count. Check projected UV translation and divisor.
    state.texcoord_index=D3DTSS_TCI_PASSTHRU;
    state.texture_transform_flags=D3DTTFF_COUNT3|D3DTTFF_PROJECTED;
    state.texture_transform.m[2][0]=5;state.texture_transform.m[2][1]=-7;
    state.texture_transform.m[2][2]=2;
    Apply_DX8_Texture_Transform(state,2,3,0,1,&s,&t,&q);
    assert(s==7 && t==-4 && q==2);
    state.texcoord_index=D3DTSS_TCI_CAMERASPACEPOSITION;
    state.texture_transform={};for(unsigned i=0;i<4;++i) state.texture_transform.m[i][i]=1;
    unsigned mismatches_old=0;
    for(unsigned trial=0;trial<1000;++trial) {
        double accum_s=0,accum_t=0,accum_q=0,accum_weight=0,old_s=0;
        double reference_s=0,reference_t=0,reference_q=0;
        for(unsigned v=0;v<3;++v) {
            const float input_s=(trial%13)+v*3.0f,input_t=(trial%7)-float(v);
            const float divisor=1+v+(trial%5)*0.125f;
            const double weight=(1.0+v)/(1.0+v*2.0); // barycentric weight / clip W
            Apply_DX8_Texture_Transform(state,input_s,input_t,divisor,1,&s,&t,&q);
            accum_s+=s*weight;accum_t+=t*weight;accum_q+=q*weight;accum_weight+=weight;
            old_s+=(input_s/divisor)*weight;
            reference_s+=input_s*weight;reference_t+=input_t*weight;reference_q+=divisor*weight;
        }
        assert(close(accum_s/accum_q,reference_s/reference_q));
        assert(close(accum_t/accum_q,reference_t/reference_q));
        if(!close(old_s/accum_weight,reference_s/reference_q)) ++mismatches_old;
    }
    assert(mismatches_old>900);
    OriginalTextureCoordinateState stages[2]={};
    Begin_Texture_Coordinate_Primitive(stages);assert(plain_begins==1 && projective_begins==0);
    for(unsigned stage=0;stage<2;++stage) {
        stages[stage].texture_transform_flags=D3DTTFF_COUNT3|D3DTTFF_PROJECTED;
        Begin_Texture_Coordinate_Primitive(stages);
        stages[stage].texture_transform_flags=0;
    }
    assert(projective_begins==2);
    std::printf("projective coordinate retention/interpolation PASS triangles=1000 old_mismatches=%u\n",mismatches_old);
}
