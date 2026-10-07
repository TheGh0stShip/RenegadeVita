"""Compile the render-sort-v1 planner header on the host and compare it with
the Python reference model (tools/vita_opaque_sort_model.py).

This test invokes g++ (with ASan/UBSan by default, like the other renderer
data-model tests). The pure-Python rule, raster and wiring checks live in
tools/test_vita_opaque_sort.py.
"""
from pathlib import Path
import os
import random
import subprocess
import tempfile
import unittest

from tools import vita_opaque_sort_model as model

ROOT = Path(__file__).resolve().parents[1]


def fixtures(seed=4242, count=300):
    rng = random.Random(seed)
    result = []
    for _ in range(count):
        slots = []
        for item in range(rng.randrange(1, 40)):
            passes = rng.randrange(1, 4)
            for current in range(passes):
                for _ in range(rng.randrange(1, 4)):
                    slots.append({'item': item, 'pass': current,
                                  'tex0': rng.randrange(-1, 6), 'tex1': rng.choice((-1, -1, 2)),
                                  'mat': rng.randrange(-1, 3), 'shader': rng.randrange(3),
                                  'detail': rng.random() < 0.2})
        result.append(slots)
    return result


class OpaqueSortNativeTests(unittest.TestCase):
    def test_header_matches_model(self):
        flags = ['-O2']
        if os.environ.get('RENEGADE_MESH_SANITIZE', '1') == '1':
            flags = ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        cases = fixtures()
        entries = []
        rng = random.Random(77)
        for _ in range(500):
            entry = [(rng.randrange(0, 3), rng.randrange(0, 4)) for _ in range(rng.randrange(0, 6))]
            if rng.random() < 0.8:
                entry.sort(key=lambda batch: batch[0])  # mostly build order
            entries.append(entry)
        lines = ['C']
        for entry in entries:
            lines.append('E %d %s' % (len(entry), ' '.join('%d %d' % batch for batch in entry)))
        for slots in cases:
            lines.append('F %d' % len(slots))
            for s in slots:
                lines.append('%d %d %d %d %d %d %d' % (s['item'], s['pass'], s['tex0'], s['tex1'],
                                                       s['mat'], s['shader'], int(s['detail'])))
        with tempfile.TemporaryDirectory(prefix='renegade-opaque-sort-') as folder:
            binary = Path(folder) / 'test'
            subprocess.run(['g++', '-std=c++17', *flags, '-Wall', '-Wextra', '-Werror',
                            '-I' + str(ROOT / 'port/renderer/vita'),
                            str(ROOT / 'tools/vita_opaque_sort_test.cpp'), '-o', str(binary)],
                           check=True)
            env = dict(os.environ, UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            completed = subprocess.run([str(binary)], input='\n'.join(lines) + '\n', check=True,
                                       capture_output=True, text=True, env=env, timeout=600)
        output = completed.stdout.splitlines()
        table = [line for line in output if line.startswith('C ')]
        self.assertEqual(len(table), 2 * 2 * 2 * 2 * 8)
        for line in table:
            blend, depth_write, color_write, alpha_test, compare, cls = map(int, line.split()[1:])
            self.assertEqual(cls, model.classify(bool(blend), bool(depth_write), bool(color_write),
                                                 bool(alpha_test), compare), line)
        eligibility = [line for line in output if line.startswith('E ')]
        self.assertEqual(len(eligibility), len(entries))
        for line, entry in zip(eligibility, entries):
            expected = model.entry_eligible([{'pass': p, 'cls': c} for p, c in entry])
            self.assertEqual(int(line.split()[1]), int(expected), entry)
        plans = [line for line in output if line.startswith('P ')]
        self.assertEqual(len(plans), len(cases) * len(model.MODES))
        for index, slots in enumerate(cases):
            for mode in model.MODES:
                line = plans[index * len(model.MODES) + mode].split()
                self.assertEqual(int(line[1]), mode)
                self.assertEqual([int(v) for v in line[2:]], model.plan(mode, slots),
                                 (index, mode))


if __name__ == '__main__':
    unittest.main()
