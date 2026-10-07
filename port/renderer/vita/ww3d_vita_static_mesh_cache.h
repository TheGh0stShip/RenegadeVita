#ifndef WW3D_VITA_STATIC_MESH_CACHE_H
#define WW3D_VITA_STATIC_MESH_CACHE_H

#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>

// GPU-resident replay of unlit, untransformed-UV MeshClass passes.
//
// The original DX8 mesh renderer registered each (MeshModelClass, user
// lighting array) pair once, copied its positions, colors and UVs into static
// vertex buffers, froze its texture/shader categories, and then drew those
// buffers with hardware transform every frame until
// DX8MeshRendererClass::Invalidate(). The Vita boundary instead re-evaluated
// every vertex through immediate mode every frame. This cache restores the
// original ownership model for the subset whose per-vertex output cannot
// change between frames: rigid (non-skin) meshes whose materials are unlit
// and whose active stages use pass-through UVs without a texture transform.
//
// Everything here is plain data so the build, validation, invalidation and
// budget rules can run on the host. The renderer owns every GL call.
namespace RenegadeVitaRenderer {

struct StaticMeshVertex {
	float position[3];
	uint8_t color[4];
	float uv0[2];
	float uv1[2];
};
static_assert(sizeof(StaticMeshVertex) == 32, "cached vertex stride is 32 bytes");

enum {
	STATIC_MESH_VERTEX_STRIDE = 32,
	STATIC_MESH_POSITION_OFFSET = 0,
	STATIC_MESH_COLOR_OFFSET = 12,
	STATIC_MESH_UV0_OFFSET = 16,
	STATIC_MESH_UV1_OFFSET = 24,
	// Local indices are 16-bit; each batch addresses its own vertex window.
	STATIC_MESH_MAX_BATCH_VERTICES = 65535,
};

// One unchanged original texture/material/shader run, in original order.
struct StaticMeshBatch {
	void *texture0;
	void *texture1;
	void *material;
	uint32_t shader_bits;
	uint32_t first_vertex;
	uint32_t vertex_count;
	uint32_t first_index;
	uint32_t index_count;
	// First vertex addressed by this batch's (window-relative) indices.
	uint32_t window_base;
	bool detail_stage;
};

// Lets consecutive batches share one set of client-array pointers whenever
// their combined vertex span still fits 16-bit indices. Each pointer change
// re-patches vitaGL's vertex program, so fewer windows mean fewer patches.
// Rewrites each batch's local indices relative to its window.
inline void Static_Mesh_Assign_Windows(StaticMeshBatch *batches, uint32_t batch_count,
	uint16_t *indices)
{
	uint32_t window = 0U;
	bool open = false;
	for (uint32_t index = 0U; index < batch_count; ++index) {
		StaticMeshBatch &batch = batches[index];
		if (!open || batch.first_vertex + batch.vertex_count - window >
			static_cast<uint32_t>(STATIC_MESH_MAX_BATCH_VERTICES) + 1U) {
			window = batch.first_vertex;
			open = true;
		}
		batch.window_base = window;
		const uint32_t delta = batch.first_vertex - window;
		if (delta == 0U) continue;
		for (uint32_t corner = 0U; corner < batch.index_count; ++corner) {
			indices[batch.first_index + corner] =
				static_cast<uint16_t>(indices[batch.first_index + corner] + delta);
		}
	}
}

// Every material whose state determined cached colors or UV eligibility.
// Materials remain live objects in the original renderer, so their state is
// compared every frame; any difference forces a rebuild of this entry.
struct StaticMeshMaterialSnapshot {
	void *material;
	float diffuse[3];
	float ambient[3];
	float emissive[3];
	float opacity;
	void *mapper[2];
	int uv_source[2];
	uint8_t lighting;
	uint8_t diffuse_source;
	uint8_t ambient_source;
	uint8_t emissive_source;
};

inline bool Static_Mesh_Snapshot_Equal(const StaticMeshMaterialSnapshot &left,
	const StaticMeshMaterialSnapshot &right)
{
	// Compare field by field so structure padding never affects the result.
	for (unsigned i = 0U; i < 3U; ++i) {
		if (left.diffuse[i] != right.diffuse[i] || left.ambient[i] != right.ambient[i] ||
			left.emissive[i] != right.emissive[i]) return false;
	}
	return left.material == right.material && left.opacity == right.opacity &&
		left.mapper[0] == right.mapper[0] && left.mapper[1] == right.mapper[1] &&
		left.uv_source[0] == right.uv_source[0] && left.uv_source[1] == right.uv_source[1] &&
		left.lighting == right.lighting && left.diffuse_source == right.diffuse_source &&
		left.ambient_source == right.ambient_source &&
		left.emissive_source == right.emissive_source;
}

// Inputs of lit vertex colours. Light directions are world-space, so a
// static object's colours depend only on its environment, transform and
// materials. Moving or re-lit objects fail this comparison and rebuild until
// they are marked volatile.
struct StaticMeshLightingSignature {
	uint8_t uses_lighting;
	uint8_t has_environment;
	uint32_t dx8_ambient;
	uint32_t light_count;
	float ambient[3];
	float light_direction[4][3];
	float light_diffuse[4][3];
	float world[12];
};

// Why a cached entry no longer matches its inputs. Telemetry only: every
// reason forces the same rebuild.
enum StaticMeshRebuildReason {
	STATIC_MESH_REBUILD_NONE = 0,
	STATIC_MESH_REBUILD_COUNTS,     // vertex, triangle or pass count
	STATIC_MESH_REBUILD_ALTERNATE,  // alternate material description toggled
	STATIC_MESH_REBUILD_MATERIAL,   // a material snapshot field
	STATIC_MESH_REBUILD_AMBIENT,    // environment presence, DX8 or equivalent ambient
	STATIC_MESH_REBUILD_LIGHTS,     // light count, direction or diffuse
	STATIC_MESH_REBUILD_WORLD,      // world rotation/scale under directional light
	STATIC_MESH_REBUILD_REASON_COUNT
};

// Same comparisons as Static_Mesh_Lighting_Equal; reports the first input
// group that differs.
inline StaticMeshRebuildReason Static_Mesh_Lighting_Difference(
	const StaticMeshLightingSignature &cached, const StaticMeshLightingSignature &current)
{
	// Unlit colours never read lighting state.
	if (!cached.uses_lighting) return STATIC_MESH_REBUILD_NONE;
	if (cached.has_environment != current.has_environment) return STATIC_MESH_REBUILD_AMBIENT;
	if (!cached.has_environment) {
		return cached.dx8_ambient == current.dx8_ambient ?
			STATIC_MESH_REBUILD_NONE : STATIC_MESH_REBUILD_AMBIENT;
	}
	for (unsigned i = 0U; i < 3U; ++i)
		if (cached.ambient[i] != current.ambient[i]) return STATIC_MESH_REBUILD_AMBIENT;
	if (cached.light_count != current.light_count) return STATIC_MESH_REBUILD_LIGHTS;
	for (uint32_t light = 0U; light < cached.light_count && light < 4U; ++light) {
		for (unsigned i = 0U; i < 3U; ++i) {
			if (cached.light_direction[light][i] != current.light_direction[light][i] ||
				cached.light_diffuse[light][i] != current.light_diffuse[light][i])
				return STATIC_MESH_REBUILD_LIGHTS;
		}
	}
	// World normals only matter when a directional light contributes.
	if (cached.light_count != 0U) {
		for (unsigned i = 0U; i < 12U; ++i)
			if (cached.world[i] != current.world[i]) return STATIC_MESH_REBUILD_WORLD;
	}
	return STATIC_MESH_REBUILD_NONE;
}

inline bool Static_Mesh_Lighting_Equal(const StaticMeshLightingSignature &cached,
	const StaticMeshLightingSignature &current)
{
	return Static_Mesh_Lighting_Difference(cached, current) == STATIC_MESH_REBUILD_NONE;
}

inline uint8_t Static_Mesh_Color_Byte(float value)
{
	if (!(value > 0.0f)) return 0U;
	if (value >= 1.0f) return 255U;
	return static_cast<uint8_t>(value * 255.0f + 0.5f);
}

// Allocation failure is an ordinary "not cacheable" outcome; never abort.
template <typename T>
class StaticMeshArray {
public:
	StaticMeshArray() : data_(NULL), count_(0U), capacity_(0U) {}
	~StaticMeshArray() { std::free(data_); }
	StaticMeshArray(const StaticMeshArray &) = delete;
	StaticMeshArray &operator=(const StaticMeshArray &) = delete;
	void Clear() { count_ = 0U; }
	void Release() { std::free(data_); data_ = NULL; count_ = capacity_ = 0U; }
	bool Reserve(uint32_t capacity) {
		if (capacity <= capacity_) return true;
		uint32_t grown = capacity_ != 0U ? capacity_ : 64U;
		while (grown < capacity) {
			if (grown > 0x7fffffffU / 2U) { grown = capacity; break; }
			grown *= 2U;
		}
		if (static_cast<size_t>(grown) > SIZE_MAX / sizeof(T)) return false;
		T *replacement = static_cast<T *>(std::realloc(data_, sizeof(T) * grown));
		if (replacement == NULL) return false;
		data_ = replacement;
		capacity_ = grown;
		return true;
	}
	T *Push() {
		if (count_ == capacity_ && !Reserve(count_ + 1U)) return NULL;
		return &data_[count_++];
	}
	void Pop() { if (count_ != 0U) --count_; }
	T *Data() { return data_; }
	const T *Data() const { return data_; }
	uint32_t Count() const { return count_; }
	T &operator[](uint32_t index) { return data_[index]; }
	const T &operator[](uint32_t index) const { return data_[index]; }
private:
	T *data_;
	uint32_t count_;
	uint32_t capacity_;
};

// Builds one cache entry's vertex/index streams. Vertices are shared only
// inside one batch, exactly like the immediate indexed batch it replaces.
class StaticMeshStreamBuilder {
public:
	StaticMeshStreamBuilder()
		: map_generation_(NULL), map_local_(NULL), map_capacity_(0U),
		  generation_(0U), open_(false), failed_(false) {}
	~StaticMeshStreamBuilder() { Release(); }
	StaticMeshStreamBuilder(const StaticMeshStreamBuilder &) = delete;
	StaticMeshStreamBuilder &operator=(const StaticMeshStreamBuilder &) = delete;

