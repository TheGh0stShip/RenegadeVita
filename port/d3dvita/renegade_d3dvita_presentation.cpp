// Platform presentation services for the VitaD3D graphics variant.
//
// In this variant the original WW3D renderer draws through DX8Wrapper and
// VitaD3D, so nothing reaches the native boundary renderer's draw entry points.
// The platform layer still uses the boundary's presentation services: display
// size, statistics, the presentation rectangle and touch mapping. This file
// provides them; draw entry points count the unexpected call and do nothing.

#include "ww3d_vita_renderer.h"

#include "dx8wrapper.h"
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

bool Capture_Resolved_Frame_RGBA(uint8_t *, size_t, bool)
{
	// Frame capture reads the native colour surface; not provided here.
	return false;
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
	return g_statistics;
}

const BackendLifecycleStatistics &Get_Backend_Lifecycle_Statistics()
{
	g_lifecycle.native_backend_ready = DX8Wrapper::_Get_D3D_Device8() != NULL;
	g_lifecycle.logical_session_active = g_lifecycle.native_backend_ready;
	return g_lifecycle;
}

} // namespace RenegadeVitaRenderer
