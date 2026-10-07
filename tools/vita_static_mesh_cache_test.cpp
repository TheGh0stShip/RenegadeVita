// Host contract for the GPU-resident static mesh cache data model.
#include <cassert>
#include <cstdio>
#include <cstdlib>
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

// ---------------------------------------------------------------------------
// Static_Mesh_Cache_Lookup state machine against a mock WW3D/GL side. The
// mock stores and compares its inputs through the same entry fields the
// renderer uses (counts, alternate flag, material snapshots, lighting
// signature), so these cases pin the production decisions.

struct MockInputs {
	uint32_t counts = 12U;
	bool alternate = false;
	float material = 1.0f;
	float ambient = 1.0f;
	float world = 1.0f;
	bool lit = false;
	bool eligible = true;
	bool build_fails = false;
	StaticMeshUploadResult upload = STATIC_MESH_UPLOAD_OK;
	uint32_t bytes = 1000U;
};

static uint32_t g_next_buffer = 100U;
static uint32_t g_forbidden_family = 0U;

struct MockOps {
	StaticMeshCacheTable &table;
	const MockInputs &in;
	uint32_t validates;
	uint32_t builds;

	MockOps(StaticMeshCacheTable &owner, const MockInputs &inputs) :
		table(owner), in(inputs), validates(0U), builds(0U) {}

	StaticMeshMaterialSnapshot Snapshot() const {
		StaticMeshMaterialSnapshot snapshot = {};
		snapshot.material = reinterpret_cast<void *>(0x55U);
		snapshot.diffuse[0] = in.material;
		snapshot.lighting = in.lit ? 1U : 0U;
		return snapshot;
	}
	StaticMeshLightingSignature Signature() const {
		StaticMeshLightingSignature signature = {};
		signature.uses_lighting = 1U;
		signature.has_environment = 1U;
		signature.ambient[0] = in.ambient;
		signature.light_count = 1U;
		signature.light_direction[0][2] = -1.0f;
		signature.world[0] = in.world;
		return signature;
	}
	StaticMeshRebuildReason Validate(const StaticMeshEntry &entry) {
		// Entries of a forgotten family may hold dangling material pointers.
		assert(g_forbidden_family == 0U || entry.family != g_forbidden_family);
		++validates;
		if (entry.vertex_count != in.counts) return STATIC_MESH_REBUILD_COUNTS;
		if (entry.alternate_materials != in.alternate) return STATIC_MESH_REBUILD_ALTERNATE;
		for (uint32_t i = 0U; i < entry.material_count; ++i)
			if (!Static_Mesh_Snapshot_Equal(entry.materials[i], Snapshot()))
				return STATIC_MESH_REBUILD_MATERIAL;
		if (!entry.lighting.uses_lighting) return STATIC_MESH_REBUILD_NONE;
		return Static_Mesh_Lighting_Difference(entry.lighting, Signature());
	}
	void Observe(StaticMeshEntry &entry) {
		Describe(entry);
		for (uint32_t i = 0U; i < entry.material_count; ++i) entry.materials[i] = Snapshot();
		if (entry.lighting.uses_lighting) entry.lighting = Signature();
	}
	void Describe(StaticMeshEntry &entry) {
		entry.vertex_count = in.counts;
		entry.alternate_materials = in.alternate;
	}
	StaticMeshBuildResult Build(bool &uses_lighting) {
		++builds;
		uses_lighting = false;
		if (in.build_fails) return STATIC_MESH_BUILD_FAILED;
		if (!in.eligible) return STATIC_MESH_BUILD_INELIGIBLE;
		uses_lighting = in.lit;
		return STATIC_MESH_BUILD_OK;
	}
	bool Retain_Materials(StaticMeshEntry &entry) {
		const StaticMeshMaterialSnapshot snapshot = Snapshot();
		return Static_Mesh_Retain_Materials(entry, &snapshot, 1U);
	}
	StaticMeshUploadResult Upload(StaticMeshEntry &entry) {
		if (in.upload != STATIC_MESH_UPLOAD_OK) return in.upload;
		assert(entry.vertex_buffer == 0U && entry.batches == NULL && entry.materials == NULL);
		entry.vertex_buffer = ++g_next_buffer;
		entry.index_buffer = ++g_next_buffer;
		entry.batches = static_cast<StaticMeshBatch *>(std::calloc(1U, sizeof(StaticMeshBatch)));
		entry.batch_count = 1U;
		entry.materials = static_cast<StaticMeshMaterialSnapshot *>(
			std::malloc(sizeof(StaticMeshMaterialSnapshot)));
		*entry.materials = Snapshot();
		entry.material_count = 1U;
		table.Account(entry, in.bytes);
		return STATIC_MESH_UPLOAD_OK;
	}
	void Capture_Lighting(StaticMeshEntry &entry) { entry.lighting = Signature(); }
	uint32_t Built_Triangles() const { return 4U; }
};

