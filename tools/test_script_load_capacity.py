"""Compile the staged original Load_Data body against a bounded chunk seam."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from contextlib import nullcontext

from tools.audit_missing_definition_callers import body

ROOT = Path(__file__).resolve().parents[1]


class ScriptLoadCapacityTests(unittest.TestCase):
    def test_original_boundary_without_assertions(self):
        implementation, _ = body((ROOT / 'staging/combat/scriptcommands.cpp').read_text(),
                                 'Load_Data', 'ScriptLoader')
        prefix = r'''
#include <cassert>
#include <cstdio>
#include <cstring>
struct ChunkSeam {
    unsigned length = 4, reads = 0, errors = 0;
    unsigned char bytes[4] = {10,20,30,40};
    unsigned Cur_Micro_Chunk_Length() { return length; }
    void Report_Error() { ++errors; }
    void Read(void *data, unsigned size) { ++reads; assert(size <= 4); memcpy(data, bytes, size); }
};
struct ScriptLoader { ChunkSeam CLoad; };
#define SCRIPT_PTR_CHECK(data) if ((data) == nullptr) return
#define WWASSERT(condition) ((void)0)
void Load_Data(ScriptLoader &loader, int size, void *data)
'''
        suffix = r'''
int main() {
    ScriptLoader loader;
    unsigned char data[8] = {1,2,3,4,5,6,7,8};
    Load_Data(loader, 8, data);
    assert(loader.CLoad.reads == 1 && data[0] == 10 && data[4] == 5);
    loader.CLoad.reads = 0;
    data[0] = 1;
    Load_Data(loader, 2, data);
    assert(loader.CLoad.reads == 0 && data[0] == 1 && loader.CLoad.errors == 1);
    Load_Data(loader, -1, data);
    assert(loader.CLoad.reads == 0 && data[0] == 1 && loader.CLoad.errors == 2);
    Load_Data(loader, 4, nullptr);
    assert(loader.CLoad.reads == 0 && loader.CLoad.errors == 3);
    Load_Data(loader, 4, data);
    assert(loader.CLoad.reads == 1 && data[3] == 40);
    loader.CLoad.length = 0;
    Load_Data(loader, 0, data);
    assert(loader.CLoad.reads == 2 && data[0] == 10);
    puts("Original Load_Data capacity: 6 cases with WWASSERT disabled PASS");
}
'''
        retained = os.environ.get('RENEGADE_SCRIPT_LOAD_PROBE_DIRECTORY')
        if retained:
            Path(retained).mkdir(parents=True, exist_ok=True)
        context = nullcontext(retained) if retained else tempfile.TemporaryDirectory()
        with context as directory:
            path = Path(directory)
            source, executable = path / 'capacity.cpp', path / 'capacity'
            source.write_text(prefix + implementation + suffix)
            command = ['c++', '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
                       '-fno-sanitize-recover=all', str(source), '-o', str(executable)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            if retained:
                (path / 'compile.log').write_text(result.stdout + result.stderr)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(executable)], cwd=ROOT, capture_output=True, text=True)
            if retained:
                (path / 'runtime.log').write_text(result.stdout + result.stderr)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('6 cases with WWASSERT disabled PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
