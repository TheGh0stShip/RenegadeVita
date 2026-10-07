"""hud-cost bit 0: TextWindowClass keeps a height measurement's build.

The message window (dialogue subtitles, objective messages) measures its
text, which builds every row, right before the view update that rebuilds the
same rows. combat-tut1-textwindow-measured-build.patch keeps the measured
build when the update would reproduce it exactly.

Pure Python: nothing here runs a compiler. The static tests tie the staged
C++ to the patch and check that every input of the build is in the reuse
predicate; the model tests replay message-window event sequences through a
Python transcription of TextWindowClass/MessageWindowClass with and without
the reuse and require identical renderer contents after every step.
"""
from pathlib import Path
import math
import random
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'staging/combat'
PATCH_NAME = 'combat-tut1-textwindow-measured-build.patch'
PATCH = ROOT / 'port/patches' / PATCH_NAME
HEADER = ROOT / 'port/compatibility/include/renegade_vita_hud_cost.h'
STAGE_SCRIPT = ROOT / 'tools/stage_sources.sh'


def function_body(source, name):
    """Body of the out-of-line definition of name (Class::Method)."""
    match = re.search(r'^' + re.escape(name) + r'\s*\(', source, re.M)
    if match is None:
        raise AssertionError('no definition: ' + name)
    start = match.start()
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[brace:index + 1]
    raise AssertionError('unbalanced function: ' + signature)


def non_blank(text):
    return [line for line in text.split('\n') if line.strip()]


def strip_port_blocks(text):
    """Drop '#if defined(RENEGADE_VITA_PORT)' blocks that have no #else, i.e.
    what a build without the port define compiles from this patch's blocks."""
    out, depth, skipping = [], 0, False
    for line in text.split('\n'):
        stripped = line.strip()
        if not skipping and stripped == '#if defined(RENEGADE_VITA_PORT)':
            skipping, depth = True, 1
            continue
        if skipping:
            if stripped.startswith('#if'):
                depth += 1
            elif stripped.startswith(('#else', '#elif')) and depth == 1:
                raise AssertionError('port block with #else: ' + line)
            elif stripped.startswith('#endif'):
                depth -= 1
                if depth == 0:
                    skipping = False
            continue
        out.append(line)
    return '\n'.join(out)


