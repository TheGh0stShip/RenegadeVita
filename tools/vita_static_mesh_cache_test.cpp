// Host contract for the GPU-resident static mesh cache data model.
#include <cassert>
#include <cstdio>
#include <vector>

#include "ww3d_vita_static_mesh_cache.h"

using namespace RenegadeVitaRenderer;

static std::vector<std::pair<uint32_t, uint32_t>> released;

static void Release(uint32_t vertex_buffer, uint32_t index_buffer)
{
	released.push_back({vertex_buffer, index_buffer});
}

static StaticMeshBatch State(uintptr_t texture, uint32_t shader)
{
	StaticMeshBatch batch = {};
	batch.texture0 = reinterpret_cast<void *>(texture);
	batch.shader_bits = shader;
	return batch;
}

static void Fill(StaticMeshVertex *vertex, uint32_t source)
{
	vertex->position[0] = static_cast<float>(source);
	vertex->position[1] = vertex->position[2] = 0.0f;
}

static void Test_Builder_Batches_And_Reuse()
{
	StaticMeshStreamBuilder builder;
	assert(builder.Begin(16U));
	assert(builder.Begin_Batch(State(1U, 7U)));
	const uint32_t first[6] = {0U, 1U, 2U, 2U, 1U, 3U};
	for (uint32_t corner = 0U; corner < 6U; ++corner) {
		if (corner % 3U == 0U) assert(builder.Reserve_Triangle());
		StaticMeshVertex *vertex = builder.Append(first[corner]);
		assert(!builder.Failed());
		if (vertex != NULL) Fill(vertex, first[corner]);
	}
	// A new run never shares vertices with the previous run.
	assert(builder.Begin_Batch(State(2U, 7U)));
	const uint32_t second[3] = {1U, 2U, 4U};
	assert(builder.Reserve_Triangle());
	for (uint32_t corner = 0U; corner < 3U; ++corner) {
		StaticMeshVertex *vertex = builder.Append(second[corner]);
		assert(vertex != NULL);
		Fill(vertex, second[corner]);
	}
	// An empty run is dropped.
	assert(builder.Begin_Batch(State(3U, 7U)));
	builder.End_Batch();
	builder.Assign_Windows();
	assert(!builder.Failed());
	assert(builder.Batches().Count() == 2U);
	assert(builder.Vertices().Count() == 7U);
	assert(builder.Indices().Count() == 9U);
	const StaticMeshBatch &a = builder.Batches()[0];
	const StaticMeshBatch &b = builder.Batches()[1];
	assert(a.first_vertex == 0U && a.vertex_count == 4U && a.index_count == 6U);
	assert(b.first_vertex == 4U && b.vertex_count == 3U && b.first_index == 6U);
	assert(a.window_base == 0U && b.window_base == 0U);
	// Every rewritten index still resolves to the original source vertex.
	for (uint32_t corner = 0U; corner < 6U; ++corner) {
		const uint32_t vertex = a.window_base + builder.Indices()[corner];
		assert(builder.Vertices()[vertex].position[0] == static_cast<float>(first[corner]));
	}
	for (uint32_t corner = 0U; corner < 3U; ++corner) {
		const uint32_t vertex = b.window_base + builder.Indices()[6U + corner];
		assert(builder.Vertices()[vertex].position[0] == static_cast<float>(second[corner]));
	}
	// Out-of-range sources fail instead of reading past the mapping table.
	assert(builder.Begin(4U));
	assert(builder.Begin_Batch(State(1U, 1U)));
	assert(builder.Append(9U) == NULL && builder.Failed());
}

static void Test_Builder_Splits_At_Sixteen_Bit_Windows()
{
	const uint32_t triangles = 30000U;
	const uint32_t sources = triangles * 3U;
	StaticMeshStreamBuilder builder;
	assert(builder.Begin(sources));
	assert(builder.Begin_Batch(State(1U, 1U)));
	for (uint32_t triangle = 0U; triangle < triangles; ++triangle) {
		assert(builder.Reserve_Triangle());
		for (uint32_t corner = 0U; corner < 3U; ++corner) {
			const uint32_t source = triangle * 3U + corner;
			StaticMeshVertex *vertex = builder.Append(source);
			assert(vertex != NULL);
			Fill(vertex, source);
		}
	}
	builder.End_Batch();
	builder.Assign_Windows();
	assert(!builder.Failed());
	assert(builder.Batches().Count() == 2U);
	uint32_t corner = 0U;
	for (uint32_t index = 0U; index < builder.Batches().Count(); ++index) {
		const StaticMeshBatch &batch = builder.Batches()[index];
		assert(batch.vertex_count <= STATIC_MESH_MAX_BATCH_VERTICES);
		assert(batch.first_vertex + batch.vertex_count - batch.window_base <= 65536U);
		assert(batch.texture0 == reinterpret_cast<void *>(1U));
		for (uint32_t i = 0U; i < batch.index_count; ++i, ++corner) {
			const uint32_t vertex = batch.window_base +
				builder.Indices()[batch.first_index + i];
			assert(builder.Vertices()[vertex].position[0] == static_cast<float>(corner));
		}
	}
	assert(corner == sources);
}

