#pragma once

#include <stddef.h>
#include <stdint.h>

class MeshClass;
class RenderInfoClass;
class RenderObjClass;
class ShaderClass;
class TextureClass;

namespace RenegadeVitaRenderer {

struct Statistics {
	bool initialized;
	uint32_t frames;
	uint32_t mesh_submissions;
	uint32_t skinned_mesh_submissions;
	uint32_t deformed_skin_vertices;
	uint32_t skin_deformation_failures;
	uint32_t vertex_submissions;
	uint32_t triangle_submissions;
	uint32_t unsupported_submissions;
	uint32_t geometry_checksum;
	uint32_t indexed_submissions;
	uint32_t indexed_vertex_references;
	uint32_t indexed_triangle_submissions;
	uint32_t indexed_geometry_checksum;
	uint32_t rejected_indexed_submissions;
	uint64_t indexed_state_applications;
	uint64_t material_passes;
	uint64_t texture_uploads;
	uint64_t texture_binds;
	uint64_t texture_requests;
	uint64_t texture_decodes;
	uint64_t texture_dds_loads;
	uint64_t texture_tga_loads;
	uint64_t texture_missing;
	uint64_t texture_source_missing;
	uint64_t texture_invalid_data;
	uint64_t texture_unsupported_formats;
	uint64_t texture_decode_failures;
	uint64_t texture_upload_failures;
	uint64_t texture_checkerboard_fallbacks;
	uint64_t texture_checkerboard_binds;
	uint64_t texture_invalid_binds;
	uint64_t texture_sampler_updates;
	uint64_t texture_unsupported_stages;
	uint64_t texture_resident;
	uint64_t texture_bytes_resident;
	uint64_t state_changes;
	uint64_t backend_errors;
};

struct BackendMemoryStatistics {
	bool available;
	int64_t system_user_free;
	int64_t system_cdram_free;
	int64_t system_phycont_free;
	uint64_t ram_total;
	uint64_t ram_free;
	uint64_t vram_total;
	uint64_t vram_free;
	uint64_t slow_total;
	uint64_t slow_free;
	uint64_t all_total;
	uint64_t all_free;
};

// vitaGL owns process-lifetime native graphics resources and does not expose
// a matching shutdown operation.  WW3D, however, may have multiple logical
// Init/Shutdown sessions during one process (the retained A2.2 regression
// followed by the live A3.0 world).  Keep those lifetimes explicitly separate
// so a later WW3D session can reactivate known state without calling vglInit a
// second time.
struct BackendLifecycleStatistics {
	bool native_initialization_attempted;
	bool native_backend_ready;
	bool logical_session_active;
	uint32_t native_initialization_calls;
	uint32_t logical_sessions;
	uint32_t logical_shutdowns;
};

// Raw buffer view presented by the original DX8Wrapper draw boundary.  The
// offsets retain Direct3D 8 DrawIndexedPrimitive semantics: indices begin at
// first_index and address vertices relative to base_vertex_index.  The
// min/count pair is the original draw's declared index range, not a request to
// rebase or rewrite the index data.
struct IndexedTriangleSubmission {
	const unsigned char *vertex_data;
	uint32_t vertex_data_size;
	uint32_t vertex_format;
	uint32_t vertex_stride;
	uint32_t vertex_capacity;
	const uint16_t *index_data;
	uint32_t index_capacity;
	uint32_t first_index;
	uint32_t triangle_count;
	uint32_t base_vertex_index;
	uint32_t min_vertex_index;
	uint32_t vertex_count;
	const float *world_transform;
	const float *view_transform;
	const float *projection_transform;
};

// Matrix payload passed to vitaGL's fixed-function transform path.  WW3D's
// DX8Wrapper retains Direct3D row-vector matrices in row-major memory, while
// glLoadMatrixf consumes OpenGL column-major memory.  Keeping the converted
// matrices explicit makes that convention boundary host-testable and, most
// importantly, keeps homogeneous W alive until the GPU performs clipping and
// perspective interpolation.
struct IndexedTransformMatrices {
	float modelview[16];
	float projection[16];
};

// CameraClass expresses its viewport in Direct3D's top-left window
// coordinates. vitaGL accepts the OpenGL lower-left viewport convention and
// performs the display-target Y inversion internally. Keep the resulting
// native viewport explicit so the platform conversion is host-testable.
struct NativeViewport {
	uint32_t x;
	uint32_t y;
	uint32_t width;
	uint32_t height;
	float min_depth;
	float max_depth;
};

enum : uint32_t {
	DISPLAY_WIDTH = 960U,
	DISPLAY_HEIGHT = 544U,
	DISPLAY_BITS = 32U
};

enum IndexedSubmissionResult {
	INDEXED_SUBMISSION_OK = 0,
	INDEXED_SUBMISSION_NOT_INITIALIZED,
	INDEXED_SUBMISSION_INVALID_ARGUMENT,
	INDEXED_SUBMISSION_UNSUPPORTED_FVF,
	INDEXED_SUBMISSION_INDEX_RANGE_ERROR,
	INDEXED_SUBMISSION_VERTEX_RANGE_ERROR,
	INDEXED_SUBMISSION_MISSING_TRANSFORM
};

bool Initialize();
void Shutdown();
void Begin_Frame(float red, float green, float blue);
void End_Frame(bool present);
void Submit_Mesh(MeshClass &mesh, RenderInfoClass &render_info);
void Apply_Indexed_Shader_State(const ShaderClass &shader);
IndexedSubmissionResult Submit_Indexed_Triangles(
	const IndexedTriangleSubmission &submission);
bool Build_Indexed_Transform_Matrices(const float *world_transform,
	const float *view_transform, const float *projection_transform,
	IndexedTransformMatrices &matrices);
bool Build_Native_Viewport(uint32_t d3d_x, uint32_t d3d_y,
	uint32_t width, uint32_t height, float min_depth, float max_depth,
	NativeViewport &viewport);
bool Build_Native_Viewport(uint32_t d3d_x, uint32_t d3d_y,
	uint32_t width, uint32_t height, float min_depth, float max_depth,
	uint32_t logical_width, uint32_t logical_height, NativeViewport &viewport);
bool Apply_Viewport(uint32_t d3d_x, uint32_t d3d_y, uint32_t width,
	uint32_t height, float min_depth, float max_depth);
bool Apply_Viewport(uint32_t d3d_x, uint32_t d3d_y, uint32_t width,
	uint32_t height, float min_depth, float max_depth,
	uint32_t logical_width, uint32_t logical_height);
void Reject_Indexed_Submission(const char *reason, uint32_t vertex_format);
void Record_Texture_Request();
void Record_Texture_Decode();
void Record_Texture_DDS_Load();
void Record_Texture_Targa_Load();
void Record_Texture_Missing();
void Record_Texture_Source_Missing();
void Record_Texture_Invalid_Data();
void Record_Texture_Unsupported_Format();
void Record_Texture_Decode_Failure();
void Record_Texture_Upload_Failure();
void Record_Texture_Checkerboard_Fallback();
void Record_Texture_Checkerboard_Bind();
void Record_Texture_Upload(uint64_t resident_bytes);
void Record_Texture_Release(uint64_t resident_bytes);
bool Bind_Texture(uint32_t native_texture, bool valid);
bool Bind_Texture_Stage(uint32_t stage, uint32_t native_texture, bool valid);
void Disable_Texture_Stage(uint32_t stage);
bool Configure_Texture_Sampler(uint32_t native_texture, bool valid,
	uint32_t address_u, uint32_t address_v, uint32_t min_filter,
	uint32_t mag_filter, uint32_t mip_filter);
bool Configure_Texture_Sampler_Stage(uint32_t stage, uint32_t native_texture,
	bool valid, uint32_t address_u, uint32_t address_v, uint32_t min_filter,
	uint32_t mag_filter, uint32_t mip_filter);
bool Apply_DX8_Texture_Stage_State(uint32_t stage, uint32_t color_op,
	uint32_t color_arg1, uint32_t color_arg2, uint32_t alpha_op,
	uint32_t alpha_arg1, uint32_t alpha_arg2, bool texture_enabled);
bool Apply_DX8_Render_State(uint32_t state, uint32_t value);
void Record_Texture_Unsupported_Stage(uint32_t stage);
void Release_Texture(uint32_t native_texture);
void Submit_Unsupported(RenderObjClass *object);
void Submit_Decals_Unsupported();
bool Capture_Resolved_Frame_RGBA(uint8_t *output, size_t output_bytes);
bool Query_Backend_Memory(BackendMemoryStatistics &memory);
void Reset_Statistics();
const Statistics &Get_Statistics();
const BackendLifecycleStatistics &Get_Backend_Lifecycle_Statistics();

} // namespace RenegadeVitaRenderer
