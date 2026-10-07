#ifndef WW3D_VITA_GXM_TUNING_H
#define WW3D_VITA_GXM_TUNING_H

#include <cstddef>
#include <cstdint>
#include <cstring>

// vitaGL/sceGxm sizes requested before vglInitExtended. The defaults are the
// values the campaign renderer has always used (the vitaGL and SDK defaults
// plus vglInitExtended(4 MiB immediate pool, ..., 16 MiB RAM reserve, ...)).
// Only fields named in the user flag file are overridden; with no file the
// init sequence is unchanged.
//
// Flag file: ux0:data/renegade/user/config/vitagl-sizing-v1.flag, one line:
//   "RVGX1" followed by one or more " key=value" tokens and a final '\n'.
// Keys (decimal, no sign/leading zero) and accepted ranges:
//   imm=MiB    vitaGL GL1 immediate vertex pool per frame   1..16  (4)
//   circ=MiB   vitaGL circular transient pool (all slices) 16..64 (32)
//   bufs=N     display buffers (vglSetDisplayBufferCount)   2..3   (3)
//   vdm=KiB    sceGxm VDM ring                         128..1024  (128)
//   vtx=KiB    sceGxm vertex ring                     2048..8192  (2048)
//   frag=KiB   sceGxm fragment ring                    512..4096  (512)
//   usse=KiB   sceGxm fragment USSE ring                 16..64   (16)
//   pb=MiB     sceGxm parameter buffer (CDRAM)            8..64   (16)
//   ramres=MiB user RAM left outside vitaGL's RAM pool   16..64   (16)
// KiB values must be multiples of 4. Each key may appear once. One circular
// slice (circ / bufs) must hold the immediate pool plus 1 MiB of other
// transient data (copied indices). Any violation rejects the whole file.
struct VitaGLSizing {
	enum Field {
		IMMEDIATE = 1U << 0,
		CIRCULAR = 1U << 1,
		BUFFERS = 1U << 2,
		VDM = 1U << 3,
		VERTEX = 1U << 4,
		FRAGMENT = 1U << 5,
		USSE = 1U << 6,
		PARAMETER = 1U << 7,
		RAM_RESERVE = 1U << 8
	};
	uint32_t immediate_pool_bytes;
	uint32_t circular_pool_bytes;
	uint32_t display_buffers;
	uint32_t vdm_ring_bytes;
	uint32_t vertex_ring_bytes;
	uint32_t fragment_ring_bytes;
	uint32_t fragment_usse_ring_bytes;
	uint32_t parameter_buffer_bytes;
	uint32_t ram_reserve_bytes;
	uint32_t overridden;
};

inline VitaGLSizing Default_VitaGL_Sizing()
{
	VitaGLSizing sizing;
	sizing.immediate_pool_bytes = 4U << 20;      // vglInitExtended argument 1
	sizing.circular_pool_bytes = 32U << 20;      // vgl.c CIRCULAR_POOL_SIZE_DEF
	sizing.display_buffers = 3U;                 // gxm.c gxm_display_buffer_count
	sizing.vdm_ring_bytes = 128U << 10;          // SCE_GXM_DEFAULT_VDM_RING_BUFFER_SIZE
	sizing.vertex_ring_bytes = 2U << 20;         // SCE_GXM_DEFAULT_VERTEX_RING_BUFFER_SIZE
	sizing.fragment_ring_bytes = 512U << 10;     // SCE_GXM_DEFAULT_FRAGMENT_RING_BUFFER_SIZE
	sizing.fragment_usse_ring_bytes = 16U << 10; // SCE_GXM_DEFAULT_FRAGMENT_USSE_RING_BUFFER_SIZE
	sizing.parameter_buffer_bytes = 16U << 20;   // SCE_GXM_DEFAULT_PARAMETER_BUFFER_SIZE
	sizing.ram_reserve_bytes = 16U << 20;        // vglInitExtended argument 4 (0x1000000)
	sizing.overridden = 0U;
	return sizing;
}

