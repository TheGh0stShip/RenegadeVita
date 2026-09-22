#include "ww3d_vita_renderer.h"

#include "camera.h"
#include "d3d8.h"
#include "dx8wrapper.h"
#include "lightenvironment.h"
#include "mesh.h"
#include "meshmatdesc.h"
#include "meshmdl.h"
#include "matrix4.h"
#include "rendobj.h"
#include "rinfo.h"
#include "shader.h"
#include "texture.h"
#include "tri.h"
#include "vertmaterial.h"
#include "ww3d_vita_render_state_contract.h"

#include <stddef.h>
#include <new>
#include <stdio.h>
#include <string.h>

#if defined(RENEGADE_HOST_RENDERER_LIFECYCLE_SELFTEST) && defined(__GNUC__)
void RenegadeVita_Release_DX8_Bound_Textures() __attribute__((weak));
#endif

#if defined(__vita__)
#include "vita_runtime_log.h"
#include "renegade_vita_text_entry.h"

#include <psp2/io/stat.h>
#include <psp2/kernel/sysmem.h>
#include <vitaGL.h>
#include "ww3d_vita_indexed_mesh_batch.h"
extern "C" void vglRenegadeEndIndexed(GLsizei count, const GLushort *indices);
#endif

namespace RenegadeVitaRenderer {
namespace {

Statistics g_statistics = {};
BackendLifecycleStatistics g_lifecycle = {};
bool g_logged_first_unsupported = false;
bool g_logged_first_indexed_rejection = false;
Vector3 *g_deformed_skin_vertices = NULL;
Vector3 *g_deformed_skin_normals = NULL;
int g_deformed_skin_capacity = 0;

bool Ensure_Deformed_Skin_Scratch(int vertex_count)
{
	if (vertex_count <= g_deformed_skin_capacity) return true;
	// Avoid reallocating both arrays for every slightly larger character mesh.
	// Bound spare capacity to ordinary skin sizes; unusually large legitimate
	// meshes still receive their exact requested capacity, not a size rejection.
	int capacity = vertex_count;
	if (vertex_count <= 16384) {
		capacity = 256;
		while (capacity < vertex_count) capacity *= 2;
	}
	Vector3 *vertices = new (std::nothrow) Vector3[capacity];
	Vector3 *normals = new (std::nothrow) Vector3[capacity];
	if (vertices == NULL || normals == NULL) {
		delete[] vertices;
		delete[] normals;
		return false;
	}
	delete[] g_deformed_skin_vertices;
	delete[] g_deformed_skin_normals;
	g_deformed_skin_vertices = vertices;
	g_deformed_skin_normals = normals;
	g_deformed_skin_capacity = capacity;
	return true;
}

void Release_Deformed_Skin_Scratch()
{
	delete[] g_deformed_skin_vertices;
	delete[] g_deformed_skin_normals;
	g_deformed_skin_vertices = NULL;
	g_deformed_skin_normals = NULL;
	g_deformed_skin_capacity = 0;
}

struct NativePresentationRect {
	uint32_t x;
	uint32_t y;
	uint32_t width;
	uint32_t height;
};

NativePresentationRect g_native_presentation_rect = {
	0U, 0U, DISPLAY_WIDTH, DISPLAY_HEIGHT
};

#if defined(__vita__)
bool g_logged_first_frame = false;
bool g_logged_first_present = false;
bool g_logged_first_mesh = false;
bool g_logged_first_skin = false;
bool g_logged_first_stage1_mesh = false;
bool g_logged_first_texture_mapper = false;
bool g_logged_first_generated_texture_coordinate = false;
bool g_logged_first_material_lighting = false;
bool g_logged_first_user_lighting = false;
bool g_logged_skin_failure = false;
bool g_logged_first_passthrough_texture_v_preserved = false;
bool g_logged_first_skin_texture_color = false;
bool g_logged_first_skin_passthrough_texture_v_preserved = false;
bool g_logged_first_original_shader_state_skip = false;
bool g_logged_first_viewport_state_skip = false;
bool g_shader_compiler_available = false;
unsigned g_shader_init_calls = 0;
int g_shader_init_last_result = -1;
NativeViewport g_current_native_viewport = {};
bool g_current_native_viewport_known = false;

struct OriginalTextureCoordinateState {
	DWORD texcoord_index;
	DWORD texture_transform_flags;
	D3DMATRIX texture_transform;
};

char To_Lower_Ascii(char value)
{
	return value >= 'A' && value <= 'Z' ?
		static_cast<char>(value - 'A' + 'a') : value;
}

bool Contains_Ascii_No_Case(const char *text, const char *needle)
{
	if (text == NULL || needle == NULL || needle[0] == '\0') return false;
	for (const char *scan = text; *scan != '\0'; ++scan) {
		unsigned index = 0U;
		while (needle[index] != '\0' && scan[index] != '\0' &&
			To_Lower_Ascii(scan[index]) == To_Lower_Ascii(needle[index])) {
			++index;
		}
		if (needle[index] == '\0') return true;
	}
	return false;
}

bool Has_Loadscreen_Texture_Prefix(const char *name)
{
	if (name == NULL) return false;
	const char *base = name;
	for (const char *scan = name; *scan != '\0'; ++scan) {
		if (*scan == '/' || *scan == '\\') base = scan + 1;
	}
	const char prefix[] = "loadscreen_";
	for (unsigned index = 0U; prefix[index] != '\0'; ++index) {
		if (To_Lower_Ascii(base[index]) != prefix[index]) return false;
	}
	return true;
}

bool Is_Loading_Screen_Diagnostic_Name(const char *name)
{
	return Has_Loadscreen_Texture_Prefix(name) ||
		Contains_Ascii_No_Case(name, "lvl94load");
}

FogStateContract g_fog_state = Default_Fog_State();
uint32_t g_dx8_ambient_color = 0U;
GLenum g_dx8_alpha_function = GL_ALWAYS;
float g_dx8_alpha_reference = 0.0f;
GLenum g_dx8_source_blend = GL_ONE;
GLenum g_dx8_destination_blend = GL_ZERO;
bool g_logged_first_fog_state = false;
bool g_logged_first_ambient_state = false;
bool g_logged_first_unsupported_render_state = false;
bool g_logged_first_state_cache_skip = false;

struct NativeTextureStageCache {
	bool enabled_known;
	bool enabled;
	bool texture_known;
	uint32_t texture;
	bool sampler_known;
	uint32_t sampler_texture;
	uint32_t address_u;
	uint32_t address_v;
	uint32_t min_filter;
	uint32_t mag_filter;
	uint32_t mip_filter;
	bool combiner_known;
	bool combiner_texture_enabled;
	uint32_t color_op;
	uint32_t color_arg1;
	uint32_t color_arg2;
	uint32_t alpha_op;
	uint32_t alpha_arg1;
	uint32_t alpha_arg2;
};

struct NativeRenderStateCache {
	bool valid[256];
	uint32_t values[256];
};

NativeTextureStageCache g_texture_stage_cache[MeshMatDescClass::MAX_TEX_STAGES] = {};
NativeRenderStateCache g_render_state_cache = {};

// Dev127 candidate reuses invariant platform work. Original draw order,
// materials and texture ownership remain unchanged. RVRC1 0 restores the
// baseline for a matching physical comparison; no native acceptance is implied.
unsigned g_render_work_cache_mode = 15U;
VitaIndexedMeshBatch g_indexed_mesh_batch;
uint64_t g_mesh_expanded_corners = 0, g_mesh_unique_vertices = 0;
uint64_t g_mesh_indexed_batches = 0;
struct NativeTextureObjectSampler {
	uint32_t texture;
	GLenum wrap_u;
	GLenum wrap_v;
	GLenum min_filter;
	GLenum mag_filter;
	uint32_t generation;
};
enum { TEXTURE_OBJECT_SAMPLER_SLOTS = 1024 };
NativeTextureObjectSampler g_texture_object_samplers[TEXTURE_OBJECT_SAMPLER_SLOTS] = {};
uint32_t g_texture_object_sampler_generation = 1U;

void Invalidate_Texture_Object_Samplers()
{
	// Uploads and external GL users invalidate all object parameters. Tags make
	// the normal invalidation O(1), including repeated procedural HUD uploads.
	++g_texture_object_sampler_generation;
	if (g_texture_object_sampler_generation == 0U) {
		memset(g_texture_object_samplers, 0, sizeof(g_texture_object_samplers));
		g_texture_object_sampler_generation = 1U;
	}
}

void Read_Render_Work_Cache_Mode()
{
	g_render_work_cache_mode = 15U;
	FILE *file = fopen("ux0:data/renegade/user/config/render-work-cache-v1.flag", "rb");
	if (file != NULL) {
		char value[9] = {};
		const size_t size = fread(value, 1U, sizeof(value), file);
		const bool read_ok = !ferror(file);
		fclose(file);
		if (read_ok && size == 8U && memcmp(value, "RVRC1 ", 6U) == 0 &&
			value[7] == '\n') {
			if (value[6] >= '0' && value[6] <= '9') {
				g_render_work_cache_mode = static_cast<unsigned>(value[6] - '0');
			} else if (value[6] >= 'A' && value[6] <= 'F') {
				g_render_work_cache_mode = 10U + static_cast<unsigned>(value[6] - 'A');
			}
		}
	}
	Vita_Append_A22_Runtime_Breadcrumb("render-work-cache",
		"version=1 mode=%u sampler=%u material=%u direct_atlas_and_dds=%u indexed_work=%u default=15 acceptance=unassessed",
		g_render_work_cache_mode, g_render_work_cache_mode & 1U,
		(g_render_work_cache_mode >> 1U) & 1U,
		(g_render_work_cache_mode >> 2U) & 1U,
		(g_render_work_cache_mode >> 3U) & 1U);
}
bool g_original_shader_state_known = false;
uint32_t g_original_shader_state_bits = 0U;
bool g_original_shader_culling_inverted = false;

void Invalidate_Original_Shader_State_Cache()
{
	g_original_shader_state_known = false;
	g_original_shader_state_bits = 0U;
	g_original_shader_culling_inverted = false;
}

void Invalidate_Native_State_Cache()
{
	memset(g_texture_stage_cache, 0, sizeof(g_texture_stage_cache));
	Invalidate_Texture_Object_Samplers();
	memset(&g_render_state_cache, 0, sizeof(g_render_state_cache));
	Invalidate_Original_Shader_State_Cache();
	memset(&g_current_native_viewport, 0, sizeof(g_current_native_viewport));
	g_current_native_viewport_known = false;
	g_logged_first_state_cache_skip = false;
	g_logged_first_passthrough_texture_v_preserved = false;
	g_logged_first_skin_passthrough_texture_v_preserved = false;
	g_logged_first_original_shader_state_skip = false;
	g_logged_first_viewport_state_skip = false;
}

bool Texture_Stage_Index_Valid(uint32_t stage)
{
	return stage < MeshMatDescClass::MAX_TEX_STAGES;
}

bool Set_Texture_Stage_Enabled(uint32_t stage, bool enabled)
{
	if (stage >= MeshMatDescClass::MAX_TEX_STAGES) {
		Record_Texture_Unsupported_Stage(stage);
		return false;
	}
	NativeTextureStageCache &cache = g_texture_stage_cache[stage];
	if (cache.enabled_known && cache.enabled == enabled) {
		++g_statistics.texture_stage_enable_skips;
		if (!g_logged_first_state_cache_skip) {
			Vita_Append_A22_Runtime_Breadcrumb("render-state",
				"first cached VitaGL texture-stage enable skip: stage=%u enabled=%d",
				stage, enabled ? 1 : 0);
			g_logged_first_state_cache_skip = true;
		}
		return true;
	}
	glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage));
	if (enabled) {
		glEnable(GL_TEXTURE_2D);
	} else {
		glDisable(GL_TEXTURE_2D);
	}
	glActiveTexture(GL_TEXTURE0);
	cache.enabled_known = true;
	cache.enabled = enabled;
	++g_statistics.state_changes;
	return true;
}

bool Render_State_Cache_Matches(uint32_t state, uint32_t value)
{
	return state < 256U && g_render_state_cache.valid[state] &&
		g_render_state_cache.values[state] == value;
}

void Store_Render_State_Cache(uint32_t state, uint32_t value)
{
	if (state < 256U) {
		g_render_state_cache.valid[state] = true;
		g_render_state_cache.values[state] = value;
	}
}

void Invalidate_Render_State_Cache(uint32_t state)
{
	if (state < 256U) {
		g_render_state_cache.valid[state] = false;
	}
}

GLenum To_GL_Depth_Function(ShaderClass::DepthCompareType function)
{
	switch (function) {
	case ShaderClass::PASS_NEVER: return GL_NEVER;
	case ShaderClass::PASS_LESS: return GL_LESS;
	case ShaderClass::PASS_EQUAL: return GL_EQUAL;
	case ShaderClass::PASS_LEQUAL: return GL_LEQUAL;
	case ShaderClass::PASS_GREATER: return GL_GREATER;
	case ShaderClass::PASS_NOTEQUAL: return GL_NOTEQUAL;
	case ShaderClass::PASS_GEQUAL: return GL_GEQUAL;
	case ShaderClass::PASS_ALWAYS: return GL_ALWAYS;
	default: return GL_LEQUAL;
	}
}

GLenum To_GL_DX8_Compare(uint32_t function)
{
	switch (function) {
	case D3DCMP_NEVER: return GL_NEVER;
	case D3DCMP_LESS: return GL_LESS;
	case D3DCMP_EQUAL: return GL_EQUAL;
	case D3DCMP_LESSEQUAL: return GL_LEQUAL;
	case D3DCMP_GREATER: return GL_GREATER;
	case D3DCMP_NOTEQUAL: return GL_NOTEQUAL;
	case D3DCMP_GREATEREQUAL: return GL_GEQUAL;
	case D3DCMP_ALWAYS: return GL_ALWAYS;
	default: return GL_LEQUAL;
	}
}

GLenum To_GL_DX8_Blend(uint32_t function)
{
	switch (function) {
	case D3DBLEND_ZERO: return GL_ZERO;
	case D3DBLEND_ONE: return GL_ONE;
	case D3DBLEND_SRCCOLOR: return GL_SRC_COLOR;
	case D3DBLEND_INVSRCCOLOR: return GL_ONE_MINUS_SRC_COLOR;
	case D3DBLEND_SRCALPHA: return GL_SRC_ALPHA;
	case D3DBLEND_INVSRCALPHA: return GL_ONE_MINUS_SRC_ALPHA;
	case D3DBLEND_DESTALPHA: return GL_DST_ALPHA;
	case D3DBLEND_INVDESTALPHA: return GL_ONE_MINUS_DST_ALPHA;
	case D3DBLEND_DESTCOLOR: return GL_DST_COLOR;
	case D3DBLEND_INVDESTCOLOR: return GL_ONE_MINUS_DST_COLOR;
	case D3DBLEND_SRCALPHASAT: return GL_SRC_ALPHA_SATURATE;
	default: return GL_ONE;
	}
}

GLenum To_GL_DX8_Fill_Mode(uint32_t mode)
{
	switch (mode) {
	case D3DFILL_POINT: return GL_POINT;
	case D3DFILL_WIREFRAME: return GL_LINE;
	case D3DFILL_SOLID:
	default:
		return GL_FILL;
	}
}

GLenum To_GL_Source_Blend(ShaderClass::SrcBlendFuncType function)
{
	switch (function) {
	case ShaderClass::SRCBLEND_ZERO: return GL_ZERO;
	case ShaderClass::SRCBLEND_ONE: return GL_ONE;
	case ShaderClass::SRCBLEND_SRC_ALPHA: return GL_SRC_ALPHA;
	case ShaderClass::SRCBLEND_ONE_MINUS_SRC_ALPHA: return GL_ONE_MINUS_SRC_ALPHA;
	default: return GL_ONE;
	}
}

GLenum To_GL_Destination_Blend(ShaderClass::DstBlendFuncType function)
{
	switch (function) {
	case ShaderClass::DSTBLEND_ZERO: return GL_ZERO;
	case ShaderClass::DSTBLEND_ONE: return GL_ONE;
	case ShaderClass::DSTBLEND_SRC_COLOR: return GL_SRC_COLOR;
	case ShaderClass::DSTBLEND_ONE_MINUS_SRC_COLOR: return GL_ONE_MINUS_SRC_COLOR;
	case ShaderClass::DSTBLEND_SRC_ALPHA: return GL_SRC_ALPHA;
	case ShaderClass::DSTBLEND_ONE_MINUS_SRC_ALPHA: return GL_ONE_MINUS_SRC_ALPHA;
	default: return GL_ZERO;
	}
}

bool Apply_Current_Fog_State()
{
#if defined(__vita__)
	if (!g_statistics.initialized) {
		return true;
	}
	const GLfloat color[4] = {
		D3D_Color_Red_Unit(g_fog_state.color),
		D3D_Color_Green_Unit(g_fog_state.color),
		D3D_Color_Blue_Unit(g_fog_state.color),
		1.0f
	};
	glFogi(GL_FOG_MODE, GL_LINEAR);
	glFogf(GL_FOG_START, g_fog_state.start);
	glFogf(GL_FOG_END, g_fog_state.end);
	glFogfv(GL_FOG_COLOR, color);
	if (g_fog_state.enabled) {
		glEnable(GL_FOG);
	} else {
		glDisable(GL_FOG);
	}
	++g_statistics.state_changes;
	const GLenum error = glGetError();
	if (error != GL_NO_ERROR) {
		++g_statistics.backend_errors;
	}
	if (!g_logged_first_fog_state) {
		Vita_Append_A22_Runtime_Breadcrumb("render-state",
			"first original DX8 fog state: enabled=%d color=%06X start=%.3f end=%.3f glGetError=%08X",
			g_fog_state.enabled ? 1 : 0, g_fog_state.color & 0x00ffffffU,
			g_fog_state.start, g_fog_state.end, static_cast<unsigned>(error));
		g_logged_first_fog_state = true;
	}
	return error == GL_NO_ERROR;
#else
	return true;
#endif
}

