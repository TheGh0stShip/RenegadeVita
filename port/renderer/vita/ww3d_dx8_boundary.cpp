// Vita implementation of the legacy DX8 platform edge retained by original
// WW3D. Engine-owned buffers and draw calls remain unchanged above this file;
// this boundary translates their CPU-backed DX8-shaped handles for the native
// renderer without implementing or emulating Direct3D itself.

#include "dx8wrapper.h"
#include "ww3d_vita_renderer.h"
#include "ddsfile.h"
#include "formconv.h"
#include "render2d.h"
#include "texture.h"
#include "texture_upload_contract.h"
#include "targa.h"
#include "ww3dformat.h"

#include <new>
#include <stdio.h>
#include <string.h>
#include <vector>

#if defined(__vita__)
#include "vita_runtime_log.h"
#include <vitaGL.h>
#endif

namespace {

IDirect3DDevice8 g_boundary_device;
D3DMATRIX g_boundary_transforms[257] = {};
D3DVIEWPORT8 g_boundary_viewport = {
	0U, 0U, RenegadeVitaRenderer::DISPLAY_WIDTH,
	RenegadeVitaRenderer::DISPLAY_HEIGHT, 0.0f, 1.0f
};
uint32_t g_logical_viewport_width = RenegadeVitaRenderer::DISPLAY_WIDTH;
uint32_t g_logical_viewport_height = RenegadeVitaRenderer::DISPLAY_HEIGHT;
const D3DCAPS8 g_vita_caps_description = {};
const D3DADAPTER_IDENTIFIER8 g_vita_adapter_description = {};

struct TextureStageSamplerState {
	DWORD address_u;
	DWORD address_v;
	DWORD min_filter;
	DWORD mag_filter;
	DWORD mip_filter;
};

TextureStageSamplerState g_texture_sampler_states[MAX_TEXTURE_STAGES] = {};
IDirect3DBaseTexture8 *g_texture_stage_textures[MAX_TEXTURE_STAGES] = {};
// This cache owns one permanent reference for the native renderer's process
// lifetime.  Failed TextureClass requests receive a separate AddRef(), so an
// ordinary caller release cannot leave the cache dangling or delete a texture
// still bound by another failed material.
IDirect3DTexture8 *g_checkerboard_fallback = NULL;

bool Apply_Texture_Stage_Sampler(DWORD stage)
{
	if (stage >= MAX_TEXTURE_STAGES) return false;
	IDirect3DBaseTexture8 *texture = g_texture_stage_textures[stage];
	if (texture == NULL) return true;
	const TextureStageSamplerState &sampler = g_texture_sampler_states[stage];
	return RenegadeVitaRenderer::Configure_Texture_Sampler(texture->NativeTexture,
		texture->Uploaded && texture->NativeTexture != 0U, sampler.address_u,
		sampler.address_v, sampler.min_filter, sampler.mag_filter,
		sampler.mip_filter);
}

bool Is_DX8_Buffer_Type(unsigned type)
{
	return type == BUFFER_TYPE_DX8 || type == BUFFER_TYPE_DYNAMIC_DX8;
}

uint32_t Mix_Texture_Checksum(uint32_t checksum, uint32_t value)
{
	return (checksum ^ value) * 16777619U;
}

bool Filename_Has_Extension(const char *filename, const char *extension)
{
	if (filename == NULL || extension == NULL) return false;
	const size_t filename_length = strlen(filename);
	const size_t extension_length = strlen(extension);
	if (filename_length < extension_length) return false;
	return stricmp(filename + filename_length - extension_length, extension) == 0;
}

bool Texture_Format_Has_Alpha(WW3DFormat format)
{
	return format == WW3D_FORMAT_DXT2 || format == WW3D_FORMAT_DXT3 ||
		format == WW3D_FORMAT_DXT4 || format == WW3D_FORMAT_DXT5;
}

bool Texture_Format_Is_Supported(WW3DFormat format)
{
	return format == WW3D_FORMAT_DXT1 || format == WW3D_FORMAT_DXT2 ||
		format == WW3D_FORMAT_DXT3 || format == WW3D_FORMAT_DXT4 ||
		format == WW3D_FORMAT_DXT5;
}

IDirect3DTexture8 *Create_Checkerboard_Fallback();

void Log_Texture_Fallback(const char *reason, const char *filename)
{
#if defined(__vita__)
	static unsigned logged_count = 0U;
	if (logged_count >= 16U) return;
	Vita_Append_A22_Runtime_Breadcrumb("texture-load",
		"texture fallback: reason=%s name=%s",
		reason != NULL ? reason : "unknown",
		filename != NULL ? filename : "(null)");
	++logged_count;
#else
	(void)reason;
	(void)filename;
#endif
}

void Log_Texture_Load(const char *source, const char *filename,
	const IDirect3DTexture8 *texture)
{
#if defined(__vita__)
	static unsigned logged_count = 0U;
	if (logged_count >= 24U || texture == NULL) return;
	Vita_Append_A22_Runtime_Breadcrumb("texture-load",
		"texture loaded: source=%s name=%s size=%ux%u mips=%u fmt=%08X bytes=%llu checksum=%08X alpha=%u fallback=%u native=%u",
		source != NULL ? source : "unknown",
		filename != NULL ? filename : "(null)",
		texture->Width, texture->Height, texture->MipLevels,
		texture->SourceFormat,
		static_cast<unsigned long long>(texture->ResidentBytes),
		texture->PixelChecksum, texture->HasAlpha ? 1U : 0U,
		texture->DiagnosticFallback ? 1U : 0U, texture->NativeTexture);
	++logged_count;
#else
	(void)source;
	(void)filename;
	(void)texture;
#endif
}

unsigned Surface_Bytes_Per_Pixel(D3DFORMAT format)
{
	switch (format) {
	case D3DFMT_A8R8G8B8:
	case D3DFMT_X8R8G8B8: return 4U;
	case D3DFMT_R8G8B8: return 3U;
	case D3DFMT_R5G6B5:
	case D3DFMT_X1R5G5B5:
	case D3DFMT_A1R5G5B5:
	case D3DFMT_A4R4G4B4:
	case D3DFMT_A8R3G3B2:
	case D3DFMT_X4R4G4B4:
	case D3DFMT_A8P8:
	case D3DFMT_A8L8: return 2U;
	default: return 1U;
	}
}

bool Convert_Surface_Pixel_To_RGBA(D3DFORMAT format,
	const unsigned char *source, unsigned char *rgba)
{
	if (source == NULL || rgba == NULL) return false;
	switch (format) {
	case D3DFMT_A8R8G8B8:
		rgba[0] = source[2]; rgba[1] = source[1];
		rgba[2] = source[0]; rgba[3] = source[3]; return true;
	case D3DFMT_X8R8G8B8:
		rgba[0] = source[2]; rgba[1] = source[1];
		rgba[2] = source[0]; rgba[3] = 0xffU; return true;
	case D3DFMT_R8G8B8:
		rgba[0] = source[2]; rgba[1] = source[1];
		rgba[2] = source[0]; rgba[3] = 0xffU; return true;
	case D3DFMT_A4R4G4B4: {
		const uint16_t pixel = static_cast<uint16_t>(source[0]) |
			(static_cast<uint16_t>(source[1]) << 8U);
		rgba[0] = static_cast<unsigned char>(((pixel >> 8U) & 0x0fU) * 17U);
		rgba[1] = static_cast<unsigned char>(((pixel >> 4U) & 0x0fU) * 17U);
		rgba[2] = static_cast<unsigned char>((pixel & 0x0fU) * 17U);
		rgba[3] = static_cast<unsigned char>(((pixel >> 12U) & 0x0fU) * 17U);
		return true;
	}
	case D3DFMT_A1R5G5B5: {
		const uint16_t pixel = static_cast<uint16_t>(source[0]) |
			(static_cast<uint16_t>(source[1]) << 8U);
		rgba[0] = static_cast<unsigned char>(((pixel >> 10U) & 0x1fU) * 255U / 31U);
		rgba[1] = static_cast<unsigned char>(((pixel >> 5U) & 0x1fU) * 255U / 31U);
		rgba[2] = static_cast<unsigned char>((pixel & 0x1fU) * 255U / 31U);
		rgba[3] = (pixel & 0x8000U) != 0U ? 0xffU : 0U;
		return true;
	}
	case D3DFMT_R5G6B5: {
		const uint16_t pixel = static_cast<uint16_t>(source[0]) |
			(static_cast<uint16_t>(source[1]) << 8U);
		rgba[0] = static_cast<unsigned char>(((pixel >> 11U) & 0x1fU) * 255U / 31U);
		rgba[1] = static_cast<unsigned char>(((pixel >> 5U) & 0x3fU) * 255U / 63U);
		rgba[2] = static_cast<unsigned char>((pixel & 0x1fU) * 255U / 31U);
		rgba[3] = 0xffU;
		return true;
	}
	case D3DFMT_A8:
		rgba[0] = rgba[1] = rgba[2] = 0xffU; rgba[3] = source[0]; return true;
	case D3DFMT_L8:
		rgba[0] = rgba[1] = rgba[2] = source[0]; rgba[3] = 0xffU; return true;
	default:
		return false;
	}
}

IDirect3DTexture8 *Create_Texture_From_Surface(IDirect3DSurface8 *surface,
	TextureClass::MipCountType mip_level_count)
{
	if (surface == NULL) {
		RenegadeVitaRenderer::Record_Texture_Invalid_Data();
		return Create_Checkerboard_Fallback();
	}
	D3DSURFACE_DESC description = {};
	if (surface->GetDesc(&description) != D3D_OK || description.Width == 0U ||
		description.Height == 0U || surface->Get_Data() == NULL) {
		RenegadeVitaRenderer::Record_Texture_Invalid_Data();
		return Create_Checkerboard_Fallback();
	}
	const unsigned bytes_per_pixel = Surface_Bytes_Per_Pixel(description.Format);
	std::vector<unsigned char> rgba(static_cast<size_t>(description.Width) *
		description.Height * 4U);
	uint32_t checksum = 2166136261U;
	for (unsigned y = 0U; y < description.Height; ++y) {
		const unsigned char *source_row = surface->Get_Data() +
			static_cast<size_t>(y) * surface->Get_Pitch();
		for (unsigned x = 0U; x < description.Width; ++x) {
			unsigned char *destination = rgba.data() +
				(static_cast<size_t>(y) * description.Width + x) * 4U;
			if (!Convert_Surface_Pixel_To_RGBA(description.Format,
				source_row + static_cast<size_t>(x) * bytes_per_pixel, destination)) {
				RenegadeVitaRenderer::Record_Texture_Unsupported_Format();
				return Create_Checkerboard_Fallback();
			}
			checksum = Mix_Texture_Checksum(checksum,
				static_cast<uint32_t>(destination[0]) |
				(static_cast<uint32_t>(destination[1]) << 8U) |
				(static_cast<uint32_t>(destination[2]) << 16U) |
				(static_cast<uint32_t>(destination[3]) << 24U));
		}
	}
	IDirect3DTexture8 *texture = new (std::nothrow) IDirect3DTexture8;
	if (texture == NULL) {
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return Create_Checkerboard_Fallback();
	}
	memset(texture, 0, sizeof(*texture));
	texture->Width = description.Width;
	texture->Height = description.Height;
	texture->MipLevels = mip_level_count == TextureClass::MIP_LEVELS_ALL ? 1U :
		static_cast<uint32_t>(mip_level_count);
	if (texture->MipLevels == 0U) texture->MipLevels = 1U;
	texture->SourceFormat = description.Format;
	texture->PixelChecksum = checksum;
	texture->ResidentBytes = rgba.size();
	texture->ReferenceCount = 1U;
	texture->HasAlpha = description.Format == D3DFMT_A8R8G8B8 ||
		description.Format == D3DFMT_A4R4G4B4 ||
		description.Format == D3DFMT_A1R5G5B5 || description.Format == D3DFMT_A8;
#if defined(__vita__)
	(void)glGetError();
	GLuint native = 0U;
	glGenTextures(1, &native);
	if (native == 0U) {
		delete texture;
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return Create_Checkerboard_Fallback();
	}
	glBindTexture(GL_TEXTURE_2D, native);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, description.Width, description.Height,
		0, GL_RGBA, GL_UNSIGNED_BYTE, rgba.data());
	if (glGetError() != GL_NO_ERROR) {
		RenegadeVitaRenderer::Release_Texture(native);
		delete texture;
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return Create_Checkerboard_Fallback();
	}
	texture->NativeTexture = native;
#else
	texture->NativeTexture = 1U;
#endif
	texture->Uploaded = true;
	RenegadeVitaRenderer::Record_Texture_Decode();
	RenegadeVitaRenderer::Record_Texture_Upload(texture->ResidentBytes);
	return texture;
}

