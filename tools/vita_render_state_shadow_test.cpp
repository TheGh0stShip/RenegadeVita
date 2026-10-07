// Host equivalence harness for the renderer's exact GL-state shadow.
//
// tools/test_vita_render_state_shadow.py extracts the real shadow block,
// Reset_Texture_Matrix_Stage, the DX8 compare/blend/fill translators and the
// Apply_DX8_Render_State switch from ww3d_vita_renderer.cpp into .inc files.
// Each is compiled twice, into namespace shadowed (shadow on) and namespace
// plain (shadow off = the unshadowed call sequence), over a GL shim that keeps
// vitaGL's observable state. Randomized call sequences that follow the
// renderer's call protocol run in lockstep; raster state, texture matrices,
// matrix mode and active unit must match after every operation, and the
// projection/modelview pair must match at every draw and at the end.
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef unsigned int GLenum;
typedef float GLfloat;
typedef unsigned char GLboolean;
typedef int GLint;

enum : GLenum {
	GL_FALSE_ENUM = 0,
	GL_NEVER = 0x0200, GL_LESS, GL_EQUAL, GL_LEQUAL, GL_GREATER, GL_NOTEQUAL,
	GL_GEQUAL, GL_ALWAYS,
	GL_ZERO = 0, GL_ONE = 1,
	GL_SRC_COLOR = 0x0300, GL_ONE_MINUS_SRC_COLOR, GL_SRC_ALPHA,
	GL_ONE_MINUS_SRC_ALPHA, GL_DST_ALPHA, GL_ONE_MINUS_DST_ALPHA, GL_DST_COLOR,
	GL_ONE_MINUS_DST_COLOR, GL_SRC_ALPHA_SATURATE,
	GL_FRONT = 0x0404, GL_BACK = 0x0405, GL_FRONT_AND_BACK = 0x0408,
	GL_POINT = 0x1B00, GL_LINE = 0x1B01, GL_FILL = 0x1B02,
	GL_CULL_FACE = 0x0B44, GL_DEPTH_TEST = 0x0B71, GL_ALPHA_TEST = 0x0BC0,
	GL_BLEND = 0x0BE2, GL_POLYGON_OFFSET_FILL = 0x8037,
	GL_MODELVIEW = 0x1700, GL_PROJECTION = 0x1701, GL_TEXTURE = 0x1702,
	GL_TEXTURE0 = 0x84C0
};
static const GLboolean GL_TRUE = 1;
static const GLboolean GL_FALSE = 0;

struct MeshMatDescClass { enum { MAX_TEX_STAGES = 2 }; };

enum : uint32_t {
	D3DRS_FILLMODE = 8, D3DRS_ZWRITEENABLE = 14, D3DRS_ALPHATESTENABLE = 15,
	D3DRS_SRCBLEND = 19, D3DRS_DESTBLEND = 20, D3DRS_CULLMODE = 22,
	D3DRS_ZFUNC = 23, D3DRS_ALPHAREF = 24, D3DRS_ALPHAFUNC = 25,
	D3DRS_ALPHABLENDENABLE = 27, D3DRS_ZBIAS = 47
};
enum : uint32_t { D3DCULL_NONE = 1, D3DCULL_CW = 2, D3DCULL_CCW = 3 };
enum : uint32_t {
	D3DCMP_NEVER = 1, D3DCMP_LESS, D3DCMP_EQUAL, D3DCMP_LESSEQUAL, D3DCMP_GREATER,
	D3DCMP_NOTEQUAL, D3DCMP_GREATEREQUAL, D3DCMP_ALWAYS
};
enum : uint32_t {
	D3DBLEND_ZERO = 1, D3DBLEND_ONE, D3DBLEND_SRCCOLOR, D3DBLEND_INVSRCCOLOR,
	D3DBLEND_SRCALPHA, D3DBLEND_INVSRCALPHA, D3DBLEND_DESTALPHA,
	D3DBLEND_INVDESTALPHA, D3DBLEND_DESTCOLOR, D3DBLEND_INVDESTCOLOR,
	D3DBLEND_SRCALPHASAT
};
enum : uint32_t { D3DFILL_POINT = 1, D3DFILL_WIREFRAME = 2, D3DFILL_SOLID = 3 };

static void Vita_Append_A22_Runtime_Breadcrumb(const char *, const char *, ...) {}

