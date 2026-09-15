#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include <algorithm>
using GLboolean=bool;using GLuint=unsigned;using GLenum=unsigned;using GLsizei=int;
using SceGxmTextureFormat=unsigned;
enum {TEXTURES_NUM=4,TEX_UNINITIALIZED=1,TEX_VALID=2,GL_FALSE=0,GL_TRUE=1,
 GL_COMPRESSED_RGBA_S3TC_DXT1_EXT=11,GL_COMPRESSED_RGBA_S3TC_DXT5_EXT=15,
 SCE_GXM_TEXTURE_FORMAT_UBC1_ABGR=21,SCE_GXM_TEXTURE_FORMAT_UBC3_ABGR=25,OBJ_NOT_USED=999,
 GL_BGRA=77,SCE_GXM_TEXTURE_FORMAT_U8U8U8U8_ABGR=78};
struct Descriptor {void *data;unsigned format,w,h,mips,u,v,min,mag,mip,bias;};
struct texture {unsigned status,format,mip_count;Descriptor gxm_tex;bool use_mips;
 void *palette_data,*data;unsigned last_frame,u_mode,v_mode,min_filter,mag_filter,mip_filter,lod_bias;};
texture texture_slots[TEXTURES_NUM]={};
static std::vector<uint8_t> storage;static bool fail=false;static unsigned allocations=0;
void *gpu_alloc_mapped_for_gpu(unsigned size) {++allocations;if(fail)return nullptr;storage.assign(size,0xcc);return storage.data();}
void vglInitSwizzledTexture(Descriptor *d,void *p,unsigned f,unsigned w,unsigned h,unsigned n) {*d={p,f,w,h,n,0,0,0,0,0,0};}
void vglInitLinearTexture(Descriptor *d,void *p,unsigned f,unsigned w,unsigned h,unsigned n) {vglInitSwizzledTexture(d,p,f,w,h,n);}
void vglSetTexUMode(Descriptor *d,unsigned v){d->u=v;}
void vglSetTexVMode(Descriptor *d,unsigned v){d->v=v;}
void vglSetTexMinFilter(Descriptor *d,unsigned v){d->min=v;}
void vglSetTexMagFilter(Descriptor *d,unsigned v){d->mag=v;}
void vglSetTexMipFilter(Descriptor *d,unsigned v){d->mip=v;}
void vglSetTexLodBias(Descriptor *d,unsigned v){d->bias=v;}
void vglSetTexMipmapCount(Descriptor *d,unsigned v){d->mips=v;}
#include "dxt-chain-production.inc"
using CopyPixel=void(*)(uint8_t*,uint8_t*);
void copy8(uint8_t *d,uint8_t *s){memcpy(d,s,8);}
void copy16(uint8_t *d,uint8_t *s){memcpy(d,s,16);}
#include "dxt-swizzle-reference.inc"
texture fresh(bool mips=true) {texture t={};t.status=TEX_UNINITIALIZED;t.use_mips=mips;t.u_mode=1;t.v_mode=2;t.min_filter=3;t.mag_filter=4;t.mip_filter=5;t.lod_bias=6;return t;}
using UINT=unsigned;
enum {D3D_OK=0,D3DFMT_A8R8G8B8=32,GL_TEXTURE_2D=1,GL_TEXTURE_MIN_FILTER=2,
 GL_TEXTURE_MAG_FILTER=3,GL_TEXTURE_WRAP_S=4,GL_TEXTURE_WRAP_T=5,
 GL_LINEAR_MIPMAP_LINEAR=6,GL_LINEAR=7,GL_REPEAT=8,GL_NO_ERROR=0};
