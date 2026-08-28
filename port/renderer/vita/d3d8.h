#pragma once

// Compile-time data contract for the legacy WW3D DX8 boundary. This is not a
// Direct3D implementation: the Vita backend implements WW3D's wrapper classes
// and translates their state into the selected native graphics API.

#include "win32_compat.h"

#include <stdint.h>

#ifndef CONST
#define CONST const
#endif

typedef int32_t HRESULT;
typedef uint32_t D3DCOLOR;
typedef uint32_t D3DFORMAT;

/* Direct3D 8 defines the sentinel format as zero.  Original ww3d2's
 * format-conversion and presentation paths use it before selecting a real
 * colour/depth format. */
static const D3DFORMAT D3DFMT_UNKNOWN = 0;
typedef uint32_t D3DPOOL;
typedef uint32_t D3DPRIMITIVETYPE;
typedef uint32_t D3DRENDERSTATETYPE;
typedef uint32_t D3DTEXTURESTAGESTATETYPE;
typedef uint32_t D3DTRANSFORMSTATETYPE;
typedef uint32_t D3DBLEND;
typedef uint32_t D3DCMPFUNC;
typedef uint32_t D3DTEXTUREOP;

struct POINT { LONG x, y; };
typedef void *HWND;

struct D3DCOLORVALUE { float r, g, b, a; };
struct D3DVECTOR { float x, y, z; };
struct D3DMATRIX { float m[4][4]; };
struct D3DLIGHT8 {
	uint32_t Type;
	D3DCOLORVALUE Diffuse;
	D3DCOLORVALUE Specular;
	D3DCOLORVALUE Ambient;
	D3DVECTOR Position;
	D3DVECTOR Direction;
	float Range;
	float Falloff;
	float Attenuation0;
	float Attenuation1;
	float Attenuation2;
	float Theta;
	float Phi;
};
struct _D3DMATERIAL8 {
	D3DCOLORVALUE Diffuse;
	D3DCOLORVALUE Ambient;
	D3DCOLORVALUE Specular;
	D3DCOLORVALUE Emissive;
	float Power;
};
typedef struct _D3DMATERIAL8 D3DMATERIAL8;
struct D3DVIEWPORT8 { uint32_t X, Y, Width, Height; float MinZ, MaxZ; };
struct D3DLOCKED_RECT { int Pitch; void *pBits; };
struct D3DSURFACE_DESC {
	D3DFORMAT Format;
	uint32_t Type;
	DWORD Usage;
	uint32_t Pool;
	UINT Size;
	uint32_t MultiSampleType;
	UINT Width;
	UINT Height;
};
struct D3DADAPTER_IDENTIFIER8 { char Driver[512]; char Description[512]; };

// The original engine stores this structure by value even though the Vita
// backend never exposes a Direct3D device. Preserve the DX8 scalar layout so
// the surrounding WW3D classes retain their original data contract.
struct D3DCAPS8 {
	uint32_t DeviceType;
	UINT AdapterOrdinal;
	DWORD Caps, Caps2, Caps3, PresentationIntervals;
	DWORD CursorCaps, DevCaps;
	DWORD PrimitiveMiscCaps, RasterCaps, ZCmpCaps;
	DWORD SrcBlendCaps, DestBlendCaps, AlphaCmpCaps, ShadeCaps;
	DWORD TextureCaps, TextureFilterCaps, CubeTextureFilterCaps;
	DWORD VolumeTextureFilterCaps, TextureAddressCaps, VolumeTextureAddressCaps;
	DWORD LineCaps;
	DWORD MaxTextureWidth, MaxTextureHeight, MaxVolumeExtent;
	DWORD MaxTextureRepeat, MaxTextureAspectRatio, MaxAnisotropy;
	float MaxVertexW;
	float GuardBandLeft, GuardBandTop, GuardBandRight, GuardBandBottom;
	float ExtentsAdjust;
	DWORD StencilCaps, FVFCaps, TextureOpCaps;
	DWORD MaxTextureBlendStages, MaxSimultaneousTextures;
	DWORD VertexProcessingCaps, MaxActiveLights, MaxUserClipPlanes;
	DWORD MaxVertexBlendMatrices, MaxVertexBlendMatrixIndex;
	float MaxPointSize;
	DWORD MaxPrimitiveCount, MaxVertexIndex, MaxStreams, MaxStreamStride;
	DWORD VertexShaderVersion, MaxVertexShaderConst, PixelShaderVersion;
	float MaxPixelShaderValue;
};

