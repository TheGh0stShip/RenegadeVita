// Vita implementation of the legacy DX8 platform edge retained by original
// WW3D. Engine-owned buffers and draw calls remain unchanged above this file;
// this boundary translates their CPU-backed DX8-shaped handles for the native
// renderer without implementing or emulating Direct3D itself.

#include "dx8wrapper.h"
#include "ww3d_vita_renderer.h"
#include "ddsfile.h"
#include "dx8rendererdebugger.h"
#include "D3dx8core.h"
#include "formconv.h"
#include "mapper.h"
#include "render2d.h"
#include "sortingrenderer.h"
#include "texture.h"
#include "texture_upload_contract.h"
#include "targa.h"
#include "vertmaterial.h"
#include "ww3dformat.h"

#include <new>
#include <stdio.h>
#include <string.h>
#include <vector>

#if defined(__vita__)
#include "vita_runtime_log.h"
#include <vitaGL.h>
extern "C" GLboolean vglRenegadeUploadDXTChain(GLuint id, GLenum format,
	GLsizei width, GLsizei height, GLsizei levels,
	const void *const *pixels, const GLsizei *sizes);
#endif

bool DX8Wrapper::_EnableTriangleDraw = true;
#if defined(__vita__) && defined(RENEGADE_VITA_PORT)
bool DX8Wrapper::Is_Native_Device_Ready()
{
	// Original lite initialization intentionally never creates a desktop D3D
	// device. Sentence rendering must follow the native backend's lifecycle,
	// not the desktop-only IsInitted flag that remains false in that mode.
	const bool ready = RenegadeVitaRenderer::Get_Statistics().initialized;
	static bool logged_ready = false;
	if (ready && !logged_ready) {
		Vita_Append_A22_Runtime_Breadcrumb("text-lifecycle",
			"native DX8 readiness: ready=1 desktop_initialized=%d device_lost=%d original_sentence_owner=1",
			IsInitted ? 1 : 0, IsDeviceLost ? 1 : 0);
		logged_ready = true;
	}
	return ready;
}
#endif
unsigned DX8Wrapper::RenderStates[256] = {};
unsigned DX8Wrapper::render_state_changes = 0;
bool SortingRendererClass::_EnableTriangleDraw = true;
bool DX8RendererDebugger::Enabled = false;

void DX8RendererDebugger::Enable(bool enable) { Enabled = enable; }
void DX8RendererDebugger::Get_String(StringClass &) {}
void DX8RendererDebugger::Update() {}
void DX8RendererDebugger::Disable_Mesh(unsigned) {}
void DX8RendererDebugger::Enable_Mesh(unsigned) {}
void DX8RendererDebugger::Disable_All() {}
void DX8RendererDebugger::Enable_All() {}

void DX8Wrapper::Get_DX8_Render_State_Value_Name(StringClass &name,
	D3DRENDERSTATETYPE state, unsigned value)
{
	(void)state;
	name.Format("%u", value);
}

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
	DWORD texcoord_index;
	DWORD texture_transform_flags;
};

struct TextureStageCombinerState {
	DWORD color_op;
	DWORD color_arg1;
	DWORD color_arg2;
	DWORD alpha_op;
	DWORD alpha_arg1;
	DWORD alpha_arg2;
};

TextureStageSamplerState g_texture_sampler_states[MAX_TEXTURE_STAGES] = {
	{
		D3DTADDRESS_WRAP, D3DTADDRESS_WRAP,
		D3DTEXF_LINEAR, D3DTEXF_LINEAR, D3DTEXF_NONE,
		D3DTSS_TCI_PASSTHRU | 0U, D3DTTFF_DISABLE
	},
	{
		D3DTADDRESS_WRAP, D3DTADDRESS_WRAP,
		D3DTEXF_LINEAR, D3DTEXF_LINEAR, D3DTEXF_NONE,
		D3DTSS_TCI_PASSTHRU | 1U, D3DTTFF_DISABLE
	}
};
TextureStageCombinerState g_texture_combiner_states[MAX_TEXTURE_STAGES] = {
	{
		D3DTOP_MODULATE, D3DTA_TEXTURE, D3DTA_DIFFUSE,
		D3DTOP_MODULATE, D3DTA_TEXTURE, D3DTA_DIFFUSE
	},
	{
		D3DTOP_DISABLE, D3DTA_TEXTURE, D3DTA_CURRENT,
		D3DTOP_DISABLE, D3DTA_TEXTURE, D3DTA_CURRENT
	}
};
IDirect3DBaseTexture8 *g_texture_stage_textures[MAX_TEXTURE_STAGES] = {};

/*
** Texture mappers are applied once per material submission.  The original
** DX8 device accepted these redundant writes cheaply; on Vita each write
** crosses into vitaGL and changes the active texture matrix.  Keep the
** boundary state exact while avoiding identical GL work for adjacent meshes.
*/
D3DMATRIX g_applied_texture_transforms[MAX_TEXTURE_STAGES] = {};
DWORD g_applied_texture_transform_flags[MAX_TEXTURE_STAGES] = {};
bool g_applied_texture_transform_valid[MAX_TEXTURE_STAGES] = {};
// This cache owns one permanent reference for the native renderer's process
// lifetime.  Failed TextureClass requests receive a separate AddRef(), so an
// ordinary caller release cannot leave the cache dangling or delete a texture
// still bound by another failed material.
IDirect3DTexture8 *g_checkerboard_fallback = NULL;

bool Retain_Bound_Texture_Stage(DWORD stage, IDirect3DBaseTexture8 *texture)
{
	if (stage >= MAX_TEXTURE_STAGES) return false;
	IDirect3DBaseTexture8 *previous = g_texture_stage_textures[stage];
	if (previous == texture) return true;
	if (texture != NULL) texture->AddRef();
	g_texture_stage_textures[stage] = texture;
	if (previous != NULL) previous->Release();
	return true;
}

void Release_Bound_Texture_Stages()
{
	for (DWORD stage = 0; stage < MAX_TEXTURE_STAGES; ++stage) {
		Retain_Bound_Texture_Stage(stage, NULL);
	}
}

bool Apply_Texture_Stage_Sampler(DWORD stage)
{
	if (stage >= MAX_TEXTURE_STAGES) return false;
	IDirect3DBaseTexture8 *texture = g_texture_stage_textures[stage];
	if (texture == NULL) return true;
	const TextureStageSamplerState &sampler = g_texture_sampler_states[stage];
	return RenegadeVitaRenderer::Configure_Texture_Sampler_Stage(stage,
		texture->NativeTexture, texture->Uploaded && texture->NativeTexture != 0U,
		sampler.address_u, sampler.address_v, sampler.min_filter,
		sampler.mag_filter, sampler.mip_filter);
}

bool Apply_Texture_Stage_Combiner(DWORD stage)
{
	if (stage >= MAX_TEXTURE_STAGES) return false;
	const TextureStageCombinerState &combiner = g_texture_combiner_states[stage];
	IDirect3DBaseTexture8 *texture = g_texture_stage_textures[stage];
	return RenegadeVitaRenderer::Apply_DX8_Texture_Stage_State(stage,
		combiner.color_op, combiner.color_arg1, combiner.color_arg2,
		combiner.alpha_op, combiner.alpha_arg1, combiner.alpha_arg2,
		texture != NULL && texture->Uploaded && texture->NativeTexture != 0U);
}

