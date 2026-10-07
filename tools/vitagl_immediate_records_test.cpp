// Equivalence of packed immediate records with the per-vertex vitaGL calls.
// vitagl.inc: patched pinned vitaGL glVertex3f, glColor4f/4ub, glNormal3f,
//             glMultiTexCoord2f and vglRenegadeImmediateVertices bodies.
// coords.inc: production indexed texture-coordinate helpers (Compute, Emit,
//             Record) from ww3d_vita_renderer.cpp.
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <random>
#include <vector>
#include "ww3d_vita_indexed_vertex_records.h"
#include "ww3d_vita_texture_transform.h"

#define SKIP_ERROR_HANDLING
#define THREAD_SAFE()
#define vgl_fast_memcpy std::memcpy
#define LEGACY_VERTEX_STRIDE 24
#define LEGACY_MT_VERTEX_STRIDE 26
#define LEGACY_NT_VERTEX_STRIDE 22
#define GL_FALSE false
#define GL_TRUE true
using GLfloat = float;
using GLsizei = int;
using GLboolean = bool;
using GLenum = unsigned;
using GLint = int;
using GLubyte = uint8_t;
using GLushort = uint16_t;
enum { GL_TEXTURE0 = 0x84C0, GL_TEXTURE1 = 0x84C1, GL_INVALID_ENUM = 0x0500,
	GL_OUT_OF_MEMORY = 0x0505 };
#define SET_GL_ERROR_WITH_VALUE(error, value) { vgl_error = error; return; }
static bool tint_dirty = false;
#define flag_dirty_frag_unif(x) tint_dirty = true;
static int vgl_error = 0;
struct V2 { float x, y; };
struct V3 { float x, y, z; };
struct V4 { union { struct { float x, y, z, w; }; struct { float r, g, b, a; }; }; };
static struct { V2 uv; V4 clr, amb, diff, spec, emiss; V3 nor; V2 uv2; } current_vtx;
static float storage[2][1 << 16];
static float *legacy_pool_ptr = storage[0], *legacy_pool_end = storage[0] + (1 << 16);
static bool lighting_state = false;
static struct { unsigned state; } texture_units[2];
static unsigned vertex_count = 0;
static GLboolean renegade_projective_immediate = GL_FALSE;
static GLboolean renegade_projective_failed = GL_FALSE;
static float renegade_texture_q[2] = { 1.0f, 1.0f };
#include "vitagl.inc"

namespace coords {
using DWORD = uint32_t;
struct D3DMATRIX { float m[4][4]; };
enum { D3DTTFF_DISABLE = 0, D3DTTFF_COUNT1 = 1, D3DTTFF_COUNT2 = 2,
	D3DTTFF_COUNT3 = 3, D3DTTFF_COUNT4 = 4, D3DTTFF_PROJECTED = 256 };
const DWORD D3DTSS_TCI_PASSTHRU = 0x00000U, D3DTSS_TCI_CAMERASPACENORMAL = 0x10000U,
	D3DTSS_TCI_CAMERASPACEPOSITION = 0x20000U,
	D3DTSS_TCI_CAMERASPACEREFLECTIONVECTOR = 0x30000U;
using RenegadeVitaRenderer::Build_DX8_Texture_Source;
struct Vector3 { float X, Y, Z; };
struct OriginalTextureCoordinateState {
	DWORD texcoord_index;
	DWORD texture_transform_flags;
	D3DMATRIX texture_transform;
};
bool g_logged_first_generated_texture_coordinate = false;
bool g_logged_first_passthrough_texture_v_preserved = false;
unsigned breadcrumbs = 0;
template<class... Args> void Vita_Append_A22_Runtime_Breadcrumb(Args...) { ++breadcrumbs; }
bool Has_Loadscreen_Texture_Prefix(const char *name) { return name && name[0] == 'L'; }
// Deterministic generated sources; only their routing is under test here.
Vector3 Compute_Indexed_Camera_Space_Normal(const float *w, const float *v, const float n[3])
{ return { n[0] * w[0] + v[1], n[1] - w[5], n[2] * v[10] }; }
Vector3 Compute_Indexed_Camera_Space_Position(const float *w, const float *v, const float p[3])
{ return { p[0] + w[12], p[1] * v[5], p[2] - w[14] }; }
Vector3 Compute_Indexed_Camera_Space_Reflection(const float *w, const float *v,
	const float p[3], const float n[3])
{ return { p[0] * n[0] + w[1], p[1] - n[1] * v[2], p[2] + n[2] }; }
float emitted_s[2], emitted_t[2], emitted_q[2];
bool emitted_projective[2];
void glMultiTexCoord2f(GLenum unit, float s, float t)
{ const unsigned i = unit - GL_TEXTURE0; emitted_s[i] = s; emitted_t[i] = t; emitted_q[i] = 1.0f; emitted_projective[i] = false; }
void vglRenegadeTexCoord3f(GLenum unit, float s, float t, float q)
{ const unsigned i = unit - GL_TEXTURE0; emitted_s[i] = s; emitted_t[i] = t; emitted_q[i] = q; emitted_projective[i] = true; }
#include "coords.inc"
} // namespace coords