static const void *const kModel = reinterpret_cast<void *>(0x1000U);
static const void *const kMeshA = reinterpret_cast<void *>(0xA000U);
static const void *const kMeshB = reinterpret_cast<void *>(0xB000U);
enum { kRetry = 300U, kStale = 1800U };

struct DrawResult {
	StaticMeshEntry *entry;
	bool built;
	uint32_t validates;
	uint32_t builds;
};

static DrawResult Draw_Full(StaticMeshCacheTable &table, StaticMeshCacheStatistics &stats,
	const MockInputs &in, const void *mesh, uint32_t frame)
{
	MockOps ops(table, in);
	DrawResult result = {NULL, false, 0U, 0U};
	result.entry = Static_Mesh_Cache_Lookup(table, stats, kModel, NULL, mesh, frame,
		static_cast<uint32_t>(kRetry), static_cast<uint32_t>(kStale), ops, result.built);
	result.validates = ops.validates;
	result.builds = ops.builds;
	// Every replayed entry has passed validation and holds streams.
	if (result.entry != NULL) {
		assert(result.entry->state == STATIC_MESH_ENTRY_READY);
		assert(result.entry->vertex_buffer != 0U && result.entry->batches != NULL);
	}
	return result;
}

static StaticMeshEntry *Draw(StaticMeshCacheTable &table, StaticMeshCacheStatistics &stats,
	const MockInputs &in, const void *mesh, uint32_t frame)
{
	return Draw_Full(table, stats, in, mesh, frame).entry;
}

static void Test_Unlit_Instances_Share_One_Entry()
{
	static StaticMeshCacheTable table;
	table.Set_Release_Callback(Release);
	StaticMeshCacheStatistics stats = {};
	MockInputs a, b;
	b.world = 7.0f;  // unlit colours never read the transform
	DrawResult first = Draw_Full(table, stats, a, kMeshA, 1U);
	assert(first.entry != NULL && first.built && first.entry->instance == NULL);
	DrawResult second = Draw_Full(table, stats, b, kMeshB, 1U);
	assert(second.entry == first.entry && !second.built);
	for (uint32_t frame = 2U; frame < 10U; ++frame) {
		assert(Draw(table, stats, a, kMeshA, frame) == first.entry);
		assert(Draw(table, stats, b, kMeshB, frame) == first.entry);
	}
	assert(stats.builds == 1U && stats.hits == 17U && stats.lit_families == 0U);
	assert(table.Live() == 1U && table.Bytes() == 1000U && stats.upload_bytes == 1000U);
	table.Clear();
}

