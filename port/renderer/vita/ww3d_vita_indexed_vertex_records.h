#ifndef WW3D_VITA_INDEXED_VERTEX_RECORDS_H
#define WW3D_VITA_INDEXED_VERTEX_RECORDS_H

#include <cstdint>

// 0 keeps every batched indexed vertex on the per-vertex vitaGL calls.
#ifndef RENEGADE_VITA_INDEXED_VERTEX_RECORDS
#define RENEGADE_VITA_INDEXED_VERTEX_RECORDS 1
#endif

// Packed immediate vertices for the DX8 indexed boundary (dynamic VB/IB,
// sorted runs, Render2D/HUD/text, particles, decals and line strips).
//
// Each unique vertex of a non-projective indexed batch used to cost
// glColor4ub/glColor4f, glNormal3f, two glMultiTexCoord2f and glVertex3f. A
// record holds exactly the stream values glVertex3f would copy from vitaGL's
// current vertex for an unlit primitive: position, both texture coordinates
// and RGBA, which is vitaGL's unlit multitexture layout. The normal is not part
// of that stream. vglRenegadeImmediateVertices appends a run of records to the
// same immediate pool glVertex3f fills, selecting the enabled units' fields as
// glVertex3f does, and leaves vitaGL's current attributes untouched; the
// caller replays the last corner's attribute calls before ending the batch.
namespace RenegadeVitaRenderer {

struct IndexedVertexRecord {
	float position[3];
	float uv0[2];
	float uv1[2];
	float color[4];
};
static_assert(sizeof(IndexedVertexRecord) == 11U * sizeof(float),
	"vitaGL reads records as 11 packed floats");

// Records accumulate in fixed scratch and are appended this many vertices at a
// time; a batch keeps the original first-reference vertex order.
enum { INDEXED_VERTEX_RECORD_CHUNK = 128 };

// vitaGL's glColor4ub stores (float)component / 255.0f. The table holds those
// exact IEEE quotients (all normal or zero, so flush-to-zero cannot apply).
struct UnitByteColorTable {
	float value[256];
	constexpr UnitByteColorTable() : value()
	{
		for (unsigned component = 0U; component < 256U; ++component)
			value[component] = static_cast<float>(component) / 255.0f;
	}
};
constexpr UnitByteColorTable UNIT_BYTE_COLOR = UnitByteColorTable();

// D3DCOLOR is ARGB in a 32-bit word; the boundary emits R, G, B, A.
inline void Decode_Indexed_Record_Color(uint32_t diffuse, float color[4])
{
	color[0] = UNIT_BYTE_COLOR.value[(diffuse >> 16U) & 0xffU];
	color[1] = UNIT_BYTE_COLOR.value[(diffuse >> 8U) & 0xffU];
	color[2] = UNIT_BYTE_COLOR.value[diffuse & 0xffU];
	color[3] = UNIT_BYTE_COLOR.value[(diffuse >> 24U) & 0xffU];
}

} // namespace RenegadeVitaRenderer

#endif