// Observable vitaGL state touched by the shadowed calls.
struct GLModel {
	bool blend, alpha_test, cull, depth_test, polygon_offset_fill;
	GLenum blend_source, blend_destination, alpha_function, depth_function;
	GLfloat alpha_reference;
	GLboolean depth_mask;
	GLboolean color_mask[4];
	GLenum cull_face, polygon_mode;
	GLfloat polygon_offset_factor, polygon_offset_units;
	GLenum matrix_mode;
	unsigned active_unit;
	GLfloat projection[16], modelview[16], texture[2][16];
	GLfloat saved_projection[16], saved_modelview[16];
	unsigned long long calls;
};

static bool Same_Bits(const void *left, const void *right, size_t bytes)
{
	return memcmp(left, right, bytes) == 0;
}

static bool Raster_Equal(const GLModel &a, const GLModel &b)
{
	return a.blend == b.blend && a.alpha_test == b.alpha_test && a.cull == b.cull &&
		a.depth_test == b.depth_test && a.polygon_offset_fill == b.polygon_offset_fill &&
		a.blend_source == b.blend_source && a.blend_destination == b.blend_destination &&
		a.alpha_function == b.alpha_function && a.depth_function == b.depth_function &&
		Same_Bits(&a.alpha_reference, &b.alpha_reference, sizeof(GLfloat)) &&
		a.depth_mask == b.depth_mask && Same_Bits(a.color_mask, b.color_mask, 4) &&
		a.cull_face == b.cull_face && a.polygon_mode == b.polygon_mode &&
		Same_Bits(&a.polygon_offset_factor, &b.polygon_offset_factor, sizeof(GLfloat)) &&
		Same_Bits(&a.polygon_offset_units, &b.polygon_offset_units, sizeof(GLfloat)) &&
		a.matrix_mode == b.matrix_mode && a.active_unit == b.active_unit &&
		Same_Bits(a.texture, b.texture, sizeof(a.texture));
}

static bool Transforms_Equal(const GLModel &a, const GLModel &b)
{
	return Same_Bits(a.projection, b.projection, sizeof(a.projection)) &&
		Same_Bits(a.modelview, b.modelview, sizeof(a.modelview));
}

#define RUN_NAMESPACE shadowed
#define RUN_ENABLED true
#include "vita_render_state_shadow_run.inc"
#undef RUN_NAMESPACE
#undef RUN_ENABLED
#define RUN_NAMESPACE plain
#define RUN_ENABLED false
#include "vita_render_state_shadow_run.inc"
#undef RUN_NAMESPACE
#undef RUN_ENABLED