bool Apply_Current_Ambient_State()
{
#if defined(__vita__)
	if (!g_statistics.initialized) {
		return true;
	}
	const GLfloat color[4] = {
		D3D_Color_Red_Unit(g_dx8_ambient_color),
		D3D_Color_Green_Unit(g_dx8_ambient_color),
		D3D_Color_Blue_Unit(g_dx8_ambient_color),
		1.0f
	};
	glLightModelfv(GL_LIGHT_MODEL_AMBIENT, color);
	++g_statistics.state_changes;
	const GLenum error = glGetError();
	if (error != GL_NO_ERROR) {
		++g_statistics.backend_errors;
	}
	if (!g_logged_first_ambient_state) {
		Vita_Append_A22_Runtime_Breadcrumb("render-state",
			"first original DX8 ambient state: color=%06X glGetError=%08X",
			g_dx8_ambient_color & 0x00ffffffU, static_cast<unsigned>(error));
		g_logged_first_ambient_state = true;
	}
	return error == GL_NO_ERROR;
#else
	return true;
#endif
}

void Apply_Original_Fog_State(const ShaderClass &shader)
{
	bool fog_enabled = false;
	uint32_t fog_color = DX8Wrapper::Get_Fog_Color();
	if (DX8Wrapper::Get_Current_Caps()->Is_Fog_Allowed() &&
		DX8Wrapper::Get_Fog_Enable()) {
		switch (shader.Get_Fog_Func()) {
		case ShaderClass::FOG_ENABLE:
			fog_enabled = true;
			break;
		case ShaderClass::FOG_SCALE_FRAGMENT:
			fog_color = 0U;
			fog_enabled = true;
			break;
		case ShaderClass::FOG_WHITE:
			fog_color = 0x00ffffffU;
			fog_enabled = true;
			break;
		case ShaderClass::FOG_DISABLE:
		default:
			fog_enabled = false;
			break;
		}
	}
	Apply_DX8_Render_State(D3DRS_FOGENABLE, fog_enabled ? 1U : 0U);
	if (fog_enabled) {
		Apply_DX8_Render_State(D3DRS_FOGCOLOR, fog_color);
	}
}

void Make_D3D_Identity(D3DMATRIX *matrix)
{
	memset(matrix, 0, sizeof(*matrix));
	matrix->m[0][0] = 1.0f;
	matrix->m[1][1] = 1.0f;
	matrix->m[2][2] = 1.0f;
	matrix->m[3][3] = 1.0f;
}

void Reset_Texture_Matrix_Stage(unsigned stage)
{
	glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage));
	glMatrixMode(GL_TEXTURE);
	glLoadIdentity();
	glMatrixMode(GL_MODELVIEW);
	glActiveTexture(GL_TEXTURE0);
}

void Capture_Original_Texture_Coordinate_State(unsigned stage,
	OriginalTextureCoordinateState *state)
{
	state->texcoord_index = D3DTSS_TCI_PASSTHRU | stage;
	state->texture_transform_flags = D3DTTFF_DISABLE;
	Make_D3D_Identity(&state->texture_transform);
	RenegadeVita_Get_DX8_Texture_Coordinate_State(stage,
		&state->texcoord_index, &state->texture_transform_flags,
		&state->texture_transform);
	Reset_Texture_Matrix_Stage(stage);
}

DWORD Texture_Coordinate_Mode(const OriginalTextureCoordinateState &state)
{
	return state.texcoord_index & 0xffff0000U;
}

bool Uses_Generated_Texture_Coordinates(
	const OriginalTextureCoordinateState &state)
{
	const DWORD mode = Texture_Coordinate_Mode(state);
	return mode == D3DTSS_TCI_CAMERASPACENORMAL ||
		mode == D3DTSS_TCI_CAMERASPACEPOSITION ||
		mode == D3DTSS_TCI_CAMERASPACEREFLECTIONVECTOR;
}

const Vector2 *Resolve_UV_Array_For_Texture_State(MeshModelClass *model,
	const OriginalTextureCoordinateState &state, const Vector2 *fallback)
{
	const int uv_source = static_cast<int>(state.texcoord_index & 0xffffU);
	if (uv_source >= 0 && uv_source < MeshMatDescClass::MAX_UV_ARRAYS) {
		const Vector2 *uvs = model->Get_UV_Array_By_Index(uv_source);
		if (uvs != NULL) return uvs;
	}
	return fallback;
}

Vector3 Normalize_Or_Default(Vector3 value, const Vector3 &fallback)
{
	if (value.Length2() <= 0.000001f) return fallback;
	value.Normalize();
	return value;
}

Vector3 Compute_Camera_Space_Position(const Matrix3D &world_transform,
	const Matrix3D &view_transform, const Vector3 &position)
{
	Vector3 world_position;
	Matrix3D::Transform_Vector(world_transform, position, &world_position);
	Vector3 camera_position;
	Matrix3D::Transform_Vector(view_transform, world_position, &camera_position);
	return camera_position;
}

Vector3 Compute_Camera_Space_Normal(const Matrix3D &world_transform,
	const Matrix3D &view_transform, const Vector3 &normal)
{
	Vector3 world_normal;
	Matrix3D::Rotate_Vector(world_transform, normal, &world_normal);
	Vector3 camera_normal;
	Matrix3D::Rotate_Vector(view_transform, world_normal, &camera_normal);
	return Normalize_Or_Default(camera_normal, Vector3(0.0f, 0.0f, 1.0f));
}

Vector3 Compute_World_Space_Normal(const Matrix3D &world_transform,
	const Vector3 &normal)
{
	Vector3 world_normal;
	Matrix3D::Rotate_Vector(world_transform, normal, &world_normal);
	return Normalize_Or_Default(world_normal, Vector3(0.0f, 0.0f, 1.0f));
}

Vector3 Compute_Camera_Space_Reflection(const Matrix3D &world_transform,
	const Matrix3D &view_transform, const Vector3 &position,
	const Vector3 &normal)
{
	const Vector3 camera_position =
		Compute_Camera_Space_Position(world_transform, view_transform, position);
	const Vector3 camera_normal =
		Compute_Camera_Space_Normal(world_transform, view_transform, normal);
	const Vector3 eye_vector =
		Normalize_Or_Default(-camera_position, Vector3(0.0f, 0.0f, 1.0f));
	const float dot = Vector3::Dot_Product(camera_normal, eye_vector);
	return Normalize_Or_Default((2.0f * dot * camera_normal) - eye_vector,
		Vector3(0.0f, 0.0f, 1.0f));
}

void Apply_DX8_Texture_Transform(const OriginalTextureCoordinateState &state,
	float in_s, float in_t, float in_r, float in_q, float *out_s,
	float *out_t)
{
	float transformed[4] = { in_s, in_t, in_r, in_q };
	const DWORD coordinate_count = state.texture_transform_flags & 0xffU;
	if (coordinate_count != D3DTTFF_DISABLE) {
		const D3DMATRIX &matrix = state.texture_transform;
		const float source[4] = { in_s, in_t, in_r, in_q };
		for (unsigned column = 0U; column < 4U; ++column) {
			transformed[column] =
				source[0] * matrix.m[0][column] +
				source[1] * matrix.m[1][column] +
				source[2] * matrix.m[2][column] +
				source[3] * matrix.m[3][column];
		}
	}
	if ((state.texture_transform_flags & D3DTTFF_PROJECTED) != 0U &&
		coordinate_count >= D3DTTFF_COUNT2 &&
		coordinate_count <= D3DTTFF_COUNT4) {
		const float divisor = transformed[coordinate_count - 1U];
		if (divisor < -0.000001f || divisor > 0.000001f) {
			transformed[0] /= divisor;
			transformed[1] /= divisor;
		}
	}
	*out_s = transformed[0];
	*out_t = coordinate_count == D3DTTFF_COUNT1 ? 0.0f : transformed[1];
}

bool Emit_Original_Texture_Coordinate(unsigned stage, GLenum texture_unit,
	const OriginalTextureCoordinateState &state, const Vector2 *uvs,
	const Vector3 *vertices, const Vector3 *normals, unsigned vertex_index,
	const Matrix3D &world_transform, const Matrix3D &view_transform,
	const char *texture_name)
{
	float source_s = 0.0f;
	float source_t = 0.0f;
	float source_r = 0.0f;
	const DWORD mode = Texture_Coordinate_Mode(state);
	if (mode == D3DTSS_TCI_PASSTHRU) {
		if (uvs == NULL) return false;
		source_s = uvs[vertex_index].X;
		source_t = uvs[vertex_index].Y;
	} else if (mode == D3DTSS_TCI_CAMERASPACENORMAL) {
		if (normals == NULL) return false;
		const Vector3 camera_normal = Compute_Camera_Space_Normal(
			world_transform, view_transform, normals[vertex_index]);
		source_s = camera_normal.X;
		source_t = camera_normal.Y;
		source_r = camera_normal.Z;
	} else if (mode == D3DTSS_TCI_CAMERASPACEPOSITION) {
		const Vector3 camera_position = Compute_Camera_Space_Position(
			world_transform, view_transform, vertices[vertex_index]);
		source_s = camera_position.X;
		source_t = camera_position.Y;
		source_r = camera_position.Z;
	} else if (mode == D3DTSS_TCI_CAMERASPACEREFLECTIONVECTOR) {
		if (normals == NULL) return false;
		const Vector3 reflection = Compute_Camera_Space_Reflection(
			world_transform, view_transform, vertices[vertex_index],
			normals[vertex_index]);
		source_s = reflection.X;
		source_t = reflection.Y;
		source_r = reflection.Z;
	} else {
		if (uvs == NULL) return false;
		source_s = uvs[vertex_index].X;
		source_t = uvs[vertex_index].Y;
	}
	if (!g_logged_first_passthrough_texture_v_preserved &&
		mode == D3DTSS_TCI_PASSTHRU &&
		!Has_Loadscreen_Texture_Prefix(texture_name)) {
		Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
			"first gameplay passthrough texture V preserved: texture=%s stage=%u",
			texture_name != NULL ? texture_name : "none", stage);
		g_logged_first_passthrough_texture_v_preserved = true;
	}
	float s = 0.0f;
	float t = 0.0f;
	Apply_DX8_Texture_Transform(state, source_s, source_t, source_r, 1.0f,
		&s, &t);
	glMultiTexCoord2f(texture_unit, s, t);
	if (!g_logged_first_generated_texture_coordinate &&
		Uses_Generated_Texture_Coordinates(state)) {
		Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
			"first generated texture coordinates: stage=%u mode=%08X flags=%08X source=(%.3f,%.3f,%.3f) final=(%.3f,%.3f)",
			stage, static_cast<unsigned>(mode),
			static_cast<unsigned>(state.texture_transform_flags),
			source_s, source_t, source_r, s, t);
		g_logged_first_generated_texture_coordinate = true;
	}
	return true;
}

Vector3 Transform_DX8_Row_Point(const float *matrix, const Vector3 &position)
{
	return Vector3(
		position.X * matrix[0] + position.Y * matrix[4] +
			position.Z * matrix[8] + matrix[12],
		position.X * matrix[1] + position.Y * matrix[5] +
			position.Z * matrix[9] + matrix[13],
		position.X * matrix[2] + position.Y * matrix[6] +
			position.Z * matrix[10] + matrix[14]);
}

Vector3 Rotate_DX8_Row_Vector(const float *matrix, const Vector3 &vector)
{
	return Vector3(
		vector.X * matrix[0] + vector.Y * matrix[4] +
			vector.Z * matrix[8],
		vector.X * matrix[1] + vector.Y * matrix[5] +
			vector.Z * matrix[9],
		vector.X * matrix[2] + vector.Y * matrix[6] +
			vector.Z * matrix[10]);
}

Vector3 Compute_Indexed_Camera_Space_Position(const float *world_transform,
	const float *view_transform, const float position[3])
{
	const Vector3 world_position = Transform_DX8_Row_Point(world_transform,
		Vector3(position[0], position[1], position[2]));
	return Transform_DX8_Row_Point(view_transform, world_position);
}

Vector3 Compute_Indexed_Camera_Space_Normal(const float *world_transform,
	const float *view_transform, const float normal[3])
{
	const Vector3 world_normal = Rotate_DX8_Row_Vector(world_transform,
		Vector3(normal[0], normal[1], normal[2]));
	const Vector3 camera_normal = Rotate_DX8_Row_Vector(view_transform,
		world_normal);
	return Normalize_Or_Default(camera_normal, Vector3(0.0f, 0.0f, 1.0f));
}

Vector3 Compute_Indexed_Camera_Space_Reflection(const float *world_transform,
	const float *view_transform, const float position[3], const float normal[3])
{
	const Vector3 camera_position = Compute_Indexed_Camera_Space_Position(
		world_transform, view_transform, position);
	const Vector3 camera_normal = Compute_Indexed_Camera_Space_Normal(
		world_transform, view_transform, normal);
	const Vector3 eye_vector =
		Normalize_Or_Default(-camera_position, Vector3(0.0f, 0.0f, 1.0f));
	const float dot = Vector3::Dot_Product(camera_normal, eye_vector);
	return Normalize_Or_Default((2.0f * dot * camera_normal) - eye_vector,
		Vector3(0.0f, 0.0f, 1.0f));
}

const float *Select_Indexed_UV_Array(
	const OriginalTextureCoordinateState &state, const float uv0[2],
	const float uv1[2])
{
	const DWORD uv_source = state.texcoord_index & 0xffffU;
	return uv_source == 1U ? uv1 : uv0;
}

bool Emit_Indexed_Texture_Coordinate(unsigned stage, GLenum texture_unit,
	const OriginalTextureCoordinateState &state, const float uv0[2],
	const float uv1[2], const float position[3], const float normal[3],
	const float *world_transform, const float *view_transform,
	const char *texture_name)
{
	float source_s = 0.0f;
	float source_t = 0.0f;
	float source_r = 0.0f;
	const DWORD mode = Texture_Coordinate_Mode(state);
	if (mode == D3DTSS_TCI_PASSTHRU) {
		const float *uv = Select_Indexed_UV_Array(state, uv0, uv1);
		source_s = uv[0];
		source_t = uv[1];
	} else if (mode == D3DTSS_TCI_CAMERASPACENORMAL) {
		const Vector3 camera_normal = Compute_Indexed_Camera_Space_Normal(
			world_transform, view_transform, normal);
		source_s = camera_normal.X;
		source_t = camera_normal.Y;
		source_r = camera_normal.Z;
	} else if (mode == D3DTSS_TCI_CAMERASPACEPOSITION) {
		const Vector3 camera_position = Compute_Indexed_Camera_Space_Position(
			world_transform, view_transform, position);
		source_s = camera_position.X;
		source_t = camera_position.Y;
		source_r = camera_position.Z;
	} else if (mode == D3DTSS_TCI_CAMERASPACEREFLECTIONVECTOR) {
		const Vector3 reflection = Compute_Indexed_Camera_Space_Reflection(
			world_transform, view_transform, position, normal);
		source_s = reflection.X;
		source_t = reflection.Y;
		source_r = reflection.Z;
	} else {
		const float *uv = Select_Indexed_UV_Array(state, uv0, uv1);
		source_s = uv[0];
		source_t = uv[1];
	}
	if (!g_logged_first_passthrough_texture_v_preserved &&
		mode == D3DTSS_TCI_PASSTHRU &&
		!Has_Loadscreen_Texture_Prefix(texture_name)) {
		Vita_Append_A22_Runtime_Breadcrumb("indexed-submit",
			"first indexed gameplay passthrough texture V preserved: texture=%s stage=%u",
			texture_name != NULL ? texture_name : "none", stage);
		g_logged_first_passthrough_texture_v_preserved = true;
	}

	float s = 0.0f;
	float t = 0.0f;
	Apply_DX8_Texture_Transform(state, source_s, source_t, source_r, 1.0f,
		&s, &t);
	glMultiTexCoord2f(texture_unit, s, t);
	if (!g_logged_first_generated_texture_coordinate &&
		Uses_Generated_Texture_Coordinates(state)) {
		Vita_Append_A22_Runtime_Breadcrumb("indexed-submit",
			"first generated texture coordinates: stage=%u mode=%08X flags=%08X source=(%.3f,%.3f,%.3f) final=(%.3f,%.3f)",
			stage, static_cast<unsigned>(mode),
			static_cast<unsigned>(state.texture_transform_flags),
			source_s, source_t, source_r, s, t);
		g_logged_first_generated_texture_coordinate = true;
	}
	return true;
}

