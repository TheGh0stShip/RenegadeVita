#pragma once

#include "dx8wrapper.h"
#include "dx8vertexbuffer.h"
#include "dx8indexbuffer.h"
#include "sortingrenderer.h"
#include "ww3d_vita_renderer.h"
#include <cstring>
#include <cstdio>
#include <limits>

static bool sorting_order_valid;
static unsigned sorting_observed_triangles;
static float sorting_last_depth;
static float sorting_min_depth;
static float sorting_max_depth;

static void Observe_Sorted_Submission(const RenegadeVitaRenderer::IndexedTriangleSubmission &submission)
{
	RenegadeVitaRenderer::IndexedTransformMatrices matrices;
	if (!RenegadeVitaRenderer::Build_Indexed_Transform_Matrices(submission.world_transform,
		submission.view_transform, submission.projection_transform, matrices)) {
		sorting_order_valid = false;
		return;
	}
	for (unsigned triangle=0; triangle<submission.triangle_count; ++triangle) {
		float depth = 0.0f;
		for (unsigned corner=0; corner<3; ++corner) {
			const unsigned index = submission.base_vertex_index +
				submission.index_data[submission.first_index + triangle*3 + corner];
			float position[3];
			std::memcpy(position, submission.vertex_data + index*submission.vertex_stride, sizeof(position));
			depth += matrices.modelview[2]*position[0] + matrices.modelview[6]*position[1] +
				matrices.modelview[10]*position[2] + matrices.modelview[14];
		}
		depth /= 3.0f;
		if (depth < sorting_last_depth) sorting_order_valid = false;
		if (depth < sorting_min_depth) sorting_min_depth = depth;
		if (depth > sorting_max_depth) sorting_max_depth = depth;
		sorting_last_depth = depth;
		++sorting_observed_triangles;
	}
}

static bool Check_Original_Sorting_Capacity(unsigned nodes, unsigned vertex_count,
	unsigned triangles, bool interleaved = false)
{
	const RenegadeVitaRenderer::Statistics before = RenegadeVitaRenderer::Get_Statistics();
	SortingVertexBufferClass *vertices = new SortingVertexBufferClass(vertex_count);
	SortingIndexBufferClass *indices = new SortingIndexBufferClass(triangles * 3);
	{
		VertexBufferClass::WriteLockClass lock(vertices);
		VertexFormatXYZNDUV2 *v = static_cast<VertexFormatXYZNDUV2 *>(lock.Get_Vertex_Array());
		std::memset(v, 0, sizeof(*v) * vertex_count);
		for (unsigned i = 0; i < vertex_count; ++i) {
			v[i].x = static_cast<float>(i % 3);
			v[i].y = i % 3 == 1 ? 1.0f : 0.0f;
			v[i].z = interleaved && i >= 3 && i < 6 ? -25.0f : -5.0f;
			v[i].nz = 1.0f;
			v[i].diffuse = 0xffffffffU;
		}
	}
	{
		IndexBufferClass::WriteLockClass lock(indices);
		for (unsigned i = 0; i < triangles * 3; ++i)
			lock.Get_Index_Array()[i] = i % (interleaved ? 6 : 3);
	}
	DX8Wrapper::Set_Transform(D3DTS_WORLD, Matrix4(true));
	Matrix4 view(true);
	view[2][2] = 2.0f;
	view[2][3] = 1.0f;
	DX8Wrapper::Set_Transform(D3DTS_VIEW, view);
	DX8Wrapper::Set_Transform(D3DTS_PROJECTION, Matrix4(true));
	DX8Wrapper::Set_Vertex_Buffer(vertices);
	DX8Wrapper::Set_Index_Buffer(indices, 0);
	for (unsigned i = 0; i < nodes; ++i) {
		Matrix4 world(true);
		world[2][3] = -static_cast<float>(i % 17);
		DX8Wrapper::Set_Transform(D3DTS_WORLD, world);
		DX8Wrapper::Draw_Triangles(BUFFER_TYPE_SORTING, 0, triangles, 0, vertex_count);
	}
	DX8Wrapper::Set_Vertex_Buffer(NULL);
	DX8Wrapper::Set_Index_Buffer(NULL, 0);
	sorting_order_valid = true;
	sorting_observed_triangles = 0;
	sorting_last_depth = -std::numeric_limits<float>::infinity();
	sorting_min_depth = std::numeric_limits<float>::infinity();
	sorting_max_depth = -std::numeric_limits<float>::infinity();
	RenegadeVitaRenderer::Set_Host_Indexed_Submission_Observer(Observe_Sorted_Submission);
	SortingRendererClass::Flush();
	RenegadeVitaRenderer::Set_Host_Indexed_Submission_Observer(NULL);
	const RenegadeVitaRenderer::Statistics after = RenegadeVitaRenderer::Get_Statistics();
	const unsigned drawn = after.indexed_triangle_submissions - before.indexed_triangle_submissions;
	const bool passed = drawn == nodes * triangles &&
		after.rejected_indexed_submissions == before.rejected_indexed_submissions &&
		vertices->Num_Refs() == 1 && indices->Num_Refs() == 1 && sorting_order_valid &&
		sorting_observed_triangles == drawn && (drawn == 0 ||
		(sorting_max_depth == -9.0f && sorting_min_depth == (interleaved ? -49.0f : -9.0f) -
			2.0f*(nodes < 17 ? nodes-1 : 16)));
	std::printf("sorting.capacity nodes=%u vertices_per_node=%u triangles_per_node=%u drawn=%u expected=%u refs=%d/%d order=%d passed=%d\n",
		nodes, vertex_count, triangles, drawn, nodes * triangles,
		vertices->Num_Refs(), indices->Num_Refs(), sorting_order_valid ? 1 : 0, passed ? 1 : 0);
	std::fflush(stdout);
	vertices->Release_Ref();
	indices->Release_Ref();
	SortingRendererClass::Deinit();
	return passed;
}