IDirect3DTexture8 *Create_Checkerboard_Fallback()
{
	if (g_checkerboard_fallback != NULL) {
		g_checkerboard_fallback->AddRef();
		RenegadeVitaRenderer::Record_Texture_Checkerboard_Fallback();
		return g_checkerboard_fallback;
	}
	// A deliberately conspicuous magenta/black diagnostic resource.  It is
	// created only after a real TextureClass request has failed, so it preserves
	// original asset ownership while making source/decode failures visible.
	unsigned char pixels[16] = {};
	RenegadeVitaTextureUpload::Build_Checkerboard_RGBA(pixels);
	IDirect3DTexture8 *texture = new (std::nothrow) IDirect3DTexture8;
	if (texture == NULL) return NULL;
	memset(texture, 0, sizeof(*texture));
	texture->Width = 2U;
	texture->Height = 2U;
	texture->MipLevels = 1U;
	texture->SourceFormat = D3DFMT_A8R8G8B8;
	texture->PixelChecksum = 0xA7B5A561U;
	texture->ResidentBytes = sizeof(pixels);
	texture->ReferenceCount = 1U;
	texture->HasAlpha = true;
	texture->DiagnosticFallback = true;
#if defined(__vita__)
	// Do not attribute a stale error from a prior engine operation to this
	// diagnostic upload.  The following query describes only this creation.
	(void)glGetError();
	GLuint native = 0U;
	glGenTextures(1, &native);
	if (native == 0U) { delete texture; return NULL; }
	glBindTexture(GL_TEXTURE_2D, native);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 2, 2, 0, GL_RGBA,
		GL_UNSIGNED_BYTE, pixels);
	if (glGetError() != GL_NO_ERROR) {
		RenegadeVitaRenderer::Release_Texture(native);
		delete texture;
		return NULL;
	}
	texture->NativeTexture = native;
