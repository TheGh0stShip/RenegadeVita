#ifndef WW3D_VITA_OPAQUE_SORT_H
#define WW3D_VITA_OPAQUE_SORT_H

#include <cstdint>
#include <cstring>

#include "ww3d_vita_static_mesh_cache.h"

// render-sort-v1 (RVSO1): pass-major replay of world-space static meshes.
//
// The original DX8RigidFVFCategoryContainer::Render drew every visible mesh's
// pass 0 (grouped by texture category) before any mesh's pass 1. The Vita
// boundary replays each mesh as soon as MeshClass::Render submits it, so a
// lightmapped world mesh alternates base texture (opaque, MODULATE, fog) and
// lightmap (multiply blend, REPLACE, no fog, no depth write) on every mesh.
// In vitaGL each alternation changes the fixed-function fragment mask and the
// blend state, i.e. a fragment program switch, a patcher blend relink and a
// full fragment uniform upload, twice per mesh.
//
// Inside one PhysicsSceneClass world-space-mesh loop (a window the wwphys
// patch opens and closes), cache-hit static meshes whose batches satisfy
// Opaque_Sort_Entry_Eligible are queued instead and replayed here in
// pass-major order. The order is exact apart from exact depth ties between
// different meshes:
//   - pass 0 batches are BASE/BASE_CUTOUT: blend off, depth and colour write,
//     LESS/LEQUAL. Each pixel ends with the nearest such fragment whatever the
//     order (alpha-tested fragments either write both or nothing).
//   - later passes are BASE or OVERLAY (depth write off, EQUAL/LEQUAL). Drawn
//     after the mesh's own complete pass 0, they can only pass where that
//     mesh's pass 0 is the stored depth, so no other mesh's pixel is touched
//     and pass order within the mesh is kept.
//   - a mesh with later passes may not alpha test in pass 0: a discarded
//     texel would let its overlay modify whatever lies behind, which depends
//     on what has been drawn by then.
// Everything else (blended pass 0, depth-write-off pass 0, ALWAYS/GREATER
// compares, skins, procedural passes, immediate-path meshes, any other draw)
// is never queued and flushes the queue first, so its position relative to
// every queued draw is unchanged.
//
// Modes: 0 off (default), 1 pass-major keeping submission order inside each
// pass (pass-0 ties resolve exactly as before), 2 pass-major with each pass
// grouped by texture/shader bucket in first-appearance order (the original
// texture-category idea; exact depth ties may resolve differently), 3 queue
// with the submission order unchanged (control for the queue's own cost;
// draw order identical to mode 0).
//
// Plain data only: the planner runs on the host; the renderer owns every GL
// call.
namespace RenegadeVitaRenderer {

enum OpaqueSortMode {
	OPAQUE_SORT_OFF = 0,
	OPAQUE_SORT_PASS_MAJOR = 1,
	OPAQUE_SORT_PASS_MAJOR_GROUPED = 2,
	OPAQUE_SORT_IDENTITY = 3,
	OPAQUE_SORT_MODE_COUNT = 4
};

enum OpaqueSortBatchClass {
	OPAQUE_SORT_CLASS_BASE = 0,
	OPAQUE_SORT_CLASS_BASE_CUTOUT = 1,
	OPAQUE_SORT_CLASS_OVERLAY = 2,
	OPAQUE_SORT_CLASS_BARRIER = 3
};

// ShaderClass::DepthCompareType values.
enum {
	OPAQUE_SORT_PASS_LESS = 1,
	OPAQUE_SORT_PASS_EQUAL = 2,
	OPAQUE_SORT_PASS_LEQUAL = 3
};

// Inputs are the translated state Apply_Original_Shader_State applies
// (Translate_Shader_State), not the raw ShaderClass bits.
inline OpaqueSortBatchClass Opaque_Sort_Classify(bool blend, bool depth_write,
	bool color_write, bool alpha_test, int depth_compare)
{
	if (depth_write) {
		if (blend || !color_write) return OPAQUE_SORT_CLASS_BARRIER;
		if (depth_compare != OPAQUE_SORT_PASS_LESS &&
			depth_compare != OPAQUE_SORT_PASS_LEQUAL) return OPAQUE_SORT_CLASS_BARRIER;
		return alpha_test ? OPAQUE_SORT_CLASS_BASE_CUTOUT : OPAQUE_SORT_CLASS_BASE;
	}
	if (depth_compare == OPAQUE_SORT_PASS_EQUAL ||
		depth_compare == OPAQUE_SORT_PASS_LEQUAL) return OPAQUE_SORT_CLASS_OVERLAY;
	return OPAQUE_SORT_CLASS_BARRIER;
}

// Batches are one cache entry's, in build order (non-decreasing pass).
inline bool Opaque_Sort_Entry_Eligible(const StaticMeshBatch *batches,
	const uint8_t *classes, uint32_t count)
{
	if (batches == NULL || classes == NULL || count == 0U) return false;
	// Without a pass-0 batch an overlay would have no base of its own.
	if (batches[0].pass != 0U) return false;
	bool multipass = false;
	for (uint32_t index = 0U; index < count; ++index) {
		if (index != 0U && batches[index].pass < batches[index - 1U].pass) return false;
		if (batches[index].pass != 0U) multipass = true;
	}
	for (uint32_t index = 0U; index < count; ++index) {
		const uint8_t batch_class = classes[index];
		if (batch_class == OPAQUE_SORT_CLASS_BARRIER) return false;
		if (batches[index].pass != 0U) continue;
		if (batch_class == OPAQUE_SORT_CLASS_OVERLAY) return false;
		if (multipass && batch_class == OPAQUE_SORT_CLASS_BASE_CUTOUT) return false;
	}
	return true;
}

// The state Replay_Static_Mesh_Entry reapplies when it differs.
inline bool Opaque_Sort_Same_State(const StaticMeshBatch &left, const StaticMeshBatch &right)
{
	return left.texture0 == right.texture0 && left.texture1 == right.texture1 &&
		left.material == right.material && left.shader_bits == right.shader_bits &&
		left.detail_stage == right.detail_stage;
}

// Mode 2 bucket: textures, shader and detail stage, i.e. the GL texture
// binding and fixed-function program/blend selection. Vertex materials are
// per-mesh objects, so including them would almost never group two meshes.
inline bool Opaque_Sort_Same_Bucket(const StaticMeshBatch &left, const StaticMeshBatch &right)
{
	return left.texture0 == right.texture0 && left.texture1 == right.texture1 &&
		left.shader_bits == right.shader_bits && left.detail_stage == right.detail_stage;
}

struct OpaqueSortItem {
	uint32_t vertex_buffer;
	uint32_t index_buffer;
	uint32_t first_batch;
	uint32_t batch_count;
	float projection[16];
	float modelview[16];
};

struct OpaqueSortStatistics {
	uint64_t windows;
	uint64_t flushes;
	uint64_t items;
	uint64_t batches;
	// Cache hits a window could not queue: a barrier class, or more batches
	// than the queue holds.
	uint64_t ineligible;
	uint64_t oversize;
	uint64_t capacity_flushes;
	// Changes between consecutive batches of each flush: in submission order
	// and in the executed order. state = Opaque_Sort_Same_State; shader =
	// shader bits; binds = owning mesh (vertex/index buffer and transforms).
	uint64_t submitted_state_changes;
	uint64_t executed_state_changes;
	uint64_t submitted_shader_changes;
	uint64_t executed_shader_changes;
	uint64_t submitted_binds;
	uint64_t executed_binds;
};

class OpaqueSortQueue {
public:
	enum { MaxItems = 256, MaxBatches = 1024 };

