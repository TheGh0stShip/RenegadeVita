"""The sorted renderer's radix depth sort must order polygons exactly like the
original Sort() (ascending depth; identical output whenever depths are
distinct), keep equal depths in submission order, and merge only runs whose
draw state is identical."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
STAGED = ROOT / 'staging/ww3d2/sortingrenderer.cpp'
PATCH = ROOT / 'port/patches/ww3d2-a36-sorting-depth-sort-and-runs.patch'

HARNESS = r'''
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#define WWASSERT(x) do { if (!(x)) std::abort(); } while (0)
struct ShortVectorIStruct {
	unsigned short i, j, k;
	ShortVectorIStruct(unsigned short i_, unsigned short j_, unsigned short k_) : i(i_), j(j_), k(k_) {}
	ShortVectorIStruct() {}
};
struct TempIndexStruct {
	ShortVectorIStruct tri;
	unsigned idx;
	TempIndexStruct() {}
	TempIndexStruct(const ShortVectorIStruct& tri_, unsigned idx_) : tri(tri_), idx(idx_) {}
};
#include "original_sort.inc"
#include "depth_sort.inc"

static unsigned state = 12345U;
static unsigned Next() { state = state * 1103515245U + 12345U; return state >> 8; }

int main()
{
	unsigned cases = 0;
	for (unsigned round = 0; round < 4000; ++round) {
		const unsigned count = round < 50 ? round : 1 + Next() % (round % 7 == 0 ? 6000 : 400);
		const unsigned shape = round % 6;
		std::vector<float> keys(count);
		std::vector<TempIndexStruct> items(count);
		for (unsigned i = 0; i < count; ++i) {
			float key;
			if (shape == 0) key = static_cast<float>(i) * 0.5f - 40.0f;            // ascending
			else if (shape == 1) key = 40.0f - static_cast<float>(i) * 0.25f;      // descending
			else if (shape == 2) key = static_cast<float>(Next() % 9) - 4.0f;      // many ties, signs
			else if (shape == 3) key = (static_cast<float>(Next() % 100000) - 50000.0f) / 7.0f;
			else if (shape == 4) key = -static_cast<float>(i / 3) + static_cast<float>(Next() % 5);
			else key = (Next() & 1) ? 0.0f : -0.0f;                                  // signed zeros
			keys[i] = key;
			items[i] = TempIndexStruct(ShortVectorIStruct(i & 0xffff, (i * 7) & 0xffff, round & 0xffff), i);
		}
		std::vector<float> radix_keys = keys, original_keys = keys;
		std::vector<TempIndexStruct> radix_items = items, original_items = items;
		Depth_Sort(radix_items.data(), radix_keys.data(), count);
		Sort<TempIndexStruct, float>(original_items.data(), original_keys.data(), static_cast<int>(count));
		// Ascending, keys travel with their items, and a permutation of the input.
		std::vector<unsigned> seen(count, 0U);
		for (unsigned i = 0; i < count; ++i) {
			if (i && !(radix_keys[i] >= radix_keys[i - 1])) { std::printf("not ascending %u\n", round); return 1; }
			const unsigned source = radix_items[i].idx;
			if (source >= count || seen[source]++ ||
				std::memcmp(&radix_keys[i], &keys[source], sizeof(float)) != 0) {
				std::printf("bad permutation %u\n", round); return 1;
			}
			// Equal depths keep submission order (stable).
			if (i && radix_keys[i] == radix_keys[i - 1] &&
				std::memcmp(&radix_keys[i], &radix_keys[i - 1], sizeof(float)) == 0 &&
				radix_items[i].idx < radix_items[i - 1].idx) { std::printf("unstable %u\n", round); return 1; }
			// Same key sequence as the original sort.
			if (!(radix_keys[i] == original_keys[i])) { std::printf("key order %u\n", round); return 1; }
		}
		// With distinct depths the order is unique, so it equals the original.
		std::vector<float> sorted = keys;
		std::sort(sorted.begin(), sorted.end());
		const bool distinct = std::adjacent_find(sorted.begin(), sorted.end()) == sorted.end();
		if (distinct) {
			for (unsigned i = 0; i < count; ++i)
				if (radix_items[i].idx != original_items[i].idx) { std::printf("differs %u\n", round); return 1; }
		}
		++cases;
	}
	std::printf("depth sort PASS cases=%u\n", cases);
	return 0;
}
'''


def section(source, start, end):
    first = source.index(start)
    return source[first:source.index(end, first)]


class SortingDepthSortTests(unittest.TestCase):
    def test_radix_sort_matches_original_order(self):
        source = STAGED.read_text()
        original = section(source, 'template <class T, class K>\nvoid InsertionSort',
                           '#if defined(RENEGADE_VITA_PORT)\n// ---')
        depth = section(source, 'static unsigned* radix_key_array;',
                        '#endif\n\n// ----------------------------------------------------------------------------\n\nstruct SortingNodeStruct')
        with tempfile.TemporaryDirectory(prefix='renegade-depth-sort-') as folder:
            directory = Path(folder)
            (directory / 'original_sort.inc').write_text(original)
            (directory / 'depth_sort.inc').write_text(depth)
            (directory / 'test.cpp').write_text(HARNESS)
            subprocess.run(['g++', '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                            '-I' + folder, str(directory / 'test.cpp'), '-o', str(directory / 'test')],
                           check=True)
            completed = subprocess.run([str(directory / 'test')], check=True,
                                       capture_output=True, text=True, timeout=300)
            self.assertIn('depth sort PASS cases=4000', completed.stdout)

    def test_runs_merge_only_identical_draw_state(self):
        source = STAGED.read_text()
        same = section(source, 'static bool Same_Draw_State(', '#endif')
        for field in ('a.shader.Get_Bits()!=b.shader.Get_Bits()', 'a.material!=b.material',
                      'a.Textures[i]!=b.Textures[i]', 'memcmp(&a.world,&b.world,sizeof(a.world))',
                      'memcmp(&a.view,&b.view,sizeof(a.view))', 'a.LightEnable[i]!=b.LightEnable[i]',
                      'memcmp(&a.Lights[i],&b.Lights[i],sizeof(a.Lights[i]))'):
            self.assertIn(field, same)
        # Lights are compared exactly when the boundary evaluates lighting.
        self.assertIn('if (a.material!=NULL && a.material->Get_Lighting()) {', same)
        boundary = (ROOT / 'port/renderer/vita/ww3d_vita_renderer.cpp').read_text()
        self.assertEqual(boundary.count('submission.draw_state->LightEnable['), 1)
        self.assertIn('submission.draw_state->material->Get_Lighting() &&', boundary)
        flush = section(source, 'void SortingRendererClass::Flush_Sorting_Pool()',
                        'void SortingRendererClass::Flush()')
        self.assertIn('Depth_Sort(tis,polygon_z_array,overlapping_polygon_count);', flush)
        self.assertIn('Depth_Sort(tris, depths, overlapping_polygon_count);', flush)
        self.assertIn('if (Same_Draw_State(run_state->sorting_state,state->sorting_state)) {', flush)
        self.assertIn('Apply_Render_State(overlapping_nodes[node_id]->sorting_state);', flush)
        stage = (ROOT / 'tools/stage_sources.sh').read_text()
        self.assertEqual(stage.count(PATCH.name), 1)
        self.assertLess(stage.index('ww3d-a35-original-sorting-lifecycle.patch'), stage.index(PATCH.name))


if __name__ == '__main__':
    unittest.main()
