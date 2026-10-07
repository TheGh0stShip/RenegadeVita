#pragma once

// Loading-time pre-warm and first-use telemetry for vitaGL fixed-function
// programs (vitagl-ffp-program-cache.patch). Vita-only; see
// ww3d_vita_ffp_program_keys.h for the persistent key record.

namespace RenegadeVitaFfpProgramWarm {

// vitaGL counter indices returned by vglRenegadeGetFfpStats. The order must
// match the RENEGADE_FFP_STAT_* enum in vitagl-ffp-program-cache.patch
// (host test test_vita_ffp_program_cache checks it).
enum Stat {
	STAT_VERSION,
	STAT_VERT_COMPILES,
	STAT_FRAG_COMPILES,
	STAT_VERT_DISK_LOADS,
	STAT_FRAG_DISK_LOADS,
	STAT_DISK_REJECTS,
	STAT_COMPILE_US,
	STAT_DISK_US,
	STAT_MASK_CHANGES,
	STAT_VERT_REPATCHES,
	STAT_FRAG_REPATCHES,
	STAT_PREWARM_VERT,
	STAT_PREWARM_FRAG,
	STAT_VERT_CACHE_SIZE,
	STAT_FRAG_CACHE_SIZE,
	STAT_COMPILE_MAX_US,
	STAT_PREWARM_BYTES,
	STAT_COUNT
};

#if defined(__vita__)
// Once, after vglInit: load the GXPs of every recorded key into vitaGL's RAM
// program cache. Disabled by ux0:data/renegade/user/config/ffp-prewarm-v1.flag
// containing "RVFP1 0\n" (recording and telemetry continue).
void Prewarm_From_Record(const char *owner);
// On loading screens and shutdown: add the keys now resident in vitaGL to
// the persistent record (written only when it grew).
void Record_Resident_Keys(const char *owner);
// Every 120 presented frames: first-use compile/disk-load breadcrumb.
void Sample_Window(unsigned frame);
#endif

} // namespace RenegadeVitaFfpProgramWarm
