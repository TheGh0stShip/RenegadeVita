#include "camera.h"
#include "dx8caps.h"
#include "dx8wrapper.h"
#include "ww3d.h"
#include "ww3d_vita_renderer.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

namespace {

bool Near(float left, float right)
{
	return fabsf(left - right) < 0.00001f;
}

bool Matrix_Near(const float *left, const Matrix4 &right)
{
	for (unsigned row = 0; row < 4U; ++row) {
		for (unsigned column = 0; column < 4U; ++column) {
			if (!Near(left[row * 4U + column], right[row][column])) {
				return false;
			}
		}
	}
	return true;
}

bool Matrix_Near(const Matrix4 &left, const Matrix4 &right)
{
	return Matrix_Near(&left[0].X, right);
}

bool Check(bool condition, const char *label, unsigned &checks)
{
	++checks;
	printf("%s: %s\n", label, condition ? "PASS" : "FAIL");
	return condition;
}

bool Same_Viewport(const D3DVIEWPORT8 &left, const D3DVIEWPORT8 &right)
{
	return left.X == right.X && left.Y == right.Y &&
		left.Width == right.Width && left.Height == right.Height &&
		Near(left.MinZ, right.MinZ) && Near(left.MaxZ, right.MaxZ);
}

} // namespace

int main()
{
	unsigned checks = 0;
	unsigned failures = 0;
	failures += !Check(RenegadeVitaRenderer::Initialize(),
		"renderer initialization", checks);

	const DX8Caps *caps = DX8Wrapper::Get_Current_Caps();
	failures += !Check(caps != NULL, "original DX8Caps object", checks);
	failures += !Check(caps != NULL && caps->Support_TnL(),
		"native vertex transform capability", checks);
	failures += !Check(caps != NULL && !caps->Support_ZBias() &&
		!caps->Support_DXTC() && !caps->Support_Gamma() &&
		!caps->Support_NPatches() && !caps->Support_Bump_Envmap() &&
		!caps->Support_Bump_Envmap_Luminance() &&
		!caps->Support_Anisotropic_Filtering() &&
		!caps->Can_Do_Multi_Pass() && !caps->Is_Fog_Allowed(),
		"unmapped capabilities remain conservative", checks);
	failures += !Check(caps != NULL && caps->Get_Max_Textures_Per_Pass() == 0,
		"unmapped texture stages are not advertised", checks);

	int width = 0;
	int height = 0;
	int bits = 0;
	bool windowed = true;
	WW3D::Get_Render_Target_Resolution(width, height, bits, windowed);
	failures += !Check(width == 960 && height == 544 && bits == 32 && !windowed,
		"default/null render target uses native display", checks);

	RenegadeVitaRenderer::NativeViewport native = {};
	failures += !Check(RenegadeVitaRenderer::Build_Native_Viewport(
		240U, 68U, 480U, 272U, 0.2f, 0.8f, native) &&
		native.x == 240U && native.y == 204U && native.width == 480U &&
		native.height == 272U && Near(native.min_depth, 0.2f) &&
		Near(native.max_depth, 0.8f),
		"D3D top-left viewport converts to vitaGL lower-left", checks);
	failures += !Check(!RenegadeVitaRenderer::Build_Native_Viewport(
		0U, 0U, 0U, 544U, 0.0f, 1.0f, native) &&
		!RenegadeVitaRenderer::Build_Native_Viewport(
		900U, 0U, 61U, 544U, 0.0f, 1.0f, native) &&
		!RenegadeVitaRenderer::Build_Native_Viewport(
		0U, 0U, 960U, 544U, -0.1f, 1.0f, native) &&
		!RenegadeVitaRenderer::Build_Native_Viewport(
		0U, 0U, 960U, 544U, 0.8f, 0.2f, native),
		"invalid viewport/depth ranges are rejected", checks);

	CameraClass camera;
	camera.Set_Viewport(Vector2(0.25f, 0.125f), Vector2(0.75f, 0.625f));
	camera.Set_Depth_Range(0.2f, 0.8f);
	camera.Set_Clip_Planes(0.5f, 500.0f);
	camera.Set_Aspect_Ratio(960.0f / 544.0f);
	Matrix3D camera_transform(1);
	camera_transform.Set_Translation(Vector3(3.0f, -2.0f, 7.0f));
	camera.Set_Transform(camera_transform);

	// This original setter updates the same retained ZBias scalar without
	// requiring the still-unmapped native D3DRS_ZBIAS branch. Camera::Apply
	// subsequently exercises Set_Projection_Transform_With_Z_Bias's 1/16 path.
	DX8Wrapper::Set_Pseudo_ZBias(8);
	camera.Apply();

	IDirect3DDevice8 *device = DX8Wrapper::_Get_D3D_Device8();
	D3DVIEWPORT8 d3d_viewport = {};
	failures += !Check(device != NULL &&
		device->GetViewport(&d3d_viewport) == D3D_OK &&
		d3d_viewport.X == 240U && d3d_viewport.Y == 68U &&
		d3d_viewport.Width == 480U && d3d_viewport.Height == 272U,
		"original CameraClass applied D3D viewport", checks);
	failures += !Check(Near(d3d_viewport.MinZ, 0.2f) &&
		Near(d3d_viewport.MaxZ, 0.8f),
		"original CameraClass applied depth range", checks);

	Matrix4 original_projection;
	camera.Get_D3D_Projection_Matrix(&original_projection);
	Matrix4 expected_projection = original_projection.Transpose();
	const float expected_bias = (8.0f / 16.0f) / (500.0f - 0.5f);
	expected_projection[2][2] -= expected_bias * expected_projection[3][2];
	D3DMATRIX device_projection = {};
	failures += !Check(device->GetTransform(D3DTS_PROJECTION,
		&device_projection) == D3D_OK &&
		Matrix_Near(&device_projection.m[0][0], expected_projection),
		"original pseudo-Z-bias projection retained", checks);
	failures += !Check(!Matrix_Near(expected_projection,
		original_projection.Transpose()),
		"conservative caps select projection-bias path", checks);

	Matrix3D original_view;
	camera.Get_View_Matrix(&original_view);
	const Matrix4 expected_view = Matrix4(original_view).Transpose();
	RenderStateStruct render_state;
	DX8Wrapper::Get_Render_State(render_state);
	failures += !Check(Matrix_Near(render_state.view, expected_view),
		"original CameraClass view reaches DX8Wrapper state", checks);

	const Matrix4 identity(true);
	DX8Wrapper::Set_Transform(D3DTS_WORLD, identity);
	DX8Wrapper::Get_Render_State(render_state);
	RenegadeVitaRenderer::IndexedTransformMatrices indexed_matrices = {};
	failures += !Check(RenegadeVitaRenderer::Build_Indexed_Transform_Matrices(
		&render_state.world[0].X, &render_state.view[0].X,
		&device_projection.m[0][0], indexed_matrices),
		"camera state feeds original indexed draw boundary", checks);

	const D3DVIEWPORT8 retained_viewport = d3d_viewport;
	D3DVIEWPORT8 invalid_viewport = retained_viewport;
	invalid_viewport.Width = 721U;
	failures += !Check(device->SetViewport(NULL) ==
		static_cast<HRESULT>(D3DERR_INVALIDCALL) &&
		device->SetViewport(&invalid_viewport) ==
		static_cast<HRESULT>(D3DERR_INVALIDCALL) &&
		device->GetViewport(&d3d_viewport) == D3D_OK &&
		Same_Viewport(d3d_viewport, retained_viewport),
		"invalid viewport leaves applied state intact", checks);
	failures += !Check(device->GetViewport(NULL) ==
		static_cast<HRESULT>(D3DERR_INVALIDCALL),
		"null viewport query is rejected", checks);

	DX8Wrapper::Set_Pseudo_ZBias(0);
	RenegadeVitaRenderer::Shutdown();
	printf("A3 original Camera/DX8 capability boundary: %u checks, %u failures\n",
		checks, failures);
	return failures == 0 ? 0 : 1;
}