void Apply_Original_Shader_State(const ShaderClass &shader)
{
	Apply_Original_Fog_State(shader);
	const uint32_t shader_bits = shader.Get_Bits();
	// Original culling inversion is global, not encoded in ShaderClass bits.
	const bool culling_inverted = ShaderClass::Is_Backface_Culling_Inverted();
	if (g_original_shader_state_known &&
		g_original_shader_state_bits == shader_bits &&
		g_original_shader_culling_inverted == culling_inverted) {
		if (!g_logged_first_original_shader_state_skip) {
			Vita_Append_A22_Runtime_Breadcrumb("render-state",
				"first cached original ShaderClass state skip: bits=%08X",
				static_cast<unsigned>(shader_bits));
			g_logged_first_original_shader_state_skip = true;
		}
		return;
	}
	const ShaderStateContract state = Translate_Shader_State(shader);
	if (shader.Get_Texturing() == ShaderClass::TEXTURING_ENABLE) {
		glActiveTexture(GL_TEXTURE0);
		glEnable(GL_TEXTURE_2D);
		switch (shader.Get_Primary_Gradient()) {
		case ShaderClass::GRADIENT_DISABLE:
			/* Original ShaderClass::Apply maps this to D3DTOP_SELECTARG1 with
			** D3DTA_TEXTURE for color and alpha.  The Vita fixed-function
			** default is modulation; leaving that default multiplies valid
			** M00 textures by black DCG/material colours and produces the
			** physical all-black-surface regression seen in dev16. */
			glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE);
			break;
		case ShaderClass::GRADIENT_ADD:
			glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_ADD);
			break;
		default:
			glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
			break;
		}
	} else {
		glActiveTexture(GL_TEXTURE0);
		glDisable(GL_TEXTURE_2D);
		glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE);
	}
	if (state.alpha_test) {
		glEnable(GL_ALPHA_TEST);
		glAlphaFunc(To_GL_Depth_Function(state.alpha_compare),
			static_cast<float>(state.alpha_reference) / 255.0f);
	} else {
		glDisable(GL_ALPHA_TEST);
	}
	const GLenum source = To_GL_Source_Blend(shader.Get_Src_Blend_Func());
	const GLenum destination = To_GL_Destination_Blend(shader.Get_Dst_Blend_Func());
	if (!state.blend) glDisable(GL_BLEND);
	else {
		glEnable(GL_BLEND);
		glBlendFunc(source, destination);
	}
	glDepthFunc(To_GL_Depth_Function(state.depth_compare));
	glDepthMask(state.depth_write ? GL_TRUE : GL_FALSE);
	glColorMask(state.color_write ? GL_TRUE : GL_FALSE, state.color_write ? GL_TRUE : GL_FALSE,
		state.color_write ? GL_TRUE : GL_FALSE, state.color_write ? GL_TRUE : GL_FALSE);
	if (state.cull) {
		glEnable(GL_CULL_FACE);
		glCullFace(culling_inverted ? GL_FRONT : GL_BACK);
	} else glDisable(GL_CULL_FACE);
	g_texture_stage_cache[0].enabled_known = true;
	g_texture_stage_cache[0].enabled =
		shader.Get_Texturing() == ShaderClass::TEXTURING_ENABLE;
	g_texture_stage_cache[0].combiner_known = false;
	Invalidate_Render_State_Cache(D3DRS_ALPHATESTENABLE);
	Invalidate_Render_State_Cache(D3DRS_ALPHAREF);
	Invalidate_Render_State_Cache(D3DRS_ALPHAFUNC);
	Invalidate_Render_State_Cache(D3DRS_ALPHABLENDENABLE);
	Invalidate_Render_State_Cache(D3DRS_SRCBLEND);
	Invalidate_Render_State_Cache(D3DRS_DESTBLEND);
	Invalidate_Render_State_Cache(D3DRS_ZFUNC);
	Invalidate_Render_State_Cache(D3DRS_ZWRITEENABLE);
	Invalidate_Render_State_Cache(D3DRS_CULLMODE);
	g_original_shader_state_known = true;
	g_original_shader_state_bits = shader_bits;
	g_original_shader_culling_inverted = culling_inverted;
	++g_statistics.state_changes;
}

GLenum To_GL_Texture_Argument(uint32_t argument)
{
	switch (argument) {
	case D3DTA_TEXTURE: return GL_TEXTURE;
	case D3DTA_DIFFUSE: return GL_PRIMARY_COLOR;
	case D3DTA_CURRENT: return GL_PREVIOUS;
	default: return GL_PREVIOUS;
	}
}

void Set_Texture_Env_White_Constant()
{
	GLfloat white[4] = { 1.0f, 1.0f, 1.0f, 1.0f };
	glTexEnvfv(GL_TEXTURE_ENV, GL_TEXTURE_ENV_COLOR, white);
}

void Apply_GL_RGB_Texture_Op(uint32_t operation, uint32_t argument0,
	uint32_t argument1)
{
	switch (operation) {
	case D3DTOP_SELECTARG1:
	case D3DTOP_SELECTARG2:
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_RGB, GL_REPLACE);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_RGB,
			To_GL_Texture_Argument(operation == D3DTOP_SELECTARG1 ?
				argument0 : argument1));
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_RGB, GL_SRC_COLOR);
		break;
	case D3DTOP_MODULATE:
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_RGB, GL_MODULATE);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_RGB,
			To_GL_Texture_Argument(argument0));
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_RGB,
			To_GL_Texture_Argument(argument1));
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_RGB, GL_SRC_COLOR);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_RGB, GL_SRC_COLOR);
		break;
	case D3DTOP_ADD:
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_RGB, GL_ADD);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_RGB,
			To_GL_Texture_Argument(argument0));
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_RGB,
			To_GL_Texture_Argument(argument1));
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_RGB, GL_SRC_COLOR);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_RGB, GL_SRC_COLOR);
		break;
	case D3DTOP_ADDSMOOTH:
		Set_Texture_Env_White_Constant();
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_RGB, GL_INTERPOLATE);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_RGB, GL_CONSTANT);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_RGB,
			To_GL_Texture_Argument(argument0));
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC2_RGB,
			To_GL_Texture_Argument(argument1));
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_RGB, GL_SRC_COLOR);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_RGB, GL_SRC_COLOR);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND2_RGB, GL_SRC_COLOR);
		break;
	case D3DTOP_SUBTRACT:
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_RGB, GL_SUBTRACT);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_RGB,
			To_GL_Texture_Argument(argument0));
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_RGB,
			To_GL_Texture_Argument(argument1));
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_RGB, GL_SRC_COLOR);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_RGB, GL_SRC_COLOR);
		break;
	case D3DTOP_BLENDTEXTUREALPHA:
	case D3DTOP_BLENDCURRENTALPHA:
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_RGB, GL_INTERPOLATE);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_RGB,
			To_GL_Texture_Argument(argument0));
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_RGB,
			To_GL_Texture_Argument(argument1));
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC2_RGB,
			operation == D3DTOP_BLENDTEXTUREALPHA ? GL_TEXTURE : GL_PREVIOUS);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_RGB, GL_SRC_COLOR);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_RGB, GL_SRC_COLOR);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND2_RGB, GL_SRC_ALPHA);
		break;
	case D3DTOP_DISABLE:
	default:
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_RGB, GL_REPLACE);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_RGB, GL_PREVIOUS);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_RGB, GL_SRC_COLOR);
		break;
	}
}

void Apply_GL_Alpha_Texture_Op(uint32_t operation, uint32_t argument0,
	uint32_t argument1)
{
	switch (operation) {
	case D3DTOP_SELECTARG1:
	case D3DTOP_SELECTARG2:
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_ALPHA, GL_REPLACE);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_ALPHA,
			To_GL_Texture_Argument(operation == D3DTOP_SELECTARG1 ?
				argument0 : argument1));
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_ALPHA, GL_SRC_ALPHA);
		break;
	case D3DTOP_MODULATE:
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_ALPHA, GL_MODULATE);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_ALPHA,
			To_GL_Texture_Argument(argument0));
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_ALPHA,
			To_GL_Texture_Argument(argument1));
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_ALPHA, GL_SRC_ALPHA);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_ALPHA, GL_SRC_ALPHA);
		break;
	case D3DTOP_ADD:
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_ALPHA, GL_ADD);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_ALPHA,
			To_GL_Texture_Argument(argument0));
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_ALPHA,
			To_GL_Texture_Argument(argument1));
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_ALPHA, GL_SRC_ALPHA);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_ALPHA, GL_SRC_ALPHA);
		break;
	case D3DTOP_ADDSMOOTH:
		Set_Texture_Env_White_Constant();
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_ALPHA, GL_INTERPOLATE);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_ALPHA, GL_CONSTANT);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_ALPHA,
			To_GL_Texture_Argument(argument0));
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC2_ALPHA,
			To_GL_Texture_Argument(argument1));
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_ALPHA, GL_SRC_ALPHA);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_ALPHA, GL_SRC_ALPHA);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND2_ALPHA, GL_SRC_ALPHA);
		break;
	case D3DTOP_SUBTRACT:
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_ALPHA, GL_SUBTRACT);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_ALPHA,
			To_GL_Texture_Argument(argument0));
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC1_ALPHA,
			To_GL_Texture_Argument(argument1));
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_ALPHA, GL_SRC_ALPHA);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND1_ALPHA, GL_SRC_ALPHA);
		break;
	case D3DTOP_DISABLE:
	default:
		glTexEnvi(GL_TEXTURE_ENV, GL_COMBINE_ALPHA, GL_REPLACE);
		glTexEnvi(GL_TEXTURE_ENV, GL_SRC0_ALPHA, GL_PREVIOUS);
		glTexEnvi(GL_TEXTURE_ENV, GL_OPERAND0_ALPHA, GL_SRC_ALPHA);
		break;
	}
}

uint32_t Original_Primary_Color_Op(const ShaderClass &shader)
{
	if (shader.Get_Texturing() != ShaderClass::TEXTURING_ENABLE) {
		return D3DTOP_DISABLE;
	}
	switch (shader.Get_Primary_Gradient()) {
	case ShaderClass::GRADIENT_DISABLE: return D3DTOP_SELECTARG1;
	case ShaderClass::GRADIENT_ADD: return D3DTOP_ADD;
	default: return D3DTOP_MODULATE;
	}
}

uint32_t Original_Primary_Alpha_Op(const ShaderClass &shader)
{
	if (shader.Get_Texturing() != ShaderClass::TEXTURING_ENABLE) {
		return D3DTOP_DISABLE;
	}
	switch (shader.Get_Primary_Gradient()) {
	case ShaderClass::GRADIENT_DISABLE: return D3DTOP_SELECTARG1;
	default: return D3DTOP_MODULATE;
	}
}

uint32_t Original_Post_Detail_Color_Op(const ShaderClass &shader)
{
	if (shader.Get_Texturing() != ShaderClass::TEXTURING_ENABLE) {
		return D3DTOP_DISABLE;
	}
	switch (shader.Get_Post_Detail_Color_Func()) {
	case ShaderClass::DETAILCOLOR_DETAIL: return D3DTOP_SELECTARG1;
	case ShaderClass::DETAILCOLOR_SCALE: return D3DTOP_MODULATE;
	case ShaderClass::DETAILCOLOR_INVSCALE: return D3DTOP_ADDSMOOTH;
	case ShaderClass::DETAILCOLOR_ADD: return D3DTOP_ADD;
	case ShaderClass::DETAILCOLOR_SUB: return D3DTOP_SUBTRACT;
	case ShaderClass::DETAILCOLOR_SUBR: return D3DTOP_SUBTRACT;
	case ShaderClass::DETAILCOLOR_BLEND: return D3DTOP_BLENDTEXTUREALPHA;
	case ShaderClass::DETAILCOLOR_DETAILBLEND: return D3DTOP_BLENDCURRENTALPHA;
	default: return D3DTOP_DISABLE;
	}
}

uint32_t Original_Post_Detail_Color_Arg1(const ShaderClass &shader)
{
	return shader.Get_Post_Detail_Color_Func() == ShaderClass::DETAILCOLOR_SUBR ?
		D3DTA_CURRENT : D3DTA_TEXTURE;
}

uint32_t Original_Post_Detail_Color_Arg2(const ShaderClass &shader)
{
	return shader.Get_Post_Detail_Color_Func() == ShaderClass::DETAILCOLOR_SUBR ?
		D3DTA_TEXTURE : D3DTA_CURRENT;
}

uint32_t Original_Post_Detail_Alpha_Op(const ShaderClass &shader)
{
	if (shader.Get_Texturing() != ShaderClass::TEXTURING_ENABLE) {
		return D3DTOP_DISABLE;
	}
	switch (shader.Get_Post_Detail_Alpha_Func()) {
	case ShaderClass::DETAILALPHA_DETAIL: return D3DTOP_SELECTARG1;
	case ShaderClass::DETAILALPHA_SCALE: return D3DTOP_MODULATE;
	case ShaderClass::DETAILALPHA_INVSCALE: return D3DTOP_ADDSMOOTH;
	default: return D3DTOP_DISABLE;
	}
}

void Apply_Original_Texture_Stage_State(const ShaderClass &shader,
	bool stage0_texture, bool stage1_texture)
{
	Apply_DX8_Texture_Stage_State(0U,
		Original_Primary_Color_Op(shader), D3DTA_TEXTURE, D3DTA_DIFFUSE,
		Original_Primary_Alpha_Op(shader), D3DTA_TEXTURE, D3DTA_DIFFUSE,
		stage0_texture);
	Apply_DX8_Texture_Stage_State(1U,
		Original_Post_Detail_Color_Op(shader),
		Original_Post_Detail_Color_Arg1(shader),
		Original_Post_Detail_Color_Arg2(shader),
		Original_Post_Detail_Alpha_Op(shader), D3DTA_TEXTURE, D3DTA_CURRENT,
		stage1_texture);
}

int Get_Original_UV_Source(VertexMaterialClass *material, unsigned stage)
{
	const int fallback_uv_source = static_cast<int>(stage);
	if (material == NULL) return fallback_uv_source;
	const int uv_source = material->Get_UV_Source(static_cast<int>(stage));
	return uv_source >= 0 ? uv_source : fallback_uv_source;
}

void Apply_Original_Texture_Coordinate_State(VertexMaterialClass *material)
{
	for (unsigned stage = 0U; stage < MeshMatDescClass::MAX_TEX_STAGES; ++stage) {
		const int uv_source = Get_Original_UV_Source(material, stage);
		TextureMapperClass *mapper = NULL;
		if (material != NULL) mapper = material->Peek_Mapper(static_cast<int>(stage));
		if (mapper != NULL) {
			mapper->Apply(uv_source);
			if (!g_logged_first_texture_mapper) {
				Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
					"first original VertexMaterial mapper: material=%s stage=%u mapper=%d uv=%d",
					material != NULL ? material->Get_Name() : "NULL",
					stage, mapper->Mapper_ID(), uv_source);
				g_logged_first_texture_mapper = true;
			}
		} else {
			DX8Wrapper::Set_DX8_Texture_Stage_State(stage,
				D3DTSS_TEXCOORDINDEX,
				D3DTSS_TCI_PASSTHRU | static_cast<unsigned>(uv_source));
			DX8Wrapper::Set_DX8_Texture_Stage_State(stage,
				D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_DISABLE);
		}
	}
}

float Clamp01(float value)
{
	return value < 0.0f ? 0.0f : (value > 1.0f ? 1.0f : value);
}

Vector3 Multiply_Color(const Vector3 &left, const Vector3 &right)
{
	return Vector3(left.X * right.X, left.Y * right.Y, left.Z * right.Z);
}

Vector3 Scale_Color(const Vector3 &color, float scale)
{
	return Vector3(color.X * scale, color.Y * scale, color.Z * scale);
}

Vector3 Clamp_Color(Vector3 color)
{
	color.X = Clamp01(color.X);
	color.Y = Clamp01(color.Y);
	color.Z = Clamp01(color.Z);
	return color;
}

Vector3 Decode_DX8_ARGB_Color(unsigned color)
{
	return Vector3(
		static_cast<float>((color >> 16U) & 0xffU) / 255.0f,
		static_cast<float>((color >> 8U) & 0xffU) / 255.0f,
		static_cast<float>(color & 0xffU) / 255.0f);
}

float Decode_DX8_ARGB_Alpha(unsigned color)
{
	return static_cast<float>((color >> 24U) & 0xffU) / 255.0f;
}

struct SourceColor {
	Vector3 color;
	float alpha;
	bool from_vertex_color;
};

SourceColor Select_Material_Color_Source(
	VertexMaterialClass::ColorSourceType source, const Vector3 &material_color,
	float material_alpha, const unsigned *color1, const unsigned *color2,
	unsigned vertex_index)
{
	const unsigned *source_color = NULL;
	if (source == VertexMaterialClass::COLOR1) {
		source_color = color1;
	} else if (source == VertexMaterialClass::COLOR2) {
		source_color = color2;
	}
	if (source_color != NULL) {
		const unsigned color = source_color[vertex_index];
		SourceColor result = {
			Decode_DX8_ARGB_Color(color),
			Decode_DX8_ARGB_Alpha(color),
			true
		};
		return result;
	}
	SourceColor result = { material_color, material_alpha, false };
	return result;
}

struct MaterialVertexColor {
	Vector3 diffuse;
	Vector3 ambient;
	Vector3 emissive;
	Vector3 final_color;
	float alpha;
	bool lighting;
	unsigned light_count;
};

struct MaterialLightDirections {
	Vector3 normalized[4];
};

void Prepare_Material_Light_Directions(const RenderInfoClass &render_info,
	MaterialLightDirections &directions)
{
	const LightEnvironmentClass *environment = render_info.light_environment;
	if (environment == NULL) return;
	const int light_count = environment->Get_Light_Count();
	for (int index = 0; index < light_count && index < 4; ++index) {
		directions.normalized[index] = Normalize_Or_Default(
			environment->Get_Light_Direction(index), Vector3(0.0f, 0.0f, 1.0f));
		++g_statistics.material_light_normalizations;
	}
}

struct CachedMaterialVertexColor {
	MaterialVertexColor color;
	VertexMaterialClass *material;
	unsigned vertex_index;
	uint32_t generation;
};

CachedMaterialVertexColor *g_material_color_scratch = NULL;
int g_material_color_capacity = 0;
uint32_t g_material_color_generation = 0U;
uint64_t g_material_skin_rgb_skips = 0U;

