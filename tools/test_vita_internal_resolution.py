"""Host tests for the Vita internal-resolution (hardware scan-out) option.

Covers the internal-resolution-v1.flag grammar, the logical 960x544 ->
physical display-buffer viewport mapping extracted from the production
renderer (bit-identical at 100%), in-place capture expansion, and the
dynamic controller's hysteresis/anti-thrash behaviour under modelled
GPU-bound, CPU-bound, stall and oscillating frame-time signals.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEADER_DIR = ROOT / 'port/renderer/vita'


def production_build_native_viewport():
    text = (ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp').read_text()
    marker = ('bool Build_Native_Viewport(uint32_t d3d_x, uint32_t d3d_y,\n'
              '\tuint32_t width, uint32_t height, float min_depth, float max_depth,\n'
              '\tuint32_t logical_width')
    start = text.index(marker)
    return text[start:text.index('\nbool Set_Native_Presentation_Rect_Internal(', start)]


HARNESS = r'''
#include "internal_resolution.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
using namespace RenegadeVitaInternalResolution;

enum : uint32_t { DISPLAY_WIDTH = 960U, DISPLAY_HEIGHT = 544U };
struct NativePresentationRect { uint32_t x, y, width, height; };
struct NativeViewport { uint32_t x, y, width, height; float min_depth, max_depth; };
NativePresentationRect g_native_presentation_rect{0U, 0U, DISPLAY_WIDTH, DISPLAY_HEIGHT};
uint32_t g_physical_display_width = DISPLAY_WIDTH;
uint32_t g_physical_display_height = DISPLAY_HEIGHT;

PRODUCTION

// Pre-change production mapping (commit 95c4976) used as the 100% reference.
static bool Reference_Build(uint32_t d3d_x, uint32_t d3d_y, uint32_t width,
	uint32_t height, float min_depth, float max_depth, uint32_t logical_width,
	uint32_t logical_height, NativeViewport &viewport)
{
	if (logical_width == 0U || logical_height == 0U || width == 0U ||
		height == 0U || d3d_x > logical_width || d3d_y > logical_height ||
		width > logical_width - d3d_x || height > logical_height - d3d_y ||
		min_depth < 0.0f || max_depth > 1.0f || min_depth > max_depth) return false;
	const uint64_t left = g_native_presentation_rect.x +
		(static_cast<uint64_t>(d3d_x) * g_native_presentation_rect.width) / logical_width;
	const uint64_t right = g_native_presentation_rect.x +
		((static_cast<uint64_t>(d3d_x) + width) * g_native_presentation_rect.width +
		 logical_width - 1U) / logical_width;
	const uint64_t top = g_native_presentation_rect.y +
		(static_cast<uint64_t>(d3d_y) * g_native_presentation_rect.height) / logical_height;
	const uint64_t bottom = g_native_presentation_rect.y +
		((static_cast<uint64_t>(d3d_y) + height) * g_native_presentation_rect.height +
		 logical_height - 1U) / logical_height;
	if (right <= left || bottom <= top || right > DISPLAY_WIDTH || bottom > DISPLAY_HEIGHT)
		return false;
	viewport.x = static_cast<uint32_t>(left);
	viewport.y = static_cast<uint32_t>(DISPLAY_HEIGHT - bottom);
	viewport.width = static_cast<uint32_t>(right - left);
	viewport.height = static_cast<uint32_t>(bottom - top);
	viewport.min_depth = min_depth;
	viewport.max_depth = max_depth;
	return true;
}

static uint32_t rng = 12345U;
static uint32_t Next(uint32_t bound) { rng = rng * 1103515245U + 12345U; return (rng >> 8) % bound; }

static void Set_Level(uint32_t level)
{
	g_physical_display_width = Level_Size(level).width;
	g_physical_display_height = Level_Size(level).height;
}

static void Test_Flag()
{
	struct Case { const char *text; bool ok; bool automatic; uint32_t level; } cases[] = {
		{"RVIR1 100\n", true, false, LEVEL_100}, {"RVIR1 75\n", true, false, LEVEL_75},
		{"RVIR1 67\n", true, false, LEVEL_67}, {"RVIR1 50\n", true, false, LEVEL_50},
		{"RVIR1 auto\n", true, true, LEVEL_100},
		{"RVIR1 100", false, false, 0}, {"RVIR1 80\n", false, false, 0},
		{"RVIR1 100\r\n", false, false, 0}, {"RVIR0 100\n", false, false, 0},
		{"RVIR1 auto\n\n", false, false, 0}, {"RVIR1 \n", false, false, 0},
		{"RVIR1 AUTO\n", false, false, 0}, {"", false, false, 0}, {"RVIR1 0100\n", false, false, 0},
	};
	for (const Case &c : cases) {
		Mode mode = {false, 99U};
		const bool ok = Parse_Flag(c.text, strlen(c.text), mode);
		assert(ok == c.ok);
		if (ok) assert(mode.automatic == c.automatic && mode.level == c.level);
		else assert(!mode.automatic && mode.level == 99U);
	}
	Mode mode = {false, 0U};
	assert(!Parse_Flag(NULL, 8, mode));
	// Hardware scan-out sizes accepted by sceDisplaySetFrameBuf.
	assert(Level_Size(LEVEL_100).width == 960 && Level_Size(LEVEL_100).height == 544);
	assert(Level_Size(LEVEL_75).width == 720 && Level_Size(LEVEL_75).height == 408);
	assert(Level_Size(LEVEL_67).width == 640 && Level_Size(LEVEL_67).height == 368);
	assert(Level_Size(LEVEL_50).width == 480 && Level_Size(LEVEL_50).height == 272);
	assert(Level_Size(LEVEL_COUNT).width == 960);
}

static void Test_Viewport_Identity_At_100()
{
	Set_Level(LEVEL_100);
	const NativePresentationRect rects[] = {{0, 0, 960, 544}, {118, 0, 724, 544}, {0, 20, 960, 504}};
	const uint32_t logicals[][2] = {{960, 544}, {800, 600}, {640, 480}, {1024, 768}};
	for (const NativePresentationRect &rect : rects) {
		g_native_presentation_rect = rect;
		for (const auto &logical : logicals) {
			for (int i = 0; i < 20000; ++i) {
				const uint32_t x = Next(logical[0] + 2U), y = Next(logical[1] + 2U);
				const uint32_t w = Next(logical[0] + 2U), h = Next(logical[1] + 2U);
				NativeViewport a = {}, b = {};
				const bool ra = Build_Native_Viewport(x, y, w, h, 0.0f, 1.0f, logical[0], logical[1], a);
				const bool rb = Reference_Build(x, y, w, h, 0.0f, 1.0f, logical[0], logical[1], b);
				assert(ra == rb);
				if (ra) assert(a.x == b.x && a.y == b.y && a.width == b.width && a.height == b.height &&
					a.min_depth == b.min_depth && a.max_depth == b.max_depth);
			}
		}
	}
	g_native_presentation_rect = {0, 0, 960, 544};
}

static void Test_Viewport_Scaled()
{
	for (uint32_t level = LEVEL_75; level < LEVEL_COUNT; ++level) {
		Set_Level(level);
		const uint32_t pw = g_physical_display_width, ph = g_physical_display_height;
		g_native_presentation_rect = {0, 0, 960, 544};
		NativeViewport v = {};
		assert(Build_Native_Viewport(0, 0, 960, 544, 0.0f, 1.0f, 960, 544, v));
		assert(v.x == 0 && v.y == 0 && v.width == pw && v.height == ph);
		// Top-left HUD quadrant lands at the GL top (y measured from bottom).
		assert(Build_Native_Viewport(0, 0, 480, 272, 0.0f, 1.0f, 960, 544, v));
		assert(v.x == 0 && v.width == (pw + 1) / 2 && v.y + v.height == ph);
		// Split views never leave a gap between adjacent logical viewports.
		for (uint32_t split = 1; split < 960; ++split) {
			NativeViewport l = {}, r = {};
			assert(Build_Native_Viewport(0, 0, split, 544, 0.0f, 1.0f, 960, 544, l));
			assert(Build_Native_Viewport(split, 0, 960 - split, 544, 0.0f, 1.0f, 960, 544, r));
			assert(r.x <= l.x + l.width && r.x + 1 >= l.x + l.width);
			assert(l.width > 0 && r.width > 0 && r.x + r.width == pw);
		}
		const NativePresentationRect rects[] = {{0, 0, 960, 544}, {118, 0, 724, 544}};
		for (const NativePresentationRect &rect : rects) {
			g_native_presentation_rect = rect;
			for (int i = 0; i < 20000; ++i) {
				const uint32_t x = Next(801), y = Next(601), w = Next(801), h = Next(601);
				NativeViewport s = {}, ref = {};
				const bool rs = Build_Native_Viewport(x, y, w, h, 0.25f, 0.75f, 800, 600, s);
				const bool rr = Reference_Build(x, y, w, h, 0.25f, 0.75f, 800, 600, ref);
				assert(rs == rr);  // acceptance never depends on the scan-out size
				if (!rs) continue;
				assert(s.width > 0 && s.height > 0);
				assert(s.x + s.width <= pw && s.y + s.height <= ph);
				assert(s.min_depth == 0.25f && s.max_depth == 0.75f);
				// The scaled rect covers the 960x544 rect scaled by pw/960, ph/544.
				const uint32_t ref_top = 544U - ref.y - ref.height;
				const uint32_t s_top = ph - s.y - s.height;
				assert(uint64_t(s.x) * 960U <= uint64_t(ref.x) * pw);
				assert(uint64_t(s.x + s.width) * 960U >= uint64_t(ref.x + ref.width) * pw);
				assert(uint64_t(s_top) * 544U <= uint64_t(ref_top) * ph);
				assert(uint64_t(s_top + s.height) * 544U >= uint64_t(ref_top + ref.height) * ph);
			}
		}
	}
	Set_Level(LEVEL_100);
	g_native_presentation_rect = {0, 0, 960, 544};
}

static void Test_Capture_Expansion()
{
	for (uint32_t level = LEVEL_100; level < LEVEL_COUNT; ++level) {
		const uint32_t pw = Level_Size(level).width, ph = Level_Size(level).height;
		std::vector<uint8_t> buffer(960U * 544U * 4U, 0xEEU), source(pw * ph * 4U);
		for (size_t i = 0; i < source.size(); ++i) source[i] = static_cast<uint8_t>(Next(256));
		memcpy(buffer.data(), source.data(), source.size());
		Expand_Capture_In_Place(buffer.data(), pw, ph, 960U, 544U);
		for (uint32_t y = 0; y < 544U; ++y) for (uint32_t x = 0; x < 960U; ++x) {
			const uint32_t sx = x * pw / 960U, sy = y * ph / 544U;
			assert(memcmp(&buffer[(size_t(y) * 960U + x) * 4U], &source[(size_t(sy) * pw + sx) * 4U], 4U) == 0);
		}
	}
	uint8_t tiny[3 * 2 * 4];
	for (int i = 0; i < 4; ++i) tiny[i] = 7;  // 1x1 -> 3x2
	Expand_Capture_In_Place(tiny, 1, 1, 3, 2);
	for (uint8_t value : tiny) assert(value == 7);
	Expand_Capture_In_Place(NULL, 1, 1, 3, 2);
}

// Present-to-present model: CPU and GPU overlap (pipelined), optional vsync.
struct Model { double cpu_ms, gpu_full_ms; bool vsync; double stall_ms; };
static uint32_t Frame_Us(const Model &m, uint32_t level, int frame)
{
	const double fill = double(Level_Size(level).width) * Level_Size(level).height / (960.0 * 544.0);
	double ms = m.cpu_ms > m.gpu_full_ms * fill ? m.cpu_ms : m.gpu_full_ms * fill;
	ms += (frame % 7) * 0.05;  // jitter
	if (m.stall_ms > 0.0) ms = m.stall_ms;
	if (m.vsync) { const double v = 1000.0 / 60.0; ms = v * (int)((ms + v - 1e-6) / v); }
	return static_cast<uint32_t>(ms * 1000.0);
}

// Upper bound on failed probes in n evaluations: each costs a step, a revert
// and a lockout that starts at BACKOFF_INITIAL and doubles to BACKOFF_MAX.
static uint32_t Max_Probes(uint32_t evaluations)
{
	uint32_t probes = 0U, lock = Controller::BACKOFF_INITIAL;
	for (uint32_t t = 0U; t < evaluations;) {
		++probes;
		t += 2U + lock;
		lock = lock * 2U > Controller::BACKOFF_MAX ? uint32_t(Controller::BACKOFF_MAX) : lock * 2U;
	}
	return probes;
}

struct Run { uint32_t changes; uint32_t level_histogram[LEVEL_COUNT]; uint32_t max_consecutive_changes; };
static Run Simulate(const Model &m, uint32_t evaluations, uint32_t start_level = LEVEL_100,
	const Model *alternate = NULL)
{
	Controller c;
	c.Reset(start_level, LEVEL_50);
	Run run = {};
	uint32_t consecutive = 0;
	int frame = 0;
	for (uint32_t e = 0; e < evaluations; ++e) {
		const Model &active = (alternate != NULL && (e & 1U)) ? *alternate : m;
		Decision d = {};
		for (uint32_t i = 0; i < Controller::WINDOW; ++i) {
			const bool full = c.Record_Frame(Frame_Us(active, c.Level(), frame++));
			assert(full == (i + 1 == Controller::WINDOW));
		}
		d = c.Evaluate();
		assert(d.kind != DECISION_NONE && c.Samples() == 0);
		assert(d.level == c.Level() && d.level < LEVEL_COUNT);
		const int32_t delta = int32_t(d.level) - int32_t(d.previous_level);
		assert(delta >= -1 && delta <= 1);  // one step at most
		if (delta != 0) { ++run.changes; ++consecutive; } else consecutive = 0;
		if (consecutive > run.max_consecutive_changes) run.max_consecutive_changes = consecutive;
		++run.level_histogram[c.Level()];
	}
	return run;
}

static void Test_Controller()
{
	{	// Not enough samples: no decision.
		Controller c;
		assert(c.Evaluate().kind == DECISION_NONE);
		for (int i = 0; i < 119; ++i) assert(!c.Record_Frame(50000));
		assert(c.Evaluate().kind == DECISION_NONE);
		assert(c.Samples() == 0 && c.Level() == LEVEL_100);  // partial window discarded
		for (int i = 0; i < 200; ++i) c.Record_Frame(50000);
		assert(c.Samples() == Controller::WINDOW);
		const Decision d = c.Evaluate();
		assert(d.kind == DECISION_DOWN && d.p50_us == 50000 && d.p95_us == 50000);
	}
	// GPU-bound at native: settles one step down and stays (with/without vsync).
	for (bool vsync : {false, true}) {
		Run r = Simulate(Model{20.0, 45.0, vsync, 0.0}, 300);
		assert(r.changes == 1 && r.level_histogram[LEVEL_75] == 300);
	}
	// Heavily GPU-bound: walks down step by step to the level that meets
	// 30 fps; 50% is fast enough to probe 67% now and then, which regresses
	// and is locked out with exponential backoff.
	{
		Run r = Simulate(Model{15.0, 90.0, false, 0.0}, 300);
		fprintf(stderr, "heavy-gpu: changes=%u L50=%u L67=%u\n", r.changes,
			r.level_histogram[LEVEL_50], r.level_histogram[LEVEL_67]);
		assert(r.level_histogram[LEVEL_50] >= 280);
		assert(r.changes <= 3U + 2U * Max_Probes(300));
		assert(r.max_consecutive_changes <= 3);
	}
	// Already fast: never leaves 100%.
	{
		Run r = Simulate(Model{10.0, 12.0, true, 0.0}, 300);
		assert(r.changes == 0 && r.level_histogram[LEVEL_100] == 300);
	}
	// Fast at a reduced start level: climbs back to 100%, one step per
	// UP_DWELL evaluations.
	{
		Run r = Simulate(Model{10.0, 12.0, true, 0.0}, 50, LEVEL_50);
		assert(r.changes == 3 && r.max_consecutive_changes == 1);
		assert(r.level_histogram[LEVEL_100] == 50U - 3U * Controller::UP_DWELL + 1U);
	}
	// CPU-bound (the measured dev238 profile): a down step buys nothing, is
	// reverted, and retries back off exponentially: changes stay logarithmic.
	for (bool vsync : {false, true}) {
		Run r = Simulate(Model{45.0, 20.0, vsync, 0.0}, 1000);
		fprintf(stderr, "cpu-bound vsync=%d: changes=%u L100=%u\n", vsync ? 1 : 0,
			r.changes, r.level_histogram[LEVEL_100]);
		assert(r.level_histogram[LEVEL_100] >= 970);
		assert(r.changes <= 2U * Max_Probes(1000));
		assert(r.max_consecutive_changes <= 2);
	}
	// Loading / level-transition stalls never move the level.
	{
		Run r = Simulate(Model{45.0, 90.0, false, 900.0}, 100);
		assert(r.changes == 0 && r.level_histogram[LEVEL_100] == 100);
	}
	// Native slow but 75% comfortably fast: up steps regress, are reverted and
	// locked out exponentially; the controller spends most time at 75%.
	{
		Run r = Simulate(Model{10.0, 40.0, true, 0.0}, 1000);
		fprintf(stderr, "native-slow: changes=%u L75=%u\n", r.changes, r.level_histogram[LEVEL_75]);
		assert(r.level_histogram[LEVEL_75] >= 900);
		assert(r.changes <= 1U + 2U * Max_Probes(1000));
		assert(r.max_consecutive_changes <= 2);
	}
	// Adversarial signal alternating slow/fast every window: bounded changes.
	{
		const Model fast{10.0, 10.0, true, 0.0};
		Run r = Simulate(Model{45.0, 45.0, true, 0.0}, 1000, LEVEL_100, &fast);
		fprintf(stderr, "alternating: changes=%u\n", r.changes);
		assert(r.changes <= 2U + 2U * 2U * Max_Probes(1000));
		assert(r.max_consecutive_changes <= 2);
	}
	assert(Max_Probes(1000) <= 10U);
	// Thresholds sit on the 30/60 fps vsync quanta with a hold band between.
	assert(Controller::UP_P95_US > 33333U && Controller::DOWN_P50_US > 33333U);
	assert(Controller::UP_P50_US < Controller::DOWN_P50_US);
}

int main()
{
	Test_Flag();
	Test_Viewport_Identity_At_100();
	Test_Viewport_Scaled();
	Test_Capture_Expansion();
	Test_Controller();
	puts("internal resolution host tests: OK");
	return 0;
}
'''


class InternalResolutionTests(unittest.TestCase):
    def test_flag_mapping_capture_and_controller(self):
        program = HARNESS.replace('PRODUCTION', production_build_native_viewport())
        program = '#include <cstring>\n' + program
        with tempfile.TemporaryDirectory(prefix='renegade-internal-resolution-') as folder:
            path = Path(folder)
            (path / 'test.cpp').write_text(program)
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                            '-I', str(HEADER_DIR), str(path / 'test.cpp'), '-o', str(path / 'test')],
                           check=True)
            result = subprocess.run([str(path / 'test')], check=True, capture_output=True, text=True)
            self.assertIn('OK', result.stdout)

    def test_production_wiring(self):
        renderer = (ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp').read_text()
        self.assertIn('ux0:data/renegade/user/config/internal-resolution-v1.flag', renderer)
        init = renderer[renderer.index('Read_Internal_Resolution_Mode();'):
                        renderer.index('vglInitExtended(')]
        self.assertIn('"internal-resolution"', init)
        call = renderer[renderer.index('vglInitExtended('):]
        call = call[:call.index(';')]
        self.assertIn('g_physical_display_width', call)
        self.assertNotIn('960', call)
        end_frame = renderer[renderer.index('void End_Frame(bool present)'):
                             renderer.index('void Record_Texture_Request()')]
        self.assertLess(end_frame.index('vglSwapBuffers('),
                        end_frame.index('Update_Internal_Resolution_After_Present();'))
        update = renderer[renderer.index('void Update_Internal_Resolution_After_Present()'):]
        update = update[:update.index('\n}\n')]
        # Commit happens on the swap that applied vglSwapResolution, before any
        # new request; evaluation runs on the shared 120-frame checkpoint.
        self.assertLess(update.index('Commit_Pending_Internal_Resolution();'),
                        update.index('vglSwapResolution('))
        self.assertIn('g_statistics.frames % Controller::WINDOW', update)
        self.assertLess(update.index('RenegadeVitaTextEntry::Active()'),
                        update.index('Record_Frame('))
        # Every full-display viewport uses the physical buffer, never 960x544.
        self.assertNotIn('glViewport(0, 0, 960, 544)', renderer)
        self.assertNotIn('glViewport(0, 0, static_cast<GLsizei>(DISPLAY_WIDTH)', renderer)
        bink = (ROOT / 'port/platform/a4_binkmovie_boundary.cpp').read_text()
        self.assertNotIn('glViewport(0, 0, 960, 544)', bink)
        self.assertIn('Get_Physical_Display_Size(', bink)


if __name__ == '__main__':
    unittest.main()
