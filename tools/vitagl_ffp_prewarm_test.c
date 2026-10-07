// Host harness for vitagl-ffp-program-cache.patch. The test driver extracts
// the patched ffp.c cache types, loader, key export and pre-warm into
// ffp_extract.inc; this file supplies minimal GXM/IO mocks.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define VGL_GIT_HASH "6e7fe40"
#define FFP_SHADER_CACHE_MAGIC 28
#define WVP_ON_GPU 0
#define SHADER_CACHE_SIZE 256
#define RENEGADE_VGL_FFP_CACHE_DIGEST "0123456789ab"
enum { VERTEX_UNIFORMS_NUM = 20, FRAGMENT_UNIFORMS_NUM = 24, FFP_ATTRIBS_NUM = 8 };
typedef int SceUID;
typedef long long SceOff;
typedef unsigned int SceGxmShaderPatcherId;
typedef struct SceGxmProgram SceGxmProgram;
typedef union { uint32_t raw; } combiner_state;
#define SCE_O_RDONLY 1
#define SCE_SEEK_SET 0
#define SCE_SEEK_END 2

// In-memory files.
#define MAX_FILES 16
static struct { char name[256]; unsigned char *data; unsigned size; } files[MAX_FILES];
static int file_count;
static struct { int file; SceOff pos; int used; } fds[8];
static int opens, closes;

static void put_file(const char *name, const void *data, unsigned size)
{
	snprintf(files[file_count].name, sizeof(files[file_count].name), "%s", name);
	files[file_count].data = malloc(size ? size : 1);
	memcpy(files[file_count].data, data, size);
	files[file_count].size = size;
	file_count++;
}

static SceUID sceIoOpen(const char *name, int flags, int mode)
{
	(void)flags; (void)mode;
	for (int i = 0; i < file_count; i++) {
		if (strcmp(files[i].name, name) == 0) {
			for (int fd = 0; fd < 8; fd++) {
				if (!fds[fd].used) {
					fds[fd].used = 1; fds[fd].file = i; fds[fd].pos = 0;
					opens++;
					return fd;
				}
			}
		}
	}
	return -1;
}
static SceOff sceIoLseek(SceUID fd, SceOff off, int whence)
{
	fds[fd].pos = whence == SCE_SEEK_END ? (SceOff)files[fds[fd].file].size + off : off;
	return fds[fd].pos;
}
static int sceIoRead(SceUID fd, void *out, unsigned size)
{
	unsigned avail = files[fds[fd].file].size - (unsigned)fds[fd].pos;
	unsigned n = size < avail ? size : avail;
	memcpy(out, files[fds[fd].file].data + fds[fd].pos, n);
	fds[fd].pos += n;
	return (int)n;
}
static int sceIoClose(SceUID fd) { fds[fd].used = 0; closes++; return 0; }

// GXP header: "GXP\0", version bytes, u32 total size at offset 8.
static int sceGxmProgramCheck(const SceGxmProgram *p) { return memcmp(p, "GXP\0", 4) == 0 ? 0 : -1; }
static unsigned sceGxmProgramGetSize(const SceGxmProgram *p) { uint32_t s; memcpy(&s, (const char *)p + 8, 4); return s; }
static unsigned sceGxmProgramGetDefaultUniformBufferSize(const SceGxmProgram *p) { (void)p; return 32; }
static void *gxm_shader_patcher;
static unsigned next_id = 100;
static int register_fail_on;
static int sceGxmShaderPatcherRegisterProgram(void *patcher, const SceGxmProgram *p, SceGxmShaderPatcherId *id)
{
	(void)patcher; (void)p;
	if (register_fail_on && next_id == (unsigned)register_fail_on) { next_id++; return -1; }
	*id = next_id++;
	return 0;
}
static uint32_t fake_time;
static uint32_t sceKernelGetProcessTimeLow(void) { return fake_time += 7; }
static long live_allocations;
static void *vglMalloc(unsigned size) { live_allocations++; return malloc(size ? size : 1); }
static void vgl_free(void *p) { live_allocations--; free(p); }

