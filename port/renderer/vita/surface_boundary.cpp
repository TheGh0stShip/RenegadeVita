// CPU-backed implementation of the original SurfaceClass DX8 boundary.
// WW3D sentence/font code still owns surface allocation and raster operations;
// only unavailable IDirect3DSurface8 storage is replaced below that contract.

#include "surfaceclass.h"
#include "dx8wrapper.h"
#include "formconv.h"
#include "vector2i.h"

#include <string.h>

namespace {

struct SurfaceStore {
	const SurfaceClass *owner;
	SurfaceClass::SurfaceDescription description;
	unsigned char *pixels;
	size_t bytes;
};

SurfaceStore g_surface_stores[64] = {};

unsigned Bytes_Per_Pixel(WW3DFormat format)
{
	switch (format) {
	case WW3D_FORMAT_A8R8G8B8:
	case WW3D_FORMAT_X8R8G8B8: return 4;
	case WW3D_FORMAT_R8G8B8: return 3;
	case WW3D_FORMAT_R5G6B5:
	case WW3D_FORMAT_X1R5G5B5:
	case WW3D_FORMAT_A1R5G5B5:
	case WW3D_FORMAT_A4R4G4B4:
	case WW3D_FORMAT_A8R3G3B2:
	case WW3D_FORMAT_X4R4G4B4:
	case WW3D_FORMAT_A8P8:
	case WW3D_FORMAT_A8L8: return 2;
	default: return 1;
	}
}

SurfaceStore *Find_Store(const SurfaceClass *owner)
{
	for (unsigned index = 0; index < sizeof(g_surface_stores) / sizeof(g_surface_stores[0]); ++index) {
		if (g_surface_stores[index].owner == owner) return &g_surface_stores[index];
	}
	return NULL;
}

SurfaceStore *Create_Store(const SurfaceClass *owner, unsigned width, unsigned height,
	WW3DFormat format)
{
	for (unsigned index = 0; index < sizeof(g_surface_stores) / sizeof(g_surface_stores[0]); ++index) {
		SurfaceStore &store = g_surface_stores[index];
		if (store.owner != NULL) continue;
		store.owner = owner;
		store.description.Format = format;
		store.description.Width = width;
		store.description.Height = height;
		store.bytes = (size_t)width * (size_t)height * Bytes_Per_Pixel(format);
		store.pixels = new unsigned char[store.bytes];
		memset(store.pixels, 0, store.bytes);
		return &store;
	}
	return NULL;
}

} // namespace

SurfaceClass::SurfaceClass(unsigned width, unsigned height, WW3DFormat format)
	: D3DSurface(NULL), SurfaceFormat(format)
{
	D3DSurface = DX8Wrapper::_Create_DX8_Surface(width, height, format);
}

SurfaceClass::SurfaceClass(const char *filename)
	: D3DSurface(NULL), SurfaceFormat(WW3D_FORMAT_UNKNOWN)
{
	D3DSurface = DX8Wrapper::_Create_DX8_Surface(filename);
	SurfaceDescription description = {};
	Get_Description(description);
	SurfaceFormat = description.Format;
}

SurfaceClass::SurfaceClass(IDirect3DSurface8 *surface)
	: D3DSurface(surface), SurfaceFormat(WW3D_FORMAT_UNKNOWN)
{
	if (D3DSurface != NULL) {
		D3DSurface->AddRef();
	}
	SurfaceDescription description = {};
	Get_Description(description);
	SurfaceFormat = description.Format;
}

SurfaceClass::~SurfaceClass(void)
{
	if (D3DSurface != NULL) {
		D3DSurface->Release();
		D3DSurface = NULL;
	}
	SurfaceStore *store = Find_Store(this);
	if (store != NULL) {
		delete [] store->pixels;
		*store = SurfaceStore{};
	}
}

void SurfaceClass::Get_Description(SurfaceDescription &description)
{
	if (D3DSurface != NULL) {
		D3DSURFACE_DESC native_description = {};
		if (D3DSurface->GetDesc(&native_description) == D3D_OK) {
			description.Format = D3DFormat_To_WW3DFormat(native_description.Format);
			description.Width = native_description.Width;
			description.Height = native_description.Height;
			return;
		}
	}
	SurfaceStore *store = Find_Store(this);
	if (store != NULL) {
		description = store->description;
	} else {
		description.Format = SurfaceFormat;
		description.Width = 0;
		description.Height = 0;
	}
}

void *SurfaceClass::Lock(int *pitch)
{
	if (D3DSurface != NULL) {
		D3DLOCKED_RECT locked = {};
		if (D3DSurface->LockRect(&locked, NULL, 0U) == D3D_OK) {
			if (pitch != NULL) *pitch = locked.Pitch;
			return locked.pBits;
		}
	}
	SurfaceStore *store = Find_Store(this);
	if (pitch != NULL) {
		*pitch = store != NULL ? (int)(store->description.Width * Bytes_Per_Pixel(store->description.Format)) : 0;
	}
	return store != NULL ? store->pixels : NULL;
}

void SurfaceClass::Unlock(void)
{
	if (D3DSurface != NULL) {
		D3DSurface->UnlockRect();
	}
}

