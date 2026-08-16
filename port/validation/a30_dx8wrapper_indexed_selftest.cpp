#include "dx8indexbuffer.h"
#include "dx8vertexbuffer.h"
#include "dx8wrapper.h"
#include "ww3d_vita_renderer.h"

#include <stdio.h>
#include <string.h>

namespace {

bool Check(bool condition, const char *label, unsigned &checks)
{
	++checks;
	printf("%s: %s\n", label, condition ? "PASS" : "FAIL");
	return condition;
}

} // namespace

int main()
{
	unsigned checks = 0;
	unsigned failures = 0;
	RenegadeVitaRenderer::Initialize();
	RenegadeVitaRenderer::Reset_Statistics();

	DX8VertexBufferClass *vertex_buffer = new DX8VertexBufferClass(
		DX8_FVF_XYZNDUV1, 8);
	DX8IndexBufferClass *index_buffer = new DX8IndexBufferClass(6);
	failures += !Check(vertex_buffer->FVF_Info().Get_FVF_Size() == 36,
		"original FVFInfoClass stride", checks);
	failures += !Check(vertex_buffer->Engine_Refs() == 0 &&
		index_buffer->Engine_Refs() == 0, "initial engine references", checks);

	unsigned char *vertex_bytes = NULL;
	HRESULT result = vertex_buffer->Get_DX8_Vertex_Buffer()->Lock(
		0, 0, &vertex_bytes, 0);
	failures += !Check(result == D3D_OK && vertex_bytes != NULL,
		"CPU vertex handle lock", checks);
	for (unsigned index = 0; index < 8; ++index) {
		VertexFormatXYZNDUV1 vertex = {};
		vertex.x = static_cast<float>(index);
		vertex.y = static_cast<float>(index * 2U);
		vertex.z = -static_cast<float>(index + 1U);
		vertex.nz = 1.0f;
		vertex.diffuse = 0xff000000U | (index * 0x00010101U);
		vertex.u1 = static_cast<float>(index) / 8.0f;
		vertex.v1 = 1.0f - vertex.u1;
		memcpy(vertex_bytes + index * sizeof(vertex), &vertex, sizeof(vertex));
	}
	vertex_buffer->Get_DX8_Vertex_Buffer()->Unlock();

	unsigned char *index_bytes = NULL;
	result = index_buffer->Get_DX8_Index_Buffer()->Lock(
		0, 0, &index_bytes, 0);
	const uint16_t indices[] = { 7, 7, 7, 1, 2, 3 };
	if (result == D3D_OK && index_bytes != NULL) {
		memcpy(index_bytes, indices, sizeof(indices));
	}
	index_buffer->Get_DX8_Index_Buffer()->Unlock();
	failures += !Check(result == D3D_OK && index_bytes != NULL,
		"CPU index handle lock", checks);

	DX8Wrapper::Set_Vertex_Buffer(vertex_buffer);
	DX8Wrapper::Set_Index_Buffer(index_buffer, 2);
	// The real path receives these from RenderObj/Camera before drawing.  Keep
	// the original-object boundary test equally explicit so an uninitialized
	// platform transform cannot masquerade as a valid indexed submission.
	const Matrix4 identity_transform(true);
	DX8Wrapper::Set_Transform(D3DTS_WORLD, identity_transform);
	DX8Wrapper::Set_Transform(D3DTS_VIEW, identity_transform);
	DX8Wrapper::Set_Transform(D3DTS_PROJECTION, identity_transform);
	failures += !Check(vertex_buffer->Engine_Refs() == 1 &&
		index_buffer->Engine_Refs() == 1, "bound engine references", checks);

	// The terrain path currently supplies DYNAMIC_DX8 as its submission hint
	// while the actual retained buffer objects are ordinary DX8 buffers.
	DX8Wrapper::Draw_Triangles(BUFFER_TYPE_DYNAMIC_DX8, 3, 1, 1, 3);
	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	failures += !Check(statistics.indexed_submissions == 1 &&
		statistics.indexed_vertex_references == 3 &&
		statistics.indexed_triangle_submissions == 1,
		"original DX8Wrapper indexed draw", checks);
	failures += !Check(statistics.indexed_geometry_checksum == 0x65e5f668U,
		"original boundary semantic fingerprint", checks);

	DX8Wrapper::Set_Vertex_Buffer(NULL);
	DX8Wrapper::Set_Index_Buffer(NULL, 0);
	failures += !Check(vertex_buffer->Engine_Refs() == 0 &&
		index_buffer->Engine_Refs() == 0, "released engine references", checks);
	vertex_buffer->Release_Ref();
	index_buffer->Release_Ref();
	RenegadeVitaRenderer::Shutdown();

	printf("A3 original DX8Wrapper indexed boundary: %u checks, %u failures\n",
		checks, failures);
	return failures == 0 ? 0 : 1;
}