struct D3DSURFACE_DESC {UINT Width,Height,Format;};
struct IDirect3DSurface8 {
 UINT w,h,pitch,format=D3DFMT_A8R8G8B8;std::vector<unsigned char> data;
 int GetDesc(D3DSURFACE_DESC *d){*d={w,h,format};return D3D_OK;}
 unsigned char *Get_Data(){return data.data();} UINT Get_Pitch(){return pitch;}
};
struct IDirect3DTexture8 {
 UINT Width,Height,MipLevels,NativeTexture,PixelChecksum;
 uint64_t ResidentBytes;IDirect3DSurface8 **SurfaceLevels;bool NativeCompressed,Uploaded;
};
static unsigned bound=0,error=0,released_count=0,uploaded_count=0,generated=0;
static uint64_t released_bytes=0,uploaded_bytes=0;
static bool fail_gen=false;
static std::vector<unsigned> deleted;
void glGenTextures(int n,GLuint *id){assert(n==1);++generated;if(fail_gen)return;*id=2;texture_slots[*id]=fresh();}
void glBindTexture(unsigned target,unsigned id){assert(target==GL_TEXTURE_2D);bound=id;}
void glTexParameteri(unsigned target,unsigned key,unsigned value){
 assert(target==GL_TEXTURE_2D);auto &t=texture_slots[bound];
 if(key==GL_TEXTURE_MIN_FILTER){t.min_filter=value;t.use_mips=value==GL_LINEAR_MIPMAP_LINEAR;}
 else if(key==GL_TEXTURE_MAG_FILTER)t.mag_filter=value;
 else if(key==GL_TEXTURE_WRAP_S)t.u_mode=value;
 else if(key==GL_TEXTURE_WRAP_T)t.v_mode=value;else assert(false);
}
unsigned glGetError(){unsigned e=error;error=0;return e;}
namespace RenegadeVitaRenderer {
 void Invalidate_Texture_State_Cache(){}
 void Release_Texture(unsigned id){deleted.push_back(id);texture_slots[id].status=0;}
 void Record_Texture_Release(uint64_t bytes){++released_count;released_bytes=bytes;}
 void Record_Texture_Upload(uint64_t bytes){++uploaded_count;uploaded_bytes=bytes;}
}
uint32_t Mix_Texture_Checksum(uint32_t state,uint32_t value){return (state^value)*16777619U;}
#include "dds-surface-production.inc"
void test_surface_owner_transaction(){
 IDirect3DSurface8 a{16,16,64,D3DFMT_A8R8G8B8,std::vector<unsigned char>(16*16*4)};
 IDirect3DSurface8 b{8,8,32,D3DFMT_A8R8G8B8,std::vector<unsigned char>(8*8*4)};
 IDirect3DSurface8 c{4,4,16,D3DFMT_A8R8G8B8,std::vector<unsigned char>(4*4*4)};
 for(auto *s:{&a,&b,&c})for(unsigned i=0;i<s->data.size();++i)s->data[i]=uint8_t(i*13+57);
 IDirect3DSurface8 *surfaces[]={&a,&b,&c};
 const auto old_a=a.data,old_b=b.data,old_c=c.data;
 const auto old_storage=storage;
 uint32_t expected_checksum=2166136261U;
 for(unsigned i=0;i<a.data.size();i+=4){auto *s=a.data.data()+i;
  uint32_t word=uint32_t(s[2])|(uint32_t(s[1])<<8)|(uint32_t(s[0])<<16)|(uint32_t(s[3])<<24);
  expected_checksum=(expected_checksum^word)*16777619U;
 }
 for(unsigned kind=0;kind<7;++kind){
  IDirect3DTexture8 t={16,16,3,1,0x12345678U,168,surfaces,true,true};const auto before=t;
  texture_slots[1]=fresh();texture_slots[1].status=TEX_VALID;texture_slots[1].data=(void*)old_storage.data();
  generated=released_count=uploaded_count=0;released_bytes=uploaded_bytes=0;deleted.clear();
  fail=kind==2;fail_gen=kind==3;error=kind==4?1:0;
  if(kind==5)b.pitch=36;
  if(kind==6)surfaces[1]=nullptr;
  const bool ok=Upload_Retained_DDS_Chain(&t,true,kind==1?1:0);
  assert(ok==(kind<2));
  assert(a.data==old_a&&b.data==old_b&&c.data==old_c);
  if(ok){
   assert(t.NativeTexture==2&&!t.NativeCompressed&&t.Uploaded&&t.SurfaceLevels==surfaces);
   assert(t.PixelChecksum==(kind==0?expected_checksum:before.PixelChecksum));
   assert(t.ResidentBytes==1408&&released_count==1&&released_bytes==168&&uploaded_count==1&&uploaded_bytes==1408);
   assert(deleted==std::vector<unsigned>{1});assert(texture_slots[2].status==TEX_VALID);
  }else{
   assert(!memcmp(&t,&before,sizeof(t))&&released_count==0&&uploaded_count==0);
   assert(texture_slots[1].status==TEX_VALID&&texture_slots[1].data==old_storage.data());
   if(kind==2||kind==4)assert(deleted==std::vector<unsigned>{2});else assert(deleted.empty());
   if(kind>=5)assert(generated==0);
  }
  b.pitch=32;surfaces[1]=&b;
 }
 fail=fail_gen=false;error=0;deleted.clear();released_count=uploaded_count=0;
 IDirect3DTexture8 t={16,16,3,1,0x12345678U,0,surfaces,false,false};texture_slots[1]=fresh();
 assert(Upload_Retained_DDS_Chain(&t,false,0));assert(t.ResidentBytes==1408&&!t.NativeCompressed&&t.Uploaded);
 assert(deleted.empty()&&released_count==0&&uploaded_count==0&&t.PixelChecksum==0x12345678U);
 puts("Production DDS surface-owner transaction PASS cases=8 OOM/error retains old GPU image; all CPU mips preserved");
}
int main(){unsigned cases=0;uint64_t blocks=0;
 for(unsigned b:{8,16})for(unsigned w=4;w<=2048;w*=2)for(unsigned h=4;h<=2048;h*=2)
 for(unsigned offset:{0,1})for(bool full:{false,true}) {
  std::vector<std::vector<uint8_t>> images;std::vector<const void*> pointers;std::vector<GLsizei> sizes;
  unsigned levels=1;if(full){unsigned n=std::min(w,h);while(n>4){++levels;n/=2;}}
  std::vector<uint8_t> expected;
  for(unsigned l=0;l<levels;++l){unsigned bw=(w>>l)/4,bh=(h>>l)/4,size=bw*bh*b;
   images.emplace_back(size+offset);auto &src=images.back();for(unsigned i=0;i<src.size();++i)src[i]=uint8_t(i*73+l*19+17);
   pointers.push_back(src.data()+offset);sizes.push_back(size);
   size_t start=expected.size();expected.resize(start+size);
   if(b==8)SwizzleTexData1x1<8,copy8>(expected.data()+start,src.data()+offset,0,0,bw,bh,bw,std::min(bw,bh));
   else SwizzleTexData1x1<16,copy16>(expected.data()+start,src.data()+offset,0,0,bw,bh,bw,std::min(bw,bh));
   blocks+=bw*bh;
  }
  const auto original=images;texture_slots[1]=fresh();allocations=0;
  assert(vglRenegadeUploadDXTChain(1,b==8?11:15,w,h,levels,pointers.data(),sizes.data()));
  assert(storage==expected&&images==original&&allocations==1);
  const auto &t=texture_slots[1];const auto &d=t.gxm_tex;
  assert(t.status==TEX_VALID&&t.data==storage.data()&&t.mip_count==levels&&t.last_frame==OBJ_NOT_USED);
  assert(d.w==w&&d.h==h&&d.mips==levels&&d.u==1&&d.v==2&&d.min==3&&d.mag==4&&d.mip==5&&d.bias==6);
  ++cases;
 }
 unsigned surface_cases=0;
 for(unsigned w:{4,8,32,128})for(unsigned h:{4,16,64}) {
  std::vector<std::vector<uint8_t>> images;std::vector<const void*> pointers;std::vector<GLsizei> sizes;
  std::vector<uint8_t> expected;
  for(unsigned a=w,b=h;a>=4&&b>=4;a/=2,b/=2) {
   images.emplace_back(a*b*4);auto &src=images.back();for(unsigned i=0;i<src.size();++i)src[i]=uint8_t(i*17+9);
   pointers.push_back(src.data());sizes.push_back(src.size());
   size_t start=expected.size();unsigned stride=std::max(a,8U)*4;expected.resize(start+stride*b,0);
   for(unsigned y=0;y<b;++y)for(unsigned x=0;x<a;++x) {
    auto *d=expected.data()+start+y*stride+x*4;const auto *s=src.data()+(y*a+x)*4;
    d[0]=s[2];d[1]=s[1];d[2]=s[0];d[3]=s[3];
   }
  }
  auto original=images;texture_slots[1]=fresh();allocations=0;
  assert(vglRenegadeUploadDXTChain(1,GL_BGRA,w,h,pointers.size(),pointers.data(),sizes.data()));
  assert(storage==expected&&images==original&&allocations==1);++surface_cases;
 }
 uint8_t bytes[16]={};const void *pixels[]={bytes};GLsizei sizes[]={16};
 for(unsigned kind=0;kind<12;++kind){texture_slots[1]=fresh();const auto before=texture_slots[1];allocations=0;
  unsigned id=1,format=11;int w=4,h=4,n=1;const void *const *p=pixels;const GLsizei *s=sizes;fail=false;sizes[0]=16;pixels[0]=bytes;
  switch(kind){case 0:id=0;break;case 1:id=TEXTURES_NUM;break;case 2:w=3;break;case 3:w=4096;break;
   case 4:w=12;break;case 5:n=0;break;case 6:n=2;break;case 7:format=99;break;
   case 8:sizes[0]=7;break;case 9:p=nullptr;break;case 10:pixels[0]=nullptr;break;case 11:fail=true;break;}
  assert(!vglRenegadeUploadDXTChain(id,format,w,h,n,p,s));assert(!memcmp(&before,&texture_slots[1],sizeof(before)));
  assert(allocations==(fail?1U:0U));
 }
 fail=false;texture_slots[1]=fresh(false);pixels[0]=bytes;sizes[0]=16;
 assert(vglRenegadeUploadDXTChain(1,15,4,4,1,pixels,sizes));assert(texture_slots[1].gxm_tex.mips==1);
 const auto valid=texture_slots[1];allocations=0;
 assert(!vglRenegadeUploadDXTChain(1,15,4,4,1,pixels,sizes));assert(allocations==0&&!memcmp(&valid,&texture_slots[1],sizeof(valid)));
 printf("DXT chain production PASS cases=%u blocks=%llu invalid/OOM=12 existing-object-preserved=1\n",cases,(unsigned long long)blocks);
 printf("DDS retained surface full-chain fallback PASS cases=%u channel-order/stride/padding/ownership=exact\n",surface_cases);
 test_surface_owner_transaction();
}