static void Test_Windows_Merge_Small_And_Split_Large()
{
	std::vector<StaticMeshBatch> batches(4);
	std::vector<uint16_t> indices = {0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2};
	const uint32_t counts[4] = {40000U, 20000U, 10000U, 30000U};
	uint32_t vertex = 0U;
	for (uint32_t i = 0U; i < 4U; ++i) {
		batches[i] = State(i + 1U, 0U);
		batches[i].first_vertex = vertex;
		batches[i].vertex_count = counts[i];
		batches[i].first_index = i * 3U;
		batches[i].index_count = 3U;
		vertex += counts[i];
	}
	Static_Mesh_Assign_Windows(batches.data(), 4U, indices.data());
	assert(batches[0].window_base == 0U && batches[1].window_base == 0U);
	assert(batches[2].window_base == 60000U && batches[3].window_base == 60000U);
	assert(indices[3] == 40000U && indices[6] == 0U && indices[9] == 10000U);
	for (uint32_t i = 0U; i < 4U; ++i) {
		assert(batches[i].window_base + indices[i * 3U] == batches[i].first_vertex);
	}
}

static void Test_Material_Snapshot_And_Colors()
{
	StaticMeshMaterialSnapshot left = {};
	left.material = reinterpret_cast<void *>(8U);
	left.diffuse[1] = 0.5f;
	StaticMeshMaterialSnapshot right = left;
	assert(Static_Mesh_Snapshot_Equal(left, right));
	right.opacity = 0.25f;
	assert(!Static_Mesh_Snapshot_Equal(left, right));
	right = left;
	right.mapper[1] = reinterpret_cast<void *>(4U);
	assert(!Static_Mesh_Snapshot_Equal(left, right));
	right = left;
	right.lighting = 1U;
	assert(!Static_Mesh_Snapshot_Equal(left, right));
	assert(Static_Mesh_Color_Byte(-1.0f) == 0U && Static_Mesh_Color_Byte(0.0f) == 0U);
	assert(Static_Mesh_Color_Byte(1.0f) == 255U && Static_Mesh_Color_Byte(4.0f) == 255U);
	assert(Static_Mesh_Color_Byte(0.5f) == 128U);
	for (unsigned value = 0U; value < 256U; ++value) {
		assert(Static_Mesh_Color_Byte(static_cast<float>(value) / 255.0f) == value);
	}
	StaticMeshStreamBuilder builder;
	assert(builder.Begin(1U));
	assert(builder.Add_Material(left) && builder.Add_Material(left));
	assert(builder.Materials().Count() == 1U && builder.Has_Material(left.material));
}

static void Test_Lighting_Signature()
{
	StaticMeshLightingSignature unlit = {};
	StaticMeshLightingSignature lit = {};
	lit.uses_lighting = 1U;
	lit.has_environment = 1U;
	lit.ambient[0] = lit.ambient[1] = lit.ambient[2] = 1.0f;
	StaticMeshLightingSignature other = lit;
	other.world[3] = 25.0f;
	// Unlit colours ignore every lighting input.
	assert(Static_Mesh_Lighting_Equal(unlit, other));
	// Without directional lights the transform cannot change any colour.
	assert(Static_Mesh_Lighting_Equal(lit, other));
	other.ambient[1] = 0.5f;
	assert(!Static_Mesh_Lighting_Equal(lit, other));
	other = lit;
	other.has_environment = 0U;
	assert(!Static_Mesh_Lighting_Equal(lit, other));
	StaticMeshLightingSignature directional = lit;
	directional.light_count = 1U;
	directional.light_direction[0][2] = -1.0f;
	directional.light_diffuse[0][0] = 0.75f;
	other = directional;
	assert(Static_Mesh_Lighting_Equal(directional, other));
	other.world[7] = 3.0f;
	assert(!Static_Mesh_Lighting_Equal(directional, other));
	other = directional;
	other.light_diffuse[0][0] = 0.5f;
	assert(!Static_Mesh_Lighting_Equal(directional, other));
	other = directional;
	other.light_count = 2U;
	assert(!Static_Mesh_Lighting_Equal(directional, other));
	// Lights beyond the four evaluated slots are never compared.
	other = directional;
	other.light_direction[1][0] = 9.0f;
	assert(Static_Mesh_Lighting_Equal(directional, other));
	StaticMeshLightingSignature global = {};
	global.uses_lighting = 1U;
	global.dx8_ambient = 0xff808080U;
	other = global;
	assert(Static_Mesh_Lighting_Equal(global, other));
	other.dx8_ambient = 0xffffffffU;
	assert(!Static_Mesh_Lighting_Equal(global, other));
}