struct IDirect3DSurface8 {
	IDirect3DSurface8(UINT width, UINT height, D3DFORMAT format,
		UINT bytes_per_pixel);
	~IDirect3DSurface8();
	ULONG AddRef();
	ULONG Release();
	HRESULT GetDesc(D3DSURFACE_DESC *description);
	HRESULT LockRect(D3DLOCKED_RECT *locked, const RECT *rectangle, DWORD flags);
	HRESULT UnlockRect();

	const unsigned char *Get_Data() const { return Storage; }
	unsigned char *Get_Data() { return Storage; }
	UINT Get_Pitch() const { return Pitch; }

private:
	unsigned char *Storage;
	UINT StorageSize;
	UINT Width;
	UINT Height;
	UINT Pitch;
	D3DFORMAT Format;
	ULONG ReferenceCount;
};
struct IDirect3DSwapChain8;

// Original WW3D owns vertex/index buffers through these DX8-shaped opaque
// handles.  On Vita they are CPU backing stores beneath the original
// VertexBufferClass/IndexBufferClass abstractions; no Direct3D runtime is
// implemented or linked.  The renderer consumes the bytes only when the
// original DX8Wrapper draw boundary is reached.
#if defined(RENEGADE_VITA_PORT)
struct IDirect3DVertexBuffer8 {
	explicit IDirect3DVertexBuffer8(UINT size);
	~IDirect3DVertexBuffer8();
	ULONG AddRef();
	ULONG Release();
	HRESULT Lock(UINT offset, UINT size, unsigned char **data, DWORD flags);
	HRESULT Unlock();
	const unsigned char *Get_Data() const { return Storage; }
	UINT Get_Size() const { return StorageSize; }

private:
	unsigned char *Storage;
	UINT StorageSize;
	ULONG ReferenceCount;
};

struct IDirect3DIndexBuffer8 {
	explicit IDirect3DIndexBuffer8(UINT size);
	~IDirect3DIndexBuffer8();
	ULONG AddRef();
	ULONG Release();
	HRESULT Lock(UINT offset, UINT size, unsigned char **data, DWORD flags);
	HRESULT Unlock();
	const unsigned char *Get_Data() const { return Storage; }
	UINT Get_Size() const { return StorageSize; }

private:
	unsigned char *Storage;
	UINT StorageSize;
	ULONG ReferenceCount;
};
#else
struct IDirect3DVertexBuffer8;
struct IDirect3DIndexBuffer8;
#endif

