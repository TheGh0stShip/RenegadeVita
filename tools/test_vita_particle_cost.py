"""Pin particle-cost-v1 (RVPE1) and prove its exactness on a reference model.

Pure Python: no compiler, emulator or device. The model transcribes the
original ParticleBufferClass circular buffer (Get_New_Particles,
Kill_Old_Particles), Update_Visual_Particle_State, Generate_APT,
Combine_Color_And_Alpha (including the aliased in-place Clamp) and the
values PointGroupClass reads through the active point table. It replays
randomized emission, lifetimes, LOD decimation thresholds (including two
renders per frame and cloned buffers with fewer than 17 LOD levels) and
checks:

* bit 0 (exact decimation) never changes a value the point group reads;
* bit 1 only changes cloned small buffers at their lowest LOD, where the
  original draws stale or never-computed state, and then yields the fresh
  keyframe values;
* the C++ skip branch walks the same keyframe cursors, in the same order, as
  the original evaluation, and the patch is registered and reproducible.
"""
from pathlib import Path
import random
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / 'staging/ww3d2/part_buf.cpp'
PATCH = ROOT / 'port/patches/ww3d2-tut1-particle-cost.patch'
HEADER = ROOT / 'port/compatibility/include/renegade_vita_particle_cost.h'
STAGE_SCRIPT = ROOT / 'tools/stage_sources.sh'

PERMUTATION = [11, 3, 7, 14, 0, 13, 1, 2, 5, 12, 15, 6, 9, 8, 4, 10]
EXACT, DRAWN, TELEMETRY = 1, 2, 4
UNSET = None  # a slot the visual update never wrote (heap garbage on Vita)


class Track:
    """One keyframed property: times[0] == 0, ascending (part_buf Reset_*)."""

    def __init__(self, rng, max_age, width):
        count = rng.randint(1, 4)
        times = sorted(rng.sample(range(1, max(2, max_age)), min(count - 1, max(0, max_age - 2))))
        self.times = [0] + times
        self.values = [[rng.uniform(-0.5, 1.5) for _ in range(width)] for _ in self.times]
        self.deltas = [[rng.uniform(-0.01, 0.01) for _ in range(width)] for _ in self.times]
        mask = rng.choice([0, 1, 3, 7, 15, 31])
        self.random = [[rng.uniform(-0.2, 0.2) for _ in range(width)] for _ in range(mask + 1)]
        self.mask = mask

    def walk(self, key, age):
        while age < self.times[key]:
            key -= 1
        return key

    def value(self, key, age, part):
        return tuple(v + d * (age - self.times[key]) + r for v, d, r in
                     zip(self.values[key], self.deltas[key], self.random[part & self.mask]))