#else
	texture->NativeTexture = 1U;
#endif
	texture->Uploaded = true;
	RenegadeVitaRenderer::Record_Texture_Upload(texture->ResidentBytes);
	RenegadeVitaRenderer::Record_Texture_Checkerboard_Fallback();
	g_checkerboard_fallback = texture;
	// Retain the cache's first reference and lend an independent one to the
	// TextureClass caller, matching normal DX8-shaped ownership semantics.
	texture->AddRef();
	return texture;
}

IDirect3DTexture8 *Load_DDS_Texture(const char *filename,
	TextureClass::MipCountType requested_mips, bool *dds_available)
{
	if (dds_available != NULL) *dds_available = false;
	if (filename == NULL || filename[0] == 0) return NULL;
	DDSFileClass dds(filename, 0U);
	if (!dds.Is_Available()) {
		return NULL;
	}
	if (dds_available != NULL) *dds_available = true;
	if (!dds.Load()) {
		Log_Texture_Fallback("dds-decode", filename);
		RenegadeVitaRenderer::Record_Texture_Decode_Failure();
		return Create_Checkerboard_Fallback();
	}
	if (!Texture_Format_Is_Supported(dds.Get_Format())) {
		Log_Texture_Fallback("dds-format", filename);
		RenegadeVitaRenderer::Record_Texture_Unsupported_Format();
		return Create_Checkerboard_Fallback();
	}
	const unsigned available_mips = dds.Get_Mip_Level_Count();
	const unsigned mip_count = requested_mips == TextureClass::MIP_LEVELS_ALL ?
		available_mips : (static_cast<unsigned>(requested_mips) < available_mips ?
			static_cast<unsigned>(requested_mips) : available_mips);
	if (mip_count == 0U) {
		Log_Texture_Fallback("dds-mips", filename);
		RenegadeVitaRenderer::Record_Texture_Invalid_Data();
		return Create_Checkerboard_Fallback();
	}
	IDirect3DTexture8 *texture = new (std::nothrow) IDirect3DTexture8;
	if (texture == NULL) {
		Log_Texture_Fallback("dds-alloc", filename);
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return Create_Checkerboard_Fallback();
	}
	memset(texture, 0, sizeof(*texture));
	texture->Width = dds.Get_Width(0U);
	texture->Height = dds.Get_Height(0U);
	texture->MipLevels = mip_count;
	texture->SourceFormat = WW3DFormat_To_D3DFormat(dds.Get_Format());
	texture->HasAlpha = Texture_Format_Has_Alpha(dds.Get_Format());
	texture->ReferenceCount = 1U;
	texture->DiagnosticFallback = false;
	uint32_t checksum = 2166136261U;
	uint64_t bytes = 0U;
#if defined(__vita__)
	(void)glGetError();
	GLuint native = 0U;
	glGenTextures(1, &native);
	if (native == 0U) {
		delete texture;
		Log_Texture_Fallback("dds-gl-gen", filename);
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return Create_Checkerboard_Fallback();
	}
	glBindTexture(GL_TEXTURE_2D, native);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
		mip_count > 1U ? GL_LINEAR_MIPMAP_LINEAR : GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
#endif
	for (unsigned level = 0U; level < mip_count; ++level) {
		const unsigned width = dds.Get_Width(level);
		const unsigned height = dds.Get_Height(level);
		std::vector<unsigned char> rgba(static_cast<size_t>(width) * height * 4U);
		for (unsigned y = 0U; y < height; ++y) {
			for (unsigned x = 0U; x < width; ++x) {
				const uint32_t argb = dds.Get_Pixel(level, x, y);
				RenegadeVitaTextureUpload::Store_RGBA_From_ARGB_Flipped(argb,
					x, y, width, height, rgba.data());
				checksum = Mix_Texture_Checksum(checksum, argb);
			}
		}
		bytes += rgba.size();
#if defined(__vita__)
		glTexImage2D(GL_TEXTURE_2D, level, GL_RGBA, width, height, 0,
			GL_RGBA, GL_UNSIGNED_BYTE, rgba.data());
#endif
	}
#if defined(__vita__)
	if (glGetError() != GL_NO_ERROR) {
		RenegadeVitaRenderer::Release_Texture(native);
		delete texture;
		Log_Texture_Fallback("dds-gl-upload", filename);
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return Create_Checkerboard_Fallback();
	}
	texture->NativeTexture = native;
	texture->Uploaded = true;
#else
	// Host validation proves archive lookup and the exact decoded upload
	// representation; target builds own the actual vitaGL object.
	texture->NativeTexture = 1U;
	texture->Uploaded = true;
#endif
	texture->PixelChecksum = checksum;
	texture->ResidentBytes = bytes;
	RenegadeVitaRenderer::Record_Texture_Decode();
	RenegadeVitaRenderer::Record_Texture_DDS_Load();
	RenegadeVitaRenderer::Record_Texture_Upload(bytes);
	Log_Texture_Load("dds", filename, texture);
	return texture;
}