	bool Begin(uint32_t source_vertex_count) {
		vertices_.Clear();
		indices_.Clear();
		batches_.Clear();
		materials_.Clear();
		open_ = false;
		failed_ = false;
		if (source_vertex_count > map_capacity_) {
			std::free(map_generation_);
			std::free(map_local_);
			map_generation_ = static_cast<uint32_t *>(
				std::calloc(source_vertex_count, sizeof(uint32_t)));
			map_local_ = static_cast<uint16_t *>(
				std::malloc(sizeof(uint16_t) * source_vertex_count));
			if (map_generation_ == NULL || map_local_ == NULL) {
				std::free(map_generation_);
				std::free(map_local_);
				map_generation_ = NULL;
				map_local_ = NULL;
				map_capacity_ = 0U;
				failed_ = true;
				return false;
			}
			map_capacity_ = source_vertex_count;
			generation_ = 0U;
		}
		source_vertex_count_ = source_vertex_count;
		return true;
	}

	bool Begin_Batch(const StaticMeshBatch &state) {
		End_Batch();
		StaticMeshBatch *batch = batches_.Push();
		if (batch == NULL) { failed_ = true; return false; }
		*batch = state;
		batch->first_vertex = vertices_.Count();
		batch->vertex_count = 0U;
		batch->first_index = indices_.Count();
		batch->index_count = 0U;
		Next_Generation();
		open_ = true;
		return true;
	}

