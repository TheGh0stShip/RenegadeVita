"""render-sort-v1 (RVSO1): ordering rule model, raster equivalence and wiring.

Pure Python; nothing here invokes a compiler. The C++ planner itself is
compared with this model by tools/test_vita_opaque_sort_native.py.
"""
from pathlib import Path
import random
import re
import subprocess
import unittest

from tools import vita_opaque_sort_model as model

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp'
HEADER = ROOT / 'port/renderer/vita/ww3d_vita_opaque_sort.h'
PATCH = ROOT / 'port/patches/wwphys-tut1-render-sort.patch'

W = H = 12
CLEAR = ((10, 20, 30), 1.0)


# --- a tiny depth-buffered rasterizer ------------------------------------

def depth_pass(compare, fragment, stored):
    return {model.PASS_LESS: fragment < stored,
            model.PASS_LEQUAL: fragment <= stored,
            model.PASS_EQUAL: fragment == stored,
            model.PASS_ALWAYS: True}[compare]


def blend(op, src, dst, alpha):
    if op == 'write':
        return src
    if op == 'multiply':      # ZERO, SRC_COLOR (lightmap pass)
        return tuple((s * d + 127) // 255 for s, d in zip(src, dst))
    if op == 'alpha':         # SRC_ALPHA, ONE_MINUS_SRC_ALPHA
        return tuple((s * alpha + d * (255 - alpha) + 127) // 255 for s, d in zip(src, dst))
    if op == 'add':
        return tuple(min(255, s + d) for s, d in zip(src, dst))
    raise ValueError(op)


def draw(framebuffer, item, batch):
    color, depth = framebuffer
    for (x, y) in batch['pixels']:
        if batch.get('discard') and (x * 7 + y * 3 + batch['discard']) % 4 == 0:
            continue
        fragment = item['depth']
        if not depth_pass(batch['compare'], fragment, depth[y][x]):
            continue
        color[y][x] = blend(batch['op'], batch['color'], color[y][x], batch.get('alpha', 255))
        if batch['depth_write']:
            depth[y][x] = fragment


def render(items, sequence):
    framebuffer = ([[CLEAR[0]] * W for _ in range(H)], [[CLEAR[1]] * W for _ in range(H)])
    for i, b in sequence:
        draw(framebuffer, items[i], items[i]['batches'][b])
    return framebuffer[0]


# --- scene generation ----------------------------------------------------

def rect_pixels(rng):
    x0, y0 = rng.randrange(W - 2), rng.randrange(H - 2)
    x1, y1 = rng.randrange(x0 + 1, W + 1), rng.randrange(y0 + 1, H + 1)
    return [(x, y) for y in range(y0, y1) for x in range(x0, x1)]


def split(pixels, parts, rng):
    """Disjoint triangle runs of one pass (batches with their own state)."""
    buckets = [[] for _ in range(parts)]
    for pixel in pixels:
        buckets[rng.randrange(parts)].append(pixel)
    return [bucket for bucket in buckets if bucket] or [pixels]


def make_batch(rng, pass_index, kind, pixels, palette):
    texture = rng.choice(palette)
    batch = {'pass': pass_index, 'pixels': pixels, 'tex0': texture, 'tex1': None,
             'mat': rng.randrange(2), 'detail': False,
             'color': (texture * 37 % 256, texture * 91 % 256, texture * 53 % 256)}
    if kind == 'base':
        batch.update(op='write', compare=rng.choice((model.PASS_LESS, model.PASS_LEQUAL)),
                     depth_write=True, shader=1)
        batch['cls'] = model.classify(False, True, True, False, batch['compare'])
    elif kind == 'cutout':
        batch.update(op='write', compare=model.PASS_LEQUAL, depth_write=True, shader=2,
                     discard=rng.randrange(1, 4))
        batch['cls'] = model.classify(False, True, True, True, batch['compare'])
    elif kind == 'overlay':
        op = rng.choice(('multiply', 'alpha', 'add', 'write'))
        batch.update(op=op, compare=rng.choice((model.PASS_EQUAL, model.PASS_LEQUAL)),
                     depth_write=False, shader={'multiply': 3, 'alpha': 4, 'add': 5, 'write': 6}[op],
                     alpha=rng.randrange(256))
        batch['cls'] = model.classify(op != 'write', False, True, False, batch['compare'])
    elif kind == 'translucent':
        # Order dependent: blended, no depth write, plain LEQUAL against the scene.
        batch.update(op='alpha', compare=model.PASS_LEQUAL, depth_write=False, shader=7,
                     alpha=rng.randrange(1, 255))
        batch['cls'] = model.classify(True, False, True, False, batch['compare'])
    elif kind == 'always':
        batch.update(op='write', compare=model.PASS_ALWAYS, depth_write=True, shader=8)
        batch['cls'] = model.classify(False, True, True, False, batch['compare'])
    return batch


def make_item(rng, depth, palette, allow_cutout_overlay=False):
    pixels = rect_pixels(rng)
    shape = rng.random()
    batches = []
    if shape < 0.12:
        kind = rng.choice(('translucent', 'always'))
        batches.append(make_batch(rng, 0, kind, pixels, palette))
        return {'depth': depth, 'batches': batches}
    base_kind = 'cutout' if (shape < 0.3) else 'base'
    passes = 1 if rng.random() < 0.4 else rng.randrange(2, 4)
    if base_kind == 'cutout' and passes > 1 and not allow_cutout_overlay and rng.random() < 0.5:
        base_kind = 'base'
    for pass_index in range(passes):
        kind = base_kind if pass_index == 0 else rng.choice(('overlay', 'overlay', 'base'))
        for part in split(pixels, rng.randrange(1, 4), rng):
            batches.append(make_batch(rng, pass_index, kind, part, palette))
    return {'depth': depth, 'batches': batches}


def make_scene(rng, ties=False, allow_cutout_overlay=False):
    count = rng.randrange(3, 12)
    depths = [round(rng.uniform(0.05, 0.95), 6) for _ in range(count)]
    if ties:
        depths = [rng.choice((0.3, 0.5, 0.7)) for _ in range(count)]
    elif len(set(depths)) != count:
        depths = [0.05 + 0.9 * i / count for i in range(count)]
        rng.shuffle(depths)
    palette = list(range(rng.randrange(1, 5)))
    return [make_item(rng, depth, palette, allow_cutout_overlay) for depth in depths]


def permissive_execution_order(items, mode):
    """execution_order with eligibility relaxed to also queue cutout+overlay."""
    original = model.entry_eligible

    def relaxed(batches):
        patched = [dict(b, cls=model.BASE if b['cls'] == model.BASE_CUTOUT else b['cls'])
                   for b in batches]
        return original(patched)
    model.entry_eligible = relaxed
    try:
        return model.execution_order(items, mode)
    finally:
        model.entry_eligible = original


# --- tests -----------------------------------------------------------------

class OpaqueSortRuleTests(unittest.TestCase):
    def test_classification_truth_table(self):
        c = model.classify
        self.assertEqual(c(False, True, True, False, model.PASS_LEQUAL), model.BASE)
        self.assertEqual(c(False, True, True, False, model.PASS_LESS), model.BASE)
        self.assertEqual(c(False, True, True, True, model.PASS_LEQUAL), model.BASE_CUTOUT)
        # Blended or colour-masked depth writers and other compares are order dependent.
        self.assertEqual(c(True, True, True, False, model.PASS_LEQUAL), model.BARRIER)
        self.assertEqual(c(False, True, False, False, model.PASS_LEQUAL), model.BARRIER)
        for compare in (model.PASS_NEVER, model.PASS_EQUAL, model.PASS_GREATER,
                        model.PASS_NOTEQUAL, model.PASS_GEQUAL, model.PASS_ALWAYS):
            self.assertEqual(c(False, True, True, False, compare), model.BARRIER, compare)
        # Depth-write-off passes touch only depth-equal pixels with EQUAL/LEQUAL.
        for blend in (False, True):
            self.assertEqual(c(blend, False, True, False, model.PASS_EQUAL), model.OVERLAY)
            self.assertEqual(c(blend, False, True, True, model.PASS_LEQUAL), model.OVERLAY)
            for compare in (model.PASS_LESS, model.PASS_ALWAYS, model.PASS_GREATER):
                self.assertEqual(c(blend, False, True, False, compare), model.BARRIER)

    def test_entry_eligibility(self):
        def entry(*spec):
            return [{'pass': p, 'cls': c} for p, c in spec]
        ok = model.entry_eligible
        self.assertTrue(ok(entry((0, model.BASE), (1, model.OVERLAY))))  # lightmapped world
        self.assertTrue(ok(entry((0, model.BASE), (0, model.BASE), (1, model.OVERLAY),
                                 (2, model.OVERLAY))))
        self.assertTrue(ok(entry((0, model.BASE_CUTOUT))))
        self.assertTrue(ok(entry((0, model.BASE), (1, model.BASE_CUTOUT))))
        self.assertFalse(ok(entry((0, model.BASE_CUTOUT), (1, model.OVERLAY))))
        self.assertFalse(ok(entry((0, model.OVERLAY))))
        self.assertFalse(ok(entry((0, model.BASE), (1, model.BARRIER))))
        self.assertFalse(ok(entry((1, model.OVERLAY))))
        self.assertFalse(ok(entry((0, model.BASE), (1, model.OVERLAY), (0, model.BASE))))
        self.assertFalse(ok([]))

    def test_plan_is_a_stable_pass_major_permutation(self):
        rng = random.Random(1337)
        for _ in range(400):
            slots = []
            for item in range(rng.randrange(1, 9)):
                passes = rng.randrange(1, 4)
                for p in range(passes):
                    for _ in range(rng.randrange(1, 3)):
                        slots.append({'item': item, 'pass': p, 'tex0': rng.randrange(3),
                                      'tex1': None, 'mat': rng.randrange(2),
                                      'shader': rng.randrange(2), 'detail': False})
            for mode in model.MODES:
                order = model.plan(mode, slots)
                self.assertEqual(sorted(order), list(range(len(slots))), mode)
                if mode in (model.OFF, model.IDENTITY):
                    self.assertEqual(order, list(range(len(slots))))
                    continue
                position = {slot: i for i, slot in enumerate(order)}
                for a in range(len(slots)):
                    for b in range(a + 1, len(slots)):
                        sa, sb = slots[a], slots[b]
                        if sa['pass'] < sb['pass']:
                            # Lower passes first, for every pair of batches.
                            self.assertLess(position[a], position[b])
                        same_key = model.bucket_key(sa) == model.bucket_key(sb)
                        if sa['pass'] == sb['pass'] and (mode == model.PASS_MAJOR or same_key):
                            # Stable: submission order kept (within a key when grouped).
                            self.assertLess(position[a], position[b])
                if mode == model.PASS_MAJOR_GROUPED:
                    # Each bucket's batches are contiguous within a pass.
                    run_keys = []
                    for slot in order:
                        key = (slots[slot]['pass'], model.bucket_key(slots[slot]))
                        if not run_keys or run_keys[-1] != key:
                            run_keys.append(key)
                    self.assertEqual(len(run_keys), len(set(run_keys)))

    def test_barrier_items_never_move(self):
        rng = random.Random(7)
        for _ in range(300):
            items = make_scene(rng)
            for mode in model.MODES:
                sequence = model.execution_order(items, mode)
                self.assertEqual(sorted(sequence), sorted(model.execution_order(items, model.OFF)))
                for index, item in enumerate(items):
                    if model.entry_eligible(item['batches']):
                        continue
                    # Everything submitted before an ineligible item still draws
                    # before it, everything after still after it.
                    positions = [k for k, (i, _) in enumerate(sequence) if i == index]
                    self.assertEqual(positions, list(range(positions[0], positions[-1] + 1)))
                    before = {i for i, _ in sequence[:positions[0]]}
                    after = {i for i, _ in sequence[positions[-1] + 1:]}
                    self.assertEqual(before, set(range(index)))
                    self.assertEqual(after, set(range(index + 1, len(items))))


class OpaqueSortRasterEquivalenceTests(unittest.TestCase):
    def test_tie_free_scenes_render_identically(self):
        rng = random.Random(20261007)
        queued_multipass = 0
        for _ in range(1500):
            items = make_scene(rng)
            reference = render(items, model.execution_order(items, model.OFF))
            for mode in (model.PASS_MAJOR, model.PASS_MAJOR_GROUPED, model.IDENTITY):
                self.assertEqual(render(items, model.execution_order(items, mode)), reference, mode)
            queued_multipass += sum(1 for item in items if model.entry_eligible(item['batches'])
                                    and item['batches'][-1]['pass'] > 0)
        self.assertGreater(queued_multipass, 1000)

    def test_cutout_base_with_overlay_must_stay_ineligible(self):
        """Negative control: queueing alpha-tested pass 0 under overlays diverges."""
        rng = random.Random(99)
        divergent = 0
        for _ in range(1500):
            items = make_scene(rng, allow_cutout_overlay=True)
            reference = render(items, model.execution_order(items, model.OFF))
            if render(items, permissive_execution_order(items, model.PASS_MAJOR)) != reference:
                divergent += 1
            # The real rule keeps these scenes exact.
            self.assertEqual(render(items, model.execution_order(items, model.PASS_MAJOR)), reference)
        self.assertGreater(divergent, 0)

    def test_pass_zero_ties_resolve_as_before_in_mode_one(self):
        """Exact depth ties: mode 1 keeps single-pass results; grouping may not."""
        rng = random.Random(5)
        grouped_divergent = 0
        for _ in range(1500):
            items = [item for item in make_scene(rng, ties=True)
                     if item['batches'][-1]['pass'] == 0]
            if not items:
                continue
            reference = render(items, model.execution_order(items, model.OFF))
            self.assertEqual(render(items, model.execution_order(items, model.PASS_MAJOR)), reference)
            self.assertEqual(render(items, model.execution_order(items, model.IDENTITY)), reference)
            if render(items, model.execution_order(items, model.PASS_MAJOR_GROUPED)) != reference:
                grouped_divergent += 1
        # Documented caveat of mode 2 (it follows the original category order).
        self.assertGreater(grouped_divergent, 0)


def function_body(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}\n', start) + 3]


class OpaqueSortWiringTests(unittest.TestCase):
    def test_flag_default_off_and_telemetry(self):
        source = RENDERER.read_text()
        self.assertIn('#define RENEGADE_VITA_OPAQUE_SORT_DEFAULT 0', source)
        self.assertIn('"ux0:data/renegade/user/config/render-sort-v1.flag"', source)
        self.assertIn('memcmp(value, "RVSO1 ", 6U) == 0', source)
        initialize = function_body(source, 'bool Initialize()')
        self.assertLess(initialize.index('Read_Vertex_Array_Mode();'),
                        initialize.index('Read_Opaque_Sort_Mode();'))
        self.assertIn('Log_Opaque_Sort_Statistics();', function_body(source, 'void End_Frame(bool present)'))
        log = function_body(source, 'void Log_Opaque_Sort_Statistics()')
        fmt = re.search(r'"frame=%u mode=%u [^"]*"', log).group(0)[1:-1]
        # Worst case: every %u 10 digits, every %llu 20, plus the breadcrumb
        # prefix; it must fit the 512-byte breadcrumb message.
        widest = fmt.replace('%llu', 'x' * 20).replace('%u', 'x' * 10)
        self.assertLess(len(widest) + len('[A3.5-dev999 render-sort 99999] '), 512)
        window = function_body(source, 'void Begin_Opaque_Sort_Window()')
        self.assertIn('g_opaque_sort_mode != static_cast<uint32_t>(OPAQUE_SORT_OFF)', window)
        self.assertIn('g_static_mesh_cache_enabled', window)

    def test_every_other_draw_flushes_first(self):
        source = RENDERER.read_text()
        submit = source[source.index('static void Submit_Mesh_Internal(MeshClass &mesh'):
                        source.index('void Submit_Mesh(MeshClass &mesh')]
        barrier = submit.index('if (material_pass != NULL || is_skin) Opaque_Sort_Barrier();')
        self.assertLess(barrier, submit.index('Fetch_Cached_Deformed_Skin('))
        self.assertLess(barrier, submit.index('Shadow_Load_Transforms(transform_matrices.projection'))
        self.assertIn('original_world_transform, transform_matrices)) {', submit)
        cache = function_body(source, 'bool Submit_Static_Mesh_Cache(')
        self.assertEqual(cache.count('Opaque_Sort_Draw_Now(flush_epoch, transforms);'), 3)
        self.assertLess(cache.index('if (Opaque_Sort_Enqueue(*entry, transforms)) return true;'),
                        cache.index('Replay_Static_Mesh_Entry(*entry);'))
        self.assertLess(cache.index('const uint32_t flush_epoch = g_opaque_sort_flush_epoch;'),
                        cache.index('Static_Mesh_Cache_Lookup('))
        release = function_body(source, 'void Release_Static_Mesh_Buffers(')
        self.assertLess(release.index('Opaque_Sort_Barrier();'), release.index('glDeleteBuffers'))
        for signature in ('void Begin_Frame(bool clear_color', 'void End_Frame(bool present)',
                          'bool Apply_DX8_Render_State(uint32_t state, uint32_t value)',
                          'bool Bind_Offscreen_Render_Target(',
                          'bool Restore_Default_Render_Target()',
                          'uint32_t logical_width, uint32_t logical_height)\n{',
                          'void Invalidate_Static_Mesh_Cache()',
                          'void Forget_Static_Mesh_Model(',
                          'void Forget_Static_Mesh_User_Lighting(',
                          'void Begin_Opaque_Sort_Window()', 'void End_Opaque_Sort_Window()'):
            body = function_body(source, signature)
            self.assertIn('Opaque_Sort_Barrier();', body, signature)
        # Host harnesses compile the production indexed-submission prefix
        # (test_vita_index_preparation); boundary draws cannot occur inside the
        # world-space-mesh window, so that path carries no barrier.
        indexed = source[source.index('IndexedSubmissionResult Submit_Indexed_Triangles('):]
        indexed = indexed[:indexed.index('#if defined(__vita__)\n\t// Let vitaGL')]
        self.assertNotIn('Opaque_Sort', indexed)

    def test_flush_replays_like_the_static_cache(self):
        source = RENDERER.read_text()
        flush = function_body(source, 'void Opaque_Sort_Flush()')
        replay = function_body(source, 'void Replay_Static_Mesh_Entry(')
        self.assertEqual(flush.count('vglRenegadeInvalidateVertexAttributes();'), 2)
        self.assertIn('Shadow_Load_Transforms(item.projection, item.modelview);', flush)
        self.assertNotRegex(flush, r'\bgl(LoadMatrixf|LoadIdentity|BlendFunc|DepthMask|DepthFunc)\(')
        # Same state predicate and the same per-batch state sequence as the replay.
        for call in ('Apply_Original_Shader_State(shader);',
                     'Apply_Platform_Texture_Stage(*texture0, 0U);',
                     'Apply_Platform_Texture_Stage(*texture1, 1U);',
                     'Apply_Original_Texture_Coordinate_State(\n\t\t\t\tstatic_cast<VertexMaterialClass *>(batch.material));',
                     'Capture_Original_Texture_Coordinate_State(stage, &coordinates);',
                     'Apply_Original_Texture_Stage_State(shader, texture0 != NULL, batch.detail_stage);'):
            self.assertIn(call, flush, call)
            self.assertIn(call, replay, call)
        # Item change rebinds buffers and forces the pointers to be set again.
        bind = flush[flush.index('if (queue.Batch_Item(slot) != item_index) {'):]
        bind = bind[:bind.index('\n\t\t}\n')]
        for needle in ('glBindBuffer(GL_ARRAY_BUFFER, item.vertex_buffer);',
                       'glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, item.index_buffer);',
                       'window = 0xffffffffU;'):
            self.assertIn(needle, bind)
        tail = flush[flush.rindex('vglRenegadeInvalidateVertexAttributes();'):]
        for needle in ('Disable_Texture_Stage(1U);', 'Apply_Original_Texture_Coordinate_State(NULL);',
                       'Release_Submission_Transforms();', 'queue.Clear();',
                       '++g_opaque_sort_flush_epoch;', 'g_opaque_sort_flushing = false;'):
            self.assertIn(needle, tail)
        header = HEADER.read_text()
        same = header[header.index('inline bool Opaque_Sort_Same_State('):]
        same = same[:same.index('\n}\n')]
        replay_same = replay[replay.index('const bool same_state'):]
        replay_same = replay_same[:replay_same.index(';')]
        for field in ('texture0', 'texture1', 'material', 'shader_bits', 'detail_stage'):
            self.assertIn('.' + field, same)
            self.assertIn('.' + field, replay_same)

    def test_static_batches_record_their_pass(self):
        source = RENDERER.read_text()
        build = source[source.index('bool Build_Static_Mesh_Streams('):
                       source.index('StaticMeshRebuildReason Static_Mesh_Entry_Current(')]
        self.assertIn('state.pass = static_cast<uint8_t>(pass);', build)
        self.assertLess(build.index('memset(&state, 0, sizeof(state));'),
                        build.index('state.pass = static_cast<uint8_t>(pass);'))
        cache_header = (ROOT / 'port/renderer/vita/ww3d_vita_static_mesh_cache.h').read_text()
        self.assertIn('\tbool detail_stage;\n\t// Original material pass; batches are built in '
                      'non-decreasing pass order.\n\tuint8_t pass;\n};', cache_header)

    def test_window_is_the_world_space_mesh_loop_only(self):
        pscene = (ROOT / 'staging/wwphys/pscene.cpp').read_text()
        self.assertEqual(pscene.count('RenegadeVitaRenderer::Begin_Opaque_Sort_Window();'), 1)
        self.assertEqual(pscene.count('RenegadeVitaRenderer::End_Opaque_Sort_Window();'), 1)
        body = pscene[pscene.index('void PhysicsSceneClass::Render_Objects('):]
        body = body[:body.index('\n}\n')]
        normal = body[body.index('} else {'):]
        begin = normal.index('Begin_Opaque_Sort_Window();')
        end = normal.index('End_Opaque_Sort_Window();')
        loop = normal[begin:end]
        self.assertIn('for (it.First(static_ws_list); !it.Is_Done(); it.Next()) {', loop)
        self.assertNotIn('static_list)', loop)
        self.assertNotIn('dyn_list', loop)
        self.assertLess(end, normal.index('WWPROFILE("static objects");'))

    def test_patch_is_staged_and_ordered_last(self):
        stage = (ROOT / 'tools/stage_sources.sh').read_text()
        line = '-d "$rv_stage/wwphys" -p1 < "$rv_root/port/patches/wwphys-tut1-render-sort.patch"'
        self.assertEqual(stage.count(line), 1)
        self.assertLess(stage.index('combat-a37-face-action-stale-end-time-clamp.patch'),
                        stage.index(line))
        patch = PATCH.read_text()
        self.assertTrue(patch.startswith('--- a/pscene.cpp\n+++ b/pscene.cpp\n'))
        added = [l for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++')]
        self.assertTrue(all('Vis' not in l for l in added))
        # The tracked staged file is exactly the patched result (zero fuzz).
        result = subprocess.run(
            ['patch', '--dry-run', '-R', '--batch', '--fuzz=0', '-d',
             str(ROOT / 'staging/wwphys'), '-p1', '-i', str(PATCH)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