IDirect3DTexture8 *Load_Targa_Texture(const char *filename,
	TextureClass::MipCountType mip_level_count)
{
	IDirect3DSurface8 *surface = DX8Wrapper::_Create_DX8_Surface(filename);
	if (surface == NULL) {
		Log_Texture_Fallback("tga-source-or-decode", filename);
		return Create_Checkerboard_Fallback();
	}
	IDirect3DTexture8 *texture = DX8Wrapper::_Create_DX8_Texture(surface,
		mip_level_count);
	surface->Release();
	if (texture != NULL && !texture->DiagnosticFallback) {
		RenegadeVitaRenderer::Record_Texture_Targa_Load();
		Log_Texture_Load("tga", filename, texture);
	}
	return texture;
}

void Submit_Bound_Triangles(const RenderStateStruct &state,
	unsigned short start_index, unsigned short polygon_count,
	unsigned short min_vertex_index, unsigned short vertex_count)
{
	if (polygon_count == 0U) {
		return;
	}
	if (state.vertex_buffer == NULL || state.index_buffer == NULL) {
		RenegadeVitaRenderer::Reject_Indexed_Submission(
			"vertex or index buffer is not bound", 0U);
		return;
	}
	if (!Is_DX8_Buffer_Type(state.vertex_buffer_type) ||
		!Is_DX8_Buffer_Type(state.index_buffer_type)) {
		RenegadeVitaRenderer::Reject_Indexed_Submission(
			"sorting buffer path is not implemented", state.vertex_buffer->FVF_Info().Get_FVF());
		return;
	}

	DX8VertexBufferClass *vertex_buffer =
		static_cast<DX8VertexBufferClass *>(state.vertex_buffer);
	DX8IndexBufferClass *index_buffer =
		static_cast<DX8IndexBufferClass *>(state.index_buffer);
	IDirect3DVertexBuffer8 *vertex_handle = vertex_buffer->Get_DX8_Vertex_Buffer();
	IDirect3DIndexBuffer8 *index_handle = index_buffer->Get_DX8_Index_Buffer();
	if (vertex_handle == NULL || index_handle == NULL) {
		RenegadeVitaRenderer::Reject_Indexed_Submission(
			"CPU buffer backing is unavailable", state.vertex_buffer->FVF_Info().Get_FVF());
		return;
	}

	uint32_t effective_vertex_count = vertex_count;
	uint32_t effective_min_vertex = min_vertex_index;
	if (effective_vertex_count < 3U) {
		effective_min_vertex = 0U;
		if (state.vertex_buffer_type == BUFFER_TYPE_DYNAMIC_DX8) {
			effective_vertex_count = state.vba_count;
		} else {
			const uint32_t consumed = static_cast<uint32_t>(state.index_base_offset) +
				static_cast<uint32_t>(state.vba_offset);
			effective_vertex_count = consumed <= state.vertex_buffer->Get_Vertex_Count() ?
				state.vertex_buffer->Get_Vertex_Count() - consumed : 0U;
		}
	}

	const uint32_t stride = state.vertex_buffer->FVF_Info().Get_FVF_Size();
	RenegadeVitaRenderer::IndexedTriangleSubmission submission = {};
	submission.vertex_data = vertex_handle->Get_Data();
	submission.vertex_data_size = vertex_handle->Get_Size();
	submission.vertex_format = state.vertex_buffer->FVF_Info().Get_FVF();
	submission.vertex_stride = stride;
	submission.vertex_capacity = stride != 0U ? vertex_handle->Get_Size() / stride : 0U;
	submission.index_data = reinterpret_cast<const uint16_t *>(index_handle->Get_Data());
	submission.index_capacity = index_handle->Get_Size() / sizeof(uint16_t);
	submission.first_index = static_cast<uint32_t>(start_index) + state.iba_offset;
	submission.triangle_count = polygon_count;
	submission.base_vertex_index = static_cast<uint32_t>(state.index_base_offset) +
		state.vba_offset;
	submission.min_vertex_index = effective_min_vertex;
	submission.vertex_count = effective_vertex_count;
	submission.world_transform = &state.world[0].X;
	submission.view_transform = &state.view[0].X;
	submission.projection_transform = &g_boundary_transforms[D3DTS_PROJECTION].m[0][0];
	/* DynamicVB users such as the original Haze/Starfield/CloudLayer/SkyObject
	** paths retain shader and texture changes in DX8Wrapper::render_state until
	** Draw_Triangles.  The native boundary must consume those same owners before
	** emitting their indexed geometry; otherwise a valid sky draw inherits stale
	** mesh state and commonly renders black. */
	RenegadeVitaRenderer::Apply_Indexed_Shader_State(state.shader);
	if (state.shader.Get_Texturing() != ShaderClass::TEXTURING_DISABLE &&
		state.Textures[0] != NULL) {
		state.Textures[0]->Apply_For_Platform_Boundary(0U);
	} else {
		RenegadeVitaRenderer::Bind_Texture(0U, false);
	}
	RenegadeVitaRenderer::Submit_Indexed_Triangles(submission);
}

} // namespace