struct IDirect3D8;
struct IDirect3DBaseTexture8 {
	// Native Vita texture metadata retained beneath the original DX8-shaped
	// ownership contract.  Source pixels remain in the original archive; this
	// is only the process-local uploaded representation.
	uint32_t NativeTexture;
	uint32_t Width;
	uint32_t Height;
	uint32_t MipLevels;
	uint32_t SourceFormat;
	uint32_t PixelChecksum;
	uint64_t ResidentBytes;
	ULONG ReferenceCount;
	IDirect3DSurface8 **SurfaceLevels;
	DWORD *SurfaceLockFlags;
	DWORD Priority;
	UINT LockedSurfaceCount;
	bool HasAlpha;
	bool Uploaded;
	bool *SurfaceLocked;
	bool TextureLocked;
	// A shared, intentionally conspicuous diagnostic texture.  This remains
	// distinct from a successfully decoded retail texture in both ownership
	// and telemetry; callers must not infer asset success from Uploaded alone.
	bool DiagnosticFallback;
	ULONG AddRef();
	ULONG Release();
};
struct IDirect3DTexture8 : IDirect3DBaseTexture8 {
	HRESULT GetLevelDesc(UINT level, D3DSURFACE_DESC *description);
	UINT GetLevelCount();
	HRESULT GetSurfaceLevel(UINT level, IDirect3DSurface8 **surface);
	HRESULT LockRect(UINT level, D3DLOCKED_RECT *locked, const RECT *rectangle,
		DWORD flags);
	HRESULT UnlockRect(UINT level);
	DWORD GetPriority();
	DWORD SetPriority(DWORD priority);
};
struct IDirect3DDevice8 {
	HRESULT SetTransform(D3DTRANSFORMSTATETYPE state, const D3DMATRIX *matrix);
	HRESULT GetTransform(D3DTRANSFORMSTATETYPE state, D3DMATRIX *matrix);
	HRESULT SetViewport(const D3DVIEWPORT8 *viewport);
	HRESULT GetViewport(D3DVIEWPORT8 *viewport);
	HRESULT SetMaterial(const D3DMATERIAL8 *material);
	HRESULT SetLight(DWORD index, const D3DLIGHT8 *light);
	HRESULT LightEnable(DWORD index, BOOL enable);
	HRESULT SetRenderState(D3DRENDERSTATETYPE state, DWORD value);
	HRESULT SetTextureStageState(DWORD stage, D3DTEXTURESTAGESTATETYPE state,
		DWORD value);
	HRESULT SetTexture(DWORD stage, IDirect3DBaseTexture8 *texture);
	HRESULT CopyRects(IDirect3DSurface8 *source, const RECT *source_rects,
		UINT count, IDirect3DSurface8 *destination, const POINT *destination_points);
};