	// Ensures three more corners fit in the current batch's 16-bit window.
	// Splitting keeps the same state; replay reapplies it harmlessly.
	bool Reserve_Triangle() {
		if (!open_ || failed_) return false;
		const StaticMeshBatch &batch = batches_[batches_.Count() - 1U];
		if (batch.vertex_count <= STATIC_MESH_MAX_BATCH_VERTICES - 3U) return true;
		const StaticMeshBatch state = batch;
		return Begin_Batch(state);
	}

	// Returns the vertex slot to fill when the source vertex is new to this
	// batch, NULL when it was already present. Check Failed() afterwards.
	StaticMeshVertex *Append(uint32_t source_vertex) {
		if (!open_ || failed_ || source_vertex >= source_vertex_count_) {
			failed_ = true;
			return NULL;
		}
		StaticMeshBatch &batch = batches_[batches_.Count() - 1U];
		uint16_t *index = indices_.Push();
		if (index == NULL) { failed_ = true; return NULL; }
		++batch.index_count;
		if (map_generation_[source_vertex] == generation_) {
			*index = map_local_[source_vertex];
			return NULL;
		}
		StaticMeshVertex *vertex = vertices_.Push();
		if (vertex == NULL) { failed_ = true; return NULL; }
		const uint16_t local = static_cast<uint16_t>(batch.vertex_count++);
		map_generation_[source_vertex] = generation_;
		map_local_[source_vertex] = local;
		*index = local;
		return vertex;
	}

	void End_Batch() {
		if (!open_) return;
		open_ = false;
		// A run whose triangles were all rejected draws nothing.
		if (batches_[batches_.Count() - 1U].index_count == 0U) batches_.Pop();
	}

	bool Add_Material(const StaticMeshMaterialSnapshot &snapshot) {
		for (uint32_t i = 0U; i < materials_.Count(); ++i) {
			if (materials_[i].material == snapshot.material) return true;
		}
		StaticMeshMaterialSnapshot *slot = materials_.Push();
		if (slot == NULL) { failed_ = true; return false; }
		*slot = snapshot;
		return true;
	}
	bool Has_Material(const void *material) const {
		for (uint32_t i = 0U; i < materials_.Count(); ++i) {
			if (materials_[i].material == material) return true;
		}
		return false;
	}

	// Call once after the last batch; see Static_Mesh_Assign_Windows.
	void Assign_Windows() {
		Static_Mesh_Assign_Windows(batches_.Data(), batches_.Count(), indices_.Data());
	}

	void Fail() { failed_ = true; }
	bool Failed() const { return failed_; }
	const StaticMeshArray<StaticMeshVertex> &Vertices() const { return vertices_; }
	const StaticMeshArray<uint16_t> &Indices() const { return indices_; }
	const StaticMeshArray<StaticMeshBatch> &Batches() const { return batches_; }
	const StaticMeshArray<StaticMeshMaterialSnapshot> &Materials() const { return materials_; }

	void Release() {
		vertices_.Release();
		indices_.Release();
		batches_.Release();
		materials_.Release();
		std::free(map_generation_);
		std::free(map_local_);
		map_generation_ = NULL;
		map_local_ = NULL;
		map_capacity_ = 0U;
		generation_ = 0U;
	}

private:
	void Next_Generation() {
		if (++generation_ == 0U) {
			std::memset(map_generation_, 0, sizeof(uint32_t) * map_capacity_);
			generation_ = 1U;
		}
	}

