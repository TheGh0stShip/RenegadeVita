// Host equivalence proof for the GPU-resident static mesh cache.
//
// Compiles the production Build_Static_Mesh_Streams (with its production
// material snapshot and pass-through helpers) and the production immediate
// Submit_Mesh pass loop against deterministic mocks. For every fixture it
// checks that
//   (a) the cached batches, expanded index by index through their windows,
//   (b) an independent walk of the fixture that follows the original
//       immediate traversal rules, and
//   (c) the stream the production immediate loop records between each
//       glBegin/glEnd
// agree corner by corner, including the state each corner is drawn with, and
// that cached batches split only at original primitive boundaries or at the
// 16-bit vertex limit. Lit colours are cached like unlit ones, and the builder
// must report uses_lighting exactly when an emitted vertex was lit. Ineligible
// fixtures must be rejected without being mistaken for allocation failures.
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <set>
#include <string>
#include <vector>

#include "ww3d_vita_indexed_mesh_batch.h"
#include "ww3d_vita_static_mesh_cache.h"

using namespace RenegadeVitaRenderer;

static const char *g_fixture_name = "(none)";

#define CHECK(condition) \
	do { \
		if (!(condition)) { \
			std::fprintf(stderr, "%s:%d: fixture %s: CHECK failed: %s\n", \
				__FILE__, __LINE__, g_fixture_name, #condition); \
			std::abort(); \
		} \
	} while (0)

// ---------------------------------------------------------------------------
// Mock WW3D / DX8 surface used by the production text.

typedef uint32_t DWORD;
enum : DWORD {
	D3DTSS_TCI_PASSTHRU = 0x00000000U,
	D3DTSS_TCI_CAMERASPACENORMAL = 0x00010000U,
	D3DTSS_TCI_CAMERASPACEPOSITION = 0x00020000U,
	D3DTTFF_DISABLE = 0U,
	D3DTTFF_COUNT2 = 2U,
};
enum : unsigned { GL_TEXTURE0 = 0x84C0U, GL_TEXTURE1 = 0x84C1U, GL_TRIANGLES = 4U };

struct Vector2 { float X, Y; };
struct Vector3 {
	float X, Y, Z;
	Vector3(float x = 0.0f, float y = 0.0f, float z = 0.0f) : X(x), Y(y), Z(z) {}
};
struct Matrix3D { float offset; };
struct RenderInfoClass { int id; };
struct MaterialLightDirections {};
struct Name { const char *Peek_Buffer() const { return "fixture"; } };
struct TextureMapperClass { DWORD mode; DWORD flags; };
using TriIndex = std::array<uint16_t, 3>;

struct MeshMatDescClass { enum { MAX_PASSES = 4, MAX_TEX_STAGES = 2, MAX_UV_ARRAYS = 8 }; };

struct VertexMaterialClass {
	enum ColorSourceType { MATERIAL = 0, COLOR1 = 1, COLOR2 = 2 };
	unsigned id = 0U;
	bool lighting = false;
	Vector3 diffuse = Vector3(1.0f, 1.0f, 1.0f);
	Vector3 ambient = Vector3(1.0f, 1.0f, 1.0f);
	Vector3 emissive = Vector3(0.0f, 0.0f, 0.0f);
	float opacity = 1.0f;
	ColorSourceType diffuse_source = MATERIAL;
	ColorSourceType ambient_source = MATERIAL;
	ColorSourceType emissive_source = MATERIAL;
	TextureMapperClass *mapper[2] = {nullptr, nullptr};
	int uv_source[2] = {-1, -1};
	// Test-only: DX8 coordinate state a mapper-less stage of this material
	// leaves behind. Reaches the builder's pass-through guard independently of
	// its mapper guard (production Apply always writes pass-through here).
	DWORD forced_mode[2] = {0U, 0U};
	DWORD forced_flags[2] = {0U, 0U};

	void Get_Diffuse(Vector3 *value) const { *value = diffuse; }
	void Get_Ambient(Vector3 *value) const { *value = ambient; }
	void Get_Emissive(Vector3 *value) const { *value = emissive; }
	float Get_Opacity() const { return opacity; }
	bool Get_Lighting() const { return lighting; }
	ColorSourceType Get_Diffuse_Color_Source() const { return diffuse_source; }
	ColorSourceType Get_Ambient_Color_Source() const { return ambient_source; }
	ColorSourceType Get_Emissive_Color_Source() const { return emissive_source; }
	TextureMapperClass *Peek_Mapper(int stage) const { return mapper[stage]; }
	int Get_UV_Source(int stage) const { return uv_source[stage]; }
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
	Name Get_Texture_Name() const { return Name(); }
	void Apply_For_Platform_Boundary(unsigned stage);
};

struct Fixture {
	std::string name;
	int vertex_count = 0;
	int pass_count = 1;
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
	bool expect_eligible = true;
	bool expect_uses_lighting = false;
	size_t expect_windows = 1U;
	size_t expect_splits = 0U;
	// Material whose state produced an ineligible verdict. The builder must
	// keep its snapshot so a later change to it reconsiders the entry.
	const VertexMaterialClass *verdict_material = nullptr;
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
	const unsigned *Get_DCG_Array(int pass) const {
		CHECK(pass >= 0 && pass < fixture->pass_count);
		return Data_Or_Null(fixture->dcg[pass]);
	}
	const unsigned *Get_Color_Array(int array, bool create) const {
		CHECK(!create && (array == 0 || array == 1));
		return Data_Or_Null(fixture->color_arrays[array]);
	}
	VertexMaterialClass::ColorSourceType Get_DCG_Source(int pass) const {
		CHECK(pass >= 0 && pass < fixture->pass_count);
		return fixture->dcg_source[pass];
	}
	TextureClass *Peek_Texture(int triangle, int pass, int stage) const {
		CHECK(pass >= 0 && pass < fixture->pass_count && stage >= 0 && stage < 2);
		CHECK(triangle >= 0 && triangle < static_cast<int>(fixture->triangles.size()));
		return fixture->textures[pass][stage][triangle];
	}
	VertexMaterialClass *Peek_Material(int vertex, int pass) const {
		// Production never asks for the material of an invalid vertex.
		CHECK(vertex >= 0 && vertex < fixture->vertex_count);
		CHECK(pass >= 0 && pass < fixture->pass_count);
		return fixture->materials[pass][vertex];
	}
	ShaderClass Get_Shader(int triangle, int pass) const {
		CHECK(pass >= 0 && pass < fixture->pass_count);
		CHECK(triangle >= 0 && triangle < static_cast<int>(fixture->triangles.size()));
		return ShaderClass{fixture->shaders[pass][triangle]};
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

// [-0.25, 1.25): exercises both clamps of the byte quantization.
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
static uint64_t g_color_evaluations = 0U;

// Deterministic and sensitive to every input that selects a color: the
// material, the vertex, and both pass-selected color arrays.
MaterialVertexColor Evaluate_Original_Material_Vertex_Color(
	VertexMaterialClass *material, const unsigned *color1, const unsigned *color2,
	unsigned vertex_index, const Vector3 *normals, const Matrix3D &world_transform,
	const RenderInfoClass &render_info, const MaterialLightDirections *light_directions)
{
	CHECK(light_directions == nullptr);
	CHECK(world_transform.offset == kWorldOffset);
	CHECK(render_info.id == kRenderInfoId);
	CHECK(normals == g_fixture->normals.data());
	CHECK(vertex_index < static_cast<unsigned>(g_fixture->vertex_count));
	++g_color_evaluations;
	const uint32_t first = color1 != nullptr ? color1[vertex_index] : 0x5a5a5a5aU;
	const uint32_t second = color2 != nullptr ? color2[vertex_index] : 0x3c3c3c3cU;
	const uint32_t key = material != nullptr ? material->id : 0xffU;
	const uint32_t hash = Mix(vertex_index * 0x10001U + key, first ^ Mix(second, 3U));
	const Vector3 tint = material != nullptr ? material->diffuse : Vector3(1.0f, 1.0f, 1.0f);
	MaterialVertexColor result = {};
	result.final_color = Vector3(Unit(hash) * tint.X, Unit(hash >> 10) * tint.Y,
		Unit(hash >> 20) * tint.Z);
	result.alpha = Unit(hash >> 7) * (material != nullptr ? material->opacity : 1.0f);
	result.lighting = material != nullptr && material->lighting;
	result.light_count = 0U;
	if (result.lighting) {
		// Lit colours additionally read the vertex normal and world transform.
		const Vector3 &normal = normals[vertex_index];
		result.final_color = Vector3(result.final_color.X * 0.5f + normal.X,
			result.final_color.Y * 0.5f + normal.Z * world_transform.offset,
			result.final_color.Z * 0.25f + normal.Y * 0.375f);
		result.light_count = 2U;
	}
	return result;
}

// Mirrors the production helper of the same name.
int Get_Original_UV_Source(VertexMaterialClass *material, unsigned stage)
{
	const int fallback_uv_source = static_cast<int>(stage);
	if (material == nullptr) return fallback_uv_source;
	const int uv_source = material->Get_UV_Source(static_cast<int>(stage));
	return uv_source >= 0 ? uv_source : fallback_uv_source;
}

DWORD Texture_Coordinate_Mode(const OriginalTextureCoordinateState &state)
{
	return state.texcoord_index & 0xffff0000U;
}

// Mirrors the production resolution of a stage's UV source index.
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
// GL / DX8 state recorders shared by the builder and the immediate loop.

struct DrawState {
	const void *texture0 = nullptr;
	const void *texture1 = nullptr;
	const void *material = nullptr;
	uint32_t shader_bits = 0U;
	bool detail = false;
};

static bool Same_State(const DrawState &left, const DrawState &right)
{
	return left.texture0 == right.texture0 && left.texture1 == right.texture1 &&
		left.material == right.material && left.shader_bits == right.shader_bits &&
		left.detail == right.detail;
}

struct Corner {
	DrawState state;
	float position[3] = {};
	uint8_t color[4] = {};
	bool has_uv0 = false;
	bool has_uv1 = false;
	float uv0[2] = {};
	float uv1[2] = {};
};

static bool Same_Corner(const Corner &left, const Corner &right)
{
	if (!Same_State(left.state, right.state)) return false;
	for (unsigned i = 0U; i < 3U; ++i) {
		if (left.position[i] != right.position[i]) return false;
	}
	for (unsigned i = 0U; i < 4U; ++i) {
		if (left.color[i] != right.color[i]) return false;
	}
	if (left.has_uv0 != right.has_uv0 || left.has_uv1 != right.has_uv1) return false;
	if (left.has_uv0 && (left.uv0[0] != right.uv0[0] || left.uv0[1] != right.uv0[1])) return false;
	if (left.has_uv1 && (left.uv1[0] != right.uv1[0] || left.uv1[1] != right.uv1[1])) return false;
	return true;
}

struct ImmediateDraw {
	DrawState state;
	std::vector<Corner> corners;
};

static OriginalTextureCoordinateState g_dx8_coordinates[2];
static DrawState g_bound;
static bool g_stage_state_complete = false;
static bool g_primitive_open = false;
static std::vector<ImmediateDraw> g_draws;
static float g_color[4];
static float g_uv[2][2];
static bool g_uv_set[2];

static void Reset_Recorders()
{
	for (unsigned stage = 0U; stage < 2U; ++stage) {
		g_dx8_coordinates[stage].texcoord_index = D3DTSS_TCI_PASSTHRU | stage;
		g_dx8_coordinates[stage].texture_transform_flags = D3DTTFF_DISABLE;
	}
	g_bound = DrawState();
	g_stage_state_complete = false;
	g_primitive_open = false;
	g_draws.clear();
	std::memset(g_color, 0, sizeof(g_color));
	std::memset(g_uv, 0, sizeof(g_uv));
	g_uv_set[0] = g_uv_set[1] = false;
}

void TextureClass::Apply_For_Platform_Boundary(unsigned stage)
{
	CHECK(!g_primitive_open && stage < 2U);
	if (stage == 0U) g_bound.texture0 = this;
	else g_bound.texture1 = this;
}

void Bind_Texture(unsigned stage, bool)
{
	CHECK(!g_primitive_open && stage == 0U);
	g_bound.texture0 = nullptr;
}

void Disable_Texture_Stage(unsigned stage)
{
	CHECK(!g_primitive_open && stage == 1U);
	g_bound.texture1 = nullptr;
}

void Apply_Original_Shader_State(ShaderClass shader)
{
	CHECK(!g_primitive_open);
	g_bound.shader_bits = shader.Get_Bits();
	g_stage_state_complete = false;
}

void Apply_Original_Texture_Stage_State(ShaderClass shader, bool texture0, bool detail)
{
	CHECK(!g_primitive_open);
	CHECK(shader.Get_Bits() == g_bound.shader_bits);
	CHECK(texture0 == (g_bound.texture0 != nullptr));
	CHECK(detail == (g_bound.texture1 != nullptr));
	g_bound.detail = detail;
	g_stage_state_complete = true;
}

// Mirrors production: a mapper owns its stage's coordinate state, otherwise
// the stage is pass-through from the material's UV source.
void Apply_Original_Texture_Coordinate_State(VertexMaterialClass *material)
{
	CHECK(!g_primitive_open);
	for (unsigned stage = 0U; stage < 2U; ++stage) {
		const DWORD uv_source = static_cast<DWORD>(Get_Original_UV_Source(material, stage));
		const TextureMapperClass *mapper =
			material != nullptr ? material->Peek_Mapper(static_cast<int>(stage)) : nullptr;
		if (mapper != nullptr) {
			g_dx8_coordinates[stage].texcoord_index = mapper->mode | uv_source;
			g_dx8_coordinates[stage].texture_transform_flags = mapper->flags;
		} else {
			g_dx8_coordinates[stage].texcoord_index = D3DTSS_TCI_PASSTHRU | uv_source |
				(material != nullptr ? material->forced_mode[stage] : 0U);
			g_dx8_coordinates[stage].texture_transform_flags =
				material != nullptr ? material->forced_flags[stage] : D3DTTFF_DISABLE;
		}
	}
	g_bound.material = material;
}

void Capture_Original_Texture_Coordinate_State(unsigned stage,
	OriginalTextureCoordinateState *state)
{
	CHECK(stage < 2U);
	*state = g_dx8_coordinates[stage];
}

// ---------------------------------------------------------------------------
// Immediate-loop-only surface (copied from the vita_mesh_batch_test style).

static unsigned g_render_work_cache_mode = 0U;
static VitaIndexedMeshBatch g_indexed_mesh_batch;
static uint64_t g_mesh_expanded_corners = 0U, g_mesh_unique_vertices = 0U;
static uint64_t g_mesh_indexed_batches = 0U;
struct MeshBoundaryTiming {
	uint64_t mesh_total_us = 0, mesh_sampled_us = 0, mesh_max_us = 0;
	uint64_t draw_end_total_us = 0, draw_end_sampled_us = 0, draw_end_max_us = 0;
	uint32_t mesh_count = 0, mesh_sample_count = 0, draw_end_count = 0, draw_end_sample_count = 0;
};
static MeshBoundaryTiming g_mesh_boundary_timing;
enum { MESH_BOUNDARY_TIMING_SAMPLE_STRIDE = 16U };
// Only the detailed-timing build samples draw ends.
[[maybe_unused]] static uint32_t g_draw_end_timing_sequence = 0U;
static uint64_t g_fake_process_time_us = 0U;
uint64_t sceKernelGetProcessTimeWide() { return ++g_fake_process_time_us; }
static bool g_logged_first_user_lighting = false;
static bool g_logged_first_skin_passthrough_texture_v_preserved = false;
static bool g_logged_first_stage1_mesh = false;
static bool g_logged_first_skin_texture_color = false;
static bool g_logged_first_material_lighting = false;
template <class... Args> void Vita_Append_A22_Runtime_Breadcrumb(Args...) {}
bool Is_Loading_Screen_Diagnostic_Name(const char *) { return false; }
bool Begin_Material_Color_Pass(int) { return false; }
void Prepare_Material_Light_Directions(const RenderInfoClass &, MaterialLightDirections &,
	const Matrix3D * = nullptr)
{
	CHECK(false && "material color caching is disabled in this fixture");
}

// Production's uncached path: the original evaluator without prepared lights.
MaterialVertexColor Evaluate_Material_Vertex_Color(bool cache_material_colors,
	VertexMaterialClass *material, const unsigned *color1, const unsigned *color2,
	unsigned vertex_index, const Vector3 *normals, const Matrix3D &world_transform,
	const RenderInfoClass &render_info, MaterialLightDirections &, bool discarded_skin_rgb)
{
	CHECK(!cache_material_colors && !discarded_skin_rgb);
	return Evaluate_Original_Material_Vertex_Color(material, color1, color2,
		vertex_index, normals, world_transform, render_info, nullptr);
}

float Clamp01(float value)
{
	return value < 0.0f ? 0.0f : (value > 1.0f ? 1.0f : value);
}

bool Emit_Original_Texture_Coordinate(unsigned stage, unsigned texture_unit,
	const OriginalTextureCoordinateState &state, const Vector2 *uvs, const Vector3 *,
	const Vector3 *, unsigned vertex_index, const Matrix3D &world_transform,
	const Matrix3D &view_transform, const char *)
{
	CHECK(stage < 2U && texture_unit == (stage == 0U ? GL_TEXTURE0 : GL_TEXTURE1));
	CHECK(world_transform.offset == kWorldOffset && view_transform.offset == kViewOffset);
	// Cache-eligible meshes only ever emit original pass-through coordinates.
	CHECK(Texture_Coordinate_Mode(state) == D3DTSS_TCI_PASSTHRU &&
		state.texture_transform_flags == D3DTTFF_DISABLE);
	if (uvs == nullptr) return false;
	g_uv[stage][0] = uvs[vertex_index].X;
	g_uv[stage][1] = uvs[vertex_index].Y;
	g_uv_set[stage] = true;
	return true;
}

void glColor4f(float r, float g, float b, float a)
{
	g_color[0] = r; g_color[1] = g; g_color[2] = b; g_color[3] = a;
}

void glBegin(unsigned mode)
{
	CHECK(mode == GL_TRIANGLES && !g_primitive_open && g_stage_state_complete);
	g_primitive_open = true;
	g_draws.push_back({g_bound, {}});
	g_uv_set[0] = g_uv_set[1] = false;
}

void Begin_Texture_Coordinate_Primitive(const OriginalTextureCoordinateState *)
{
	glBegin(GL_TRIANGLES);
}

void glVertex3f(float x, float y, float z)
{
	CHECK(g_primitive_open);
	ImmediateDraw &draw = g_draws.back();
	CHECK(Same_State(draw.state, g_bound));
	Corner corner;
	corner.state = draw.state;
	corner.position[0] = x; corner.position[1] = y; corner.position[2] = z;
	for (unsigned i = 0U; i < 4U; ++i) corner.color[i] = Static_Mesh_Color_Byte(g_color[i]);
	corner.has_uv0 = g_uv_set[0];
	corner.has_uv1 = g_uv_set[1];
	if (corner.has_uv0) { corner.uv0[0] = g_uv[0][0]; corner.uv0[1] = g_uv[0][1]; }
	if (corner.has_uv1) { corner.uv1[0] = g_uv[1][0]; corner.uv1[1] = g_uv[1][1]; }
	draw.corners.push_back(corner);
	g_uv_set[0] = g_uv_set[1] = false;
}

void glEnd()
{
	CHECK(g_primitive_open);
	g_primitive_open = false;
}

void vglRenegadeEndIndexed(int, const uint16_t *)
{
	CHECK(false && "fixtures run the original non-indexed immediate mode");
}

// ---------------------------------------------------------------------------
// Production text under test.

// Profiling scopes are timing only.
#define RENEGADE_FRAME_PROFILE(name) ((void)0)
StaticMeshStreamBuilder g_static_mesh_builder;
#include "static-mesh-helpers.inc"
#include "static-mesh-build.inc"

static void Run_Immediate(MeshModelClass *model, MeshClass &mesh,
	RenderInfoClass &render_info, const Fixture &fixture)
{
	const Vector3 *vertices = fixture.positions.data();
	const Vector3 *normals = fixture.normals.data();
	const TriIndex *triangles = fixture.triangles.data();
	const int vertex_count = fixture.vertex_count;
	const int triangle_count = static_cast<int>(fixture.triangles.size());
	const bool is_skin = false;
	const int base_pass_count = fixture.pass_count;
	const Matrix3D original_world_transform = {kWorldOffset};
	const Matrix3D original_view_transform = {kViewOffset};
	// Submit_Mesh_Internal's locals for an ordinary (non-procedural) pass:
	// every model pass over every triangle in original order.
	const bool procedural_pass = false;
	const int draw_pass_count = base_pass_count;
	const int submitted_triangle_count = triangle_count;
	const auto triangle_at = [](int draw_index) { return draw_index; };
	const auto texture_for = [model](int triangle_index, int pass, int stage) {
		return model->Peek_Texture(triangle_index, pass, stage);
	};
	const auto shader_for = [model](int triangle_index, int pass) {
		return model->Get_Shader(triangle_index, pass);
	};
	const auto material_for = [model](int vertex_index, int pass) {
		return model->Peek_Material(vertex_index, pass);
	};
#define __vita__ 1
#include "immediate-production.inc"
#undef __vita__
}

// ---------------------------------------------------------------------------
// (b) Independent walk of the original immediate traversal rules.

struct ReferenceBatch {
	DrawState state;
	size_t run;
	uint32_t index_count;
	uint32_t vertex_count;
};

struct Reference {
	bool eligible = true;
	// Any emitted (valid-triangle) corner evaluated with a lit material.
	bool uses_lighting = false;
	std::vector<std::string> verdicts;
	// Every original primitive (glBegin/glEnd), including ones left empty.
	std::vector<ImmediateDraw> runs;
	std::vector<ReferenceBatch> batches;
	std::set<const void *> materials;
};

static void Reject(Reference &reference, const char *reason)
{
	if (reference.eligible || reference.verdicts.size() < 4U) reference.verdicts.push_back(reason);
	reference.eligible = false;
}

static Reference Walk_Reference(const Fixture &f, const RenderInfoClass &render_info,
	const Matrix3D &world)
{
	Reference reference;
	const unsigned vertex_count = static_cast<unsigned>(f.vertex_count);
	const unsigned *user_lighting = Data_Or_Null(f.user_lighting);
	std::vector<uint32_t> stamp(vertex_count, 0U);
	uint32_t generation = 0U;
	for (int pass = 0; pass < f.pass_count; ++pass) {
		const unsigned *dcg = Data_Or_Null(f.dcg[pass]);
		const unsigned *color1 = user_lighting != nullptr ? user_lighting :
			Data_Or_Null(f.color_arrays[0]);
		const unsigned *color2 = Data_Or_Null(f.color_arrays[1]);
		if (color1 == nullptr && f.dcg_source[pass] == VertexMaterialClass::COLOR1) color1 = dcg;
		if (color2 == nullptr && f.dcg_source[pass] == VertexMaterialClass::COLOR2) color2 = dcg;
		bool open = false;
		DrawState state;
		const TextureClass *bound1 = nullptr;
		const Vector2 *uv0 = nullptr;
		const Vector2 *uv1 = nullptr;
		bool batch_open = false;
		uint32_t batch_unique = 0U;
		for (size_t t = 0U; t < f.triangles.size(); ++t) {
			TextureClass *texture0 = f.textures[pass][0][t];
			TextureClass *texture1 = f.textures[pass][1][t];
			const TriIndex &triangle = f.triangles[t];
			VertexMaterialClass *run_material =
				triangle[0] < vertex_count ? f.materials[pass][triangle[0]] : nullptr;
			const unsigned bits = f.shaders[pass][t];
			const bool detail = (bits & SHADER_POST_DETAIL) != 0U && texture1 != nullptr;
			if (!open || texture0 != state.texture0 || texture1 != bound1 ||
				run_material != state.material || detail != state.detail ||
				bits != state.shader_bits) {
				open = true;
				bound1 = texture1;
				state.texture0 = texture0;
				state.texture1 = detail ? texture1 : nullptr;
				state.material = run_material;
				state.shader_bits = bits;
				state.detail = detail;
				reference.runs.push_back({state, {}});
				reference.materials.insert(run_material);
				batch_open = false;
				const Vector2 *resolved[2];
				bool passthrough[2];
				for (unsigned stage = 0U; stage < 2U; ++stage) {
					const int source = run_material != nullptr && run_material->uv_source[stage] >= 0 ?
						run_material->uv_source[stage] : static_cast<int>(stage);
					const TextureMapperClass *mapper =
						run_material != nullptr ? run_material->mapper[stage] : nullptr;
					const DWORD mode = mapper != nullptr ? mapper->mode :
						(run_material != nullptr ? run_material->forced_mode[stage] : 0U);
					const DWORD flags = mapper != nullptr ? mapper->flags :
						(run_material != nullptr ? run_material->forced_flags[stage] : 0U);
					passthrough[stage] = mode == D3DTSS_TCI_PASSTHRU && flags == D3DTTFF_DISABLE;
					const Vector2 *by_index = source >= 0 && source < MeshMatDescClass::MAX_UV_ARRAYS ?
						Data_Or_Null(f.uv_by_index[source]) : nullptr;
					resolved[stage] = by_index != nullptr ? by_index : Data_Or_Null(f.pass_uvs[pass][stage]);
				}
				uv0 = resolved[0];
				uv1 = resolved[1] != nullptr ? resolved[1] : resolved[0];
				if (detail && texture0 == nullptr) Reject(reference, "detail stage over untextured base");
				if (texture0 != nullptr && run_material != nullptr && run_material->mapper[0] != nullptr)
					Reject(reference, "stage 0 mapper with bound texture");
				if (detail && run_material != nullptr && run_material->mapper[1] != nullptr)
					Reject(reference, "stage 1 mapper with detail stage");
				if (texture0 != nullptr && !passthrough[0]) Reject(reference, "stage 0 not pass-through");
				if (texture0 != nullptr && uv0 == nullptr) Reject(reference, "stage 0 has no UV array");
				if (detail && !passthrough[1]) Reject(reference, "stage 1 not pass-through");
				if (detail && uv1 == nullptr) Reject(reference, "stage 1 has no UV array");
			}
			if (triangle[0] >= vertex_count || triangle[1] >= vertex_count ||
				triangle[2] >= vertex_count) continue;
			if (!batch_open || batch_unique > STATIC_MESH_MAX_BATCH_VERTICES - 3U) {
				reference.batches.push_back({state, reference.runs.size() - 1U, 0U, 0U});
				batch_open = true;
				batch_unique = 0U;
				++generation;
			}
			ReferenceBatch &batch = reference.batches.back();
			for (unsigned corner_index = 0U; corner_index < 3U; ++corner_index) {
				const unsigned vertex = triangle[corner_index];
				VertexMaterialClass *vertex_material = f.materials[pass][vertex];
				reference.materials.insert(vertex_material);
				const MaterialVertexColor color = Evaluate_Original_Material_Vertex_Color(
					vertex_material, color1, color2, vertex, f.normals.data(), world,
					render_info, nullptr);
				if (color.lighting) reference.uses_lighting = true;
				Corner corner;
				corner.state = state;
				corner.position[0] = f.positions[vertex].X;
				corner.position[1] = f.positions[vertex].Y;
				corner.position[2] = f.positions[vertex].Z;
				corner.color[0] = Static_Mesh_Color_Byte(color.final_color.X);
				corner.color[1] = Static_Mesh_Color_Byte(color.final_color.Y);
				corner.color[2] = Static_Mesh_Color_Byte(color.final_color.Z);
				corner.color[3] = Static_Mesh_Color_Byte(color.alpha);
				if (texture0 != nullptr && uv0 != nullptr) {
					corner.has_uv0 = true;
					corner.uv0[0] = uv0[vertex].X;
					corner.uv0[1] = uv0[vertex].Y;
				}
				if (detail && uv1 != nullptr) {
					corner.has_uv1 = true;
					corner.uv1[0] = uv1[vertex].X;
					corner.uv1[1] = uv1[vertex].Y;
				}
				reference.runs.back().corners.push_back(corner);
				++batch.index_count;
				if (stamp[vertex] != generation) {
					stamp[vertex] = generation;
					++batch_unique;
					++batch.vertex_count;
				}
			}
		}
	}
	if (reference.batches.empty()) Reject(reference, "no drawable triangle");
	return reference;
}

// ---------------------------------------------------------------------------
// (a) Expansion of the cached streams exactly as replay addresses them.

static DrawState Batch_State(const StaticMeshBatch &batch)
{
	DrawState state;
	state.texture0 = batch.texture0;
	state.texture1 = batch.texture1;
	state.material = batch.material;
	state.shader_bits = batch.shader_bits;
	state.detail = batch.detail_stage;
	return state;
}

static std::vector<Corner> Expand_Cache(const StaticMeshStreamBuilder &builder)
{
	std::vector<Corner> corners;
	const StaticMeshArray<StaticMeshBatch> &batches = builder.Batches();
	const StaticMeshArray<uint16_t> &indices = builder.Indices();
	const StaticMeshArray<StaticMeshVertex> &vertices = builder.Vertices();
	for (uint32_t b = 0U; b < batches.Count(); ++b) {
		const StaticMeshBatch &batch = batches[b];
		CHECK(batch.window_base <= batch.first_vertex);
		CHECK(batch.first_vertex + batch.vertex_count - batch.window_base <=
			static_cast<uint32_t>(STATIC_MESH_MAX_BATCH_VERTICES) + 1U);
		CHECK(batch.first_index + batch.index_count <= indices.Count());
		std::vector<bool> referenced(batch.vertex_count, false);
		for (uint32_t i = batch.first_index; i < batch.first_index + batch.index_count; ++i) {
			const uint32_t vertex = batch.window_base + indices[i];
			// A batch only addresses the vertices it recorded itself.
			CHECK(vertex >= batch.first_vertex && vertex < batch.first_vertex + batch.vertex_count);
			referenced[vertex - batch.first_vertex] = true;
			const StaticMeshVertex &source = vertices[vertex];
			Corner corner;
			corner.state = Batch_State(batch);
			std::memcpy(corner.position, source.position, sizeof(corner.position));
			std::memcpy(corner.color, source.color, sizeof(corner.color));
			corner.has_uv0 = batch.texture0 != nullptr;
			corner.has_uv1 = batch.detail_stage;
			if (corner.has_uv0) std::memcpy(corner.uv0, source.uv0, sizeof(corner.uv0));
			else CHECK(source.uv0[0] == 0.0f && source.uv0[1] == 0.0f);
			if (corner.has_uv1) std::memcpy(corner.uv1, source.uv1, sizeof(corner.uv1));
			else CHECK(source.uv1[0] == 0.0f && source.uv1[1] == 0.0f);
			corners.push_back(corner);
		}
		for (uint32_t v = 0U; v < batch.vertex_count; ++v) CHECK(referenced[v]);
	}
	return corners;
}

static unsigned Texture_Id(const void *texture)
{
	return texture != nullptr ? static_cast<const TextureClass *>(texture)->id : 0U;
}

static unsigned Material_Id(const void *material)
{
	return material != nullptr ? static_cast<const VertexMaterialClass *>(material)->id : 0U;
}

static void Describe(const char *label, const Corner &corner)
{
	std::fprintf(stderr,
		"  %-9s tex0=%u tex1=%u material=%u shader=%08X detail=%d pos=(%g,%g,%g) "
		"rgba=(%u,%u,%u,%u) uv0%s=(%g,%g) uv1%s=(%g,%g)\n",
		label, Texture_Id(corner.state.texture0), Texture_Id(corner.state.texture1),
		Material_Id(corner.state.material), corner.state.shader_bits, corner.state.detail ? 1 : 0,
		corner.position[0], corner.position[1], corner.position[2],
		corner.color[0], corner.color[1], corner.color[2], corner.color[3],
		corner.has_uv0 ? "" : "(unused)", corner.uv0[0], corner.uv0[1],
		corner.has_uv1 ? "" : "(unused)", corner.uv1[0], corner.uv1[1]);
}

static void Compare_Streams(const char *what, const char *left_label,
	const std::vector<Corner> &left, const char *right_label, const std::vector<Corner> &right)
{
	const size_t count = left.size() < right.size() ? left.size() : right.size();
	for (size_t i = 0U; i < count; ++i) {
		if (!Same_Corner(left[i], right[i])) {
			std::fprintf(stderr, "fixture %s: %s mismatch at corner %zu of %zu/%zu\n",
				g_fixture_name, what, i, left.size(), right.size());
			Describe(left_label, left[i]);
			Describe(right_label, right[i]);
			std::abort();
		}
	}
	if (left.size() != right.size()) {
		std::fprintf(stderr, "fixture %s: %s corner count %s=%zu %s=%zu\n", g_fixture_name,
			what, left_label, left.size(), right_label, right.size());
		std::abort();
	}
}

static bool Has_Snapshot(const StaticMeshStreamBuilder &builder, const void *material)
{
	for (uint32_t i = 0U; i < builder.Materials().Count(); ++i) {
		if (builder.Materials()[i].material == material) return true;
	}
	return false;
}

struct Totals {
	size_t eligible = 0U, ineligible = 0U, corners = 0U, batches = 0U, splits = 0U;
	size_t windows = 0U, rewritten = 0U, empty_runs = 0U, lit = 0U;
};

static void Check_Fixture(const Fixture &f, bool report, Totals &totals)
{
	g_fixture_name = f.name.c_str();
	g_fixture = &f;
	MeshModelClass model = {&f};
	MeshClass mesh = {&f};
	RenderInfoClass render_info = {kRenderInfoId};
	const Matrix3D world = {kWorldOffset};
	const Reference reference = Walk_Reference(f, render_info, world);
	CHECK(reference.eligible == f.expect_eligible);

	CHECK(!reference.eligible || reference.uses_lighting == f.expect_uses_lighting);

	Reset_Recorders();
	// Seeded with the wrong answer: the builder must always write it.
	bool uses_lighting = !reference.uses_lighting;
	const bool built = Build_Static_Mesh_Streams(mesh, &model, render_info, f.positions.data(),
		f.normals.data(), f.triangles.data(), f.vertex_count,
		static_cast<int>(f.triangles.size()), f.pass_count, world, uses_lighting);
	const StaticMeshStreamBuilder &builder = g_static_mesh_builder;
	// An eligibility verdict is never reported as a storage failure.
	CHECK(!builder.Failed());
	CHECK(built == reference.eligible);
	if (!built) {
		if (f.verdict_material != nullptr) CHECK(Has_Snapshot(builder, f.verdict_material));
		++totals.ineligible;
		if (report) {
			std::printf("fixture=%s eligible=0 verdict=\"%s\" snapshots=%u\n", f.name.c_str(),
				reference.verdicts.front().c_str(), builder.Materials().Count());
		}
		return;
	}

	CHECK(uses_lighting == reference.uses_lighting);

	// Every material that shaped a run's UV state or a corner's color is
	// snapshotted exactly once, and nothing else is.
	std::set<const void *> snapshots;
	for (uint32_t i = 0U; i < builder.Materials().Count(); ++i) {
		CHECK(snapshots.insert(builder.Materials()[i].material).second);
	}
	CHECK(snapshots == reference.materials);

	// Batch boundaries: identical to the original primitives except for
	// 16-bit splits, which happen only when the next triangle could overflow.
	const StaticMeshArray<StaticMeshBatch> &batches = builder.Batches();
	CHECK(batches.Count() == reference.batches.size());
	uint32_t first_vertex = 0U, first_index = 0U, window = 0U;
	size_t windows = 0U, rewritten = 0U, splits = 0U;
	for (uint32_t i = 0U; i < batches.Count(); ++i) {
		const StaticMeshBatch &batch = batches[i];
		const ReferenceBatch &expected = reference.batches[i];
		CHECK(Same_State(Batch_State(batch), expected.state));
		CHECK(batch.first_vertex == first_vertex && batch.first_index == first_index);
		CHECK(batch.index_count == expected.index_count);
		CHECK(batch.vertex_count == expected.vertex_count);
		CHECK(batch.index_count != 0U && batch.index_count % 3U == 0U);
		CHECK(batch.vertex_count <= static_cast<uint32_t>(STATIC_MESH_MAX_BATCH_VERTICES));
		if (i != 0U && reference.batches[i - 1U].run == expected.run) {
			CHECK(batches[i - 1U].vertex_count > STATIC_MESH_MAX_BATCH_VERTICES - 3U);
			++splits;
		}
		if (i == 0U || batch.first_vertex + batch.vertex_count - window >
			static_cast<uint32_t>(STATIC_MESH_MAX_BATCH_VERTICES) + 1U) {
			window = batch.first_vertex;
			++windows;
		}
		CHECK(batch.window_base == window);
		if (batch.window_base != batch.first_vertex) ++rewritten;
		first_vertex += batch.vertex_count;
		first_index += batch.index_count;
	}
	CHECK(first_vertex == builder.Vertices().Count());
	CHECK(first_index == builder.Indices().Count());
	CHECK(windows == f.expect_windows && splits == f.expect_splits);

	std::vector<Corner> expected;
	size_t empty_runs = 0U;
	for (const ImmediateDraw &run : reference.runs) {
		if (run.corners.empty()) ++empty_runs;
		expected.insert(expected.end(), run.corners.begin(), run.corners.end());
	}
	// (a) == (b)
	Compare_Streams("cache vs reference", "cache", Expand_Cache(builder), "reference", expected);

	// (c) == (b): the production immediate loop, primitive by primitive.
	Reset_Recorders();
	Run_Immediate(&model, mesh, render_info, f);
	CHECK(!g_primitive_open);
	CHECK(g_draws.size() == reference.runs.size());
	for (size_t i = 0U; i < g_draws.size(); ++i) {
		CHECK(Same_State(g_draws[i].state, reference.runs[i].state));
		Compare_Streams("immediate vs reference", "immediate", g_draws[i].corners,
			"reference", reference.runs[i].corners);
	}

	++totals.eligible;
	if (uses_lighting) ++totals.lit;
	totals.corners += expected.size();
	totals.batches += batches.Count();
	totals.splits += splits;
	totals.windows += windows;
	totals.rewritten += rewritten;
	totals.empty_runs += empty_runs;
	if (report) {
		std::printf("fixture=%s eligible=1 lit=%d passes=%d triangles=%zu primitives=%zu empty=%zu "
			"batches=%u splits=%zu windows=%zu rewritten=%zu vertices=%u corners=%zu snapshots=%u\n",
			f.name.c_str(), uses_lighting ? 1 : 0, f.pass_count, f.triangles.size(),
			reference.runs.size(), empty_runs,
			batches.Count(), splits, windows, rewritten, builder.Vertices().Count(),
			expected.size(), builder.Materials().Count());
	}
}

// ---------------------------------------------------------------------------
// Fixtures.

static TextureClass g_textures[6] = {{1}, {2}, {3}, {4}, {5}, {6}};
static TextureMapperClass g_environment_mapper = {D3DTSS_TCI_CAMERASPACENORMAL, D3DTTFF_COUNT2};
// A mapper whose current DX8 state still reads as pass-through (for example an
// animated offset at zero): only the mapper guard can reject it.
static TextureMapperClass g_identity_mapper = {D3DTSS_TCI_PASSTHRU, D3DTTFF_DISABLE};
static VertexMaterialClass g_general[4];
static VertexMaterialClass g_lit;
static VertexMaterialClass g_mapper0;
static VertexMaterialClass g_mapper1;
static VertexMaterialClass g_identity_mapper0;
static VertexMaterialClass g_identity_mapper1;
static VertexMaterialClass g_generated0;
static VertexMaterialClass g_transformed0;
static VertexMaterialClass g_generated1;

static void Setup_Materials()
{
	g_general[0].id = 1U;
	g_general[1].id = 2U;
	g_general[1].diffuse = Vector3(0.5f, 0.75f, 1.0f);
	g_general[1].opacity = 0.5f;
	g_general[1].diffuse_source = VertexMaterialClass::COLOR1;
	g_general[1].uv_source[1] = 0;     // detail stage reads UV array 0
	g_general[2].id = 3U;
	g_general[2].diffuse = Vector3(1.0f, 0.25f, 0.5f);
	g_general[2].opacity = 0.75f;
	g_general[2].diffuse_source = VertexMaterialClass::COLOR2;
	g_general[2].uv_source[0] = 5;     // base stage reads UV array 5
	g_general[3].id = 4U;
	g_general[3].diffuse = Vector3(0.125f, 1.0f, 1.0f);
	g_general[3].uv_source[0] = 7;     // absent array: falls back to the pass array
	g_general[3].uv_source[1] = 6;
	g_lit.id = 10U;
	g_lit.lighting = true;
	g_mapper0.id = 11U;
	g_mapper0.mapper[0] = &g_environment_mapper;
	g_mapper1.id = 12U;
	g_mapper1.mapper[1] = &g_environment_mapper;
	g_identity_mapper0.id = 16U;
	g_identity_mapper0.mapper[0] = &g_identity_mapper;
	g_identity_mapper1.id = 17U;
	g_identity_mapper1.mapper[1] = &g_identity_mapper;
	g_generated0.id = 13U;
	g_generated0.forced_mode[0] = D3DTSS_TCI_CAMERASPACEPOSITION;
	g_transformed0.id = 14U;
	g_transformed0.forced_flags[0] = D3DTTFF_COUNT2;
	g_generated1.id = 15U;
	g_generated1.forced_mode[1] = D3DTSS_TCI_CAMERASPACENORMAL;
}

static VertexMaterialClass *General_Or_Null(unsigned index)
{
	return index < 4U ? &g_general[index] : nullptr;
}

static TriIndex Tri(unsigned a, unsigned b, unsigned c)
{
	return TriIndex{static_cast<uint16_t>(a), static_cast<uint16_t>(b), static_cast<uint16_t>(c)};
}

static std::vector<Vector2> Make_UVs(int count, uint32_t salt)
{
	std::vector<Vector2> uvs(static_cast<size_t>(count));
	for (int i = 0; i < count; ++i) {
		const uint32_t index = static_cast<uint32_t>(i);
		uvs[i].X = static_cast<float>(Mix(index, salt) & 0xffffU) / 4096.0f - 4.0f;
		uvs[i].Y = static_cast<float>(Mix(index, salt + 1U) & 0xffffU) / 2048.0f;
	}
	return uvs;
}

static std::vector<unsigned> Make_Colors(int count, uint32_t salt)
{
	std::vector<unsigned> colors(static_cast<size_t>(count));
	for (int i = 0; i < count; ++i) colors[i] = Mix(static_cast<uint32_t>(i), salt);
	return colors;
}

static Fixture Make_Fixture(const char *name, int vertex_count, int triangle_count, int pass_count)
{
	Fixture f;
	f.name = name;
	f.vertex_count = vertex_count;
	f.pass_count = pass_count;
	f.positions.resize(static_cast<size_t>(vertex_count));
	f.normals.resize(static_cast<size_t>(vertex_count));
	for (int i = 0; i < vertex_count; ++i) {
		const uint32_t index = static_cast<uint32_t>(i);
		f.positions[i] = Vector3(static_cast<float>(i) * 0.5f,
			static_cast<float>(Mix(index, 7U) & 0xfffU) / 64.0f, -static_cast<float>(i % 977));
		f.normals[i] = Vector3(static_cast<float>(Mix(index, 9U) & 0xffU) / 256.0f,
			static_cast<float>(i % 3), static_cast<float>(Mix(index, 11U) & 0xffU) / 128.0f - 1.0f);
	}
	f.triangles.assign(static_cast<size_t>(triangle_count), Tri(0U, 0U, 0U));
	// Arrays 1, 3, 4 and 7 are absent so default stage 1 and some material
	// sources fall back to the pass arrays.
	for (unsigned index : {0U, 2U, 5U, 6U}) f.uv_by_index[index] = Make_UVs(vertex_count, 100U + index);
	f.color_arrays[0] = Make_Colors(vertex_count, 0xa1U);
	f.color_arrays[1] = Make_Colors(vertex_count, 0xb2U);
	for (int pass = 0; pass < pass_count; ++pass) {
		f.pass_uvs[pass][0] = Make_UVs(vertex_count, 10U + 2U * static_cast<uint32_t>(pass));
		f.pass_uvs[pass][1] = Make_UVs(vertex_count, 11U + 2U * static_cast<uint32_t>(pass));
		f.dcg[pass] = Make_Colors(vertex_count, 0xc3U + static_cast<uint32_t>(pass));
		f.textures[pass][0].assign(static_cast<size_t>(triangle_count), &g_textures[0]);
		f.textures[pass][1].assign(static_cast<size_t>(triangle_count), nullptr);
		f.materials[pass].assign(static_cast<size_t>(vertex_count), &g_general[0]);
		f.shaders[pass].assign(static_cast<size_t>(triangle_count), SHADER_TEXTURING);
	}
	return f;
}

// Three passes, texture/shader/material runs of different lengths per pass,
// detail toggling, NULL vertex materials, adjacent triangles sharing vertices,
// repeated vertices inside a triangle, and distant runs reusing vertices.
static Fixture Fixture_Multi_Pass_Runs()
{
	Fixture f = Make_Fixture("multi_pass_state_runs", 900, 1500, 3);
	f.color_arrays[0].clear();   // color1 comes from each pass's DCG when its source is COLOR1
	f.pass_uvs[1][1].clear();    // pass 1 detail falls back to the resolved base array
	for (unsigned t = 0U; t < 1500U; ++t) {
		const unsigned a = (t * 5U / 3U) % 880U;
		TriIndex triangle = Tri(a, a + 1U, a + 2U + t % 4U);
		if (t % 7U == 0U) triangle = Tri(a, a + 9U, a);
		if (t % 13U == 0U) {
			const unsigned b = (t * 37U) % 850U;
			triangle = Tri(b, b + 3U, b + 6U);
		}
		f.triangles[t] = triangle;
	}
	static const unsigned run_length[3] = {37U, 11U, 200U};
	for (unsigned pass = 0U; pass < 3U; ++pass) {
		for (unsigned v = 0U; v < 900U; ++v) f.materials[pass][v] = General_Or_Null((v / 45U + pass) % 5U);
		for (unsigned t = 0U; t < 1500U; ++t) {
			const unsigned group = t / run_length[pass];
			TextureClass *texture0 = group % 4U == 3U ? nullptr : &g_textures[(group + pass) % 4U];
			TextureClass *texture1 = pass == 1U ?
				((t / 50U) % 3U == 0U ? nullptr : &g_textures[5]) : &g_textures[4U + (t / 23U) % 2U];
			unsigned bits = SHADER_TEXTURING | (((t / 101U) % 3U) << 4);
			if ((t / 53U) % 2U == 1U && texture0 != nullptr) bits |= SHADER_POST_DETAIL;
			f.textures[pass][0][t] = texture0;
			f.textures[pass][1][t] = texture1;
			f.shaders[pass][t] = bits;
		}
	}
	return f;
}

// Invalid indices in every corner position (corner 0 invalid also makes the
// run material NULL), a run made only of invalid triangles between two runs
// of identical state, repeated vertices, and a lit material that is only ever
// corner 0 of invalid triangles: it becomes a run material but is never
// evaluated, so the mesh does not use lighting.
static Fixture Fixture_Invalid_Triangles()
{
	Fixture f = Make_Fixture("invalid_triangles", 200, 400, 2);
	f.color_arrays[0].clear();
	f.color_arrays[1].clear();
	f.dcg_source[0] = VertexMaterialClass::COLOR2;
	f.dcg_source[1] = VertexMaterialClass::COLOR1;
	for (unsigned t = 0U; t < 400U; ++t) {
		const unsigned a = t % 190U;
		TriIndex triangle = Tri(a, a + 1U, a + 2U);
		if (t % 5U == 1U) triangle = Tri(a, a, a + 1U);
		switch (t % 17U) {
		case 3U: triangle[0] = 200U; break;
		case 7U: triangle[1] = 65535U; break;
		case 11U: triangle = Tri(195U, a, 201U); break;
		default: break;
		}
		if (t >= 100U && t < 110U) triangle = Tri(a, a + 1U, 250U);
		f.triangles[t] = triangle;
	}
	for (unsigned pass = 0U; pass < 2U; ++pass) {
		for (unsigned v = 0U; v < 200U; ++v) f.materials[pass][v] = &g_general[(v / 30U + pass) % 4U];
		f.materials[pass][195] = &g_lit;
		for (unsigned t = 0U; t < 400U; ++t) {
			TextureClass *texture0 = &g_textures[(t / 9U + pass) % 3U];
			if (t >= 90U && t < 120U) texture0 = &g_textures[0];
			if (t >= 100U && t < 110U) texture0 = &g_textures[5];
			unsigned bits = SHADER_TEXTURING;
			TextureClass *texture1 = nullptr;
			if (pass == 0U && (t / 40U) % 2U == 1U) bits |= 0x100U;
			if (pass == 1U && t >= 200U && t < 300U) {
				texture1 = &g_textures[3];
				bits |= SHADER_POST_DETAIL;
			}
			f.textures[pass][0][t] = texture0;
			f.textures[pass][1][t] = texture1;
			f.shaders[pass][t] = bits;
		}
	}
	return f;
}

// Detail on/off, a stage 1 texture that changes while the detail stage is
// off (new original primitive, identical cached state), untextured runs
// (with a detail bit but no stage 1 texture, and with an unused stage 1
// texture), a stage 0 mapper on untextured runs and a stage 1 mapper on
// non-detail runs (both still cacheable), and user lighting as color1.
static Fixture Fixture_Detail_And_Untextured()
{
	Fixture f = Make_Fixture("detail_and_untextured_runs", 300, 600, 2);
	f.user_lighting = Make_Colors(300, 0xd4U);
	f.color_arrays[1].clear();
	f.dcg_source[0] = VertexMaterialClass::COLOR2;
	f.dcg_source[1] = VertexMaterialClass::COLOR1;
	for (unsigned t = 0U; t < 600U; ++t) {
		const unsigned mode = (t / 20U) % 6U;
		const unsigned base = mode == 0U ? 200U : (mode == 3U || mode == 4U ? 0U : 100U);
		f.triangles[t] = Tri(base + (t * 3U) % 97U, (t * 7U + 1U) % 300U, (t * 13U + 2U) % 300U);
	}
	for (unsigned pass = 0U; pass < 2U; ++pass) {
		for (unsigned v = 0U; v < 300U; ++v) {
			f.materials[pass][v] = v < 100U ? &g_mapper0 :
				(v < 200U ? &g_mapper1 : &g_general[(v + pass) % 4U]);
		}
		for (unsigned t = 0U; t < 600U; ++t) {
			const unsigned mode = (t / 20U) % 6U;
			TextureClass *texture0 = &g_textures[pass == 0U ? (t / 120U) % 2U : 2U];
			TextureClass *texture1 = nullptr;
			unsigned bits = SHADER_TEXTURING | (pass == 1U ? 0x40U : 0U);
			switch (mode) {
			case 0U: texture1 = &g_textures[3]; bits |= SHADER_POST_DETAIL; break;
			case 1U: texture1 = &g_textures[3]; break;
			case 2U: texture1 = &g_textures[4]; break;
			case 3U: texture0 = nullptr; bits = SHADER_POST_DETAIL; break;
			case 4U: texture0 = nullptr; texture1 = &g_textures[3]; bits = 0U; break;
			default: texture0 = &g_textures[1]; bits |= SHADER_POST_DETAIL; break;
			}
			f.textures[pass][0][t] = texture0;
			f.textures[pass][1][t] = texture1;
			f.shaders[pass][t] = bits;
		}
	}
	return f;
}

// Twelve vertices reused by ~200 short runs: every batch re-records the
// vertices it shares with other runs and indexes them through one window.
static Fixture Fixture_Shared_Vertices()
{
	Fixture f = Make_Fixture("shared_vertices_short_runs", 12, 300, 2);
	for (unsigned t = 0U; t < 300U; ++t) f.triangles[t] = Tri(t % 12U, (t + 1U) % 12U, (t + 5U) % 12U);
	for (unsigned pass = 0U; pass < 2U; ++pass) {
		for (unsigned v = 0U; v < 12U; ++v) f.materials[pass][v] = &g_general[(v / 6U + pass) % 2U];
		for (unsigned t = 0U; t < 300U; ++t) {
			unsigned bits = SHADER_TEXTURING | ((t / 3U) % 2U != 0U ? 0x20U : 0U);
			f.textures[pass][0][t] = &g_textures[(t / 2U + pass) % 2U];
			if (pass == 1U) {
				f.textures[pass][1][t] = &g_textures[3];
				bits |= SHADER_POST_DETAIL;
			}
			f.shaders[pass][t] = bits;
		}
	}
	return f;
}

// 65536 vertices and 40000-triangle fans per run: more than 65535 corners and
// unique vertices in one run force 16-bit splits (reusing the fan centre
// across each split) and several vertex windows, while the shorter runs
// after them share a window at a nonzero offset (rewritten indices).
static Fixture Fixture_Large_Split()
{
	Fixture f = Make_Fixture("large_split_windows", 65536, 50000, 2);
	for (unsigned t = 0U; t < 50000U; ++t) {
		if (t < 40000U) {
			f.triangles[t] = Tri(0U, (2U * t + 1U) % 65536U, (2U * t + 2U) % 65536U);
		} else {
			const unsigned a = (t * 7U) % 65536U;
			f.triangles[t] = Tri(a, (a + 1U) % 65536U, (a + 3U) % 65536U);
		}
	}
	for (unsigned v = 0U; v < 65536U; ++v) {
		f.materials[0][v] = &g_general[(v / 4096U) % 4U];
		f.materials[1][v] = &g_general[(v / 8192U + 1U) % 4U];
	}
	for (unsigned t = 0U; t < 50000U; ++t) {
		f.textures[0][0][t] = &g_textures[t < 40000U ? 0 : 1];
		if (t >= 45000U) {
			f.textures[0][1][t] = &g_textures[3];
			f.shaders[0][t] = SHADER_TEXTURING | SHADER_POST_DETAIL;
		}
		f.textures[1][0][t] = &g_textures[2];
		f.shaders[1][t] = SHADER_TEXTURING | 0x40U;
	}
	// Pass 0: the 40000-fan run splits once (65533 + 14468 vertices) and the
	// later runs share the second window; pass 1 repeats the split and needs
	// two more windows because neither half fits beside the previous one.
	f.expect_windows = 4U;
	f.expect_splits = 2U;
	return f;
}

// Lands exactly on both 16-bit boundaries: a run of 3-new-vertex triangles
// reaches 65532 vertices and may still take one more triangle (65535, local
// index 65534, no split); the next one-vertex run spans exactly 65536 and
// must share the window (rewritten index 65535); the run after it would span
// 65537 and must open a new window.
static Fixture Fixture_Window_Boundary()
{
	Fixture f = Make_Fixture("window_boundary_16bit", 65536, 21848, 1);
	for (unsigned k = 0U; k < 21845U; ++k) f.triangles[k] = Tri(3U * k, 3U * k + 1U, 3U * k + 2U);
	f.triangles[21845] = Tri(65535U, 65535U, 65535U);
	f.triangles[21846] = Tri(7U, 7U, 7U);
	f.triangles[21847] = Tri(65535U, 9U, 65535U);
	f.textures[0][0][21845] = &g_textures[1];
	f.textures[0][0][21847] = &g_textures[1];
	for (unsigned v = 0U; v < 65536U; ++v) f.materials[0][v] = &g_general[v % 3U == 0U ? 0U : 1U + v % 3U];
	f.expect_windows = 2U;
	return f;
}

// Triangles (a, a + 1, a + 3) with even a: odd vertices are never corner 0.
static Fixture Make_Small(const char *name, int pass_count = 1)
{
	Fixture f = Make_Fixture(name, 64, 96, pass_count);
	for (unsigned t = 0U; t < 96U; ++t) {
		const unsigned a = (t * 2U) % 60U;
		f.triangles[t] = Tri(a, a + 1U, a + 3U);
	}
	for (int pass = 0; pass < pass_count; ++pass) {
		for (unsigned t = 0U; t < 96U; ++t) {
			f.textures[pass][0][t] = &g_textures[(t / 12U + static_cast<unsigned>(pass)) % 3U];
		}
		for (unsigned v = 0U; v < 64U; ++v) {
			f.materials[pass][v] = &g_general[(v / 16U + static_cast<unsigned>(pass)) % 4U];
		}
	}
	return f;
}

static void Set_Materials(Fixture &f, unsigned first, unsigned last, VertexMaterialClass *material)
{
	for (unsigned v = first; v < last; ++v) f.materials[0][v] = material;
}

static void Enable_Detail(Fixture &f)
{
	for (unsigned t = 0U; t < f.triangles.size(); ++t) {
		f.textures[0][1][t] = &g_textures[3];
		f.shaders[0][t] |= SHADER_POST_DETAIL;
	}
}

static std::vector<Fixture> Make_Fixtures()
{
	std::vector<Fixture> fixtures;
	fixtures.push_back(Make_Small("small_baseline"));
	fixtures.push_back(Fixture_Multi_Pass_Runs());
	fixtures.push_back(Fixture_Invalid_Triangles());
	fixtures.push_back(Fixture_Detail_And_Untextured());
	fixtures.push_back(Fixture_Shared_Vertices());
	fixtures.push_back(Fixture_Large_Split());
	fixtures.push_back(Fixture_Window_Boundary());

	// Lit vertices both as run material (even, corner 0) and as other corners.
	Fixture lit = Make_Small("lit_vertex_material");
	Set_Materials(lit, 40U, 48U, &g_lit);
	lit.expect_uses_lighting = true;
	fixtures.push_back(lit);

	// One lit vertex, never corner 0, only in the second pass: lighting is
	// reported for the whole mesh while every run state stays unlit.
	Fixture lit_second_pass = Make_Small("lit_single_corner_second_pass", 2);
	lit_second_pass.materials[1][27] = &g_lit;
	lit_second_pass.expect_uses_lighting = true;
	fixtures.push_back(lit_second_pass);

	Fixture mapper0 = Make_Small("ineligible_stage0_mapper_bound_texture");
	Set_Materials(mapper0, 16U, 24U, &g_mapper0);
	mapper0.verdict_material = &g_mapper0;
	fixtures.push_back(mapper0);

	Fixture identity0 = Make_Small("ineligible_stage0_mapper_identity_state");
	Set_Materials(identity0, 16U, 24U, &g_identity_mapper0);
	identity0.verdict_material = &g_identity_mapper0;
	fixtures.push_back(identity0);

	Fixture generated0 = Make_Small("ineligible_stage0_generated_coordinates");
	Set_Materials(generated0, 16U, 24U, &g_generated0);
	generated0.verdict_material = &g_generated0;
	fixtures.push_back(generated0);

	Fixture transformed0 = Make_Small("ineligible_stage0_texture_transform");
	Set_Materials(transformed0, 16U, 24U, &g_transformed0);
	transformed0.verdict_material = &g_transformed0;
	fixtures.push_back(transformed0);

	Fixture null_uv = Make_Small("ineligible_stage0_null_uv_array");
	null_uv.uv_by_index[0].clear();
	null_uv.pass_uvs[0][0].clear();
	null_uv.verdict_material = &g_general[0];
	fixtures.push_back(null_uv);

	Fixture detail_untextured = Make_Small("ineligible_detail_without_base_texture");
	for (unsigned t = 24U; t < 36U; ++t) {
		detail_untextured.textures[0][0][t] = nullptr;
		detail_untextured.textures[0][1][t] = &g_textures[3];
		detail_untextured.shaders[0][t] = SHADER_TEXTURING | SHADER_POST_DETAIL;
	}
	fixtures.push_back(detail_untextured);

	Fixture mapper1 = Make_Small("ineligible_stage1_mapper_detail");
	Enable_Detail(mapper1);
	Set_Materials(mapper1, 16U, 24U, &g_mapper1);
	mapper1.verdict_material = &g_mapper1;
	fixtures.push_back(mapper1);

	Fixture identity1 = Make_Small("ineligible_stage1_mapper_identity_state_detail");
	Enable_Detail(identity1);
	Set_Materials(identity1, 16U, 24U, &g_identity_mapper1);
	identity1.verdict_material = &g_identity_mapper1;
	fixtures.push_back(identity1);

	Fixture generated1 = Make_Small("ineligible_stage1_generated_coordinates_detail");
	Enable_Detail(generated1);
	Set_Materials(generated1, 16U, 24U, &g_generated1);
	generated1.verdict_material = &g_generated1;
	fixtures.push_back(generated1);

	Fixture no_triangles = Make_Small("ineligible_no_drawable_triangle");
	for (unsigned t = 0U; t < 96U; ++t) no_triangles.triangles[t][2] = 64U;
	fixtures.push_back(no_triangles);

	for (Fixture &fixture : fixtures) {
		if (fixture.name.compare(0, 11, "ineligible_") == 0) fixture.expect_eligible = false;
	}
	return fixtures;
}

int main()
{
	Setup_Materials();
	const std::vector<Fixture> fixtures = Make_Fixtures();
	Totals totals;
	for (const Fixture &fixture : fixtures) Check_Fixture(fixture, true, totals);
	// Again in reverse order: the shared builder's vertex map has grown and
	// its generations advanced, which must not leak into any later build.
	Totals repeat;
	for (size_t i = fixtures.size(); i-- != 0U;) Check_Fixture(fixtures[i], false, repeat);
	CHECK(repeat.corners == totals.corners && repeat.batches == totals.batches);
	g_fixture_name = "(summary)";
	CHECK(totals.splits != 0U && totals.rewritten != 0U && totals.empty_runs != 0U);
	CHECK(totals.lit != 0U && totals.lit < totals.eligible);
	std::printf("static mesh cache equivalence PASS eligible=%zu lit=%zu ineligible=%zu corners=%zu "
		"batches=%zu splits=%zu windows=%zu rewritten=%zu empty_primitives=%zu evaluations=%llu\n",
		totals.eligible, totals.lit, totals.ineligible, totals.corners, totals.batches, totals.splits,
		totals.windows, totals.rewritten, totals.empty_runs,
		static_cast<unsigned long long>(g_color_evaluations));
	return 0;
}
