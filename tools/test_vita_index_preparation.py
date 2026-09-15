"""Execute both production indexed validation/checksum traversals."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IndexPreparationTest(unittest.TestCase):
    def test_fused_matches_separate_traversals(self):
        source = (ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp').read_text()
        def section(start, end):
            offset = source.index(start)
            return source[offset:source.index(end, offset)]
        prefix = section('IndexedSubmissionResult Submit_Indexed_Triangles(',
                         '#if defined(__vita__)\n\t// Let vitaGL')
        # Stop at the native emitter: exercise every production validation and
        # checksum operation; capture its local result without issuing a draw.
        prefix += '\n g_statistics.indexed_geometry_checksum=checksum; return INDEXED_SUBMISSION_OK; }\n'
        with tempfile.TemporaryDirectory(prefix='renegade-index-') as folder:
            directory = Path(folder)
            (directory / 'production.inc').write_text('\n'.join([
                section('uint32_t Mix_Checksum(', 'void Log_Indexed_Rejection('),
                section('bool Build_Indexed_Transform_Matrices(', 'bool Map_Native_Pixel_To_Logical('), prefix]))
            (directory / 'test.cpp').write_text(r'''
#include "ww3d_vita_renderer.h"
#include <cstdio>
#include <cstring>
#include <cassert>
#include <vector>
namespace RenegadeVitaRenderer {
Statistics g_statistics={}; unsigned g_render_work_cache_mode=0;
void Log_Indexed_Rejection(const char*,uint32_t) {}
#include "production.inc"
}
using namespace RenegadeVitaRenderer;
int main() {
    std::vector<unsigned char> vertices(44*64);
    for (unsigned i=0;i<vertices.size();++i) vertices[i]=(i*13)%253;
    uint16_t indices[9]={0,1,2,2,1,3,3,4,0};
    float matrix[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    unsigned cases=0;
    for (unsigned layout=0;layout<2;++layout) for(unsigned scenario=0;scenario<15;++scenario) {
        IndexedTriangleSubmission s={};
        s.vertex_data=vertices.data(); s.vertex_data_size=vertices.size();
        s.vertex_capacity=64; s.vertex_stride=layout ? 44 : 36;
        s.vertex_format=layout ? 0x252 : 0x152;
        s.index_data=indices; s.index_capacity=9; s.triangle_count=3;
        s.vertex_count=5; s.world_transform=matrix; s.view_transform=matrix; s.projection_transform=matrix;
        if(scenario==1) s.vertex_capacity=4;
        if(scenario==2) s.first_index=8;
        if(scenario==3) s.base_vertex_index=61;
        if(scenario==4) s.min_vertex_index=1;
        if(scenario==5) s.vertex_count=UINT32_MAX;
        if(scenario==6) s.vertex_stride=20;
        if(scenario==7) s.index_data=nullptr;
        if(scenario==8) s.vertex_data_size=4;
        if(scenario==9) s.world_transform=nullptr;
        if(scenario==10) s.triangle_count=UINT32_MAX;
        if(scenario==11) s.min_vertex_index=UINT32_MAX;
        if(scenario==12) s.base_vertex_index=3;
        if(scenario==13) {s.first_index=3; s.triangle_count=2;}
        if(scenario==14) s.vertex_format=0;
        g_statistics={}; g_statistics.initialized=true;
        g_statistics.indexed_geometry_checksum=2166136261U;
        g_render_work_cache_mode=0;
        auto a=Submit_Indexed_Triangles(s); auto reference=g_statistics;
        g_statistics={}; g_statistics.initialized=true;
        g_statistics.indexed_geometry_checksum=2166136261U;
        g_render_work_cache_mode=8;
        assert(a==Submit_Indexed_Triangles(s));
        assert(reference.indexed_geometry_checksum==g_statistics.indexed_geometry_checksum);
        assert(reference.rejected_indexed_submissions==g_statistics.rejected_indexed_submissions);
        assert(reference.unsupported_submissions==g_statistics.unsupported_submissions);
        ++cases;
    }
    std::printf("indexed preparation equivalence PASS cases=%u\n",cases);
}
''')
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                '-D__vita__=1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                '-I'+folder, '-I'+str(ROOT / 'port/renderer/vita'), str(directory / 'test.cpp'),
                '-o', str(directory / 'test')], check=True)
            subprocess.run([str(directory / 'test')], check=True)


if __name__ == '__main__':
    unittest.main()