// The original DX8Caps hardware-probing translation unit is a Direct3D
// enumeration boundary and is intentionally not part of the native Vita
// target. This constructor supplies the original capability abstraction with
// a conservative description of only the platform behavior currently mapped.
DX8Caps::DX8Caps(IDirect3D8 *direct3d, const D3DCAPS8 &caps,
	WW3DFormat display_format, const D3DADAPTER_IDENTIFIER8 &adapter_id)
	: MaxDisplayWidth(RenegadeVitaRenderer::DISPLAY_WIDTH),
	  MaxDisplayHeight(RenegadeVitaRenderer::DISPLAY_HEIGHT), Caps(caps),
	  SupportTnL(true), SupportDXTC(false), supportGamma(false),
	  SupportNPatches(false), SupportBumpEnvmap(false),
	  SupportBumpEnvmapLuminance(false), SupportZBias(false),
	  SupportAnisotropicFiltering(false), CanDoMultiPass(false),
	  IsFogAllowed(false), MaxTexturesPerPass(0), VertexShaderVersion(0),
	  PixelShaderVersion(0), DeviceId(0), DriverBuildVersion(0),
	  DriverVersionStatus(DRIVER_STATUS_UNKNOWN), VendorId(VENDOR_UNKNOWN),
	  DriverDLL("Vita native renderer boundary"), Direct3D(direct3d),
	  CapsLog("Conservative native Vita capabilities"),
	  CompactLog("VITA_NATIVE_CONSERVATIVE")
{
	(void)display_format;
	(void)adapter_id;
	memset(SupportTextureFormat, 0, sizeof(SupportTextureFormat));
	memset(SupportRenderToTextureFormat, 0,
		sizeof(SupportRenderToTextureFormat));
}

namespace {

DX8Caps g_vita_caps(NULL, g_vita_caps_description, WW3D_FORMAT_UNKNOWN,
	g_vita_adapter_description);

} // namespace

#if defined(RENEGADE_VITA_PORT)

IDirect3DVertexBuffer8::IDirect3DVertexBuffer8(UINT size)
	: Storage(new (std::nothrow) unsigned char[size]), StorageSize(size),
	  ReferenceCount(1)
{
}

IDirect3DVertexBuffer8::~IDirect3DVertexBuffer8()
{
	delete [] Storage;
}

ULONG IDirect3DVertexBuffer8::AddRef()
{
	return ++ReferenceCount;
}

ULONG IDirect3DVertexBuffer8::Release()
{
	if (ReferenceCount == 0) {
		return 0;
	}
	const ULONG remaining = --ReferenceCount;
	if (remaining == 0) {
		delete this;
	}
	return remaining;
}

HRESULT IDirect3DVertexBuffer8::Lock(UINT offset, UINT size,
	unsigned char **data, DWORD flags)
{
	(void)flags;
	if (data == NULL || Storage == NULL || offset > StorageSize) {
		return static_cast<HRESULT>(-1);
	}
	const UINT lock_size = size == 0 ? StorageSize - offset : size;
	if (lock_size > StorageSize - offset) {
		return static_cast<HRESULT>(-1);
	}
	*data = Storage + offset;
	return D3D_OK;
}

HRESULT IDirect3DVertexBuffer8::Unlock()
{
	return D3D_OK;
}

IDirect3DIndexBuffer8::IDirect3DIndexBuffer8(UINT size)
	: Storage(new (std::nothrow) unsigned char[size]), StorageSize(size),
	  ReferenceCount(1)
{
}

IDirect3DIndexBuffer8::~IDirect3DIndexBuffer8()
{
	delete [] Storage;
}

ULONG IDirect3DIndexBuffer8::AddRef()
{
	return ++ReferenceCount;
}

ULONG IDirect3DIndexBuffer8::Release()
{
	if (ReferenceCount == 0) {
		return 0;
	}
	const ULONG remaining = --ReferenceCount;
	if (remaining == 0) {
		delete this;
	}
	return remaining;
}

HRESULT IDirect3DIndexBuffer8::Lock(UINT offset, UINT size,
	unsigned char **data, DWORD flags)
{
	(void)flags;
	if (data == NULL || Storage == NULL || offset > StorageSize) {
		return static_cast<HRESULT>(-1);
	}
	const UINT lock_size = size == 0 ? StorageSize - offset : size;
	if (lock_size > StorageSize - offset) {
		return static_cast<HRESULT>(-1);
	}
	*data = Storage + offset;
	return D3D_OK;
}

HRESULT IDirect3DIndexBuffer8::Unlock()
{
	return D3D_OK;
}

#endif

unsigned number_of_DX8_calls = 0;
bool _DX8SingleThreaded = false;

void DX8_Assert()
{
	// Original buffer lock sites use this as a Direct3D-device/thread guard.
	// The Vita handles validate every lock range themselves and are not tied to
	// a Direct3D interface, so there is no additional device object to assert.
}

void Log_DX8_ErrorCode(unsigned result)
{
	char reason[80];
	snprintf(reason, sizeof(reason), "CPU-backed DX8 handle error=%08X", result);
	RenegadeVitaRenderer::Reject_Indexed_Submission(reason, 0U);
}

bool DX8Wrapper::IsInitted = false;
bool DX8Wrapper::IsDeviceLost = false;
unsigned DX8Wrapper::TextureStageStates[MAX_TEXTURE_STAGES][32] = {};
IDirect3DBaseTexture8 *DX8Wrapper::Textures[MAX_TEXTURE_STAGES] = {};
RenderStateStruct DX8Wrapper::render_state;
unsigned DX8Wrapper::render_state_changed = 0;
IDirect3DDevice8 *DX8Wrapper::D3DDevice = &g_boundary_device;
int DX8Wrapper::ResolutionWidth = RenegadeVitaRenderer::DISPLAY_WIDTH;
int DX8Wrapper::ResolutionHeight = RenegadeVitaRenderer::DISPLAY_HEIGHT;
int DX8Wrapper::BitDepth = RenegadeVitaRenderer::DISPLAY_BITS;
int DX8Wrapper::TextureBitDepth = RenegadeVitaRenderer::DISPLAY_BITS;
bool DX8Wrapper::IsWindowed = false;
unsigned DX8Wrapper::matrix_changes = 0;
unsigned DX8Wrapper::texture_stage_state_changes = 0;
unsigned DX8Wrapper::texture_changes = 0;
int DX8Wrapper::ZBias = 0;
float DX8Wrapper::ZNear = 0.1f;
float DX8Wrapper::ZFar = 1000.0f;
Matrix4 DX8Wrapper::ProjectionMatrix(true);
DX8Caps *DX8Wrapper::CurrentCaps = &g_vita_caps;

namespace Debug_Statistics {
// The original texture application records this optional desktop diagnostic.
// Vita keeps the authoritative resource counters in RenegadeVitaRenderer;
// this deliberately narrow compatibility sink preserves Apply's call path.
void Record_Texture(TextureClass *) {}
}