static StaticMeshEntry *Ready(StaticMeshCacheTable &table, uintptr_t model,
	uintptr_t lighting, uint32_t frame, uint32_t bytes)
{
	StaticMeshEntry *entry = table.Insert(reinterpret_cast<void *>(model),
		reinterpret_cast<void *>(lighting));
	assert(entry != NULL);
	entry->state = STATIC_MESH_ENTRY_READY;
	entry->vertex_buffer = static_cast<uint32_t>(model * 10U + lighting);
	entry->index_buffer = entry->vertex_buffer + 1U;
	entry->last_used_frame = frame;
	table.Account(*entry, bytes);
	return entry;
}

static void Test_Table_Lifetime_Budget_And_Invalidation()
{
	static StaticMeshCacheTable table;
	table.Set_Release_Callback(Release);
	released.clear();
	Ready(table, 0x1000U, 0U, 1U, 100U);
	Ready(table, 0x1000U, 0x77U, 2U, 100U);
	Ready(table, 0x2000U, 0U, 3U, 100U);
	assert(table.Live() == 3U && table.Bytes() == 300U);
	assert(table.Find(reinterpret_cast<void *>(0x1000U), reinterpret_cast<void *>(0x77U)) != NULL);
	assert(table.Find(reinterpret_cast<void *>(0x3000U), NULL) == NULL);

	// Model destruction drops every lighting variant of that model only.
	assert(table.Forget_Model(reinterpret_cast<void *>(0x1000U)) == 2U);
	assert(table.Live() == 1U && table.Bytes() == 100U && released.size() == 2U);
	assert(table.Find(reinterpret_cast<void *>(0x1000U), NULL) == NULL);
	assert(table.Find(reinterpret_cast<void *>(0x2000U), NULL) != NULL);
	// Tombstones keep later probes reachable and are reused.
	Ready(table, 0x1000U, 0x99U, 4U, 50U);
	assert(table.Forget_User_Lighting(reinterpret_cast<void *>(0x1000U),
		reinterpret_cast<void *>(0x99U)) == 1U);
	assert(table.Forget_User_Lighting(reinterpret_cast<void *>(0x1000U),
		reinterpret_cast<void *>(0x99U)) == 0U);

	// LRU eviction never drops geometry drawn in the current frame.
	released.clear();
	Ready(table, 0x4000U, 0U, 9U, 100U);
	Ready(table, 0x5000U, 0U, 7U, 100U);
	assert(table.Bytes() == 300U);
	assert(table.Enforce_Budget(150U, 9U) == 2U);
	assert(table.Bytes() == 100U && released.size() == 2U);
	assert(table.Find(reinterpret_cast<void *>(0x4000U), NULL) != NULL);
	assert(table.Enforce_Budget(0U, 9U) == 0U);

	// Stale entries of every state are reclaimed when the table is full.
	StaticMeshEntry *stale = table.Insert(reinterpret_cast<void *>(0x6000U), NULL);
	stale->state = STATIC_MESH_ENTRY_INELIGIBLE;
	stale->last_used_frame = 10U;
	assert(table.Evict_Stale(5000U, 1800U) == 2U);
	assert(table.Live() == 0U);

	// Invalidation (DX8MeshRendererClass::Invalidate) releases all storage.
	released.clear();
	Ready(table, 0x7000U, 0U, 1U, 10U);
	Ready(table, 0x8000U, 0U, 1U, 10U);
	table.Clear();
	assert(table.Live() == 0U && table.Bytes() == 0U && released.size() == 2U);
}

static void Test_Table_Fills_And_Compacts()
{
	static StaticMeshCacheTable table;
	table.Set_Release_Callback(Release);
	const uint32_t limit = (StaticMeshCacheTable::Capacity * 3U) / 4U;
	for (uint32_t i = 0U; i < limit; ++i) {
		assert(table.Insert(reinterpret_cast<void *>(0x10000U + i * 16U), NULL) != NULL);
	}
	assert(table.Insert(reinterpret_cast<void *>(0x9U), NULL) == NULL);
	for (uint32_t i = 0U; i < limit; i += 2U) {
		assert(table.Forget_Model(reinterpret_cast<void *>(0x10000U + i * 16U)) == 1U);
	}
	// Tombstone-heavy tables compact instead of refusing new entries.
	for (uint32_t i = 0U; i < limit / 2U; ++i) {
		assert(table.Insert(reinterpret_cast<void *>(0x900000U + i * 16U), NULL) != NULL);
	}
	for (uint32_t i = 1U; i < limit; i += 2U) {
		assert(table.Find(reinterpret_cast<void *>(0x10000U + i * 16U), NULL) != NULL);
	}
	for (uint32_t i = 0U; i < limit / 2U; ++i) {
		assert(table.Find(reinterpret_cast<void *>(0x900000U + i * 16U), NULL) != NULL);
	}
	table.Clear();
}

int main()
{
	Test_Builder_Batches_And_Reuse();
	Test_Builder_Splits_At_Sixteen_Bit_Windows();
	Test_Windows_Merge_Small_And_Split_Large();
	Test_Material_Snapshot_And_Colors();
	Test_Lighting_Signature();
	Test_Table_Lifetime_Budget_And_Invalidation();
	Test_Table_Fills_And_Compacts();
	std::puts("Static mesh cache host contract PASS");
	return 0;
}
