"""Pure-Python checks for the Vita frame-pacing policy (frame-pacing-v1.flag).

No compiler is invoked. The behaviour tests run synthetic frame-time traces
through tools/frame_pacing_model.py, a line-for-line Python mirror of
port/renderer/vita/frame_pacing.h. The parity tests parse the C++ header and
fail if its constants, flag table, decision names, or the per-method order of
state mutations and decision results drift from the Python mirror. The wiring
tests pin how ww3d_vita_renderer.cpp drives the controller around
vglSwapBuffers.
"""
from collections import Counter
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import frame_pacing_model as fp  # noqa: E402

HEADER = ROOT / 'port/renderer/vita/frame_pacing.h'
MODEL = ROOT / 'tools/frame_pacing_model.py'
RENDERER = ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp'

VSYNC_US = 1000000.0 / 60.0
C = fp.Controller


# ---------------------------------------------------------------- trace model

def present_us(cpu_ms, gpu_ms, interval, frame):
    """Game-thread present-to-present time for a pipelined CPU/GPU frame.

    When the frame is cheaper than the swap interval the CPU blocks on display
    back-pressure, so the interval is the vsync quantum; otherwise the queue
    never fills and the CPU-side interval is the slower of CPU and GPU.
    """
    jitter = ((frame * 7919) % 11 - 5) * 40.0  # +-200 us, deterministic
    work_us = max(cpu_ms, gpu_ms) * 1000.0
    return int(max(work_us, interval * VSYNC_US) + jitter)


def busy_us(cpu_ms, frame):
    jitter = ((frame * 104729) % 7 - 3) * 50.0
    return int(cpu_ms * 1000.0 + jitter)


class Run:
    def __init__(self):
        self.transitions = 0
        self.frames_at = Counter()
        self.kinds = Counter()


def simulate(mode, frames, cost, suspend=lambda frame: False, controller=None):
    """cost(frame) -> (cpu_ms, gpu_ms) or a float present gap in ms (stall)."""
    c = controller or C()
    if controller is None:
        c.Reset(mode)
    run = Run()
    for frame in range(frames):
        interval = c.Interval()
        sample = cost(frame)
        if isinstance(sample, tuple):
            cpu_ms, gpu_ms = sample
            gap = present_us(cpu_ms, gpu_ms, interval, frame)
            busy = busy_us(cpu_ms, frame)
        else:
            gap = int(sample * 1000.0)
            busy = gap
        d = c.Record_Frame(gap, busy, suspend(frame))
        assert d.previous_interval == interval
        assert d.interval == c.Interval() and d.interval in (1, 2)
        run.kinds[d.kind] += 1
        if d.interval != d.previous_interval:
            run.transitions += 1
        run.frames_at[d.interval] += 1
    return run


def constant(cpu_ms, gpu_ms):
    return lambda frame: (cpu_ms, gpu_ms)


def max_failed_probes(windows):
    """Upper bound on failed 60 Hz probes in `windows` evaluations at 30 Hz:
    each needs UP_DWELL windows of headroom (or the lockout, if longer), one
    probation window, then locks out for BACKOFF_INITIAL doubling to MAX."""
    probes, lock, t = 0, C.BACKOFF_INITIAL, C.UP_DWELL + 1
    while t <= windows:
        probes += 1
        t += 1 + max(lock, C.UP_DWELL)
        lock = min(lock * 2, C.BACKOFF_MAX)
    return probes


# ------------------------------------------------------------ flag / cadence