IDirect3DSurface8 *DX8Wrapper::_Create_DX8_Surface(unsigned int width,
	unsigned int height, WW3DFormat format)
{
	const D3DFORMAT d3d_format = WW3DFormat_To_D3DFormat(format);
	const unsigned bytes_per_pixel = Surface_Bytes_Per_Pixel(d3d_format);
	IDirect3DSurface8 *surface = new (std::nothrow) IDirect3DSurface8(
		width, height, d3d_format, bytes_per_pixel);
	if (surface == NULL || surface->Get_Data() == NULL) {
		if (surface != NULL) surface->Release();
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return NULL;
	}
	return surface;
}

IDirect3DSurface8 *DX8Wrapper::_Create_DX8_Surface(const char *filename)
{
	if (filename == NULL || filename[0] == '\0') {
		RenegadeVitaRenderer::Record_Texture_Source_Missing();
		return NULL;
	}
	Targa targa;
	if (targa.Open(filename, TGA_READMODE) != 0) {
		RenegadeVitaRenderer::Record_Texture_Source_Missing();
		return NULL;
	}
	/* Match original WW3D TextureLoader semantics exactly: after opening the
	** TGA and reading its header, DX8 toggles the Y-origin bit before calling
	** Targa::Load().  The same Targa object must remain open so Load consumes
	** that adjusted descriptor instead of re-reading the file header. */
	targa.Header.ImageDescriptor ^= TGAIDF_YORIGIN;
	if (targa.Load(filename, TGAF_IMAGE, false) != 0) {
		RenegadeVitaRenderer::Record_Texture_Decode_Failure();
		return NULL;
	}
	WW3DFormat source_format = WW3D_FORMAT_UNKNOWN;
	unsigned source_bpp = 0U;
	Get_WW3D_Format(source_format, source_bpp, targa);
	if (source_format == WW3D_FORMAT_UNKNOWN || source_bpp == 0U ||
		targa.Header.Width == 0U || targa.Header.Height == 0U ||
		targa.GetImage() == NULL) {
		RenegadeVitaRenderer::Record_Texture_Invalid_Data();
		return NULL;
	}
	IDirect3DSurface8 *surface = _Create_DX8_Surface(targa.Header.Width,
		targa.Header.Height, source_format);
	if (surface == NULL) return NULL;
	D3DLOCKED_RECT locked = {};
	if (surface->LockRect(&locked, NULL, 0U) != D3D_OK || locked.pBits == NULL ||
		locked.Pitch < static_cast<int>(targa.Header.Width * source_bpp)) {
		surface->Release();
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return NULL;
	}
	const size_t row_bytes = static_cast<size_t>(targa.Header.Width) * source_bpp;
	for (unsigned y = 0U; y < targa.Header.Height; ++y) {
		memcpy(static_cast<unsigned char *>(locked.pBits) +
			static_cast<size_t>(y) * locked.Pitch,
			reinterpret_cast<const unsigned char *>(targa.GetImage()) + y * row_bytes,
			row_bytes);
	}
	surface->UnlockRect();
	return surface;
}

IDirect3DTexture8 *DX8Wrapper::_Create_DX8_Texture(IDirect3DSurface8 *surface,
	TextureClass::MipCountType mip_level_count)
{
	return Create_Texture_From_Surface(surface, mip_level_count);
}

IDirect3DTexture8 *DX8Wrapper::_Create_DX8_Texture(const char *filename,
	TextureClass::MipCountType mip_level_count)
{
	RenegadeVitaRenderer::Record_Texture_Request();
	if (filename == NULL || filename[0] == 0) {
		Log_Texture_Fallback("empty-name", filename);
		RenegadeVitaRenderer::Record_Texture_Source_Missing();
		return Create_Checkerboard_Fallback();
	}
	bool dds_available = false;
	IDirect3DTexture8 *texture = Load_DDS_Texture(filename, mip_level_count,
		&dds_available);
	if (texture != NULL || dds_available) return texture;
	if (Filename_Has_Extension(filename, ".tga")) {
		return Load_Targa_Texture(filename, mip_level_count);
	}
	Log_Texture_Fallback("dds-missing", filename);
	RenegadeVitaRenderer::Record_Texture_Source_Missing();
	return Create_Checkerboard_Fallback();
}

ULONG IDirect3DBaseTexture8::AddRef()
{
	return ++ReferenceCount;
}

ULONG IDirect3DBaseTexture8::Release()
{
	if (ReferenceCount == 0U) return 0U;
	const ULONG remaining = --ReferenceCount;
	if (remaining == 0U) {
		RenegadeVitaRenderer::Release_Texture(NativeTexture);
		RenegadeVitaRenderer::Record_Texture_Release(ResidentBytes);
		delete static_cast<IDirect3DTexture8 *>(this);
	}
	return remaining;
}

UINT IDirect3DTexture8::GetLevelCount()
{
	/* The current Vita texture boundary never manufactures a DX8 texture. If a
	** retained original caller holds a non-null platform handle, expose the
	** conservative base-level-only contract instead of inventing mip storage. */
	return MipLevels == 0U ? 1U : MipLevels;
}

HRESULT IDirect3DTexture8::GetLevelDesc(UINT level, D3DSURFACE_DESC *description)
{
	if (description == NULL || level >= GetLevelCount()) return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	memset(description, 0, sizeof(*description));
	description->Width = Width >> level;
	description->Height = Height >> level;
	if (description->Width == 0U) description->Width = 1U;
	if (description->Height == 0U) description->Height = 1U;
	description->Format = SourceFormat;
	description->Size = static_cast<UINT>(description->Width * description->Height * 4U);
	return D3D_OK;
}

HRESULT IDirect3DTexture8::GetSurfaceLevel(UINT, IDirect3DSurface8 **surface)
{
	if (surface != NULL) *surface = NULL;
	return static_cast<HRESULT>(D3DERR_INVALIDCALL);
}

IDirect3DSurface8::IDirect3DSurface8(UINT width, UINT height,
	D3DFORMAT format, UINT bytes_per_pixel)
	: Storage(NULL), StorageSize(0U), Width(width), Height(height), Pitch(0U),
	  Format(format), ReferenceCount(1U)
{
	if (width == 0U || height == 0U || bytes_per_pixel == 0U ||
		width > UINT32_MAX / bytes_per_pixel) return;
	Pitch = width * bytes_per_pixel;
	if (height > UINT32_MAX / Pitch) {
		Pitch = 0U;
		return;
	}
	StorageSize = Pitch * height;
	Storage = new (std::nothrow) unsigned char[StorageSize];
	if (Storage == NULL) {
		StorageSize = 0U;
		Pitch = 0U;
	}
}