	OpaqueSortQueue() : item_count_(0U), batch_count_(0U) {}

	bool Empty() const { return item_count_ == 0U; }
	uint32_t Item_Count() const { return item_count_; }
	uint32_t Batch_Count() const { return batch_count_; }
	bool Fits(uint32_t batch_count) const {
		return item_count_ < static_cast<uint32_t>(MaxItems) &&
			batch_count <= static_cast<uint32_t>(MaxBatches) - batch_count_;
	}
	void Clear() { item_count_ = 0U; batch_count_ = 0U; }

	// Copies the batches: a later lookup may rebuild, evict or move the entry
	// (its buffers are only released after a barrier flushed this queue).
	bool Push(uint32_t vertex_buffer, uint32_t index_buffer,
		const StaticMeshBatch *batches, uint32_t batch_count,
		const float *projection, const float *modelview) {
		if (batches == NULL || batch_count == 0U || !Fits(batch_count)) return false;
		OpaqueSortItem &item = items_[item_count_];
		item.vertex_buffer = vertex_buffer;
		item.index_buffer = index_buffer;
		item.first_batch = batch_count_;
		item.batch_count = batch_count;
		std::memcpy(item.projection, projection, sizeof(item.projection));
		std::memcpy(item.modelview, modelview, sizeof(item.modelview));
		for (uint32_t index = 0U; index < batch_count; ++index) {
			batches_[batch_count_ + index] = batches[index];
			batch_items_[batch_count_ + index] = static_cast<uint16_t>(item_count_);
		}
		batch_count_ += batch_count;
		++item_count_;
		return true;
	}

	const OpaqueSortItem &Item(uint32_t index) const { return items_[index]; }
	const StaticMeshBatch &Batch(uint32_t slot) const { return batches_[slot]; }
	uint32_t Batch_Item(uint32_t slot) const { return batch_items_[slot]; }

	// Writes the execution order of batch slots (Batch_Count() entries).
	// Slots are numbered in submission order. Every mode is a stable
	// permutation: batches of one item keep their relative order within a
	// pass, and every pass of an item follows its lower passes.
	uint32_t Plan(uint32_t mode, uint16_t *order) {
		const uint32_t count = batch_count_;
		const bool grouped = mode == static_cast<uint32_t>(OPAQUE_SORT_PASS_MAJOR_GROUPED);
		if (mode != static_cast<uint32_t>(OPAQUE_SORT_PASS_MAJOR) && !grouped) {
			for (uint32_t slot = 0U; slot < count; ++slot) order[slot] = static_cast<uint16_t>(slot);
			return count;
		}
		uint32_t max_pass = 0U;
		for (uint32_t slot = 0U; slot < count; ++slot) {
			const uint32_t pass = batches_[slot].pass;
			if (pass > max_pass) max_pass = pass;
		}
		uint32_t written = 0U;
		for (uint32_t pass = 0U; pass <= max_pass; ++pass) {
			const uint32_t first = written;
			for (uint32_t slot = 0U; slot < count; ++slot) {
				if (static_cast<uint32_t>(batches_[slot].pass) == pass)
					order[written++] = static_cast<uint16_t>(slot);
			}
			if (grouped && written - first > 1U)
				Group_By_State(order + first, written - first);
		}
		return written;
	}

