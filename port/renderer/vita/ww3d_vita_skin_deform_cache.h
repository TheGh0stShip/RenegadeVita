#ifndef WW3D_VITA_SKIN_DEFORM_CACHE_H
#define WW3D_VITA_SKIN_DEFORM_CACHE_H

#include <cstdint>
#include <cstring>
#include <new>

// Reuse of original MeshClass::Get_Deformed_Vertices output within one frame
// (reports/SKIN_PATH_COST.md item 4).
//
// The original DX8SkinFVFCategoryContainer deformed every visible skin once
// per flush and drew both its base passes and its procedural material passes
// from that one vertex buffer. The Vita boundary submits the base pass from
// MeshClass::Render and the queued material passes from
// DX8MeshRendererClass::Flush, so it deformed the same skin again for every
// material pass, and again for every further render of the same skin in the
// frame (material-pass-only shadow/projector/stealth renders, other cameras).
// This cache lets a later submission reuse a stored deformation only when a
// fresh deformation would produce identical bytes:
//
//  - MeshModelClass::get_deformed_vertices(dst_vert, dst_norm, htree) is a
//    pure function of exactly the model's vertex, normal and bone-link arrays,
//    its vertex count, and HTreeClass::Get_Transform(pivot) for each pivot the
//    bone links reference (OPTIMIZE_VNORMS is off, so normals are read raw;
//    the renderer validates dirty normals before every submission anyway).
//  - The model is keyed by address and Forget_Model() runs from the original
//    model reset/destruction/assignment/geometry-unique hooks before any of
//    those arrays change, so a recycled or mutated model never matches a
//    stored entry. MeshClass::Scale makes the geometry unique first.
//  - Every referenced pivot transform is copied at store time and compared
//    bitwise at lookup. Any HTree change in between (animation progress,
//    Update_Sub_Object_Transforms, Set_Transform, Control_Bone, Set_HTree,
//    cinematics, another camera's or render-to-texture render) that touches a
//    used bone misses and the caller deforms again. There is no original
//    per-HTree serial: the hierarchy-valid flag is a boolean dirty bit that
//    every Update_Sub_Object_Transforms sets again, so a valid flag at two
//    renders cannot prove that both saw the same pose.
//  - The mesh address is only a lookup hint; it is never dereferenced, and a
//    hit requires the inputs above to match, so a destroyed mesh whose address
//    is reused (or a LOD/model switch on a live mesh) cannot produce different
//    output. Entries never outlive the frame in which they were stored.
//
// Storage is fixed, allocated on first use and recycled every frame; when it
// is exhausted the caller uses the original uncached scratch path.
namespace RenegadeVitaRenderer {

struct SkinDeformCacheStatistics {
	uint64_t stores;
	uint64_t hits;
	uint64_t misses;
	uint64_t stale;
	uint64_t overflows;
	uint64_t forgets;
	uint64_t allocation_failures;
};

template <typename Vec3>
class SkinDeformCache {
public:
	enum {
		MAX_ENTRIES = 32,
		MAX_VERTICES = 8192,
		MAX_BONES = 1024,
		MATRIX_BYTES = 48
	};

	// Constant-initialized and trivially destructible, so the renderer's
	// namespace-scope instance is usable from original model hooks at any
	// point of static initialization or teardown. Release() frees storage.

	// Entries live for one rendered frame; storage is recycled afterwards.
	void Begin_Frame(uint32_t frame)
	{
		if (frame == frame_) return;
		frame_ = frame;
		entry_count_ = 0;
		used_vertices_ = 0;
		used_bones_ = 0;
		pending_valid_ = false;
	}

	// Material-pass lookup. Returns the stored deformation of `mesh` only when
	// it was produced from `model` with bitwise-identical pivot transforms.
	template <typename TransformAt>
	bool Find(const void *mesh, const void *model, int vertex_count, int pivot_count,
		TransformAt transform_at, const Vec3 **vertices, const Vec3 **normals)
	{
		for (int index = 0; index < entry_count_; ++index) {
			const Entry &entry = entries_[index];
			if (entry.mesh != mesh) continue;
			if (entry.model != model || entry.vertex_count != vertex_count ||
				entry.pivot_count != pivot_count) {
				++statistics_.stale;
				return false;
			}
			for (int bone = 0; bone < entry.bone_count; ++bone) {
				const Bone &stored = bones_[entry.bone_offset + bone];
				if (memcmp(stored.transform, transform_at(stored.pivot),
					MATRIX_BYTES) != 0) {
					++statistics_.stale;
					return false;
				}
			}
			*vertices = vertices_ + entry.vertex_offset;
			*normals = normals_ + entry.vertex_offset;
			++statistics_.hits;
			return true;
		}
		++statistics_.misses;
		return false;
	}