class StaticContractTests(unittest.TestCase):
    def setUp(self):
        self.cpp = (STAGE / 'textwindow.cpp').read_text()
        self.h = (STAGE / 'textwindow.h').read_text()

    def test_patch_registered_once_after_every_other_textwindow_patch(self):
        stage = STAGE_SCRIPT.read_text()
        self.assertEqual(stage.count(PATCH_NAME), 1)
        self.assertTrue(PATCH.is_file())
        order = re.findall(r'port/patches/([A-Za-z0-9_.-]+\.patch)', stage)
        later = order[order.index(PATCH_NAME) + 1:]
        for name in later:
            text = (ROOT / 'port/patches' / name).read_text(errors='replace')
            self.assertNotIn('a/textwindow.', text, name)
        line = [l for l in stage.splitlines() if PATCH_NAME in l][0]
        self.assertIn('-d "$rv_stage/combat" -p1 <', line)

    def test_patch_only_adds_lines(self):
        body = [l for l in PATCH.read_text().splitlines()
                if not l.startswith(('---', '+++', '@@'))]
        self.assertFalse([l for l in body if l.startswith('-')])
        self.assertEqual(re.findall(r'^\+\+\+ (\S+)', PATCH.read_text(), re.M),
                         ['b/textwindow.h', 'b/textwindow.cpp'])

    def test_staging_is_preimage_plus_patch_and_non_port_build_unchanged(self):
        if shutil.which('patch') is None:
            self.skipTest('patch not installed')
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('textwindow.h', 'textwindow.cpp'):
                shutil.copy(STAGE / name, Path(tmp) / name)
            subprocess.run(['patch', '--batch', '-R', '--fuzz=0', '-p1', '-s',
                            '--no-backup-if-mismatch', '-d', tmp, '-i', str(PATCH)],
                           check=True)
            pre = {n: (Path(tmp) / n).read_text() for n in ('textwindow.h', 'textwindow.cpp')}
            subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-s',
                            '--no-backup-if-mismatch', '-d', tmp, '-i', str(PATCH)],
                           check=True)
            for name in pre:
                self.assertEqual((Path(tmp) / name).read_text(),
                                 (STAGE / name).read_text(), name)
        # Every change is inside a port block: without RENEGADE_VITA_PORT the
        # staged files are the pre-image byte for byte.
        # (Blank lines around the blocks are the only other additions.)
        self.assertEqual(non_blank(strip_port_blocks(self.h)), non_blank(pre['textwindow.h']))
        self.assertEqual(non_blank(strip_port_blocks(self.cpp)), non_blank(pre['textwindow.cpp']))

    def test_every_view_input_change_forgets_the_measured_build(self):
        functions = sorted(set(re.findall(r'^(TextWindowClass::\w+)\s*\(', self.cpp, re.M)))
        self.assertIn('TextWindowClass::Update_Row', functions)
        dirtying = []
        for name in functions:
            body = function_body(self.cpp, name)
            if 'IsViewDirty = true;' in body:
                dirtying.append(name)
                after = body[body.index('IsViewDirty = true;'):]
                self.assertIn('Forget_Measured_Build ();', after, name)
        self.assertEqual(sorted(dirtying), sorted([
            'TextWindowClass::Add_Column', 'TextWindowClass::Remove_Column',
            'TextWindowClass::Delete_All_Columns', 'TextWindowClass::Delete_Item',
            'TextWindowClass::Insert_Item', 'TextWindowClass::Set_Item_Text',
            'TextWindowClass::Set_Item_Color', 'TextWindowClass::Delete_All_Items']))
        self.assertIn('Forget_Measured_Build ();',
                      function_body(self.cpp, 'TextWindowClass::Free_Renderers'))
        # Build_View and Free_Contents recreate/free renderers through it.
        self.assertIn('Free_Renderers ();', function_body(self.cpp, 'TextWindowClass::Build_View'))
        self.assertIn('Free_Renderers ();', function_body(self.cpp, 'TextWindowClass::Free_Contents'))
        # Header-inline setters change inputs the predicate compares instead.
        self.assertIn('{ AreColumnsDisplayed = onoff; IsViewDirty = true;', self.h)
        self.assertIn('void\t\t\t\tSet_Text_Area (const RectClass &rect)\t{ TextRect = rect; }', self.h)

    def test_keep_predicate_covers_every_build_input(self):
        body = function_body(self.cpp, 'TextWindowClass::Can_Keep_Measured_Build')
        for term in (
                'MeasuredBuildValid == false',
                'Renegade_Vita_HUD_Cost_Enabled (RENEGADE_VITA_HUD_COST_TEXTWINDOW_MEASURED_BUILD) == false',
                'TextRenderers[0] == NULL || TextRenderers[1] == NULL',
                'DX8Wrapper::Is_Initted () == false',
                'MeasuredFirstLineIndex == FirstLineIndex',
                'MeasuredRowCount == row_count',
                'MeasuredColumnsDisplayed == AreColumnsDisplayed',
                'MeasuredTextRect.Left == TextRect.Left',
                'MeasuredTextRect.Top == TextRect.Top',
                'MeasuredTextRect.Right == TextRect.Right',
                '(MeasuredHasInnerRows == false || (MeasuredInnerRowBottom > TextRect.Bottom) == false)',
                'MeasuredResolution == Render2DClass::Get_Screen_Resolution ()',
                'MeasuredUVBias == WW3D::Is_Screen_UV_Biased ()'):
            self.assertIn(term, body)
        # The view-building inputs read by Update_View/Update_Row are exactly
        # those: TextRect edges, columns, FirstLineIndex, ColumnHeight and
        # LineSpacing (fixed per renderer lifetime) and the fonts.
        update = function_body(self.cpp, 'TextWindowClass::Update_View')
        row = function_body(self.cpp, 'TextWindowClass::Update_Row')
        used = set(re.findall(r'TextRect\.(\w+)', update + row))
        self.assertEqual(used, {'Left', 'Top', 'Right', 'Bottom'})
        self.assertIn('if ((y_pos + row_height) > TextRect.Bottom && info_only == false) {', update)
        self.assertEqual(self.cpp.count('ColumnHeight = '), 1)  # Build_View only
        self.assertNotIn('LineSpacing =', self.cpp)

    def test_reuse_only_replaces_full_updates_and_records_only_measurements(self):
        update = function_body(self.cpp, 'TextWindowClass::Update_View')
        keep = update.index('if (info_only == false && total_height == NULL && Can_Keep_Measured_Build ()) {')
        reset = update.index('TextRenderers[0]->Reset ();')
        self.assertLess(update.index('Build_View ();'), keep)
        self.assertLess(keep, update.index('Forget_Measured_Build ();'))
        self.assertLess(update.index('Forget_Measured_Build ();'), reset)
        kept = update[keep:update.index('}', keep)]
        self.assertIn('CurrentDisplayCount\t= MeasuredRowCount;', kept)
        self.assertIn('IsViewDirty\t\t\t\t= false;', kept)
        record = update.index('if (info_only && Renegade_Vita_HUD_Cost_Enabled '
                              '(RENEGADE_VITA_HUD_COST_TEXTWINDOW_MEASURED_BUILD)) {')
        self.assertLess(update.index('IsViewDirty = false;', reset), record)
        self.assertIn('MeasuredBuildValid\t\t\t= DX8Wrapper::Is_Initted ();', update[record:])
        # Inner-row bottoms use the exact expression of the stop test.
        self.assertIn('if (item_index + 1 < item_count) {', update)
        self.assertIn('const float row_bottom = (y_pos + row_height);', update)

    def test_flag_header_is_strict_and_default_off(self):
        header = HEADER.read_text()
        self.assertIn('"ux0:data/renegade/user/config/hud-cost-v1.flag"', header)
        self.assertIn('#define RENEGADE_VITA_HUD_COST_DEFAULT 0U', header)
        self.assertIn('size != 8U || memcmp(value, "RVHD1 ", 6U) != 0 ||', header)
        self.assertIn("value[7] != '\\n'", header)
        self.assertIn('static const unsigned mode = Renegade_Vita_HUD_Cost_Read();', header)
        self.assertIn('RENEGADE_VITA_HUD_COST_TEXTWINDOW_MEASURED_BUILD = 1U', header)
        self.assertIn('#include "renegade_vita_hud_cost.h"', self.cpp)

    def test_flag_parse_cases(self):
        def parse(value, fallback=0):
            # Mirror of Renegade_Vita_HUD_Cost_Parse.
            if len(value) != 8 or value[:6] != b'RVHD1 ' or value[7:8] != b'\n':
                return fallback
            digit = chr(value[6])
            if digit.isdigit():
                mode = ord(digit) - ord('0')
            elif 'A' <= digit <= 'F':
                mode = 10 + ord(digit) - ord('A')
            else:
                return fallback
            return mode & 1
        self.assertEqual(parse(b'RVHD1 1\n'), 1)
        self.assertEqual(parse(b'RVHD1 0\n', 1), 0)
        self.assertEqual(parse(b'RVHD1 F\n'), 1)
        self.assertEqual(parse(b'RVHD1 2\n'), 0)
        for bad in (b'RVHD1 1', b'RVHD1 1\r\n', b'RVHD1 f\n', b'rvhd1 1\n', b'RVHD2 1\n', b''):
            self.assertEqual(parse(bad, 7), 7, bad)