class FlagAndCadenceTests(unittest.TestCase):
    def test_flag_grammar(self):
        cases = {
            b'RVFR1 off\n': fp.MODE_OFF,
            b'RVFR1 30\n': fp.MODE_LOCK30,
            b'RVFR1 auto\n': fp.MODE_ADAPTIVE,
        }
        for text, mode in cases.items():
            self.assertEqual(fp.Parse_Flag(text), mode, text)
        for text in (b'', b'RVFR1 30', b'RVFR1 30\r\n', b'RVFR1 60\n', b'RVFR1 AUTO\n',
                     b'RVFR0 30\n', b'RVFR1 \n', b'RVFR1  30\n', b'RVFR1 auto\n\n',
                     b'RVFR1 030\n', b'RVFR1 off \n', b'rvfr1 off\n', b'RVFR1 1\n'):
            self.assertIsNone(fp.Parse_Flag(text), text)
        self.assertIsNone(fp.Parse_Flag(None))
        self.assertEqual([fp.Mode_Name(m) for m in range(4)],
                         ['off', 'lock30', 'adaptive', 'off'])

    def test_cadence_counts_judder_as_changes(self):
        cad = fp.Cadence()
        for delta in [1] * 30:
            cad.Record(delta)
        self.assertEqual((cad.frames, cad.one, cad.changes), (30, 30, 0))
        cad.Reset()
        for delta in [2] * 30:
            cad.Record(delta)
        self.assertEqual((cad.two, cad.changes), (30, 1))  # Reset keeps the predecessor
        cad = fp.Cadence()
        for delta in [1, 2] * 15:
            cad.Record(delta)
        self.assertEqual((cad.one, cad.two, cad.changes), (15, 15, 29))
        cad = fp.Cadence()
        cad.Record(1)
        cad.Break()
        cad.Record(3)
        cad.Record(0)
        self.assertEqual((cad.zero, cad.one, cad.three_plus, cad.changes), (1, 1, 1, 1))

    def test_cadence_reset_keeps_predecessor(self):
        cad = fp.Cadence()
        cad.Record(1)
        cad.Reset()
        cad.Record(2)  # the 1 -> 2 change straddles the window boundary
        self.assertEqual((cad.frames, cad.changes), (1, 1))


# ------------------------------------------------------------- controller