namespace {

struct Rng {
	uint64_t state;
	uint32_t Next()
	{
		state ^= state << 13; state ^= state >> 7; state ^= state << 17;
		return static_cast<uint32_t>(state >> 16);
	}
	uint32_t Below(uint32_t count) { return Next() % count; }
};

enum { MATRIX_POOL = 7 };
GLfloat g_matrix_pool[MATRIX_POOL][16];

void Build_Matrix_Pool()
{
	for (int m = 0; m < MATRIX_POOL; ++m) {
		for (int i = 0; i < 16; ++i) g_matrix_pool[m][i] = (i % 5 == 0) ? 1.0f : 0.0f;
	}
	// 1: identity values passed as an explicit matrix; 2/3: same values with a
	// -0.0 element (bitwise different); 4: a NaN payload; 5/6: ordinary matrices.
	g_matrix_pool[2][1] = -0.0f;
	g_matrix_pool[3][4] = -0.0f;
	uint32_t nan_bits = 0x7fc01234U;
	memcpy(&g_matrix_pool[4][3], &nan_bits, sizeof(nan_bits));
	for (int i = 0; i < 16; ++i) {
		g_matrix_pool[5][i] = 0.25f * static_cast<float>(i) - 1.0f;
		g_matrix_pool[6][i] = 0.25f * static_cast<float>(i) - 1.0f;
	}
	g_matrix_pool[6][15] = 2.0f;
}

const GLfloat *Pick_Matrix(Rng &rng, bool allow_null)
{
	const uint32_t pick = rng.Below(MATRIX_POOL + (allow_null ? 1U : 0U));
	return pick == MATRIX_POOL ? NULL : g_matrix_pool[pick];
}

GLenum Pick(Rng &rng, const GLenum *values, unsigned count)
{
	return values[rng.Below(count)];
}

const GLenum kCompares[] = { GL_NEVER, GL_LESS, GL_EQUAL, GL_LEQUAL, GL_GREATER,
	GL_NOTEQUAL, GL_GEQUAL, GL_ALWAYS };
const GLenum kSources[] = { GL_ZERO, GL_ONE, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA };
const GLenum kDestinations[] = { GL_ZERO, GL_ONE, GL_SRC_COLOR, GL_ONE_MINUS_SRC_COLOR,
	GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA };
const uint32_t kDX8States[] = { D3DRS_ALPHABLENDENABLE, D3DRS_SRCBLEND, D3DRS_DESTBLEND,
	D3DRS_ALPHATESTENABLE, D3DRS_ALPHAREF, D3DRS_ALPHAFUNC, D3DRS_ZFUNC,
	D3DRS_ZWRITEENABLE, D3DRS_CULLMODE, D3DRS_FILLMODE, D3DRS_ZBIAS };

uint32_t Pick_DX8_Value(Rng &rng, uint32_t state)
{
	switch (state) {
	case D3DRS_SRCBLEND:
	case D3DRS_DESTBLEND: return 1U + rng.Below(11U);
	case D3DRS_ALPHAFUNC:
	case D3DRS_ZFUNC: return 1U + rng.Below(8U);
	case D3DRS_CULLMODE: return 1U + rng.Below(3U);
	case D3DRS_FILLMODE: return 1U + rng.Below(3U);
	case D3DRS_ZBIAS: return rng.Below(3U) == 0U ? 0U : rng.Below(16U);
	case D3DRS_ALPHAREF: return rng.Below(4U) * 0x40U + rng.Below(2U);
	default: return rng.Below(2U);
	}
}

struct Operation {
	unsigned kind;
	uint32_t a, b, c, d, e, f, g;
	const GLfloat *projection;
	const GLfloat *modelview;
};

enum OperationKind {
	OP_SHADER, OP_DX8, OP_DRAW, OP_BEGIN_FRAME, OP_BOUNDARY_TEXTURE, OP_BINK,
	OP_INVALIDATE, OP_REACTIVATE, OP_KIND_COUNT
};

Operation Make_Operation(Rng &rng)
{
	Operation op = {};
	const uint32_t roll = rng.Below(100U);
	op.kind = roll < 30U ? OP_SHADER : roll < 55U ? OP_DX8 : roll < 85U ? OP_DRAW :
		roll < 88U ? OP_BEGIN_FRAME : roll < 93U ? OP_BOUNDARY_TEXTURE :
		roll < 95U ? OP_BINK : roll < 98U ? OP_INVALIDATE : OP_REACTIVATE;
	// Shader state: few distinct values so redundant calls are common.
	op.a = rng.Next();
	op.b = Pick(rng, kCompares, 8U);
	op.c = Pick(rng, kSources, 4U);
	op.d = Pick(rng, kDestinations, 6U);
	op.e = Pick(rng, kCompares, 8U);
	op.f = kDX8States[rng.Below(11U)];
	op.g = Pick_DX8_Value(rng, op.f);
	op.projection = Pick_Matrix(rng, op.kind == OP_BOUNDARY_TEXTURE);
	op.modelview = Pick_Matrix(rng, false);
	return op;
}

#define APPLY_OPERATION(NS) \
void Apply_##NS(const Operation &op, bool boundary_hook) \
{ \
	using namespace NS; \
	switch (op.kind) { \
	case OP_SHADER: { \
		/* Apply_Original_Shader_State's raster sequence. */ \
		const bool alpha_test = (op.a & 1U) != 0U; \
		const bool blend = (op.a & 2U) != 0U; \
		const bool depth_write = (op.a & 4U) != 0U; \
		const bool color_write = (op.a & 8U) != 0U; \
		const bool cull = (op.a & 16U) != 0U; \
		const bool inverted = (op.a & 32U) != 0U; \
		const unsigned reference = (op.a >> 8U) & 3U ? 0x60U : 0x80U; \
		if (alpha_test) { \
			Shadow_Alpha_Test(true); \
			Shadow_Alpha_Func(op.b, static_cast<float>(reference) / 255.0f); \
		} else { \
			Shadow_Alpha_Test(false); \
		} \
		if (!blend) Shadow_Blend(false); \
		else { Shadow_Blend(true); Shadow_Blend_Func(op.c, op.d); } \
		Shadow_Depth_Func(op.e); \
		Shadow_Depth_Mask(depth_write ? GL_TRUE : GL_FALSE); \
		Shadow_Color_Mask(color_write ? GL_TRUE : GL_FALSE, color_write ? GL_TRUE : GL_FALSE, \
			color_write ? GL_TRUE : GL_FALSE, color_write ? GL_TRUE : GL_FALSE); \
		if (cull) { Shadow_Cull(true); Shadow_Cull_Face(inverted ? GL_FRONT : GL_BACK); } \
		else Shadow_Cull(false); \
		break; \
	} \
	case OP_DX8: \
		if (!Harness_DX8_Render_State(op.f, op.g)) abort(); \
		break; \
	case OP_DRAW: \
		/* Submit_Mesh_Internal / Submit_Indexed_Triangles transform protocol. */ \
		Shadow_Load_Transforms(op.projection, op.modelview); \
		Reset_Texture_Matrix_Stage(0U); \
		Reset_Texture_Matrix_Stage(1U); \
		break; \
	case OP_BEGIN_FRAME: \
		Shadow_Load_Transforms(NULL, NULL); \
		break; \
	case OP_BOUNDARY_TEXTURE: { \
		/* ww3d_dx8_boundary.cpp Apply_Texture_Stage_Transform. */ \
		const unsigned stage = op.a & 1U; \
		glActiveTexture(GL_TEXTURE0 + stage); \
		glMatrixMode(GL_TEXTURE); \
		if (op.projection == NULL) glLoadIdentity(); \
		else glLoadMatrixf(op.projection); \
		if (boundary_hook) Invalidate_Texture_Identity_Shadow(stage); \
		glMatrixMode(GL_MODELVIEW); \
		glActiveTexture(GL_TEXTURE0); \
		break; \
	} \
	case OP_BINK: { \
		/* BINKMovie::Render: raw changes, exact restore (push/pop matrices). */ \
		const GLenum mode = g_gl.matrix_mode; \
		const bool depth = g_gl.depth_test, cull = g_gl.cull, blend = g_gl.blend; \
		glDisable(GL_DEPTH_TEST); glDisable(GL_CULL_FACE); glDisable(GL_BLEND); \
		memcpy(g_gl.saved_projection, g_gl.projection, sizeof(g_gl.projection)); \
		memcpy(g_gl.saved_modelview, g_gl.modelview, sizeof(g_gl.modelview)); \
		glMatrixMode(GL_PROJECTION); glLoadMatrixf(g_matrix_pool[6]); \
		glMatrixMode(GL_MODELVIEW); glLoadIdentity(); \
		memcpy(g_gl.modelview, g_gl.saved_modelview, sizeof(g_gl.modelview)); \
		memcpy(g_gl.projection, g_gl.saved_projection, sizeof(g_gl.projection)); \
		glMatrixMode(mode); \
		if (depth) glEnable(GL_DEPTH_TEST); \
		if (cull) glEnable(GL_CULL_FACE); \
		if (blend) glEnable(GL_BLEND); \
		break; \
	} \
	case OP_INVALIDATE: \
		/* Invalidate_Native_State_Cache: render-target bind/restore, init. */ \
		Invalidate_GL_State_Shadow(); \
		break; \
	case OP_REACTIVATE: \
		/* Reactivate_Native_Backend_State: invalidate, then raw calls. */ \
		Invalidate_GL_State_Shadow(); \
		glEnable(GL_DEPTH_TEST); glDepthFunc(GL_LEQUAL); glDisable(GL_CULL_FACE); \
		glMatrixMode(GL_PROJECTION); glLoadIdentity(); \
		glMatrixMode(GL_MODELVIEW); glLoadIdentity(); \
		break; \
	default: abort(); \
	} \
}

APPLY_OPERATION(shadowed)
APPLY_OPERATION(plain)

void Reset_Models()
{
	shadowed::g_gl = GLModel();
	plain::g_gl = GLModel();
	shadowed::g_gl.matrix_mode = plain::g_gl.matrix_mode = GL_MODELVIEW;
	shadowed::Configure();
	plain::Configure();
	shadowed::Invalidate_GL_State_Shadow();
	plain::Invalidate_GL_State_Shadow();
	memset(&shadowed::g_gl_state_shadow_counters, 0, sizeof(shadowed::g_gl_state_shadow_counters));
	memset(&plain::g_gl_state_shadow_counters, 0, sizeof(plain::g_gl_state_shadow_counters));
	shadowed::g_dx8_alpha_function = plain::g_dx8_alpha_function = GL_ALWAYS;
	shadowed::g_dx8_alpha_reference = plain::g_dx8_alpha_reference = 0.0f;
	shadowed::g_dx8_source_blend = plain::g_dx8_source_blend = GL_ONE;
	shadowed::g_dx8_destination_blend = plain::g_dx8_destination_blend = GL_ZERO;
}

// Returns the first diverging operation index, or -1 when equivalent.
long Run_Sequence(uint64_t seed, unsigned length, bool boundary_hook)
{
	Reset_Models();
	Rng rng = { seed * 0x9E3779B97F4A7C15ULL + 1U };
	for (unsigned index = 0; index < length; ++index) {
		const Operation op = Make_Operation(rng);
		Apply_shadowed(op, boundary_hook);
		Apply_plain(op, boundary_hook);
		if (!Raster_Equal(shadowed::g_gl, plain::g_gl)) return static_cast<long>(index);
		if ((op.kind == OP_DRAW || op.kind == OP_BEGIN_FRAME || op.kind == OP_REACTIVATE) &&
			!Transforms_Equal(shadowed::g_gl, plain::g_gl)) {
			return static_cast<long>(index);
		}
		if (op.kind == OP_DRAW) {
			// The draw happens here; afterwards both release their transforms.
			shadowed::Release_Submission_Transforms();
			plain::Release_Submission_Transforms();
			if (!Raster_Equal(shadowed::g_gl, plain::g_gl)) return static_cast<long>(index);
		}
	}
	shadowed::Shadow_Load_Transforms(NULL, NULL);
	plain::Shadow_Load_Transforms(NULL, NULL);
	if (!Raster_Equal(shadowed::g_gl, plain::g_gl) ||
		!Transforms_Equal(shadowed::g_gl, plain::g_gl)) {
		return static_cast<long>(length);
	}
	return -1;
}

}  // namespace