	// Base-pass store, step 1: drop any older entry for `mesh` and reserve
	// output storage. The caller deforms into the returned arrays and then
	// calls Commit(); the arrays stay valid for the caller's current draw
	// whether or not Commit() succeeds.
	bool Reserve(const void *mesh, const void *model, int vertex_count,
		Vec3 **vertices, Vec3 **normals)
	{
		Discard_Pending();
		Drop_Mesh(mesh);
		if (vertex_count <= 0 || !Ensure_Storage()) return false;
		if (entry_count_ >= MAX_ENTRIES || vertex_count > MAX_VERTICES - used_vertices_) {
			++statistics_.overflows;
			return false;
		}
		pending_.mesh = mesh;
		pending_.model = model;
		pending_.vertex_count = vertex_count;
		pending_.pivot_count = 0;
		pending_.vertex_offset = used_vertices_;
		pending_.bone_offset = used_bones_;
		pending_.bone_count = 0;
		pending_valid_ = true;
		used_vertices_ += vertex_count;
		*vertices = vertices_ + pending_.vertex_offset;
		*normals = normals_ + pending_.vertex_offset;
		return true;
	}

	// Base-pass store, step 2: snapshot every pivot the bone links reference
	// (one per run of equal links, as get_deformed_vertices walks them) and
	// publish the entry.
	template <typename TransformAt>
	bool Commit(const uint16_t *bone_links, int vertex_count, int pivot_count,
		TransformAt transform_at)
	{
		if (!pending_valid_) return false;
		pending_valid_ = false;
		if (bone_links == NULL || pivot_count <= 0 ||
			vertex_count != pending_.vertex_count) {
			Roll_Back_Pending();
			return false;
		}
		int bone_count = 0;
		int previous = -1;
		for (int vertex = 0; vertex < vertex_count; ++vertex) {
			const int pivot = static_cast<int>(bone_links[vertex]);
			if (pivot == previous) continue;
			if (pivot >= pivot_count) {
				Roll_Back_Pending();
				return false;
			}
			if (bone_count >= MAX_BONES - used_bones_) {
				++statistics_.overflows;
				Roll_Back_Pending();
				return false;
			}
			Bone &stored = bones_[used_bones_ + bone_count++];
			stored.pivot = pivot;
			memcpy(stored.transform, transform_at(pivot), MATRIX_BYTES);
			previous = pivot;
		}
		pending_.pivot_count = pivot_count;
		pending_.bone_count = bone_count;
		used_bones_ += bone_count;
		entries_[entry_count_++] = pending_;
		++statistics_.stores;
		return true;
	}

	// Original MeshModelClass reset/destruction/geometry-unique hook.
	void Forget_Model(const void *model)
	{
		if (pending_valid_ && pending_.model == model) Discard_Pending();
		for (int index = 0; index < entry_count_;) {
			if (entries_[index].model == model) {
				entries_[index] = entries_[--entry_count_];
				++statistics_.forgets;
			} else {
				++index;
			}
		}
	}

	void Release()
	{
		delete[] vertices_;
		delete[] normals_;
		delete[] bones_;
		vertices_ = NULL;
		normals_ = NULL;
		bones_ = NULL;
		allocation_failed_ = false;
		entry_count_ = 0;
		used_vertices_ = 0;
		used_bones_ = 0;
		pending_valid_ = false;
	}

	int Entry_Count() const { return entry_count_; }
	uint32_t Bytes() const
	{
		return vertices_ == NULL ? 0U : static_cast<uint32_t>(
			2U * MAX_VERTICES * sizeof(Vec3) + MAX_BONES * sizeof(Bone));
	}
	const SkinDeformCacheStatistics &Counters() const { return statistics_; }

private:
	struct Entry {
		const void *mesh;
		const void *model;
		int vertex_count;
		int pivot_count;
		int vertex_offset;
		int bone_offset;
		int bone_count;
	};
	struct Bone {
		int pivot;
		unsigned char transform[MATRIX_BYTES];
	};

	bool Ensure_Storage()
	{
		if (vertices_ != NULL) return true;
		if (allocation_failed_) return false;
		vertices_ = new (std::nothrow) Vec3[MAX_VERTICES];
		normals_ = new (std::nothrow) Vec3[MAX_VERTICES];
		bones_ = new (std::nothrow) Bone[MAX_BONES];
		if (vertices_ != NULL && normals_ != NULL && bones_ != NULL) return true;
		delete[] vertices_;
		delete[] normals_;
		delete[] bones_;
		vertices_ = NULL;
		normals_ = NULL;
		bones_ = NULL;
		allocation_failed_ = true;
		++statistics_.allocation_failures;
		return false;
	}

	void Drop_Mesh(const void *mesh)
	{
		for (int index = 0; index < entry_count_; ++index) {
			if (entries_[index].mesh == mesh) {
				entries_[index] = entries_[--entry_count_];
				return;
			}
		}
	}

	// The pending reservation is always the newest allocation.
	void Roll_Back_Pending()
	{
		used_vertices_ = pending_.vertex_offset;
		used_bones_ = pending_.bone_offset;
	}

	void Discard_Pending()
	{
		if (!pending_valid_) return;
		pending_valid_ = false;
		Roll_Back_Pending();
	}

	Vec3 *vertices_ = NULL;
	Vec3 *normals_ = NULL;
	Bone *bones_ = NULL;
	bool allocation_failed_ = false;
	uint32_t frame_ = 0U;
	Entry entries_[MAX_ENTRIES] = {};
	int entry_count_ = 0;
	int used_vertices_ = 0;
	int used_bones_ = 0;
	Entry pending_ = {};
	bool pending_valid_ = false;
	SkinDeformCacheStatistics statistics_ = {};
};

} // namespace RenegadeVitaRenderer

#endif
