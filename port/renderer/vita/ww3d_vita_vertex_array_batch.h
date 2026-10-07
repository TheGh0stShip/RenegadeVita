#ifndef WW3D_VITA_VERTEX_ARRAY_BATCH_H
#define WW3D_VITA_VERTEX_ARRAY_BATCH_H

#include <cstdint>
#include <new>

// Client vertex streams for one unchanged original material/texture batch of
// the per-frame mesh path. Every mesh vertex the batch references is stored
// once, in first-reference order, and each corner becomes a 16-bit index to
// it. Streams are separate (structure of arrays) because vitaGL copies
// [0, highest index] * stride bytes of every enabled client array per draw.
// Storage is sized per mesh and reused; it never outlives the draw that
// consumes it (vitaGL copies client arrays and indices before returning).
class VitaVertexArrayBatch {
public:
	enum { MaxVertices = 65535 };
	VitaVertexArrayBatch()
		: positions_(nullptr), colors_(nullptr), uv0_(nullptr), uv1_(nullptr),
		  remap_(nullptr), sources_(nullptr), indices_(nullptr),
		  vertex_capacity_(0), index_capacity_(0), vertices_(0), count_(0),
		  last_slot_(0) {}
	~VitaVertexArrayBatch() { Release(); }
	VitaVertexArrayBatch(const VitaVertexArrayBatch &) = delete;
	VitaVertexArrayBatch &operator=(const VitaVertexArrayBatch &) = delete;

	// Sizes storage for a mesh with mesh_vertices vertices whose batches
	// reference at most index_capacity corners. Call only between batches.
	// False (with all storage released) when the mesh exceeds the 16-bit
	// index range or allocation fails; the caller then stays immediate.
	bool Reserve(uint32_t mesh_vertices, uint32_t index_capacity) {
		if (mesh_vertices == 0U || mesh_vertices > MaxVertices || index_capacity == 0U)
			return false;
		if (mesh_vertices > vertex_capacity_) {
			float *positions = new (std::nothrow) float[mesh_vertices * 3U];
			float *colors = new (std::nothrow) float[mesh_vertices * 4U];
			float *uv0 = new (std::nothrow) float[mesh_vertices * 2U];
			float *uv1 = new (std::nothrow) float[mesh_vertices * 2U];
			uint32_t *remap = new (std::nothrow) uint32_t[mesh_vertices];
			uint32_t *sources = new (std::nothrow) uint32_t[mesh_vertices];
			if (positions == nullptr || colors == nullptr || uv0 == nullptr ||
				uv1 == nullptr || remap == nullptr || sources == nullptr) {
				delete[] positions; delete[] colors; delete[] uv0; delete[] uv1;
				delete[] remap; delete[] sources;
				Release();
				return false;
			}
			for (uint32_t i = 0U; i < mesh_vertices; ++i) remap[i] = 0U;
			delete[] positions_; delete[] colors_; delete[] uv0_; delete[] uv1_;
			delete[] remap_; delete[] sources_;
			positions_ = positions; colors_ = colors; uv0_ = uv0; uv1_ = uv1;
			remap_ = remap; sources_ = sources;
			vertex_capacity_ = mesh_vertices;
		}
		if (index_capacity > index_capacity_) {
			uint16_t *indices = new (std::nothrow) uint16_t[index_capacity];
			if (indices == nullptr) {
				Release();
				return false;
			}
			delete[] indices_;
			indices_ = indices;
			index_capacity_ = index_capacity;
		}
		return true;
	}
	void Release() {
		delete[] positions_; delete[] colors_; delete[] uv0_; delete[] uv1_;
		delete[] remap_; delete[] sources_; delete[] indices_;
		positions_ = colors_ = uv0_ = uv1_ = nullptr;
		remap_ = sources_ = nullptr;
		indices_ = nullptr;
		vertex_capacity_ = index_capacity_ = 0U;
		vertices_ = count_ = last_slot_ = 0U;
	}
	// Forgets the current batch in O(its vertices); storage stays reserved.
	void Reset() {
		for (uint32_t i = 0U; i < vertices_; ++i) remap_[sources_[i]] = 0U;
		vertices_ = count_ = last_slot_ = 0U;
	}
	// Appends one corner (source < reserved mesh vertices, at most the
	// reserved index count per batch). Returns true when the vertex is new to
	// the batch; the caller must then fill its slot's attributes.
	bool Append(uint32_t source, uint32_t *slot) {
		uint32_t &entry = remap_[source];
		const bool fresh = entry == 0U;
		if (fresh) {
			sources_[vertices_] = source;
			entry = ++vertices_;
		}
		last_slot_ = entry - 1U;
		indices_[count_++] = static_cast<uint16_t>(last_slot_);
		*slot = last_slot_;
		return fresh;
	}
	float *Position(uint32_t slot) { return positions_ + slot * 3U; }
	float *Color(uint32_t slot) { return colors_ + slot * 4U; }
	float *Uv0(uint32_t slot) { return uv0_ + slot * 2U; }
	float *Uv1(uint32_t slot) { return uv1_ + slot * 2U; }
	const float *Positions() const { return positions_; }
	const float *Colors() const { return colors_; }
	const float *Uv0s() const { return uv0_; }
	const float *Uv1s() const { return uv1_; }
	const uint16_t *Indices() const { return indices_; }
	uint32_t Count() const { return count_; }
	uint32_t Vertices() const { return vertices_; }
	// Slot of the most recently appended corner (valid when Count() != 0).
	uint32_t Last_Slot() const { return last_slot_; }
	uint32_t Bytes() const {
		return vertex_capacity_ * (11U * sizeof(float) + 2U * sizeof(uint32_t)) +
			index_capacity_ * sizeof(uint16_t);
	}

private:
	float *positions_, *colors_, *uv0_, *uv1_;
	uint32_t *remap_, *sources_;
	uint16_t *indices_;
	uint32_t vertex_capacity_, index_capacity_, vertices_, count_, last_slot_;
};

#endif
