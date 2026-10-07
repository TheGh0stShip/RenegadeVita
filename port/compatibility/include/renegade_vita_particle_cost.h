#pragma once

// particle-cost-v1 (RVPE1): switches for the original ParticleBufferClass
// visual-state path (staging/ww3d2/part_buf.cpp, applied by
// port/patches/ww3d2-tut1-particle-cost.patch). Emission, kinematics, LOD
// selection, sorting and submission stay original.
//
// ux0:data/renegade/user/config/particle-cost-v1.flag holds exactly
// "RVPE1 <hex digit>\n" (0-9, A-F), a bit mask:
//   bit 0 (1)  Keyframe evaluation and colour/alpha combining skip particles
//              that the active point table of the same Render excludes (LOD
//              decimation, dead slots). Keyframe cursors still advance, so
//              every value the point group reads is bit-identical.
//   bit 1 (2)  Evaluate visual state whenever the active point table can draw
//              a particle (DecimationThreshold < 16). The original test,
//              DecimationThreshold < LodCount - 1, means that only for 17 LOD
//              levels; cloned buffers with fewer than 17 particles keep
//              LodCount = MaxNum and at their lowest LOD draw stale or never
//              computed colour/size. Changes pixels for those clones only.
//   bit 2 (4)  One "A3.6 particle-cost:" log line per 900 WW3D frames.
// Default 5 (bits 0 and 2). "RVPE1 4" is the original evaluation with the
// same telemetry, for A/B. Any other content leaves the default; unknown
// bits are ignored.

#include <stddef.h>
#include <stdio.h>
#include <string.h>

#ifndef RENEGADE_VITA_PARTICLE_COST_DEFAULT
#define RENEGADE_VITA_PARTICLE_COST_DEFAULT 4U
#endif

namespace RenegadeVitaParticleCost {

enum {
	EXACT_DECIMATION = 1U,
	DRAWN_VISUAL_STATE = 2U,
	TELEMETRY = 4U,
	KNOWN_BITS = 7U,
	TELEMETRY_WINDOW_FRAMES = 900U
};

inline bool Parse_Flag(const char *data, size_t bytes, unsigned &mode)
{
	if (data == NULL || bytes != 8U || memcmp(data, "RVPE1 ", 6U) != 0 || data[7] != '\n') {
		return false;
	}
	const char digit = data[6];
	if (digit >= '0' && digit <= '9') {
		mode = static_cast<unsigned>(digit - '0') & KNOWN_BITS;
		return true;
	}
	if (digit >= 'A' && digit <= 'F') {
		mode = (10U + static_cast<unsigned>(digit - 'A')) & KNOWN_BITS;
		return true;
	}
	return false;
}

inline unsigned Read_Mode(void)
{
	unsigned mode = RENEGADE_VITA_PARTICLE_COST_DEFAULT & KNOWN_BITS;
#if defined(__vita__)
	FILE *file = fopen("ux0:data/renegade/user/config/particle-cost-v1.flag", "rb");
	if (file != NULL) {
		char value[9] = {};
		const size_t size = fread(value, 1U, sizeof(value), file);
		const bool read_ok = !ferror(file);
		fclose(file);
		unsigned parsed = mode;
		if (read_ok && Parse_Flag(value, size, parsed)) {
			mode = parsed;
		}
	}
#endif
	return mode;
}

}  // namespace RenegadeVitaParticleCost
