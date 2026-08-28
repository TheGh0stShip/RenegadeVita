#include "ww3d_vita_renderer.h"

#include "camera.h"
#include "d3d8.h"
#include "dx8wrapper.h"
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

#if defined(__vita__)
#include "vita_runtime_log.h"

#include <psp2/io/stat.h>
#include <psp2/kernel/sysmem.h>
#include <vitaGL.h>
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
	Vector3 *vertices = new (std::nothrow) Vector3[vertex_count];
	Vector3 *normals = new (std::nothrow) Vector3[vertex_count];
	if (vertices == NULL || normals == NULL) {
		delete[] vertices;
		delete[] normals;
		return false;
	}
	delete[] g_deformed_skin_vertices;
	delete[] g_deformed_skin_normals;
	g_deformed_skin_vertices = vertices;
	g_deformed_skin_normals = normals;
	g_deformed_skin_capacity = vertex_count;
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

#if defined(__vita__)
bool g_logged_first_frame = false;
bool g_logged_first_present = false;
bool g_logged_first_mesh = false;
bool g_logged_first_skin = false;
bool g_logged_first_stage1_mesh = false;
bool g_logged_first_texture_mapper = false;
bool g_logged_first_generated_texture_coordinate = false;
bool g_logged_skin_failure = false;
bool g_logged_first_static_material_fallback = false;
bool g_shader_compiler_available = false;
unsigned g_shader_init_calls = 0;
int g_shader_init_last_result = -1;

struct OriginalTextureCoordinateState {
	DWORD texcoord_index;
	DWORD texture_transform_flags;
	D3DMATRIX texture_transform;
};

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
	const Matrix3D &world_transform, const Matrix3D &view_transform)
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
	float s = 0.0f;
	float t = 0.0f;
	Apply_DX8_Texture_Transform(state, source_s, source_t, source_r, 1.0f,
		&s, &t);
	glMultiTexCoord2f(texture_unit, s, t);
	if (Uses_Generated_Texture_Coordinates(state) &&
		!g_logged_first_generated_texture_coordinate) {
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
	const float *world_transform, const float *view_transform)
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

	float s = 0.0f;
	float t = 0.0f;
	Apply_DX8_Texture_Transform(state, source_s, source_t, source_r, 1.0f,
		&s, &t);
	glMultiTexCoord2f(texture_unit, s, t);
	if (Uses_Generated_Texture_Coordinates(state) &&
		!g_logged_first_generated_texture_coordinate) {
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
		glCullFace(GL_BACK);
	} else glDisable(GL_CULL_FACE);
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

bool Is_Near_Black(const Vector3 &color)
{
	return color.X <= 0.003f && color.Y <= 0.003f && color.Z <= 0.003f;
}

Vector3 Max_Color(const Vector3 &left, const Vector3 &right)
{
	return Vector3(left.X > right.X ? left.X : right.X,
		left.Y > right.Y ? left.Y : right.Y,
		left.Z > right.Z ? left.Z : right.Z);
}

