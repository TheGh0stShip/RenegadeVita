// Platform presentation services for the VitaD3D graphics variant.
//
// In this variant the original WW3D renderer draws through DX8Wrapper and
// VitaD3D, so nothing reaches the native boundary renderer's draw entry points.
// The platform layer still uses the boundary's presentation services: display
// size, statistics, the presentation rectangle and touch mapping. This file
// provides them; draw entry points count the unexpected call and do nothing.

#include "ww3d_vita_renderer.h"

#include "dx8wrapper.h"
#include "statistics.h"
#include "ww3d.h"
#include "a30_vita_runtime.h"

#include <string.h>

namespace RenegadeVitaRenderer {
namespace {

Statistics g_statistics;
BackendLifecycleStatistics g_lifecycle;

struct PresentationRect {
	uint32_t x, y, width, height;
};
PresentationRect g_presentation = {0U, 0U, DISPLAY_WIDTH, DISPLAY_HEIGHT};

void Note_Unreachable(const char *entry)
{
	++g_statistics.unsupported_submissions;
	if (g_statistics.unsupported_submissions == 1U) {
		A30_Vita_Log("[d3dvita] unexpected native renderer entry: %s\n", entry);
	}
}

bool Valid_Rect(uint32_t x, uint32_t y, uint32_t width, uint32_t height)
{
	return width != 0U && height != 0U && x <= DISPLAY_WIDTH && y <= DISPLAY_HEIGHT &&
		width <= DISPLAY_WIDTH - x && height <= DISPLAY_HEIGHT - y;
}

} // namespace

bool Initialize()
{
	g_lifecycle.native_initialization_attempted = true;
	g_lifecycle.native_backend_ready = DX8Wrapper::_Get_D3D_Device8() != NULL;
	return g_lifecycle.native_backend_ready;
}

void Shutdown() {}
void Begin_Frame(float, float, float) { Note_Unreachable("Begin_Frame"); }
void End_Frame(bool) { Note_Unreachable("End_Frame"); }
void Submit_Mesh(MeshClass &, RenderInfoClass &) { Note_Unreachable("Submit_Mesh"); }
void Apply_Indexed_Shader_State(const ShaderClass &, bool, bool)
{
	Note_Unreachable("Apply_Indexed_Shader_State");
}
IndexedSubmissionResult Submit_Indexed_Triangles(const IndexedTriangleSubmission &)
{
	Note_Unreachable("Submit_Indexed_Triangles");
	return INDEXED_SUBMISSION_NOT_INITIALIZED;
}

bool Build_Indexed_Transform_Matrices(const float *, const float *, const float *,
	IndexedTransformMatrices &)
{
	return false;
}

bool Build_Native_Viewport(uint32_t d3d_x, uint32_t d3d_y, uint32_t width, uint32_t height,
	float min_depth, float max_depth, NativeViewport &viewport)
{
	return Build_Native_Viewport(d3d_x, d3d_y, width, height, min_depth, max_depth,
		DISPLAY_WIDTH, DISPLAY_HEIGHT, viewport);
}

bool Build_Native_Viewport(uint32_t d3d_x, uint32_t d3d_y, uint32_t width, uint32_t height,
	float min_depth, float max_depth, uint32_t, uint32_t, NativeViewport &viewport)
{
	// Direct3D's top-left viewport is the native one.
	viewport.x = d3d_x;
	viewport.y = d3d_y;
	viewport.width = width;
	viewport.height = height;
	viewport.min_depth = min_depth;
	viewport.max_depth = max_depth;
	return width != 0U && height != 0U;
}

bool Set_Native_Presentation_Rect(uint32_t x, uint32_t y, uint32_t width, uint32_t height)
{
	if (!Set_Native_Presentation_Rect_Quiet(x, y, width, height)) {
		A30_Vita_Log("[d3dvita] rejected presentation rect %u,%u %ux%u\n", x, y, width, height);
		return false;
	}
	return true;
}

// The platform sets the aspect-preserving rectangle for a logical WW3D
// resolution; VitaD3D letterboxes that back buffer into the same rectangle,
// so touch input maps through it.
bool Set_Native_Presentation_Rect_Quiet(uint32_t x, uint32_t y, uint32_t width, uint32_t height)
{
	if (!Valid_Rect(x, y, width, height)) return false;
	g_presentation.x = x;
	g_presentation.y = y;
	g_presentation.width = width;
	g_presentation.height = height;
	return true;
}

void Reset_Native_Presentation_Rect()
{
	Reset_Native_Presentation_Rect_Quiet();
}

void Reset_Native_Presentation_Rect_Quiet()
{
	g_presentation.x = 0U;
	g_presentation.y = 0U;
	g_presentation.width = DISPLAY_WIDTH;
	g_presentation.height = DISPLAY_HEIGHT;
}

bool Map_Native_Pixel_To_Logical(float x, float y, float logical_width, float logical_height,
	float &logical_x, float &logical_y)
{
	const float left = static_cast<float>(g_presentation.x);
	const float top = static_cast<float>(g_presentation.y);
	const float width = static_cast<float>(g_presentation.width);
	const float height = static_cast<float>(g_presentation.height);
	if (x < left || y < top || x >= left + width || y >= top + height) return false;
	logical_x = (x - left) * logical_width / width;
	logical_y = (y - top) * logical_height / height;
	return true;
}

bool Apply_Viewport(uint32_t d3d_x, uint32_t d3d_y, uint32_t width, uint32_t height,
	float min_depth, float max_depth)
{
	return Apply_Viewport(d3d_x, d3d_y, width, height, min_depth, max_depth,
		DISPLAY_WIDTH, DISPLAY_HEIGHT);
}

bool Apply_Viewport(uint32_t d3d_x, uint32_t d3d_y, uint32_t width, uint32_t height,
	float min_depth, float max_depth, uint32_t, uint32_t)
{
	D3DVIEWPORT8 viewport = {d3d_x, d3d_y, width, height, min_depth, max_depth};
	DX8Wrapper::Set_Viewport(&viewport);
	return true;
}

void Reject_Indexed_Submission(const char *reason, uint32_t vertex_format)
{
	++g_statistics.rejected_indexed_submissions;
	if (g_statistics.rejected_indexed_submissions == 1U) {
		A30_Vita_Log("[d3dvita] rejected submission %s fvf=%08X\n",
			reason ? reason : "", static_cast<unsigned>(vertex_format));
	}
}

void Record_Texture_Request() { ++g_statistics.texture_requests; }
void Record_Texture_Decode() { ++g_statistics.texture_decodes; }
void Record_Texture_DDS_Load() { ++g_statistics.texture_dds_loads; }
void Record_Texture_Targa_Load() { ++g_statistics.texture_tga_loads; }
void Record_Texture_Missing() { ++g_statistics.texture_missing; }
void Record_Texture_Source_Missing() { ++g_statistics.texture_source_missing; }
void Record_Texture_Invalid_Data() { ++g_statistics.texture_invalid_data; }
void Record_Texture_Unsupported_Format() { ++g_statistics.texture_unsupported_formats; }
void Record_Texture_Decode_Failure() { ++g_statistics.texture_decode_failures; }
void Record_Texture_Upload_Failure() { ++g_statistics.texture_upload_failures; }
void Record_Texture_Checkerboard_Fallback() { ++g_statistics.texture_checkerboard_fallbacks; }
void Record_Texture_Checkerboard_Bind() { ++g_statistics.texture_checkerboard_binds; }
void Record_Texture_Upload(uint64_t resident_bytes)
{
	++g_statistics.texture_uploads;
	++g_statistics.texture_resident;
	g_statistics.texture_bytes_resident += resident_bytes;
}
void Record_Texture_Release(uint64_t resident_bytes)
{
	if (g_statistics.texture_resident != 0U) --g_statistics.texture_resident;
	g_statistics.texture_bytes_resident -=
		resident_bytes < g_statistics.texture_bytes_resident ? resident_bytes
		                                                     : g_statistics.texture_bytes_resident;
}

// DX8Wrapper owns texture binding here and keeps its cache coherent.
void Invalidate_Texture_State_Cache() {}

bool Use_Direct_Text_Atlas_Upload() { return false; }
bool Use_Native_DDS_Upload() { return false; }
bool Bind_Texture(uint32_t, bool) { Note_Unreachable("Bind_Texture"); return false; }
bool Bind_Texture_Stage(uint32_t, uint32_t, bool) { Note_Unreachable("Bind_Texture_Stage"); return false; }
void Disable_Texture_Stage(uint32_t) {}
bool Configure_Texture_Sampler(uint32_t, bool, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t)
{
	return false;
}
bool Configure_Texture_Sampler_Stage(uint32_t, uint32_t, bool, uint32_t, uint32_t, uint32_t,
	uint32_t, uint32_t)
{
	return false;
}
bool Apply_DX8_Texture_Stage_State(uint32_t, uint32_t, uint32_t, uint32_t, uint32_t, uint32_t,
	uint32_t, bool)
{
	return false;
}
bool Apply_DX8_Render_State(uint32_t, uint32_t) { return false; }
void Record_Texture_Unsupported_Stage(uint32_t) { ++g_statistics.texture_unsupported_stages; }
void Release_Texture(uint32_t) {}
void Submit_Unsupported(RenderObjClass *) { Note_Unreachable("Submit_Unsupported"); }
void Submit_Decals_Unsupported() { Note_Unreachable("Submit_Decals_Unsupported"); }

// Reads the presented frame through IDirect3DDevice8::GetFrontBuffer at the
// current back-buffer size and lays it into the 960x544 RGBA8888 capture
// (bottom-up rows, as the native renderer's readback produced) with the same
// aspect-preserving letterbox VitaD3D presents.
bool Capture_Resolved_Frame_RGBA(uint8_t *output, size_t output_bytes, bool)
{
	const size_t required = static_cast<size_t>(DISPLAY_WIDTH) * DISPLAY_HEIGHT * 4U;
	IDirect3DDevice8 *device = DX8Wrapper::_Get_D3D_Device8();
	if (output == NULL || output_bytes < required || device == NULL) return false;
	int width = 0, height = 0, bits = 0;
	bool windowed = false;
	WW3D::Get_Device_Resolution(width, height, bits, windowed);
	if (width <= 0 || height <= 0) return false;
	IDirect3DSurface8 *surface = NULL;
	if (device->CreateImageSurface(width, height, D3DFMT_A8R8G8B8, &surface) != D3D_OK) return false;
	D3DLOCKED_RECT locked;
	bool ok = device->GetFrontBuffer(surface) == D3D_OK &&
		surface->LockRect(&locked, NULL, D3DLOCK_READONLY) == D3D_OK;
	if (ok) {
		memset(output, 0, required);
		const float scale_x = static_cast<float>(DISPLAY_WIDTH) / static_cast<float>(width);
		const float scale_y = static_cast<float>(DISPLAY_HEIGHT) / static_cast<float>(height);
		const float scale = scale_x < scale_y ? scale_x : scale_y;
		const float left = (static_cast<float>(DISPLAY_WIDTH) - width * scale) * 0.5F;
		const float top = (static_cast<float>(DISPLAY_HEIGHT) - height * scale) * 0.5F;
		for (uint32_t y = 0; y < DISPLAY_HEIGHT; ++y) {
			const int sy = static_cast<int>((y + 0.5F - top) / scale);
			if (sy < 0 || sy >= height) continue;
			const uint32_t *row = reinterpret_cast<const uint32_t *>(
				static_cast<const uint8_t *>(locked.pBits) + sy * locked.Pitch);
			uint8_t *out = output + static_cast<size_t>(DISPLAY_HEIGHT - 1U - y) * DISPLAY_WIDTH * 4U;
			for (uint32_t x = 0; x < DISPLAY_WIDTH; ++x) {
				const int sx = static_cast<int>((x + 0.5F - left) / scale);
				if (sx < 0 || sx >= width) continue;
				const uint32_t argb = row[sx];
				out[x * 4U + 0U] = static_cast<uint8_t>(argb >> 16);
				out[x * 4U + 1U] = static_cast<uint8_t>(argb >> 8);
				out[x * 4U + 2U] = static_cast<uint8_t>(argb);
				out[x * 4U + 3U] = static_cast<uint8_t>(argb >> 24);
			}
		}
		surface->UnlockRect();
	}
	surface->Release();
	return ok;
}

bool Query_Backend_Memory(BackendMemoryStatistics &memory)
{
	memset(&memory, 0, sizeof(memory));
	return false;
}

void Reset_Statistics()
{
	memset(&g_statistics, 0, sizeof(g_statistics));
}

const Statistics &Get_Statistics()
{
	g_statistics.initialized = DX8Wrapper::_Get_D3D_Device8() != NULL;
	g_statistics.frames = static_cast<uint32_t>(WW3D::Get_Frame_Count());
	// The original renderer's own per-frame statistics for the last completed
	// frame: Direct3D calls stand in for mesh submissions, and polygons and
	// vertices include skinned and sorted geometry.
	g_statistics.mesh_submissions = DX8Wrapper::Get_Last_Frame_DX8_Calls();
	g_statistics.triangle_submissions = static_cast<uint32_t>(
		Debug_Statistics::Get_DX8_Polygons() + Debug_Statistics::Get_DX8_Skin_Polygons() +
		Debug_Statistics::Get_Sorting_Polygons());
	g_statistics.vertex_submissions = static_cast<uint32_t>(
		Debug_Statistics::Get_DX8_Vertices() + Debug_Statistics::Get_DX8_Skin_Vertices() +
		Debug_Statistics::Get_Sorting_Vertices());
	return g_statistics;
}

const BackendLifecycleStatistics &Get_Backend_Lifecycle_Statistics()
{
	g_lifecycle.native_backend_ready = DX8Wrapper::_Get_D3D_Device8() != NULL;
	g_lifecycle.logical_session_active = g_lifecycle.native_backend_ready;
	return g_lifecycle;
}

} // namespace RenegadeVitaRenderer