bool Begin_Material_Color_Pass(int vertex_count)
{
	if ((g_render_work_cache_mode & 2U) == 0U) return false;
	// Scratch never grows with scene residency and never survives as cached
	// values across a pass, mesh, frame, skin deformation or load boundary.
	// Large meshes use direct-mapped entries rather than losing reuse entirely.
	// Vertex/material keys make collisions evictions, never stale color hits.
	if (vertex_count <= 0) {
		++g_statistics.material_color_cache_fallback_passes;
		return false;
	}
	const int entry_count = vertex_count < 8192 ? vertex_count : 8192;
	if (entry_count > g_material_color_capacity) {
		CachedMaterialVertexColor *replacement =
			new (std::nothrow) CachedMaterialVertexColor[entry_count];
		if (replacement == NULL) {
			++g_statistics.material_color_cache_fallback_passes;
			return false;
		}
		for (int index = 0; index < entry_count; ++index) {
			replacement[index].generation = 0U;
		}
		delete[] g_material_color_scratch;
		g_material_color_scratch = replacement;
		g_material_color_capacity = entry_count;
		g_statistics.material_color_cache_bytes =
			static_cast<uint64_t>(entry_count) * sizeof(CachedMaterialVertexColor);
	}
	// Starting a pass is O(1), not a sweep of every possible vertex slot.
	// Zero is reserved for unused entries; wrap clears all allocated entries
	// before reusing generation one, including slots outside this smaller mesh.
	++g_material_color_generation;
	if (g_material_color_generation == 0U) {
		for (int index = 0; index < g_material_color_capacity; ++index) {
			g_material_color_scratch[index].generation = 0U;
		}
		g_material_color_generation = 1U;
	}
	return true;
}

MaterialVertexColor Evaluate_Original_Material_Vertex_Color(
	VertexMaterialClass *material, const unsigned *color1,
	const unsigned *color2, unsigned vertex_index, const Vector3 *normals,
	const Matrix3D &world_transform, const RenderInfoClass &render_info,
	const MaterialLightDirections *light_directions)
{
	++g_statistics.material_color_evaluations;
	Vector3 material_diffuse(1.0f, 1.0f, 1.0f);
	Vector3 material_ambient(1.0f, 1.0f, 1.0f);
	Vector3 material_emissive(0.0f, 0.0f, 0.0f);
	float material_alpha = 1.0f;
	bool lighting = false;
	VertexMaterialClass::ColorSourceType diffuse_source = VertexMaterialClass::MATERIAL;
	VertexMaterialClass::ColorSourceType ambient_source = VertexMaterialClass::MATERIAL;
	VertexMaterialClass::ColorSourceType emissive_source = VertexMaterialClass::MATERIAL;
	if (material != NULL) {
		material->Get_Diffuse(&material_diffuse);
		material->Get_Ambient(&material_ambient);
		material->Get_Emissive(&material_emissive);
		material_alpha = material->Get_Opacity();
		lighting = material->Get_Lighting();
		diffuse_source = material->Get_Diffuse_Color_Source();
		ambient_source = material->Get_Ambient_Color_Source();
		emissive_source = material->Get_Emissive_Color_Source();
	}
	const SourceColor diffuse = Select_Material_Color_Source(diffuse_source,
		material_diffuse, material_alpha, color1, color2, vertex_index);
	const SourceColor ambient = Select_Material_Color_Source(ambient_source,
		material_ambient, material_alpha, color1, color2, vertex_index);
	const SourceColor emissive = Select_Material_Color_Source(emissive_source,
		material_emissive, material_alpha, color1, color2, vertex_index);

	MaterialVertexColor result = {
		diffuse.color, ambient.color, emissive.color, diffuse.color,
		diffuse.alpha, lighting, 0U
	};
	if (!lighting) {
		result.final_color = Clamp_Color(diffuse.color);
		return result;
	}

	Vector3 ambient_light = Decode_DX8_ARGB_Color(g_dx8_ambient_color);
	const LightEnvironmentClass *light_environment = render_info.light_environment;
	if (light_environment != NULL) {
		ambient_light = light_environment->Get_Equivalent_Ambient();
	}
	Vector3 lit_color =
		Multiply_Color(ambient.color, ambient_light) + emissive.color;
	if (light_environment != NULL && normals != NULL) {
		const Vector3 normal = Compute_World_Space_Normal(world_transform,
			normals[vertex_index]);
		const int light_count = light_environment->Get_Light_Count();
		for (int light_index = 0; light_index < light_count && light_index < 4;
			++light_index) {
			const Vector3 light_direction = light_directions != NULL ?
				light_directions->normalized[light_index] : Normalize_Or_Default(
					light_environment->Get_Light_Direction(light_index),
					Vector3(0.0f, 0.0f, 1.0f));
			if (light_directions == NULL) ++g_statistics.material_light_normalizations;
			const float dot = Vector3::Dot_Product(normal, light_direction);
			if (dot > 0.0f) {
				lit_color += Multiply_Color(diffuse.color,
					Scale_Color(light_environment->Get_Light_Diffuse(light_index),
						dot));
			}
		}
		result.light_count = static_cast<unsigned>(light_count > 4 ? 4 : light_count);
	}
	result.final_color = Clamp_Color(lit_color);
	return result;
}

float Evaluate_Original_Diffuse_Alpha(VertexMaterialClass *material,
	const unsigned *color1, const unsigned *color2, unsigned vertex_index)
{
	if (material == NULL) return 1.0f;
	const VertexMaterialClass::ColorSourceType source =
		material->Get_Diffuse_Color_Source();
	const unsigned *colors = source == VertexMaterialClass::COLOR1 ? color1 :
		(source == VertexMaterialClass::COLOR2 ? color2 : NULL);
	return colors != NULL ? Decode_DX8_ARGB_Alpha(colors[vertex_index]) :
		material->Get_Opacity();
}

MaterialVertexColor Evaluate_Material_Vertex_Color(bool cache_material_colors,
	VertexMaterialClass *material, const unsigned *color1, const unsigned *color2,
	unsigned vertex_index, const Vector3 *normals, const Matrix3D &world_transform,
	const RenderInfoClass &render_info, const MaterialLightDirections &light_directions,
	bool discarded_skin_rgb = false)
{
	// The existing textured-skin path overwrites RGB with white before glColor.
	// Retain the original diffuse alpha source, including absent-array fallback.
	// First-color diagnostics request the complete evaluator at the call site.
	if (discarded_skin_rgb && (g_render_work_cache_mode & 2U) != 0U) {
		MaterialVertexColor submitted = {};
		submitted.final_color = Vector3(1.0f, 1.0f, 1.0f);
		submitted.alpha = Evaluate_Original_Diffuse_Alpha(material, color1,
			color2, vertex_index);
		++g_material_skin_rgb_skips;
		return submitted;
	}
	MaterialVertexColor vertex_color;
	CachedMaterialVertexColor *cached_color = cache_material_colors ?
		&g_material_color_scratch[vertex_index & 8191U] : NULL;
	if (cached_color != NULL &&
		cached_color->generation == g_material_color_generation &&
		cached_color->vertex_index == vertex_index &&
		cached_color->material == material) {
		vertex_color = cached_color->color;
		++g_statistics.material_color_cache_hits;
	} else {
		vertex_color = Evaluate_Original_Material_Vertex_Color(material,
			color1, color2, vertex_index, normals,
			world_transform, render_info,
			cache_material_colors ? &light_directions : NULL);
		if (cached_color != NULL) {
			cached_color->color = vertex_color;
			cached_color->material = material;
			cached_color->vertex_index = vertex_index;
			cached_color->generation = g_material_color_generation;
		}
	}
	return vertex_color;
}

void Log_System_Memory(const char *stage)
{
	SceKernelFreeMemorySizeInfo memory = {};
	memory.size = sizeof(memory);
	const int result = sceKernelGetFreeMemorySize(&memory);
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"free memory %s: rc=%08X user=%d cdram=%d phycont=%d",
		stage, static_cast<unsigned>(result), memory.size_user,
		memory.size_cdram, memory.size_phycont);
}

void Log_Shader_Module(const char *label, const char *path)
{
	SceIoStat status = {};
	const int result = sceIoGetstat(path, &status);
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"libshacccg %s: path=%s stat_rc=%08X size=%llu",
		label, path, static_cast<unsigned>(result),
		result >= 0 ? static_cast<unsigned long long>(status.st_size) : 0ULL);
}

const char *Shark_Level_Name(shark_log_level level)
{
	switch (level) {
	case SHARK_LOG_INFO:
		return "INFO";
	case SHARK_LOG_WARNING:
		return "WARNING";
	case SHARK_LOG_ERROR:
		return "ERROR";
	default:
		return "UNKNOWN";
	}
}

void Shark_Log_Callback(const char *message, shark_log_level level, int line)
{
	Vita_Append_A22_Runtime_Breadcrumb("shader-compiler",
		"level=%s(%d) line=%d message=%s", Shark_Level_Name(level),
		static_cast<int>(level), line, message != NULL ? message : "(null)");
}

GLenum Log_GL_Result(const char *operation)
{
	const GLenum error = glGetError();
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"%s return: glGetError=%08X", operation, static_cast<unsigned>(error));
	return error;
}

uint64_t VitaGL_Phycont_Mem_Total()
{
#if defined(RENEGADE_VITAGL_HAS_PHYCONT_MEM) && RENEGADE_VITAGL_HAS_PHYCONT_MEM
	return vglMemTotal(RENEGADE_VITAGL_PHYCONT_MEM);
#else
	return 0;
#endif
}

uint64_t VitaGL_Phycont_Mem_Free()
{
#if defined(RENEGADE_VITAGL_HAS_PHYCONT_MEM) && RENEGADE_VITAGL_HAS_PHYCONT_MEM
	return vglMemFree(RENEGADE_VITAGL_PHYCONT_MEM);
#else
	return 0;
#endif
}

void Log_VitaGL_Memory()
{
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"vitaGL pools bytes total/free: RAM=%llu/%llu VRAM=%llu/%llu SLOW=%llu/%llu BUDGET=%llu/%llu ALL=%llu/%llu",
		static_cast<unsigned long long>(vglMemTotal(VGL_MEM_RAM)),
		static_cast<unsigned long long>(vglMemFree(VGL_MEM_RAM)),
		static_cast<unsigned long long>(vglMemTotal(VGL_MEM_VRAM)),
		static_cast<unsigned long long>(vglMemFree(VGL_MEM_VRAM)),
		static_cast<unsigned long long>(VitaGL_Phycont_Mem_Total()),
		static_cast<unsigned long long>(VitaGL_Phycont_Mem_Free()),
		static_cast<unsigned long long>(vglMemTotal(VGL_MEM_BUDGET)),
		static_cast<unsigned long long>(vglMemFree(VGL_MEM_BUDGET)),
		static_cast<unsigned long long>(vglMemTotal(VGL_MEM_ALL)),
		static_cast<unsigned long long>(vglMemFree(VGL_MEM_ALL)));
}
#endif

bool Reactivate_Native_Backend_State()
{
#if defined(__vita__)
	Vita_Append_A22_Runtime_Breadcrumb("renderer-lifecycle",
		"logical session reactivation entry: native_calls=%u prior_sessions=%u",
		g_lifecycle.native_initialization_calls,
		g_lifecycle.logical_sessions);
	(void)glGetError();
	glViewport(0, 0, static_cast<GLsizei>(DISPLAY_WIDTH),
		static_cast<GLsizei>(DISPLAY_HEIGHT));
	glDepthRangef(0.0f, 1.0f);
	glEnable(GL_DEPTH_TEST);
	glDepthFunc(GL_LEQUAL);
	glDisable(GL_CULL_FACE);
	glDisable(GL_FOG);
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	const GLenum error = glGetError();
	Vita_Append_A22_Runtime_Breadcrumb("renderer-lifecycle",
		"logical session reactivation return: glGetError=%08X native_calls=%u",
		static_cast<unsigned>(error),
		g_lifecycle.native_initialization_calls);
	if (error != GL_NO_ERROR) {
		return false;
	}
	Invalidate_Native_State_Cache();
	g_logged_first_frame = false;
	g_logged_first_present = false;
	g_logged_first_mesh = false;
#endif
	return true;
}

uint32_t Mix_Checksum(uint32_t value, uint32_t word)
{
	return (value ^ word) * 16777619U;
}

bool Is_Zero_Matrix(const float *matrix)
{
	if (matrix == NULL) {
		return true;
	}
	for (unsigned index = 0; index < 16; ++index) {
		if (matrix[index] != 0.0f) {
			return false;
		}
	}
	return true;
}

uint32_t Float_Bits(float value)
{
	uint32_t bits = 0;
	memcpy(&bits, &value, sizeof(bits));
	return bits;
}

void Log_Indexed_Rejection(const char *reason, uint32_t vertex_format)
{
	if (g_logged_first_indexed_rejection) {
		return;
	}
#if defined(__vita__)
	Vita_Append_A22_Runtime_Breadcrumb("indexed-submit",
		"first rejected original DX8Wrapper draw: reason=%s fvf=%08X",
		reason != NULL ? reason : "(unknown)", vertex_format);
#else
	fprintf(stderr,
		"A3.0 first rejected original DX8Wrapper draw: reason=%s fvf=%08X\n",
		reason != NULL ? reason : "(unknown)", vertex_format);
#endif
	g_logged_first_indexed_rejection = true;
}

} // namespace

bool Use_Direct_Text_Atlas_Upload()
{
#if defined(__vita__)
	if ((g_render_work_cache_mode & 4U) != 0U) {
		++g_statistics.direct_text_atlas_requests;
		return true;
	}
#endif
	return false;
}

bool Use_Native_DDS_Upload()
{
#if defined(__vita__)
	return (g_render_work_cache_mode & 4U) != 0U;
#else
	return false;
#endif
}

void Invalidate_Texture_State_Cache()
{
#if defined(__vita__)
	memset(g_texture_stage_cache, 0, sizeof(g_texture_stage_cache));
	// Uploads, external GL mutation and deletion may change a native object's
	// parameters or recycle its name. Never retain object memos across them.
	Invalidate_Texture_Object_Samplers();
	Invalidate_Original_Shader_State_Cache();
#endif
}

bool Build_Indexed_Transform_Matrices(const float *world_transform,
	const float *view_transform, const float *projection_transform,
	IndexedTransformMatrices &matrices)
{
	if (Is_Zero_Matrix(world_transform) || Is_Zero_Matrix(view_transform) ||
		Is_Zero_Matrix(projection_transform)) {
		return false;
	}

	// DX8Wrapper stores the transposes of WWMath's column-vector matrices.
	// For an original p * Dworld * Dview operation, glLoadMatrixf must receive
	// Dworld * Dview: vitaGL transposes that row-major memory internally and
	// consequently evaluates V * W * p in its fixed-function vertex shader.
	for (unsigned row = 0; row < 4U; ++row) {
		for (unsigned column = 0; column < 4U; ++column) {
			float value = 0.0f;
			for (unsigned inner = 0; inner < 4U; ++inner) {
				value += world_transform[row * 4U + inner] *
					view_transform[inner * 4U + column];
			}
			matrices.modelview[row * 4U + column] = value;
		}
	}

	memcpy(matrices.projection, projection_transform,
		sizeof(matrices.projection));
	for (unsigned row = 0; row < 4U; ++row) {
		// Direct3D clip depth is 0..W; OpenGL/vitaGL clip depth is -W..W.
		// In row-vector memory this is Dprojection * transpose(C), where
		// C maps (x,y,z,w) to (x,y,2z-w,w).
		matrices.projection[row * 4U + 2U] =
			2.0f * projection_transform[row * 4U + 2U] -
			projection_transform[row * 4U + 3U];
	}
	return true;
}

bool Map_Native_Pixel_To_Logical(float x, float y, float logical_width,
	float logical_height, float &logical_x, float &logical_y)
{
	const NativePresentationRect &rect = g_native_presentation_rect;
	if (!(logical_width > 0.0f) || !(logical_height > 0.0f) ||
		rect.width == 0U || rect.height == 0U ||
		!(x >= rect.x && y >= rect.y &&
		  x < rect.x + rect.width && y < rect.y + rect.height)) return false;
	logical_x = (x - rect.x) * logical_width / rect.width;
	logical_y = (y - rect.y) * logical_height / rect.height;
	return true;
}

bool Build_Native_Viewport(uint32_t d3d_x, uint32_t d3d_y,
	uint32_t width, uint32_t height, float min_depth, float max_depth,
	NativeViewport &viewport)
{
	return Build_Native_Viewport(d3d_x, d3d_y, width, height, min_depth,
		max_depth, DISPLAY_WIDTH, DISPLAY_HEIGHT, viewport);
}

bool Build_Native_Viewport(uint32_t d3d_x, uint32_t d3d_y,
	uint32_t width, uint32_t height, float min_depth, float max_depth,
	uint32_t logical_width, uint32_t logical_height, NativeViewport &viewport)
{
	if (logical_width == 0U || logical_height == 0U || width == 0U ||
		height == 0U || d3d_x > logical_width || d3d_y > logical_height ||
		width > logical_width - d3d_x || height > logical_height - d3d_y ||
		min_depth < 0.0f || max_depth > 1.0f || min_depth > max_depth) {
		return false;
	}

	const uint64_t left =
		g_native_presentation_rect.x +
		(static_cast<uint64_t>(d3d_x) *
			g_native_presentation_rect.width) / logical_width;
	const uint64_t right =
		g_native_presentation_rect.x +
		((static_cast<uint64_t>(d3d_x) + width) *
			g_native_presentation_rect.width +
			logical_width - 1U) / logical_width;
	const uint64_t top =
		g_native_presentation_rect.y +
		(static_cast<uint64_t>(d3d_y) *
			g_native_presentation_rect.height) / logical_height;
	const uint64_t bottom =
		g_native_presentation_rect.y +
		((static_cast<uint64_t>(d3d_y) + height) *
			g_native_presentation_rect.height +
			logical_height - 1U) / logical_height;
	if (right <= left || bottom <= top || right > DISPLAY_WIDTH ||
		bottom > DISPLAY_HEIGHT) {
		return false;
	}

	viewport.x = static_cast<uint32_t>(left);
	viewport.y = static_cast<uint32_t>(DISPLAY_HEIGHT - bottom);
	viewport.width = static_cast<uint32_t>(right - left);
	viewport.height = static_cast<uint32_t>(bottom - top);
	viewport.min_depth = min_depth;
	viewport.max_depth = max_depth;
	return true;
}