static void Test_Lit_Instances_Keep_Their_Own_Entries()
{
	static StaticMeshCacheTable table;
	table.Set_Release_Callback(Release);
	StaticMeshCacheStatistics stats = {};
	MockInputs a, b;
	a.lit = b.lit = true;
	b.world = 2.0f;  // a second copy of the model, rotated differently
	DrawResult first = Draw_Full(table, stats, a, kMeshA, 1U);
	assert(first.entry != NULL && first.built && first.entry->instance == kMeshA);
	DrawResult second = Draw_Full(table, stats, b, kMeshB, 1U);
	assert(second.entry != NULL && second.built && second.entry->instance == kMeshB);
	StaticMeshEntry *entry_a = first.entry;
	StaticMeshEntry *entry_b = second.entry;
	assert(entry_a != entry_b);
	StaticMeshEntry *marker = table.Find(kModel, NULL);
	assert(marker != NULL && marker->state == STATIC_MESH_ENTRY_PER_INSTANCE);
	assert(marker->vertex_buffer == 0U && marker->bytes == 0U && marker->materials == NULL);
	assert(entry_a->family == marker->family && entry_b->family == marker->family);
	// Before per-instance keying the two transforms invalidated one shared
	// entry on every draw. Now both replay for as long as they hold still.
	for (uint32_t frame = 2U; frame < 200U; ++frame) {
		assert(Draw(table, stats, a, kMeshA, frame) == entry_a);
		assert(Draw(table, stats, b, kMeshB, frame) == entry_b);
	}
	assert(stats.builds == 2U && stats.rebuilds == 0U && stats.collisions == 0U);
	assert(stats.volatile_entries == 0U && table.Volatile() == 0U);
	assert(stats.lit_families == 1U && table.Live() == 3U && table.Bytes() == 2000U);
	assert(stats.max_frame_builds == 2U && stats.max_frame_upload_bytes == 2000U);
	// A one-off change (a building's power state) costs one rebuild.
	a.ambient = 0.5f;
	DrawResult changed = Draw_Full(table, stats, a, kMeshA, 300U);
	assert(changed.entry == entry_a && changed.built);
	assert(stats.rebuilds == 1U && stats.rebuild_reasons[STATIC_MESH_REBUILD_AMBIENT] == 1U);
	// A marker never replays, even without an instance key.
	MockOps ops(table, a);
	bool built = false;
	assert(Static_Mesh_Cache_Lookup(table, stats, kModel, NULL, NULL, 301U,
		static_cast<uint32_t>(kRetry), static_cast<uint32_t>(kStale), ops, built) == NULL);
	assert(ops.builds == 0U && ops.validates == 0U);
	table.Clear();
}

static void Test_Same_Frame_Collision_Goes_Volatile_And_Frees_Buffers()
{
	static StaticMeshCacheTable table;
	table.Set_Release_Callback(Release);
	StaticMeshCacheStatistics stats = {};
	MockInputs in;
	in.lit = true;
	StaticMeshEntry *entry = Draw(table, stats, in, kMeshA, 1U);
	assert(entry != NULL && Draw(table, stats, in, kMeshA, 5U) == entry);
	released.clear();
	// The same instance drawn again this frame under another light environment.
	MockInputs other = in;
	other.ambient = 0.25f;
	assert(Draw(table, stats, other, kMeshA, 5U) == NULL);
	assert(entry->state == STATIC_MESH_ENTRY_VOLATILE && table.Volatile() == 1U);
	assert(stats.collisions == 1U && stats.rebuilds == 0U && stats.builds == 1U);
	assert(stats.rebuild_reasons[STATIC_MESH_REBUILD_AMBIENT] == 1U);
	assert(released.size() == 1U && table.Bytes() == 0U && entry->vertex_buffer == 0U);
	assert(entry->batches == NULL && entry->materials != NULL);
	table.Clear();
	assert(table.Volatile() == 0U);
}

