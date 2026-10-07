// Host driver for the render-sort-v1 planner (ww3d_vita_opaque_sort.h).
// tools/test_vita_opaque_sort_native.py feeds fixtures on stdin and compares
// every answer with tools/vita_opaque_sort_model.py.
//
//   C                      -> "C blend depth_write color_write alpha_test compare class"
//                             for every input combination
//   E n (pass class)*n     -> "E eligible"
//   F n (item pass tex0 tex1 mat shader detail)*n
//                          -> "P mode slot..." for modes 0..3; items are
//                             contiguous, numbered from 0, ids < 0 mean NULL
#include <cstdint>
#include <cstdio>
#include <vector>

#include "ww3d_vita_opaque_sort.h"

using namespace RenegadeVitaRenderer;

namespace {

void *Pointer(int id)
{
	return id < 0 ? NULL : reinterpret_cast<void *>(static_cast<uintptr_t>(id + 1) * 64U);
}

OpaqueSortQueue g_queue;
uint16_t g_order[OpaqueSortQueue::MaxBatches];

bool Run_Fixture()
{
	unsigned count = 0U;
	if (std::scanf("%u", &count) != 1 || count > static_cast<unsigned>(OpaqueSortQueue::MaxBatches))
		return false;
	std::vector<StaticMeshBatch> batches(count);
	std::vector<int> owners(count);
	for (unsigned index = 0U; index < count; ++index) {
		int item = 0, pass = 0, texture0 = 0, texture1 = 0, material = 0, shader = 0, detail = 0;
		if (std::scanf("%d %d %d %d %d %d %d", &item, &pass, &texture0, &texture1, &material,
			&shader, &detail) != 7) return false;
		StaticMeshBatch batch = {};
		batch.texture0 = Pointer(texture0);
		batch.texture1 = Pointer(texture1);
		batch.material = Pointer(material);
		batch.shader_bits = static_cast<uint32_t>(shader);
		batch.detail_stage = detail != 0;
		batch.pass = static_cast<uint8_t>(pass);
		batch.index_count = 3U;
		batches[index] = batch;
		owners[index] = item;
	}
	static const float identity[16] = {
		1.0f, 0.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0.0f, 0.0f,
		0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 0.0f, 0.0f, 1.0f
	};
	g_queue.Clear();
	unsigned first = 0U;
	while (first < count) {
		unsigned end = first + 1U;
		while (end < count && owners[end] == owners[first]) ++end;
		if (!g_queue.Push(static_cast<uint32_t>(owners[first] + 1), static_cast<uint32_t>(owners[first] + 1),
			&batches[first], end - first, identity, identity)) return false;
		first = end;
	}
	for (unsigned mode = 0U; mode < static_cast<unsigned>(OPAQUE_SORT_MODE_COUNT); ++mode) {
		const uint32_t written = g_queue.Plan(mode, g_order);
		std::printf("P %u", mode);
		for (uint32_t index = 0U; index < written; ++index) std::printf(" %u", static_cast<unsigned>(g_order[index]));
		std::printf("\n");
	}
	return true;
}

bool Run_Eligibility()
{
	unsigned count = 0U;
	if (std::scanf("%u", &count) != 1 || count > 64U) return false;
	std::vector<StaticMeshBatch> batches(count == 0U ? 1U : count);
	std::vector<uint8_t> classes(count == 0U ? 1U : count);
	for (unsigned index = 0U; index < count; ++index) {
		unsigned pass = 0U, batch_class = 0U;
		if (std::scanf("%u %u", &pass, &batch_class) != 2) return false;
		StaticMeshBatch batch = {};
		batch.pass = static_cast<uint8_t>(pass);
		batches[index] = batch;
		classes[index] = static_cast<uint8_t>(batch_class);
	}
	std::printf("E %d\n", Opaque_Sort_Entry_Eligible(batches.data(), classes.data(), count) ? 1 : 0);
	return true;
}

} // namespace

int main()
{
	char command[8] = {};
	while (std::scanf("%7s", command) == 1) {
		if (command[0] == 'C') {
			for (int blend = 0; blend < 2; ++blend)
				for (int depth_write = 0; depth_write < 2; ++depth_write)
					for (int color_write = 0; color_write < 2; ++color_write)
						for (int alpha_test = 0; alpha_test < 2; ++alpha_test)
							for (int compare = 0; compare < 8; ++compare)
								std::printf("C %d %d %d %d %d %d\n", blend, depth_write, color_write,
									alpha_test, compare, static_cast<int>(Opaque_Sort_Classify(
										blend != 0, depth_write != 0, color_write != 0,
										alpha_test != 0, compare)));
		} else if (command[0] == 'E') {
			if (!Run_Eligibility()) return 2;
		} else if (command[0] == 'F') {
			if (!Run_Fixture()) return 3;
		} else {
			return 4;
		}
	}
	return 0;
}
