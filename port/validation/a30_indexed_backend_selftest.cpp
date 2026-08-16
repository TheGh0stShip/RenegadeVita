#include "ww3d_vita_renderer.h"

#include <math.h>
#include <stdio.h>

namespace {

struct VertexXYZNDUV1 {
	float x, y, z;
	float nx, ny, nz;
	uint32_t diffuse;
	float u, v;
};

static_assert(sizeof(VertexXYZNDUV1) == 36,
	"WW3D XYZNDUV1 must retain its 36-byte ILP32 disk/runtime layout");

void Set_Identity(float matrix[16])
{
	for (unsigned index = 0; index < 16; ++index) {
		matrix[index] = 0.0f;
	}
	matrix[0] = matrix[5] = matrix[10] = matrix[15] = 1.0f;
}

void Transform_D3D_Row(const float matrix[16], const float input[4],
	float output[4])
{
	for (unsigned column = 0; column < 4U; ++column) {
		output[column] = input[0] * matrix[column] +
			input[1] * matrix[4U + column] +
			input[2] * matrix[8U + column] +
			input[3] * matrix[12U + column];
	}
}

// Emulate vitaGL's glLoadMatrixf implementation: the API's column-major
// input is transposed into an internal matrix and its FFP shader evaluates
// matrix * column-vector.
void Transform_VitaGL_Loaded(const float matrix_input[16],
	const float input[4], float output[4])
{
	for (unsigned row = 0; row < 4U; ++row) {
		output[row] = matrix_input[row] * input[0] +
			matrix_input[4U + row] * input[1] +
			matrix_input[8U + row] * input[2] +
			matrix_input[12U + row] * input[3];
	}
}

bool Near(float left, float right)
{
	return fabsf(left - right) < 0.00001f;
}

bool Check(bool condition, const char *label, unsigned &checks)
{
	++checks;
	printf("%s: %s\n", label, condition ? "PASS" : "FAIL");
	return condition;
}

} // namespace