class ControllerTests(unittest.TestCase):
    def test_off_never_touches_the_interval(self):
        for cost in (constant(10, 10), constant(25, 25), lambda f: 900.0):
            run = simulate(fp.MODE_OFF, 2000, cost, suspend=lambda f: f % 97 == 0)
            self.assertEqual(run.transitions, 0)
            self.assertEqual(run.frames_at[1], 2000)
            self.assertEqual(set(run.kinds), {fp.DECISION_NONE})
        self.assertEqual(C().Interval(), 1)

    def test_lock30_arms_after_steady_frames_and_holds(self):
        run = simulate(fp.MODE_LOCK30, 3000, constant(12, 12))
        self.assertEqual(run.transitions, 1)
        self.assertEqual(run.frames_at[1], C.ARM_FRAMES - 1)
        self.assertEqual(run.frames_at[2], 3000 - (C.ARM_FRAMES - 1))
        self.assertEqual(run.kinds[fp.DECISION_DOWN] + run.kinds[fp.DECISION_UP], 0)

    def test_lock30_even_when_content_is_slower_than_30(self):
        run = simulate(fp.MODE_LOCK30, 1000, constant(40, 20))
        self.assertEqual(run.transitions, 1)
        self.assertEqual(run.frames_at[2], 1000 - (C.ARM_FRAMES - 1))

    def test_stall_releases_and_rearms(self):
        stall_at = 500

        def cost(frame):
            return 450.0 if frame == stall_at else (14, 14)
        c = C()
        c.Reset(fp.MODE_LOCK30)
        kinds = []
        for frame in range(1000):
            sample = cost(frame)
            gap = int(sample * 1000) if not isinstance(sample, tuple) else \
                present_us(14, 14, c.Interval(), frame)
            d = c.Record_Frame(gap, busy_us(14, frame), False)
            if d.interval != d.previous_interval:
                kinds.append((frame, fp.Decision_Name(d.kind), d.previous_interval, d.interval))
        self.assertEqual(kinds, [
            (C.ARM_FRAMES - 1, 'arm', 1, 2),
            (stall_at, 'suspend', 2, 1),
            (stall_at + C.ARM_FRAMES, 'arm', 1, 2),
        ])

    def test_loading_bursts_never_arm(self):
        # Loading screen: one present plus three catch-up presents a vblank
        # apart per progress change, separated by long load work.
        def cost(frame):
            return 600.0 if frame % 4 == 0 else (2, 2)
        for mode in (fp.MODE_LOCK30, fp.MODE_ADAPTIVE):
            run = simulate(mode, 4000, cost)
            self.assertEqual(run.transitions, 0)
            self.assertEqual(run.frames_at[1], 4000)
            self.assertEqual(run.kinds[fp.DECISION_ARM], 0)

    def test_text_entry_suspends(self):
        run = simulate(fp.MODE_LOCK30, 2000, constant(10, 10),
                       suspend=lambda f: 800 <= f < 900)
        self.assertEqual(run.transitions, 3)  # arm, suspend, re-arm
        self.assertEqual(run.kinds[fp.DECISION_SUSPEND], 1)

    def test_adaptive_fast_content_stays_at_60(self):
        run = simulate(fp.MODE_ADAPTIVE, 6000, constant(10, 12))
        self.assertEqual(run.transitions, 0)
        self.assertEqual(run.frames_at[1], 6000)
        self.assertEqual(run.kinds[fp.DECISION_DOWN], 0)

    def test_adaptive_mid_content_locks_to_30_once(self):
        # 45 fps content: alternating 16.7/33.3 display with vsync at 60.
        run = simulate(fp.MODE_ADAPTIVE, 6000, constant(22, 18))
        self.assertEqual(run.transitions, 1)
        self.assertEqual(run.kinds[fp.DECISION_DOWN], 1)
        self.assertEqual(run.kinds[fp.DECISION_UP], 0)
        # Decided on the first full window after arming.
        self.assertEqual(run.frames_at[1], C.ARM_FRAMES - 1 + C.WINDOW)

    def test_adaptive_returns_to_60_after_sustained_headroom(self):
        heavy_frames = 1200

        def cost(frame):
            return (22, 18) if frame < heavy_frames else (9, 10)
        c = C()
        c.Reset(fp.MODE_ADAPTIVE)
        events = []
        for frame in range(6000):
            cpu, gpu = cost(frame)
            d = c.Record_Frame(present_us(cpu, gpu, c.Interval(), frame), busy_us(cpu, frame), False)
            if d.interval != d.previous_interval:
                events.append((fp.Decision_Name(d.kind), frame))
        self.assertEqual([k for k, _ in events], ['down', 'up'])
        # Up needs UP_DWELL full windows at 30 after the content got lighter.
        self.assertGreaterEqual(events[1][1] - heavy_frames, (C.UP_DWELL - 1) * C.WINDOW)
        self.assertLessEqual(events[1][1] - heavy_frames, (C.UP_DWELL + 1) * C.WINDOW)
        self.assertEqual(c.Interval(), 1)

    def test_adaptive_hold_band_between_thresholds(self):
        # At 30 the CPU busy p95 (15 ms) is above UP_BUSY_P95_US although 60
        # might just fit: hold at 30, no probing, no oscillation.
        def cost(frame):
            return (22, 18) if frame < 300 else (15, 15)
        run = simulate(fp.MODE_ADAPTIVE, 20000, cost)
        self.assertEqual(run.transitions, 1)
        self.assertEqual(run.kinds[fp.DECISION_UP], 0)

    def test_adaptive_gpu_bound_probes_are_backed_off(self):
        # CPU busy 9 ms looks like headroom at 30, but the hidden 24 ms GPU
        # cost misses 60 on every probe: reverted, locked out exponentially.
        frames = 60000
        run = simulate(fp.MODE_ADAPTIVE, frames, constant(9, 24))
        windows = frames // C.WINDOW
        probes = run.kinds[fp.DECISION_UP]
        self.assertEqual(run.kinds[fp.DECISION_REVERT_UP], probes)
        self.assertLessEqual(probes, max_failed_probes(windows))
        self.assertLessEqual(probes, 10)
        self.assertEqual(run.transitions, 1 + 2 * probes)
        self.assertGreaterEqual(run.frames_at[2] / frames, 0.97)

    def test_adaptive_adversarial_alternation_is_bounded(self):
        # Heavy and light content alternating every window.
        def cost(frame):
            return (22, 24) if (frame // C.WINDOW) % 2 else (8, 8)
        frames = 60000
        run = simulate(fp.MODE_ADAPTIVE, frames, cost)
        windows = frames // C.WINDOW
        # Never 3 headroom windows in a row at 30: at most the initial down.
        self.assertLessEqual(run.transitions, 2)
        # Light for 4 windows, heavy for 1: every probe meets a heavy window
        # inside probation, so probes back off like the GPU-bound case.
        def cost2(frame):
            return (22, 24) if (frame // C.WINDOW) % 5 == 4 else (8, 8)
        run2 = simulate(fp.MODE_ADAPTIVE, frames, cost2)
        self.assertEqual(run2.kinds[fp.DECISION_REVERT_UP], run2.kinds[fp.DECISION_UP])
        self.assertLessEqual(run2.transitions, 1 + 2 * max_failed_probes(windows))

    def test_down_after_probation_is_not_locked(self):
        # Heavy, then light long enough to pass probation, then heavy again,
        # then light: two ordinary down/up pairs and no lockout.
        def cost(frame):
            if frame < 600 or 2400 <= frame < 3000:
                return (22, 18)
            return (9, 10)
        c = C()
        c.Reset(fp.MODE_ADAPTIVE)
        events = []
        for frame in range(6000):
            cpu, gpu = cost(frame)
            d = c.Record_Frame(present_us(cpu, gpu, c.Interval(), frame), busy_us(cpu, frame), False)
            if d.interval != d.previous_interval:
                events.append((fp.Decision_Name(d.kind), d.up_lock))
        self.assertEqual(events, [('down', 0), ('up', 0), ('down', 0), ('up', 0)])

    def test_jitter_and_isolated_hitches_do_not_lock(self):
        # 60 Hz with +-0.8 ms jitter and two 40 ms hitches every window.
        c = C()
        c.Reset(fp.MODE_ADAPTIVE)
        for frame in range(6000):
            gap = int(VSYNC_US + ((frame * 31) % 17 - 8) * 100)
            if frame % C.WINDOW in (10, 40):
                gap = 40000
            d = c.Record_Frame(gap, 8000, False)
            self.assertEqual(d.interval, 1)
        # Three slow frames in a window (5%) reach p95 and lock.
        c.Reset(fp.MODE_ADAPTIVE)
        intervals = []
        for frame in range(C.ARM_FRAMES - 1 + 2 * C.WINDOW):
            gap = 40000 if frame % C.WINDOW in (10, 30, 50) else int(VSYNC_US)
            intervals.append(c.Record_Frame(gap, 8000, False).interval)
        self.assertEqual(intervals[-1], 2)

    def test_threshold_boundaries(self):
        def window(mode, target_interval, interval_value, busy_value):
            c = C()
            c.Reset(mode)
            for _ in range(C.ARM_FRAMES):
                c.Record_Frame(16000, 8000, False)
            if target_interval == 2:
                for _ in range(C.WINDOW):  # force down first
                    c.Record_Frame(40000, 30000, False)
                assert c.Interval() == 2
            d = None
            for _ in range(C.WINDOW):
                d = c.Record_Frame(interval_value, busy_value, False)
            return c, d
        _, d = window(fp.MODE_ADAPTIVE, 1, C.DOWN_P95_US, 8000)
        self.assertEqual(d.kind, fp.DECISION_HOLD)
        _, d = window(fp.MODE_ADAPTIVE, 1, C.DOWN_P95_US + 1, 8000)
        self.assertEqual(d.kind, fp.DECISION_DOWN)
        self.assertEqual(d.p95_interval_us, C.DOWN_P95_US + 1)
        c, d = window(fp.MODE_ADAPTIVE, 2, 33333, C.UP_BUSY_P95_US)
        self.assertEqual(d.headroom_windows, 1)
        c, d = window(fp.MODE_ADAPTIVE, 2, 33333, C.UP_BUSY_P95_US + 1)
        self.assertEqual(d.headroom_windows, 0)
        # Stall threshold is exclusive.
        c = C()
        c.Reset(fp.MODE_LOCK30)
        self.assertEqual(c.Record_Frame(C.STALL_US, 0, False).kind, fp.DECISION_NONE)
        for _ in range(C.ARM_FRAMES - 1):
            c.Record_Frame(C.STALL_US, 0, False)
        self.assertEqual(c.Interval(), 2)
        self.assertEqual(c.Record_Frame(C.STALL_US + 1, 0, False).kind, fp.DECISION_SUSPEND)

    def test_backoff_doubles_to_cap(self):
        c = C()
        c.Reset(fp.MODE_ADAPTIVE)
        locks = []
        for frame in range(400000):
            cpu, gpu = 9, 24
            d = c.Record_Frame(present_us(cpu, gpu, c.Interval(), frame), busy_us(cpu, frame), False)
            if d.kind == fp.DECISION_REVERT_UP:
                locks.append(d.up_lock)
        self.assertEqual(locks[:7], [4, 8, 16, 32, 64, 128, 256])
        self.assertTrue(all(lock == C.BACKOFF_MAX for lock in locks[6:]))

    def test_reset_rejects_unknown_mode(self):
        c = C()
        c.Reset(7)
        self.assertEqual(c.Mode(), fp.MODE_OFF)
        self.assertEqual(c.Record_Frame(16000, 8000, False).kind, fp.DECISION_NONE)

    def test_thresholds_sit_on_vsync_quanta(self):
        self.assertGreater(C.DOWN_P95_US, VSYNC_US)
        self.assertLess(C.DOWN_P95_US, 2 * VSYNC_US)
        self.assertLess(C.UP_BUSY_P95_US, VSYNC_US)
        self.assertGreater(C.STALL_US, 4 * 2 * VSYNC_US)
        self.assertEqual((C.WINDOW * 95) // 100, 57)


# ---------------------------------------------------- C++ / Python parity

def cpp_controller_section(text):
    start = text.index('class Controller {')
    return text[start:text.index('} // namespace RenegadeVitaFramePacing', start)]


def brace_body(text, signature):
    start = text.index(signature)
    open_at = text.index('{', start)
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[open_at:i + 1]
    raise AssertionError(signature)


def python_method(text, class_name, name):
    start = text.index('class %s' % class_name)
    start = text.index('    def %s(' % name, start)
    end = text.find('\n    def ', start + 1)
    nxt = text.find('\nclass ', start + 1)
    candidates = [x for x in (end, nxt) if x != -1]
    return text[start:min(candidates) if candidates else len(text)]


CONSTANTS = ('WINDOW', 'DOWN_P95_US', 'UP_BUSY_P95_US', 'UP_DWELL', 'PROBATION_WINDOWS',
             'STALL_US', 'ARM_FRAMES', 'BACKOFF_INITIAL', 'BACKOFF_MAX')
SYMBOL = r'\b(?:DECISION_[A-Z_]+|MODE_[A-Z0-9]+|%s)\b' % '|'.join(CONSTANTS)


def cpp_tokens(body):
    tokens = []
    for m in re.finditer(r'\b([a-z][a-z0-9_]*_)\b|(%s)' % SYMBOL, body):
        tokens.append((m.start(), m.group(1) or m.group(2)))
    return [t for _, t in tokens]


def py_tokens(body):
    tokens = []
    for m in re.finditer(r'self\._([a-z][a-z0-9_]*)\b|(%s)' % SYMBOL, body):
        tokens.append((m.start(), (m.group(1) + '_') if m.group(1) else m.group(2)))
    return [t for _, t in tokens]


def cpp_mutations(body):
    events = []
    for m in re.finditer(r'(?:\+\+|--)([a-z][a-z0-9_]*_)\b', body):
        events.append((m.start(), m.group(1)))
    for m in re.finditer(r'\b([a-z][a-z0-9_]*_)(?:\[[^\]]*\])?\s*=(?!=)', body):
        events.append((m.start(), m.group(1)))
    return [name for _, name in sorted(events)]


def py_mutations(body):
    return [m.group(1) + '_' for m in re.finditer(
        r'self\._([a-z][a-z0-9_]*)(?:\[[^\]]*\])?\s*(?:=(?!=)|\+=|-=)', body)]


def decisions(tokens):
    return [t for t in tokens if t.startswith('DECISION_')]


class ParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = HEADER.read_text()
        cls.model = MODEL.read_text()
        cls.controller = cpp_controller_section(cls.header)

    def test_constants_match(self):
        enum = self.controller[:self.controller.index('};')]
        values = dict(re.findall(r'(\w+) = (\d+)U', enum))
        self.assertEqual(set(values), set(CONSTANTS))
        for name in CONSTANTS:
            self.assertEqual(int(values[name]), getattr(C, name), name)
        modes = dict(re.findall(r'(MODE_\w+) = (\d+)U', self.header))
        self.assertEqual({k: int(v) for k, v in modes.items()},
                         {k: getattr(fp, k) for k in modes})
        self.assertEqual(len(modes), 4)

    def test_flag_table_and_names_match(self):
        entries = re.findall(r'\{"([^"]+)", (MODE_\w+)\}', self.header)
        self.assertEqual([(t, getattr(fp, m)) for t, m in entries], list(fp.FLAG_ENTRIES))
        self.assertIn('memcmp(data, "RVFR1 ", 6U)', self.header)
        self.assertIn('size < 8U', self.header)
        mode_names = re.findall(r'case (MODE_\w+): return "([^"]+)";', self.header)
        for mode, name in mode_names:
            self.assertEqual(fp.Mode_Name(getattr(fp, mode)), name)
        enum = self.header[self.header.index('enum DecisionKind {'):]
        enum = enum[:enum.index('};')]
        kinds = re.findall(r'\b(DECISION_[A-Z_]+)\b', enum)
        self.assertEqual([getattr(fp, k) for k in kinds], list(range(len(kinds))))
        names = re.findall(r'case (DECISION_\w+): return "([^"]+)";', self.header)
        self.assertEqual(len(names), len(kinds) - 1)
        for kind, name in names:
            self.assertEqual(fp.Decision_Name(getattr(fp, kind)), name)
        self.assertEqual(fp.Decision_Name(fp.DECISION_NONE), 'none')

    def test_methods_mirror_line_for_line(self):
        pairs = [
            ('void Reset(uint32_t mode)', 'Controller', 'Reset'),
            ('uint32_t Interval() const', 'Controller', 'Interval'),
            ('Decision Record_Frame(', 'Controller', 'Record_Frame'),
            ('static uint32_t P95(', 'Controller', '_P95'),
            ('void Lock_Up()', 'Controller', '_Lock_Up'),
            ('DecisionKind Decide(', 'Controller', '_Decide'),
        ]
        for signature, cls, name in pairs:
            cpp = brace_body(self.controller, signature)
            py = python_method(self.model, cls, name)
            ct, pt = cpp_tokens(cpp), py_tokens(py)
            self.assertEqual(Counter(ct), Counter(pt), name)
            self.assertEqual(decisions(ct), decisions(pt), name)
            self.assertEqual(cpp_mutations(cpp), py_mutations(py), name)
        cad_cpp = self.header[self.header.index('class Cadence {'):self.header.index('enum DecisionKind')]
        cad_py = self.model[self.model.index('class Cadence:'):self.model.index('DECISION_NONE = 0')]
        for name in ('Record', 'Break'):
            cpp = brace_body(cad_cpp, 'void %s(' % name)
            py = python_method(cad_py, 'Cadence', name)
            self.assertEqual(cpp_mutations(cpp), py_mutations(py), name)
            self.assertEqual(Counter(cpp_tokens(cpp)), Counter(py_tokens(py)), name)
        record_cpp = brace_body(cad_cpp, 'void Record(')
        self.assertEqual(re.findall(r'\+\+(\w+)', record_cpp),
                         ['frames', 'zero', 'one', 'two', 'three_plus', 'changes'])

    def test_header_is_platform_free(self):
        includes = re.findall(r'#include <([^>]+)>', self.header)
        self.assertEqual(includes, ['stddef.h', 'stdint.h', 'string.h'])
        self.assertNotIn('#include "', self.header)
        code = re.sub(r'//[^\n]*', '', self.header)
        for forbidden in ('psp2', 'vitaGL', 'gl', 'TimeManager', 'sce', 'egl'):
            self.assertNotIn(forbidden, code)


# --------------------------------------------------------- renderer wiring

class WiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = RENDERER.read_text()

    def function(self, signature):
        return brace_body(self.renderer, signature)

    def test_flag_read_after_vsync_choice(self):
        r = self.renderer
        self.assertIn('#include "frame_pacing.h"', r)
        self.assertIn('ux0:data/renegade/user/config/frame-pacing-v1.flag', r)
        init = r[r.index('bool Initialize()'):]
        self.assertLess(init.index('vglWaitVblankStart(vsync_enabled'),
                        init.index('Read_Frame_Pacing_Mode(vsync_enabled);'))
        read = self.function('void Read_Frame_Pacing_Mode(bool vsync_enabled)')
        self.assertIn('accepted && mode != MODE_OFF && !vsync_enabled', read)
        self.assertIn('g_frame_pacing.Reset(mode);', read)
        self.assertNotIn('eglSwapInterval', read)

    def test_end_frame_order(self):
        end_frame = self.function('void End_Frame(bool present)')
        before = end_frame.index('Frame_Pacing_Before_Present();')
        swap = end_frame.index('vglSwapBuffers(')
        after = end_frame.index('Frame_Pacing_After_Present();')
        resolution = end_frame.index('Update_Internal_Resolution_After_Present();')
        self.assertLess(before, swap)
        self.assertLess(swap, after)
        self.assertLess(after, resolution)

    def test_default_path_is_inert(self):
        after = self.function('void Frame_Pacing_After_Present()')
        statements = [line.strip() for line in after[1:].splitlines() if line.strip()]
        self.assertEqual(statements[:2], ['using namespace RenegadeVitaFramePacing;',
                                          'if (!g_frame_pacing_enabled) return;'])
        before = self.function('void Frame_Pacing_Before_Present()')
        self.assertIn('if (g_frame_pacing_enabled)', before)
        # The only swap-interval write, and never in "off"/observe mode.
        self.assertEqual(self.renderer.count('eglSwapInterval('), 1)
        guard = after.index('g_frame_pacing_mode != MODE_OFF')
        self.assertLess(guard, after.index('eglSwapInterval('))
        self.assertIn('decision.interval != g_frame_pacing_applied_interval', after)

    def test_simulation_time_untouched(self):
        glue_start = self.renderer.index('// frame-pacing-v1.flag (RVFR1')
        glue = self.renderer[glue_start:self.renderer.index(
            '// Defaults reproduce the shipped vitaGL/sceGxm sizes', glue_start)]
        glue = re.sub(r'//[^\n]*', '', glue)
        for forbidden in ('TimeManager', 'sceKernelDelayThread', 'sceDisplayWaitVblank',
                          'WW3D::Sync', 'Set_Time_Scale'):
            self.assertNotIn(forbidden, glue)
        self.assertIn('RenegadeVitaTextEntry::Active()', glue)
        self.assertIn('interval_us > Controller::STALL_US', glue)

    def test_transition_logging_is_sparse(self):
        after = self.function('void Frame_Pacing_After_Present()')
        self.assertIn('g_frame_pacing_transitions <= 32U || (g_frame_pacing_transitions % 32U) == 0U', after)
        self.assertIn('g_frame_pacing_cadence.frames >= 1200U', after)


if __name__ == '__main__':
    unittest.main()
