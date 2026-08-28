#pragma once

#include <stddef.h>
#include <stdint.h>

// Pure, host-testable part of the DDS-to-vitaGL boundary. DDSFileClass yields
// an engine ARGB value; VitaGL receives byte-addressed RGBA. Keeping this
// conversion here prevents a silent red/blue or alpha-order regression.
namespace RenegadeVitaTextureUpload {

inline void Store_RGBA_From_ARGB(uint32_t argb, unsigned char *destination)
{
	destination[0] = static_cast<unsigned char>((argb >> 16U) & 0xffU);
	destination[1] = static_cast<unsigned char>((argb >> 8U) & 0xffU);
	destination[2] = static_cast<unsigned char>(argb & 0xffU);
	destination[3] = static_cast<unsigned char>((argb >> 24U) & 0xffU);
}

// DDSFileClass addresses pixels from the retail image's top row. Gameplay
// uploads must preserve that row order; a previous Vita-side bottom-up
// conversion mirrored character, door, powerup, scope, and objective textures.
inline void Store_RGBA_From_ARGB_At(uint32_t argb, unsigned source_x,
	unsigned source_y, unsigned width, unsigned char *destination)
{
	Store_RGBA_From_ARGB(argb,
		destination + (static_cast<size_t>(source_y) * width + source_x) * 4U);
}

// Retained only for intentionally bottom-up diagnostic surfaces. Retail DDS
// gameplay uploads use Store_RGBA_From_ARGB_At.
inline void Store_RGBA_From_ARGB_Flipped(uint32_t argb, unsigned source_x,
	unsigned source_y, unsigned width, unsigned height,
	unsigned char *destination)
{
	const unsigned destination_y = height - 1U - source_y;
	Store_RGBA_From_ARGB(argb,
		destination + (static_cast<size_t>(destination_y) * width + source_x) * 4U);
}

inline void Build_Checkerboard_RGBA(unsigned char *destination)
{
	static const uint32_t pixels[4] = {
		0xffff00ffU, 0xff000000U, 0xff000000U, 0xffff00ffU
	};
	for (unsigned index = 0U; index < 4U; ++index) {
		Store_RGBA_From_ARGB(pixels[index], destination + index * 4U);
	}
}

} // namespace RenegadeVitaTextureUpload
