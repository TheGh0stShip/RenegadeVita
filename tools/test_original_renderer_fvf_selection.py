"""Retain the original category FVF policy over all structural input combinations.

Mesh/sorting inputs are test doubles. The 72 layouts are potential producer
outputs, not evidence that all occur in retail assets or render on hardware.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OriginalRendererFVFSelectionTest(unittest.TestCase):
    def test_all_layouts_sort_override_and_user_lighting(self):
        source = (ROOT / 'staging/ww3d2/dx8renderer.cpp').read_text()
        start = source.index('unsigned DX8FVFCategoryContainer::Define_FVF(')
        end = source.index('DX8RigidFVFCategoryContainer::DX8RigidFVFCategoryContainer(', start)
        body = source[start:source.rfind('// ----------------------------------------------------------------------------', start, end)]
        prefix = r'''
#include <cassert>
#include <set>
enum { D3DFVF_XYZ=2, D3DFVF_NORMAL=16, D3DFVF_DIFFUSE=64, D3DFVF_SPECULAR=128,
 D3DFVF_TEX1=256,D3DFVF_TEX2=512,D3DFVF_TEX3=768,D3DFVF_TEX4=1024,
 D3DFVF_TEX5=1280,D3DFVF_TEX6=1536,D3DFVF_TEX7=1792,D3DFVF_TEX8=2048 };
struct MeshGeometryClass { enum { SORT=1 }; };
struct MeshModelClass {
 bool sorted=false, normals=false, diffuse=false, specular=false;
 int uv=0; unsigned color=0;
 bool Get_Flag(int) const { return sorted; }
 int Get_UV_Array_Count() const { return uv; }
 unsigned *Get_Color_Array(int i, bool) { return (i ? specular : diffuse) ? &color : nullptr; }
 bool Needs_Vertex_Normals() const { return normals; }
};
struct WW3D { static bool sorting; static bool Is_Sorting_Enabled() { return sorting; } };
bool WW3D::sorting=true;
const unsigned dynamic_fvf_type=0x252;
struct DX8FVFCategoryContainer {
 static unsigned Define_FVF(MeshModelClass *,unsigned *,bool);
};
'''
        checks = r'''
int main() {
 std::set<unsigned> formats;
 MeshModelClass mesh;
 for(int uv=0;uv<=8;++uv) for(int n=0;n<2;++n)
 for(int d=0;d<2;++d) for(int s=0;s<2;++s) {
  mesh.uv=uv;mesh.normals=n;mesh.diffuse=d;mesh.specular=s;
  unsigned expected=2U|(n?16U:0U)|(d?64U:0U)|(s?128U:0U)|(unsigned(uv)<<8);
  for(int enabled=0;enabled<2;++enabled) {
   assert(DX8FVFCategoryContainer::Define_FVF(&mesh,nullptr,enabled)==expected);
   unsigned user=0;
   assert(DX8FVFCategoryContainer::Define_FVF(&mesh,&user,enabled)==(expected|64U));
  }
  formats.insert(expected);
  mesh.sorted=true;
  assert(DX8FVFCategoryContainer::Define_FVF(&mesh,nullptr,true)==dynamic_fvf_type);
  WW3D::sorting=false;
  assert(DX8FVFCategoryContainer::Define_FVF(&mesh,nullptr,true)==expected);
  WW3D::sorting=true;mesh.sorted=false;
 }
 assert(formats.size()==72);
 assert(formats.count(0x152) && formats.count(0x252));
}
'''
        with tempfile.TemporaryDirectory() as folder:
            cpp = Path(folder) / 'fvf.cpp'; binary = Path(folder) / 'fvf'
            cpp.write_text(prefix + body + checks)
            subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            '-Wno-unused-parameter', '-fsanitize=address,undefined',
                            str(cpp), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, env={**os.environ,
                           'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1',
                           'UBSAN_OPTIONS': 'halt_on_error=1'})
            arm = Path('/usr/local/vitasdk/bin/arm-vita-eabi-g++')
            if arm.exists():
                subprocess.run([str(arm), '-std=c++17', '-mcpu=cortex-a9',
                                '-mfpu=neon', '-mfloat-abi=hard', '-Wno-unused-parameter',
                                '-include', str(ROOT / 'port/compatibility/include/renegade_target_abi.h'),
                                '-c', str(cpp), '-o', str(Path(folder) / 'fvf.arm.o')], check=True)


if __name__ == '__main__':
    unittest.main()