	StaticMeshArray<StaticMeshVertex> vertices_;
	StaticMeshArray<uint16_t> indices_;
	StaticMeshArray<StaticMeshBatch> batches_;
	StaticMeshArray<StaticMeshMaterialSnapshot> materials_;
	uint32_t *map_generation_;
	uint16_t *map_local_;
	uint32_t map_capacity_;
	uint32_t source_vertex_count_ = 0U;
	uint32_t generation_;
	bool open_;
	bool failed_;
};

enum StaticMeshEntryState {
	STATIC_MESH_ENTRY_EMPTY = 0,
	STATIC_MESH_ENTRY_TOMBSTONE,
	STATIC_MESH_ENTRY_READY,
	// The current material description cannot be cached; immediate mode owns it.
	STATIC_MESH_ENTRY_INELIGIBLE,
	// Inputs keep changing (animated material, moving lit object); immediate
	// mode owns it. Holds no GPU storage; its inputs are sampled so it can
	// return once they settle (see Static_Mesh_Cache_Lookup).
	STATIC_MESH_ENTRY_VOLATILE,
	// Shared (model, user lighting) entry whose colours turned out lit. Holds
	// no storage; it only names the family whose instances keep their own
	// entries, keyed additionally by the drawing MeshClass.
	STATIC_MESH_ENTRY_PER_INSTANCE,
};

struct StaticMeshEntry {
	const void *model;
	const void *user_lighting;
	// NULL for shared entries; the drawing MeshClass for lit instances.
	const void *instance;
	// Shared entries get a fresh id on insertion; instance entries copy their
	// marker's id. A mismatch means the marker was forgotten (model or
	// lighting array released), so the instance entry's material pointers may
	// dangle and it is dropped without being read.
	uint32_t family;
	StaticMeshEntryState state;
	uint32_t vertex_count;
	uint32_t triangle_count;
	uint32_t pass_count;
	bool alternate_materials;
	// Times this entry went VOLATILE since it was last stable for a long
	// period; doubles the stability a VOLATILE entry must show to return.
	uint8_t volatile_level;
	// Consecutive unchanged samples of a VOLATILE entry's inputs.
	uint16_t stable_samples;
	uint32_t rebuilds;
	uint32_t built_frame;
	uint32_t last_used_frame;
	uint32_t retry_frame;
	uint32_t vertex_buffer;
	uint32_t index_buffer;
	uint32_t bytes;
	StaticMeshBatch *batches;
	uint32_t batch_count;
	StaticMeshMaterialSnapshot *materials;
	uint32_t material_count;
	StaticMeshLightingSignature lighting;
};

struct StaticMeshCacheStatistics {
	uint64_t hits;
	uint64_t builds;
	uint64_t rebuilds;
	uint64_t ineligible;
	uint64_t volatile_entries;
	uint64_t evictions;
	uint64_t invalidations;
	uint64_t allocation_failures;
	uint64_t cached_batches;
	uint64_t cached_triangles;
	// Misses of a READY or INELIGIBLE entry, by first differing input group.
	uint64_t rebuild_reasons[STATIC_MESH_REBUILD_REASON_COUNT];
	// A key drawn earlier in the same frame no longer matched (two draws
	// disagree about its inputs); it goes VOLATILE without rebuilding.
	uint64_t collisions;
	// Inputs changed again the frame after a (re)build; VOLATILE at once.
	uint64_t rapid_volatile;
	// VOLATILE entries whose sampled inputs settled and were rebuilt.
	uint64_t volatile_recoveries;
	// Streams above a quarter of the budget; ineligible until inputs change.
	uint64_t oversize_rejects;
	uint64_t upload_bytes;
	uint64_t lit_families;
	// Instance entries dropped because their family marker was forgotten.
	uint64_t stale_instances;
	// Build attempts and uploaded bytes in the current frame, and their
	// maxima since the renderer last logged and cleared them.
	uint32_t frame;
	uint32_t frame_builds;
	uint32_t frame_upload_bytes;
	uint32_t max_frame_builds;
	uint32_t max_frame_upload_bytes;
};

// Open-addressed table keyed by (model, user lighting, instance). Shared
// entries probe from the model's hash so every one of a model is reachable
// from that sequence; instance entries probe from a hash that also mixes the
// instance, so many instances of one model do not lengthen its probe run.
class StaticMeshCacheTable {
public:
	enum { Capacity = 16384, MaxRebuilds = 4 };
	typedef void (*ReleaseBuffers)(uint32_t vertex_buffer, uint32_t index_buffer);

	StaticMeshCacheTable() : entries_(), live_(0U), used_(0U), bytes_(0U),
		volatile_(0U), next_family_(0U), release_(NULL) {}

	void Set_Release_Callback(ReleaseBuffers release) { release_ = release; }

	StaticMeshEntry *Find(const void *model, const void *user_lighting,
		const void *instance = NULL) {
		uint32_t slot = Hash(model, instance);
		for (uint32_t probe = 0U; probe < Capacity; ++probe) {
			StaticMeshEntry &entry = entries_[slot];
			if (entry.state == STATIC_MESH_ENTRY_EMPTY) return NULL;
			if (entry.state != STATIC_MESH_ENTRY_TOMBSTONE && entry.model == model &&
				entry.user_lighting == user_lighting && entry.instance == instance)
				return &entry;
			slot = (slot + 1U) & (Capacity - 1U);
		}
		return NULL;
	}

	// Returns NULL when the table is too full; the caller then draws normally.
	// Shared entries (no instance) start a new family; instance entries join
	// the given one. Any insertion may compact the table and move entries.
	StaticMeshEntry *Insert(const void *model, const void *user_lighting,
		const void *instance = NULL, uint32_t family = 0U) {
		if (used_ >= (Capacity * 3U) / 4U) Compact();
		if (used_ >= (Capacity * 3U) / 4U) return NULL;
		uint32_t slot = Hash(model, instance);
		StaticMeshEntry *reuse = NULL;
		for (uint32_t probe = 0U; probe < Capacity; ++probe) {
			StaticMeshEntry &entry = entries_[slot];
			if (entry.state == STATIC_MESH_ENTRY_TOMBSTONE && reuse == NULL) reuse = &entry;
			if (entry.state == STATIC_MESH_ENTRY_EMPTY) {
				if (reuse == NULL) { reuse = &entry; ++used_; }
				break;
			}
			slot = (slot + 1U) & (Capacity - 1U);
		}
		if (reuse == NULL) return NULL;
		std::memset(reuse, 0, sizeof(*reuse));
		reuse->model = model;
		reuse->user_lighting = user_lighting;
		reuse->instance = instance;
		reuse->family = instance == NULL ? Next_Family() : family;
		reuse->state = STATIC_MESH_ENTRY_INELIGIBLE;
		++live_;
		return reuse;
	}

