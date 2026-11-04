"""Execute production source-window admission against a wide-arithmetic oracle."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SortingWindowTests(unittest.TestCase):
    def test_vertex_and_index_windows(self):
        source = (ROOT / 'port/renderer/vita/ww3d_dx8_boundary.cpp').read_text()
        start = source.index('const unsigned source_vertex_offset')
        vertex = source[start:source.index('\n\tDynamicVBAccessClass dynamic_vertices', start)]
        start = source.index('const unsigned source_index_offset')
        index = source[start:source.index('\n\tDynamicIBAccessClass dynamic_indices', start)]
        code = r'''
#include <cassert>
#include <cstdint>
struct Buffer {
    unsigned capacity;
    unsigned Get_Vertex_Count() const { return capacity; }
    unsigned Get_Index_Count() const { return capacity; }
};
struct State { Buffer *vertex_buffer, *index_buffer; unsigned short vba_offset, index_base_offset, iba_offset; } render_state;
bool rejected;
const unsigned dynamic_fvf_type=0;
namespace RenegadeVitaRenderer { void Reject_Indexed_Submission(const char*, unsigned) { rejected=true; } }
'''
        code += 'void vertex(unsigned short min_vertex_index, unsigned short vertex_count) {\n' + vertex + '\n}\n'
        code += 'void index(unsigned short start_index, unsigned index_count) {\n' + index + '\n}\n'
        code += r'''
int main() {
    const unsigned values[]={0,1,2,31,32,63,64,65534,65535};
    Buffer b;
    render_state.vertex_buffer=render_state.index_buffer=&b;
    for (unsigned cap:values) for (unsigned a:values) for (unsigned c:values)
    for (unsigned count:values) {
        b.capacity=cap; render_state.vba_offset=a;
        render_state.index_base_offset=c; render_state.iba_offset=a;
        rejected=false; vertex(c,count);
        assert(rejected == (uint64_t(a)+c+c+count>cap));
        rejected=false; index(c,count);
        assert(rejected == (uint64_t(a)+c+count>cap));
    }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            cpp = Path(directory) / 'windows.cpp'
            cpp.write_text(code)
            exe = Path(directory) / 'windows'
            subprocess.run(['g++', '-std=c++17', '-fsanitize=address,undefined', str(cpp), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
