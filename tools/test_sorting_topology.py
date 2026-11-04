"""Exercise the production sorting index translation without a render loop."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SortingTopologyTests(unittest.TestCase):
    def test_winding_anchor_rebase_and_invalid_range(self):
        text = (ROOT / 'port/renderer/vita/ww3d_dx8_boundary.cpp').read_text()
        start = text.index('for (unsigned i = 0U; i < index_count; ++i)',
                           text.index('void DX8Wrapper::Draw_Sorting_IB_VB'))
        end = text.index('\n\t}\n\n\tSet_Vertex_Buffer', start)
        body = text[start:end]
        start = text.index('const unsigned output_index_count',
                           text.index('void DX8Wrapper::Draw_Sorting_IB_VB'))
        capacity = text[start:text.index('const unsigned source_index_offset', start)]
        code = r'''
#include <cassert>
#include <cstdint>
#include <vector>
enum { D3DPT_TRIANGLELIST, D3DPT_TRIANGLESTRIP, D3DPT_TRIANGLEFAN };
const unsigned dynamic_fvf_type = 0;
bool rejected;
namespace RenegadeVitaRenderer {
void Reject_Indexed_Submission(const char *, unsigned) { rejected = true; }
}
void admit(unsigned primitive_type, unsigned polygon_count, unsigned index_count) {
'''+capacity+r'''
}
void translate(unsigned primitive_type, const unsigned short *source,
    unsigned short *destination, unsigned index_count, unsigned polygon_count,
    unsigned min_vertex_index, unsigned vertex_count) {
'''+body+r'''
}
int main() {
    // Every possible 16-bit polygon count must fit the expanded buffer or
    // reject before allocating/accessing its source. Oracle uses 64-bit sizes.
    for (unsigned count=1; count<=65535; ++count) {
        for (unsigned topology: {D3DPT_TRIANGLELIST, D3DPT_TRIANGLESTRIP, D3DPT_TRIANGLEFAN}) {
            unsigned input = topology==D3DPT_TRIANGLELIST ? count*3U : count+2U;
            uint64_t required = topology==D3DPT_TRIANGLESTRIP ? uint64_t(count)+2 : uint64_t(count)*3;
            rejected=false;
            admit(topology,count,input);
            assert(rejected == (required>65535));
        }
    }
    rejected=false;
    // Non-monotonic indices catch accidental sequential triangulation/reversal.
    const unsigned short vertices[] = {105, 103, 107, 104, 106};
    unsigned short output[9] = {};
    translate(D3DPT_TRIANGLEFAN, vertices, output, 5, 3, 100, 8);
    const unsigned short expected[] = {5,3,7, 5,7,4, 5,4,6};
    for (unsigned i=0; i<9; ++i) assert(output[i] == expected[i]);
    assert(!rejected);
    for (unsigned topology: {D3DPT_TRIANGLELIST, D3DPT_TRIANGLESTRIP}) {
        translate(topology, vertices, output, 3, 1, 100, 8);
        for (unsigned i=0; i<3; ++i) assert(output[i] == vertices[i]-100);
    }
    // Declared range excludes either the anchor or an outer vertex.
    for (unsigned minimum: {104U, 106U}) {
        rejected=false;
        translate(D3DPT_TRIANGLEFAN, vertices, output, 5, 3, minimum, 2);
        assert(rejected);
    }
    const unsigned short high[] = {65535,65533,65534};
    rejected=false;
    translate(D3DPT_TRIANGLEFAN, high, output, 3, 1, 65533, 3);
    assert(!rejected && output[0]==2 && output[1]==0 && output[2]==1);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'topology.cpp'
            source.write_text(code)
            exe = Path(directory) / 'topology'
            subprocess.run(['g++', '-std=c++17', '-fsanitize=address,undefined',
                            str(source), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