class Buffer:
    def __init__(self, rng, max_num, lod_count, properties):
        self.max_num = max_num
        self.lod_count = lod_count
        self.max_age = rng.randint(40, 400)
        self.start = self.end = self.new_end = 0
        self.non_new = self.new_num = 0
        self.timestamp = [0] * max_num
        self.queue = []
        self.tracks = {name: Track(rng, self.max_age, 3 if name == 'color' else 1)
                       for name in properties}
        self.arrays = {name: [UNSET] * max_num for name in properties}
        self.diffuse = [UNSET] * max_num
        self.decimation = 0

    # --- kinematic state (flag independent) -------------------------------
    def emit(self, timestamps):
        for stamp in timestamps:
            self.queue.append(stamp)
            if len(self.queue) == self.max_num + 1:
                self.queue.pop(0)

    def get_new_particles(self, now):
        for stamp in self.queue:
            self.timestamp[self.new_end] = stamp
            if now - stamp >= self.max_age:
                continue
            self.new_end = (self.new_end + 1) % self.max_num
            self.new_num += 1
            if self.new_num + self.non_new == self.max_num + 1:
                self.start = (self.start + 1) % self.max_num
                self.non_new -= 1
                if self.non_new == -1:
                    self.end = (self.end + 1) % self.max_num
                    self.non_new = 0
                    self.new_num -= 1
        self.queue = []

    def ranges(self):
        if self.start < self.end or (self.start == self.end and self.non_new == 0):
            return (self.start, self.end), (self.end, self.end)
        return (self.start, self.max_num), (0, self.end)

    def kill_old_particles(self, now):
        (a, b), (c, d) = self.ranges()
        broke = False
        i = a
        while i < b:
            if now - self.timestamp[i] < self.max_age:
                broke = True
                break
            self.non_new -= 1
            i += 1
        if not broke:
            i = c
            while i < d:
                if now - self.timestamp[i] < self.max_age:
                    break
                self.non_new -= 1
                i += 1
        self.start = i

    def update_kinematics(self, now):
        self.get_new_particles(now)
        self.kill_old_particles(now)
        self.end = self.new_end
        self.non_new += self.new_num
        self.new_num = 0

    # --- visual state (the code RVPE1 touches) ----------------------------
    def update_visual(self, now, mode):
        decimation = self.decimation if mode & EXACT else 0
        keys = {name: len(track.times) - 1 for name, track in self.tracks.items()}
        for lo, hi in self.ranges():
            for part in range(lo, hi):
                age = now - self.timestamp[part]
                skip = decimation != 0 and PERMUTATION[part & 0xF] < decimation
                for name, track in self.tracks.items():
                    keys[name] = track.walk(keys[name], age)
                    if not skip:
                        self.arrays[name][part] = track.value(keys[name], age, part)

    def generate_apt(self):
        if self.non_new < self.max_num or self.decimation > 0:
            if self.start < self.end or (self.start == self.end and self.non_new == 0):
                spans = [(self.start, self.end)]
            else:
                spans = [(0, self.end), (self.start, self.max_num)]
            return [i for lo, hi in spans for i in range(lo, hi)
                    if PERMUTATION[i & 0xF] >= self.decimation]
        return list(range(self.non_new))

    def combine(self, mode):
        color, alpha = self.arrays.get('color'), self.arrays.get('alpha')
        if color is None and alpha is None:
            return
        spans = [(0, self.max_num)]
        if mode & EXACT:
            (a, b), (c, d) = self.ranges()
            spans = [(a, b), (c, d)]
        for lo, hi in spans:
            for i in range(lo, hi):
                rgb = color[i] if color is not None else (1.0, 1.0, 1.0)
                a_ = alpha[i] if alpha is not None else (1.0,)
                if rgb is UNSET or a_ is UNSET:
                    self.diffuse[i] = UNSET
                    continue
                # VectorProcessorClass::Clamp with dst == src: min then max.
                self.diffuse[i] = tuple(min(max(v, 0.0), 1.0) for v in (*rgb, a_[0]))

    def render(self, now, mode):
        original = self.decimation < self.lod_count - 1
        drawable = self.decimation < 16
        if original or (drawable and mode & DRAWN):
            self.update_visual(now, mode)
        apt = self.generate_apt()
        self.combine(mode)
        consumed = []
        for i in apt:
            row = [self.diffuse[i] if ('color' in self.arrays or 'alpha' in self.arrays) else 'default']
            for name in ('size', 'orientation', 'frame'):
                if name in self.arrays:
                    row.append(self.arrays[name][i])
            consumed.append((i, tuple(row)))
        return consumed

    def fresh(self, now, apt_rows):
        """Values a full, undecimated evaluation would give the drawn slots."""
        out = []
        for i, _ in apt_rows:
            age = now - self.timestamp[i]
            vals = {name: track.value(track.walk(len(track.times) - 1, age), age, i)
                    for name, track in self.tracks.items()}
            row = []
            if 'color' in vals or 'alpha' in vals:
                rgb = vals.get('color', (1.0, 1.0, 1.0))
                a_ = vals.get('alpha', (1.0,))
                row.append(tuple(min(max(v, 0.0), 1.0) for v in (*rgb, a_[0])))
            else:
                row.append('default')
            for name in ('size', 'orientation', 'frame'):
                if name in vals:
                    row.append(vals[name])
            out.append((i, tuple(row)))
        return out