enum : uint32_t {
	D3D_OK = 0,
	D3DERR_INVALIDCALL = 0x8876086cU,
	D3DPOOL_DEFAULT = 0,
	D3DPOOL_MANAGED = 1,
	D3DPOOL_SYSTEMMEM = 2,
	D3DTS_VIEW = 2,
	D3DTS_PROJECTION = 3,
	D3DTS_WORLD = 256,
	D3DTS_TEXTURE0 = 16,
	D3DRS_ZBIAS = 47,
	D3DRS_AMBIENT = 26,
	D3DRS_FOGENABLE = 28,
	D3DRS_FOGCOLOR = 34,
	D3DRS_FOGSTART = 36,
	D3DRS_FOGEND = 37,
	D3DRS_FILLMODE = 8,
	D3DRS_ZWRITEENABLE = 14,
	D3DRS_ALPHATESTENABLE = 15,
	D3DRS_SRCBLEND = 19,
	D3DRS_DESTBLEND = 20,
	D3DRS_CULLMODE = 22,
	D3DRS_ZFUNC = 23,
	D3DRS_ALPHAREF = 24,
	D3DRS_ALPHAFUNC = 25,
	D3DRS_ALPHABLENDENABLE = 27,
	D3DRS_SPECULARENABLE = 29,
	D3DRS_LIGHTING = 137,
	D3DRS_DIFFUSEMATERIALSOURCE = 145,
	D3DRS_AMBIENTMATERIALSOURCE = 147,
	D3DRS_EMISSIVEMATERIALSOURCE = 148,
	D3DRS_PATCHSEGMENTS = 164,
	D3DTSS_COLOROP = 1,
	D3DTSS_COLORARG1 = 2,
	D3DTSS_COLORARG2 = 3,
	D3DTSS_ALPHAOP = 4,
	D3DTSS_ALPHAARG1 = 5,
	D3DTSS_ALPHAARG2 = 6,
	D3DTSS_BUMPENVMAT00 = 7,
	D3DTSS_BUMPENVMAT01 = 8,
	D3DTSS_BUMPENVMAT10 = 9,
	D3DTSS_BUMPENVMAT11 = 10,
	D3DTSS_TEXCOORDINDEX = 11,
	D3DTSS_ADDRESSU = 13,
	D3DTSS_ADDRESSV = 14,
	D3DTSS_MAGFILTER = 16,
	D3DTSS_MINFILTER = 17,
	D3DTSS_MIPFILTER = 18,
	D3DTSS_MAXANISOTROPY = 21,
	D3DTSS_TEXTURETRANSFORMFLAGS = 24,
	D3DTOP_DISABLE = 1,
	D3DTOP_SELECTARG1 = 2,
	D3DTOP_SELECTARG2 = 3,
	D3DTOP_MODULATE = 4,
	D3DTOP_ADD = 7,
	D3DTOP_SUBTRACT = 10,
	D3DTOP_ADDSMOOTH = 11,
	D3DTOP_BLENDTEXTUREALPHA = 13,
	D3DTOP_BLENDCURRENTALPHA = 16,
	D3DTOP_BUMPENVMAP = 22,
	D3DTOP_BUMPENVMAPLUMINANCE = 23,
	D3DTOP_DOTPRODUCT3 = 24,
	D3DBLEND_ZERO = 1,
	D3DBLEND_ONE = 2,
	D3DBLEND_SRCCOLOR = 3,
	D3DBLEND_INVSRCCOLOR = 4,
	D3DBLEND_SRCALPHA = 5,
	D3DBLEND_INVSRCALPHA = 6,
	D3DCMP_LESSEQUAL = 4,
	D3DCMP_GREATEREQUAL = 7,
	D3DMCS_MATERIAL = 0,
	D3DMCS_COLOR1 = 1,
	D3DMCS_COLOR2 = 2,
	D3DFILL_WIREFRAME = 2,
	D3DFILL_POINT = 1,
	D3DFILL_SOLID = 3,
	D3DTTFF_DISABLE = 0,
	D3DTTFF_COUNT1 = 1,
	D3DTTFF_COUNT2 = 2,
	D3DTTFF_COUNT3 = 3,
	D3DTTFF_COUNT4 = 4,
	D3DTTFF_PROJECTED = 256,
	D3DZB_FALSE = 0,
	D3DZB_TRUE = 1,
	D3DZB_USEW = 2,
	D3DSHADE_FLAT = 1,
	D3DSHADE_GOURAUD = 2,
	D3DSHADE_PHONG = 3,
	D3DBLEND_DESTALPHA = 7,
	D3DBLEND_INVDESTALPHA = 8,
	D3DBLEND_DESTCOLOR = 9,
	D3DBLEND_INVDESTCOLOR = 10,
	D3DBLEND_SRCALPHASAT = 11,
	D3DBLEND_BOTHSRCALPHA = 12,
	D3DBLEND_BOTHINVSRCALPHA = 13,
	D3DCMP_NEVER = 1,
	D3DCMP_LESS = 2,
	D3DCMP_EQUAL = 3,
	D3DCMP_GREATER = 5,
	D3DCMP_NOTEQUAL = 6,
	D3DCMP_ALWAYS = 8,
	D3DFOG_NONE = 0,
	D3DFOG_EXP = 1,
	D3DFOG_EXP2 = 2,
	D3DFOG_LINEAR = 3,
	D3DSTENCILOP_KEEP = 1,
	D3DSTENCILOP_ZERO = 2,
	D3DSTENCILOP_REPLACE = 3,
	D3DSTENCILOP_INCRSAT = 4,
	D3DSTENCILOP_DECRSAT = 5,
	D3DSTENCILOP_INVERT = 6,
	D3DSTENCILOP_INCR = 7,
	D3DSTENCILOP_DECR = 8,
	D3DVBF_DISABLE = 0,
	D3DVBF_1WEIGHTS = 1,
	D3DVBF_2WEIGHTS = 2,
	D3DVBF_3WEIGHTS = 3,
	D3DVBF_TWEENING = 255,
	D3DVBF_0WEIGHTS = 256,
	D3DPATCHEDGE_DISCRETE = 0,
	D3DPATCHEDGE_CONTINUOUS = 1,
	D3DDMT_ENABLE = 0,
	D3DDMT_DISABLE = 1,
	D3DBLENDOP_ADD = 1,
	D3DBLENDOP_SUBTRACT = 2,
	D3DBLENDOP_REVSUBTRACT = 3,
	D3DBLENDOP_MIN = 4,
	D3DBLENDOP_MAX = 5,
	D3DTADDRESS_WRAP = 1,
	D3DTADDRESS_CLAMP = 3,
	D3DTEXF_NONE = 0,
	D3DTEXF_POINT = 1,
	D3DTEXF_LINEAR = 2,
	D3DTEXF_ANISOTROPIC = 3,
	D3DCULL_NONE = 1,
	D3DCULL_CW = 2,
	D3DCULL_CCW = 3,
	D3DFMT_R8G8B8 = 20,
	D3DFMT_A8R8G8B8 = 21,
	D3DFMT_X8R8G8B8 = 22,
	D3DFMT_R5G6B5 = 23,
	D3DFMT_X1R5G5B5 = 24,
	D3DFMT_A1R5G5B5 = 25,
	D3DFMT_A4R4G4B4 = 26,
	D3DFMT_R3G3B2 = 27,
	D3DFMT_A8 = 28,
	D3DFMT_A8R3G3B2 = 29,
	D3DFMT_X4R4G4B4 = 30,
	D3DFMT_A8P8 = 40,
	D3DFMT_P8 = 41,
	D3DFMT_L8 = 50,
	D3DFMT_A8L8 = 51,
	D3DFMT_A4L4 = 52,
	D3DFMT_V8U8 = 60,
	D3DFMT_L6V5U5 = 61,
	D3DFMT_X8L8V8U8 = 62,
	D3DFMT_Q8W8V8U8 = 63,
	D3DFMT_V16U16 = 64,
	D3DFMT_W11V11U10 = 65,
	D3DFMT_UYVY = 0x59565955U,
	D3DFMT_YUY2 = 0x32595559U,
	D3DFMT_DXT1 = 0x31545844U,
	D3DFMT_DXT2 = 0x32545844U,
	D3DFMT_DXT3 = 0x33545844U,
	D3DFMT_DXT4 = 0x34545844U,
	D3DFMT_DXT5 = 0x35545844U,
	D3DFMT_D16_LOCKABLE = 70,
	D3DFMT_D32 = 71,
	D3DFMT_D15S1 = 73,
	D3DFMT_D24S8 = 75,
	D3DFMT_D16 = 80,
	D3DFMT_D24X8 = 77,
	D3DFMT_D24X4S4 = 79,
	D3DLOCK_READONLY = 0x0010,
	D3DLOCK_NOSYSLOCK = 0x0800,
	D3DLOCK_NOOVERWRITE = 0x1000,
	D3DLOCK_DISCARD = 0x2000,
};