bool Set_Native_Presentation_Rect_Internal(uint32_t x, uint32_t y,
	uint32_t width, uint32_t height, bool log_change)
{
	if (width == 0U || height == 0U || x > DISPLAY_WIDTH ||
		y > DISPLAY_HEIGHT || width > DISPLAY_WIDTH - x ||
		height > DISPLAY_HEIGHT - y) {
		return false;
	}
	if (g_native_presentation_rect.x == x &&
		g_native_presentation_rect.y == y &&
		g_native_presentation_rect.width == width &&
		g_native_presentation_rect.height == height) {
		return true;
	}
	g_native_presentation_rect.x = x;
	g_native_presentation_rect.y = y;
	g_native_presentation_rect.width = width;
	g_native_presentation_rect.height = height;
#if defined(__vita__)
	g_current_native_viewport_known = false;
	if (log_change) {
		Vita_Append_A22_Runtime_Breadcrumb("camera-state",
			"native presentation rect: top_left=%u,%u size=%ux%u display=%ux%u",
			x, y, width, height, DISPLAY_WIDTH, DISPLAY_HEIGHT);
	}
#endif
	return true;
}

bool Set_Native_Presentation_Rect(uint32_t x, uint32_t y,
	uint32_t width, uint32_t height)
{
	return Set_Native_Presentation_Rect_Internal(x, y, width, height, true);
}

bool Set_Native_Presentation_Rect_Quiet(uint32_t x, uint32_t y,
	uint32_t width, uint32_t height)
{
	return Set_Native_Presentation_Rect_Internal(x, y, width, height, false);
}

void Reset_Native_Presentation_Rect()
{
	(void)Set_Native_Presentation_Rect(0U, 0U, DISPLAY_WIDTH, DISPLAY_HEIGHT);
}

void Reset_Native_Presentation_Rect_Quiet()
{
	(void)Set_Native_Presentation_Rect_Quiet(0U, 0U, DISPLAY_WIDTH,
		DISPLAY_HEIGHT);
}

bool Apply_Viewport(uint32_t d3d_x, uint32_t d3d_y, uint32_t width,
	uint32_t height, float min_depth, float max_depth)
{
	return Apply_Viewport(d3d_x, d3d_y, width, height, min_depth, max_depth,
		DISPLAY_WIDTH, DISPLAY_HEIGHT);
}

bool Apply_Viewport(uint32_t d3d_x, uint32_t d3d_y, uint32_t width,
	uint32_t height, float min_depth, float max_depth,
	uint32_t logical_width, uint32_t logical_height)
{
	NativeViewport viewport = {};
	if (!Build_Native_Viewport(d3d_x, d3d_y, width, height, min_depth,
		max_depth, logical_width, logical_height, viewport)) {
		return false;
	}

#if defined(__vita__)
	if (!g_statistics.initialized) {
		return false;
	}
	if (g_current_native_viewport_known &&
		g_current_native_viewport.x == viewport.x &&
		g_current_native_viewport.y == viewport.y &&
		g_current_native_viewport.width == viewport.width &&
		g_current_native_viewport.height == viewport.height &&
		g_current_native_viewport.min_depth == viewport.min_depth &&
		g_current_native_viewport.max_depth == viewport.max_depth) {
		if (!g_logged_first_viewport_state_skip) {
			Vita_Append_A22_Runtime_Breadcrumb("camera-state",
				"first cached original CameraClass viewport skip: d3d=%u,%u %ux%u native=%u,%u %ux%u",
				d3d_x, d3d_y, width, height, viewport.x, viewport.y,
				viewport.width, viewport.height);
			g_logged_first_viewport_state_skip = true;
		}
		return true;
	}
	// Consume an older error before issuing the two camera-owned operations so
	// the return value describes this viewport transition, not unrelated state.
	const GLenum prior_error = glGetError();
	glViewport(static_cast<GLint>(viewport.x),
		static_cast<GLint>(viewport.y), static_cast<GLsizei>(viewport.width),
		static_cast<GLsizei>(viewport.height));
	glDepthRangef(viewport.min_depth, viewport.max_depth);
	const GLenum operation_error = glGetError();
	++g_statistics.state_changes;
	if (operation_error != GL_NO_ERROR) {
		++g_statistics.backend_errors;
	} else {
		g_current_native_viewport = viewport;
		g_current_native_viewport_known = true;
	}
	static bool logged_first_camera_viewport = false;
	if (!logged_first_camera_viewport) {
		Vita_Append_A22_Runtime_Breadcrumb("camera-state",
			"original CameraClass viewport: d3d=%u,%u %ux%u native=%u,%u %ux%u presentation=%u,%u %ux%u depth=%.6f..%.6f prior_gl=%08X gl=%08X",
			d3d_x, d3d_y, width, height, viewport.x, viewport.y,
			viewport.width, viewport.height,
			g_native_presentation_rect.x, g_native_presentation_rect.y,
			g_native_presentation_rect.width,
			g_native_presentation_rect.height, viewport.min_depth,
			viewport.max_depth, static_cast<unsigned>(prior_error),
			static_cast<unsigned>(operation_error));
		logged_first_camera_viewport = true;
	}
	return operation_error == GL_NO_ERROR;
#else
	return true;
#endif
}

#if defined(__vita__)
extern "C" int __real_shark_init(const char *path);

extern "C" int __wrap_shark_init(const char *path)
{
	Vita_Append_A22_Runtime_Breadcrumb("shader-compiler",
		"shark_init entry: call=%u path=%s", g_shader_init_calls + 1,
		path != NULL ? path : "(default ur0:/data/libshacccg.suprx)");
	const int result = __real_shark_init(path);
	++g_shader_init_calls;
	g_shader_init_last_result = result;
	if (result >= 0) {
		g_shader_compiler_available = true;
	}
	Vita_Append_A22_Runtime_Breadcrumb("shader-compiler",
		"shark_init return: call=%u rc=%08X available=%d", g_shader_init_calls,
		static_cast<unsigned>(result), g_shader_compiler_available ? 1 : 0);
	return result;
}
#endif

void Apply_Indexed_Shader_State(const ShaderClass &shader,
	bool stage0_texture, bool stage1_texture)
{
	++g_statistics.indexed_state_applications;
#if defined(__vita__)
	Apply_Original_Shader_State(shader);
	/* The original dynamic DX8 path normally reaches ShaderClass::Apply before
	** DrawIndexedPrimitive.  Native indexed submission bypasses that desktop
	** device call, so translate its per-stage contract here instead of allowing
	** a Render2D glyph atlas to inherit a preceding mesh's combiner.  In
	** particular, Render2DSentence requires texture alpha modulated by its
	** vertex color for the procedural A4R4G4B4 atlas to remain visible. */
	Apply_Original_Texture_Stage_State(shader, stage0_texture, stage1_texture);
#else
	(void)shader;
	(void)stage0_texture;
	(void)stage1_texture;
#endif
}

bool Initialize()
{
	if (g_statistics.initialized) {
		return true;
	}
	if (g_lifecycle.native_initialization_attempted) {
		if (!g_lifecycle.native_backend_ready) {
#if defined(__vita__)
			Vita_Append_A22_Runtime_Breadcrumb("renderer-lifecycle",
				"logical session rejected: first native initialization failed; vglInit retry prohibited");
#endif
			return false;
		}
		if (!Reactivate_Native_Backend_State()) {
			return false;
		}
		g_statistics.initialized = true;
		g_lifecycle.logical_session_active = true;
		++g_lifecycle.logical_sessions;
#if defined(__vita__)
		Vita_Append_A22_Runtime_Breadcrumb("renderer-lifecycle",
			"logical session reactivated: session=%u native_calls=%u",
			g_lifecycle.logical_sessions,
			g_lifecycle.native_initialization_calls);
#endif
		return true;
	}

	g_lifecycle.native_initialization_attempted = true;
	++g_lifecycle.native_initialization_calls;
#if defined(__vita__)
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"entry: backend=vitaGL commit=6e7fe40 API=vglInit native_call=%u",
		g_lifecycle.native_initialization_calls);
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"display request: 960x544 buffers=3 color=SCE_GXM_COLOR_FORMAT_A8B8G8R8 depth=SCE_GXM_DEPTH_STENCIL_FORMAT_DF32M_S8 msaa=SCE_GXM_MULTISAMPLE_4X");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"memory policy: legacy_pool=4194304 circular_pool=33554432 ram_reserve=16777216 cdram_reserve=0 phycont_reserve=0 cdlg_pool=0");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"GXM defaults: parameter=16777216 vdm=131072 vertex=2097152 fragment=524288 fragment_usse=16384 shader_patcher=1048576/1048576/1048576 vertex_attrib=262144/65536");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"shader compiler config: vitaShaRK default=ur0:/data/libshacccg.suprx fallback=ur0:data/external/libshacccg.suprx opt=FAST fastmath=1 fastprecision=0 fastint=1");
	Log_System_Memory("before vglInit");
	Log_Shader_Module("default", "ur0:/data/libshacccg.suprx");
	Log_Shader_Module("fallback", "ur0:data/external/libshacccg.suprx");
	shark_install_log_cb(Shark_Log_Callback);
	shark_set_warnings_level(SHARK_WARN_HIGH);
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"vitaShaRK diagnostic callback installation: complete");
	const char *shader_cache_path = "ux0:data/renegade/cache/vitagl-shader-cache";
	(void)sceIoMkdir(shader_cache_path, 0777);
	vglSetShaderCachePath(shader_cache_path);
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"vitaGL shader cache path: %s", shader_cache_path);
	g_shader_compiler_available = false;
	g_shader_init_calls = 0;
	g_shader_init_last_result = -1;
	Read_Render_Work_Cache_Mode();
	Invalidate_Native_State_Cache();

	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "vglInit entry");
#if RENEGADE_VITA_M00_DEMO
	const GLboolean resolution_fallback = vglInit(4 * 1024 * 1024);
#else
	const SceGxmMultisampleMode campaign_msaa = RENEGADE_VITA_CAMPAIGN_MSAA_4X
		? SCE_GXM_MULTISAMPLE_4X : SCE_GXM_MULTISAMPLE_NONE;
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "campaign framebuffer msaa=%dx",
		RENEGADE_VITA_CAMPAIGN_MSAA_4X ? 4 : 0);
	const GLboolean resolution_fallback = vglInitExtended(
		4 * 1024 * 1024, 960, 544, 0x1000000, campaign_msaa);
#endif
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"vglInit return: raw=%d semantic=resolution_fallback call_completed=1",
		static_cast<int>(resolution_fallback));
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"internal stages reached before vglInit return: GXM/context/framebuffer/depth/shader-patcher/clear-program/index-buffer/texture0 attempted; installed NO_DEBUG archive does not expose their individual return codes");
	Log_System_Memory("after vglInit");
	Log_VitaGL_Memory();
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"shader compiler init summary: calls=%u last_rc=%08X available=%d",
		g_shader_init_calls, static_cast<unsigned>(g_shader_init_last_result),
		g_shader_compiler_available ? 1 : 0);

	GLint initial_viewport[4] = {};
	glGetIntegerv(GL_VIEWPORT, initial_viewport);
	const GLenum query_error = Log_GL_Result("viewport query");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"framebuffer/display query: viewport=%d,%d %dx%d expected=960x544",
		initial_viewport[0], initial_viewport[1], initial_viewport[2], initial_viewport[3]);

	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "glViewport entry");
	glViewport(0, 0, 960, 544);
	const GLenum viewport_error = Log_GL_Result("glViewport");
	if (viewport_error == GL_NO_ERROR) {
		g_current_native_viewport.x = 0U;
		g_current_native_viewport.y = 0U;
		g_current_native_viewport.width = DISPLAY_WIDTH;
		g_current_native_viewport.height = DISPLAY_HEIGHT;
		g_current_native_viewport.min_depth = 0.0f;
		g_current_native_viewport.max_depth = 1.0f;
		g_current_native_viewport_known = true;
	}
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "depth buffer state entry");
	glEnable(GL_DEPTH_TEST);
	glDepthFunc(GL_LEQUAL);
	const GLenum depth_error = Log_GL_Result("depth enable/function");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "raster state-cache entry");
	glDisable(GL_CULL_FACE);
	glDisable(GL_FOG);
	const GLenum raster_error = Log_GL_Result("cull disable/state cache");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "projection state entry");
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	const GLenum projection_error = Log_GL_Result("projection identity");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "modelview state entry");
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	const GLenum modelview_error = Log_GL_Result("modelview identity");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"vertex/index/texture backend state: vglInit path returned after immediate-pool/default-index/texture0 setup; FFP programs are lazy at first mesh");

	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"first clear entry: color=0.035,0.055,0.085,1 depth=1");
	glClearColor(0.035f, 0.055f, 0.085f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	const GLenum clear_error = Log_GL_Result("first clear/framebuffer scene reset");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"first present entry: frame_before=%u", vglGetFrameNumber());
	vglSwapBuffers(GL_FALSE);
	const GLenum present_error = Log_GL_Result("first vglSwapBuffers");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"first present return: frame_after=%u splash_transition_requested=1",
		vglGetFrameNumber());

	const bool display_ready = initial_viewport[2] > 0 && initial_viewport[3] > 0;
	const bool gl_ready = query_error == GL_NO_ERROR && viewport_error == GL_NO_ERROR &&
		depth_error == GL_NO_ERROR && raster_error == GL_NO_ERROR &&
		projection_error == GL_NO_ERROR && modelview_error == GL_NO_ERROR &&
		clear_error == GL_NO_ERROR && present_error == GL_NO_ERROR;
	if (!g_shader_compiler_available || !display_ready || !gl_ready) {
		Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
			"failure return: shader_available=%d last_rc=%08X display_ready=%d gl_ready=%d",
			g_shader_compiler_available ? 1 : 0,
			static_cast<unsigned>(g_shader_init_last_result), display_ready ? 1 : 0,
			gl_ready ? 1 : 0);
		return false;
	}
	g_logged_first_frame = false;
	g_logged_first_present = false;
	g_logged_first_mesh = false;
#endif
	g_lifecycle.native_backend_ready = true;
	g_statistics.initialized = true;
	g_lifecycle.logical_session_active = true;
	++g_lifecycle.logical_sessions;
#if defined(__vita__)
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"successful renderer initialization return: initialized=1 resolution_fallback=%d native_calls=%u logical_session=%u",
		static_cast<int>(resolution_fallback),
		g_lifecycle.native_initialization_calls,
		g_lifecycle.logical_sessions);
#endif
	return true;
}

void Shutdown()
{
	// vitaGL does not expose a process-lifetime shutdown call. The application
	// owns it until clean process exit.  This ends only WW3D's logical session.
	if (g_statistics.initialized || g_lifecycle.logical_session_active) {
		++g_lifecycle.logical_shutdowns;
	}
#if defined(RENEGADE_HOST_RENDERER_LIFECYCLE_SELFTEST) && defined(__GNUC__)
	if (RenegadeVita_Release_DX8_Bound_Textures != NULL) {
		RenegadeVita_Release_DX8_Bound_Textures();
	}
#else
	RenegadeVita_Release_DX8_Bound_Textures();
#endif
	g_statistics.initialized = false;
	g_lifecycle.logical_session_active = false;
	Release_Deformed_Skin_Scratch();
#if defined(__vita__)
	delete[] g_material_color_scratch;
	g_material_color_scratch = NULL;
	g_material_color_capacity = 0;
	g_material_color_generation = 0U;
	g_statistics.material_color_cache_bytes = 0U;
	Invalidate_Native_State_Cache();
	Vita_Append_A22_Runtime_Breadcrumb("renderer-lifecycle",
		"logical shutdown: shutdowns=%u sessions=%u native_calls=%u native_ready=%d",
		g_lifecycle.logical_shutdowns, g_lifecycle.logical_sessions,
		g_lifecycle.native_initialization_calls,
		g_lifecycle.native_backend_ready ? 1 : 0);
#endif
}

