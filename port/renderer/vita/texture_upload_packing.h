#pragma once

#include <stddef.h>
#include <stdint.h>

// Pure, host-testable helpers for the RVTX1 texture upload switch
// (ux0:data/renegade/user/config/tutorial-texture-v1.flag). The DX8 boundary
// owns the GL calls; this header only fixes the flag grammar and the texel
// re-packing so both can be proven without a compiler on the device.
namespace RenegadeVitaTexturePacking {

// Mask bits accepted after "RVTX1 ".
enum {
	// Archive A1R5G5B5 TGAs keep 16-bit GPU texels (RGBA5551) instead of the
	// RGBA8888 expansion. Same 5/5/5/1 fields, moved, never rounded.
	MODE_PACK_A1R5G5B5 = 1U,
	MODE_KNOWN_BITS = 1U
};

// Accepts exactly "RVTX1 <hex digit>\n" (the strict 8-byte style of the other
// RVxx1 switches). Unknown bits are dropped; anything else is 0 = unchanged.
inline unsigned Parse_Mode(const char *data, size_t size)
{
	if (data == NULL || size != 8U || data[0] != 'R' || data[1] != 'V' ||
		data[2] != 'T' || data[3] != 'X' || data[4] != '1' || data[5] != ' ' ||
		data[7] != '\n') {
		return 0U;
	}
	const char digit = data[6];
	unsigned value;
	if (digit >= '0' && digit <= '9') value = static_cast<unsigned>(digit - '0');
	else if (digit >= 'A' && digit <= 'F') value = 10U + static_cast<unsigned>(digit - 'A');
	else if (digit >= 'a' && digit <= 'f') value = 10U + static_cast<unsigned>(digit - 'a');
	else return 0U;
	return value & MODE_KNOWN_BITS;
}

// D3D A1R5G5B5 (A:15 R:14-10 G:9-5 B:4-0, little-endian, as Targa/the DX8
// surface store it) -> GL_UNSIGNED_SHORT_5_5_5_1 (R:15-11 G:10-6 B:5-1 A:0),
// the layout vitaGL stores natively as SCE_GXM_TEXTURE_FORMAT_U5U5U5U1_RGBA.
inline uint16_t Pack_RGBA5551_From_A1R5G5B5(uint16_t pixel)
{
	return static_cast<uint16_t>(((pixel & 0x7fffU) << 1U) | (pixel >> 15U));
}

// Inverse, for proofs only: every 16-bit value round-trips.
inline uint16_t Unpack_A1R5G5B5_From_RGBA5551(uint16_t packed)
{
	return static_cast<uint16_t>((packed >> 1U) | ((packed & 1U) << 15U));
}

// Re-packs one tightly packed destination row from a surface row of `width`
// little-endian A1R5G5B5 texels. Returns the FNV-1a style identity mix of the
// packed words (diagnostic only; not the RGBA8888 checksum domain).
inline uint32_t Pack_A1R5G5B5_Row(const unsigned char *source, unsigned width,
	uint16_t *destination, uint32_t checksum)
{
	for (unsigned x = 0U; x < width; ++x) {
		const uint16_t pixel = static_cast<uint16_t>(source[x * 2U]) |
			static_cast<uint16_t>(static_cast<uint16_t>(source[x * 2U + 1U]) << 8U);
		const uint16_t packed = Pack_RGBA5551_From_A1R5G5B5(pixel);
		destination[x] = packed;
		checksum = (checksum ^ packed) * 16777619U;
	}
	return checksum;
}

// vitaGL gpu_alloc_texture storage for a linear level: rows padded to 8 texels.
inline uint64_t Linear_Texture_Bytes(unsigned width, unsigned height,
	unsigned bytes_per_texel)
{
	return static_cast<uint64_t>((width + 7U) & ~7U) * height * bytes_per_texel;
}

} // namespace RenegadeVitaTexturePacking