#include "renegade_user_root.h"
#include "vita_runtime_log.h"

#include <stdio.h>
#include <stdlib.h>

// Bring-up evidence: the presented frame at a few early gameplay frames,
// written as 24-bit BMPs under the variant's capture directory.
void D3DVita_Capture_Gameplay_Frame(unsigned frame)
{
	if (frame != 30U && frame != 120U && frame != 300U) return;
	const size_t bytes = static_cast<size_t>(RenegadeVitaRenderer::DISPLAY_WIDTH) *
		RenegadeVitaRenderer::DISPLAY_HEIGHT * 4U;
	uint8_t *rgba = static_cast<uint8_t *>(malloc(bytes));
	if (rgba == NULL) return;
	char path[128];
	snprintf(path, sizeof(path), RENEGADE_VITA_USER_ROOT "/captures/d3dvita-gameplay-f%u.bmp", frame);
	bool written = false;
	if (RenegadeVitaRenderer::Capture_Resolved_Frame_RGBA(rgba, bytes, true)) {
		if (FILE *file = fopen(path, "wb")) {
			const uint32_t width = RenegadeVitaRenderer::DISPLAY_WIDTH;
			const uint32_t height = RenegadeVitaRenderer::DISPLAY_HEIGHT;
			const uint32_t image = width * height * 3U;
			uint8_t header[54] = {'B', 'M'};
			auto put32 = [&](unsigned at, uint32_t v) {
				for (unsigned i = 0; i < 4; ++i) header[at + i] = static_cast<uint8_t>(v >> (8 * i));
			};
			put32(2, 54U + image); put32(10, 54U); put32(14, 40U);
			put32(18, width); put32(22, height);
			header[26] = 1; header[28] = 24; put32(34, image);
			fwrite(header, 1, sizeof(header), file);
			// The capture rows are already bottom-up, as BMP stores them.
			uint8_t row[960 * 3];
			for (uint32_t y = 0; y < height; ++y) {
				const uint8_t *src = rgba + static_cast<size_t>(y) * width * 4U;
				for (uint32_t x = 0; x < width; ++x) {
					row[x * 3 + 0] = src[x * 4 + 2];
					row[x * 3 + 1] = src[x * 4 + 1];
					row[x * 3 + 2] = src[x * 4 + 0];
				}
				fwrite(row, 1, width * 3U, file);
			}
			fclose(file);
			written = true;
		}
	}
	free(rgba);
	Vita_Append_A22_Runtime_Breadcrumb("d3dvita", "gameplay capture frame=%u written=%d path=%s",
		frame, written ? 1 : 0, path);
}