#define D3DTA_DIFFUSE 0x00000000U
#define D3DTA_CURRENT 0x00000001U
#define D3DTA_TEXTURE 0x00000002U
#define D3DTSS_TCI_PASSTHRU 0x00000U
#define D3DTSS_TCI_CAMERASPACENORMAL 0x10000U
#define D3DTSS_TCI_CAMERASPACEPOSITION 0x20000U
#define D3DTSS_TCI_CAMERASPACEREFLECTIONVECTOR 0x30000U
#define D3DTEXOPCAPS_SELECTARG1 0x0000002U
#define D3DTEXOPCAPS_MODULATE 0x0000008U
#define D3DTEXOPCAPS_ADD 0x0000040U
#define D3DTEXOPCAPS_SUBTRACT 0x0000200U
#define D3DTEXOPCAPS_ADDSMOOTH 0x0000400U
#define D3DTEXOPCAPS_BLENDTEXTUREALPHA 0x0001000U
#define D3DTEXOPCAPS_BLENDCURRENTALPHA 0x0008000U
#define D3DTEXOPCAPS_BUMPENVMAP 0x0200000U
#define D3DTEXOPCAPS_BUMPENVMAPLUMINANCE 0x0400000U
#define D3DTEXOPCAPS_DOTPRODUCT3 0x0800000U
#define D3DPTFILTERCAPS_MINFLINEAR 0x00000200U
#define D3DPTFILTERCAPS_MINFANISOTROPIC 0x00000400U
#define D3DPTFILTERCAPS_MIPFLINEAR 0x00020000U
#define D3DPTFILTERCAPS_MAGFLINEAR 0x02000000U
#define D3DPTFILTERCAPS_MAGFANISOTROPIC 0x04000000U