# --------------------------------------------------------------------------
# Model: Python transcription of the staged TextWindowClass and the
# MessageWindowClass calls into it. A Render2DSentenceClass build is modelled
# as the ordered list of (text, location, colour, wrap) it was given since its
# last Reset, plus the 2D resolution and UV bias at build time.
# --------------------------------------------------------------------------
class Rect:
    def __init__(self, l, t, r, b):
        self.l, self.t, self.r, self.b = l, t, r, b

    def key(self):
        return (self.l, self.t, self.r, self.b)

    def copy(self):
        return Rect(self.l, self.t, self.r, self.b)

    def height(self):
        return self.b - self.t


class World:
    """Global 2D state read while building (Get_Screen_Resolution, UV bias)."""
    def __init__(self):
        self.resolution = (0.0, 0.0, 960.0, 544.0)
        self.uv_bias = False
        self.initted = True


CHAR_W, CHAR_H = 7.0, 12.5   # fractional height exercises int() truncation


def text_rows(text, wrap):
    width = CHAR_W * len(text)
    return max(1, math.ceil(width / max(wrap, 1.0)))


class TextWindowModel:
    def __init__(self, world, keep, mutation=None):
        self.world, self.keep, self.mutation = world, keep, mutation
        self.first = 0
        self.display_count = 0
        self.displayed = False
        self.columns_displayed = False
        self.dirty = True
        self.rect = Rect(0, 0, 0, 0)
        self.column_height = 0.0
        self.line_spacing = 0.0
        self.columns = []          # [name, width, color, items=[[text, color, data]]]
        self.renderers = None      # build content or None
        self.measured = None
        self.builds = self.kept = 0

    # content mutators -------------------------------------------------
    def forget(self):
        self.measured = None

    def add_column(self, name, width, color):
        self.columns.append([name, width, color, []])
        self.dirty = True
        self.forget()

    def insert_item(self, index, text):
        items = self.columns[0][3]
        item = [text, (1, 1, 1), 0]
        if index < len(items):
            items.insert(index + 1, item)
        else:
            items.append(item)
            index = len(items) - 1
        for column in self.columns[1:]:
            column[3].insert(index, ['', (1, 1, 1), 0])
        self.dirty = True
        self.forget()
        return index

    def delete_item(self, index):
        for column in self.columns:
            if 0 <= index < len(column[3]):
                del column[3][index]
        self.dirty = True
        self.forget()

    def set_item_color(self, index, col, color):
        self.columns[col][3][index][1] = color
        self.dirty = True
        self.forget()

    def set_item_data(self, index, data):
        self.columns[0][3][index][2] = data

    def get_item_data(self, index):
        return self.columns[0][3][index][2]

    def item_count(self):
        return len(self.columns[0][3])

    def display_columns(self, onoff):
        self.columns_displayed = onoff
        self.dirty = True

    def set_backdrop(self, screen):
        self.first = 0
        self.displayed = False
        self.rect = Rect(screen.l + 30, screen.t + 10, screen.r - 30, screen.b - 10)

    def set_text_area(self, rect):
        self.rect = rect.copy()

    def display(self, onoff):
        if onoff != self.displayed:
            self.first = 0
            self.display_count = 0
            self.displayed = onoff
            self.dirty = onoff

    def get_display_count(self):
        if self.dirty:
            self.update_view()
        return self.display_count

    def page_down(self):
        self.first += self.display_count
        self.update_view()

    def page_up(self):
        self.first = max(0, self.first - self.display_count)
        self.update_view()

    def get_total_display_height(self):
        return self.update_view(want_total=True, info_only=True)

    def render(self):
        if not self.displayed:
            return
        if self.dirty or self.renderers is None:
            self.update_view()

    # build --------------------------------------------------------------
    def build_view(self):
        self.renderers = []
        self.forget()
        self.column_height = 1.5 * 9.0

    def can_keep(self):
        m = self.measured
        if m is None or not self.world.initted or self.renderers is None:
            return False
        rows = max(0, self.item_count() - self.first)
        checks = {
            'first': m['first'] == self.first,
            'rows': m['rows'] == rows,
            'columns': m['columns'] == self.columns_displayed,
            'left': m['rect'].l == self.rect.l,
            'top': m['rect'].t == self.rect.t,
            'right': m['rect'].r == self.rect.r,
            'overflow': (not m['has_inner']) or not (m['inner'] > self.rect.b),
            'resolution': m['resolution'] == self.world.resolution,
            'uv_bias': m['uv_bias'] == self.world.uv_bias,
        }
        for term in self.mutation or ():
            del checks[term]
        return all(checks.values())

    def update_row(self, index, y, content):
        x = float(int(self.rect.l))
        height = 0.0
        for col_index, column in enumerate(self.columns):
            text, color, _ = column[3][index]
            col_width = column[1] * (self.rect.r - self.rect.l)
            if col_index + 1 >= len(self.columns):
                col_width = self.rect.r - x
            wrap = col_width - 5
            content.append(('row', text, color, int(x), int(y), wrap))
            height = max(height, text_rows(text, wrap) * CHAR_H)
            x += int(column[1] * (self.rect.r - self.rect.l))
        return height

    def update_view(self, want_total=False, info_only=False):
        if self.renderers is None:
            self.build_view()
        if self.keep and not info_only and not want_total and self.can_keep():
            self.display_count = self.measured['rows']
            self.dirty = False
            self.kept += 1
            return None
        self.forget()
        self.builds += 1
        content = []
        if self.columns_displayed:
            x = self.rect.l
            for column in self.columns:
                content.append(('header', column[0], column[2], x, self.rect.t))
                x += column[1] * (self.rect.r - self.rect.l)
        y = self.rect.t + (self.column_height if self.columns_displayed else 0)
        self.display_count = 0
        count = self.item_count()
        has_inner, inner = False, 0.0
        for index in range(self.first, count):
            h = self.update_row(index, y, content)
            self.display_count += 1
            if index + 1 < count:
                bottom = y + h
                if not has_inner or bottom > inner:
                    has_inner, inner = True, bottom
            if (y + h) > self.rect.b and not info_only:
                break
            y += int(h + self.line_spacing)
        self.renderers = [self.world.resolution, self.world.uv_bias, self.world.initted,
                          tuple(content) if self.world.initted else ()]
        if not info_only:
            self.dirty = False
        if info_only and self.keep:
            self.measured = dict(
                first=self.first, rows=self.display_count, has_inner=has_inner,
                inner=inner, rect=self.rect.copy(), columns=self.columns_displayed,
                resolution=self.world.resolution, uv_bias=self.world.uv_bias) \
                if self.world.initted else None
        return y - self.rect.t

    def state(self):
        return (self.renderers, self.display_count, self.dirty, self.first,
                self.displayed, self.rect.key(),
                [[tuple(i) for i in c[3]] for c in self.columns])