void SurfaceClass::Clear()
{
	SurfaceDescription description = {};
	Get_Description(description);
	int pitch = 0;
	unsigned char *pixels = static_cast<unsigned char *>(Lock(&pitch));
	if (pixels == NULL || pitch <= 0) return;
	for (unsigned y = 0U; y < description.Height; ++y) {
		memset(pixels + static_cast<size_t>(y) * pitch, 0,
			static_cast<size_t>(description.Width) * Bytes_Per_Pixel(description.Format));
	}
	Unlock();
}

void SurfaceClass::Copy(const unsigned char *other)
{
	if (other == NULL) return;
	SurfaceDescription description = {};
	Get_Description(description);
	const size_t row_bytes = static_cast<size_t>(description.Width) *
		Bytes_Per_Pixel(description.Format);
	int pitch = 0;
	unsigned char *pixels = static_cast<unsigned char *>(Lock(&pitch));
	if (pixels == NULL || pitch < static_cast<int>(row_bytes)) return;
	for (unsigned y = 0U; y < description.Height; ++y) {
		memcpy(pixels + static_cast<size_t>(y) * pitch,
			other + static_cast<size_t>(y) * row_bytes, row_bytes);
	}
	Unlock();
}

void SurfaceClass::Copy(unsigned int dstx, unsigned int dsty, unsigned int srcx,
	unsigned int srcy, unsigned int width, unsigned int height,
	const SurfaceClass *other)
{
	if (other == NULL || width == 0U || height == 0U) return;
	SurfaceDescription destination = {};
	SurfaceDescription source = {};
	Get_Description(destination);
	const_cast<SurfaceClass *>(other)->Get_Description(source);
	if (destination.Format != source.Format || dstx >= destination.Width ||
		dsty >= destination.Height || srcx >= source.Width || srcy >= source.Height) return;
	width = (width < destination.Width - dstx) ? width : destination.Width - dstx;
	width = (width < source.Width - srcx) ? width : source.Width - srcx;
	height = (height < destination.Height - dsty) ? height : destination.Height - dsty;
	height = (height < source.Height - srcy) ? height : source.Height - srcy;
	const size_t bytes_per_pixel = Bytes_Per_Pixel(destination.Format);
	int destination_pitch = 0;
	int source_pitch = 0;
	unsigned char *destination_pixels = static_cast<unsigned char *>(Lock(&destination_pitch));
	unsigned char *source_pixels = static_cast<unsigned char *>(
		const_cast<SurfaceClass *>(other)->Lock(&source_pitch));
	if (destination_pixels == NULL || source_pixels == NULL) {
		if (destination_pixels != NULL) Unlock();
		if (source_pixels != NULL) const_cast<SurfaceClass *>(other)->Unlock();
		return;
	}
	for (unsigned y = 0U; y < height; ++y) {
		memmove(destination_pixels + static_cast<size_t>(dsty + y) * destination_pitch +
			static_cast<size_t>(dstx) * bytes_per_pixel,
			source_pixels + static_cast<size_t>(srcy + y) * source_pitch +
			static_cast<size_t>(srcx) * bytes_per_pixel, static_cast<size_t>(width) * bytes_per_pixel);
	}
	const_cast<SurfaceClass *>(other)->Unlock();
	Unlock();
}

void SurfaceClass::FindBB(Vector2i *min, Vector2i *max)
{
	if (min == NULL || max == NULL) return;
	SurfaceDescription description = {};
	Get_Description(description);
	const int left = min->I < 0 ? 0 : min->I;
	const int top = min->J < 0 ? 0 : min->J;
	const int right = max->I > static_cast<int>(description.Width) ?
		static_cast<int>(description.Width) : max->I;
	const int bottom = max->J > static_cast<int>(description.Height) ?
		static_cast<int>(description.Height) : max->J;
	Vector2i actual_min(right, bottom);
	Vector2i actual_max(left, top);
	const unsigned bytes_per_pixel = Bytes_Per_Pixel(description.Format);
	int pitch = 0;
	const unsigned char *pixels = static_cast<const unsigned char *>(Lock(&pitch));
	if (pixels == NULL || pitch <= 0) return;
	for (int y = top; y < bottom; ++y) {
		for (int x = left; x < right; ++x) {
			const unsigned char *pixel = pixels + static_cast<size_t>(y) * pitch +
				static_cast<size_t>(x) * bytes_per_pixel;
			bool opaque = false;
			switch (description.Format) {
			case WW3D_FORMAT_A8R8G8B8: opaque = pixel[3] != 0U; break;
			case WW3D_FORMAT_A4R4G4B4: opaque = (pixel[1] & 0xf0U) != 0U; break;
			case WW3D_FORMAT_A1R5G5B5: opaque = (pixel[1] & 0x80U) != 0U; break;
			case WW3D_FORMAT_A8: opaque = pixel[0] != 0U; break;
			default: opaque = true; break;
			}
			if (opaque) {
				if (x < actual_min.I) actual_min.I = x;
				if (y < actual_min.J) actual_min.J = y;
				if (x > actual_max.I) actual_max.I = x;
				if (y > actual_max.J) actual_max.J = y;
			}
		}
	}
	Unlock();
	*min = actual_min;
	*max = actual_max;
}

bool SurfaceClass::Is_Transparent_Column(unsigned int column)
{
	SurfaceDescription description = {};
	Get_Description(description);
	if (column >= description.Width) return true;
	Vector2i min(static_cast<int>(column), 0);
	Vector2i max(static_cast<int>(column + 1U), static_cast<int>(description.Height));
	FindBB(&min, &max);
	return min.I > max.I || min.J > max.J;
}