int main(int argc, char **argv)
{
	const unsigned sequences = argc > 1 ? static_cast<unsigned>(atoi(argv[1])) : 2000U;
	const unsigned length = argc > 2 ? static_cast<unsigned>(atoi(argv[2])) : 400U;
	Build_Matrix_Pool();
	unsigned long long shadowed_calls = 0ULL, plain_calls = 0ULL;
	unsigned long long raster_skips = 0ULL, transform_skips = 0ULL, texture_skips = 0ULL;
	for (unsigned seed = 0; seed < sequences; ++seed) {
		const long divergence = Run_Sequence(seed, length, true);
		if (divergence >= 0) {
			printf("render state shadow FAIL seed=%u op=%ld\n", seed, divergence);
			return 1;
		}
		shadowed_calls += shadowed::g_gl.calls;
		plain_calls += plain::g_gl.calls;
		raster_skips += shadowed::g_gl_state_shadow_counters.raster_skips;
		transform_skips += shadowed::g_gl_state_shadow_counters.transform_skips;
		texture_skips += shadowed::g_gl_state_shadow_counters.texture_matrix_skips;
		if (plain::g_gl_state_shadow_counters.raster_skips != 0ULL ||
			plain::g_gl_state_shadow_counters.transform_skips != 0ULL ||
			plain::g_gl_state_shadow_counters.texture_matrix_skips != 0ULL) {
			printf("render state shadow FAIL disabled shadow skipped a call seed=%u\n", seed);
			return 1;
		}
	}
	if (shadowed_calls >= plain_calls || raster_skips == 0ULL || transform_skips == 0ULL ||
		texture_skips == 0ULL) {
		printf("render state shadow FAIL no reduction shadowed=%llu plain=%llu\n",
			shadowed_calls, plain_calls);
		return 1;
	}
	printf("render state shadow PASS sequences=%u length=%u gl_calls_shadowed=%llu gl_calls_plain=%llu raster_skips=%llu transform_skips=%llu texture_matrix_skips=%llu\n",
		sequences, length, shadowed_calls, plain_calls, raster_skips, transform_skips,
		texture_skips);
	// Negative control: without the boundary's texture-matrix invalidation the
	// shadow must be caught diverging, proving the comparison has teeth.
	unsigned detected = 0U;
	for (unsigned seed = 0; seed < 200U; ++seed) {
		if (Run_Sequence(seed, length, false) >= 0) ++detected;
	}
	if (detected == 0U) {
		printf("render state shadow FAIL negative control undetected\n");
		return 1;
	}
	printf("render state shadow negative control PASS detected=%u/200\n", detected);
	return 0;
}