void Begin_Frame(float red, float green, float blue)
{
	if (!g_statistics.initialized) {
		return;
	}
	++g_statistics.frames;
#if defined(__vita__)
	if (!g_logged_first_frame) {
		Vita_Append_A22_Runtime_Breadcrumb("render-frame",
			"WW3D first Begin_Frame entry: clear=(%.3f,%.3f,%.3f)", red, green, blue);
	}
	glClearColor(red, green, blue, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	if (!g_logged_first_frame) {
		const GLenum error = glGetError();
		Vita_Append_A22_Runtime_Breadcrumb("render-frame",
			"WW3D first Begin_Frame return: glGetError=%08X frame=%u",
			static_cast<unsigned>(error), vglGetFrameNumber());
		g_logged_first_frame = true;
	}
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	g_statistics.state_changes += 5U;
#else
	(void)red;
	(void)green;
	(void)blue;
#endif
}

void End_Frame(bool present)
{
#if defined(__vita__)
	if (g_statistics.initialized && present) {
		if (!g_logged_first_present) {
			Vita_Append_A22_Runtime_Breadcrumb("render-frame",
				"WW3D first End_Frame present entry: frame_before=%u", vglGetFrameNumber());
		}
		vglSwapBuffers(RenegadeVitaTextEntry::Active() ? GL_TRUE : GL_FALSE);
		const GLenum present_error = glGetError();
		if (present_error != GL_NO_ERROR) {
			++g_statistics.backend_errors;
		}
		if (!g_logged_first_present) {
			Vita_Append_A22_Runtime_Breadcrumb("render-frame",
				"WW3D first End_Frame present return: frame_after=%u glGetError=%08X",
				vglGetFrameNumber(), static_cast<unsigned>(present_error));
			g_logged_first_present = true;
		}
		if (g_statistics.frames % 120U == 0U) {
			Vita_Append_A22_Runtime_Breadcrumb("render-work-cache",
				"version=1 mode=%u frame=%u sampler_writes=%llu material_evaluations=%llu material_hits=%llu fallback_passes=%llu scratch_bytes=%llu object_table_bytes=%u direct_atlas_requests=%llu light_normalizations=%llu mesh_corners=%llu mesh_unique=%llu mesh_batches=%llu mesh_scratch=%u skin_rgb_skips=%llu",
				g_render_work_cache_mode, g_statistics.frames,
				static_cast<unsigned long long>(g_statistics.texture_sampler_parameter_writes),
				static_cast<unsigned long long>(g_statistics.material_color_evaluations),
				static_cast<unsigned long long>(g_statistics.material_color_cache_hits),
				static_cast<unsigned long long>(g_statistics.material_color_cache_fallback_passes),
				static_cast<unsigned long long>(g_statistics.material_color_cache_bytes),
				static_cast<unsigned>(sizeof(g_texture_object_samplers)),
				static_cast<unsigned long long>(g_statistics.direct_text_atlas_requests),
				static_cast<unsigned long long>(g_statistics.material_light_normalizations),
				static_cast<unsigned long long>(g_mesh_expanded_corners),
				static_cast<unsigned long long>(g_mesh_unique_vertices),
				static_cast<unsigned long long>(g_mesh_indexed_batches),
				static_cast<unsigned>(sizeof(g_indexed_mesh_batch)),
				static_cast<unsigned long long>(g_material_skin_rgb_skips));
		}
	}
#else
	(void)present;
#endif
}

void Record_Texture_Request()
{
	++g_statistics.texture_requests;
}

void Record_Texture_Decode()
{
	++g_statistics.texture_decodes;
}

void Record_Texture_DDS_Load()
{
	++g_statistics.texture_dds_loads;
}

void Record_Texture_Targa_Load()
{
	++g_statistics.texture_tga_loads;
}

void Record_Texture_Missing()
{
	++g_statistics.texture_missing;
}

void Record_Texture_Source_Missing()
{
	++g_statistics.texture_missing;
	++g_statistics.texture_source_missing;
}

void Record_Texture_Invalid_Data()
{
	++g_statistics.texture_missing;
	++g_statistics.texture_invalid_data;
}

void Record_Texture_Unsupported_Format()
{
	++g_statistics.texture_missing;
	++g_statistics.texture_unsupported_formats;
}

void Record_Texture_Decode_Failure()
{
	++g_statistics.texture_missing;
	++g_statistics.texture_decode_failures;
}

void Record_Texture_Upload_Failure()
{
	++g_statistics.texture_missing;
	++g_statistics.texture_upload_failures;
}

void Record_Texture_Checkerboard_Fallback()
{
	++g_statistics.texture_checkerboard_fallbacks;
}

void Record_Texture_Checkerboard_Bind()
{
	++g_statistics.texture_checkerboard_binds;
}

void Record_Texture_Upload(uint64_t resident_bytes)
{
	++g_statistics.texture_uploads;
	++g_statistics.texture_resident;
	g_statistics.texture_bytes_resident += resident_bytes;
}

void Record_Texture_Release(uint64_t resident_bytes)
{
	if (g_statistics.texture_resident != 0U) --g_statistics.texture_resident;
	if (resident_bytes <= g_statistics.texture_bytes_resident) {
		g_statistics.texture_bytes_resident -= resident_bytes;
	} else {
		g_statistics.texture_bytes_resident = 0U;
	}
}

bool Bind_Texture(uint32_t native_texture, bool valid)
{
	return Bind_Texture_Stage(0U, native_texture, valid);
}

bool Bind_Texture_Stage(uint32_t stage, uint32_t native_texture, bool valid)
{
	if (stage >= MeshMatDescClass::MAX_TEX_STAGES) {
		Record_Texture_Unsupported_Stage(stage);
		return false;
	}
	if (!valid || native_texture == 0U) {
		if (valid && native_texture == 0U) {
			++g_statistics.texture_invalid_binds;
		}
#if defined(__vita__)
		Set_Texture_Stage_Enabled(stage, false);
#endif
		return false;
	}
#if defined(__vita__)
	Set_Texture_Stage_Enabled(stage, true);
	NativeTextureStageCache &cache = g_texture_stage_cache[stage];
	if (cache.texture_known && cache.texture == native_texture) {
		++g_statistics.texture_bind_skips;
		return true;
	}
	glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage));
	glBindTexture(GL_TEXTURE_2D, native_texture);
	glActiveTexture(GL_TEXTURE0);
	cache.texture_known = true;
	cache.texture = native_texture;
#endif
	++g_statistics.texture_binds;
	return true;
}

void Disable_Texture_Stage(uint32_t stage)
{
#if defined(__vita__)
	Set_Texture_Stage_Enabled(stage, false);
#else
	(void)stage;
#endif
}

bool Configure_Texture_Sampler(uint32_t native_texture, bool valid,
	uint32_t address_u, uint32_t address_v, uint32_t min_filter,
	uint32_t mag_filter, uint32_t mip_filter)
{
	return Configure_Texture_Sampler_Stage(0U, native_texture, valid,
		address_u, address_v, min_filter, mag_filter, mip_filter);
}

bool Configure_Texture_Sampler_Stage(uint32_t stage, uint32_t native_texture,
	bool valid, uint32_t address_u, uint32_t address_v, uint32_t min_filter,
	uint32_t mag_filter, uint32_t mip_filter)
{
	if (stage >= MeshMatDescClass::MAX_TEX_STAGES) {
		Record_Texture_Unsupported_Stage(stage);
		return false;
	}
	if (!valid || native_texture == 0U) {
		if (valid && native_texture == 0U) {
			++g_statistics.texture_invalid_binds;
		}
		return false;
	}
#if defined(__vita__)
	// D3D8's TextureClass owns the state choices.  This narrow translation only
	// maps its established address/filter contract to VitaGL; it does not add a
	// Vita sensitivity, cache, or material policy of its own.
	NativeTextureStageCache &cache = g_texture_stage_cache[stage];
	const bool sampler_matches = cache.sampler_known && cache.sampler_texture == native_texture &&
		cache.address_u == address_u && cache.address_v == address_v &&
		cache.min_filter == min_filter && cache.mag_filter == mag_filter &&
		cache.mip_filter == mip_filter;
	const bool binding_matches = cache.texture_known && cache.texture == native_texture;
	if (sampler_matches && binding_matches) {
		++g_statistics.texture_sampler_skips;
		return true;
	}
	const GLenum wrap_u = address_u == 3U ? GL_CLAMP_TO_EDGE : GL_REPEAT;
	const GLenum wrap_v = address_v == 3U ? GL_CLAMP_TO_EDGE : GL_REPEAT;
	const bool point_min = min_filter == 1U;
	GLenum native_min = point_min ? GL_NEAREST : GL_LINEAR;
	if (mip_filter == 1U) {
		native_min = point_min ? GL_NEAREST_MIPMAP_NEAREST : GL_LINEAR_MIPMAP_NEAREST;
	} else if (mip_filter == 2U || mip_filter == 3U) {
		native_min = point_min ? GL_NEAREST_MIPMAP_LINEAR : GL_LINEAR_MIPMAP_LINEAR;
	}
	const GLenum native_mag = mag_filter == 1U ? GL_NEAREST : GL_LINEAR;
	NativeTextureObjectSampler &object_sampler = g_texture_object_samplers[
		(native_texture * 2654435761U) & (TEXTURE_OBJECT_SAMPLER_SLOTS - 1U)];
	const bool object_known = (g_render_work_cache_mode & 1U) != 0U &&
		object_sampler.generation == g_texture_object_sampler_generation &&
		object_sampler.texture == native_texture;
	const bool write_u = !object_known || object_sampler.wrap_u != wrap_u;
	const bool write_v = !object_known || object_sampler.wrap_v != wrap_v;
	const bool write_min = !object_known || object_sampler.min_filter != native_min;
	const bool write_mag = !object_known || object_sampler.mag_filter != native_mag;
	const bool write_sampler = write_u || write_v || write_min || write_mag;
	if (!write_sampler && binding_matches) {
		++g_statistics.texture_sampler_skips;
		return true;
	}
	glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage));
	if (!binding_matches) {
		glBindTexture(GL_TEXTURE_2D, native_texture);
		++g_statistics.texture_binds;
	} else {
		++g_statistics.texture_bind_skips;
	}
	// glTexParameteri mutates the texture object, not the active stage.
	// Another stage's memo for this object must not survive a sampler write,
	// including a partially failed write. Other texture objects remain cached.
	for (uint32_t other = 0U; other < MeshMatDescClass::MAX_TEX_STAGES; ++other) {
		NativeTextureStageCache &alias = g_texture_stage_cache[other];
		if (alias.sampler_texture == native_texture) alias.sampler_known = false;
	}
	// The original sequential DX8 state changes remain immediate. Suppress
	// only unchanged native object parameters, not intermediate owner states.
	// Clear before any write so a partially failed update cannot become a hit.
	object_sampler.generation = 0U;
	if (write_u) glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap_u);
	if (write_v) glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap_v);
	if (write_min) glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, native_min);
	if (write_mag) glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, native_mag);
	g_statistics.texture_sampler_parameter_writes +=
		static_cast<unsigned>(write_u) + static_cast<unsigned>(write_v) +
		static_cast<unsigned>(write_min) + static_cast<unsigned>(write_mag);
	glActiveTexture(GL_TEXTURE0);
	if (write_sampler) ++g_statistics.texture_sampler_updates;
	else ++g_statistics.texture_sampler_skips;
	if (glGetError() != GL_NO_ERROR) {
		cache.texture_known = false;
		++g_statistics.backend_errors;
		return false;
	}
	cache.texture_known = true;
	cache.texture = native_texture;
	cache.sampler_known = true;
	cache.sampler_texture = native_texture;
	cache.address_u = address_u;
	cache.address_v = address_v;
	cache.min_filter = min_filter;
	cache.mag_filter = mag_filter;
	cache.mip_filter = mip_filter;
	object_sampler.texture = native_texture;
	object_sampler.wrap_u = wrap_u;
	object_sampler.wrap_v = wrap_v;
	object_sampler.min_filter = native_min;
	object_sampler.mag_filter = native_mag;
	object_sampler.generation = g_texture_object_sampler_generation;
#else
	(void)address_u;
	(void)address_v;
	(void)min_filter;
	(void)mag_filter;
	(void)mip_filter;
	++g_statistics.texture_sampler_updates;
#endif
	return true;
}

bool Apply_DX8_Texture_Stage_State(uint32_t stage, uint32_t color_op,
	uint32_t color_arg1, uint32_t color_arg2, uint32_t alpha_op,
	uint32_t alpha_arg1, uint32_t alpha_arg2, bool texture_enabled)
{
	if (stage >= MeshMatDescClass::MAX_TEX_STAGES) {
		Record_Texture_Unsupported_Stage(stage);
		return false;
	}
#if defined(__vita__)
	if (!texture_enabled) {
		Set_Texture_Stage_Enabled(stage, false);
		NativeTextureStageCache &cache = g_texture_stage_cache[stage];
		if (cache.combiner_known && !cache.combiner_texture_enabled &&
			cache.color_op == color_op && cache.color_arg1 == color_arg1 &&
			cache.color_arg2 == color_arg2 && cache.alpha_op == alpha_op &&
			cache.alpha_arg1 == alpha_arg1 && cache.alpha_arg2 == alpha_arg2) {
			++g_statistics.texture_combiner_skips;
			return true;
		}
		cache.combiner_known = true;
		cache.combiner_texture_enabled = false;
		cache.color_op = color_op;
		cache.color_arg1 = color_arg1;
		cache.color_arg2 = color_arg2;
		cache.alpha_op = alpha_op;
		cache.alpha_arg1 = alpha_arg1;
		cache.alpha_arg2 = alpha_arg2;
		return true;
	}
	NativeTextureStageCache &cache = g_texture_stage_cache[stage];
	Set_Texture_Stage_Enabled(stage, true);
	if (cache.combiner_known && cache.combiner_texture_enabled &&
		cache.color_op == color_op && cache.color_arg1 == color_arg1 &&
		cache.color_arg2 == color_arg2 && cache.alpha_op == alpha_op &&
		cache.alpha_arg1 == alpha_arg1 && cache.alpha_arg2 == alpha_arg2) {
		++g_statistics.texture_combiner_skips;
		return true;
	}
	glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage));
	glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_COMBINE);
	Apply_GL_RGB_Texture_Op(color_op, color_arg1, color_arg2);
	Apply_GL_Alpha_Texture_Op(alpha_op, alpha_arg1, alpha_arg2);
	glActiveTexture(GL_TEXTURE0);
	cache.combiner_known = true;
	cache.combiner_texture_enabled = true;
	cache.color_op = color_op;
	cache.color_arg1 = color_arg1;
	cache.color_arg2 = color_arg2;
	cache.alpha_op = alpha_op;
	cache.alpha_arg1 = alpha_arg1;
	cache.alpha_arg2 = alpha_arg2;
	++g_statistics.state_changes;
	if (glGetError() != GL_NO_ERROR) {
		++g_statistics.backend_errors;
		return false;
	}
#else
	(void)stage;
	(void)color_op;
	(void)color_arg1;
	(void)color_arg2;
	(void)alpha_op;
	(void)alpha_arg1;
	(void)alpha_arg2;
	(void)texture_enabled;
#endif
	return true;
}

bool Apply_DX8_Render_State(uint32_t state, uint32_t value)
{
#if defined(__vita__)
	if (Render_State_Cache_Matches(state, value)) {
		++g_statistics.render_state_skips;
		return true;
	}
	if (Update_Fog_State_From_DX8_Render_State(state, value, g_fog_state)) {
		const bool applied = Apply_Current_Fog_State();
		if (applied && g_statistics.initialized) {
			Store_Render_State_Cache(state, value);
		}
		return applied;
	}
	if (Update_Ambient_State_From_DX8_Render_State(state, value,
		g_dx8_ambient_color)) {
		const bool applied = Apply_Current_Ambient_State();
		if (applied && g_statistics.initialized) {
			Store_Render_State_Cache(state, value);
		}
		return applied;
	}
	if (!g_statistics.initialized) {
		return true;
	}
	bool handled = true;
	bool shader_state_overlap = false;
	switch (state) {
	case D3DRS_ALPHABLENDENABLE:
		shader_state_overlap = true;
		if (value != 0U) {
			glEnable(GL_BLEND);
			glBlendFunc(g_dx8_source_blend, g_dx8_destination_blend);
		} else {
			glDisable(GL_BLEND);
		}
		break;
	case D3DRS_SRCBLEND:
		shader_state_overlap = true;
		g_dx8_source_blend = To_GL_DX8_Blend(value);
		glBlendFunc(g_dx8_source_blend, g_dx8_destination_blend);
		break;
	case D3DRS_DESTBLEND:
		shader_state_overlap = true;
		g_dx8_destination_blend = To_GL_DX8_Blend(value);
		glBlendFunc(g_dx8_source_blend, g_dx8_destination_blend);
		break;
	case D3DRS_ALPHATESTENABLE:
		shader_state_overlap = true;
		if (value != 0U) {
			glEnable(GL_ALPHA_TEST);
		} else {
			glDisable(GL_ALPHA_TEST);
		}
		break;
	case D3DRS_ALPHAREF:
		shader_state_overlap = true;
		g_dx8_alpha_reference =
			static_cast<float>(value & 0xffU) / 255.0f;
		glAlphaFunc(g_dx8_alpha_function, g_dx8_alpha_reference);
		break;
	case D3DRS_ALPHAFUNC:
		shader_state_overlap = true;
		g_dx8_alpha_function = To_GL_DX8_Compare(value);
		glAlphaFunc(g_dx8_alpha_function, g_dx8_alpha_reference);
		break;
	case D3DRS_ZFUNC:
		shader_state_overlap = true;
		glDepthFunc(To_GL_DX8_Compare(value));
		break;
	case D3DRS_ZWRITEENABLE:
		shader_state_overlap = true;
		glDepthMask(value != 0U ? GL_TRUE : GL_FALSE);
		break;
	case D3DRS_CULLMODE:
		shader_state_overlap = true;
		if (value == D3DCULL_NONE) {
			glDisable(GL_CULL_FACE);
		} else {
			glEnable(GL_CULL_FACE);
			// The native baseline keeps GL's counterclockwise front faces.
			// DX8 names the winding to discard, not the winding to retain.
			// Preserve normal CW culling and distinguish the inverted mode.
			glCullFace(value == D3DCULL_CCW ? GL_FRONT : GL_BACK);
		}
		break;
	case D3DRS_FILLMODE:
		glPolygonMode(GL_FRONT_AND_BACK, To_GL_DX8_Fill_Mode(value));
		break;
	default:
		handled = false;
		break;
	}
	if (!handled) {
		if (!g_logged_first_unsupported_render_state) {
			Vita_Append_A22_Runtime_Breadcrumb("render-state",
				"first deferred DX8 render state: state=%u value=%08X",
				state, value);
			g_logged_first_unsupported_render_state = true;
		}
		return true;
	}
	++g_statistics.state_changes;
	if (shader_state_overlap) {
		Invalidate_Original_Shader_State_Cache();
	}
	const GLenum error = glGetError();
	if (error != GL_NO_ERROR) {
		++g_statistics.backend_errors;
		return false;
	}
	Store_Render_State_Cache(state, value);
#else
	(void)state;
	(void)value;
#endif
	return true;
}

void Record_Texture_Unsupported_Stage(uint32_t stage)
{
	if (stage >= MeshMatDescClass::MAX_TEX_STAGES) {
		++g_statistics.texture_unsupported_stages;
	}
}

void Release_Texture(uint32_t native_texture)
{
#if defined(__vita__)
	if (native_texture != 0U) {
		glDeleteTextures(1, &native_texture);
		Invalidate_Texture_State_Cache();
	}
#else
	(void)native_texture;
#endif
}