#define D3DDP_MAXTEXCOORD 8
#define D3DFVF_XYZ 0x0002U
#define D3DFVF_XYZRHW 0x0004U
#define D3DFVF_XYZB1 0x0006U
#define D3DFVF_XYZB2 0x0008U
#define D3DFVF_XYZB3 0x000aU
#define D3DFVF_XYZB4 0x000cU
#define D3DFVF_XYZB5 0x000eU
#define D3DFVF_NORMAL 0x0010U
#define D3DFVF_PSIZE 0x0020U
#define D3DFVF_DIFFUSE 0x0040U
#define D3DFVF_SPECULAR 0x0080U
#define D3DFVF_TEX0 0x0000U
#define D3DFVF_TEX1 0x0100U
#define D3DFVF_TEX2 0x0200U
#define D3DFVF_TEX3 0x0300U
#define D3DFVF_TEX4 0x0400U
#define D3DFVF_TEX5 0x0500U
#define D3DFVF_TEX6 0x0600U
#define D3DFVF_TEX7 0x0700U
#define D3DFVF_TEX8 0x0800U
#define D3DFVF_LASTBETA_UBYTE4 0x1000U
#define D3DFVF_TEXTUREFORMAT1 3U
#define D3DFVF_TEXTUREFORMAT2 0U
#define D3DFVF_TEXTUREFORMAT3 1U
#define D3DFVF_TEXTUREFORMAT4 2U
#define D3DFVF_TEXCOORDSIZE1(index) (D3DFVF_TEXTUREFORMAT1 << ((index) * 2U + 16U))
#define D3DFVF_TEXCOORDSIZE2(index) D3DFVF_TEXTUREFORMAT2
#define D3DFVF_TEXCOORDSIZE3(index) (D3DFVF_TEXTUREFORMAT3 << ((index) * 2U + 16U))
#define D3DFVF_TEXCOORDSIZE4(index) (D3DFVF_TEXTUREFORMAT4 << ((index) * 2U + 16U))

#define D3DCOLOR_ARGB(a, r, g, b) \
	((D3DCOLOR)((((uint32_t)(a) & 0xffU) << 24) | \
	(((uint32_t)(r) & 0xffU) << 16) | (((uint32_t)(g) & 0xffU) << 8) | \
	((uint32_t)(b) & 0xffU)))
#define D3DCOLOR_RGBA(r, g, b, a) D3DCOLOR_ARGB(a, r, g, b)
#define D3DCOLOR_COLORVALUE(r, g, b, a) \
	D3DCOLOR_RGBA((uint32_t)((r) * 255.0f), (uint32_t)((g) * 255.0f), \
		(uint32_t)((b) * 255.0f), (uint32_t)((a) * 255.0f))