void Log_Static_Material_Fallback(MeshClass &mesh, TextureClass *texture,
	VertexMaterialClass *material, const ShaderClass &shader,
	const Vector3 &diffuse, const Vector3 &ambient, const Vector3 &emissive,
	const Vector3 &selected, float opacity)
{
	if (g_logged_first_static_material_fallback) return;
	Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
		"first static material black fallback: mesh=%s texture=%s shader=%08X gradient=%d material=%p diffuse=(%.3f,%.3f,%.3f) ambient=(%.3f,%.3f,%.3f) emissive=(%.3f,%.3f,%.3f) selected=(%.3f,%.3f,%.3f) opacity=%.3f",
		mesh.Get_Name(),
		texture != NULL ? texture->Get_Texture_Name().Peek_Buffer() : "none",
		shader.Get_Bits(), static_cast<int>(shader.Get_Primary_Gradient()),
		static_cast<void *>(material),
		diffuse.X, diffuse.Y, diffuse.Z, ambient.X, ambient.Y, ambient.Z,
		emissive.X, emissive.Y, emissive.Z, selected.X, selected.Y,
		selected.Z, opacity);
	g_logged_first_static_material_fallback = true;
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
		(static_cast<uint64_t>(d3d_x) * DISPLAY_WIDTH) / logical_width;
	const uint64_t right =
		((static_cast<uint64_t>(d3d_x) + width) * DISPLAY_WIDTH +
			logical_width - 1U) / logical_width;
	const uint64_t top =
		(static_cast<uint64_t>(d3d_y) * DISPLAY_HEIGHT) / logical_height;
	const uint64_t bottom =
		((static_cast<uint64_t>(d3d_y) + height) * DISPLAY_HEIGHT +
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
	}
	static bool logged_first_camera_viewport = false;
	if (!logged_first_camera_viewport) {
		Vita_Append_A22_Runtime_Breadcrumb("camera-state",
			"original CameraClass viewport: d3d=%u,%u %ux%u native=%u,%u %ux%u depth=%.6f..%.6f prior_gl=%08X gl=%08X",
			d3d_x, d3d_y, width, height, viewport.x, viewport.y,
			viewport.width, viewport.height, viewport.min_depth,
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

void Apply_Indexed_Shader_State(const ShaderClass &shader)
{
	++g_statistics.indexed_state_applications;
#if defined(__vita__)
	Apply_Original_Shader_State(shader);
#else
	(void)shader;
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
	g_shader_compiler_available = false;
	g_shader_init_calls = 0;
	g_shader_init_last_result = -1;

	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "vglInit entry");
	const GLboolean resolution_fallback = vglInit(4 * 1024 * 1024);
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
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "depth buffer state entry");
	glEnable(GL_DEPTH_TEST);
	glDepthFunc(GL_LEQUAL);
	const GLenum depth_error = Log_GL_Result("depth enable/function");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "raster state-cache entry");
	glDisable(GL_CULL_FACE);
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
	RenegadeVita_Release_DX8_Bound_Textures();
	g_statistics.initialized = false;
	g_lifecycle.logical_session_active = false;
	Release_Deformed_Skin_Scratch();
#if defined(__vita__)
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
		vglSwapBuffers(GL_FALSE);
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
	if (!valid || native_texture == 0U) {
		++g_statistics.texture_invalid_binds;
#if defined(__vita__)
		glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage));
		glDisable(GL_TEXTURE_2D);
		glActiveTexture(GL_TEXTURE0);
#endif
		return false;
	}
	++g_statistics.texture_binds;
#if defined(__vita__)
	glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage));
	glEnable(GL_TEXTURE_2D);
	glBindTexture(GL_TEXTURE_2D, native_texture);
	glActiveTexture(GL_TEXTURE0);
#endif
	return true;
}

void Disable_Texture_Stage(uint32_t stage)
{
#if defined(__vita__)
	glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage));
	glDisable(GL_TEXTURE_2D);
	glActiveTexture(GL_TEXTURE0);
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
	if (!valid || native_texture == 0U) {
		++g_statistics.texture_invalid_binds;
		return false;
	}
	++g_statistics.texture_sampler_updates;
#if defined(__vita__)
	// D3D8's TextureClass owns the state choices.  This narrow translation only
	// maps its established address/filter contract to VitaGL; it does not add a
	// Vita sensitivity, cache, or material policy of its own.
	const GLenum wrap_u = address_u == 3U ? GL_CLAMP_TO_EDGE : GL_REPEAT;
	const GLenum wrap_v = address_v == 3U ? GL_CLAMP_TO_EDGE : GL_REPEAT;
	const bool point_min = min_filter == 1U;
	GLenum native_min = point_min ? GL_NEAREST : GL_LINEAR;
	if (mip_filter == 1U) {
		native_min = point_min ? GL_NEAREST_MIPMAP_NEAREST : GL_LINEAR_MIPMAP_NEAREST;
	} else if (mip_filter == 2U || mip_filter == 3U) {
		native_min = point_min ? GL_NEAREST_MIPMAP_LINEAR : GL_LINEAR_MIPMAP_LINEAR;
	}
	glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage));
	glBindTexture(GL_TEXTURE_2D, native_texture);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap_u);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap_v);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, native_min);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
		mag_filter == 1U ? GL_NEAREST : GL_LINEAR);
	glActiveTexture(GL_TEXTURE0);
	if (glGetError() != GL_NO_ERROR) {
		++g_statistics.backend_errors;
		return false;
	}
