#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#define MAX(a,b) std::max(unsigned(a),unsigned(b))
#define VGL_ALIGN(x,a) (((x)+(a)-1)/(a)*(a))
using GLboolean=bool;
enum { GL_RGBA=1,GL_UNSIGNED_BYTE=2,SCE_GXM_TEXTURE_FORMAT_U8U8U8U8_ABGR=3,OBJ_NOT_USED=9999,FRAME_PURGE_FREQ=3,GL_OUT_OF_MEMORY=99 };
static bool fail_allocation=false;
static unsigned last_error=0;
#define SET_GL_ERROR(e) last_error=(e);return;
struct texture { unsigned last_frame,mip_count; void *data; void *gxm_tex; int status=0; void *palette_data=nullptr; };
static unsigned vgl_framecount=100,unpack_row_len=0;
static std::vector<uint8_t> allocated;
static unsigned old_copies=0,retirements=0;
static const void *old_pointer;
void *gpu_alloc_mapped_for_gpu(size_t size) { if(fail_allocation) return nullptr;allocated.assign(size,0xcd);return allocated.data(); }
void gpu_free_texture_data(texture *t) { assert(t->data==old_pointer);++retirements; }
void sceGxmTextureSetData(void **p,void *data) { *p=data; }
void vgl_fast_memcpy(void *dst,const void *src,size_t size) {
    if(src==old_pointer) ++old_copies;
    std::memcpy(dst,src,size);
}
using SceGxmTextureFormat=unsigned;
enum { TEX_VALID=1,SCE_GXM_TEXTURE_BASE_FORMAT_P8=0xee000000 };
static void *color_table=nullptr;
static unsigned descriptor_width=0,descriptor_height=0;
unsigned tex_format_to_bytespp(unsigned) { return 4; }
void vgl_memset(void *p,int c,size_t size) { std::memset(p,c,size); }
void vglInitLinearTexture(void **p,void *data,unsigned,unsigned w,unsigned h,unsigned mips) {
    *p=data;descriptor_width=w;descriptor_height=h;assert(mips==1);
}
#include "allocation.inc"
unsigned nearest_po2(unsigned n) { unsigned result=1;while(result<n) result*=2;return result; }
struct Fixture { unsigned w,h,x,y,width,height,level,mips,format; };
#define INPUTS \
    unsigned orig_w=f.w,orig_h=f.h,xoffset=f.x,yoffset=f.y,width=f.width,height=f.height; \
    unsigned level=f.level,format=f.format,type=GL_UNSIGNED_BYTE,tex_format=SCE_GXM_TEXTURE_FORMAT_U8U8U8U8_ABGR; \
    unsigned bpp=4,po2_w=0,po2_h=0,jumps[16]={}; bool fast_store=true; \
    (void)level;(void)format;(void)type;(void)tex_format;
void baseline(texture *tex,const Fixture &f,const void *pixels) {
    INPUTS
    #include "baseline.inc"
}
void patched(texture *tex,const Fixture &f,const void *pixels) {
    INPUTS
    #include "patched.inc"
}
int main() {
    for(unsigned width:{319,320,512}) for(unsigned height:{239,240}) {
        std::vector<uint8_t> image(width*height*4);
        for(size_t i=0;i<image.size();++i) image[i]=uint8_t(i*17+3);
        texture t={OBJ_NOT_USED,0,nullptr,nullptr};
        gpu_alloc_texture(width,height,SCE_GXM_TEXTURE_FORMAT_U8U8U8U8_ABGR,
            image.data(),&t,4,nullptr,nullptr,true);
        assert(descriptor_width==width && descriptor_height==height && t.status==TEX_VALID);
        assert(allocated.size()==VGL_ALIGN(width,8)*height*4);
        for(unsigned y=0;y<height;++y)
            assert(std::memcmp(allocated.data()+y*VGL_ALIGN(width,8)*4,image.data()+y*width*4,width*4)==0);
    }
    std::puts("pinned linear texture allocation PASS: NPOT dimensions, aligned stride, source pixels");
    std::vector<Fixture> fixtures={
        {320,240,0,0,320,240,0,1,GL_RGBA},
        {512,256,0,0,512,256,0,1,GL_RGBA},
        {319,239,0,0,319,239,0,1,GL_RGBA},
        {512,256,0,0,320,240,0,1,GL_RGBA},
        {320,240,8,7,96,83,0,1,GL_RGBA},
        {512,256,0,0,512,256,0,2,GL_RGBA},
        {320,240,0,0,320,240,0,1,77}};
    unsigned cases=0,avoided=0;
    for(const auto &f:fixtures) for(unsigned row_pad:{0,8}) {
        unpack_row_len=row_pad ? f.width+row_pad : 0;
        size_t size=VGL_ALIGN(f.w,8)*f.h*4;
        if(f.mips>1) size=nearest_po2(f.w)*nearest_po2(f.h)*4*5/4;
        std::vector<uint8_t> original(size),pixels((f.width+row_pad)*f.height*4);
        for(size_t i=0;i<original.size();++i) original[i]=uint8_t(i*17+31);
        for(size_t i=0;i<pixels.size();++i) pixels[i]=uint8_t(i*31+7);
        const auto before=original;old_pointer=original.data();
        texture t={99,f.mips,original.data(),original.data()};
        old_copies=retirements=0;baseline(&t,f,pixels.data());
        assert(old_copies==1 && retirements==1 && original==before);
        const auto expected=allocated;
        t={99,f.mips,original.data(),original.data()};old_copies=retirements=0;
        patched(&t,f,pixels.data());
        assert(allocated==expected && original==before && retirements==1);
        assert(t.data==allocated.data() && t.gxm_tex==allocated.data() && t.last_frame==OBJ_NOT_USED);
        const bool full=f.level==0 && f.mips==1 && f.x==0 && f.y==0 && f.width==f.w && f.height==f.h && f.w%8==0 && f.format==GL_RGBA;
        assert(old_copies==(full ? 0U : 1U));avoided+=full;++cases;
    }
    std::printf("texture RGBA upload equivalence PASS cases=%u avoided_old_copies=%u old_storage_unchanged=1\n",cases,avoided);
    std::printf("movie 320x240 storage_bytes=524288->307200 steady_copy_bytes=831488->307200\n");
    std::vector<uint8_t> original(320*240*4,42),pixels(original.size(),7);
    old_pointer=original.data();texture t={99,1,original.data(),original.data()};
    retirements=old_copies=0;fail_allocation=true;
    patched(&t,fixtures.front(),pixels.data());
    assert(last_error==GL_OUT_OF_MEMORY && retirements==0 && old_copies==0);
    assert(t.data==original.data() && t.gxm_tex==original.data());
    assert(std::all_of(original.begin(),original.end(),[](uint8_t x){return x==42;}));
    std::puts("texture replacement allocation failure PASS: previous image retained");
}