// Exercise the original queue and CPU-backed draw boundary without retail data.
static bool Check_Original_Sorting_Renderer()
{
	Matrix4 old_world, old_view, old_projection;
	DX8Wrapper::Get_Transform(D3DTS_WORLD, old_world);
	DX8Wrapper::Get_Transform(D3DTS_VIEW, old_view);
	DX8Wrapper::Get_Transform(D3DTS_PROJECTION, old_projection);
	DX8Wrapper::Set_Transform(D3DTS_PROJECTION, Matrix4(true));
	const RenegadeVitaRenderer::Statistics before = RenegadeVitaRenderer::Get_Statistics();
	SortingVertexBufferClass *vertices = new SortingVertexBufferClass(6);
	SortingIndexBufferClass *indices = new SortingIndexBufferClass(6);
	{
		VertexBufferClass::WriteLockClass lock(vertices);
		VertexFormatXYZNDUV2 *v = static_cast<VertexFormatXYZNDUV2 *>(lock.Get_Vertex_Array());
		std::memset(v, 0, sizeof(*v) * 6);
		for (unsigned i = 0; i < 6; ++i) {
			v[i].x = static_cast<float>(i % 3);
			v[i].y = i % 3 == 1 ? 1.0f : 0.0f;
			v[i].z = i < 3 ? -5.0f : -10.0f;
			v[i].nz = 1.0f;
			v[i].diffuse = 0xffffffffU;
		}
	}
	{
		IndexBufferClass::WriteLockClass lock(indices);
		for (unsigned i = 0; i < 6; ++i) lock.Get_Index_Array()[i] = i;
	}
	DX8Wrapper::Set_Vertex_Buffer(vertices);
	DX8Wrapper::Set_Index_Buffer(indices, 0);
	DX8Wrapper::Set_Transform(D3DTS_WORLD, Matrix4(true));
	DX8Wrapper::Set_Transform(D3DTS_VIEW, Matrix4(true));
	SortingRendererClass::Insert_Triangles(0, 1, 0, 3);
	DX8Wrapper::Draw_Triangles(BUFFER_TYPE_SORTING, 3, 1, 3, 3);
	DX8Wrapper::Set_Vertex_Buffer(NULL);
	DX8Wrapper::Set_Index_Buffer(NULL, 0);
	const bool queued_refs = vertices->Num_Refs() == 3 && indices->Num_Refs() == 3;
	SortingRendererClass::Flush();
	const RenegadeVitaRenderer::Statistics after = RenegadeVitaRenderer::Get_Statistics();
	const bool flushed = after.indexed_triangle_submissions == before.indexed_triangle_submissions + 2 &&
		after.rejected_indexed_submissions == before.rejected_indexed_submissions &&
		vertices->Num_Refs() == 1 && indices->Num_Refs() == 1;
	// Deinit must also release queued work when a session exits before a flush.
	DX8Wrapper::Set_Vertex_Buffer(vertices);
	DX8Wrapper::Set_Index_Buffer(indices, 0);
	SortingRendererClass::Insert_Triangles(0, 1, 0, 3);
	DX8Wrapper::Set_Vertex_Buffer(NULL);
	DX8Wrapper::Set_Index_Buffer(NULL, 0);
	SortingRendererClass::Deinit();
	const bool released = vertices->Num_Refs() == 1 && indices->Num_Refs() == 1;
	vertices->Release_Ref();
	indices->Release_Ref();
	DX8Wrapper::Set_Transform(D3DTS_WORLD, old_world);
	DX8Wrapper::Set_Transform(D3DTS_VIEW, old_view);
	DX8Wrapper::Set_Transform(D3DTS_PROJECTION, old_projection);
	return queued_refs && flushed && released;
}

