#pragma once

// D3DX is not present on Vita. Original WW3D files include this header at the
// DX8 implementation boundary; the Vita backend supplies the required
// platform operations rather than linking D3DX.

#include "d3d8.h"

// D3DXGetFVFVertexSize is a format-description helper, not a GPU operation.
// Keep the original WW3D FVFInfoClass intact and provide the byte-count
// calculation at the D3DX compatibility boundary.
static inline UINT D3DXGetFVFVertexSize(DWORD fvf)
{
	UINT size = 0;
	switch (fvf & 0x400eU) { // D3DFVF_POSITION_MASK
	case D3DFVF_XYZ:    size = 3U * sizeof(float); break;
	case D3DFVF_XYZRHW: size = 4U * sizeof(float); break;
	case D3DFVF_XYZB1:  size = 4U * sizeof(float); break;
	case D3DFVF_XYZB2:  size = 5U * sizeof(float); break;
	case D3DFVF_XYZB3:  size = 6U * sizeof(float); break;
	case D3DFVF_XYZB4:  size = 7U * sizeof(float); break;
	case D3DFVF_XYZB5:  size = 8U * sizeof(float); break;
	case 0x4002U:       size = 4U * sizeof(float); break; // D3DFVF_XYZW
	default: break;
	}

	if ((fvf & D3DFVF_NORMAL) != 0U) size += 3U * sizeof(float);
	if ((fvf & D3DFVF_PSIZE) != 0U) size += sizeof(float);
	if ((fvf & D3DFVF_DIFFUSE) != 0U) size += sizeof(DWORD);
	if ((fvf & D3DFVF_SPECULAR) != 0U) size += sizeof(DWORD);

	const UINT texture_count = (fvf >> 8U) & 0x0fU;
	for (UINT stage = 0; stage < texture_count; ++stage) {
		const UINT format = (fvf >> (16U + 2U * stage)) & 0x03U;
		const UINT component_count = format == D3DFVF_TEXTUREFORMAT1 ? 1U :
			(format == D3DFVF_TEXTUREFORMAT3 ? 3U :
			(format == D3DFVF_TEXTUREFORMAT4 ? 4U : 2U));
		size += component_count * sizeof(float);
	}
	return size;
}