int main()
{
	unsigned checks = 0;
	unsigned failures = 0;
	if (!RenegadeVitaRenderer::Initialize()) {
		fprintf(stderr, "renderer initialization unexpectedly failed\n");
		return 1;
	}
	RenegadeVitaRenderer::Reset_Statistics();

	VertexXYZNDUV1 vertices[8] = {};
	for (unsigned index = 0; index < 8; ++index) {
		vertices[index].x = static_cast<float>(index);
		vertices[index].y = static_cast<float>(index * 2U);
		vertices[index].z = -static_cast<float>(index + 1U);
		vertices[index].nx = 0.0f;
		vertices[index].ny = 0.0f;
		vertices[index].nz = 1.0f;
		vertices[index].diffuse = 0xff000000U | (index * 0x00010101U);
		vertices[index].u = static_cast<float>(index) / 8.0f;
		vertices[index].v = 1.0f - vertices[index].u;
	}

	// Three leading indices are outside the submitted range.  The actual draw
	// starts at index 3, and raw 1/2/3 address vertices 3/4/5 through base 2.
	const uint16_t indices[] = { 7, 7, 7, 1, 2, 3 };
	float identity[16];
	Set_Identity(identity);

	RenegadeVitaRenderer::IndexedTriangleSubmission submission = {};
	submission.vertex_data = reinterpret_cast<const unsigned char *>(vertices);
	submission.vertex_data_size = sizeof(vertices);
	submission.vertex_format = 0x00000152U;
	submission.vertex_stride = sizeof(VertexXYZNDUV1);
	submission.vertex_capacity = 8;
	submission.index_data = indices;
	submission.index_capacity = sizeof(indices) / sizeof(indices[0]);
	submission.first_index = 3;
	submission.triangle_count = 1;
	submission.base_vertex_index = 2;
	submission.min_vertex_index = 1;
	submission.vertex_count = 3;
	submission.world_transform = identity;
	submission.view_transform = identity;
	submission.projection_transform = identity;

	const RenegadeVitaRenderer::IndexedSubmissionResult success =
		RenegadeVitaRenderer::Submit_Indexed_Triangles(submission);
	const RenegadeVitaRenderer::Statistics &after_success =
		RenegadeVitaRenderer::Get_Statistics();
	failures += !Check(success == RenegadeVitaRenderer::INDEXED_SUBMISSION_OK,
		"indexed submission result", checks);
	failures += !Check(after_success.indexed_submissions == 1,
		"submission counter", checks);
	failures += !Check(after_success.indexed_vertex_references == 3,
		"index start/base semantics", checks);
	failures += !Check(after_success.indexed_triangle_submissions == 1,
		"triangle counter", checks);
	failures += !Check(after_success.indexed_geometry_checksum == 0x65e5f668U,
		"semantic geometry fingerprint", checks);

	RenegadeVitaRenderer::IndexedTriangleSubmission unsupported = submission;
	unsupported.vertex_format = 0x00000112U;
	failures += !Check(RenegadeVitaRenderer::Submit_Indexed_Triangles(unsupported) ==
		RenegadeVitaRenderer::INDEXED_SUBMISSION_UNSUPPORTED_FVF,
		"unsupported FVF rejected", checks);

	RenegadeVitaRenderer::IndexedTriangleSubmission bad_index_range = submission;
	bad_index_range.first_index = 4;
	failures += !Check(RenegadeVitaRenderer::Submit_Indexed_Triangles(bad_index_range) ==
		RenegadeVitaRenderer::INDEXED_SUBMISSION_INDEX_RANGE_ERROR,
		"index bounds rejected", checks);

	uint16_t bad_indices[] = { 0, 4, 2 };
	RenegadeVitaRenderer::IndexedTriangleSubmission bad_vertex_range = submission;
	bad_vertex_range.index_data = bad_indices;
	bad_vertex_range.index_capacity = 3;
	bad_vertex_range.first_index = 0;
	failures += !Check(RenegadeVitaRenderer::Submit_Indexed_Triangles(bad_vertex_range) ==
		RenegadeVitaRenderer::INDEXED_SUBMISSION_VERTEX_RANGE_ERROR,
		"declared vertex bounds rejected", checks);

	const RenegadeVitaRenderer::Statistics &final_statistics =
		RenegadeVitaRenderer::Get_Statistics();
	failures += !Check(final_statistics.indexed_submissions == 1 &&
		final_statistics.rejected_indexed_submissions == 3 &&
		final_statistics.unsupported_submissions == 1,
		"success/rejection accounting", checks);

	// Non-trivial D3D row-vector transforms prove the production conversion
	// preserves homogeneous W.  The old CPU pre-divide path would force W=1
	// before vitaGL and could not satisfy this contract.
	const float world[16] = {
		1, 0, 0, 0,
		0, 1, 0, 0,
		0, 0, 1, 0,
		2, -1, 1, 1
	};
	const float view[16] = {
		1, 0, 0, 0,
		0, 2, 0, 0,
		0, 0, 1, 0,
		-3, 4, 2, 1
	};
	const float d3d_projection[16] = {
		2, 0, 0, 0,
		0, 3, 0, 0,
		0, 0, 0.75f, 1,
		0, 0, 0.25f, 0
	};
	RenegadeVitaRenderer::IndexedTransformMatrices matrices = {};
	const bool matrices_ready =
		RenegadeVitaRenderer::Build_Indexed_Transform_Matrices(
			world, view, d3d_projection, matrices);
	failures += !Check(matrices_ready, "homogeneous matrix conversion", checks);

	const float object_position[4] = { 1, 2, 3, 1 };
	float d3d_world[4], d3d_view[4], d3d_clip[4];
	Transform_D3D_Row(world, object_position, d3d_world);
	Transform_D3D_Row(view, d3d_world, d3d_view);
	Transform_D3D_Row(d3d_projection, d3d_view, d3d_clip);
	float gl_view[4], gl_clip[4];
	Transform_VitaGL_Loaded(matrices.modelview, object_position, gl_view);
	Transform_VitaGL_Loaded(matrices.projection, gl_view, gl_clip);
	failures += !Check(Near(gl_clip[0], d3d_clip[0]) &&
		Near(gl_clip[1], d3d_clip[1]) &&
		Near(gl_clip[2], 2.0f * d3d_clip[2] - d3d_clip[3]) &&
		Near(gl_clip[3], d3d_clip[3]) && !Near(gl_clip[3], 1.0f),
		"D3D row convention and homogeneous W preserved", checks);
	failures += !Check(Near(gl_clip[2] / gl_clip[3],
		2.0f * (d3d_clip[2] / d3d_clip[3]) - 1.0f),
		"D3D-to-OpenGL clip-depth mapping", checks);

	// At equal screen-space weight, UVs attached to W=2 and W=4 must resolve
	// to 1/3, not the affine 1/2 produced after CPU pre-division.
	const float perspective_uv = (0.5f * 0.0f / 2.0f + 0.5f * 1.0f / 4.0f) /
		(0.5f / 2.0f + 0.5f / 4.0f);
	failures += !Check(Near(perspective_uv, 1.0f / 3.0f) &&
		!Near(perspective_uv, 0.5f), "perspective interpolation retained", checks);

	float zero[16] = {};
	failures += !Check(!RenegadeVitaRenderer::Build_Indexed_Transform_Matrices(
		zero, view, d3d_projection, matrices),
		"missing transform rejected on host", checks);

	printf("A3 indexed backend: %u checks, %u failures, checksum=%08X\n",
		checks, failures, final_statistics.indexed_geometry_checksum);
	RenegadeVitaRenderer::Shutdown();
	return failures == 0 ? 0 : 1;
}