void Submit_Mesh(MeshClass &mesh, RenderInfoClass &render_info)
{
	MeshModelClass *model = mesh.Peek_Model();
	if (!g_statistics.initialized || model == NULL) {
		return;
	}

	const int vertex_count = model->Get_Vertex_Count();
	const int triangle_count = model->Get_Polygon_Count();
	const bool is_skin = model->Get_Flag(MeshGeometryClass::SKIN);
	const Vector3 *vertices = model->Get_Vertex_Array();
	const Vector3 *normals = model->Get_Vertex_Normal_Array();
	const TriIndex *triangles = model->Get_Polygon_Array();
	if (vertices == NULL || triangles == NULL || vertex_count <= 0 || triangle_count <= 0) {
		return;
	}
	if (is_skin) {
		if (!Ensure_Deformed_Skin_Scratch(vertex_count)) {
			++g_statistics.skin_deformation_failures;
			++g_statistics.backend_errors;
#if defined(__vita__)
			if (!g_logged_skin_failure) {
				Vita_Append_A22_Runtime_Breadcrumb("skin-submit",
					"deformed scratch allocation failed: vertices=%d", vertex_count);
				g_logged_skin_failure = true;
			}
#endif
			return;
		}
		/* Original DX8SkinFVFCategoryContainer dynamically deforms every skin
		** through its owning HTree before drawing it with an identity world
		** transform. Preserve that ownership here; model-space source vertices
		** are not a renderable substitute for animated character geometry. */
		mesh.Get_Deformed_Vertices(g_deformed_skin_vertices,
			g_deformed_skin_normals);
		vertices = g_deformed_skin_vertices;
		normals = g_deformed_skin_normals;
		++g_statistics.skinned_mesh_submissions;
		g_statistics.deformed_skin_vertices += static_cast<uint32_t>(vertex_count);
	}

	const int pass_count = model->Get_Pass_Count();
	const int base_pass_count = pass_count > 0 ? pass_count : 1;
	++g_statistics.mesh_submissions;
	g_statistics.vertex_submissions += static_cast<uint32_t>(vertex_count);
	g_statistics.triangle_submissions += static_cast<uint32_t>(triangle_count);
	g_statistics.geometry_checksum = Mix_Checksum(g_statistics.geometry_checksum,
		static_cast<uint32_t>(vertex_count));
	g_statistics.geometry_checksum = Mix_Checksum(g_statistics.geometry_checksum,
		static_cast<uint32_t>(triangle_count));
	g_statistics.material_passes +=
		static_cast<uint64_t>(base_pass_count);

#if !defined(__vita__)
	// The host target has no Vita framebuffer, but it must still execute the
	// same original material-to-TextureClass boundary as the physical path.
	// This validates archive lookup, DDS decode, upload representation, bind
	// ownership, and repeat lifecycle teardown rather than mistaking a
	// geometry-only headless frame for a textured-frame proof.
	for (int pass = 0; pass < base_pass_count; ++pass) {
		TextureClass *bound_textures[MeshMatDescClass::MAX_TEX_STAGES] = {};
		for (int triangle_index = 0; triangle_index < triangle_count; ++triangle_index) {
			for (int stage = 0; stage < MeshMatDescClass::MAX_TEX_STAGES; ++stage) {
				TextureClass *texture = model->Peek_Texture(triangle_index, pass, stage);
				if (texture != bound_textures[stage]) {
					bound_textures[stage] = texture;
					if (bound_textures[stage] != NULL) {
						bound_textures[stage]->Apply_For_Platform_Boundary(
							static_cast<unsigned int>(stage));
					} else if (stage == 0) {
						Bind_Texture(0U, false);
					} else {
						Disable_Texture_Stage(static_cast<uint32_t>(stage));
					}
				}
			}
		}
	}
#endif

#if defined(__vita__)
	/*
	 * Keep the original object, view, and D3D projection transforms intact
	 * until vitaGL's vertex stage.  The former path called Camera::Project on
	 * the CPU and then submitted divided coordinates under identity matrices;
	 * that discarded homogeneous W and made texture interpolation affine.
	 */
	Matrix3D original_world_transform;
	if (is_skin) original_world_transform.Make_Identity();
	else original_world_transform = mesh.Get_Transform();
	const Matrix4 world_transform(original_world_transform);
	const Matrix3D &original_view_transform = render_info.Camera.Get_View_Matrix();
	const Matrix4 view_transform(original_view_transform);
	Matrix4 d3d_projection;
	render_info.Camera.Get_D3D_Projection_Matrix(&d3d_projection);
	const Matrix4 dx8_world = world_transform.Transpose();
	const Matrix4 dx8_view = view_transform.Transpose();
	const Matrix4 dx8_projection = d3d_projection.Transpose();
	IndexedTransformMatrices transform_matrices = {};
	if (!Build_Indexed_Transform_Matrices(&dx8_world[0][0], &dx8_view[0][0],
		&dx8_projection[0][0], transform_matrices)) {
		++g_statistics.backend_errors;
		Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
			"original MeshClass transform conversion failed");
		return;
	}
	glMatrixMode(GL_PROJECTION);
	glLoadMatrixf(transform_matrices.projection);
	glMatrixMode(GL_MODELVIEW);
	glLoadMatrixf(transform_matrices.modelview);
	g_statistics.state_changes += 4U;
	TextureClass *first_texture = model->Peek_Texture(0, 0, 0);
	if (!g_logged_first_mesh) {
		Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
			"first original MeshClass submission entry: vertices=%d triangles=%d passes=%d",
			vertex_count, triangle_count, base_pass_count);
	}
		const char *first_texture_name = first_texture != NULL ?
			first_texture->Get_Texture_Name().Peek_Buffer() : "none";
		if (is_skin && !g_logged_first_skin &&
			!Is_Loading_Screen_Diagnostic_Name(mesh.Get_Name()) &&
			!Is_Loading_Screen_Diagnostic_Name(first_texture_name)) {
			Vita_Append_A22_Runtime_Breadcrumb("skin-submit",
				"first original deformed skin submission: mesh=%s vertices=%d triangles=%d passes=%d texture=%s uv=%d dcg=%d world=identity",
				mesh.Get_Name(), vertex_count, triangle_count, pass_count,
				first_texture_name,
				model->Get_UV_Array(0, 0) != NULL ? 1 : 0,
				model->Get_DCG_Array(0) != NULL ? 1 : 0);
		g_logged_first_skin = true;
	}
	for (int pass = 0; pass < base_pass_count; ++pass) {
		const Vector2 *uvs[MeshMatDescClass::MAX_TEX_STAGES] = {
			model->Get_UV_Array(pass, 0),
			model->Get_UV_Array(pass, 1)
		};
		const unsigned *diffuse_colors = model->Get_DCG_Array(pass);
		const unsigned *user_lighting =
			is_skin ? NULL : mesh.Get_User_Lighting_Array(false);
		const unsigned *color1 =
			user_lighting != NULL ? user_lighting :
				model->Get_Color_Array(0, false);
		const unsigned *color2 = model->Get_Color_Array(1, false);
		if (color1 == NULL && model->Get_DCG_Source(pass) == VertexMaterialClass::COLOR1) {
			color1 = diffuse_colors;
		}
		if (color2 == NULL && model->Get_DCG_Source(pass) == VertexMaterialClass::COLOR2) {
			color2 = diffuse_colors;
		}
#if defined(__vita__)
		if (user_lighting != NULL && !g_logged_first_user_lighting) {
			Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
				"first original user lighting color source: mesh=%s pass=%d vertices=%d first=%08X",
				mesh.Get_Name(), pass, vertex_count, user_lighting[0]);
			g_logged_first_user_lighting = true;
		}
#endif
		TextureClass *bound_textures[MeshMatDescClass::MAX_TEX_STAGES] = {};
		unsigned current_shader_bits = 0xffffffffU;
		VertexMaterialClass *current_material = NULL;
		const Vector2 *current_uvs[MeshMatDescClass::MAX_TEX_STAGES] = {};
		OriginalTextureCoordinateState
			current_texture_coordinates[MeshMatDescClass::MAX_TEX_STAGES] = {};
		bool current_detail_stage = false;
		bool primitive_open = false;
		const bool cache_material_colors = Begin_Material_Color_Pass(vertex_count);
		MaterialLightDirections light_directions;
		if (cache_material_colors) {
			Prepare_Material_Light_Directions(render_info, light_directions);
		}
		const bool indexed_batch = (g_render_work_cache_mode & 8U) != 0U;
		bool current_texturing = false;
		auto emit_vertex = [&](unsigned vertex_index, bool emit_position) {
				if (bound_textures[0] != NULL) {
					Emit_Original_Texture_Coordinate(0U, GL_TEXTURE0,
						current_texture_coordinates[0], current_uvs[0], vertices,
						normals, vertex_index, original_world_transform,
						original_view_transform,
						bound_textures[0]->Get_Texture_Name().Peek_Buffer());
				}
				if (current_detail_stage) {
					const Vector2 *detail_uvs =
						current_uvs[1] != NULL ? current_uvs[1] : current_uvs[0];
					Emit_Original_Texture_Coordinate(1U, GL_TEXTURE1,
						current_texture_coordinates[1], detail_uvs, vertices,
						normals, vertex_index, original_world_transform,
						original_view_transform,
						bound_textures[1]->Get_Texture_Name().Peek_Buffer());
				}
			/* Preserve the original mesh material color owner.  The former Vita
			** bridge invented RGB from each normal, visibly recoloring otherwise
			** valid NPC skin textures.  The current path now evaluates original
			** VertexMaterial lighting and color-source state below the WW3D
			** boundary before handing the result to vitaGL for texture modulation. */
			VertexMaterialClass *material =
				model->Peek_Material(static_cast<int>(vertex_index), pass);
			const bool skin_color_passthrough = is_skin && bound_textures[0] != NULL &&
				current_texturing;
			const bool record_original_skin_color = skin_color_passthrough &&
				!g_logged_first_skin_texture_color &&
				!Is_Loading_Screen_Diagnostic_Name(mesh.Get_Name()) &&
				!Is_Loading_Screen_Diagnostic_Name(
					bound_textures[0]->Get_Texture_Name().Peek_Buffer());
			const MaterialVertexColor vertex_color = Evaluate_Material_Vertex_Color(
				cache_material_colors, material, color1, color2, vertex_index,
				normals, original_world_transform, render_info, light_directions,
				skin_color_passthrough && !record_original_skin_color &&
					g_logged_first_material_lighting);
			Vector3 final_color = vertex_color.final_color;
			if (skin_color_passthrough) {
				if (record_original_skin_color) {
					Vita_Append_A22_Runtime_Breadcrumb("skin-submit",
						"first textured skin color pass-through: mesh=%s pass=%d texture=%s material_lighting=%d original_rgb=(%.3f,%.3f,%.3f) alpha=%.3f",
						mesh.Get_Name(), pass,
						bound_textures[0]->Get_Texture_Name().Peek_Buffer(),
						vertex_color.lighting ? 1 : 0, final_color.X,
						final_color.Y, final_color.Z, vertex_color.alpha);
					g_logged_first_skin_texture_color = true;
				}
				final_color = Vector3(1.0f, 1.0f, 1.0f);
			}
			if (!g_logged_first_material_lighting) {
				Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
					"first original material lighting: mesh=%s pass=%d lighting=%d lights=%u color1=%d color2=%d rgb=(%.3f,%.3f,%.3f) alpha=%.3f",
					mesh.Get_Name(), pass, vertex_color.lighting ? 1 : 0,
					vertex_color.light_count, color1 != NULL ? 1 : 0,
					color2 != NULL ? 1 : 0, final_color.X, final_color.Y,
					final_color.Z, vertex_color.alpha);
				g_logged_first_material_lighting = true;
			}
			glColor4f(Clamp01(final_color.X), Clamp01(final_color.Y),
				Clamp01(final_color.Z), Clamp01(vertex_color.alpha));
			if (emit_position) glVertex3f(vertices[vertex_index].X, vertices[vertex_index].Y,
				vertices[vertex_index].Z);
		};
		auto end_batch = [&]() {
			if (indexed_batch && g_indexed_mesh_batch.Count() != 0U) {
				// Immediate GL attributes persist across draws. Restore the final
				// original corner even when its vertex was reused from earlier.
				emit_vertex(g_indexed_mesh_batch.Last(), false);
				vglRenegadeEndIndexed(g_indexed_mesh_batch.Count(),
					g_indexed_mesh_batch.Indices());
				g_mesh_expanded_corners += g_indexed_mesh_batch.Count();
				g_mesh_unique_vertices += g_indexed_mesh_batch.Vertices();
				++g_mesh_indexed_batches;
			} else glEnd();
		};
		for (int triangle_index = 0; triangle_index < triangle_count; ++triangle_index) {
			TextureClass *triangle_textures[MeshMatDescClass::MAX_TEX_STAGES] = {
				model->Peek_Texture(triangle_index, pass, 0),
				model->Peek_Texture(triangle_index, pass, 1)
			};
			const TriIndex &group_triangle = triangles[triangle_index];
			VertexMaterialClass *triangle_material =
				group_triangle[0] < vertex_count ?
					model->Peek_Material(static_cast<int>(group_triangle[0]), pass) :
					NULL;
			const ShaderClass triangle_shader = model->Get_Shader(triangle_index, pass);
			const unsigned triangle_shader_bits = triangle_shader.Get_Bits();
			const bool detail_stage =
				triangle_shader.Uses_Post_Detail_Texture() &&
				triangle_textures[1] != NULL;
			if (triangle_textures[0] != bound_textures[0] ||
				triangle_textures[1] != bound_textures[1] ||
				triangle_material != current_material ||
				detail_stage != current_detail_stage ||
				triangle_shader_bits != current_shader_bits || !primitive_open) {
				if (primitive_open) end_batch();
				bound_textures[0] = triangle_textures[0];
				bound_textures[1] = triangle_textures[1];
				current_material = triangle_material;
				current_detail_stage = detail_stage;
				current_shader_bits = triangle_shader_bits;
				current_texturing = triangle_shader.Get_Texturing() == ShaderClass::TEXTURING_ENABLE;
				// ShaderClass remains the authoritative original material policy.
				// Translate only the fixed-function state VitaGL exposes here; this
				// preserves alpha-cutout, conventional transparency and additive fire.
				Apply_Original_Shader_State(triangle_shader);
				if (bound_textures[0] != NULL) {
					// Retain TextureClass as the resource/lifetime owner and invoke its
					// original filter, mip, wrap, and bind sequence through the narrow
					// platform bridge.
					bound_textures[0]->Apply_For_Platform_Boundary(0U);
				} else {
					Bind_Texture(0U, false);
				}
				if (current_detail_stage) {
					bound_textures[1]->Apply_For_Platform_Boundary(1U);
				} else {
					Disable_Texture_Stage(1U);
				}
				Apply_Original_Texture_Coordinate_State(current_material);
				for (unsigned stage = 0U; stage < MeshMatDescClass::MAX_TEX_STAGES; ++stage) {
					Capture_Original_Texture_Coordinate_State(stage,
						&current_texture_coordinates[stage]);
					current_uvs[stage] = Resolve_UV_Array_For_Texture_State(model,
						current_texture_coordinates[stage], uvs[stage]);
				}
				if (is_skin && bound_textures[0] != NULL &&
					!g_logged_first_skin_passthrough_texture_v_preserved &&
					Texture_Coordinate_Mode(current_texture_coordinates[0]) ==
						D3DTSS_TCI_PASSTHRU &&
					!Is_Loading_Screen_Diagnostic_Name(mesh.Get_Name()) &&
					!Is_Loading_Screen_Diagnostic_Name(
						bound_textures[0]->Get_Texture_Name().Peek_Buffer())) {
					Vita_Append_A22_Runtime_Breadcrumb("skin-submit",
						"first skinned gameplay passthrough texture V preserved: mesh=%s pass=%d texture=%s uv_source=%u flags=%08X",
						mesh.Get_Name(), pass,
						bound_textures[0]->Get_Texture_Name().Peek_Buffer(),
						static_cast<unsigned>(
							current_texture_coordinates[0].texcoord_index & 0xffffU),
						static_cast<unsigned>(
							current_texture_coordinates[0].texture_transform_flags));
					g_logged_first_skin_passthrough_texture_v_preserved = true;
				}
				Apply_Original_Texture_Stage_State(triangle_shader,
					bound_textures[0] != NULL, current_detail_stage);
				if (current_detail_stage && !g_logged_first_stage1_mesh) {
					Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
						"first original MeshClass stage1 texture: mesh=%s pass=%d texture0=%s texture1=%s shader=%08X color=%d alpha=%d uv1=%d",
						mesh.Get_Name(), pass,
						bound_textures[0] != NULL ?
							bound_textures[0]->Get_Texture_Name().Peek_Buffer() : "none",
						bound_textures[1] != NULL ?
							bound_textures[1]->Get_Texture_Name().Peek_Buffer() : "none",
						triangle_shader_bits,
						static_cast<int>(triangle_shader.Get_Post_Detail_Color_Func()),
						static_cast<int>(triangle_shader.Get_Post_Detail_Alpha_Func()),
						current_uvs[1] != NULL ? 1 : 0);
					g_logged_first_stage1_mesh = true;
				}
				if (indexed_batch) g_indexed_mesh_batch.Reset();
				glBegin(GL_TRIANGLES);
				primitive_open = true;
			}
			const TriIndex &triangle = triangles[triangle_index];
			unsigned vertex_indices[3] = {
				static_cast<unsigned>(vertex_count), static_cast<unsigned>(vertex_count),
				static_cast<unsigned>(vertex_count)
			};
			for (int corner = 0; corner < 3; ++corner) {
				const unsigned vertex_index = triangle[corner];
				if (vertex_index >= static_cast<unsigned>(vertex_count)) {
					vertex_indices[corner] = static_cast<unsigned>(vertex_count);
					break;
				}
				vertex_indices[corner] = vertex_index;
			}
			if (vertex_indices[0] >= static_cast<unsigned>(vertex_count) ||
				vertex_indices[1] >= static_cast<unsigned>(vertex_count) ||
				vertex_indices[2] >= static_cast<unsigned>(vertex_count)) {
				continue;
			}
			if (indexed_batch && g_indexed_mesh_batch.Full()) {
				end_batch();
				g_indexed_mesh_batch.Reset();
				glBegin(GL_TRIANGLES);
			}
			for (int corner = 0; corner < 3; ++corner) {
				const unsigned vertex_index = vertex_indices[corner];
				if (!indexed_batch || g_indexed_mesh_batch.Append(vertex_index)) {
					emit_vertex(vertex_index, true);
				}
			}
		}
		if (primitive_open) end_batch();
	}
	Disable_Texture_Stage(1U);
	Apply_Original_Texture_Coordinate_State(NULL);
	// Submit_Indexed_Triangles may be used later in the same frame by HUD or
	// native DX8 boundary callers. Restore its explicit identity baseline only
	// after this homogeneous mesh submission is complete.
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	g_statistics.state_changes += 4U;
	if (!g_logged_first_mesh) {
		const GLenum error = glGetError();
		Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
			"first original MeshClass submission return: glGetError=%08X",
			static_cast<unsigned>(error));
		g_logged_first_mesh = true;
	}