// Globals the patched code saves/restores and the uniform reloaders set.
static SceGxmProgram *ffp_vertex_program, *ffp_fragment_program;
static int *ffp_vertex_params, *ffp_vertex_attribs, *ffp_fragment_params;
static SceGxmProgram *reloaded_vertex, *reloaded_fragment;
static void reload_vertex_uniforms_and_attributes(int *params, int *attribs)
{
	reloaded_vertex = ffp_vertex_program;
	params[0] = 1;
	ffp_vertex_params = params;
	ffp_vertex_attribs = attribs;
}
static void reload_fragment_uniforms(int *params)
{
	reloaded_fragment = ffp_fragment_program;
	params[0] = 2;
	ffp_fragment_params = params;
}

#include "ffp_extract.inc"

static int failures;
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "%s:%d CHECK(%s)\n", __FILE__, __LINE__, #x); failures++; } } while (0)

static unsigned make_gxp(unsigned char *out, unsigned size, unsigned header_size, unsigned char fill)
{
	memset(out, fill, size);
	memcpy(out, "GXP\0", 4);
	memcpy(out + 8, &header_size, 4);
	return size;
}

int main(void)
{
	unsigned char gxp[64];
	char name[256];
	snprintf(vgl_renegade_ffp_cache_path, sizeof(vgl_renegade_ffp_cache_path), "cache/ffp-%s", vglRenegadeGetFfpCacheTag());
	CHECK(strcmp(vglRenegadeGetFfpCacheTag(), "6e7fe40-m28-w0-p0123456789ab") == 0);

	// Valid vertex GXPs for two keys, one truncated, one bad magic.
	const uint32_t vkeys[] = { 0x00000038u, 0x80000008u, 0x00000030u, 0x00000010u, 0x00000038u, 0x00000001u };
	snprintf(name, sizeof(name), "%s/v/%08X-%d.gxp", vgl_renegade_ffp_cache_path, 0x00000038u, 0);
	put_file(name, gxp, make_gxp(gxp, 40, 40, 0xA1));
	snprintf(name, sizeof(name), "%s/v/%08X-%d.gxp", vgl_renegade_ffp_cache_path, 0x80000008u, 0);
	put_file(name, gxp, make_gxp(gxp, 48, 44, 0xA2)); // padded: header <= file accepted
	snprintf(name, sizeof(name), "%s/v/%08X-%d.gxp", vgl_renegade_ffp_cache_path, 0x00000030u, 0);
	put_file(name, gxp, make_gxp(gxp, 24, 40, 0xA3)); // truncated
	snprintf(name, sizeof(name), "%s/v/%08X-%d.gxp", vgl_renegade_ffp_cache_path, 0x00000010u, 0);
	make_gxp(gxp, 40, 40, 0xA4); gxp[0] = 'X';
	put_file(name, gxp, 40);
	snprintf(name, sizeof(name), "%s/v/%08X-%d.gxp", vgl_renegade_ffp_cache_path, 0x00000001u, 0);
	put_file(name, gxp, make_gxp(gxp, 40, 40, 0xA5)); // key outside VERTEX_SHADER_MASK: never read
	const uint32_t fkeys[] = {
		0x00000003u, 0u, 0u,
		0x00000003u, 0x11u, 0x22u,
		0x00000007u, 0u, 0u, // no file
	};
	snprintf(name, sizeof(name), "%s/f/%08X-%016llX.gxp", vgl_renegade_ffp_cache_path, 0x00000003u, 0ull);
	put_file(name, gxp, make_gxp(gxp, 36, 36, 0xB1));
	snprintf(name, sizeof(name), "%s/f/%08X-%016llX.gxp", vgl_renegade_ffp_cache_path, 0x00000003u, 0x0000002200000011ull);
	put_file(name, gxp, make_gxp(gxp, 52, 52, 0xB2));

	// Pretend a program is active; pre-warm must not disturb it.
	SceGxmProgram *active_v = (SceGxmProgram *)"active-v", *active_f = (SceGxmProgram *)"active-f";
	int active_vp[4], active_va[4], active_fp[4];
	ffp_vertex_program = active_v; ffp_vertex_params = active_vp; ffp_vertex_attribs = active_va;
	ffp_fragment_program = active_f; ffp_fragment_params = active_fp;

	int vl = -1, fl = -1;
	vglRenegadePrewarmFfpPrograms(vkeys, 6, fkeys, 3, &vl, &fl);
	CHECK(vl == 2 && fl == 2);
	CHECK(vert_shader_cache_size == 2 && frag_shader_cache_size == 2);
	CHECK(vert_shader_cache_idx == 1 && frag_shader_cache_idx == 1);
	CHECK(vert_shader_cache[0].mask.raw == 0x00000038u && vert_shader_cache[1].mask.raw == 0x80000008u);
	CHECK(((unsigned char *)vert_shader_cache[0].prog)[20] == 0xA1 && ((unsigned char *)vert_shader_cache[1].prog)[47] == 0xA2);
	CHECK(vert_shader_cache[1].vert_unifs[0] == 1 && reloaded_vertex == vert_shader_cache[1].prog);
	CHECK(frag_shader_cache[1].cmb_mask.raw == 0x0000002200000011ull && frag_shader_cache[1].frag_unifs[0] == 2);
	CHECK(((unsigned char *)frag_shader_cache[1].prog)[51] == 0xB2 && reloaded_fragment == frag_shader_cache[1].prog);
	CHECK(vert_shader_cache[0].unif_buf_size == 32 && vert_shader_cache[0].unif_buf != NULL);
	CHECK(ffp_vertex_program == active_v && ffp_vertex_params == active_vp && ffp_vertex_attribs == active_va);
	CHECK(ffp_fragment_program == active_f && ffp_fragment_params == active_fp);
	CHECK(opens == closes);
	uint32_t stats[32] = {0};
	CHECK(vglRenegadeGetFfpStats(stats, 32) == RENEGADE_FFP_STAT_COUNT);
	CHECK(stats[RENEGADE_FFP_STAT_VERSION] == 1);
	CHECK(stats[RENEGADE_FFP_STAT_PREWARM_VERT] == 2 && stats[RENEGADE_FFP_STAT_PREWARM_FRAG] == 2);
	CHECK(stats[RENEGADE_FFP_STAT_DISK_REJECTS] == 2); // truncated + bad magic
	CHECK(stats[RENEGADE_FFP_STAT_PREWARM_BYTES] == 40 + 44 + 36 + 52 + 4 * 32);
	CHECK(stats[RENEGADE_FFP_STAT_VERT_CACHE_SIZE] == 2 && stats[RENEGADE_FFP_STAT_COMPILE_US] == 0);
	CHECK(live_allocations == 8); // 4 programs + 4 uniform buffers

	// A second pre-warm with the same keys loads nothing (all resident).
	vglRenegadePrewarmFfpPrograms(vkeys, 6, fkeys, 3, &vl, &fl);
	CHECK(vl == 0 && fl == 0 && vert_shader_cache_size == 2 && frag_shader_cache_size == 2);

	// Key export reproduces insertion order and the combiner split.
	uint32_t ev[8], ef[24];
	int nv = 0, nf = 0;
	vglRenegadeGetFfpKeys(ev, 8, &nv, ef, 8, &nf);
	CHECK(nv == 2 && nf == 2 && ev[0] == 0x38u && ev[1] == 0x80000008u);
	CHECK(ef[3] == 0x3u && ef[4] == 0x11u && ef[5] == 0x22u);
	vglRenegadeGetFfpKeys(ev, 1, &nv, ef, 1, &nf);
	CHECK(nv == 1 && nf == 1);

	// Registration failure frees the program and inserts nothing.
	snprintf(name, sizeof(name), "%s/f/%08X-%016llX.gxp", vgl_renegade_ffp_cache_path, 0x00000007u, 0ull);
	put_file(name, gxp, make_gxp(gxp, 36, 36, 0xB3));
	register_fail_on = (int)next_id;
	long before = live_allocations;
	vglRenegadePrewarmFfpPrograms(vkeys, 0, fkeys, 3, &vl, &fl);
	CHECK(fl == 0 && frag_shader_cache_size == 2 && live_allocations == before);
	register_fail_on = 0;

	// Capacity: a full ring is never wrapped by pre-warm.
	vert_shader_cache_size = SHADER_CACHE_SIZE;
	snprintf(name, sizeof(name), "%s/v/%08X-%d.gxp", vgl_renegade_ffp_cache_path, 0x00000008u, 0);
	put_file(name, gxp, make_gxp(gxp, 40, 40, 0xA6));
	const uint32_t extra = 0x00000008u;
	vglRenegadePrewarmFfpPrograms(&extra, 1, fkeys, 0, &vl, &fl);
	CHECK(vl == 0 && vert_shader_cache_idx == 1);

	if (failures) {
		fprintf(stderr, "%d failure(s)\n", failures);
		return 1;
	}
	puts("vitagl_ffp_prewarm_test: OK");
	return 0;
}