#else
	(void)address_u;
	(void)address_v;
	(void)min_filter;
	(void)mag_filter;
	(void)mip_filter;
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
	glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage));
	if (!texture_enabled) {
		glDisable(GL_TEXTURE_2D);
		glActiveTexture(GL_TEXTURE0);
		return true;
	}
	glEnable(GL_TEXTURE_2D);
	glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_COMBINE);
	Apply_GL_RGB_Texture_Op(color_op, color_arg1, color_arg2);
	Apply_GL_Alpha_Texture_Op(alpha_op, alpha_arg1, alpha_arg2);
	glActiveTexture(GL_TEXTURE0);
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

void Record_Texture_Unsupported_Stage(uint32_t stage)
{
	if (stage >= MeshMatDescClass::MAX_TEX_STAGES) {
		++g_statistics.texture_unsupported_stages;
	}
}

void Release_Texture(uint32_t native_texture)
{
#if defined(__vita__)
	if (native_texture != 0U) glDeleteTextures(1, &native_texture);
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
	if (is_skin && !g_logged_first_skin) {
		Vita_Append_A22_Runtime_Breadcrumb("skin-submit",
			"first original deformed skin submission: mesh=%s vertices=%d triangles=%d passes=%d texture=%s uv=%d dcg=%d world=identity",
			mesh.Get_Name(), vertex_count, triangle_count, pass_count,
			first_texture != NULL ? first_texture->Get_Texture_Name().Peek_Buffer() : "none",
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
		TextureClass *bound_textures[MeshMatDescClass::MAX_TEX_STAGES] = {};
		unsigned current_shader_bits = 0xffffffffU;
		VertexMaterialClass *current_material = NULL;
		const Vector2 *current_uvs[MeshMatDescClass::MAX_TEX_STAGES] = {};
		OriginalTextureCoordinateState
			current_texture_coordinates[MeshMatDescClass::MAX_TEX_STAGES] = {};
		bool current_detail_stage = false;
		bool primitive_open = false;
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
				if (primitive_open) glEnd();
				bound_textures[0] = triangle_textures[0];
				bound_textures[1] = triangle_textures[1];
				current_material = triangle_material;
				current_detail_stage = detail_stage;
				current_shader_bits = triangle_shader_bits;
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
			for (int corner = 0; corner < 3; ++corner) {
				const unsigned vertex_index = vertex_indices[corner];
				if (bound_textures[0] != NULL) {
					Emit_Original_Texture_Coordinate(0U, GL_TEXTURE0,
						current_texture_coordinates[0], current_uvs[0], vertices,
						normals, vertex_index, original_world_transform,
						original_view_transform);
				}
				if (current_detail_stage) {
					const Vector2 *detail_uvs =
						current_uvs[1] != NULL ? current_uvs[1] : current_uvs[0];
					Emit_Original_Texture_Coordinate(1U, GL_TEXTURE1,
						current_texture_coordinates[1], detail_uvs, vertices,
						normals, vertex_index, original_world_transform,
						original_view_transform);
				}
				/* Preserve the original mesh material color owner.  The former Vita
				** bridge invented RGB from each normal, visibly recoloring otherwise
				** valid NPC skin textures.  DCG is D3D ARGB; when no per-vertex DCG
				** exists, the current pass VertexMaterial diffuse/opacity is
				** authoritative. */
				if (diffuse_colors != NULL) {
					const unsigned diffuse = diffuse_colors[vertex_index];
					glColor4ub(static_cast<GLubyte>((diffuse >> 16U) & 0xffU),
						static_cast<GLubyte>((diffuse >> 8U) & 0xffU),
						static_cast<GLubyte>(diffuse & 0xffU),
						static_cast<GLubyte>((diffuse >> 24U) & 0xffU));
				} else {
					VertexMaterialClass *material =
						model->Peek_Material(static_cast<int>(vertex_index), pass);
					Vector3 diffuse(1.0f, 1.0f, 1.0f);
					Vector3 ambient(0.0f, 0.0f, 0.0f);
					Vector3 emissive(0.0f, 0.0f, 0.0f);
					float opacity = 1.0f;
					if (material != NULL) {
						material->Get_Diffuse(&diffuse);
						material->Get_Ambient(&ambient);
						material->Get_Emissive(&emissive);
						opacity = material->Get_Opacity();
					}
					if (!is_skin && bound_textures[0] != NULL && Is_Near_Black(diffuse)) {
						Vector3 fallback = Max_Color(ambient, emissive);
						if (Is_Near_Black(fallback)) {
							/* Original DX8 lighting would combine scene/material
							** state before texture modulation. Until that full
							** lighting path is represented in vitaGL, keep
							** textured static surfaces visible rather than
							** multiplying valid retail textures by black. */
							fallback = Vector3(1.0f, 1.0f, 1.0f);
						}
						Log_Static_Material_Fallback(mesh, bound_textures[0], material,
							triangle_shader, diffuse, ambient, emissive, fallback, opacity);
						diffuse = fallback;
					}
					glColor4f(Clamp01(diffuse.X), Clamp01(diffuse.Y),
						Clamp01(diffuse.Z), Clamp01(opacity));
				}
				glVertex3f(vertices[vertex_index].X, vertices[vertex_index].Y,
					vertices[vertex_index].Z);
			}
		}
		if (primitive_open) glEnd();
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

	uint32_t checksum = g_statistics.indexed_geometry_checksum;
	checksum = Mix_Checksum(checksum, submission.vertex_format);
	checksum = Mix_Checksum(checksum, submission.vertex_stride);
	checksum = Mix_Checksum(checksum, submission.first_index);
	checksum = Mix_Checksum(checksum, submission.triangle_count);
	checksum = Mix_Checksum(checksum, submission.base_vertex_index);
	checksum = Mix_Checksum(checksum, submission.min_vertex_index);
	checksum = Mix_Checksum(checksum, submission.vertex_count);

	for (uint32_t offset = 0; offset < requested_indices; ++offset) {
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

	glBegin(GL_TRIANGLES);
	for (uint32_t triangle = 0; triangle < submission.triangle_count; ++triangle) {
		for (uint32_t corner = 0; corner < 3U; ++corner) {
			const uint32_t index_offset = triangle * 3U + corner;
			const uint32_t relative_index = submission.index_data[
				submission.first_index + index_offset];
			const uint32_t actual_index = submission.base_vertex_index + relative_index;
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
				submission.world_transform, submission.view_transform);
			Emit_Indexed_Texture_Coordinate(1U, GL_TEXTURE1,
				texture_coordinates[1], uv0, uv1, position, normal,
				submission.world_transform, submission.view_transform);
			glVertex3f(position[0], position[1], position[2]);
		}
	}
	glEnd();
	const uint32_t emitted_triangles = submission.triangle_count;
	Disable_Texture_Stage(1U);

	// The accepted A2.2 Submit_Mesh path emits already-projected coordinates
	// and deliberately remains unchanged.  Restore its identity convention in
	// case both original paths are traversed within one diagnostic frame.
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

bool Capture_Resolved_Frame_RGBA(uint8_t *output, size_t output_bytes)
{
	const size_t required = static_cast<size_t>(DISPLAY_WIDTH) *
		static_cast<size_t>(DISPLAY_HEIGHT) * 4U;
	if (!g_statistics.initialized || output == NULL || output_bytes < required) {
		return false;
	}
#if defined(__vita__)
	(void)glGetError();
	/* vglReadPixels performs GPU-backed readback of the active resolved color
	** target. The runtime invokes this after original WW3D traversal and before
	** the swap, so the clean image is exactly the frame about to be presented. */
	vglReadPixels(0, 0, static_cast<GLsizei>(DISPLAY_WIDTH),
		static_cast<GLsizei>(DISPLAY_HEIGHT), GL_RGBA, GL_UNSIGNED_BYTE, output);
	const GLenum error = glGetError();
	if (error != GL_NO_ERROR) {
		++g_statistics.backend_errors;
		return false;
	}
#else
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
