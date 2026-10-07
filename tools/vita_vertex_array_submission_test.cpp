// Host equivalence proof for vertex-array-v1 (per-frame mesh batches drawn from
// client arrays instead of per-vertex immediate calls).
//
// Compiles the production per-frame pass loop of Submit_Mesh_Internal together
// with the production Vertex_Array_Batch_Eligible / Draw_Vertex_Array_Batch
// against a GL shim, runs every fixture once with vertex arrays disabled
// (immediate or indexed-immediate, the reference) and once enabled, and
// requires byte equality of:
//   - the expanded corner stream of every non-empty draw (position, colour,
//     uv0/uv1 for each enabled texture unit, per emitted index),
//   - the ordered state-call sequence around the draws,
//   - the current colour/uv attributes observed at every state call and at
//     the end (immediate attributes persist across draws),
//   - the set of (pass, vertex, material, discarded-rgb) colour evaluations.
// It also checks the vitaGL contracts the array path relies on: no bound
// buffers, client texcoord arrays enabled for exactly the enabled texture
// units, attribute invalidation between array and immediate layouts, and no
// client arrays left enabled for following immediate draws.
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <set>
#include <string>
#include <tuple>
#include <vector>

#include "ww3d_vita_indexed_mesh_batch.h"
#include "ww3d_vita_vertex_array_batch.h"

static const char *g_fixture_name = "(none)";