IDirect3DSurface8::~IDirect3DSurface8()
{
	delete [] Storage;
}

ULONG IDirect3DSurface8::AddRef()
{
	return ++ReferenceCount;
}

ULONG IDirect3DSurface8::Release()
{
	if (ReferenceCount == 0U) return 0U;
	const ULONG remaining = --ReferenceCount;
	if (remaining == 0U) delete this;
	return remaining;
}

HRESULT IDirect3DSurface8::GetDesc(D3DSURFACE_DESC *description)
{
	if (description == NULL || Storage == NULL) return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	memset(description, 0, sizeof(*description));
	description->Format = Format;
	description->Width = Width;
	description->Height = Height;
	description->Size = StorageSize;
	return D3D_OK;
}

HRESULT IDirect3DSurface8::LockRect(D3DLOCKED_RECT *locked,
	const RECT *rectangle, DWORD)
{
	if (locked == NULL || Storage == NULL) return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	UINT left = 0U;
	UINT top = 0U;
	if (rectangle != NULL) {
		if (rectangle->left < 0 || rectangle->top < 0 || rectangle->right < rectangle->left ||
			rectangle->bottom < rectangle->top || static_cast<UINT>(rectangle->right) > Width ||
			static_cast<UINT>(rectangle->bottom) > Height) return static_cast<HRESULT>(D3DERR_INVALIDCALL);
		left = static_cast<UINT>(rectangle->left);
		top = static_cast<UINT>(rectangle->top);
	}
	locked->Pitch = static_cast<int>(Pitch);
	locked->pBits = Storage + static_cast<size_t>(top) * Pitch +
		static_cast<size_t>(left) * Surface_Bytes_Per_Pixel(Format);
	return D3D_OK;
}

HRESULT IDirect3DSurface8::UnlockRect()
{
	return D3D_OK;
}

HRESULT IDirect3DDevice8::CopyRects(IDirect3DSurface8 *, const RECT *, UINT,
	IDirect3DSurface8 *, const POINT *)
{
	return static_cast<HRESULT>(D3DERR_INVALIDCALL);
}

HRESULT IDirect3DDevice8::SetTransform(D3DTRANSFORMSTATETYPE state,
	const D3DMATRIX *matrix)
{
	if (matrix != NULL && state < 257U) {
		g_boundary_transforms[state] = *matrix;
	}
	return D3D_OK;
}

HRESULT IDirect3DDevice8::GetTransform(D3DTRANSFORMSTATETYPE state,
	D3DMATRIX *matrix)
{
	if (matrix == NULL) {
		return D3D_OK;
	}
	if (state < 257U) {
		*matrix = g_boundary_transforms[state];
	} else {
		memset(matrix, 0, sizeof(*matrix));
	}
	return D3D_OK;
}

HRESULT IDirect3DDevice8::SetViewport(const D3DVIEWPORT8 *viewport)
{
	if (viewport == NULL || !RenegadeVitaRenderer::Apply_Viewport(viewport->X,
		viewport->Y, viewport->Width, viewport->Height, viewport->MinZ,
		viewport->MaxZ, g_logical_viewport_width,
		g_logical_viewport_height)) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	g_boundary_viewport = *viewport;
	return D3D_OK;
}

HRESULT IDirect3DDevice8::GetViewport(D3DVIEWPORT8 *viewport)
{
	if (viewport == NULL) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	*viewport = g_boundary_viewport;
	return D3D_OK;
}

HRESULT IDirect3DDevice8::SetTextureStageState(DWORD stage,
	D3DTEXTURESTAGESTATETYPE state, DWORD value)
{
	if (stage >= MAX_TEXTURE_STAGES) return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	TextureStageSamplerState &sampler = g_texture_sampler_states[stage];
	switch (state) {
	case D3DTSS_ADDRESSU: sampler.address_u = value; break;
	case D3DTSS_ADDRESSV: sampler.address_v = value; break;
	case D3DTSS_MINFILTER: sampler.min_filter = value; break;
	case D3DTSS_MAGFILTER: sampler.mag_filter = value; break;
	case D3DTSS_MIPFILTER: sampler.mip_filter = value; break;
	default:
		// TextureClass owns sampler state above this boundary.  Other original
		// stage semantics remain deliberately counted rather than discarded.
		if (stage != 0U) RenegadeVitaRenderer::Record_Texture_Unsupported_Stage(stage);
		return D3D_OK;
	}
	if (stage != 0U) {
		RenegadeVitaRenderer::Record_Texture_Unsupported_Stage(stage);
		return D3D_OK;
	}
	return Apply_Texture_Stage_Sampler(stage) ? D3D_OK :
		static_cast<HRESULT>(D3DERR_INVALIDCALL);
}

HRESULT IDirect3DDevice8::SetTexture(DWORD stage, IDirect3DBaseTexture8 *texture)
{
	if (stage >= MAX_TEXTURE_STAGES) return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	g_texture_stage_textures[stage] = texture;
	if (stage != 0U) {
		RenegadeVitaRenderer::Record_Texture_Unsupported_Stage(stage);
		return D3D_OK;
	}
	if (texture == NULL) {
		RenegadeVitaRenderer::Bind_Texture(0U, false);
		return D3D_OK;
	}
	if (texture->DiagnosticFallback) {
		RenegadeVitaRenderer::Record_Texture_Checkerboard_Bind();
	}
	RenegadeVitaRenderer::Bind_Texture(texture->NativeTexture,
		texture->Uploaded && texture->NativeTexture != 0U);
	return Apply_Texture_Stage_Sampler(stage) ? D3D_OK :
		static_cast<HRESULT>(D3DERR_INVALIDCALL);
}

void DX8Wrapper::Get_DX8_Texture_Stage_State_Value_Name(StringClass &name,
	D3DTEXTURESTAGESTATETYPE state, unsigned value)
{
	(void)state;
	(void)value;
	name = "VITA_BACKEND";
}

void DX8Wrapper::Get_Device_Resolution(int &width, int &height, int &bits,
	bool &windowed)
{
	width = ResolutionWidth;
	height = ResolutionHeight;
	bits = BitDepth;
	windowed = IsWindowed;
}