	// The only way the renderer changes a live entry's state, so the
	// resident VOLATILE count stays exact.
	void Set_State(StaticMeshEntry &entry, StaticMeshEntryState state) {
		if (entry.state == STATIC_MESH_ENTRY_VOLATILE) --volatile_;
		if (state == STATIC_MESH_ENTRY_VOLATILE) ++volatile_;
		entry.state = state;
	}

	// Frees GPU buffers and replay batches. Material snapshots and the
	// lighting signature stay: a VOLATILE entry keeps comparing them.
	void Release_Buffers(StaticMeshEntry &entry) {
		if ((entry.vertex_buffer != 0U || entry.index_buffer != 0U) && release_ != NULL)
			release_(entry.vertex_buffer, entry.index_buffer);
		entry.vertex_buffer = entry.index_buffer = 0U;
		if (entry.bytes <= bytes_) bytes_ -= entry.bytes;
		else bytes_ = 0U;
		entry.bytes = 0U;
		std::free(entry.batches);
		entry.batches = NULL;
		entry.batch_count = 0U;
	}

	// Frees GPU buffers and per-entry arrays but keeps the key and counters.
	void Release_Storage(StaticMeshEntry &entry) {
		Release_Buffers(entry);
		std::free(entry.materials);
		entry.materials = NULL;
		entry.material_count = 0U;
	}

	// Never reads material pointers, so it is safe for entries whose model or
	// lighting array has already been released.
	void Remove(StaticMeshEntry &entry) {
		if (entry.state == STATIC_MESH_ENTRY_EMPTY ||
			entry.state == STATIC_MESH_ENTRY_TOMBSTONE) return;
		if (entry.state == STATIC_MESH_ENTRY_VOLATILE) --volatile_;
		Release_Storage(entry);
		std::memset(&entry, 0, sizeof(entry));
		entry.state = STATIC_MESH_ENTRY_TOMBSTONE;
		--live_;
	}

	// Mirrors model destruction and material-description switches. Removes
	// every shared entry and family marker of the model; instance entries,
	// which probe elsewhere, are retired through their family id.
	uint32_t Forget_Model(const void *model) {
		uint32_t removed = 0U;
		uint32_t slot = Hash(model);
		for (uint32_t probe = 0U; probe < Capacity; ++probe) {
			StaticMeshEntry &entry = entries_[slot];
			if (entry.state == STATIC_MESH_ENTRY_EMPTY) break;
			if (entry.state != STATIC_MESH_ENTRY_TOMBSTONE && entry.model == model) {
				Remove(entry);
				++removed;
			}
			slot = (slot + 1U) & (Capacity - 1U);
		}
		return removed;
	}

	// Removes the shared entry or family marker; the family's instance
	// entries are retired through their family id.
	uint32_t Forget_User_Lighting(const void *model, const void *user_lighting) {
		StaticMeshEntry *entry = Find(model, user_lighting);
		if (entry == NULL) return 0U;
		Remove(*entry);
		return 1U;
	}

	// Mirrors DX8MeshRendererClass::Invalidate().
	void Clear() {
		for (uint32_t i = 0U; i < Capacity; ++i) {
			if (entries_[i].state != STATIC_MESH_ENTRY_EMPTY &&
				entries_[i].state != STATIC_MESH_ENTRY_TOMBSTONE) Release_Storage(entries_[i]);
		}
		std::memset(entries_, 0, sizeof(entries_));
		live_ = used_ = 0U;
		bytes_ = 0U;
		volatile_ = 0U;
	}

	// Adopts built streams' bookkeeping. Ownership of the arrays transfers.
	void Account(StaticMeshEntry &entry, uint32_t bytes) {
		entry.bytes = bytes;
		bytes_ += bytes;
	}

	// Evicts least-recently-used ready entries not drawn in current_frame
	// until the resident total fits the budget. Returns evicted entries.
	uint32_t Enforce_Budget(uint32_t budget, uint32_t current_frame) {
		uint32_t evicted = 0U;
		while (bytes_ > budget) {
			StaticMeshEntry *oldest = NULL;
			for (uint32_t i = 0U; i < Capacity; ++i) {
				StaticMeshEntry &entry = entries_[i];
				if (entry.state != STATIC_MESH_ENTRY_READY || entry.bytes == 0U ||
					entry.last_used_frame == current_frame) continue;
				if (oldest == NULL || static_cast<int32_t>(entry.last_used_frame -
					oldest->last_used_frame) < 0) oldest = &entry;
			}
			if (oldest == NULL) break;
			Remove(*oldest);
			++evicted;
		}
		return evicted;
	}

