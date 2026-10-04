"""Run original material task/queue bodies with observable host boundaries.

Allocator, material and mesh observers are test doubles. This verifies the
original queue's retention, FIFO and flush contract, not native draw execution.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProceduralMaterialQueueTest(unittest.TestCase):
    def test_original_retention_order_flush_and_reuse(self):
        source = (ROOT / 'staging/ww3d2/dx8renderer.cpp').read_text()
        start = source.index('class MatPassTaskClass :')
        task = source[start:source.index('DEFINE_AUTO_POOL(MatPassTaskClass', start)]
        start = source.index('void DX8FVFCategoryContainer::Add_Visible_Material_Pass(')
        end = source.index('void DX8RigidFVFCategoryContainer::Render_Delayed_Procedural_Material_Passes(', start)
        brace = source.index('{', end)
        depth = 1
        end = brace + 1
        while depth:
            depth += (source[end] == '{') - (source[end] == '}')
            end += 1
        queues = source[start:end]
        prefix = r'''
#include <cassert>
#include <cstddef>
#include <vector>
#define WWASSERT(x) assert(x)
#define SNAPSHOT_SAY(x) ((void)0)
template<class T, int N> class AutoPoolClass {};
struct IndexBufferClass {};
struct VertexBufferClass {};
static std::vector<int> events;
struct MaterialPassClass {
    int refs = 1;
    int id;
    explicit MaterialPassClass(int value): id(value) {}
    void Add_Ref() { ++refs; }
    void Release_Ref() { assert(refs > 1); --refs; }
};
struct MeshClass {
    int refs = 1;
    void Add_Ref() { ++refs; }
    void Release_Ref() { assert(refs > 1); --refs; }
    void Render_Material_Pass(MaterialPassClass *pass, IndexBufferClass *buffer) {
        assert(buffer != nullptr && refs > 1 && pass->refs > 1);
        events.push_back(pass->id);
    }
};
struct DX8Wrapper {
    static void Set_Vertex_Buffer(VertexBufferClass *v) { assert(v); events.push_back(-1); }
    static void Set_Index_Buffer(IndexBufferClass *v, int offset) { assert(v && !offset); events.push_back(-2); }
};
'''
        types = r'''
struct DX8FVFCategoryContainer {
    MatPassTaskClass *visible_matpass_head = nullptr, *visible_matpass_tail = nullptr;
    IndexBufferClass *index_buffer;
    bool AnythingToRender = false;
    explicit DX8FVFCategoryContainer(IndexBufferClass *buffer): index_buffer(buffer) {}
    void Add_Visible_Material_Pass(MaterialPassClass *, MeshClass *);
    void Render_Procedural_Material_Passes();
};
struct DX8RigidFVFCategoryContainer: DX8FVFCategoryContainer {
    MatPassTaskClass *delayed_matpass_head = nullptr, *delayed_matpass_tail = nullptr;
    VertexBufferClass *vertex_buffer;
    bool AnyDelayedPassesToRender = false;
    DX8RigidFVFCategoryContainer(IndexBufferClass *ib, VertexBufferClass *vb):
        DX8FVFCategoryContainer(ib), vertex_buffer(vb) {}
    bool Any_Delayed_Passes_To_Render() const { return AnyDelayedPassesToRender; }
    void Add_Delayed_Visible_Material_Pass(MaterialPassClass *, MeshClass *);
    void Render_Delayed_Procedural_Material_Passes();
};
'''
        checks = r'''
int main() {
    IndexBufferClass ib; VertexBufferClass vb;
    MeshClass mesh;
    MaterialPassClass a(1), b(2), c(3), d(4);
    DX8RigidFVFCategoryContainer queue(&ib, &vb);
    queue.Render_Procedural_Material_Passes();
    queue.Render_Delayed_Procedural_Material_Passes();
    assert(events.empty());
    for (int cycle = 0; cycle < 3; ++cycle) {
        events.clear();
        queue.Add_Visible_Material_Pass(&a, &mesh);
        queue.Add_Visible_Material_Pass(&b, &mesh);
        queue.Add_Delayed_Visible_Material_Pass(&c, &mesh);
        queue.Add_Delayed_Visible_Material_Pass(&d, &mesh);
        assert(mesh.refs == 5 && a.refs == 2 && b.refs == 2 && c.refs == 2 && d.refs == 2);
        assert(queue.AnythingToRender && queue.AnyDelayedPassesToRender);
        queue.Render_Procedural_Material_Passes();
        assert((events == std::vector<int>{1,2}));
        assert(mesh.refs == 3 && a.refs == 1 && b.refs == 1 && c.refs == 2 && d.refs == 2);
        assert(!queue.visible_matpass_head && !queue.visible_matpass_tail);
        queue.Render_Delayed_Procedural_Material_Passes();
        assert((events == std::vector<int>{1,2,-1,-2,3,4}));
        assert(mesh.refs == 1 && c.refs == 1 && d.refs == 1);
        assert(!queue.delayed_matpass_head && !queue.delayed_matpass_tail && !queue.AnyDelayedPassesToRender);
        auto count = events.size();
        queue.Render_Procedural_Material_Passes();
        queue.Render_Delayed_Procedural_Material_Passes();
        assert(events.size() == count);
    }
}
'''
        with tempfile.TemporaryDirectory(prefix='renegade-original-material-') as folder:
            path = Path(folder)
            cpp = path / 'queue.cpp'
            cpp.write_text(prefix + task + types + queues + checks)
            binary = path / 'queue'
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            str(cpp), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, env={**os.environ,
                           'ASAN_OPTIONS': 'detect_leaks=1:halt_on_error=1',
                           'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'})
            arm = Path('/usr/local/vitasdk/bin/arm-vita-eabi-g++')
            if arm.exists():
                subprocess.run([str(arm), '-std=c++17', '-O1', '-Wall', '-Wextra', '-Werror',
                                '-mcpu=cortex-a9', '-mfpu=neon', '-mfloat-abi=hard',
                                '-include', str(ROOT / 'port/compatibility/include/renegade_target_abi.h'),
                                '-c', str(cpp), '-o', str(path / 'queue.arm.o')], check=True)


if __name__ == '__main__':
    unittest.main()