class MessageWindowModel:
    SCREEN = Rect(111.0, 11.0, 900.0, 113.0)
    TEXT = Rect(141.0, 17.0, 870.0, 108.0)

    def __init__(self, world, keep, mutation=None):
        self.tw = TextWindowModel(world, keep, mutation)
        self.rect_dirty = True
        self.current = self.SCREEN.copy()
        self.current.b = self.current.t + 1
        self.tw.set_backdrop(self.current)
        text = self.TEXT.copy()
        text.b = text.t + 1
        self.tw.set_text_area(text)
        self.tw.add_column('', 1.0, (1, 1, 1))
        self.tw.display_columns(False)

    def update_window_rectangle(self):
        top_border = self.TEXT.t - self.SCREEN.t
        bottom_border = self.SCREEN.b - self.TEXT.b
        vert = top_border + bottom_border
        total = self.tw.get_total_display_height()
        if self.rect_dirty or total > (self.current.height() - vert):
            self.current.b = min(max(self.current.t + total + vert, 0), self.SCREEN.b)
            self.tw.set_backdrop(self.current)
            text = self.TEXT.copy()
            text.t = self.current.t + top_border
            text.b = self.current.b - bottom_border
            self.tw.set_text_area(text)
        self.rect_dirty = False

    def add_message(self, text, color, decay_ms):
        if text:
            index = self.tw.insert_item(self.tw.item_count(), text)
            self.tw.set_item_color(index, 0, color)
            self.tw.set_item_data(index, decay_ms)
        self.update_window_rectangle()
        if text:
            self.tw.display(True)

    def reset_current_rect(self):
        self.current = self.SCREEN.copy()
        self.current.b = self.current.t + 1

    def on_frame_update(self, ticks):
        tw = self.tw
        if not tw.displayed:
            return
        if tw.item_count() == 0:
            tw.display(False)
            self.reset_current_rect()
            return
        remove = tw.item_count() - tw.get_display_count()
        for _ in range(remove):
            tw.delete_item(0)
        for index in range(tw.item_count() - 1, -1, -1):
            left = tw.get_item_data(index) - ticks
            tw.set_item_data(index, left)
            if left <= 0:
                tw.delete_item(index)

    def render(self):
        if self.rect_dirty:
            self.update_window_rectangle()
        self.tw.render()