static void Test_Volatile_Recovers_With_Hysteresis()
{
	static StaticMeshCacheTable table;
	table.Set_Release_Callback(Release);
	StaticMeshCacheStatistics stats = {};
	MockInputs in;
	in.lit = true;
	StaticMeshEntry *entry = Draw(table, stats, in, kMeshA, 1U);
	assert(entry != NULL);
	// Turning on the very next frame: animated, so no burst of rebuilds.
	in.world = 2.0f;
	assert(Draw(table, stats, in, kMeshA, 2U) == NULL);
	assert(entry->state == STATIC_MESH_ENTRY_VOLATILE && stats.rapid_volatile == 1U);
	assert(stats.rebuild_reasons[STATIC_MESH_REBUILD_WORLD] == 1U && table.Bytes() == 0U);
	assert(stats.builds == 1U && stats.rebuilds == 0U);
	// While it keeps moving it is compared once per sample period only.
	uint32_t validates = 0U;
	for (uint32_t frame = 3U; frame < 200U; ++frame) {
		in.world = static_cast<float>(frame);
		DrawResult moving = Draw_Full(table, stats, in, kMeshA, frame);
		assert(moving.entry == NULL && moving.builds == 0U);
		validates += moving.validates;
	}
	// Samples at frames 32, 62, ..., 182.
	assert(validates == 6U);
	assert(table.Volatile() == 1U && stats.volatile_recoveries == 0U);
	// Parked: four unchanged samples (about four seconds) bring it back.
	uint32_t frame = 200U;
	uint32_t recovered_at = 0U;
	for (; frame < 400U && recovered_at == 0U; ++frame) {
		DrawResult parked = Draw_Full(table, stats, in, kMeshA, frame);
		if (parked.entry != NULL) {
			assert(parked.built && parked.entry == entry);
			recovered_at = frame;
		}
	}
	assert(recovered_at != 0U && stats.volatile_recoveries == 1U && table.Volatile() == 0U);
	assert(recovered_at - 199U > 3U * STATIC_MESH_VOLATILE_SAMPLE_FRAMES);
	assert(recovered_at - 199U <= 5U * STATIC_MESH_VOLATILE_SAMPLE_FRAMES);
	assert(entry->state == STATIC_MESH_ENTRY_READY && entry->bytes == 1000U);
	// Moving again after recovery returns at once and must then hold still
	// twice as long before the next attempt.
	in.world = -1.0f;
	const uint32_t second_start = recovered_at + 10U;
	assert(Draw(table, stats, in, kMeshA, second_start) == NULL);
	assert(entry->state == STATIC_MESH_ENTRY_VOLATILE && entry->volatile_level == 2U);
	assert(Static_Mesh_Volatile_Required_Samples(entry->volatile_level) == 8U);
	uint32_t second = 0U;
	for (frame = second_start + 1U; frame < second_start + 600U && second == 0U; ++frame) {
		if (Draw(table, stats, in, kMeshA, frame) != NULL) second = frame;
	}
	assert(second != 0U && second - second_start > 7U * STATIC_MESH_VOLATILE_SAMPLE_FRAMES);
	assert(stats.volatile_recoveries == 2U);
	// A long stable period forgives the history.
	for (frame = second + 1U; frame < second + kStale + 10U; ++frame) {
		assert(Draw(table, stats, in, kMeshA, frame) == entry);
	}
	assert(entry->rebuilds == 0U && entry->volatile_level == 0U);
	// The backoff is capped.
	assert(Static_Mesh_Volatile_Required_Samples(200U) ==
		static_cast<uint32_t>(STATIC_MESH_VOLATILE_STABLE_SAMPLES) <<
		STATIC_MESH_VOLATILE_MAX_BACKOFF);
	table.Clear();
}

static void Test_Repeated_Rebuilds_Reach_The_Limit()
{
	static StaticMeshCacheTable table;
	table.Set_Release_Callback(Release);
	StaticMeshCacheStatistics stats = {};
	MockInputs in;
	StaticMeshEntry *entry = Draw(table, stats, in, kMeshA, 1U);
	assert(entry != NULL);
	uint32_t frame = 1U;
	for (uint32_t change = 1U; change <= StaticMeshCacheTable::MaxRebuilds; ++change) {
		frame += 10U;
		in.material = static_cast<float>(change) * 0.1f;
		assert(Draw(table, stats, in, kMeshA, frame) == entry);
	}
	assert(stats.rebuilds == StaticMeshCacheTable::MaxRebuilds);
	frame += 10U;
	in.material = 0.9f;
	assert(Draw(table, stats, in, kMeshA, frame) == NULL);
	assert(entry->state == STATIC_MESH_ENTRY_VOLATILE && table.Volatile() == 1U);
	assert(stats.rebuild_reasons[STATIC_MESH_REBUILD_MATERIAL] == 5U);
	table.Clear();
}

