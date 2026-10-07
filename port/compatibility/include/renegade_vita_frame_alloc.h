#pragma once

// RVAL1: value-identical heap-allocation reuse on paths that run every frame
// or for every text-atlas build during gameplay.
//
// ux0:data/renegade/user/config/frame-alloc-v1.flag holding exactly
// "RVAL1 <hex digit>\n" (8 bytes, digit 0-9 or A-F) selects the bit mask.
// "RVAL1 0\n" restores every original allocation for A/B comparison. An absent
// or malformed file keeps DEFAULT_MODE.
//
//   bit 0 (1) TEXTURE_RGBA_SCRATCH: Create_Texture_From_Surface converts into
//             the retained per-thread upload scratch instead of a fresh
//             zero-filled vector. The scratch may grow only for creations of
//             at most MAX_SCRATCH_GROWTH_BYTES (every Render2DSentence text
//             atlas is <= 256x256); larger creations reuse it only when it
//             already has the capacity, so retained memory never exceeds
//             max(existing high-water, 256 KiB).
//   bit 1 (2) HUD_TARGET_NAME_TEMP: the per-frame target-name comparison copy
//             in hud.cpp passes WideStringClass's original temporary-buffer
//             hint instead of taking a heap buffer every frame.
//
// Both only select where identical bytes are stored, so the default enables
// them. The value is read once per process; the renderer primes it during
// initialization so no per-frame caller performs the file read.

#include <stddef.h>
#include <stdio.h>
#include <string.h>

namespace RenegadeVitaFrameAlloc {

enum : unsigned {
	TEXTURE_RGBA_SCRATCH = 1U,
	HUD_TARGET_NAME_TEMP = 2U,
	DEFAULT_MODE = 0U,
	MAX_SCRATCH_GROWTH_BYTES = 256U * 1024U
};

// Mask encoded by the flag bytes, or fallback when they are malformed.
inline unsigned Parse_Mode(const char *value, size_t size, unsigned fallback)
{
	if (value == NULL || size != 8U || memcmp(value, "RVAL1 ", 6U) != 0 ||
		value[7] != '\n') {
		return fallback;
	}
	const char digit = value[6];
	if (digit >= '0' && digit <= '9') return static_cast<unsigned>(digit - '0');
	if (digit >= 'A' && digit <= 'F') return 10U + static_cast<unsigned>(digit - 'A');
	return fallback;
}

inline unsigned Read_Mode()
{
	unsigned mode = DEFAULT_MODE;
	FILE *file = fopen("ux0:data/renegade/user/config/frame-alloc-v1.flag", "rb");
	if (file != NULL) {
		char value[9] = {};
		const size_t size = fread(value, 1U, sizeof(value), file);
		const bool read_ok = !ferror(file);
		fclose(file);
		if (read_ok) mode = Parse_Mode(value, size, DEFAULT_MODE);
	}
	return mode;
}

// One instance across translation units (inline function static).
inline unsigned Mode()
{
	static const unsigned mode = Read_Mode();
	return mode;
}

inline bool Enabled(unsigned bit)
{
	return (Mode() & bit) != 0U;
}

// Whether a texture creation of `bytes` RGBA bytes converts into the retained
// scratch whose current capacity is `scratch_capacity`.
inline bool Use_Texture_Scratch(size_t bytes, size_t scratch_capacity)
{
	return Enabled(TEXTURE_RGBA_SCRATCH) &&
		(bytes <= MAX_SCRATCH_GROWTH_BYTES || bytes <= scratch_capacity);
}

} // namespace RenegadeVitaFrameAlloc