#define CHECK(condition) \
	do { \
		if (!(condition)) { \
			std::fprintf(stderr, "%s:%d: fixture %s: CHECK failed: %s\n", \
				__FILE__, __LINE__, g_fixture_name, #condition); \
			std::exit(3); \
		} \
	} while (0)

#define RENEGADE_FRAME_PROFILE(name)
#define RENEGADE_VITA_M00_DEMO 0

// ---------------------------------------------------------------------------
// Mock WW3D / DX8 surface used by the production text.

typedef uint32_t DWORD;
typedef int GLsizei;
typedef unsigned GLenum;
typedef float GLfloat;
typedef int GLint;
typedef void GLvoid;
enum : DWORD {
	D3DTSS_TCI_PASSTHRU = 0x00000000U,
	D3DTSS_TCI_CAMERASPACENORMAL = 0x00010000U,
	D3DTTFF_DISABLE = 0U,
	D3DTTFF_COUNT1 = 1U,
	D3DTTFF_COUNT2 = 2U,
	D3DTTFF_COUNT3 = 3U,
	D3DTTFF_COUNT4 = 4U,
	D3DTTFF_PROJECTED = 256U,
};
enum : unsigned {
	GL_TEXTURE0 = 0x84C0U, GL_TEXTURE1 = 0x84C1U, GL_TRIANGLES = 4U,
	GL_FLOAT = 0x1406U, GL_UNSIGNED_SHORT = 0x1403U,
	GL_ARRAY_BUFFER = 0x8892U, GL_ELEMENT_ARRAY_BUFFER = 0x8893U,
	GL_VERTEX_ARRAY = 0x8074U, GL_COLOR_ARRAY = 0x8076U,
	GL_TEXTURE_COORD_ARRAY = 0x8078U,
};

struct Vector2 { float X, Y; };
struct Vector3 {
	float X, Y, Z;
	Vector3(float x = 0.0f, float y = 0.0f, float z = 0.0f) : X(x), Y(y), Z(z) {}
};
struct Matrix3D { float offset; };
struct RenderInfoClass { int id; };
struct MaterialLightDirections { int prepared = 0; };
struct Name {
	const char *text;
	const char *Peek_Buffer() const { return text; }
};
using TriIndex = std::array<uint16_t, 3>;

struct MeshMatDescClass { enum { MAX_PASSES = 4, MAX_TEX_STAGES = 2, MAX_UV_ARRAYS = 8 }; };

struct VertexMaterialClass {
	enum ColorSourceType { MATERIAL = 0, COLOR1 = 1, COLOR2 = 2 };
	unsigned id = 0U;
	int uv_source[2] = {-1, -1};
	DWORD mode[2] = {0U, 0U};
	DWORD flags[2] = {0U, 0U};
};

struct OriginalTextureCoordinateState {
	DWORD texcoord_index;
	DWORD texture_transform_flags;
};

enum : unsigned { SHADER_TEXTURING = 1U, SHADER_POST_DETAIL = 2U };
struct ShaderClass {
	enum { TEXTURING_ENABLE = 1 };
	unsigned bits;
	unsigned Get_Bits() const { return bits; }
	bool Uses_Post_Detail_Texture() const { return (bits & SHADER_POST_DETAIL) != 0U; }
	unsigned Get_Texturing() const { return bits & SHADER_TEXTURING; }
	int Get_Post_Detail_Color_Func() const { return static_cast<int>((bits >> 8) & 7U); }
	int Get_Post_Detail_Alpha_Func() const { return static_cast<int>((bits >> 11) & 7U); }
};

struct TextureClass {
	unsigned id;
	bool valid;
	Name Get_Texture_Name() const { return Name{"fixture-texture"}; }
	void Apply_For_Platform_Boundary(unsigned stage);
};

struct Fixture {
	std::string name;
	int vertex_count = 0;
	int pass_count = 1;
	bool is_skin = false;
	std::vector<Vector3> positions;
	std::vector<Vector3> normals;
	std::vector<TriIndex> triangles;
	std::vector<Vector2> uv_by_index[MeshMatDescClass::MAX_UV_ARRAYS];
	std::vector<Vector2> pass_uvs[MeshMatDescClass::MAX_PASSES][2];
	std::vector<unsigned> user_lighting;
	std::vector<unsigned> color_arrays[2];
	std::vector<unsigned> dcg[MeshMatDescClass::MAX_PASSES];
	VertexMaterialClass::ColorSourceType dcg_source[MeshMatDescClass::MAX_PASSES] = {
		VertexMaterialClass::COLOR1, VertexMaterialClass::COLOR2,
		VertexMaterialClass::MATERIAL, VertexMaterialClass::COLOR1
	};
	std::vector<TextureClass *> textures[MeshMatDescClass::MAX_PASSES][2];
	std::vector<VertexMaterialClass *> materials[MeshMatDescClass::MAX_PASSES];
	std::vector<unsigned> shaders[MeshMatDescClass::MAX_PASSES];
};

static const Fixture *g_fixture = nullptr;

template <typename T>
static const T *Data_Or_Null(const std::vector<T> &values)
{
	return values.empty() ? nullptr : values.data();
}

struct MeshModelClass {
	const Fixture *fixture;
	const Vector2 *Get_UV_Array(int pass, int stage) const {
		CHECK(pass >= 0 && pass < fixture->pass_count && stage >= 0 && stage < 2);
		return Data_Or_Null(fixture->pass_uvs[pass][stage]);
	}
	const Vector2 *Get_UV_Array_By_Index(int index) const {
		CHECK(index >= 0 && index < MeshMatDescClass::MAX_UV_ARRAYS);
		return Data_Or_Null(fixture->uv_by_index[index]);
	}
	const unsigned *Get_DCG_Array(int pass) const { return Data_Or_Null(fixture->dcg[pass]); }
	const unsigned *Get_Color_Array(int array, bool create) const {
		CHECK(!create && (array == 0 || array == 1));
		return Data_Or_Null(fixture->color_arrays[array]);
	}
	VertexMaterialClass::ColorSourceType Get_DCG_Source(int pass) const {
		return fixture->dcg_source[pass];
	}
};

struct MeshClass {
	const Fixture *fixture;
	const char *Get_Name() const { return fixture->name.c_str(); }
	const unsigned *Get_User_Lighting_Array(bool create) const {
		CHECK(!create);
		return Data_Or_Null(fixture->user_lighting);
	}
};

static uint32_t Mix(uint32_t value, uint32_t salt)
{
	value ^= salt * 0x9e3779b9U;
	value *= 0x85ebca6bU;
	value ^= value >> 13;
	value *= 0xc2b2ae35U;
	value ^= value >> 16;
	return value;
}

// [-0.25, 1.25): exercises both clamps.
static float Unit(uint32_t bits)
{
	return static_cast<float>(bits & 0x3ffU) / 682.0f - 0.25f;
}

struct MaterialVertexColor {
	Vector3 final_color;
	float alpha;
	bool lighting;
	unsigned light_count;
};

static const float kWorldOffset = 0.25f;
static const float kViewOffset = -0.5f;
static const int kRenderInfoId = 7;

// Production statistics/breadcrumb surface touched by the loop.
static unsigned g_render_work_cache_mode = 0U;
static VitaIndexedMeshBatch g_indexed_mesh_batch;
static uint64_t g_mesh_expanded_corners = 0U, g_mesh_unique_vertices = 0U;
static uint64_t g_mesh_indexed_batches = 0U;
static VitaVertexArrayBatch g_vertex_array_batch;
static bool g_vertex_array_enabled = false;
static bool g_logged_first_vertex_array_batch = false;
static uint64_t g_vertex_array_batches = 0U, g_vertex_array_corners = 0U;
static uint64_t g_vertex_array_vertices = 0U;
static bool g_logged_first_user_lighting = false;
static bool g_logged_first_skin_passthrough_texture_v_preserved = false;
static bool g_logged_first_stage1_mesh = false;
static bool g_logged_first_skin_texture_color = false;
static bool g_logged_first_material_lighting = false;
static bool g_logged_first_passthrough_texture_v_preserved = false;
static void Record_Breadcrumb(const char *tag, const char *format);
// First-occurrence breadcrumbs are part of the compared sequence; only the
// array path's own breadcrumb is mode specific.
template <class... Args>
void Vita_Append_A22_Runtime_Breadcrumb(const char *tag, const char *format, Args...)
{
	if (std::strcmp(tag, "vertex-array") != 0) Record_Breadcrumb(tag, format);
}
bool Is_Loading_Screen_Diagnostic_Name(const char *) { return false; }

static bool g_cache_material_colors = false;
bool Begin_Material_Color_Pass(int) { return g_cache_material_colors; }
void Prepare_Material_Light_Directions(const RenderInfoClass &render_info,
	MaterialLightDirections &directions, const Matrix3D *world)
{
	CHECK(render_info.id == kRenderInfoId && world != nullptr && world->offset == kWorldOffset);
	directions.prepared = 1;
}

// (pass, vertex, material id, discarded rgb, cached) of every evaluation.
static int g_current_pass = -1;
static std::set<std::tuple<int, unsigned, unsigned, bool, bool>> g_evaluations;

// Deterministic and sensitive to every input that selects a colour.
MaterialVertexColor Evaluate_Material_Vertex_Color(bool cache_material_colors,
	VertexMaterialClass *material, const unsigned *color1, const unsigned *color2,
	unsigned vertex_index, const Vector3 *normals, const Matrix3D &world_transform,
	const RenderInfoClass &render_info, MaterialLightDirections &directions,
	bool discarded_skin_rgb)
{
	CHECK(world_transform.offset == kWorldOffset && render_info.id == kRenderInfoId);
	CHECK(normals == g_fixture->normals.data());
	CHECK(vertex_index < static_cast<unsigned>(g_fixture->vertex_count));
	CHECK(directions.prepared == (cache_material_colors ? 1 : 0));
	CHECK(cache_material_colors == ((g_render_work_cache_mode & 2U) != 0U));
	const unsigned key = material != nullptr ? material->id : 0xffU;
	g_evaluations.insert(std::make_tuple(g_current_pass, vertex_index, key,
		discarded_skin_rgb, cache_material_colors));
	const uint32_t first = color1 != nullptr ? color1[vertex_index] : 0x5a5a5a5aU;
	const uint32_t second = color2 != nullptr ? color2[vertex_index] : 0x3c3c3c3cU;
	const uint32_t hash = Mix(vertex_index * 0x10001U + key, first ^ Mix(second, 3U));
	MaterialVertexColor result = {};
	result.final_color = Vector3(Unit(hash), Unit(hash >> 10), Unit(hash >> 20));
	result.alpha = Unit(hash >> 7);
	result.lighting = (key & 1U) != 0U;
	result.light_count = result.lighting ? 2U : 0U;
	if (result.lighting) {
		const Vector3 &normal = normals[vertex_index];
		result.final_color.X = result.final_color.X * 0.5f + normal.X;
		result.final_color.Y = result.final_color.Y * 0.5f + normal.Z;
	}
	// Production returns white RGB for a discarded skin colour only with the
	// render work cache enabled; otherwise the caller's override applies.
	if (discarded_skin_rgb && (g_render_work_cache_mode & 2U) != 0U)
		result.final_color = Vector3(1.0f, 1.0f, 1.0f);
	return result;
}

float Clamp01(float value)
{
	return value < 0.0f ? 0.0f : (value > 1.0f ? 1.0f : value);
}

DWORD Texture_Coordinate_Mode(const OriginalTextureCoordinateState &state)
{
	return state.texcoord_index & 0xffff0000U;
}

const Vector2 *Resolve_UV_Array_For_Texture_State(MeshModelClass *model,
	const OriginalTextureCoordinateState &state, const Vector2 *fallback)
{
	const int uv_source = static_cast<int>(state.texcoord_index & 0xffffU);
	if (uv_source >= 0 && uv_source < MeshMatDescClass::MAX_UV_ARRAYS) {
		const Vector2 *uvs = model->Get_UV_Array_By_Index(uv_source);
		if (uvs != nullptr) return uvs;
	}
	return fallback;
}

// ---------------------------------------------------------------------------
// GL / DX8 shim.

struct NativeTextureStageCache {
	bool enabled_known;
	bool enabled;
};
static NativeTextureStageCache g_texture_stage_cache[MeshMatDescClass::MAX_TEX_STAGES];

struct Corner {
	float position[3];
	float color[4];
	float uv[2][2];
	bool has_uv[2];
};

static bool Same_Bytes(const Corner &left, const Corner &right)
{
	if (left.has_uv[0] != right.has_uv[0] || left.has_uv[1] != right.has_uv[1]) return false;
	if (std::memcmp(left.position, right.position, sizeof(left.position)) != 0) return false;
	if (std::memcmp(left.color, right.color, sizeof(left.color)) != 0) return false;
	for (unsigned stage = 0U; stage < 2U; ++stage) {
		if (left.has_uv[stage] &&
			std::memcmp(left.uv[stage], right.uv[stage], sizeof(left.uv[stage])) != 0) return false;
	}
	return true;
}

struct Event {
	std::string call;
	// Current immediate attributes when the call happened (non-draw events).
	float color[4];
	float uv[2][2];
	std::vector<Corner> corners;
	bool draw = false;
};

struct Recording {
	std::vector<Event> events;
	unsigned immediate_draws = 0U;
	unsigned array_draws = 0U;
	std::set<std::tuple<int, unsigned, unsigned, bool, bool>> evaluations;
};

static Recording *g_recording = nullptr;
static OriginalTextureCoordinateState g_dx8_coordinates[2];
static bool g_unit_enabled[2];
static float g_color[4];
static float g_uv[2][2];
static bool g_primitive_open = false;
static std::vector<Corner> g_immediate_vertices;
enum Layout { LAYOUT_INVALID, LAYOUT_IMMEDIATE, LAYOUT_ARRAY };
static Layout g_layout = LAYOUT_INVALID;
static bool g_client_vertex = false, g_client_color = false, g_client_texture[2] = {};
static unsigned g_client_unit = 0U;
static const float *g_vertex_pointer = nullptr, *g_color_pointer = nullptr;
static const float *g_texture_pointer[2] = {};
static unsigned g_bound_buffer[2] = {};

static void Record(const std::string &call)
{
	CHECK(!g_primitive_open);
	Event event;
	event.call = call;
	std::memcpy(event.color, g_color, sizeof(g_color));
	std::memcpy(event.uv, g_uv, sizeof(g_uv));
	g_recording->events.push_back(event);
}

static void Record_Breadcrumb(const char *tag, const char *format)
{
	Event event;
	event.call = std::string("breadcrumb ") + tag + " " + format;
	std::memcpy(event.color, g_color, sizeof(g_color));
	std::memcpy(event.uv, g_uv, sizeof(g_uv));
	g_recording->events.push_back(event);
}

static void Reset_Shim()
{
	for (unsigned stage = 0U; stage < 2U; ++stage) {
		g_dx8_coordinates[stage].texcoord_index = D3DTSS_TCI_PASSTHRU | stage;
		g_dx8_coordinates[stage].texture_transform_flags = D3DTTFF_DISABLE;
		g_unit_enabled[stage] = false;
		g_texture_stage_cache[stage] = NativeTextureStageCache{true, false};
		g_client_texture[stage] = false;
		g_texture_pointer[stage] = nullptr;
	}
	for (unsigned i = 0U; i < 4U; ++i) g_color[i] = 0.125f * static_cast<float>(i + 1U);
	g_uv[0][0] = 0.5f; g_uv[0][1] = -0.5f; g_uv[1][0] = 0.25f; g_uv[1][1] = -0.25f;
	g_primitive_open = false;
	g_immediate_vertices.clear();
	g_layout = LAYOUT_INVALID;
	g_client_vertex = g_client_color = false;
	g_client_unit = 0U;
	g_vertex_pointer = g_color_pointer = nullptr;
	g_bound_buffer[0] = g_bound_buffer[1] = 0U;
	g_indexed_mesh_batch.Reset();
}

static void Set_Unit(unsigned stage, bool enabled)
{
	g_unit_enabled[stage] = enabled;
	g_texture_stage_cache[stage] = NativeTextureStageCache{true, enabled};
}

void TextureClass::Apply_For_Platform_Boundary(unsigned stage)
{
	CHECK(stage < 2U);
	Set_Unit(stage, valid);
	Record("texture " + std::to_string(stage) + " " + std::to_string(id));
}

void Bind_Texture(unsigned stage, bool valid)
{
	CHECK(stage == 0U && !valid);
	Set_Unit(0U, false);
	Record("bind0 off");
}

void Disable_Texture_Stage(unsigned stage)
{
	CHECK(stage == 1U);
	Set_Unit(1U, false);
	Record("disable1");
}

void Apply_Original_Shader_State(ShaderClass shader)
{
	Set_Unit(0U, shader.Get_Texturing() != 0U);
	Record("shader " + std::to_string(shader.Get_Bits()));
}

void Apply_Original_Texture_Stage_State(ShaderClass shader, bool texture0, bool detail)
{
	Record("stage-state " + std::to_string(shader.Get_Bits()) + " " +
		std::to_string(texture0) + std::to_string(detail));
}

void Apply_Original_Texture_Coordinate_State(VertexMaterialClass *material)
{
	for (unsigned stage = 0U; stage < 2U; ++stage) {
		const int source = material != nullptr && material->uv_source[stage] >= 0 ?
			material->uv_source[stage] : static_cast<int>(stage);
		g_dx8_coordinates[stage].texcoord_index = static_cast<DWORD>(source) |
			(material != nullptr ? material->mode[stage] : 0U);
		g_dx8_coordinates[stage].texture_transform_flags =
			material != nullptr ? material->flags[stage] : D3DTTFF_DISABLE;
	}
	Record("coordinates " + std::to_string(material != nullptr ? material->id : 0xffU));
}

void Capture_Original_Texture_Coordinate_State(unsigned stage,
	OriginalTextureCoordinateState *state)
{
	CHECK(stage < 2U);
	*state = g_dx8_coordinates[stage];
}

bool Emit_Original_Texture_Coordinate(unsigned stage, unsigned texture_unit,
	const OriginalTextureCoordinateState &state, const Vector2 *uvs, const Vector3 *,
	const Vector3 *, unsigned vertex_index, const Matrix3D &world_transform,
	const Matrix3D &view_transform, const char *)
{
	CHECK(stage < 2U && texture_unit == (stage == 0U ? GL_TEXTURE0 : GL_TEXTURE1));
	CHECK(world_transform.offset == kWorldOffset && view_transform.offset == kViewOffset);
	if (uvs == nullptr) return false;
	if (Texture_Coordinate_Mode(state) == D3DTSS_TCI_PASSTHRU &&
		state.texture_transform_flags == D3DTTFF_DISABLE) {
		if (!g_logged_first_passthrough_texture_v_preserved) {
			Record_Breadcrumb("mesh-submit", "first gameplay passthrough texture V preserved");
			g_logged_first_passthrough_texture_v_preserved = true;
		}
		g_uv[stage][0] = uvs[vertex_index].X;
		g_uv[stage][1] = uvs[vertex_index].Y;
		return true;
	}
	// Stand-in for generated/transformed coordinates: any distinct function.
	g_uv[stage][0] = uvs[vertex_index].X * 2.0f + 0.125f;
	g_uv[stage][1] = uvs[vertex_index].Y * -3.0f;
	return true;
}

void glColor4f(float r, float g, float b, float a)
{
	g_color[0] = r; g_color[1] = g; g_color[2] = b; g_color[3] = a;
}

void glMultiTexCoord2f(unsigned unit, float s, float t)
{
	CHECK(unit == GL_TEXTURE0 || unit == GL_TEXTURE1);
	g_uv[unit - GL_TEXTURE0][0] = s;
	g_uv[unit - GL_TEXTURE0][1] = t;
}

static void Open_Immediate()
{
	CHECK(!g_primitive_open);
	CHECK(!g_client_vertex && !g_client_color && !g_client_texture[0] && !g_client_texture[1]);
	g_primitive_open = true;
	g_immediate_vertices.clear();
}

void Begin_Texture_Coordinate_Primitive(const OriginalTextureCoordinateState *states)
{
	(void)states;
	Open_Immediate();
}

void glVertex3f(float x, float y, float z)
{
	CHECK(g_primitive_open);
	Corner corner;
	std::memset(&corner, 0, sizeof(corner));
	corner.position[0] = x; corner.position[1] = y; corner.position[2] = z;
	std::memcpy(corner.color, g_color, sizeof(g_color));
	for (unsigned stage = 0U; stage < 2U; ++stage) {
		corner.has_uv[stage] = g_unit_enabled[stage];
		if (corner.has_uv[stage]) std::memcpy(corner.uv[stage], g_uv[stage], sizeof(g_uv[stage]));
	}
	g_immediate_vertices.push_back(corner);
}

static void Close_Immediate(const std::vector<Corner> &corners)
{
	CHECK(g_primitive_open);
	CHECK(g_layout != LAYOUT_ARRAY);
	g_layout = LAYOUT_IMMEDIATE;
	g_primitive_open = false;
	if (corners.empty()) return;
	Event event;
	event.call = "draw";
	event.draw = true;
	event.corners = corners;
	g_recording->events.push_back(event);
	++g_recording->immediate_draws;
}

void glEnd()
{
	Close_Immediate(g_immediate_vertices);
}

void vglRenegadeEndIndexed(int count, const uint16_t *indices)
{
	std::vector<Corner> corners;
	for (int i = 0; i < count; ++i) {
		CHECK(indices[i] < g_immediate_vertices.size());
		corners.push_back(g_immediate_vertices[indices[i]]);
	}
	Close_Immediate(corners);
}

void vglRenegadeInvalidateVertexAttributes() { g_layout = LAYOUT_INVALID; }
void glBindBuffer(unsigned target, unsigned buffer)
{
	CHECK(target == GL_ARRAY_BUFFER || target == GL_ELEMENT_ARRAY_BUFFER);
	g_bound_buffer[target == GL_ARRAY_BUFFER ? 0 : 1] = buffer;
}
static bool *Client_Flag(unsigned array)
{
	if (array == GL_VERTEX_ARRAY) return &g_client_vertex;
	if (array == GL_COLOR_ARRAY) return &g_client_color;
	CHECK(array == GL_TEXTURE_COORD_ARRAY);
	return &g_client_texture[g_client_unit];
}
void glEnableClientState(unsigned array) { CHECK(!g_primitive_open); *Client_Flag(array) = true; }
void glDisableClientState(unsigned array) { CHECK(!g_primitive_open); *Client_Flag(array) = false; }
void glClientActiveTexture(unsigned unit)
{
	CHECK(unit == GL_TEXTURE0 || unit == GL_TEXTURE1);
	g_client_unit = unit - GL_TEXTURE0;
}
void glVertexPointer(int size, unsigned type, int stride, const void *pointer)
{
	CHECK(size == 3 && type == GL_FLOAT && stride == 0 && g_bound_buffer[0] == 0U);
	g_vertex_pointer = static_cast<const float *>(pointer);
}
void glColorPointer(int size, unsigned type, int stride, const void *pointer)
{
	CHECK(size == 4 && type == GL_FLOAT && stride == 0 && g_bound_buffer[0] == 0U);
	g_color_pointer = static_cast<const float *>(pointer);
}
void glTexCoordPointer(int size, unsigned type, int stride, const void *pointer)
{
	CHECK(size == 2 && type == GL_FLOAT && stride == 0 && g_bound_buffer[0] == 0U);
	g_texture_pointer[g_client_unit] = static_cast<const float *>(pointer);
}
void glDrawElements(unsigned mode, int count, unsigned type, const void *pointer)
{
	CHECK(!g_primitive_open && mode == GL_TRIANGLES && type == GL_UNSIGNED_SHORT);
	CHECK(count > 0 && count % 3 == 0);
	CHECK(g_bound_buffer[0] == 0U && g_bound_buffer[1] == 0U);
	CHECK(g_client_vertex && g_client_color);
	// vitaGL builds the client-array layout from the enabled units; a texcoord
	// array must exist for exactly the units the immediate layout would use.
	CHECK(g_client_texture[0] == g_unit_enabled[0]);
	CHECK(g_client_texture[1] == g_unit_enabled[1]);
	CHECK(g_layout != LAYOUT_IMMEDIATE);
	g_layout = LAYOUT_ARRAY;
	const uint16_t *indices = static_cast<const uint16_t *>(pointer);
	Event event;
	event.call = "draw";
	event.draw = true;
	for (int i = 0; i < count; ++i) {
		const unsigned index = indices[i];
		Corner corner;
		std::memset(&corner, 0, sizeof(corner));
		std::memcpy(corner.position, g_vertex_pointer + index * 3U, sizeof(corner.position));
		std::memcpy(corner.color, g_color_pointer + index * 4U, sizeof(corner.color));
		for (unsigned stage = 0U; stage < 2U; ++stage) {
			corner.has_uv[stage] = g_client_texture[stage];
			if (corner.has_uv[stage])
				std::memcpy(corner.uv[stage], g_texture_pointer[stage] + index * 2U,
					sizeof(corner.uv[stage]));
		}
		event.corners.push_back(corner);
	}
	g_recording->events.push_back(event);
	++g_recording->array_draws;
}

// ---------------------------------------------------------------------------
// Production text under test.

#define __vita__ 1
#include "vertex-array-helpers.inc"
#undef __vita__

static void Run_Pass_Loop(MeshModelClass *model, MeshClass &mesh,
	RenderInfoClass &render_info, const Fixture &fixture)
{
	const Vector3 *vertices = fixture.positions.data();
	const Vector3 *normals = fixture.normals.data();
	const TriIndex *triangles = fixture.triangles.data();
	const int vertex_count = fixture.vertex_count;
	const int submitted_triangle_count = static_cast<int>(fixture.triangles.size());
	const bool is_skin = fixture.is_skin;
	const bool procedural_pass = false;
	const int draw_pass_count = fixture.pass_count;
	const Matrix3D original_world_transform = {kWorldOffset};
	const Matrix3D original_view_transform = {kViewOffset};
	const auto triangle_at = [](int draw_index) { return draw_index; };
	const auto texture_for = [&fixture](int triangle, int pass, int stage) {
		g_current_pass = pass;
		return fixture.textures[pass][stage][triangle];
	};
	const auto shader_for = [&fixture](int triangle, int pass) {
		return ShaderClass{fixture.shaders[pass][triangle]};
	};
	const auto material_for = [&fixture](int vertex, int pass) {
		CHECK(vertex >= 0 && vertex < fixture.vertex_count);
		return fixture.materials[pass][vertex];
	};
#define __vita__ 1
#include "pass-loop-production.inc"
#undef __vita__
	Record("end");
}

// ---------------------------------------------------------------------------
// Fixtures.

struct World {
	std::vector<TextureClass> textures;
	std::vector<VertexMaterialClass> materials;
};

static uint32_t g_seed = 1U;
static uint32_t Next() { g_seed = Mix(g_seed, 0x51ed270bU); return g_seed; }

static Fixture Make_Fixture(const char *name, const World &world, uint32_t seed,
	bool is_skin, int vertex_count, int triangle_count, int pass_count, bool with_invalid)
{
	g_seed = seed;
	Fixture f;
	f.name = name;
	f.is_skin = is_skin;
	f.vertex_count = vertex_count;
	f.pass_count = pass_count;
	for (int v = 0; v < vertex_count; ++v) {
		f.positions.push_back(Vector3(Unit(Next()) * 9.0f, Unit(Next()) * 7.0f, Unit(Next())));
		f.normals.push_back(Vector3(Unit(Next()), Unit(Next()), Unit(Next())));
		f.color_arrays[0].push_back(Next());
		f.color_arrays[1].push_back(Next());
	}
	for (int index = 0; index < MeshMatDescClass::MAX_UV_ARRAYS; ++index) {
		if (index == 5) continue;  // a material UV source with no array falls back
		for (int v = 0; v < vertex_count; ++v)
			f.uv_by_index[index].push_back(Vector2{Unit(Next()) * 4.0f, Unit(Next()) * 3.0f});
	}
	for (int pass = 0; pass < pass_count; ++pass) {
		for (int stage = 0; stage < 2; ++stage)
			for (int v = 0; v < vertex_count; ++v)
				f.pass_uvs[pass][stage].push_back(Vector2{Unit(Next()), Unit(Next())});
		for (int v = 0; v < vertex_count; ++v)
			f.dcg[pass].push_back(Next());
		for (int v = 0; v < vertex_count; ++v) {
			const uint32_t pick = Next() % (world.materials.size() + 1U);
			f.materials[pass].push_back(pick == world.materials.size() ? nullptr :
				const_cast<VertexMaterialClass *>(&world.materials[pick]));
		}
	}
	for (int t = 0; t < triangle_count; ++t) {
		TriIndex triangle;
		for (int c = 0; c < 3; ++c)
			triangle[c] = static_cast<uint16_t>(Next() % static_cast<uint32_t>(vertex_count));
		if (with_invalid && Next() % 17U == 0U)
			triangle[Next() % 3U] = static_cast<uint16_t>(vertex_count + Next() % 3U);
		f.triangles.push_back(triangle);
	}
	// Runs of identical state so batches span several triangles.
	for (int pass = 0; pass < pass_count; ++pass) {
		int run = 0;
		TextureClass *t0 = nullptr, *t1 = nullptr;
		unsigned shader = 0U;
		for (int t = 0; t < triangle_count; ++t) {
			if (run-- <= 0) {
				run = static_cast<int>(Next() % 12U);
				const uint32_t pick0 = Next() % (world.textures.size() + 2U);
				t0 = pick0 >= world.textures.size() ? nullptr :
					const_cast<TextureClass *>(&world.textures[pick0]);
				const uint32_t pick1 = Next() % (world.textures.size() + 3U);
				t1 = pick1 >= world.textures.size() ? nullptr :
					const_cast<TextureClass *>(&world.textures[pick1]);
				shader = (Next() % 5U == 0U ? 0U : SHADER_TEXTURING) |
					(Next() % 2U == 0U ? SHADER_POST_DETAIL : 0U) | ((Next() % 3U) << 8);
			}
			f.textures[pass][0].push_back(t0);
			f.textures[pass][1].push_back(t1);
			f.shaders[pass].push_back(shader);
		}
	}
	return f;
}

struct Options {
	bool indexed;
	bool cache_colors;
	bool logged;
};

static Recording Run(const Fixture &fixture, const Options &options, bool arrays)
{
	Recording recording;
	g_recording = &recording;
	g_fixture = &fixture;
	Reset_Shim();
	g_render_work_cache_mode = (options.indexed ? 8U : 0U) | (options.cache_colors ? 2U : 0U);
	g_cache_material_colors = options.cache_colors;
	g_vertex_array_enabled = arrays;
	g_logged_first_material_lighting = options.logged;
	g_logged_first_skin_texture_color = options.logged;
	g_logged_first_passthrough_texture_v_preserved = options.logged;
	g_logged_first_user_lighting = g_logged_first_skin_passthrough_texture_v_preserved =
		g_logged_first_stage1_mesh = options.logged;
	g_evaluations.clear();
	MeshModelClass model = {&fixture};
	MeshClass mesh = {&fixture};
	RenderInfoClass render_info = {kRenderInfoId};
	Run_Pass_Loop(&model, mesh, render_info, fixture);
	CHECK(g_vertex_array_batch.Vertices() == 0U && g_vertex_array_batch.Count() == 0U);
	recording.evaluations = g_evaluations;
	g_recording = nullptr;
	return recording;
}

static void Compare(const Recording &reference, const Recording &arrays)
{
	CHECK(reference.array_draws == 0U);
	CHECK(reference.events.size() == arrays.events.size());
	for (size_t i = 0U; i < reference.events.size(); ++i) {
		const Event &left = reference.events[i];
		const Event &right = arrays.events[i];
		if (left.call != right.call) {
			std::fprintf(stderr, "event %zu: '%s' vs '%s'\n", i, left.call.c_str(), right.call.c_str());
		}
		CHECK(left.call == right.call && left.draw == right.draw);
		if (!left.draw) {
			if (std::memcmp(left.color, right.color, sizeof(left.color)) != 0 ||
				std::memcmp(left.uv, right.uv, sizeof(left.uv)) != 0)
				std::fprintf(stderr, "event %zu (%s): current attributes differ\n", i, left.call.c_str());
			CHECK(std::memcmp(left.color, right.color, sizeof(left.color)) == 0);
			CHECK(std::memcmp(left.uv, right.uv, sizeof(left.uv)) == 0);
			continue;
		}
		CHECK(left.corners.size() == right.corners.size());
		for (size_t c = 0U; c < left.corners.size(); ++c) {
			if (!Same_Bytes(left.corners[c], right.corners[c]))
				std::fprintf(stderr, "event %zu corner %zu differs\n", i, c);
			CHECK(Same_Bytes(left.corners[c], right.corners[c]));
		}
	}
	CHECK(reference.evaluations == arrays.evaluations);
}

int main()
{
	World world;
	world.textures = {
		TextureClass{1U, true}, TextureClass{2U, true}, TextureClass{3U, true},
		TextureClass{4U, false},  // failed texture: unit stays disabled
	};
	world.materials.resize(6);
	for (unsigned i = 0U; i < world.materials.size(); ++i) world.materials[i].id = i + 1U;
	world.materials[1].uv_source[0] = 3;
	world.materials[1].uv_source[1] = 6;
	world.materials[2].uv_source[1] = 5;  // no such array: falls back
	world.materials[3].mode[0] = D3DTSS_TCI_CAMERASPACENORMAL;  // generated stage 0
	world.materials[4].flags[1] = D3DTTFF_COUNT3 | D3DTTFF_PROJECTED;  // projective stage 1
	world.materials[5].flags[0] = D3DTTFF_COUNT2;  // transformed stage 0

	struct Shape { const char *name; uint32_t seed; bool skin; int vertices, triangles, passes; bool invalid; };
	const Shape shapes[] = {
		{"rigid-small", 11U, false, 24, 60, 1, false},
		{"rigid-multipass", 23U, false, 48, 160, 2, true},
		{"skin", 37U, true, 64, 220, 2, true},
		{"skin-large", 41U, true, 400, 1200, 1, false},
		{"rigid-large", 53U, false, 600, 1800, 3, true},
	};
	unsigned compared = 0U, array_draws = 0U, immediate_with_arrays = 0U;
	for (const Shape &shape : shapes) {
		const Fixture fixture = Make_Fixture(shape.name, world, shape.seed, shape.skin,
			shape.vertices, shape.triangles, shape.passes, shape.invalid);
		g_fixture_name = shape.name;
		for (unsigned mode = 0U; mode < 8U; ++mode) {
			const Options options = {(mode & 1U) != 0U, (mode & 2U) != 0U, (mode & 4U) != 0U};
			const Recording reference = Run(fixture, options, false);
			const Recording arrays = Run(fixture, options, true);
			Compare(reference, arrays);
			if (options.logged) {
				CHECK(arrays.array_draws != 0U);
				// Ineligible batches (generated, transformed or projective
				// coordinates, failed textures) must stay immediate.
				CHECK(arrays.immediate_draws != 0U);
			} else {
				// Pending first-occurrence breadcrumbs keep at least the first
				// batch immediate.
				CHECK(arrays.immediate_draws != 0U);
			}
			array_draws += arrays.array_draws;
			immediate_with_arrays += arrays.immediate_draws;
			++compared;
		}
	}
	// Index storage and remap reuse across meshes of different sizes.
	{
		VitaVertexArrayBatch batch;
		CHECK(!batch.Reserve(70000U, 3U));
		CHECK(!batch.Reserve(10U, 0U));
		CHECK(batch.Reserve(65535U, 6U));
		uint32_t slot = 0U;
		CHECK(batch.Append(65534U, &slot) && slot == 0U);
		CHECK(batch.Append(7U, &slot) && slot == 1U);
		CHECK(!batch.Append(65534U, &slot) && slot == 0U && batch.Last_Slot() == 0U);
		CHECK(batch.Count() == 3U && batch.Vertices() == 2U);
		batch.Reset();
		CHECK(batch.Append(7U, &slot) && slot == 0U);
		batch.Reset();
		CHECK(batch.Reserve(10U, 3U) && batch.Append(9U, &slot) && slot == 0U);
	}
	std::printf("vertex array submission equivalence: %u runs compared, %u array draws, %u immediate draws in array mode\n",
		compared, array_draws, immediate_with_arrays);
	return 0;
}