// Parses the complete flag file contents. Returns false (and leaves *out
// untouched) unless the text is exactly one valid line.
inline bool Parse_VitaGL_Sizing_Flag(const char *text, size_t length, VitaGLSizing *out)
{
	static const char kPrefix[] = "RVGX1";
	const size_t prefix_length = sizeof(kPrefix) - 1U;
	if (text == NULL || out == NULL || length <= prefix_length + 1U || length > 160U ||
		memcmp(text, kPrefix, prefix_length) != 0 || text[length - 1U] != '\n') {
		return false;
	}
	struct Key {
		const char *name;
		uint32_t field;
		uint32_t minimum;
		uint32_t maximum;
		uint32_t shift;
		uint32_t multiple;
	};
	static const Key kKeys[] = {
		{ "imm", VitaGLSizing::IMMEDIATE, 1U, 16U, 20U, 1U },
		{ "circ", VitaGLSizing::CIRCULAR, 16U, 64U, 20U, 1U },
		{ "bufs", VitaGLSizing::BUFFERS, 2U, 3U, 0U, 1U },
		{ "vdm", VitaGLSizing::VDM, 128U, 1024U, 10U, 4U },
		{ "vtx", VitaGLSizing::VERTEX, 2048U, 8192U, 10U, 4U },
		{ "frag", VitaGLSizing::FRAGMENT, 512U, 4096U, 10U, 4U },
		{ "usse", VitaGLSizing::USSE, 16U, 64U, 10U, 4U },
		{ "pb", VitaGLSizing::PARAMETER, 8U, 64U, 20U, 1U },
		{ "ramres", VitaGLSizing::RAM_RESERVE, 16U, 64U, 20U, 1U },
	};
	VitaGLSizing sizing = *out;
	uint32_t seen = 0U;
	size_t position = prefix_length;
	const size_t end = length - 1U;
	if (position == end) return false;
	while (position < end) {
		if (text[position] != ' ') return false;
		++position;
		const size_t name_begin = position;
		while (position < end && text[position] >= 'a' && text[position] <= 'z') ++position;
		const size_t name_length = position - name_begin;
		if (name_length == 0U || position >= end || text[position] != '=') return false;
		++position;
		const size_t digits_begin = position;
		uint32_t value = 0U;
		while (position < end && text[position] >= '0' && text[position] <= '9') {
			if (position - digits_begin >= 5U) return false;
			value = value * 10U + static_cast<uint32_t>(text[position] - '0');
			++position;
		}
		const size_t digit_count = position - digits_begin;
		if (digit_count == 0U || (digit_count > 1U && text[digits_begin] == '0')) return false;
		const Key *key = NULL;
		for (size_t index = 0U; index < sizeof(kKeys) / sizeof(kKeys[0]); ++index) {
			if (strlen(kKeys[index].name) == name_length &&
				memcmp(kKeys[index].name, text + name_begin, name_length) == 0) {
				key = &kKeys[index];
				break;
			}
		}
		if (key == NULL || (seen & key->field) != 0U || value < key->minimum ||
			value > key->maximum || value % key->multiple != 0U) {
			return false;
		}
		seen |= key->field;
		const uint32_t bytes = value << key->shift;
		switch (key->field) {
		case VitaGLSizing::IMMEDIATE: sizing.immediate_pool_bytes = bytes; break;
		case VitaGLSizing::CIRCULAR: sizing.circular_pool_bytes = bytes; break;
		case VitaGLSizing::BUFFERS: sizing.display_buffers = bytes; break;
		case VitaGLSizing::VDM: sizing.vdm_ring_bytes = bytes; break;
		case VitaGLSizing::VERTEX: sizing.vertex_ring_bytes = bytes; break;
		case VitaGLSizing::FRAGMENT: sizing.fragment_ring_bytes = bytes; break;
		case VitaGLSizing::USSE: sizing.fragment_usse_ring_bytes = bytes; break;
		case VitaGLSizing::PARAMETER: sizing.parameter_buffer_bytes = bytes; break;
		default: sizing.ram_reserve_bytes = bytes; break;
		}
	}
	// vitaGL reserves the immediate pool from the current frame's circular
	// slice; keep room for the transient index copies drawn from that slice.
	if (sizing.circular_pool_bytes / sizing.display_buffers <
		sizing.immediate_pool_bytes + (1U << 20)) {
		return false;
	}
	sizing.overridden = seen;
	*out = sizing;
	return true;
}

// Bytes between a pool base and its cursor; 0 for missing or reversed spans.
inline uint32_t VitaGL_Span_Bytes(const void *base, const void *cursor)
{
	if (base == NULL || cursor == NULL) return 0U;
	const uintptr_t begin = reinterpret_cast<uintptr_t>(base);
	const uintptr_t current = reinterpret_cast<uintptr_t>(cursor);
	return current > begin ? static_cast<uint32_t>(current - begin) : 0U;
}

// Per-window peaks of vitaGL's per-frame transient storage, sampled once per
// presented frame immediately before vglSwapBuffers. vitaGL bounds-checks the
// immediate pool only on the Renegade projective path, so used > capacity is
// an overrun into the rest of the frame's circular slice. A circular slice
// overrun turns each later transient allocation of that frame into a heap
// allocation with deferred free.
struct VitaGLPoolWindow {
	uint32_t frames;
	uint32_t immediate_peak_bytes;
	uint32_t immediate_capacity_bytes;
	uint32_t immediate_overrun_frames;
	uint64_t immediate_total_bytes;
	uint32_t circular_peak_bytes;
	uint32_t circular_slice_bytes;
	uint32_t circular_overrun_frames;

	void Reset()
	{
		frames = immediate_peak_bytes = immediate_capacity_bytes = 0U;
		immediate_overrun_frames = circular_peak_bytes = 0U;
		circular_slice_bytes = circular_overrun_frames = 0U;
		immediate_total_bytes = 0U;
	}

	void Record(uint32_t immediate_used, uint32_t immediate_capacity,
		uint32_t circular_used, uint32_t circular_slice)
	{
		++frames;
		immediate_total_bytes += immediate_used;
		if (immediate_used > immediate_peak_bytes) immediate_peak_bytes = immediate_used;
		immediate_capacity_bytes = immediate_capacity;
		if (immediate_capacity != 0U && immediate_used > immediate_capacity) {
			++immediate_overrun_frames;
		}
		if (circular_used > circular_peak_bytes) circular_peak_bytes = circular_used;
		circular_slice_bytes = circular_slice;
		if (circular_slice != 0U && circular_used > circular_slice) {
			++circular_overrun_frames;
		}
	}

	uint32_t Immediate_Average_Bytes() const
	{
		return frames != 0U ? static_cast<uint32_t>(immediate_total_bytes / frames) : 0U;
	}
};

#endif
