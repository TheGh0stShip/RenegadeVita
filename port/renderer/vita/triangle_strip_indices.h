#pragma once

#include <cstddef>
#include <cstdint>

namespace RenegadeVitaRenderer {

// Translate the DX8 strip topology for the indexed triangle-list emitter.
// Preserve alternating winding and degenerates; validate before writing.
inline bool Expand_Triangle_Strip(const uint16_t *source, size_t source_capacity,
	size_t first_index, size_t triangle_count, uint16_t *output, size_t output_capacity)
{
	if (first_index > source_capacity || triangle_count > output_capacity / 3U) return false;
	if (triangle_count == 0U) return true;
	const size_t available = source_capacity - first_index;
	if (source == nullptr || output == nullptr || available < 2U || triangle_count > available - 2U) return false;
	for (size_t triangle = 0; triangle < triangle_count; ++triangle) {
		const size_t start = first_index + triangle;
		const bool odd = (triangle & 1U) != 0U;
		output[triangle * 3U] = source[start + (odd ? 1U : 0U)];
		output[triangle * 3U + 1U] = source[start + (odd ? 0U : 1U)];
		output[triangle * 3U + 2U] = source[start + 2U];
	}
	return true;
}

} // namespace RenegadeVitaRenderer
