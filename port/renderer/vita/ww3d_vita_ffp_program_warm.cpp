#include "ww3d_vita_ffp_program_warm.h"
#include "ww3d_vita_ffp_program_keys.h"

#if defined(__vita__)
#include "vita_runtime_log.h"

#include <psp2/io/fcntl.h>
#include <psp2/kernel/processmgr.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

// Renegade extensions from vitagl-ffp-program-cache.patch.
extern "C" const char *vglRenegadeGetFfpCacheTag(void);
extern "C" const char *vglRenegadeGetFfpCachePath(void);
extern "C" uint32_t vglRenegadeGetFfpStats(uint32_t *out, uint32_t max_count);
extern "C" void vglRenegadeGetFfpKeys(uint32_t *vert, int max_vert, int *n_vert,
	uint32_t *frag, int max_frag, int *n_frag);
extern "C" void vglRenegadePrewarmFfpPrograms(const uint32_t *vert, int n_vert,
	const uint32_t *frag, int n_frag, int *vert_loaded, int *frag_loaded);

namespace RenegadeVitaFfpProgramWarm {
namespace {

using namespace RenegadeVitaFfpProgramKeys;

// vitaGL's RAM program cache holds at most 256 programs of each kind.
enum { kResidentCapacity = 256, kMaxWindowLines = 600 };

KeySet g_record;
// Set once vglInit has configured the cache path (Prewarm_From_Record runs
// right after it); recording before that would bind the wrong directory.
bool g_cache_configured = false;
bool g_record_loaded = false;
char g_file_buffer[kMaxFileBytes];
uint32_t g_resident_vertex[kResidentCapacity];
uint32_t g_resident_fragment[kResidentCapacity * 3];
uint32_t g_previous[STAT_COUNT];
unsigned g_windows = 0U;
unsigned g_window_lines = 0U;

bool Key_File_Path(char *path, size_t capacity, const char *leaf)
{
	const int written = snprintf(path, capacity, "%s/%s", vglRenegadeGetFfpCachePath(), leaf);
	return written > 0 && static_cast<size_t>(written) < capacity;
}

bool Read_Prewarm_Enabled()
{
	bool enabled = true;
	FILE *file = fopen("ux0:data/renegade/user/config/ffp-prewarm-v1.flag", "rb");
	if (file != NULL) {
		char value[9] = {};
		const size_t size = fread(value, 1U, sizeof(value), file);
		const bool read_ok = !ferror(file);
		fclose(file);
		if (read_ok && size == 8U && memcmp(value, "RVPW1 ", 6U) == 0 &&
			value[7] == '\n' && (value[6] == '0' || value[6] == '1')) {
			enabled = value[6] == '1';
		}
	}
	return enabled;
}

// Reads and validates the record once per process. A missing, stale-tag or
// damaged file yields an empty record that the next save replaces.
const char *Load_Record()
{
	if (g_record_loaded) return "cached";
	g_record_loaded = true;
	Clear(g_record);
	char path[256];
	if (!Key_File_Path(path, sizeof(path), "program-keys.txt")) return "path-too-long";
	const SceUID file = sceIoOpen(path, SCE_O_RDONLY, 0);
	if (file < 0) return "absent";
	const SceOff end = sceIoLseek(file, 0, SCE_SEEK_END);
	const char *status = "rejected";
	if (end > 0 && end <= static_cast<SceOff>(kMaxFileBytes) &&
		sceIoLseek(file, 0, SCE_SEEK_SET) == 0) {
		const unsigned size = static_cast<unsigned>(end);
		if (sceIoRead(file, g_file_buffer, size) == static_cast<int>(size) &&
			Parse(g_file_buffer, size, vglRenegadeGetFfpCacheTag(), g_record)) {
			status = "valid";
		}
	}
	sceIoClose(file);
	return status;
}

// Writes the record to a temporary file, then replaces the previous one.
int Write_Record(unsigned &bytes)
{
	bytes = 0U;
	const size_t size = Serialize(g_record, vglRenegadeGetFfpCacheTag(),
		g_file_buffer, sizeof(g_file_buffer));
	if (size == 0U) return -1;
	char path[256];
	char temporary[256];
	if (!Key_File_Path(path, sizeof(path), "program-keys.txt") ||
		!Key_File_Path(temporary, sizeof(temporary), "program-keys.tmp")) return -2;
	const SceUID file = sceIoOpen(temporary, SCE_O_WRONLY | SCE_O_CREAT | SCE_O_TRUNC, 0777);
	if (file < 0) return file;
	const int written = sceIoWrite(file, g_file_buffer, size);
	const int closed = sceIoClose(file);
	if (written != static_cast<int>(size) || closed < 0) {
		sceIoRemove(temporary);
		return written < 0 ? written : -3;
	}
	sceIoRemove(path);
	const int renamed = sceIoRename(temporary, path);
	if (renamed < 0) return renamed;
	bytes = static_cast<unsigned>(size);
	return 0;
}

unsigned Delta(const uint32_t *now, Stat stat)
{
	return now[stat] - g_previous[stat];
}

} // namespace

void Prewarm_From_Record(const char *owner)
{
	const uint64_t started_us = sceKernelGetProcessTimeWide();
	g_cache_configured = true;
	const char *status = Load_Record();
	const bool enabled = Read_Prewarm_Enabled();
	int vertex_loaded = 0;
	int fragment_loaded = 0;
	if (enabled && (g_record.vertex_count != 0U || g_record.fragment_count != 0U)) {
		uint32_t fragment[kMaxFragmentKeys * 3];
		for (unsigned i = 0U; i < g_record.fragment_count; ++i) {
			fragment[i * 3U + 0U] = g_record.fragment[i].mask;
			fragment[i * 3U + 1U] = g_record.fragment[i].combiner_low;
			fragment[i * 3U + 2U] = g_record.fragment[i].combiner_high;
		}
		vglRenegadePrewarmFfpPrograms(g_record.vertex, static_cast<int>(g_record.vertex_count),
			fragment, static_cast<int>(g_record.fragment_count), &vertex_loaded, &fragment_loaded);
	}
	uint32_t stats[STAT_COUNT] = {};
	vglRenegadeGetFfpStats(stats, STAT_COUNT);
	// Gameplay windows report only first-use work after this boot pre-warm.
	memcpy(g_previous, stats, sizeof(g_previous));
	Vita_Append_A22_Runtime_Breadcrumb("ffp-program-cache",
		"prewarm: version=1 owner=%s enabled=%d path=%s tag=%s record=%s keys=%u/%u loaded=%d/%d bytes=%u disk_us=%u rejects=%u elapsed_us=%llu",
		owner != NULL ? owner : "(none)", enabled ? 1 : 0, vglRenegadeGetFfpCachePath(),
		vglRenegadeGetFfpCacheTag(), status, g_record.vertex_count, g_record.fragment_count,
		vertex_loaded, fragment_loaded, stats[STAT_PREWARM_BYTES], stats[STAT_DISK_US],
		stats[STAT_DISK_REJECTS],
		static_cast<unsigned long long>(sceKernelGetProcessTimeWide() - started_us));
}

void Record_Resident_Keys(const char *owner)
{
	if (!g_cache_configured) return;
	const uint64_t started_us = sceKernelGetProcessTimeWide();
	const char *status = Load_Record();
	int vertex_count = 0;
	int fragment_count = 0;
	vglRenegadeGetFfpKeys(g_resident_vertex, kResidentCapacity, &vertex_count,
		g_resident_fragment, kResidentCapacity, &fragment_count);
	const unsigned added = Merge(g_record, g_resident_vertex, static_cast<unsigned>(vertex_count),
		g_resident_fragment, static_cast<unsigned>(fragment_count));
	if (added == 0U) return;
	unsigned bytes = 0U;
	const int result = Write_Record(bytes);
	Vita_Append_A22_Runtime_Breadcrumb("ffp-program-cache",
		"record: version=1 owner=%s previous=%s resident=%d/%d added=%u keys=%u/%u bytes=%u rc=%08X elapsed_us=%llu",
		owner != NULL ? owner : "(none)", status, vertex_count, fragment_count, added,
		g_record.vertex_count, g_record.fragment_count, bytes, static_cast<unsigned>(result),
		static_cast<unsigned long long>(sceKernelGetProcessTimeWide() - started_us));
}

void Sample_Window(unsigned frame)
{
	uint32_t now[STAT_COUNT] = {};
	if (vglRenegadeGetFfpStats(now, STAT_COUNT) != STAT_COUNT) return;
	++g_windows;
	const unsigned first_use = Delta(now, STAT_VERT_COMPILES) + Delta(now, STAT_FRAG_COMPILES) +
		Delta(now, STAT_VERT_DISK_LOADS) + Delta(now, STAT_FRAG_DISK_LOADS) +
		Delta(now, STAT_DISK_REJECTS);
	// First-use windows always; otherwise a steady-state sample every tenth
	// window for the per-draw key-change and re-patch rates.
	if ((first_use != 0U || g_windows % 10U == 1U) && g_window_lines < kMaxWindowLines) {
		++g_window_lines;
		const unsigned compile_us = Delta(now, STAT_COMPILE_US);
		const unsigned disk_us = Delta(now, STAT_DISK_US);
		Vita_Append_A22_Runtime_Breadcrumb("ffp-program-cache",
			"window: version=1 frame=%u window=120 compiles=%u/%u compile_ms=%u.%03u disk_loads=%u/%u disk_ms=%u.%03u rejects=%u mask_changes=%u repatches=%u/%u resident=%u/%u total_compiles=%u total_compile_ms=%u max_compile_ms=%u.%03u",
			frame, Delta(now, STAT_VERT_COMPILES), Delta(now, STAT_FRAG_COMPILES),
			compile_us / 1000U, compile_us % 1000U,
			Delta(now, STAT_VERT_DISK_LOADS), Delta(now, STAT_FRAG_DISK_LOADS),
			disk_us / 1000U, disk_us % 1000U, Delta(now, STAT_DISK_REJECTS),
			Delta(now, STAT_MASK_CHANGES), Delta(now, STAT_VERT_REPATCHES),
			Delta(now, STAT_FRAG_REPATCHES), now[STAT_VERT_CACHE_SIZE], now[STAT_FRAG_CACHE_SIZE],
			now[STAT_VERT_COMPILES] + now[STAT_FRAG_COMPILES], now[STAT_COMPILE_US] / 1000U,
			now[STAT_COMPILE_MAX_US] / 1000U, now[STAT_COMPILE_MAX_US] % 1000U);
	}
	memcpy(g_previous, now, sizeof(g_previous));
}

} // namespace RenegadeVitaFfpProgramWarm
#endif
