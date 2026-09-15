#ifndef WW3D_VITA_INDEXED_MESH_BATCH_H
#define WW3D_VITA_INDEXED_MESH_BATCH_H

#include <cstdint>
#include <cstring>

// Reuse vertices only within one unchanged original material/texture batch.
// Hash collisions emit another identical vertex; they never change triangles.
// Fixed storage bounds both transient GPU indices and the 16-bit vertex range.
class VitaIndexedMeshBatch {
public:
    enum { Slots = 8192, IndexCapacity = 12288 };
    VitaIndexedMeshBatch() : entries_{}, generation_(0), count_(0), vertices_(0), last_(0) {}
    void Reset() {
        if (++generation_ == 0) {
            std::memset(entries_, 0, sizeof(entries_));
            generation_ = 1;
        }
        count_ = vertices_ = 0;
    }
    bool Full() const { return count_ > IndexCapacity - 3; }
    // Call only for validated complete triangles and after Full() is handled.
    bool Append(uint32_t source) {
        Entry &entry = entries_[source % Slots];
        const bool fresh = entry.generation != generation_ || entry.source != source;
        if (fresh) {
            entry = {generation_, source, vertices_++};
        }
        indices_[count_++] = static_cast<uint16_t>(entry.vertex);
        last_ = source;
        return fresh;
    }
    uint32_t Count() const { return count_; }
    uint32_t Vertices() const { return vertices_; }
    uint32_t Last() const { return last_; }
    const uint16_t *Indices() const { return indices_; }
private:
    struct Entry { uint32_t generation, source, vertex; };
    Entry entries_[Slots];
    uint16_t indices_[IndexCapacity];
    uint32_t generation_, count_, vertices_, last_;
};

#endif