def scenario(seed, mode, monotonic=True):
    rng = random.Random(seed)
    max_num = rng.choice([2, 3, 4, 8, 9, 12, 16, 17, 21, 40, 100])
    cloned = rng.random() < 0.5
    lod_count = min(max_num, 17) if cloned else 17
    properties = rng.sample(['color', 'alpha', 'size', 'orientation', 'frame'], rng.randint(1, 5))
    buf = Buffer(rng, max_num, lod_count, properties)
    now = 1000
    frames = []
    for _ in range(rng.randint(30, 90)):
        dt = rng.randint(1, 60)
        stamps = sorted(rng.randint(now, now + dt) for _ in range(rng.randint(0, 6)))
        if not monotonic:
            rng.shuffle(stamps)
        now += dt
        buf.emit(stamps)
        buf.update_kinematics(now)
        renders = []
        for _ in range(rng.choice([1, 1, 2])):
            # The optimizer leaves DecimationThreshold in [0, LodCount - 1].
            buf.decimation = rng.choice([0, lod_count - 1, rng.randint(0, lod_count - 1)])
            rows = buf.render(now, mode)
            renders.append((buf.decimation, rows, buf.fresh(now, rows)))
        frames.append(renders)
    return lod_count, frames


class ReferenceModelTests(unittest.TestCase):
    SEEDS = range(120)

    def test_exact_decimation_preserves_every_consumed_value(self):
        for seed in self.SEEDS:
            for monotonic in (True, False):
                _, base = scenario(seed, 0, monotonic)
                _, exact = scenario(seed, EXACT, monotonic)
                _, exact_t = scenario(seed, EXACT | TELEMETRY, monotonic)
                self.assertEqual(
                    [[rows for _, rows, _ in f] for f in base],
                    [[rows for _, rows, _ in f] for f in exact], (seed, monotonic))
                self.assertEqual(exact, exact_t)

    def test_drawn_visual_state_changes_only_clone_lowest_lod(self):
        stale_seen = corrected = 0
        for seed in self.SEEDS:
            lod_count, base = scenario(seed, 0)
            _, drawn = scenario(seed, DRAWN)
            _, both = scenario(seed, DRAWN | EXACT)
            self.assertEqual([[r for _, r, _ in f] for f in drawn],
                             [[r for _, r, _ in f] for f in both], seed)
            for frame_base, frame_drawn in zip(base, drawn):
                for (dt, rows_base, fresh), (_, rows_drawn, _) in zip(frame_base, frame_drawn):
                    if lod_count == 17 or dt < lod_count - 1:
                        self.assertEqual(rows_base, rows_drawn, seed)
                        continue
                    # Original skips the update but still draws slots whose
                    # permutation entry reaches DecimationThreshold.
                    self.assertEqual(rows_drawn, fresh, seed)
                    if rows_base:
                        stale_seen += 1
                        corrected += rows_base != rows_drawn
        self.assertGreater(stale_seen, 0)
        self.assertGreater(corrected, 0)

    def test_full_lod_buffers_draw_fresh_values_in_every_mode(self):
        for seed in range(60):
            for mode in (0, EXACT, DRAWN, EXACT | DRAWN):
                lod_count, frames = scenario(seed, mode)
                for renders in frames:
                    for dt, rows, fresh in renders:
                        if dt < lod_count - 1 or mode & DRAWN:
                            self.assertEqual(rows, fresh, (seed, mode))


def _function(source, signature):
    start = source.index(signature)
    end = source.index('\n}\n', start)
    return source[start:end + 2]