static bool same_bits(const void *a, const void *b, size_t bytes) { return std::memcmp(a, b, bytes) == 0; }

static void test_color_table()
{
	for (unsigned c = 0U; c < 256U; ++c) {
		volatile float component = static_cast<float>(c);
		const float divided = component / 255.0f;
		assert(same_bits(&divided, &RenegadeVitaRenderer::UNIT_BYTE_COLOR.value[c], sizeof(float)));
	}
	float rgba[4];
	RenegadeVitaRenderer::Decode_Indexed_Record_Color(0x80402010U, rgba);
	assert(rgba[0] == 64.0f / 255.0f && rgba[1] == 32.0f / 255.0f &&
		rgba[2] == 16.0f / 255.0f && rgba[3] == 128.0f / 255.0f);
}

struct Vertex { float position[3], normal[3], uv0[2], uv1[2], primary[4]; uint32_t diffuse; bool lit; };

static void per_vertex(const Vertex &v, bool position)
{
	if (v.lit) glColor4f(v.primary[0], v.primary[1], v.primary[2], v.primary[3]);
	else glColor4ub(static_cast<GLubyte>((v.diffuse >> 16U) & 0xffU),
		static_cast<GLubyte>((v.diffuse >> 8U) & 0xffU),
		static_cast<GLubyte>(v.diffuse & 0xffU),
		static_cast<GLubyte>((v.diffuse >> 24U) & 0xffU));
	glNormal3f(v.normal[0], v.normal[1], v.normal[2]);
	glMultiTexCoord2f(GL_TEXTURE0, v.uv0[0], v.uv0[1]);
	glMultiTexCoord2f(GL_TEXTURE1, v.uv1[0], v.uv1[1]);
	if (position) glVertex3f(v.position[0], v.position[1], v.position[2]);
}

static void test_vitagl_streams()
{
	std::mt19937 random(1234U);
	std::uniform_real_distribution<float> value(-300.0f, 300.0f);
	const float specials[] = { -0.0f, 1e-40f, -1e-42f, 3.4e38f, 0.5f };
	std::vector<Vertex> vertices(700);
	for (size_t i = 0; i < vertices.size(); ++i) {
		Vertex &v = vertices[i];
		float *fields[] = { v.position, v.normal, v.uv0, v.uv1, v.primary };
		const unsigned counts[] = { 3, 3, 2, 2, 4 };
		for (unsigned f = 0; f < 5U; ++f) for (unsigned c = 0; c < counts[f]; ++c)
			fields[f][c] = (i + c) % 37U == 0U ? specials[(i + f) % 5U] : value(random);
		v.diffuse = random();
		v.lit = i % 5U == 3U;
	}
	unsigned layouts = 0U;
	for (unsigned units = 0U; units < 3U; ++units) {
		texture_units[0].state = units >= 1U;
		texture_units[1].state = units >= 2U;
		float *ends[2]; unsigned counts[2]; decltype(current_vtx) finals[2];
		for (unsigned path = 0U; path < 2U; ++path) {
			std::memset(&current_vtx, 0x5a, sizeof(current_vtx));
			std::memset(storage[path], 0xa5, sizeof(storage[path]));
			legacy_pool_ptr = storage[path];
			vertex_count = 0U;
			if (path == 0U) {
				for (const Vertex &v : vertices) per_vertex(v, true);
			} else {
				RenegadeVitaRenderer::IndexedVertexRecord records[RenegadeVitaRenderer::INDEXED_VERTEX_RECORD_CHUNK];
				size_t next = 0U, run = 0U;
				while (next < vertices.size()) {
					// Uneven runs, including empty probes, up to the chunk size.
					const size_t length = std::min<size_t>(vertices.size() - next,
						(run++ * 53U) % (RenegadeVitaRenderer::INDEXED_VERTEX_RECORD_CHUNK + 1U));
					for (size_t r = 0U; r < length; ++r) {
						const Vertex &v = vertices[next + r];
						std::memcpy(records[r].position, v.position, sizeof(v.position));
						std::memcpy(records[r].uv0, v.uv0, sizeof(v.uv0));
						std::memcpy(records[r].uv1, v.uv1, sizeof(v.uv1));
						if (v.lit) std::memcpy(records[r].color, v.primary, sizeof(v.primary));
						else RenegadeVitaRenderer::Decode_Indexed_Record_Color(v.diffuse, records[r].color);
					}
					const auto before = current_vtx;
					assert(vglRenegadeImmediateVertices(reinterpret_cast<const GLfloat *>(records),
						static_cast<GLsizei>(length)));
					assert(same_bits(&before, &current_vtx, sizeof(current_vtx)));
					next += length;
				}
				per_vertex(vertices.back(), false);
			}
			ends[path] = legacy_pool_ptr;
			counts[path] = vertex_count;
			finals[path] = current_vtx;
		}
		const size_t used = static_cast<size_t>(ends[0] - storage[0]);
		const size_t stride = units == 2U ? 11U : units == 1U ? 9U : 7U;
		assert(used == stride * vertices.size());
		assert(static_cast<size_t>(ends[1] - storage[1]) == used);
		assert(counts[0] == counts[1] && counts[0] == vertices.size());
		assert(same_bits(storage[0], storage[1], sizeof(storage[0])));
		assert(same_bits(&finals[0], &finals[1], sizeof(finals[0])));
		++layouts;
	}
	// Lit and projective primitives and negative counts write nothing.
	float record[11] = {};
	for (unsigned rejected = 0U; rejected < 3U; ++rejected) {
		lighting_state = rejected == 0U;
		renegade_projective_immediate = rejected == 1U;
		legacy_pool_ptr = storage[0];
		vertex_count = 7U;
		assert(!vglRenegadeImmediateVertices(record, rejected == 2U ? -1 : 1));
		assert(vglRenegadeImmediateVertices(record, 0) == (rejected == 2U));
		assert(legacy_pool_ptr == storage[0] && vertex_count == 7U);
	}
	lighting_state = false;
	renegade_projective_immediate = GL_FALSE;
	assert(vglRenegadeImmediateVertices(record, 0) && vertex_count == 7U &&
		legacy_pool_ptr == storage[0]);
	std::printf("vitaGL immediate records stream equivalence PASS layouts=%u vertices=%zu\n",
		layouts, vertices.size());
}