bool Apply_Texture_Stage_Transform(DWORD stage)
{
	if (stage >= MAX_TEXTURE_STAGES) return false;
#if defined(__vita__)
	const TextureStageSamplerState &sampler = g_texture_sampler_states[stage];
	const D3DMATRIX &transform = g_boundary_transforms[D3DTS_TEXTURE0 + stage];
	if (g_applied_texture_transform_valid[stage] &&
		g_applied_texture_transform_flags[stage] == sampler.texture_transform_flags &&
		memcmp(&g_applied_texture_transforms[stage], &transform, sizeof(D3DMATRIX)) == 0) {
		return true;
	}
	glActiveTexture(GL_TEXTURE0 + static_cast<GLenum>(stage));
	glMatrixMode(GL_TEXTURE);
	if ((sampler.texture_transform_flags & 0xffU) == D3DTTFF_DISABLE) {
		glLoadIdentity();
	} else {
		glLoadMatrixf(&transform.m[0][0]);
	}
	glMatrixMode(GL_MODELVIEW);
	glActiveTexture(GL_TEXTURE0);
	if (glGetError() != GL_NO_ERROR) {
		return false;
	}
	g_applied_texture_transforms[stage] = transform;
	g_applied_texture_transform_flags[stage] = sampler.texture_transform_flags;
	g_applied_texture_transform_valid[stage] = true;
#endif
	return true;
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
	static bool logged_reticle = false;
	const bool reticle = filename != NULL &&
		(stricmp(filename, "hd_reticle.tga") == 0 ||
		 stricmp(filename, "hd_reticle.dds") == 0);
	if (reticle && !logged_reticle && texture != NULL) {
		Vita_Append_A22_Runtime_Breadcrumb("asset-proof",
			"reticle decoded: source=%s name=%s size=%ux%u fallback=%u native=%u",
			source != NULL ? source : "unknown", filename,
			texture->Width, texture->Height,
			texture->DiagnosticFallback ? 1U : 0U, texture->NativeTexture);
		logged_reticle = true;
	}
	if (logged_count >= 24U || texture == NULL) return;
	Vita_Append_A22_Runtime_Breadcrumb("texture-load",
		"texture loaded: source=%s name=%s size=%ux%u mips=%u fmt=%08X bytes=%llu checksum=%08X alpha=%u fallback=%u native=%u compressed=%u",
		source != NULL ? source : "unknown",
		filename != NULL ? filename : "(null)",
		texture->Width, texture->Height, texture->MipLevels,
		texture->SourceFormat,
		static_cast<unsigned long long>(texture->ResidentBytes),
		texture->PixelChecksum, texture->HasAlpha ? 1U : 0U,
		texture->DiagnosticFallback ? 1U : 0U, texture->NativeTexture,
		texture->NativeCompressed ? 1U : 0U);
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

bool Surface_Format_Can_Convert_To_RGBA(D3DFORMAT format)
{
	switch (format) {
	case D3DFMT_A8R8G8B8:
	case D3DFMT_X8R8G8B8:
	case D3DFMT_R8G8B8:
	case D3DFMT_A4R4G4B4:
	case D3DFMT_A1R5G5B5:
	case D3DFMT_R5G6B5:
	case D3DFMT_A8:
	case D3DFMT_L8:
		return true;
	default:
		return false;
	}
}

bool Write_RGBA_To_Surface_Pixel(D3DFORMAT format, const unsigned char *rgba,
	unsigned char *destination)
{
	if (rgba == NULL || destination == NULL) return false;
	switch (format) {
	case D3DFMT_A8R8G8B8:
		destination[0] = rgba[2];
		destination[1] = rgba[1];
		destination[2] = rgba[0];
		destination[3] = rgba[3];
		return true;
	case D3DFMT_X8R8G8B8:
		destination[0] = rgba[2];
		destination[1] = rgba[1];
		destination[2] = rgba[0];
		destination[3] = 0xffU;
		return true;
	case D3DFMT_R8G8B8:
		destination[0] = rgba[2];
		destination[1] = rgba[1];
		destination[2] = rgba[0];
		return true;
	case D3DFMT_A4R4G4B4: {
		const uint16_t pixel =
			(static_cast<uint16_t>(rgba[3] >> 4U) << 12U) |
			(static_cast<uint16_t>(rgba[0] >> 4U) << 8U) |
			(static_cast<uint16_t>(rgba[1] >> 4U) << 4U) |
			static_cast<uint16_t>(rgba[2] >> 4U);
		destination[0] = static_cast<unsigned char>(pixel & 0xffU);
		destination[1] = static_cast<unsigned char>(pixel >> 8U);
		return true;
	}
	case D3DFMT_A1R5G5B5: {
		const uint16_t pixel =
			(rgba[3] >= 0x80U ? 0x8000U : 0U) |
			(static_cast<uint16_t>(rgba[0] >> 3U) << 10U) |
			(static_cast<uint16_t>(rgba[1] >> 3U) << 5U) |
			static_cast<uint16_t>(rgba[2] >> 3U);
		destination[0] = static_cast<unsigned char>(pixel & 0xffU);
		destination[1] = static_cast<unsigned char>(pixel >> 8U);
		return true;
	}
	case D3DFMT_R5G6B5: {
		const uint16_t pixel =
			(static_cast<uint16_t>(rgba[0] >> 3U) << 11U) |
			(static_cast<uint16_t>(rgba[1] >> 2U) << 5U) |
			static_cast<uint16_t>(rgba[2] >> 3U);
		destination[0] = static_cast<unsigned char>(pixel & 0xffU);
		destination[1] = static_cast<unsigned char>(pixel >> 8U);
		return true;
	}
	case D3DFMT_A8:
		destination[0] = rgba[3];
		return true;
	case D3DFMT_L8:
		destination[0] = static_cast<unsigned char>(
			(static_cast<unsigned>(rgba[0]) * 30U +
			static_cast<unsigned>(rgba[1]) * 59U +
			static_cast<unsigned>(rgba[2]) * 11U) / 100U);
		return true;
	default:
		return false;
	}
}

bool Surface_Format_Can_Write_RGBA(D3DFORMAT format)
{
	switch (format) {
	case D3DFMT_A8R8G8B8:
	case D3DFMT_X8R8G8B8:
	case D3DFMT_R8G8B8:
	case D3DFMT_A4R4G4B4:
	case D3DFMT_A1R5G5B5:
	case D3DFMT_R5G6B5:
	case D3DFMT_A8:
	case D3DFMT_L8:
		return true;
	default:
		return false;
	}
}

bool Surface_Format_Is_Block_Compressed(D3DFORMAT format)
{
	return format == D3DFMT_DXT1 || format == D3DFMT_DXT2 ||
		format == D3DFMT_DXT3 || format == D3DFMT_DXT4 ||
		format == D3DFMT_DXT5;
}

bool Validate_Surface_Copy_Rect(const D3DSURFACE_DESC &description,
	const RECT *rectangle, RECT *out)
{
	if (out == NULL || description.Width == 0U || description.Height == 0U) {
		return false;
	}
	if (rectangle == NULL) {
		out->left = 0;
		out->top = 0;
		out->right = static_cast<LONG>(description.Width);
		out->bottom = static_cast<LONG>(description.Height);
		return true;
	}
	if (rectangle->left < 0 || rectangle->top < 0 ||
		rectangle->right < rectangle->left ||
		rectangle->bottom < rectangle->top ||
		static_cast<UINT>(rectangle->right) > description.Width ||
		static_cast<UINT>(rectangle->bottom) > description.Height) {
		return false;
	}
	*out = *rectangle;
	return true;
}

bool Validate_Surface_Destination_Rect(const D3DSURFACE_DESC &description,
	const RECT &source_rect, const POINT *point, const RECT *destination_rect,
	RECT *out)
{
	if (out == NULL) return false;
	if (destination_rect != NULL) {
		return Validate_Surface_Copy_Rect(description, destination_rect, out);
	}
	const LONG width = source_rect.right - source_rect.left;
	const LONG height = source_rect.bottom - source_rect.top;
	const LONG left = point != NULL ? point->x : source_rect.left;
	const LONG top = point != NULL ? point->y : source_rect.top;
	if (left < 0 || top < 0 || width < 0 || height < 0 ||
		static_cast<UINT>(left) > description.Width ||
		static_cast<UINT>(top) > description.Height ||
		static_cast<UINT>(width) > description.Width - static_cast<UINT>(left) ||
		static_cast<UINT>(height) > description.Height - static_cast<UINT>(top)) {
		return false;
	}
	out->left = left;
	out->top = top;
	out->right = left + width;
	out->bottom = top + height;
	return true;
}

bool Copy_Surface_Rect_Bytes(IDirect3DSurface8 *source, const RECT &source_rect,
	IDirect3DSurface8 *destination, const RECT &destination_rect,
	UINT bytes_per_pixel)
{
	if (source == NULL || destination == NULL || source->Get_Data() == NULL ||
		destination->Get_Data() == NULL || bytes_per_pixel == 0U) {
		return false;
	}
	const UINT width = static_cast<UINT>(source_rect.right - source_rect.left);
	const UINT height = static_cast<UINT>(source_rect.bottom - source_rect.top);
	if (width == 0U || height == 0U) return true;
	if (width != static_cast<UINT>(destination_rect.right - destination_rect.left) ||
		height != static_cast<UINT>(destination_rect.bottom - destination_rect.top)) {
		return false;
	}
	const size_t row_bytes = static_cast<size_t>(width) * bytes_per_pixel;
	const size_t source_offset = static_cast<size_t>(source_rect.top) *
		source->Get_Pitch() + static_cast<size_t>(source_rect.left) *
		bytes_per_pixel;
	const size_t destination_offset = static_cast<size_t>(destination_rect.top) *
		destination->Get_Pitch() + static_cast<size_t>(destination_rect.left) *
		bytes_per_pixel;
	const unsigned char *source_base = source->Get_Data() + source_offset;
	unsigned char *destination_base = destination->Get_Data() + destination_offset;
	if (source == destination && destination_offset > source_offset) {
		for (UINT y = height; y > 0U; --y) {
			const UINT row = y - 1U;
			memmove(destination_base + static_cast<size_t>(row) *
				destination->Get_Pitch(),
				source_base + static_cast<size_t>(row) * source->Get_Pitch(),
				row_bytes);
		}
		return true;
	}
	for (UINT y = 0U; y < height; ++y) {
		memmove(destination_base + static_cast<size_t>(y) *
			destination->Get_Pitch(),
			source_base + static_cast<size_t>(y) * source->Get_Pitch(),
			row_bytes);
	}
	return true;
}

bool Load_Surface_Rect_Filtered(IDirect3DSurface8 *destination,
	const RECT &destination_rect, IDirect3DSurface8 *source,
	const RECT &source_rect, DWORD filter)
{
	D3DSURFACE_DESC source_description = {};
	D3DSURFACE_DESC destination_description = {};
	if (source == NULL || destination == NULL || source->Get_Data() == NULL ||
		destination->Get_Data() == NULL ||
		source->GetDesc(&source_description) != D3D_OK ||
		destination->GetDesc(&destination_description) != D3D_OK ||
		!Surface_Format_Can_Convert_To_RGBA(source_description.Format) ||
		!Surface_Format_Can_Write_RGBA(destination_description.Format)) {
		return false;
	}
	const UINT source_width =
		static_cast<UINT>(source_rect.right - source_rect.left);
	const UINT source_height =
		static_cast<UINT>(source_rect.bottom - source_rect.top);
	const UINT destination_width =
		static_cast<UINT>(destination_rect.right - destination_rect.left);
	const UINT destination_height =
		static_cast<UINT>(destination_rect.bottom - destination_rect.top);
	if (source_width == 0U || source_height == 0U ||
		destination_width == 0U || destination_height == 0U) {
		return true;
	}
	const UINT source_bpp = Surface_Bytes_Per_Pixel(source_description.Format);
	const UINT destination_bpp =
		Surface_Bytes_Per_Pixel(destination_description.Format);
	const bool point_sample = filter == D3DX_FILTER_NONE ||
		filter == D3DX_FILTER_POINT || destination_width >= source_width ||
		destination_height >= source_height;
	for (UINT y = 0U; y < destination_height; ++y) {
		for (UINT x = 0U; x < destination_width; ++x) {
			unsigned rgba_sum[4] = {};
			unsigned sample_count = 0U;
			UINT begin_x = static_cast<UINT>(
				(static_cast<uint64_t>(x) * source_width) / destination_width);
			UINT begin_y = static_cast<UINT>(
				(static_cast<uint64_t>(y) * source_height) / destination_height);
			UINT end_x = point_sample ? begin_x + 1U : static_cast<UINT>(
				(static_cast<uint64_t>(x + 1U) * source_width +
				destination_width - 1U) / destination_width);
			UINT end_y = point_sample ? begin_y + 1U : static_cast<UINT>(
				(static_cast<uint64_t>(y + 1U) * source_height +
				destination_height - 1U) / destination_height);
			if (end_x <= begin_x) end_x = begin_x + 1U;
			if (end_y <= begin_y) end_y = begin_y + 1U;
			if (end_x > source_width) end_x = source_width;
			if (end_y > source_height) end_y = source_height;
			for (UINT sy = begin_y; sy < end_y; ++sy) {
				const unsigned char *source_row = source->Get_Data() +
					static_cast<size_t>(source_rect.top + sy) *
					source->Get_Pitch();
				for (UINT sx = begin_x; sx < end_x; ++sx) {
					unsigned char rgba[4] = {};
					if (!Convert_Surface_Pixel_To_RGBA(source_description.Format,
						source_row + static_cast<size_t>(source_rect.left + sx) *
						source_bpp, rgba)) {
						return false;
					}
					rgba_sum[0] += rgba[0];
					rgba_sum[1] += rgba[1];
					rgba_sum[2] += rgba[2];
					rgba_sum[3] += rgba[3];
					++sample_count;
				}
			}
			if (sample_count == 0U) return false;
			unsigned char averaged[4] = {
				static_cast<unsigned char>(rgba_sum[0] / sample_count),
				static_cast<unsigned char>(rgba_sum[1] / sample_count),
				static_cast<unsigned char>(rgba_sum[2] / sample_count),
				static_cast<unsigned char>(rgba_sum[3] / sample_count)
			};
			unsigned char *destination_pixel = destination->Get_Data() +
				static_cast<size_t>(destination_rect.top + y) *
				destination->Get_Pitch() +
				static_cast<size_t>(destination_rect.left + x) * destination_bpp;
			if (!Write_RGBA_To_Surface_Pixel(destination_description.Format,
				averaged, destination_pixel)) {
				return false;
			}
		}
	}
	return true;
}

UINT Texture_Level_Dimension(UINT base, UINT level)
{
	const UINT dimension = base >> level;
	return dimension == 0U ? 1U : dimension;
}

UINT Calculate_Texture_Mip_Count(UINT width, UINT height,
	TextureClass::MipCountType requested_mips)
{
	UINT full_count = 1U;
	for (UINT w = width, h = height; w > 1U || h > 1U; ) {
		if (w > 1U) w >>= 1U;
		if (h > 1U) h >>= 1U;
		++full_count;
	}
	if (requested_mips == TextureClass::MIP_LEVELS_ALL) return full_count;
	UINT mip_count = static_cast<UINT>(requested_mips);
	if (mip_count == 0U) mip_count = 1U;
	return mip_count < full_count ? mip_count : full_count;
}

uint64_t Calculate_Texture_Resident_Bytes(UINT width, UINT height,
	UINT mip_count)
{
	uint64_t bytes = 0U;
	for (UINT level = 0U; level < mip_count; ++level) {
		bytes += static_cast<uint64_t>(Texture_Level_Dimension(width, level)) *
			static_cast<uint64_t>(Texture_Level_Dimension(height, level)) * 4U;
	}
	return bytes;
}

void Destroy_Texture_Surface_Levels(IDirect3DTexture8 *texture)
{
	if (texture == NULL) return;
	const UINT mip_count = texture->GetLevelCount();
	if (texture->SurfaceLevels != NULL) {
		for (UINT level = 0U; level < mip_count; ++level) {
			if (texture->SurfaceLevels[level] != NULL) {
				texture->SurfaceLevels[level]->Set_Texture_Owner(NULL, 0U);
				texture->SurfaceLevels[level]->Release();
				texture->SurfaceLevels[level] = NULL;
			}
		}
		delete [] texture->SurfaceLevels;
		texture->SurfaceLevels = NULL;
	}
	delete [] texture->SurfaceLocked;
	texture->SurfaceLocked = NULL;
	delete [] texture->SurfaceLockFlags;
	texture->SurfaceLockFlags = NULL;
	texture->LockedSurfaceCount = 0U;
	texture->TextureLocked = false;
}

bool Allocate_Texture_Surface_Levels(IDirect3DTexture8 *texture)
{
	if (texture == NULL) return false;
	const UINT mip_count = texture->GetLevelCount();
	if (texture->SurfaceLevels == NULL) {
		texture->SurfaceLevels = new (std::nothrow) IDirect3DSurface8 *[mip_count];
		if (texture->SurfaceLevels == NULL) return false;
		memset(texture->SurfaceLevels, 0, sizeof(IDirect3DSurface8 *) * mip_count);
	}
	if (texture->SurfaceLocked == NULL) {
		texture->SurfaceLocked = new (std::nothrow) bool[mip_count];
		if (texture->SurfaceLocked == NULL) {
			Destroy_Texture_Surface_Levels(texture);
			return false;
		}
		memset(texture->SurfaceLocked, 0, sizeof(bool) * mip_count);
	}
	if (texture->SurfaceLockFlags == NULL) {
		texture->SurfaceLockFlags = new (std::nothrow) DWORD[mip_count];
		if (texture->SurfaceLockFlags == NULL) {
			Destroy_Texture_Surface_Levels(texture);
			return false;
		}
		memset(texture->SurfaceLockFlags, 0, sizeof(DWORD) * mip_count);
	}
	return true;
}

bool Convert_Surface_To_RGBA(IDirect3DSurface8 *surface,
	std::vector<unsigned char> &rgba, uint32_t *checksum)
{
	if (surface == NULL || surface->Get_Data() == NULL) return false;
	D3DSURFACE_DESC description = {};
	if (surface->GetDesc(&description) != D3D_OK || description.Width == 0U ||
		description.Height == 0U ||
		!Surface_Format_Can_Convert_To_RGBA(description.Format)) {
		return false;
	}
	const unsigned bytes_per_pixel = Surface_Bytes_Per_Pixel(description.Format);
	rgba.assign(static_cast<size_t>(description.Width) * description.Height * 4U, 0U);
	uint32_t mixed = 2166136261U;
	for (unsigned y = 0U; y < description.Height; ++y) {
		const unsigned char *source_row = surface->Get_Data() +
			static_cast<size_t>(y) * surface->Get_Pitch();
		for (unsigned x = 0U; x < description.Width; ++x) {
			unsigned char *destination = rgba.data() +
				(static_cast<size_t>(y) * description.Width + x) * 4U;
			if (!Convert_Surface_Pixel_To_RGBA(description.Format,
				source_row + static_cast<size_t>(x) * bytes_per_pixel, destination)) {
				return false;
			}
			mixed = Mix_Texture_Checksum(mixed,
				static_cast<uint32_t>(destination[0]) |
				(static_cast<uint32_t>(destination[1]) << 8U) |
				(static_cast<uint32_t>(destination[2]) << 16U) |
				(static_cast<uint32_t>(destination[3]) << 24U));
		}
	}
	if (checksum != NULL) *checksum = mixed;
	return true;
}

#if defined(__vita__)
// Upload into a fresh object before retiring the old compressed image. The
// original CPU surfaces, including other mips and any caller's references,
// remain intact. No GPU object can contain mixed compressed/RGBA levels.
bool Upload_Retained_DDS_Chain(IDirect3DTexture8 *texture, bool replace,
	UINT changed_level)
{
	if (texture == NULL || texture->SurfaceLevels == NULL ||
		texture->MipLevels == 0U || texture->MipLevels > 10U) return false;
	const void *pixels[10] = {};
	GLsizei sizes[10] = {};
	uint64_t bytes = 0U;
	for (UINT level = 0; level < texture->MipLevels; ++level) {
		IDirect3DSurface8 *surface = texture->SurfaceLevels[level];
		D3DSURFACE_DESC description = {};
		const UINT width = texture->Width >> level, height = texture->Height >> level;
		if (surface == NULL || surface->Get_Data() == NULL ||
			surface->GetDesc(&description) != D3D_OK ||
			description.Format != D3DFMT_A8R8G8B8 || width < 4U || height < 4U ||
			width > 2048U || height > 2048U || description.Width != width ||
			description.Height != height || surface->Get_Pitch() != width * 4U) return false;
		pixels[level] = surface->Get_Data();
		sizes[level] = static_cast<GLsizei>(width * height * 4U);
		bytes += static_cast<uint64_t>(width < 8U ? 8U : width) * height * 4U;
	}
	GLuint native = replace ? 0U : texture->NativeTexture;
	if (replace) glGenTextures(1, &native);
	if (native == 0U) return false;
	glBindTexture(GL_TEXTURE_2D, native);
	RenegadeVitaRenderer::Invalidate_Texture_State_Cache();
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
		texture->MipLevels > 1U ? GL_LINEAR_MIPMAP_LINEAR : GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	if (!vglRenegadeUploadDXTChain(native, GL_BGRA, texture->Width,
		texture->Height, texture->MipLevels, pixels, sizes) || glGetError() != GL_NO_ERROR) {
		if (replace) RenegadeVitaRenderer::Release_Texture(native);
		return false;
	}
	if (replace) {
		RenegadeVitaRenderer::Release_Texture(texture->NativeTexture);
		RenegadeVitaRenderer::Record_Texture_Release(texture->ResidentBytes);
		RenegadeVitaRenderer::Record_Texture_Upload(bytes);
		if (changed_level == 0U) {
			uint32_t checksum = 2166136261U;
			const unsigned char *source = static_cast<const unsigned char *>(pixels[0]);
			for (GLsizei offset = 0; offset < sizes[0]; offset += 4) {
				const uint32_t rgba = source[offset + 2] |
					(static_cast<uint32_t>(source[offset + 1]) << 8U) |
					(static_cast<uint32_t>(source[offset]) << 16U) |
					(static_cast<uint32_t>(source[offset + 3]) << 24U);
				checksum = Mix_Texture_Checksum(checksum, rgba);
			}
			texture->PixelChecksum = checksum;
		}
	}
	texture->NativeTexture = native;
	texture->ResidentBytes = bytes;
	texture->NativeCompressed = false;
	texture->Uploaded = true;
	return true;
}
#endif

bool Upload_Texture_Level_From_Surface(IDirect3DTexture8 *texture, UINT level)
{
	if (texture == NULL || texture->SurfaceLevels == NULL ||
		level >= texture->GetLevelCount() || texture->SurfaceLevels[level] == NULL) {
		return false;
	}
#if defined(__vita__)
	if (texture->NativeCompressed) return Upload_Retained_DDS_Chain(texture, true, level);
#endif
	D3DSURFACE_DESC description = {};
	if (texture->SurfaceLevels[level]->GetDesc(&description) != D3D_OK) {
		return false;
	}
	std::vector<unsigned char> rgba;
	uint32_t checksum = 0U;
	if (!Convert_Surface_To_RGBA(texture->SurfaceLevels[level], rgba, &checksum)) {
		return false;
	}
#if defined(__vita__)
	(void)glGetError();
	if (texture->NativeTexture == 0U) {
		GLuint native = 0U;
		glGenTextures(1, &native);
		if (native == 0U) return false;
		texture->NativeTexture = native;
	}
	glBindTexture(GL_TEXTURE_2D, texture->NativeTexture);
	RenegadeVitaRenderer::Invalidate_Texture_State_Cache();
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
		texture->GetLevelCount() > 1U ? GL_LINEAR_MIPMAP_LINEAR : GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	glTexImage2D(GL_TEXTURE_2D, level, GL_RGBA, description.Width,
		description.Height, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba.data());
	if (glGetError() != GL_NO_ERROR) return false;
#else
	if (texture->NativeTexture == 0U) texture->NativeTexture = 1U;
#endif
	texture->Uploaded = true;
	if (level == 0U) texture->PixelChecksum = checksum;
	return true;
}

bool Attach_Texture_Surface_Copy(IDirect3DTexture8 *texture, UINT level,
	IDirect3DSurface8 *source)
{
	if (texture == NULL || source == NULL || level >= texture->GetLevelCount() ||
		source->Get_Data() == NULL || !Allocate_Texture_Surface_Levels(texture)) {
		return false;
	}
	D3DSURFACE_DESC description = {};
	if (source->GetDesc(&description) != D3D_OK) return false;
	IDirect3DSurface8 *copy = new (std::nothrow) IDirect3DSurface8(
		description.Width, description.Height, description.Format,
		Surface_Bytes_Per_Pixel(description.Format));
	if (copy == NULL || copy->Get_Data() == NULL) {
		if (copy != NULL) copy->Release();
		return false;
	}
	const size_t row_bytes = static_cast<size_t>(description.Width) *
		Surface_Bytes_Per_Pixel(description.Format);
	for (unsigned y = 0U; y < description.Height; ++y) {
		memcpy(copy->Get_Data() + static_cast<size_t>(y) * copy->Get_Pitch(),
			source->Get_Data() + static_cast<size_t>(y) * source->Get_Pitch(),
			row_bytes);
	}
	if (texture->SurfaceLevels[level] != NULL) {
		texture->SurfaceLevels[level]->Set_Texture_Owner(NULL, 0U);
		texture->SurfaceLevels[level]->Release();
	}
	copy->Set_Texture_Owner(texture, level);
	texture->SurfaceLevels[level] = copy;
	return true;
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
	RenegadeVitaRenderer::Invalidate_Texture_State_Cache();
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
	(void)Attach_Texture_Surface_Copy(texture, 0U, surface);
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
	RenegadeVitaRenderer::Invalidate_Texture_State_Cache();
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
	if (!Allocate_Texture_Surface_Levels(texture)) {
		delete texture;
		Log_Texture_Fallback("dds-surface-levels", filename);
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return Create_Checkerboard_Fallback();
	}
	uint32_t checksum = 2166136261U;
	uint64_t bytes = 0U;
#if defined(__vita__)
	const void *native_pixels[10] = {};
	GLsizei native_sizes[10] = {};
	const GLenum native_format = dds.Get_Format() == WW3D_FORMAT_DXT1 ?
		GL_COMPRESSED_RGBA_S3TC_DXT1_EXT : GL_COMPRESSED_RGBA_S3TC_DXT5_EXT;
	bool native_dxt = RenegadeVitaRenderer::Use_Native_DDS_Upload() && mip_count <= 10U &&
		(dds.Get_Format() == WW3D_FORMAT_DXT1 || dds.Get_Format() == WW3D_FORMAT_DXT5) &&
		texture->Width <= 2048U && texture->Height <= 2048U &&
		(texture->Width & (texture->Width - 1U)) == 0U &&
		(texture->Height & (texture->Height - 1U)) == 0U;
	uint64_t compressed_bytes = 0U;
	for (unsigned level = 0; native_dxt && level < mip_count; ++level) {
		const unsigned width = texture->Width >> level, height = texture->Height >> level;
		const unsigned count = (width / 4U) * (height / 4U) *
			(dds.Get_Format() == WW3D_FORMAT_DXT1 ? 8U : 16U);
		native_dxt = width >= 4U && height >= 4U && dds.Get_Width(level) == width &&
			dds.Get_Height(level) == height && dds.Get_Level_Size(level) >= count;
		native_pixels[level] = dds.Get_Memory_Pointer(level);
		native_sizes[level] = static_cast<GLsizei>(count);
		compressed_bytes += count;
	}
	(void)glGetError();
	GLuint native = 0U;
	glGenTextures(1, &native);
	if (native == 0U) {
		Destroy_Texture_Surface_Levels(texture);
		delete texture;
		Log_Texture_Fallback("dds-gl-gen", filename);
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return Create_Checkerboard_Fallback();
	}
	texture->NativeTexture = native;
	glBindTexture(GL_TEXTURE_2D, native);
	RenegadeVitaRenderer::Invalidate_Texture_State_Cache();
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
		IDirect3DSurface8 *surface = new (std::nothrow) IDirect3DSurface8(
			width, height, D3DFMT_A8R8G8B8,
			Surface_Bytes_Per_Pixel(D3DFMT_A8R8G8B8));
		if (surface == NULL || surface->Get_Data() == NULL) {
			if (surface != NULL) surface->Release();
#if defined(__vita__)
			RenegadeVitaRenderer::Release_Texture(native);
#endif
			Destroy_Texture_Surface_Levels(texture);
			delete texture;
			Log_Texture_Fallback("dds-surface-alloc", filename);
			RenegadeVitaRenderer::Record_Texture_Upload_Failure();
			return Create_Checkerboard_Fallback();
		}
		const unsigned surface_bpp = Surface_Bytes_Per_Pixel(D3DFMT_A8R8G8B8);
		const bool use_block_decode = surface_bpp == sizeof(uint32_t) &&
			(dds.Get_Format() == WW3D_FORMAT_DXT1 || dds.Get_Format() == WW3D_FORMAT_DXT5) &&
			(width & 3U) == 0U && (height & 3U) == 0U;
		for (unsigned y = 0U; y < height; ++y) {
			unsigned char *surface_row = surface->Get_Data() +
				static_cast<size_t>(y) * surface->Get_Pitch();
			const size_t rgba_row_offset = static_cast<size_t>(y) * width * 4U;
			if (use_block_decode && (y & 3U) == 0U) {
				// Original DDS block decode shares endpoint/alpha work across
				// sixteen pixels. The retained CPU surface is also our row cache;
				// no separate scratch image or per-block allocation is needed.
				for (unsigned block_x = 0U; block_x < width; block_x += 4U) {
					// Return value reports alpha presence, not decode success.
					(void)dds.Get_4x4_Block(surface_row +
						static_cast<size_t>(block_x) * surface_bpp,
						surface->Get_Pitch(), WW3D_FORMAT_A8R8G8B8,
						level, block_x, y);
				}
			}
			for (unsigned x = 0U; x < width; ++x) {
				uint32_t argb;
				if (use_block_decode) {
					memcpy(&argb, surface_row + static_cast<size_t>(x) * surface_bpp,
						sizeof(argb));
				} else {
					argb = dds.Get_Pixel(level, x, y);
				}
				RenegadeVitaTextureUpload::Store_RGBA_From_ARGB_At(argb,
					x, y, width, rgba.data());
				checksum = Mix_Texture_Checksum(checksum, argb);
				// Populate the retained CPU surface while this decoded pixel is
				// hot, rather than traversing the whole RGBA image a second time.
				if (!use_block_decode) {
					Write_RGBA_To_Surface_Pixel(D3DFMT_A8R8G8B8,
						rgba.data() + rgba_row_offset + static_cast<size_t>(x) * 4U,
						surface_row + static_cast<size_t>(x) * surface_bpp);
				}
			}
		}
		surface->Set_Texture_Owner(texture, level);
		texture->SurfaceLevels[level] = surface;
		bytes += rgba.size();
#if defined(__vita__)
		if (!native_dxt) {
			glTexImage2D(GL_TEXTURE_2D, level, GL_RGBA, width, height, 0,
				GL_RGBA, GL_UNSIGNED_BYTE, rgba.data());
		}
#endif
	}
#if defined(__vita__)
	bool native_upload_ok = true;
	if (native_dxt) {
		if (vglRenegadeUploadDXTChain(native, native_format, texture->Width,
			texture->Height, mip_count, native_pixels, native_sizes)) {
			texture->NativeCompressed = true;
			bytes = compressed_bytes;
		} else {
			// Allocation/eligibility failure retains all original CPU surfaces.
			// Attempt one complete RGBA chain in the still-fresh GL object.
			native_upload_ok = Upload_Retained_DDS_Chain(texture, false, 0U);
			if (native_upload_ok) bytes = texture->ResidentBytes;
		}
	}
	if (!native_upload_ok || glGetError() != GL_NO_ERROR) {
		RenegadeVitaRenderer::Release_Texture(native);
		Destroy_Texture_Surface_Levels(texture);
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

int Get_Indexed_Material_UV_Source(VertexMaterialClass *material, unsigned stage)
{
	const int fallback_uv_source = static_cast<int>(stage);
	if (material == NULL) return fallback_uv_source;
	const int uv_source = material->Get_UV_Source(static_cast<int>(stage));
	return uv_source >= 0 ? uv_source : fallback_uv_source;
}

void Apply_Indexed_Texture_Coordinate_State(VertexMaterialClass *material)
{
	static bool logged_first_mapper = false;
	for (unsigned stage = 0U; stage < MAX_TEXTURE_STAGES; ++stage) {
		const int uv_source = Get_Indexed_Material_UV_Source(material, stage);
		TextureMapperClass *mapper = NULL;
		if (material != NULL) mapper = material->Peek_Mapper(static_cast<int>(stage));
		if (mapper != NULL) {
			mapper->Apply(uv_source);
#if defined(__vita__)
			if (!logged_first_mapper) {
				Vita_Append_A22_Runtime_Breadcrumb("indexed-submit",
					"first original indexed VertexMaterial mapper: material=%s stage=%u mapper=%d uv=%d",
					material != NULL ? material->Get_Name() : "NULL",
					stage, mapper->Mapper_ID(), uv_source);
				logged_first_mapper = true;
			}
#endif
		} else {
			DX8Wrapper::Set_DX8_Texture_Stage_State(stage,
				D3DTSS_TEXCOORDINDEX,
				D3DTSS_TCI_PASSTHRU | static_cast<unsigned>(uv_source));
			DX8Wrapper::Set_DX8_Texture_Stage_State(stage,
				D3DTSS_TEXTURETRANSFORMFLAGS, D3DTTFF_DISABLE);
		}
	}
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
	for (unsigned stage = 0; stage < 2U && stage < MAX_TEXTURE_STAGES; ++stage) {
		submission.texture_names[stage] = state.Textures[stage] != NULL ?
			state.Textures[stage]->Get_Texture_Name().Peek_Buffer() : NULL;
	}
	/* DynamicVB users such as original Render2D, Haze, Starfield, CloudLayer,
	** and SkyObject retain shader and texture changes in DX8Wrapper::render_state
	** until Draw_Triangles.  The native boundary must consume the complete
	** original shader contract, including each texture combiner, before emitting
	** indexed geometry.  Without that, a glyph atlas can inherit the preceding
	** mesh's texture-alpha rule and render transparent despite valid pixels. */
	const bool indexed_texturing =
		state.shader.Get_Texturing() != ShaderClass::TEXTURING_DISABLE;
	const bool stage0_texture = indexed_texturing && state.Textures[0] != NULL;
	const bool stage1_texture = indexed_texturing && state.Textures[1] != NULL;
	for (unsigned stage = 0; stage < MAX_TEXTURE_STAGES; ++stage) {
		if (indexed_texturing && state.Textures[stage] != NULL) {
			state.Textures[stage]->Apply_For_Platform_Boundary(stage);
		} else if (stage == 0U) {
			RenegadeVitaRenderer::Bind_Texture(0U, false);
		} else {
			RenegadeVitaRenderer::Disable_Texture_Stage(stage);
		}
	}
	// TextureClass::Apply replays the device's stage combiner as well as its
	// binding/sampler. Apply the draw's original ShaderClass after those calls
	// so a previous mesh or movie cannot overwrite the glyph alpha contract.
	RenegadeVitaRenderer::Apply_Indexed_Shader_State(state.shader,
		stage0_texture, stage1_texture);
	Apply_Indexed_Texture_Coordinate_State(state.material);
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
	  SupportAnisotropicFiltering(false), CanDoMultiPass(true),
	  IsFogAllowed(true), MaxTexturesPerPass(MAX_TEXTURE_STAGES), VertexShaderVersion(0),
	  PixelShaderVersion(0), DeviceId(0), DriverBuildVersion(0),
	  DriverVersionStatus(DRIVER_STATUS_UNKNOWN), VendorId(VENDOR_UNKNOWN),
	  DriverDLL("Vita native renderer boundary"), Direct3D(direct3d),
	  CapsLog("Conservative native Vita capabilities"),
	  CompactLog("VITA_NATIVE_CONSERVATIVE")
{
	(void)display_format;
	(void)adapter_id;
	Caps.TextureOpCaps = D3DTEXOPCAPS_SELECTARG1 | D3DTEXOPCAPS_MODULATE |
		D3DTEXOPCAPS_ADD | D3DTEXOPCAPS_SUBTRACT | D3DTEXOPCAPS_ADDSMOOTH |
		D3DTEXOPCAPS_BLENDTEXTUREALPHA | D3DTEXOPCAPS_BLENDCURRENTALPHA;
	Caps.MaxTextureBlendStages = MAX_TEXTURE_STAGES;
	Caps.MaxSimultaneousTextures = MAX_TEXTURE_STAGES;
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
bool DX8Wrapper::FogEnable = false;
D3DCOLOR DX8Wrapper::FogColor = 0;

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

IDirect3DTexture8 *DX8Wrapper::_Create_DX8_Texture(unsigned int width,
	unsigned int height, WW3DFormat format,
	TextureClass::MipCountType mip_level_count, D3DPOOL pool,
	bool rendertarget)
{
	(void)pool;
	(void)rendertarget;
	if (width == 0U || height == 0U) {
		RenegadeVitaRenderer::Record_Texture_Invalid_Data();
		return NULL;
	}
	const D3DFORMAT d3d_format = WW3DFormat_To_D3DFormat(format);
	if (d3d_format == D3DFMT_UNKNOWN ||
		!Surface_Format_Can_Convert_To_RGBA(d3d_format)) {
		RenegadeVitaRenderer::Record_Texture_Unsupported_Format();
		return NULL;
	}
	IDirect3DTexture8 *texture = new (std::nothrow) IDirect3DTexture8;
	if (texture == NULL) {
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return NULL;
	}
	memset(texture, 0, sizeof(*texture));
	texture->Width = width;
	texture->Height = height;
	texture->MipLevels = Calculate_Texture_Mip_Count(width, height,
		mip_level_count);
	texture->SourceFormat = d3d_format;
	texture->ResidentBytes = Calculate_Texture_Resident_Bytes(width, height,
		texture->MipLevels);
	texture->ReferenceCount = 1U;
	texture->HasAlpha = d3d_format == D3DFMT_A8R8G8B8 ||
		d3d_format == D3DFMT_A4R4G4B4 ||
		d3d_format == D3DFMT_A1R5G5B5 || d3d_format == D3DFMT_A8;
	if (!Allocate_Texture_Surface_Levels(texture)) {
		delete texture;
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return NULL;
	}
	for (UINT level = 0U; level < texture->MipLevels; ++level) {
		const UINT level_width = Texture_Level_Dimension(width, level);
		const UINT level_height = Texture_Level_Dimension(height, level);
		IDirect3DSurface8 *surface = new (std::nothrow) IDirect3DSurface8(
			level_width, level_height, d3d_format,
			Surface_Bytes_Per_Pixel(d3d_format));
		if (surface == NULL || surface->Get_Data() == NULL) {
			if (surface != NULL) surface->Release();
			Destroy_Texture_Surface_Levels(texture);
			delete texture;
			RenegadeVitaRenderer::Record_Texture_Upload_Failure();
			return NULL;
		}
		surface->Set_Texture_Owner(texture, level);
		texture->SurfaceLevels[level] = surface;
		if (!Upload_Texture_Level_From_Surface(texture, level)) {
			Destroy_Texture_Surface_Levels(texture);
			if (texture->NativeTexture != 0U) {
				RenegadeVitaRenderer::Release_Texture(texture->NativeTexture);
			}
			delete texture;
			RenegadeVitaRenderer::Record_Texture_Upload_Failure();
			return NULL;
		}
	}
	RenegadeVitaRenderer::Record_Texture_Upload(texture->ResidentBytes);
	return texture;
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
		Destroy_Texture_Surface_Levels(static_cast<IDirect3DTexture8 *>(this));
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
	description->Size = static_cast<UINT>(description->Width * description->Height *
		Surface_Bytes_Per_Pixel(SourceFormat));
	return D3D_OK;
}

HRESULT IDirect3DTexture8::GetSurfaceLevel(UINT level, IDirect3DSurface8 **surface)
{
	if (surface != NULL) *surface = NULL;
	if (surface == NULL || level >= GetLevelCount()) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	if (SurfaceLevels != NULL && SurfaceLevels[level] != NULL) {
		SurfaceLevels[level]->AddRef();
		*surface = SurfaceLevels[level];
		return D3D_OK;
	}
	D3DSURFACE_DESC description = {};
	if (GetLevelDesc(level, &description) != D3D_OK) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	IDirect3DSurface8 *descriptor_surface = new (std::nothrow) IDirect3DSurface8(
		description.Width, description.Height, description.Format,
		Surface_Bytes_Per_Pixel(description.Format));
	if (descriptor_surface == NULL || descriptor_surface->Get_Data() == NULL) {
		if (descriptor_surface != NULL) descriptor_surface->Release();
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	*surface = descriptor_surface;
	return D3D_OK;
}

HRESULT IDirect3DTexture8::LockRect(UINT level, D3DLOCKED_RECT *locked,
	const RECT *rectangle, DWORD flags)
{
	if (locked == NULL || level >= GetLevelCount() ||
		SurfaceLevels == NULL || SurfaceLevels[level] == NULL ||
		SurfaceLocked == NULL || SurfaceLockFlags == NULL ||
		SurfaceLocked[level]) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	const HRESULT result = SurfaceLevels[level]->LockRect(locked, rectangle, flags);
	if (result == D3D_OK) {
		SurfaceLocked[level] = true;
		SurfaceLockFlags[level] = flags;
		++LockedSurfaceCount;
		TextureLocked = true;
	}
	return result;
}

HRESULT IDirect3DTexture8::UnlockRect(UINT level)
{
	if (level >= GetLevelCount() || SurfaceLevels == NULL ||
		SurfaceLevels[level] == NULL || SurfaceLocked == NULL ||
		SurfaceLockFlags == NULL || !SurfaceLocked[level]) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	const HRESULT result = SurfaceLevels[level]->UnlockRect();
	const DWORD flags = SurfaceLockFlags[level];
	SurfaceLocked[level] = false;
	SurfaceLockFlags[level] = 0U;
	if (LockedSurfaceCount > 0U) --LockedSurfaceCount;
	TextureLocked = LockedSurfaceCount != 0U;
	if (result != D3D_OK) return result;
	if ((flags & D3DLOCK_READONLY) != 0U) return D3D_OK;
	return D3D_OK;
}

DWORD IDirect3DTexture8::GetPriority()
{
	return Priority;
}

DWORD IDirect3DTexture8::SetPriority(DWORD priority)
{
	const DWORD previous = Priority;
	Priority = priority;
	return previous;
}

IDirect3DSurface8::IDirect3DSurface8(UINT width, UINT height,
	D3DFORMAT format, UINT bytes_per_pixel)
	: Storage(NULL), StorageSize(0U), Width(width), Height(height), Pitch(0U),
	  Format(format), ReferenceCount(1U), OwnerTexture(NULL),
	  OwnerTextureLevel(0U), LockFlags(0U), Locked(false)
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
	} else {
		memset(Storage, 0, StorageSize);
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
	const RECT *rectangle, DWORD flags)
{
	if (locked == NULL || Storage == NULL || Locked) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
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
	LockFlags = flags;
	Locked = true;
	return D3D_OK;
}

HRESULT IDirect3DSurface8::UnlockRect()
{
	if (!Locked) return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	const DWORD flags = LockFlags;
	LockFlags = 0U;
	Locked = false;
	if ((flags & D3DLOCK_READONLY) != 0U) return D3D_OK;
	return Upload_Texture_Owner();
}

void IDirect3DSurface8::Set_Texture_Owner(IDirect3DTexture8 *texture, UINT level)
{
	OwnerTexture = texture;
	OwnerTextureLevel = level;
}

HRESULT IDirect3DSurface8::Upload_Texture_Owner()
{
	if (OwnerTexture == NULL) return D3D_OK;
	if (OwnerTexture->SurfaceLevels == NULL ||
		OwnerTextureLevel >= OwnerTexture->GetLevelCount() ||
		OwnerTexture->SurfaceLevels[OwnerTextureLevel] != this) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	if (!Upload_Texture_Level_From_Surface(OwnerTexture, OwnerTextureLevel)) {
		RenegadeVitaRenderer::Record_Texture_Upload_Failure();
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	return D3D_OK;
}

HRESULT IDirect3DDevice8::CopyRects(IDirect3DSurface8 *source,
	const RECT *source_rects, UINT count, IDirect3DSurface8 *destination,
	const POINT *destination_points)
{
	if (source == NULL || destination == NULL || source->Get_Data() == NULL ||
		destination->Get_Data() == NULL ||
		(source_rects == NULL && count != 0U)) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	D3DSURFACE_DESC source_description = {};
	D3DSURFACE_DESC destination_description = {};
	if (source->GetDesc(&source_description) != D3D_OK ||
		destination->GetDesc(&destination_description) != D3D_OK ||
		source_description.Format != destination_description.Format ||
		Surface_Format_Is_Block_Compressed(source_description.Format)) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	const UINT bytes_per_pixel =
		Surface_Bytes_Per_Pixel(source_description.Format);
	if (bytes_per_pixel == 0U) return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	if (source_rects == NULL && count == 0U) {
		RECT source_rect = {};
		RECT destination_rect = {};
		if (!Validate_Surface_Copy_Rect(source_description, NULL, &source_rect) ||
			!Validate_Surface_Destination_Rect(destination_description, source_rect,
			destination_points, NULL, &destination_rect) ||
			!Copy_Surface_Rect_Bytes(source, source_rect, destination,
			destination_rect, bytes_per_pixel)) {
			return static_cast<HRESULT>(D3DERR_INVALIDCALL);
		}
		return destination->Upload_Texture_Owner();
	}
	for (UINT index = 0U; index < count; ++index) {
		RECT source_rect = {};
		RECT destination_rect = {};
		const POINT *destination_point = destination_points != NULL ?
			&destination_points[index] : NULL;
		if (!Validate_Surface_Copy_Rect(source_description, &source_rects[index],
			&source_rect) ||
			!Validate_Surface_Destination_Rect(destination_description, source_rect,
			destination_point, NULL, &destination_rect) ||
			!Copy_Surface_Rect_Bytes(source, source_rect, destination,
			destination_rect, bytes_per_pixel)) {
			return static_cast<HRESULT>(D3DERR_INVALIDCALL);
		}
	}
	return destination->Upload_Texture_Owner();
}

HRESULT D3DXLoadSurfaceFromSurface(IDirect3DSurface8 *destination,
	const void *destination_palette, const RECT *destination_rect,
	IDirect3DSurface8 *source, const void *source_palette,
	const RECT *source_rect, DWORD filter, D3DCOLOR color_key)
{
	if (destination == NULL || source == NULL || destination_palette != NULL ||
		source_palette != NULL || color_key != 0U ||
		destination->Get_Data() == NULL || source->Get_Data() == NULL) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	D3DSURFACE_DESC source_description = {};
	D3DSURFACE_DESC destination_description = {};
	RECT validated_source = {};
	RECT validated_destination = {};
	if (source->GetDesc(&source_description) != D3D_OK ||
		destination->GetDesc(&destination_description) != D3D_OK ||
		!Validate_Surface_Copy_Rect(source_description, source_rect,
		&validated_source) ||
		!Validate_Surface_Copy_Rect(destination_description, destination_rect,
		&validated_destination)) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	const UINT source_width =
		static_cast<UINT>(validated_source.right - validated_source.left);
	const UINT source_height =
		static_cast<UINT>(validated_source.bottom - validated_source.top);
	const UINT destination_width =
		static_cast<UINT>(validated_destination.right - validated_destination.left);
	const UINT destination_height =
		static_cast<UINT>(validated_destination.bottom - validated_destination.top);
	if (source_width == destination_width && source_height == destination_height &&
		source_description.Format == destination_description.Format &&
		!Surface_Format_Is_Block_Compressed(source_description.Format)) {
		const UINT bytes_per_pixel =
			Surface_Bytes_Per_Pixel(source_description.Format);
		if (!Copy_Surface_Rect_Bytes(source, validated_source, destination,
			validated_destination, bytes_per_pixel)) {
			return static_cast<HRESULT>(D3DERR_INVALIDCALL);
		}
		return destination->Upload_Texture_Owner();
	}
	if (!Load_Surface_Rect_Filtered(destination, validated_destination, source,
		validated_source, filter)) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	return destination->Upload_Texture_Owner();
}

HRESULT D3DXFilterTexture(IDirect3DTexture8 *texture, const void *palette,
	UINT source_level, DWORD filter)
{
	if (texture == NULL || palette != NULL || source_level >= texture->GetLevelCount() ||
		texture->SurfaceLevels == NULL) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	const UINT level_count = texture->GetLevelCount();
	for (UINT level = source_level + 1U; level < level_count; ++level) {
		if (texture->SurfaceLevels[level - 1U] == NULL ||
			texture->SurfaceLevels[level] == NULL) {
			return static_cast<HRESULT>(D3DERR_INVALIDCALL);
		}
		const HRESULT result = D3DXLoadSurfaceFromSurface(
			texture->SurfaceLevels[level], NULL, NULL,
			texture->SurfaceLevels[level - 1U], NULL, NULL, filter, 0U);
		if (result != D3D_OK) return result;
	}
	return D3D_OK;
}

void RenegadeVita_Release_DX8_Bound_Textures()
{
	Release_Bound_Texture_Stages();
}

bool RenegadeVita_Get_DX8_Texture_Coordinate_State(DWORD stage,
	DWORD *texcoord_index, DWORD *texture_transform_flags,
	D3DMATRIX *texture_transform)
{
	if (stage >= MAX_TEXTURE_STAGES) return false;
	const TextureStageSamplerState &sampler = g_texture_sampler_states[stage];
	if (texcoord_index != NULL) {
		*texcoord_index = sampler.texcoord_index;
	}
	if (texture_transform_flags != NULL) {
		*texture_transform_flags = sampler.texture_transform_flags;
	}
	if (texture_transform != NULL) {
		*texture_transform = g_boundary_transforms[D3DTS_TEXTURE0 + stage];
	}
	return true;
}

void RenegadeVita_Invalidate_DX8_Texture_Stage_Transform(DWORD stage)
{
	if (stage < MAX_TEXTURE_STAGES) {
		g_applied_texture_transform_valid[stage] = false;
	}
}

HRESULT IDirect3DDevice8::SetTransform(D3DTRANSFORMSTATETYPE state,
	const D3DMATRIX *matrix)
{
	if (matrix != NULL && state < 257U) {
		g_boundary_transforms[state] = *matrix;
		if (state >= D3DTS_TEXTURE0 &&
			state < static_cast<D3DTRANSFORMSTATETYPE>(D3DTS_TEXTURE0 + MAX_TEXTURE_STAGES)) {
			const DWORD stage = static_cast<DWORD>(state - D3DTS_TEXTURE0);
			return Apply_Texture_Stage_Transform(stage) ? D3D_OK :
				static_cast<HRESULT>(D3DERR_INVALIDCALL);
		}
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

HRESULT IDirect3DDevice8::SetRenderState(D3DRENDERSTATETYPE state, DWORD value)
{
	return RenegadeVitaRenderer::Apply_DX8_Render_State(
		static_cast<uint32_t>(state), static_cast<uint32_t>(value)) ?
		D3D_OK : static_cast<HRESULT>(D3DERR_INVALIDCALL);
}

HRESULT IDirect3DDevice8::SetTextureStageState(DWORD stage,
	D3DTEXTURESTAGESTATETYPE state, DWORD value)
{
	if (stage >= MAX_TEXTURE_STAGES) {
		RenegadeVitaRenderer::Record_Texture_Unsupported_Stage(stage);
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	TextureStageSamplerState &sampler = g_texture_sampler_states[stage];
	TextureStageCombinerState &combiner = g_texture_combiner_states[stage];
	switch (state) {
	case D3DTSS_COLOROP: combiner.color_op = value; break;
	case D3DTSS_COLORARG1: combiner.color_arg1 = value; break;
	case D3DTSS_COLORARG2: combiner.color_arg2 = value; break;
	case D3DTSS_ALPHAOP: combiner.alpha_op = value; break;
	case D3DTSS_ALPHAARG1: combiner.alpha_arg1 = value; break;
	case D3DTSS_ALPHAARG2: combiner.alpha_arg2 = value; break;
	case D3DTSS_ADDRESSU: sampler.address_u = value; break;
	case D3DTSS_ADDRESSV: sampler.address_v = value; break;
	case D3DTSS_MINFILTER: sampler.min_filter = value; break;
	case D3DTSS_MAGFILTER: sampler.mag_filter = value; break;
	case D3DTSS_MIPFILTER: sampler.mip_filter = value; break;
	case D3DTSS_TEXCOORDINDEX: sampler.texcoord_index = value; break;
	case D3DTSS_TEXTURETRANSFORMFLAGS: sampler.texture_transform_flags = value; break;
	default:
		// In-range states that are not needed by the current Vita backend stay
		// accepted at the DX8 edge; unsupported-stage telemetry is reserved for
		// out-of-range stage requests so retail stage-1 materials remain visible
		// as supported traffic in hardware logs.
		RenegadeVitaRenderer::Record_Texture_Unsupported_Stage(stage);
		return D3D_OK;
	}
	switch (state) {
	case D3DTSS_COLOROP:
	case D3DTSS_COLORARG1:
	case D3DTSS_COLORARG2:
	case D3DTSS_ALPHAOP:
	case D3DTSS_ALPHAARG1:
	case D3DTSS_ALPHAARG2:
		return Apply_Texture_Stage_Combiner(stage) ? D3D_OK :
			static_cast<HRESULT>(D3DERR_INVALIDCALL);
	case D3DTSS_TEXCOORDINDEX:
	case D3DTSS_TEXTURETRANSFORMFLAGS:
		return Apply_Texture_Stage_Transform(stage) ? D3D_OK :
			static_cast<HRESULT>(D3DERR_INVALIDCALL);
	default:
		break;
	}
	return Apply_Texture_Stage_Sampler(stage) ? D3D_OK :
		static_cast<HRESULT>(D3DERR_INVALIDCALL);
}

HRESULT IDirect3DDevice8::SetTexture(DWORD stage, IDirect3DBaseTexture8 *texture)
{
	if (stage >= MAX_TEXTURE_STAGES) {
		RenegadeVitaRenderer::Record_Texture_Unsupported_Stage(stage);
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	if (!Retain_Bound_Texture_Stage(stage, texture)) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	if (texture == NULL) {
		RenegadeVitaRenderer::Disable_Texture_Stage(stage);
		return D3D_OK;
	}
	if (texture->DiagnosticFallback) {
		RenegadeVitaRenderer::Record_Texture_Checkerboard_Bind();
	}
	RenegadeVitaRenderer::Bind_Texture_Stage(stage, texture->NativeTexture,
		texture->Uploaded && texture->NativeTexture != 0U);
	if (!Apply_Texture_Stage_Sampler(stage)) {
		return static_cast<HRESULT>(D3DERR_INVALIDCALL);
	}
	return Apply_Texture_Stage_Combiner(stage) ? D3D_OK :
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
	// A resolution/session transition can reset the Vita texture matrices while
	// retaining the process-local boundary cache. Force the next mapper call to
	// re-emit its state instead of trusting stale GL state.
	for (int stage = 0; stage < MAX_TEXTURE_STAGES; ++stage) {
		g_applied_texture_transform_valid[stage] = false;
	}
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
	g_boundary_viewport.X = 0U;
	g_boundary_viewport.Y = 0U;
	g_boundary_viewport.Width = g_logical_viewport_width;
	g_boundary_viewport.Height = g_logical_viewport_height;
	g_boundary_viewport.MinZ = 0.0f;
	g_boundary_viewport.MaxZ = 1.0f;
#if defined(__vita__)
	const bool viewport_applied = !RenegadeVitaRenderer::Get_Statistics().initialized ||
		RenegadeVitaRenderer::Apply_Viewport(g_boundary_viewport.X,
			g_boundary_viewport.Y, g_boundary_viewport.Width,
			g_boundary_viewport.Height, g_boundary_viewport.MinZ,
			g_boundary_viewport.MaxZ, g_logical_viewport_width,
			g_logical_viewport_height);
	Vita_Append_A22_Runtime_Breadcrumb("camera-state",
		"DX8Wrapper::Set_Device_Resolution logical=%dx%d viewport=%u,%u %ux%u native_display=%ux%u applied=%d",
		ResolutionWidth, ResolutionHeight, g_boundary_viewport.X,
		g_boundary_viewport.Y, g_boundary_viewport.Width,
		g_boundary_viewport.Height, RenegadeVitaRenderer::DISPLAY_WIDTH,
		RenegadeVitaRenderer::DISPLAY_HEIGHT, viewport_applied ? 1 : 0);
	return viewport_applied;
#else
	return true;
#endif
}

TextureClass *DX8Wrapper::Create_Render_Target(int width, int height,
	WW3DFormat format)
{
	// Original Create_Projector_Render_Target tries UNKNOWN even when no
	// explicit format is supported. Its callers handle NULL without submitting
	// an offscreen draw. This allocation probe is not a rejected indexed draw:
	// counting it as one incorrectly aborts the first ordinary gameplay frame.
	// Keep capabilities false and the original NULL fallback. Actual attempts
	// to bind non-default render targets still fail their submission checks.
#if defined(__vita__)
	static bool logged_unavailable = false;
	if (!logged_unavailable) {
		Vita_Append_A22_Runtime_Breadcrumb("render-capability",
			"render-to-texture creation is unsupported: size=%dx%d format=%u result=NULL original_projector_fallback=1 draw_submitted=0",
			width, height, static_cast<unsigned>(format));
		logged_unavailable = true;
	}
#else
	(void)width;
	(void)height;
	(void)format;
#endif
	return NULL;
}

void DX8Wrapper::Set_Viewport(const D3DVIEWPORT8 *viewport)
{
	DX8_THREAD_ASSERT();
	DX8CALL(SetViewport(viewport));
}

void DX8Wrapper::Apply_Render_State_Changes()
{
	if (!render_state_changed) return;

	const unsigned changed = render_state_changed;
#if defined(__vita__)
	static bool logged_first_deferred_apply = false;
	if (!logged_first_deferred_apply) {
		Vita_Append_A22_Runtime_Breadcrumb("indexed-submit",
			"DX8Wrapper deferred render state apply: mask=%08X shader=%d textures=%d material=%d lights=%d world=%d view=%d vb=%d ib=%d",
			changed,
			(changed & SHADER_CHANGED) != 0U ? 1 : 0,
			(changed & TEXTURES_CHANGED) != 0U ? 1 : 0,
			(changed & MATERIAL_CHANGED) != 0U ? 1 : 0,
			(changed & LIGHTS_CHANGED) != 0U ? 1 : 0,
			(changed & WORLD_CHANGED) != 0U ? 1 : 0,
			(changed & VIEW_CHANGED) != 0U ? 1 : 0,
			(changed & VERTEX_BUFFER_CHANGED) != 0U ? 1 : 0,
			(changed & INDEX_BUFFER_CHANGED) != 0U ? 1 : 0);
		logged_first_deferred_apply = true;
	}
#endif

	if (changed & SHADER_CHANGED) {
		render_state.shader.Apply();
	}

	unsigned texture_mask = TEXTURE0_CHANGED;
	for (unsigned stage = 0U; stage < MAX_TEXTURE_STAGES; ++stage, texture_mask <<= 1U) {
		if ((changed & texture_mask) == 0U) continue;
		if (render_state.Textures[stage] != NULL) {
			render_state.Textures[stage]->Apply(stage);
		} else {
			TextureClass::Apply_Null(stage);
		}
	}

	if (changed & WORLD_CHANGED) {
		_Set_DX8_Transform(D3DTS_WORLD, render_state.world);
	}
	if (changed & VIEW_CHANGED) {
		_Set_DX8_Transform(D3DTS_VIEW, render_state.view);
	}

	/*
	** The Vita indexed submit path evaluates VertexMaterial ownership in
	** RenegadeVitaRenderer and reads the CPU-backed vertex/index buffers directly.
	** There is no native stream-source object to bind here.  Consuming the flags
	** still restores the original DX8Wrapper draw-time state lifetime, while
	** Submit_Bound_Triangles remains the single bridge for buffer emission.
	*/
	(void)(changed & MATERIAL_CHANGED);
	(void)(changed & LIGHTS_CHANGED);
	(void)(changed & VERTEX_BUFFER_CHANGED);
	(void)(changed & INDEX_BUFFER_CHANGED);

	render_state_changed &= ((unsigned)WORLD_IDENTITY | (unsigned)VIEW_IDENTITY);
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
	Apply_Render_State_Changes();
	Submit_Bound_Triangles(render_state, start_index, polygon_count,
		min_vertex_index, vertex_count);
}

void DX8Wrapper::Draw_Triangles(unsigned short start_index,
	unsigned short polygon_count, unsigned short min_vertex_index,
	unsigned short vertex_count)
{
	Apply_Render_State_Changes();
	Submit_Bound_Triangles(render_state, start_index, polygon_count,
		min_vertex_index, vertex_count);
}