WORDS = ('Logan', 'Sydney', 'Havoc', 'range', 'target', 'Humm-Vee', 'ladder',
         'Press', 'Triangle', 'to', 'talk', 'the', 'soldier', 'Nod', 'GDI',
         'objective', 'updated', 'Mobius', 'barracks', 'refinery')


def run_sequence(seed, frames, mutation=None, extra=True):
    rng = random.Random(seed)
    world = [World(), World()]
    windows = [MessageWindowModel(world[0], False), MessageWindowModel(world[1], True, mutation)]
    mismatches = 0

    def both(action):
        nonlocal mismatches
        for w in windows:
            action(w)
        if windows[0].tw.state() != windows[1].tw.state():
            mismatches += 1

    for _ in range(frames):
        # Script think: dialogue/objective messages, sometimes two per frame.
        roll = rng.random()
        if roll < 0.08:
            for _ in range(1 + (rng.random() < 0.2)):
                text = ' '.join(rng.choice(WORDS) for _ in range(rng.randint(0, 28)))
                color = rng.choice(((1, 1, 1), (0, 1, 0), (1, 0.5, 0)))
                decay = rng.choice((5000, 6000, 9000, 20000))
                both(lambda w: w.add_message(text, color, decay))
        if extra and rng.random() < 0.01:
            resolution = rng.choice(((0.0, 0.0, 960.0, 544.0), (0.0, 0.0, 640.0, 480.0)))
            for w in world:
                w.resolution = resolution
        if extra and rng.random() < 0.01:
            for w in world:
                w.uv_bias = not w.uv_bias
        if extra and rng.random() < 0.005:
            for w in world:
                w.initted = not w.initted
        if extra and rng.random() < 0.01 and windows[0].tw.item_count():
            index = rng.randrange(windows[0].tw.item_count())
            both(lambda w: w.tw.set_item_color(index, 0, (0.5, 0.5, 1)))
        if extra and rng.random() < 0.01:
            choice = rng.random()
            both(lambda w: w.tw.page_down() if choice < 0.5 else w.tw.page_up())
        if extra and rng.random() < 0.005:
            flag = rng.random() < 0.5
            both(lambda w: w.tw.display_columns(flag))
        if extra and rng.random() < 0.003:
            both(lambda w: setattr(w, 'rect_dirty', True))
        if extra and rng.random() < 0.01:
            # Another owner re-laying out the text area (one edge moves).
            edge, delta = rng.choice('ltrb'), rng.choice((-6.0, 4.0))
            def shift(w):
                rect = w.tw.rect.copy()
                setattr(rect, edge, getattr(rect, edge) + delta)
                w.tw.set_text_area(rect)
            both(shift)
        ticks = rng.choice((16, 33, 33, 50, 120))
        both(lambda w: w.on_frame_update(ticks))
        both(lambda w: w.render())
    return windows, mismatches


