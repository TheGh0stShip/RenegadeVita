"""Compare category layout metadata with the verbatim Westwood FVF constructor."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CategoryFVFLayoutTest(unittest.TestCase):
    def test_original_offsets_all_layouts_and_rejections(self):
        source = (ROOT / 'staging/ww3d2/dx8fvf.cpp').read_text()
        start = source.index('FVFInfoClass::FVFInfoClass(')
        body = source[start:source.index('void FVFInfoClass::Get_FVF_Name(', start)]
        prefix = r'''
#include "category_fvf_layout.h"
#include <cassert>
#include <cstring>
#include <cstdint>
using DWORD=uint32_t;
enum {D3DFVF_XYZ=2,D3DFVF_XYZB4=12,D3DFVF_NORMAL=16,D3DFVF_DIFFUSE=64,
      D3DFVF_SPECULAR=128,D3DFVF_LASTBETA_UBYTE4=4096,D3DDP_MAXTEXCOORD=8};
#define D3DFVF_TEXCOORDSIZE1(i) (3U<<(16U+2U*(i)))
#define D3DFVF_TEXCOORDSIZE2(i) 0U
#define D3DFVF_TEXCOORDSIZE3(i) (1U<<(16U+2U*(i)))
#define D3DFVF_TEXCOORDSIZE4(i) (2U<<(16U+2U*(i)))
// Vertex-size provider is independent of the offset constructor under test.
unsigned Get_FVF_Vertex_Size(unsigned) { return 0; }
struct FVFInfoClass {
 unsigned FVF,fvf_size,location_offset,blend_offset,normal_offset,diffuse_offset,specular_offset;
 unsigned texcoord_offset[8];
 explicit FVFInfoClass(unsigned);
};
'''
        checks = r'''
int main() {
 using namespace RenegadeVitaRenderer;
 unsigned cases=0;
 for(unsigned uv=0;uv<=8;++uv) for(unsigned n=0;n<2;++n)
 for(unsigned d=0;d<2;++d) for(unsigned s=0;s<2;++s) {
  unsigned fvf=2U|(n?16U:0U)|(d?64U:0U)|(s?128U:0U)|(uv<<8);
  FVFInfoClass original(fvf);CategoryFVFLayout layout={};
  assert(Decode_Category_FVF(fvf,layout));
  assert(layout.normal_offset==original.normal_offset);
  assert(layout.diffuse_offset==original.diffuse_offset);
  assert(layout.specular_offset==original.specular_offset);
  for(unsigned i=0;i<8;++i) assert(layout.uv_offsets[i]==original.texcoord_offset[i]);
  assert(layout.stride==12U+12U*n+4U*d+4U*s+8U*uv);
  assert(layout.uv_count==uv && layout.has_normal==bool(n));
  assert(layout.has_diffuse==bool(d) && layout.has_specular==bool(s));
  ++cases;
 }
 assert(cases==72);
 CategoryFVFLayout sentinel={};sentinel.stride=123;
 for(uint32_t bad:{0U,4U,6U,12U,0x902U,0x10002U,0x40000002U,0xffffffffU}) {
  auto copy=sentinel;assert(!Decode_Category_FVF(bad,copy));
  assert(std::memcmp(&copy,&sentinel,sizeof(copy))==0);
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            cpp=Path(folder)/'layout.cpp';binary=Path(folder)/'layout'
            cpp.write_text('#include <initializer_list>\n'+prefix+body+checks)
            include=str(ROOT/'port/renderer/vita')
            subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',
                            '-Wno-type-limits','-I'+include,'-fsanitize=address,undefined',
                            str(cpp),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True,env={**os.environ,
                           'ASAN_OPTIONS':'detect_leaks=1:halt_on_error=1',
                           'UBSAN_OPTIONS':'halt_on_error=1'})
            arm=Path('/usr/local/vitasdk/bin/arm-vita-eabi-g++')
            if arm.exists():
                subprocess.run([str(arm),'-std=c++17','-mcpu=cortex-a9','-mfpu=neon',
                                '-mfloat-abi=hard','-I'+include,'-include',
                                str(ROOT/'port/compatibility/include/renegade_target_abi.h'),
                                '-c',str(cpp),'-o',str(Path(folder)/'layout.arm.o')],check=True)


if __name__ == '__main__':
    unittest.main()