class SourceContractTests(unittest.TestCase):
    def setUp(self):
        self.source = STAGED.read_text(encoding='utf-8', errors='replace')

    def test_skip_branch_walks_the_original_cursors_in_order(self):
        body = _function(self.source, 'void ParticleBufferClass::Update_Visual_Particle_State(void)')
        walk = re.compile(r'for \(; part_age < (\w+)\[(\w+)\]; (\w+)--\);')
        first = body.index('for (part = Start; part < sub1_end; part++) {')
        second = body.index('for (part = sub2_start; part < End; part++) {')
        skip_open = 'if (decimation != 0U && PermutationArray[part & 0xF] < decimation) {'
        skip_close = 'skipped++;\n\t\t\tcontinue;\n\t\t}'
        for loop in (body[first:second], body[second:]):
            self.assertEqual(loop.count(skip_open), 1)
            branch_start = loop.index(skip_open)
            branch_end = loop.index(skip_close, branch_start)
            branch = loop[branch_start:branch_end]
            evaluation = loop[branch_end + len(skip_close):]
            got = [m.groups() for m in walk.finditer(branch)]
            expected = [m.groups() for m in walk.finditer(evaluation)]
            self.assertEqual(len(got), 7)
            self.assertEqual(got, expected, 'skip-branch walks must mirror evaluation walks')
            for _, key, decremented in got:
                self.assertEqual(key, decremented)
            # The skip precedes every visual-array store in the loop body.
            self.assertNotIn('[part] =', branch)
            self.assertLess(loop.index(skip_open), loop.index('color[part] ='))
        self.assertIn('const unsigned int decimation =\n\t\t(Particle_Cost_Mode() & RenegadeVitaParticleCost::EXACT_DECIMATION) != 0U ? DecimationThreshold : 0U;', body)

    def test_render_keeps_original_test_and_gates_the_correction(self):
        render = _function(self.source, 'void ParticleBufferClass::Render(RenderInfoClass & rinfo)')
        self.assertIn('const bool original_visual_update = DecimationThreshold < LodCount - 1;', render)
        self.assertIn('const bool drawable = DecimationThreshold < 16U;', render)
        self.assertIn('(drawable && (particle_cost_mode & RenegadeVitaParticleCost::DRAWN_VISUAL_STATE) != 0U)', render)
        self.assertLess(render.index('Update_Kinematic_Particle_State();'), render.index('Update_Visual_Particle_State();'))

    def test_combine_uses_whole_buffer_unless_exact_mode(self):
        combine = _function(self.source, 'void ParticleBufferClass::Combine_Color_And_Alpha()')
        self.assertIn('unsigned range_count[2] = { cnt, 0U };', combine)
        self.assertIn('unsigned range_first[2] = { 0U, 0U };', combine)
        self.assertIn('if ((Particle_Cost_Mode() & RenegadeVitaParticleCost::EXACT_DECIMATION) != 0U) {', combine)
        self.assertIn('VectorProcessorClass::Clamp(\n\t\t\t\tdiffuse,\n\t\t\t\tdiffuse,', combine)

    def test_flag_grammar_and_defaults(self):
        header = HEADER.read_text(encoding='utf-8')
        self.assertIn('"ux0:data/renegade/user/config/particle-cost-v1.flag"', header)
        self.assertIn('#define RENEGADE_VITA_PARTICLE_COST_DEFAULT 5U', header)
        self.assertIn('bytes != 8U || memcmp(data, "RVPE1 ", 6U) != 0 || data[7] != \'\\n\'', header)
        self.assertIn('EXACT_DECIMATION = 1U', header)
        self.assertIn('DRAWN_VISUAL_STATE = 2U', header)
        self.assertIn('TELEMETRY = 4U', header)
        self.assertIn('#if defined(__vita__)', header)
        # The flag is read during emitter construction, not first mid-frame.
        ctor = self.source[self.source.index('\tLodCount = 17;'):]
        self.assertTrue(ctor.startswith('\tLodCount = 17;\n\tLodBias = 1.0f;\n\t(void)Particle_Cost_Mode();'))

    def test_patch_is_registered_after_the_keyframe_guard_and_reproducible(self):
        script = STAGE_SCRIPT.read_text(encoding='utf-8')
        guard = script.index('ww3d2-a35-particle-size-keyframe-guard.patch')
        ours = script.index('ww3d2-tut1-particle-cost.patch')
        self.assertLess(guard, ours)
        self.assertEqual(script.count('ww3d2-tut1-particle-cost.patch'), 1)
        line = script[:ours].rsplit('\n', 2)
        self.assertIn('patch --batch --forward --fuzz=0 --no-backup-if-mismatch', line[-2])
        self.assertIn('-d "$rv_stage/ww3d2" -p1', line[-1])
        if shutil.which('patch') is None:
            self.skipTest('patch(1) unavailable')
        with tempfile.TemporaryDirectory(prefix='renegade-particle-cost-') as folder:
            target = Path(folder) / 'part_buf.cpp'
            shutil.copyfile(STAGED, target)
            subprocess.run(['patch', '--batch', '--reverse', '--fuzz=0', '--no-backup-if-mismatch',
                            '-d', folder, '-p1', '-i', str(PATCH)], check=True,
                           stdout=subprocess.DEVNULL)
            self.assertNotIn('Particle_Cost_Mode', target.read_text(encoding='utf-8'))
            subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '--no-backup-if-mismatch',
                            '-d', folder, '-p1', '-i', str(PATCH)], check=True,
                           stdout=subprocess.DEVNULL)
            self.assertEqual(target.read_bytes(), STAGED.read_bytes())


if __name__ == '__main__':
    unittest.main()