	// Drops entries of any state not drawn for max_age frames. Used when the
	// table is full so retired level geometry cannot pin every slot.
	uint32_t Evict_Stale(uint32_t current_frame, uint32_t max_age) {
		uint32_t evicted = 0U;
		for (uint32_t i = 0U; i < Capacity; ++i) {
			StaticMeshEntry &entry = entries_[i];
			if (entry.state == STATIC_MESH_ENTRY_EMPTY ||
				entry.state == STATIC_MESH_ENTRY_TOMBSTONE) continue;
			if (current_frame - entry.last_used_frame > max_age) {
				Remove(entry);
				++evicted;
			}
		}
		return evicted;
	}

	uint32_t Live() const { return live_; }
	uint32_t Bytes() const { return bytes_; }
	uint32_t Volatile() const { return volatile_; }

private:
	static uint32_t Hash(const void *model, const void *instance = NULL) {
		uintptr_t key = reinterpret_cast<uintptr_t>(model);
		if (instance != NULL)
			key ^= reinterpret_cast<uintptr_t>(instance) * static_cast<uintptr_t>(0x9e3779b1U);
		key ^= key >> 16;
		key *= 0x7feb352dU;
		key ^= key >> 15;
		return static_cast<uint32_t>(key) & (Capacity - 1U);
	}

	uint32_t Next_Family() {
		if (++next_family_ == 0U) next_family_ = 1U;
		return next_family_;
	}

	// Rehash in place to drop tombstones when the table fills with them.
	void Compact() {
		if (used_ == live_) return;
		StaticMeshEntry *saved = static_cast<StaticMeshEntry *>(
			std::malloc(sizeof(StaticMeshEntry) * (live_ != 0U ? live_ : 1U)));
		if (saved == NULL) return;
		uint32_t count = 0U;
		for (uint32_t i = 0U; i < Capacity; ++i) {
			if (entries_[i].state != STATIC_MESH_ENTRY_EMPTY &&
				entries_[i].state != STATIC_MESH_ENTRY_TOMBSTONE) saved[count++] = entries_[i];
		}
		std::memset(entries_, 0, sizeof(entries_));
		used_ = live_ = 0U;
		for (uint32_t i = 0U; i < count; ++i) {
			uint32_t slot = Hash(saved[i].model, saved[i].instance);
			while (entries_[slot].state != STATIC_MESH_ENTRY_EMPTY)
				slot = (slot + 1U) & (Capacity - 1U);
			entries_[slot] = saved[i];
			++used_;
			++live_;
		}
		std::free(saved);
	}