static void Test_Forgotten_Family_Is_Retired_Unread()
{
	static StaticMeshCacheTable table;
	table.Set_Release_Callback(Release);
	StaticMeshCacheStatistics stats = {};
	MockInputs a, b;
	a.lit = b.lit = true;
	b.world = 3.0f;
	assert(Draw(table, stats, a, kMeshA, 1U) != NULL);
	assert(Draw(table, stats, b, kMeshB, 1U) != NULL);
	const uint32_t family = table.Find(kModel, NULL)->family;
	// Model destruction or a material switch: the marker goes, the instance
	// entries (which probe elsewhere) stay until their family is checked.
	released.clear();
	assert(table.Forget_Model(kModel) == 1U && table.Live() == 2U);
	g_forbidden_family = family;
	DrawResult first = Draw_Full(table, stats, a, kMeshA, 2U);
	assert(first.entry != NULL && first.built && first.entry->family != family);
	assert(stats.stale_instances == 1U && released.size() == 1U);
	DrawResult second = Draw_Full(table, stats, b, kMeshB, 2U);
	assert(second.entry != NULL && second.built && second.entry->family == first.entry->family);
	assert(stats.stale_instances == 2U && table.Live() == 3U && table.Bytes() == 2000U);
	// Forgetting the user-lighting key retires the family the same way.
	assert(table.Forget_User_Lighting(kModel, NULL) == 1U);
	g_forbidden_family = first.entry->family;
	assert(Draw(table, stats, a, kMeshA, 3U) != NULL && stats.stale_instances == 3U);
	g_forbidden_family = 0U;
	table.Clear();
}

static void Test_Oversize_And_Allocation_Failures()
{
	static StaticMeshCacheTable table;
	table.Set_Release_Callback(Release);
	StaticMeshCacheStatistics stats = {};
	MockInputs in;
	in.upload = STATIC_MESH_UPLOAD_OVERSIZE;
	DrawResult rejected = Draw_Full(table, stats, in, kMeshA, 1U);
	assert(rejected.entry == NULL && rejected.builds == 1U);
	assert(stats.oversize_rejects == 1U && stats.allocation_failures == 0U);
	// The size cannot change while the inputs hold, so it is not retried.
	for (uint32_t frame = 2U; frame < 1000U; ++frame) {
		DrawResult again = Draw_Full(table, stats, in, kMeshA, frame);
		assert(again.entry == NULL && again.builds == 0U);
	}
	// A material change reconsiders it.
	in.material = 0.5f;
	in.upload = STATIC_MESH_UPLOAD_OK;
	assert(Draw(table, stats, in, kMeshA, 1000U) != NULL);
	table.Clear();

	StaticMeshCacheStatistics failures = {};
	in.upload = STATIC_MESH_UPLOAD_FAILED;
	assert(Draw(table, failures, in, kMeshA, 1U) == NULL);
	assert(failures.allocation_failures == 1U && failures.oversize_rejects == 0U);
	in.upload = STATIC_MESH_UPLOAD_OK;
	for (uint32_t frame = 2U; frame < 1U + kRetry; ++frame) {
		DrawResult waiting = Draw_Full(table, failures, in, kMeshA, frame);
		assert(waiting.entry == NULL && waiting.builds == 0U);
	}
	assert(Draw(table, failures, in, kMeshA, 1U + kRetry) != NULL);
	table.Clear();

	// An ineligible verdict holds until its inputs change.
	StaticMeshCacheStatistics verdicts = {};
	in.eligible = false;
	assert(Draw(table, verdicts, in, kMeshA, 1U) == NULL && verdicts.ineligible == 1U);
	in.eligible = true;
	for (uint32_t frame = 2U; frame < 2000U; ++frame) {
		DrawResult held = Draw_Full(table, verdicts, in, kMeshA, frame);
		assert(held.entry == NULL && held.builds == 0U);
	}
	in.alternate = true;
	assert(Draw(table, verdicts, in, kMeshA, 2000U) != NULL);
	assert(verdicts.rebuild_reasons[STATIC_MESH_REBUILD_ALTERNATE] == 1U);
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
	Test_Unlit_Instances_Share_One_Entry();
	Test_Lit_Instances_Keep_Their_Own_Entries();
	Test_Same_Frame_Collision_Goes_Volatile_And_Frees_Buffers();
	Test_Volatile_Recovers_With_Hysteresis();
	Test_Repeated_Rebuilds_Reach_The_Limit();
	Test_Forgotten_Family_Is_Retired_Unread();
	Test_Oversize_And_Allocation_Failures();
	std::puts("Static mesh cache host contract PASS");
	return 0;
}