#else
	(void)render_info;
#endif
}

IndexedSubmissionResult Submit_Indexed_Triangles(
	const IndexedTriangleSubmission &submission)
{
	if (!g_statistics.initialized) {
		++g_statistics.rejected_indexed_submissions;
		Log_Indexed_Rejection("renderer is not initialized", submission.vertex_format);
		return INDEXED_SUBMISSION_NOT_INITIALIZED;
	}

	const uint32_t mesh_fvf = 0x00000152U; // XYZ | NORMAL | DIFFUSE | TEX1
	const uint32_t render2d_fvf = 0x00000252U; // legacy dynamic XYZ | N | D | TEX2
	const bool mesh_layout = submission.vertex_format == mesh_fvf &&
		submission.vertex_stride == 36U;
	const bool dynamic_two_uv_layout = submission.vertex_format == render2d_fvf &&
		submission.vertex_stride == 44U;
	if (!mesh_layout && !dynamic_two_uv_layout) {
		++g_statistics.unsupported_submissions;
		++g_statistics.rejected_indexed_submissions;
		static bool logged_rejected_layout = false;
		if (!logged_rejected_layout) {
			fprintf(stderr, "A4 indexed layout rejected: fvf=%08X stride=%u mesh=%d dynamic2uv=%d\n",
				submission.vertex_format, submission.vertex_stride,
				mesh_layout ? 1 : 0, dynamic_two_uv_layout ? 1 : 0);
			logged_rejected_layout = true;
		}
		Log_Indexed_Rejection("unsupported FVF/stride", submission.vertex_format);
		return INDEXED_SUBMISSION_UNSUPPORTED_FVF;
	}
	if (submission.vertex_data == NULL || submission.index_data == NULL ||
		submission.triangle_count == 0U || submission.vertex_count == 0U ||
		submission.vertex_stride == 0U ||
		submission.vertex_capacity > submission.vertex_data_size / submission.vertex_stride) {
		++g_statistics.rejected_indexed_submissions;
		Log_Indexed_Rejection("invalid buffer view", submission.vertex_format);
		return INDEXED_SUBMISSION_INVALID_ARGUMENT;
	}

	const uint32_t requested_indices = submission.triangle_count * 3U;
	if (submission.triangle_count > 0xffffffffU / 3U ||
		submission.first_index > submission.index_capacity ||
		requested_indices > submission.index_capacity - submission.first_index) {
		++g_statistics.rejected_indexed_submissions;
		Log_Indexed_Rejection("index buffer range", submission.vertex_format);
		return INDEXED_SUBMISSION_INDEX_RANGE_ERROR;
	}
	if (submission.min_vertex_index > 0xffffffffU - submission.vertex_count ||
		submission.base_vertex_index > submission.vertex_capacity) {
		++g_statistics.rejected_indexed_submissions;
		Log_Indexed_Rejection("declared vertex range", submission.vertex_format);
		return INDEXED_SUBMISSION_VERTEX_RANGE_ERROR;
	}

	const uint32_t declared_end = submission.min_vertex_index + submission.vertex_count;
	uint32_t checksum = g_statistics.indexed_geometry_checksum;
	checksum = Mix_Checksum(checksum, submission.vertex_format);
	checksum = Mix_Checksum(checksum, submission.vertex_stride);
	checksum = Mix_Checksum(checksum, submission.first_index);
	checksum = Mix_Checksum(checksum, submission.triangle_count);
	checksum = Mix_Checksum(checksum, submission.base_vertex_index);
	checksum = Mix_Checksum(checksum, submission.min_vertex_index);
	checksum = Mix_Checksum(checksum, submission.vertex_count);
#if defined(__vita__)
	const bool fused_index_preparation = (g_render_work_cache_mode & 8U) != 0U;
#else
	const bool fused_index_preparation = false;
#endif
	for (uint32_t offset = 0; offset < requested_indices; ++offset) {
		const uint32_t relative_index =
			submission.index_data[submission.first_index + offset];
		if (relative_index < submission.min_vertex_index || relative_index >= declared_end ||
			relative_index > 0xffffffffU - submission.base_vertex_index ||
			submission.base_vertex_index + relative_index >= submission.vertex_capacity) {
			++g_statistics.rejected_indexed_submissions;
			Log_Indexed_Rejection("referenced vertex range", submission.vertex_format);
			return INDEXED_SUBMISSION_VERTEX_RANGE_ERROR;
		}
		if (fused_index_preparation) {
			// Preserve bounds checks and checksum order, including repeated indices.
			// Commit this local checksum only after the entire draw is valid.
			const uint32_t actual_index = submission.base_vertex_index + relative_index;
			const unsigned char *vertex = submission.vertex_data +
				actual_index * submission.vertex_stride;
			float position[3];
			uint32_t diffuse = 0U;
			memcpy(position, vertex, sizeof(position));
			memcpy(&diffuse, vertex + 24U, sizeof(diffuse));
			checksum = Mix_Checksum(checksum, relative_index);
			checksum = Mix_Checksum(checksum, actual_index);
			checksum = Mix_Checksum(checksum, Float_Bits(position[0]));
			checksum = Mix_Checksum(checksum, Float_Bits(position[1]));
			checksum = Mix_Checksum(checksum, Float_Bits(position[2]));
			checksum = Mix_Checksum(checksum, diffuse);
		}
	}
	IndexedTransformMatrices transform_matrices = {};
	if (!Build_Indexed_Transform_Matrices(submission.world_transform,
		submission.view_transform, submission.projection_transform,
		transform_matrices)) {
		++g_statistics.rejected_indexed_submissions;
		Log_Indexed_Rejection("world/view/projection transform unavailable",
			submission.vertex_format);
		return INDEXED_SUBMISSION_MISSING_TRANSFORM;
	}

	// Keep the separate baseline traversal available for later comparison.
	for (uint32_t offset = 0; !fused_index_preparation && offset < requested_indices; ++offset) {
		const uint32_t relative_index =
			submission.index_data[submission.first_index + offset];
		const uint32_t actual_index = submission.base_vertex_index + relative_index;
		const unsigned char *vertex = submission.vertex_data +
			actual_index * submission.vertex_stride;
		float position[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
		uint32_t diffuse = 0;
		memcpy(position, vertex, 3U * sizeof(float));
		const uint32_t diffuse_offset = 24U;
		memcpy(&diffuse, vertex + diffuse_offset, sizeof(diffuse));

		checksum = Mix_Checksum(checksum, relative_index);
		checksum = Mix_Checksum(checksum, actual_index);
		checksum = Mix_Checksum(checksum, Float_Bits(position[0]));
		checksum = Mix_Checksum(checksum, Float_Bits(position[1]));
		checksum = Mix_Checksum(checksum, Float_Bits(position[2]));
		checksum = Mix_Checksum(checksum, diffuse);
	}

#if defined(__vita__)
	// Let vitaGL's fixed-function vertex shader retain homogeneous W through
	// clipping and interpolation.  CPU-dividing to NDC here would turn W into
	// one, incorrectly draw behind-camera geometry and make UVs affine.
	glMatrixMode(GL_PROJECTION);
	glLoadMatrixf(transform_matrices.projection);
	glMatrixMode(GL_MODELVIEW);
	glLoadMatrixf(transform_matrices.modelview);

	OriginalTextureCoordinateState texture_coordinates[MAX_TEXTURE_STAGES] = {};
	for (unsigned stage = 0U; stage < MAX_TEXTURE_STAGES; ++stage) {
		Capture_Original_Texture_Coordinate_State(stage,
			&texture_coordinates[stage]);
	}
	const uint32_t diffuse_offset = 24U;
	const uint32_t uv0_offset = 28U;
	const uint32_t uv1_offset = dynamic_two_uv_layout ? 36U : uv0_offset;

	const bool indexed_batch = fused_index_preparation;
	auto emit_indexed_vertex = [&](uint32_t actual_index, bool emit_position) {
		const unsigned char *vertex = submission.vertex_data +
			actual_index * submission.vertex_stride;
		float position[3];
		float normal[3];
		float uv0[2];
		float uv1[2];
		uint32_t diffuse = 0;
		memcpy(position, vertex, 3U * sizeof(float));
		/* Render2D's original dynamic FVF retains a second UV slot after
		 * the populated first UV. Its leading position/normal/diffuse
		 * layout is therefore identical to the mesh layout. */
		memcpy(&diffuse, vertex + diffuse_offset, sizeof(diffuse));
		memcpy(normal, vertex + 12U, 3U * sizeof(float));
		memcpy(uv0, vertex + uv0_offset, 2U * sizeof(float));
		memcpy(uv1, vertex + uv1_offset, 2U * sizeof(float));
		glColor4ub(static_cast<GLubyte>((diffuse >> 16U) & 0xffU),
			static_cast<GLubyte>((diffuse >> 8U) & 0xffU),
			static_cast<GLubyte>(diffuse & 0xffU),
			static_cast<GLubyte>((diffuse >> 24U) & 0xffU));
		if (mesh_layout || dynamic_two_uv_layout) {
			glNormal3f(normal[0], normal[1], normal[2]);
		} else {
			glNormal3f(0.0f, 0.0f, 1.0f);
		}
			Emit_Indexed_Texture_Coordinate(0U, GL_TEXTURE0,
				texture_coordinates[0], uv0, uv1, position, normal,
				submission.world_transform, submission.view_transform,
				submission.texture_names[0]);
			Emit_Indexed_Texture_Coordinate(1U, GL_TEXTURE1,
				texture_coordinates[1], uv0, uv1, position, normal,
				submission.world_transform, submission.view_transform,
				submission.texture_names[1]);
		if (emit_position) glVertex3f(position[0], position[1], position[2]);
	};
	auto end_indexed_batch = [&]() {
		if (indexed_batch && g_indexed_mesh_batch.Count()) {
			emit_indexed_vertex(g_indexed_mesh_batch.Last(), false);
			vglRenegadeEndIndexed(g_indexed_mesh_batch.Count(), g_indexed_mesh_batch.Indices());
			g_mesh_expanded_corners += g_indexed_mesh_batch.Count();
			g_mesh_unique_vertices += g_indexed_mesh_batch.Vertices();
			++g_mesh_indexed_batches;
		} else glEnd();
	};
	if (indexed_batch) g_indexed_mesh_batch.Reset();
	glBegin(GL_TRIANGLES);
	for (uint32_t triangle = 0; triangle < submission.triangle_count; ++triangle) {
		if (indexed_batch && g_indexed_mesh_batch.Full()) {
			end_indexed_batch();
			g_indexed_mesh_batch.Reset();
			glBegin(GL_TRIANGLES);
		}
		for (uint32_t corner = 0; corner < 3U; ++corner) {
			const uint32_t relative_index = submission.index_data[
				submission.first_index + triangle * 3U + corner];
			const uint32_t actual_index = submission.base_vertex_index + relative_index;
			if (!indexed_batch || g_indexed_mesh_batch.Append(actual_index)) {
				emit_indexed_vertex(actual_index, true);
			}
		}
	}
	end_indexed_batch();
	const uint32_t emitted_triangles = submission.triangle_count;
	Disable_Texture_Stage(1U);

	// Restore the shared identity baseline after homogeneous GPU submission.
	// Both mesh and generic indexed draws load their original transforms.
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	g_statistics.state_changes += 4U;
#endif

	++g_statistics.indexed_submissions;
	++g_statistics.material_passes;
	g_statistics.indexed_vertex_references += requested_indices;
	g_statistics.indexed_triangle_submissions += submission.triangle_count;
	g_statistics.indexed_geometry_checksum = checksum;

#if defined(__vita__)
	static bool logged_first_indexed_submission = false;
	if (!logged_first_indexed_submission) {
		const GLenum error = glGetError();
		Vita_Append_A22_Runtime_Breadcrumb("indexed-submit",
			"first original DX8Wrapper indexed draw: fvf=%08X stride=%u first=%u triangles=%u emitted=%u base=%u min=%u vertices=%u checksum=%08X glGetError=%08X",
			submission.vertex_format, submission.vertex_stride,
			submission.first_index, submission.triangle_count,
			emitted_triangles,
			submission.base_vertex_index, submission.min_vertex_index,
			submission.vertex_count, checksum, static_cast<unsigned>(error));
		logged_first_indexed_submission = true;
	}
#endif
	return INDEXED_SUBMISSION_OK;
}

void Reject_Indexed_Submission(const char *reason, uint32_t vertex_format)
{
	++g_statistics.unsupported_submissions;
	++g_statistics.rejected_indexed_submissions;
	Log_Indexed_Rejection(reason, vertex_format);
}

void Submit_Unsupported(RenderObjClass *object)
{
	++g_statistics.unsupported_submissions;
	if (!g_logged_first_unsupported) {
		const char *name = object != NULL ? object->Get_Name() : "(null)";
		const int class_id = object != NULL ? object->Class_ID() : -1;
#if defined(__vita__)
		Vita_Append_A22_Runtime_Breadcrumb("unsupported-submit",
			"first unsupported RenderObj: name=%s class_id=%d",
			name != NULL ? name : "(null)", class_id);
#else
		fprintf(stderr, "A2.2 first unsupported RenderObj: name=%s class_id=%d\n",
			name != NULL ? name : "(null)", class_id);
#endif
		g_logged_first_unsupported = true;
	}
}

void Submit_Decals_Unsupported()
{
	++g_statistics.unsupported_submissions;
	if (!g_logged_first_unsupported) {
#if defined(__vita__)
		Vita_Append_A22_Runtime_Breadcrumb("unsupported-submit",
			"first unsupported operation: decal mesh render");
#else
		fprintf(stderr, "A2.2 first unsupported operation: decal mesh render\n");
#endif
		g_logged_first_unsupported = true;
	}
}

bool Capture_Resolved_Frame_RGBA(uint8_t *output, size_t output_bytes,
	bool presented_frame)
{
	const size_t required = static_cast<size_t>(DISPLAY_WIDTH) *
		static_cast<size_t>(DISPLAY_HEIGHT) * 4U;
	if (!g_statistics.initialized || output == NULL || output_bytes < required) {
		return false;
	}
#if defined(__vita__)
	memset(output, 0, required);
	(void)glGetError();
	// vitaGL rotates the back-buffer index in vglSwapBuffers. A post-present
	// capture must read the front buffer, not the next render destination.
	glReadBuffer(presented_frame ? GL_FRONT : GL_BACK);
	// Keep the RGBA8888 CPU readback path. The pinned GPU-transfer variant
	// uses a negative display stride and Dev122 fails inside Vita3K during
	// this loading capture. Emulator framebuffer screenshots remain separate
	// evidence until native readback synchronization is validated.
	glReadPixels(0, 0, static_cast<GLsizei>(DISPLAY_WIDTH),
		static_cast<GLsizei>(DISPLAY_HEIGHT), GL_RGBA, GL_UNSIGNED_BYTE, output);
	const GLenum error = glGetError();
	glReadBuffer(GL_BACK);
	if (error != GL_NO_ERROR) {
		++g_statistics.backend_errors;
		return false;
	}
#else
	(void)presented_frame;
	memset(output, 0, required);
#endif
	return true;
}

bool Query_Backend_Memory(BackendMemoryStatistics &memory)
{
	memory = {};
#if defined(__vita__)
	SceKernelFreeMemorySizeInfo system = {};
	system.size = sizeof(system);
	if (sceKernelGetFreeMemorySize(&system) < 0) {
		return false;
	}
	memory.available = true;
	memory.system_user_free = system.size_user;
	memory.system_cdram_free = system.size_cdram;
	memory.system_phycont_free = system.size_phycont;
	memory.ram_total = vglMemTotal(VGL_MEM_RAM);
	memory.ram_free = vglMemFree(VGL_MEM_RAM);
	memory.vram_total = vglMemTotal(VGL_MEM_VRAM);
	memory.vram_free = vglMemFree(VGL_MEM_VRAM);
	memory.slow_total = VitaGL_Phycont_Mem_Total();
	memory.slow_free = VitaGL_Phycont_Mem_Free();
	memory.all_total = vglMemTotal(VGL_MEM_ALL);
	memory.all_free = vglMemFree(VGL_MEM_ALL);
#endif
	return memory.available;
}

void Reset_Statistics()
{
#if defined(__vita__)
	g_mesh_expanded_corners = g_mesh_unique_vertices = g_mesh_indexed_batches = 0;
	g_material_skin_rgb_skips = 0U;
#endif
	const bool initialized = g_statistics.initialized;
	g_statistics = {};
	g_statistics.initialized = initialized;
	g_logged_first_unsupported = false;
	g_logged_first_indexed_rejection = false;
}

const Statistics &Get_Statistics()
{
	return g_statistics;
}

const BackendLifecycleStatistics &Get_Backend_Lifecycle_Statistics()
{
	return g_lifecycle;
}

} // namespace RenegadeVitaRenderer