static unsigned strip_observed;
static bool strip_observation_valid;
static void Observe_Strip_Submission(const RenegadeVitaRenderer::IndexedTriangleSubmission &submission)
{
	const uint16_t expected[] = {0,1,2,2,1,3,2,3,4};
	++strip_observed;
	strip_observation_valid = submission.triangle_count == 3 && submission.first_index == 0 &&
		submission.base_vertex_index == 1 && submission.vertex_count == 5 &&
		submission.index_capacity == 9 &&
		std::memcmp(submission.index_data, expected, sizeof(expected)) == 0;
}

// Execute the actual DX8 strip entry point using original CPU-backed buffers.
static bool Check_Native_Strip_Renderer()
{
	DX8VertexBufferClass *vertices = new DX8VertexBufferClass(
		D3DFVF_XYZ | D3DFVF_NORMAL | D3DFVF_DIFFUSE | D3DFVF_TEX2, 6);
	DX8IndexBufferClass *indices = new DX8IndexBufferClass(7);
	{
		VertexBufferClass::WriteLockClass lock(vertices);
		auto *v = static_cast<VertexFormatXYZNDUV2 *>(lock.Get_Vertex_Array());
		std::memset(v, 0, sizeof(*v) * 6);
		for (unsigned i = 0; i < 6; ++i) {
			v[i].x = static_cast<float>(i % 2);
			v[i].y = static_cast<float>(i / 2);
			v[i].nz = 1.0f;
			v[i].diffuse = 0xffffffffU;
		}
	}
	{
		IndexBufferClass::WriteLockClass lock(indices);
		const uint16_t source[] = {99,99,0,1,2,3,4};
		std::memcpy(lock.Get_Index_Array(), source, sizeof(source));
	}
	DX8Wrapper::Set_Transform(D3DTS_WORLD, Matrix4(true));
	DX8Wrapper::Set_Transform(D3DTS_VIEW, Matrix4(true));
	DX8Wrapper::Set_Transform(D3DTS_PROJECTION, Matrix4(true));
	DX8Wrapper::Set_Vertex_Buffer(vertices);
	DX8Wrapper::Set_Index_Buffer(indices, 1);
	strip_observed = 0;
	strip_observation_valid = false;
	RenegadeVitaRenderer::Set_Host_Indexed_Submission_Observer(Observe_Strip_Submission);
	const auto before = RenegadeVitaRenderer::Get_Statistics();
	DX8Wrapper::Draw_Strip(2, 3, 0, 5);
	const auto valid = RenegadeVitaRenderer::Get_Statistics();
	bool passed = strip_observed == 1 && strip_observation_valid &&
		valid.indexed_triangle_submissions == before.indexed_triangle_submissions + 3 &&
		valid.rejected_indexed_submissions == before.rejected_indexed_submissions;
	DX8Wrapper::Draw_Strip(5, 3, 0, 5);
	DX8Wrapper::Draw_Strip(2, 0, 0, 5);
	const auto after = RenegadeVitaRenderer::Get_Statistics();
	passed = passed && strip_observed == 1 &&
		after.indexed_triangle_submissions == valid.indexed_triangle_submissions &&
		after.rejected_indexed_submissions == valid.rejected_indexed_submissions + 1;
	RenegadeVitaRenderer::Set_Host_Indexed_Submission_Observer(NULL);
	DX8Wrapper::Set_Vertex_Buffer(NULL);
	DX8Wrapper::Set_Index_Buffer(NULL, 0);
	passed = passed && vertices->Num_Refs() == 1 && indices->Num_Refs() == 1;
	vertices->Release_Ref();
	indices->Release_Ref();
	std::printf("indexed.strip observed=%u winding_offsets_bounds_refs=%d\n", strip_observed, passed ? 1 : 0);
	return passed;
}