	// Changes between consecutive batches, before and after planning.
	void Count_Changes(const uint16_t *order, uint32_t count,
		OpaqueSortStatistics &statistics) const {
		for (uint32_t position = 0U; position < count; ++position) {
			const uint32_t submitted = position;
			const uint32_t executed = order[position];
			if (position == 0U) {
				++statistics.submitted_state_changes;
				++statistics.executed_state_changes;
				++statistics.submitted_shader_changes;
				++statistics.executed_shader_changes;
				++statistics.submitted_binds;
				++statistics.executed_binds;
				continue;
			}
			const uint32_t submitted_previous = position - 1U;
			const uint32_t executed_previous = order[position - 1U];
			if (!Opaque_Sort_Same_State(batches_[submitted_previous], batches_[submitted]))
				++statistics.submitted_state_changes;
			if (!Opaque_Sort_Same_State(batches_[executed_previous], batches_[executed]))
				++statistics.executed_state_changes;
			if (batches_[submitted_previous].shader_bits != batches_[submitted].shader_bits)
				++statistics.submitted_shader_changes;
			if (batches_[executed_previous].shader_bits != batches_[executed].shader_bits)
				++statistics.executed_shader_changes;
			if (batch_items_[submitted_previous] != batch_items_[submitted])
				++statistics.submitted_binds;
			if (batch_items_[executed_previous] != batch_items_[executed])
				++statistics.executed_binds;
		}
	}

private:
	// Stable grouping by bucket (Opaque_Sort_Same_Bucket), groups in order of
	// first appearance: a counting sort over group ids assigned by an
	// open-addressed table.
	void Group_By_State(uint16_t *slots, uint32_t count) {
		enum { TableSize = 2048, TableMask = TableSize - 1 };
		static_assert(TableSize >= 2 * MaxBatches, "group table load factor");
		uint32_t group_count = 0U;
		for (uint32_t index = 0U; index < static_cast<uint32_t>(TableSize); ++index)
			table_[index] = 0xffffU;
		for (uint32_t index = 0U; index < count; ++index) {
			const StaticMeshBatch &batch = batches_[slots[index]];
			uint32_t probe = Hash(batch) & static_cast<uint32_t>(TableMask);
			for (;;) {
				const uint16_t representative = table_[probe];
				if (representative == 0xffffU) {
					table_[probe] = static_cast<uint16_t>(index);
					group_of_[index] = static_cast<uint16_t>(group_count);
					group_first_[group_count] = 0U;
					++group_count;
					break;
				}
				if (Opaque_Sort_Same_Bucket(batches_[slots[representative]], batch)) {
					group_of_[index] = group_of_[representative];
					break;
				}
				probe = (probe + 1U) & static_cast<uint32_t>(TableMask);
			}
		}
		if (group_count == count) return;
		for (uint32_t index = 0U; index < count; ++index) ++group_first_[group_of_[index]];
		uint32_t running = 0U;
		for (uint32_t group = 0U; group < group_count; ++group) {
			const uint32_t size = group_first_[group];
			group_first_[group] = static_cast<uint16_t>(running);
			running += size;
		}
		for (uint32_t index = 0U; index < count; ++index)
			scratch_[group_first_[group_of_[index]]++] = slots[index];
		std::memcpy(slots, scratch_, sizeof(uint16_t) * count);
	}

	static uint32_t Hash(const StaticMeshBatch &batch) {
		uint32_t hash = 2166136261U;
		const uintptr_t words[2] = {
			reinterpret_cast<uintptr_t>(batch.texture0),
			reinterpret_cast<uintptr_t>(batch.texture1)
		};
		for (unsigned index = 0U; index < 2U; ++index) {
			hash = (hash ^ static_cast<uint32_t>(words[index] >> 4U)) * 16777619U;
		}
		hash = (hash ^ batch.shader_bits) * 16777619U;
		hash = (hash ^ (batch.detail_stage ? 1U : 0U)) * 16777619U;
		return hash ^ (hash >> 15U);
	}

	OpaqueSortItem items_[MaxItems];
	StaticMeshBatch batches_[MaxBatches];
	uint16_t batch_items_[MaxBatches];
	uint16_t table_[2048];
	uint16_t group_of_[MaxBatches];
	uint16_t group_first_[MaxBatches];
	uint16_t scratch_[MaxBatches];
	uint32_t item_count_;
	uint32_t batch_count_;
};

} // namespace RenegadeVitaRenderer

#endif