class MessageWindowModelTests(unittest.TestCase):
    def test_kept_builds_are_identical_to_rebuilds(self):
        total_original = total_port = total_kept = 0
        for seed in range(40):
            windows, mismatches = run_sequence(seed, 1500)
            self.assertEqual(mismatches, 0, 'seed %d' % seed)
            total_original += windows[0].tw.builds
            total_port += windows[1].tw.builds
            total_kept += windows[1].tw.kept
        self.assertEqual(total_original, total_port + total_kept)
        self.assertGreater(total_kept, 100)

    def test_subtitle_flow_saves_one_build_per_message(self):
        world = [World(), World()]
        original = MessageWindowModel(world[0], False)
        port = MessageWindowModel(world[1], True)
        lines = ['Welcome to the training facility.',
                 'Follow Lieutenant Logan to the firing range and speak with Sergeant Sydney.',
                 'Good.', 'Now climb the ladder.']
        for line in lines:
            for w in (original, port):
                w.add_message(line, (1, 1, 1), 6000)
                w.on_frame_update(33)
                w.render()
            self.assertEqual(original.tw.state(), port.tw.state())
        self.assertEqual(original.tw.builds, 2 * len(lines))
        self.assertEqual(port.tw.builds, len(lines))
        self.assertEqual(port.tw.kept, len(lines))

    def test_clamped_window_overflow_is_rebuilt(self):
        world = [World(), World()]
        original = MessageWindowModel(world[0], False)
        port = MessageWindowModel(world[1], True)
        long_line = ' '.join(['objective'] * 40)
        for _ in range(6):
            for w in (original, port):
                w.add_message(long_line, (1, 1, 1), 60000)
                w.on_frame_update(16)
                w.render()
            self.assertEqual(original.tw.state(), port.tw.state())
        self.assertGreater(port.tw.builds, 6)

    def test_model_detects_a_missing_predicate_term(self):
        # FirstLineIndex is also implied by the row count, so drop both.
        for mutation in (('overflow',), ('resolution',), ('uv_bias',), ('top',),
                         ('left',), ('right',), ('first', 'rows'), ('columns',)):
            found = False
            for seed in range(60):
                _, mismatches = run_sequence(seed, 1500, mutation)
                if mismatches:
                    found = True
                    break
            self.assertTrue(found, mutation)


if __name__ == '__main__':
    unittest.main()