	StaticMeshEntry entries_[Capacity];
	uint32_t live_;
	uint32_t used_;
	uint32_t bytes_;
	uint32_t volatile_;
	// Never reset, so a family id is not reused after Clear().
	uint32_t next_family_;
	ReleaseBuffers release_;
};

enum {
	// A VOLATILE entry compares its inputs with the previous sample at most
	// once per this many frames (only when drawn), so it costs a frame
	// compare per draw in between.
	STATIC_MESH_VOLATILE_SAMPLE_FRAMES = 30,
	// Unchanged samples needed before the first return to eligibility...
	STATIC_MESH_VOLATILE_STABLE_SAMPLES = 4,
	// ...doubled per further VOLATILE episode, up to this many doublings.
	STATIC_MESH_VOLATILE_MAX_BACKOFF = 4,
};

enum StaticMeshBuildResult {
	STATIC_MESH_BUILD_OK = 0,
	STATIC_MESH_BUILD_INELIGIBLE,
	STATIC_MESH_BUILD_FAILED,  // host allocation failure, not a verdict
};

enum StaticMeshUploadResult {
	STATIC_MESH_UPLOAD_OK = 0,
	STATIC_MESH_UPLOAD_OVERSIZE,  // larger than a quarter of the budget
	STATIC_MESH_UPLOAD_FAILED,    // budget, reserve or GL allocation
};

enum StaticMeshMissAction {
	STATIC_MESH_MISS_REBUILD = 0,
	STATIC_MESH_MISS_COLLISION,
	STATIC_MESH_MISS_RAPID,
	STATIC_MESH_MISS_LIMIT,
};

inline uint32_t Static_Mesh_Retry_Frame(uint32_t frame, uint32_t delay)
{
	const uint32_t retry = frame + delay;
	return retry != 0U ? retry : 1U;
}

// Decides what a changed READY or INELIGIBLE entry does. previous_use is its
// last_used_frame before this draw.
inline StaticMeshMissAction Static_Mesh_Miss_Action(StaticMeshEntry &entry,
	uint32_t previous_use, uint32_t frame)
{
	if (entry.state == STATIC_MESH_ENTRY_READY) {
		// Drawn earlier this frame with other inputs: every rebuild would be
		// undone by the next draw of the same key.
		if (previous_use == frame) return STATIC_MESH_MISS_COLLISION;
		// Changed on two consecutive frames: animated, not a one-off change.
		if (frame - entry.built_frame == 1U) return STATIC_MESH_MISS_RAPID;
	}
	if (++entry.rebuilds > StaticMeshCacheTable::MaxRebuilds) return STATIC_MESH_MISS_LIMIT;
	return STATIC_MESH_MISS_REBUILD;
}

inline uint32_t Static_Mesh_Volatile_Required_Samples(uint8_t volatile_level)
{
	uint32_t shift = volatile_level > 1U ? volatile_level - 1U : 0U;
	if (shift > STATIC_MESH_VOLATILE_MAX_BACKOFF) shift = STATIC_MESH_VOLATILE_MAX_BACKOFF;
	return static_cast<uint32_t>(STATIC_MESH_VOLATILE_STABLE_SAMPLES) << shift;
}

// The caller must already have released the entry's GPU buffers.
inline void Static_Mesh_Mark_Volatile(StaticMeshCacheTable &table,
	StaticMeshCacheStatistics &statistics, StaticMeshEntry &entry, uint32_t frame)
{
	table.Set_State(entry, STATIC_MESH_ENTRY_VOLATILE);
	++statistics.volatile_entries;
	if (entry.volatile_level != 0xffU) ++entry.volatile_level;
	entry.stable_samples = 0U;
	entry.retry_frame = frame + STATIC_MESH_VOLATILE_SAMPLE_FRAMES;
}

// Keeps the snapshots behind an ineligible verdict so a later change to them
// reconsiders the entry. False only when the copy cannot be allocated.
inline bool Static_Mesh_Retain_Materials(StaticMeshEntry &entry,
	const StaticMeshMaterialSnapshot *materials, uint32_t count)
{
	if (count == 0U) return true;
	StaticMeshMaterialSnapshot *copy = static_cast<StaticMeshMaterialSnapshot *>(
		std::malloc(sizeof(StaticMeshMaterialSnapshot) * count));
	if (copy == NULL) return false;
	std::memcpy(copy, materials, sizeof(StaticMeshMaterialSnapshot) * count);
	std::free(entry.materials);
	entry.materials = copy;
	entry.material_count = count;
	return true;
}

inline void Static_Mesh_Statistics_Frame(StaticMeshCacheStatistics &statistics, uint32_t frame)
{
	if (statistics.frame == frame) return;
	statistics.frame = frame;
	statistics.frame_builds = 0U;
	statistics.frame_upload_bytes = 0U;
}

// Insert, reclaiming entries not drawn for stale_frames when the table is full.
inline StaticMeshEntry *Static_Mesh_Insert(StaticMeshCacheTable &table,
	StaticMeshCacheStatistics &statistics, const void *model, const void *user_lighting,
	const void *instance, uint32_t family, uint32_t frame, uint32_t stale_frames)
{
	StaticMeshEntry *entry = table.Insert(model, user_lighting, instance, family);
	if (entry == NULL) {
		statistics.evictions += table.Evict_Stale(frame, stale_frames);
		entry = table.Insert(model, user_lighting, instance, family);
		if (entry == NULL) return NULL;
	}
	entry->last_used_frame = frame;
	return entry;
}

// Entry state machine for one rigid mesh draw. Returns the entry to replay,
// or NULL when the immediate path must draw; built reports a fresh upload.
// The returned pointer is valid until the next insertion.
//
// Ops supplies every WW3D read and GL call:
//   StaticMeshRebuildReason Validate(const StaticMeshEntry &) - compare inputs
//   void Observe(StaticMeshEntry &)   - record current inputs (VOLATILE only)
//   void Describe(StaticMeshEntry &)  - store counts and alternate flag
//   StaticMeshBuildResult Build(bool &uses_lighting) - fill the stream builder
//   bool Retain_Materials(StaticMeshEntry &)          - keep verdict snapshots
//   StaticMeshUploadResult Upload(StaticMeshEntry &)  - GPU buffers, batches,
//                                                       materials, Account()
//   void Capture_Lighting(StaticMeshEntry &)
//   uint32_t Built_Triangles()
//
// Every replayed entry has passed Validate against the inputs of this draw,
// so the key only selects which candidate to test; keying lit instances
// separately never changes what is drawn.
template <typename Ops>
StaticMeshEntry *Static_Mesh_Cache_Lookup(StaticMeshCacheTable &table,
	StaticMeshCacheStatistics &statistics, const void *model, const void *user_lighting,
	const void *instance_key, uint32_t frame, uint32_t retry_frames,
	uint32_t stale_frames, Ops &ops, bool &built)
{
	built = false;
	Static_Mesh_Statistics_Frame(statistics, frame);
	const void *instance = NULL;
	uint32_t family = 0U;
	StaticMeshEntry *entry = table.Find(model, user_lighting);
	if (entry != NULL && entry->state == STATIC_MESH_ENTRY_PER_INSTANCE) {
		// A family marker holds no streams; without an instance to key the
		// lit streams by, the immediate path draws.
		if (instance_key == NULL) return NULL;
		entry->last_used_frame = frame;
		family = entry->family;
		instance = instance_key;
		entry = table.Find(model, user_lighting, instance);
		if (entry != NULL && entry->family != family) {
			table.Remove(*entry);
			++statistics.stale_instances;
			entry = NULL;
		}
	}
	if (entry != NULL) {
		const uint32_t previous_use = entry->last_used_frame;
		entry->last_used_frame = frame;
		if (entry->state == STATIC_MESH_ENTRY_VOLATILE) {
			if (static_cast<int32_t>(frame - entry->retry_frame) < 0) return NULL;
			entry->retry_frame = frame + STATIC_MESH_VOLATILE_SAMPLE_FRAMES;
			if (ops.Validate(*entry) != STATIC_MESH_REBUILD_NONE) {
				entry->stable_samples = 0U;
				ops.Observe(*entry);
				return NULL;
			}
			if (entry->stable_samples != 0xffffU) ++entry->stable_samples;
			if (entry->stable_samples <
				Static_Mesh_Volatile_Required_Samples(entry->volatile_level)) return NULL;
			// Settled: rebuild once with no headroom left, so an input that
			// changes again sends it straight back with a longer wait.
			++statistics.volatile_recoveries;
			entry->rebuilds = StaticMeshCacheTable::MaxRebuilds;
			table.Release_Storage(*entry);
		} else {
			const StaticMeshRebuildReason reason = ops.Validate(*entry);
			if (entry->state == STATIC_MESH_ENTRY_READY && reason == STATIC_MESH_REBUILD_NONE) {
				// Rebuilds are forgiven after a long stable period, so occasional
				// lighting changes over a level do not exhaust the volatile limit.
				if ((entry->rebuilds != 0U || entry->volatile_level != 0U) &&
					frame - entry->built_frame > stale_frames) {
					entry->rebuilds = 0U;
					entry->volatile_level = 0U;
				}
				++statistics.hits;
				return entry;
			}
			// Unchanged ineligible geometry stays on immediate mode. Only an
			// allocation failure (nonzero retry frame) is attempted again later.
			if (entry->state == STATIC_MESH_ENTRY_INELIGIBLE &&
				reason == STATIC_MESH_REBUILD_NONE &&
				(entry->retry_frame == 0U ||
				 static_cast<int32_t>(frame - entry->retry_frame) < 0)) return NULL;
			if (reason != STATIC_MESH_REBUILD_NONE) {
				++statistics.rebuild_reasons[reason];
				const StaticMeshMissAction action =
					Static_Mesh_Miss_Action(*entry, previous_use, frame);
				if (action != STATIC_MESH_MISS_REBUILD) {
					if (action == STATIC_MESH_MISS_COLLISION) ++statistics.collisions;
					else if (action == STATIC_MESH_MISS_RAPID) ++statistics.rapid_volatile;
					table.Release_Buffers(*entry);
					ops.Observe(*entry);
					Static_Mesh_Mark_Volatile(table, statistics, *entry, frame);
					return NULL;
				}
				++statistics.rebuilds;
			}
			table.Release_Storage(*entry);
		}
	} else {
		entry = Static_Mesh_Insert(table, statistics, model, user_lighting, instance,
			family, frame, stale_frames);
		if (entry == NULL) return NULL;
	}

	ops.Describe(*entry);
	table.Set_State(*entry, STATIC_MESH_ENTRY_INELIGIBLE);
	entry->retry_frame = 0U;
	entry->stable_samples = 0U;
	std::memset(&entry->lighting, 0, sizeof(entry->lighting));
	if (++statistics.frame_builds > statistics.max_frame_builds)
		statistics.max_frame_builds = statistics.frame_builds;
	bool uses_lighting = false;
	const StaticMeshBuildResult result = ops.Build(uses_lighting);
	if (result == STATIC_MESH_BUILD_FAILED) {
		++statistics.allocation_failures;
		entry->retry_frame = Static_Mesh_Retry_Frame(frame, retry_frames);
		return NULL;
	}
	if (result == STATIC_MESH_BUILD_INELIGIBLE) {
		++statistics.ineligible;
		// Without the snapshots a material change could not reconsider the
		// entry; VOLATILE sampling retries it instead.
		if (!ops.Retain_Materials(*entry))
			Static_Mesh_Mark_Volatile(table, statistics, *entry, frame);
		return NULL;
	}
	if (uses_lighting && instance == NULL && instance_key != NULL) {
		// Lit colours depend on each instance's transform and light
		// environment. The shared entry becomes the family marker and these
		// streams are cached for the drawing instance instead.
		table.Set_State(*entry, STATIC_MESH_ENTRY_PER_INSTANCE);
		family = entry->family;
		instance = instance_key;
		++statistics.lit_families;
		StaticMeshEntry *stale = table.Find(model, user_lighting, instance);
		if (stale != NULL) {
			table.Remove(*stale);
			++statistics.stale_instances;
		}
		entry = Static_Mesh_Insert(table, statistics, model, user_lighting, instance,
			family, frame, stale_frames);
		if (entry == NULL) return NULL;
		ops.Describe(*entry);
	}
	const StaticMeshUploadResult uploaded = ops.Upload(*entry);
	if (uploaded == STATIC_MESH_UPLOAD_OVERSIZE) {
		// The stream size follows from geometry and run boundaries, so a
		// retry cannot fit until the materials or counts change.
		++statistics.oversize_rejects;
		if (!ops.Retain_Materials(*entry))
			Static_Mesh_Mark_Volatile(table, statistics, *entry, frame);
		return NULL;
	}
	if (uploaded != STATIC_MESH_UPLOAD_OK) {
		++statistics.allocation_failures;
		entry->retry_frame = Static_Mesh_Retry_Frame(frame, retry_frames);
		return NULL;
	}
	if (uses_lighting) ops.Capture_Lighting(*entry);
	table.Set_State(*entry, STATIC_MESH_ENTRY_READY);
	entry->built_frame = frame;
	++statistics.builds;
	statistics.cached_batches += entry->batch_count;
	statistics.cached_triangles += ops.Built_Triangles();
	statistics.upload_bytes += entry->bytes;
	statistics.frame_upload_bytes += entry->bytes;
	if (statistics.frame_upload_bytes > statistics.max_frame_upload_bytes)
		statistics.max_frame_upload_bytes = statistics.frame_upload_bytes;
	built = true;
	return entry;
}

} // namespace RenegadeVitaRenderer

#endif