void DX8Wrapper::Get_Render_Target_Resolution(int &width, int &height,
	int &bits, bool &windowed)
{
	// Non-default render targets are not mapped yet. The active A3 world path
	// renders to the immutable native display target, so retain its exact
	// dimensions under the original query.
	Get_Device_Resolution(width, height, bits, windowed);
}

bool DX8Wrapper::Set_Device_Resolution(int width, int height, int bits,
	int windowed, bool resize_window)
{
	(void)resize_window;
	if (width != -1) {
		if (width <= 0) return false;
		ResolutionWidth = width;
	}
	if (height != -1) {
		if (height <= 0) return false;
		ResolutionHeight = height;
	}
	if (bits != -1) {
		if (bits != 16 && bits != 32) return false;
		BitDepth = bits;
	}
	if (windowed != -1) {
		IsWindowed = windowed != 0;
	}
	Render2DClass::Set_Screen_Resolution(RectClass(0, 0,
		static_cast<float>(ResolutionWidth),
		static_cast<float>(ResolutionHeight)));
	g_logical_viewport_width = static_cast<uint32_t>(ResolutionWidth);
	g_logical_viewport_height = static_cast<uint32_t>(ResolutionHeight);
	return true;
}

TextureClass *DX8Wrapper::Create_Render_Target(int width, int height,
	WW3DFormat format)
{
	// Original projector setup first asks DX8Caps whether a render-to-texture
	// format is supported. The native capability contract truthfully advertises
	// none, so an unexpected creation attempt must remain a failed allocation,
	// not a fabricated offscreen texture. Record the unsupported platform edge
	// for the A3 runtime diagnostics and preserve the caller's NULL fallback.
	(void)width;
	(void)height;
	(void)format;
	RenegadeVitaRenderer::Reject_Indexed_Submission(
		"render-to-texture creation is unsupported", 0U);
	return NULL;
}

void DX8Wrapper::Set_Viewport(const D3DVIEWPORT8 *viewport)
{
	DX8_THREAD_ASSERT();
	DX8CALL(SetViewport(viewport));
}

void DX8Wrapper::Set_Vertex_Buffer(const VertexBufferClass *vertex_buffer)
{
	render_state.vba_offset = 0;
	render_state.vba_count = 0;
	if (render_state.vertex_buffer != NULL) {
		render_state.vertex_buffer->Release_Engine_Ref();
	}
	REF_PTR_SET(render_state.vertex_buffer,
		const_cast<VertexBufferClass *>(vertex_buffer));
	if (vertex_buffer != NULL) {
		vertex_buffer->Add_Engine_Ref();
		render_state.vertex_buffer_type = vertex_buffer->Type();
	} else {
		// Preserve the original implementation's invalidation behavior.
		render_state.index_buffer_type = BUFFER_TYPE_INVALID;
	}
	render_state_changed |= VERTEX_BUFFER_CHANGED;
}

void DX8Wrapper::Set_Index_Buffer(const IndexBufferClass *index_buffer,
	unsigned short index_base_offset)
{
	render_state.iba_offset = 0;
	if (render_state.index_buffer != NULL) {
		render_state.index_buffer->Release_Engine_Ref();
	}
	REF_PTR_SET(render_state.index_buffer,
		const_cast<IndexBufferClass *>(index_buffer));
	render_state.index_base_offset = index_base_offset;
	if (index_buffer != NULL) {
		index_buffer->Add_Engine_Ref();
		render_state.index_buffer_type = index_buffer->Type();
	} else {
		render_state.index_buffer_type = BUFFER_TYPE_INVALID;
	}
	render_state_changed |= INDEX_BUFFER_CHANGED;
}

void DX8Wrapper::Set_Vertex_Buffer(const DynamicVBAccessClass &access_const)
{
	if (render_state.vertex_buffer != NULL) {
		render_state.vertex_buffer->Release_Engine_Ref();
	}
	DynamicVBAccessClass &access =
		const_cast<DynamicVBAccessClass &>(access_const);
	render_state.vertex_buffer_type = access.Get_Type();
	render_state.vba_offset = access.VertexBufferOffset;
	render_state.vba_count = access.Get_Vertex_Count();
	REF_PTR_SET(render_state.vertex_buffer, access.VertexBuffer);
	render_state.vertex_buffer->Add_Engine_Ref();
	render_state_changed |= VERTEX_BUFFER_CHANGED;
	render_state_changed |= INDEX_BUFFER_CHANGED;
}

void DX8Wrapper::Set_Index_Buffer(const DynamicIBAccessClass &access_const,
	unsigned short index_base_offset)
{
	if (render_state.index_buffer != NULL) {
		render_state.index_buffer->Release_Engine_Ref();
	}
	DynamicIBAccessClass &access =
		const_cast<DynamicIBAccessClass &>(access_const);
	render_state.index_base_offset = index_base_offset;
	render_state.index_buffer_type = access.Get_Type();
	render_state.iba_offset = access.IndexBufferOffset;
	REF_PTR_SET(render_state.index_buffer, access.IndexBuffer);
	render_state.index_buffer->Add_Engine_Ref();
	render_state_changed |= INDEX_BUFFER_CHANGED;
}

void DX8Wrapper::Draw_Triangles(unsigned buffer_type,
	unsigned short start_index, unsigned short polygon_count,
	unsigned short min_vertex_index, unsigned short vertex_count)
{
	if (buffer_type == BUFFER_TYPE_SORTING ||
		buffer_type == BUFFER_TYPE_DYNAMIC_SORTING) {
		RenegadeVitaRenderer::Reject_Indexed_Submission(
			"sorting renderer submission is deferred", 0U);
		return;
	}
	if (buffer_type != BUFFER_TYPE_DX8 &&
		buffer_type != BUFFER_TYPE_DYNAMIC_DX8) {
		RenegadeVitaRenderer::Reject_Indexed_Submission(
			"invalid requested buffer type", 0U);
		return;
	}
	Submit_Bound_Triangles(render_state, start_index, polygon_count,
		min_vertex_index, vertex_count);
}

void DX8Wrapper::Draw_Triangles(unsigned short start_index,
	unsigned short polygon_count, unsigned short min_vertex_index,
	unsigned short vertex_count)
{
	Submit_Bound_Triangles(render_state, start_index, polygon_count,
		min_vertex_index, vertex_count);
}