static void test_record_coordinates()
{
	using namespace coords;
	std::mt19937 random(99U);
	std::uniform_real_distribution<float> value(-4.0f, 4.0f);
	const DWORD modes[] = { D3DTSS_TCI_PASSTHRU, D3DTSS_TCI_CAMERASPACENORMAL,
		D3DTSS_TCI_CAMERASPACEPOSITION, D3DTSS_TCI_CAMERASPACEREFLECTIONVECTOR, 0x40000U };
	const DWORD flags[] = { D3DTTFF_DISABLE, D3DTTFF_COUNT1, D3DTTFF_COUNT2, D3DTTFF_COUNT3,
		D3DTTFF_COUNT4, D3DTTFF_COUNT2 | D3DTTFF_PROJECTED, D3DTTFF_PROJECTED,
		D3DTTFF_COUNT4 | D3DTTFF_PROJECTED };
	unsigned cases = 0U;
	for (DWORD mode : modes) for (DWORD flag : flags) for (DWORD source = 0U; source < 2U; ++source)
	for (unsigned stage = 0U; stage < 2U; ++stage) for (unsigned sample = 0U; sample < 16U; ++sample) {
		OriginalTextureCoordinateState state = {};
		state.texcoord_index = mode | source;
		state.texture_transform_flags = flag;
		for (auto &row : state.texture_transform.m) for (float &cell : row) cell = value(random);
		float uv0[2] = { value(random), value(random) }, uv1[2] = { value(random), value(random) };
		float position[3] = { value(random), value(random), value(random) };
		float normal[3] = { value(random), value(random), value(random) };
		float world[16], view[16];
		for (float &cell : world) cell = value(random);
		for (float &cell : view) cell = value(random);
		const char *name = sample % 3U == 0U ? "Lscreen" : "gameplay";
		// Reset one-shot breadcrumbs so both paths take their logging branches.
		g_logged_first_generated_texture_coordinate = g_logged_first_passthrough_texture_v_preserved = false;
		breadcrumbs = 0U;
		Emit_Indexed_Texture_Coordinate(stage, GL_TEXTURE0 + stage, state, uv0, uv1,
			position, normal, world, view, name);
		const unsigned emit_breadcrumbs = breadcrumbs;
		const bool emit_flags[2] = { g_logged_first_generated_texture_coordinate,
			g_logged_first_passthrough_texture_v_preserved };
		g_logged_first_generated_texture_coordinate = g_logged_first_passthrough_texture_v_preserved = false;
		breadcrumbs = 0U;
		float coordinate[2] = { -1.0f, -1.0f };
		Record_Indexed_Texture_Coordinate(stage, state, uv0, uv1, position, normal,
			world, view, name, coordinate);
		assert(same_bits(&coordinate[0], &emitted_s[stage], sizeof(float)));
		assert(same_bits(&coordinate[1], &emitted_t[stage], sizeof(float)));
		assert(breadcrumbs == emit_breadcrumbs &&
			g_logged_first_generated_texture_coordinate == emit_flags[0] &&
			g_logged_first_passthrough_texture_v_preserved == emit_flags[1]);
		++cases;
	}
	std::printf("production record/emit texture coordinate equivalence PASS cases=%u\n", cases);
}

int main()
{
	test_color_table();
	test_vitagl_streams();
	test_record_coordinates();
}
