#pragma once

#include <stdint.h>

namespace RenegadeVitaRenderer {

// Layout metadata for the original category selector's XYZ, optional N/D/S
// and zero-to-eight 2D UV channels. This is a buffer view, not an asset format.
struct CategoryFVFLayout {
	uint32_t stride;
	uint32_t normal_offset;
	uint32_t diffuse_offset;
	uint32_t specular_offset;
	uint32_t uv_offsets[8];
	uint32_t uv_count;
	bool has_normal;
	bool has_diffuse;
	bool has_specular;
};

inline bool Decode_Category_FVF(uint32_t fvf, CategoryFVFLayout &output)
{
	// Reject transformed/blended positions, reserved bits and non-2D UV sizes.
	if ((fvf & 0x0eU) != 0x02U || (fvf & ~0x0fd2U) != 0U) return false;
	const uint32_t uv_count = (fvf >> 8U) & 0x0fU;
	if (uv_count > 8U) return false;
	CategoryFVFLayout layout = {};
	layout.has_normal = (fvf & 0x10U) != 0U;
	layout.has_diffuse = (fvf & 0x40U) != 0U;
	layout.has_specular = (fvf & 0x80U) != 0U;
	layout.normal_offset = 12U;
	layout.diffuse_offset = layout.normal_offset + (layout.has_normal ? 12U : 0U);
	layout.specular_offset = layout.diffuse_offset + (layout.has_diffuse ? 4U : 0U);
	const uint32_t uv_start = layout.specular_offset + (layout.has_specular ? 4U : 0U);
	for (uint32_t channel = 0; channel < 8U; ++channel)
		layout.uv_offsets[channel] = uv_start + channel * 8U;
	layout.uv_count = uv_count;
	layout.stride = uv_start + uv_count * 8U;
	output = layout;
	return true;
}

} // namespace RenegadeVitaRenderer
