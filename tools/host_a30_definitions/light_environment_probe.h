#pragma once

#include "dx8wrapper.h"
#include "lightenvironment.h"
#include "light.h"
#include "ww3d_vita_renderer.h"
#include "vertmaterial.h"
#include <cstdio>
#include <cmath>
#include <cstring>

static bool Check_Indexed_Primary_Color()
{
	using namespace RenegadeVitaRenderer;
	unsigned char vertex[40] = {};
	const float normal[3] = {0.0f, 0.0f, 1.0f};
	const unsigned diffuse = 0x80402010U, specular = 0x40806020U;
	memcpy(vertex + 12, normal, sizeof(normal));
	memcpy(vertex + 24, &diffuse, sizeof(diffuse));
	memcpy(vertex + 28, &specular, sizeof(specular));
	float world[16] = {1,0,0,0, 0,1,0,0, 0,0,2,0, 0,0,0,1};
	RenderStateStruct state;
	state.material = new VertexMaterialClass;
	state.material->Set_Lighting(true);
	state.material->Set_Diffuse(0.4f, 0.2f, 0.1f);
	state.material->Set_Ambient(0.0f, 0.0f, 0.0f);
	state.material->Set_Emissive(0.05f, 0.1f, 0.15f);
	state.material->Set_Opacity(0.75f);
	for (unsigned slot = 0; slot < 4; ++slot) state.LightEnable[slot] = false;
	state.LightEnable[0] = true;
	state.Lights[0] = D3DLIGHT8{};
	state.Lights[0].Type = D3DLIGHT_DIRECTIONAL;
	state.Lights[0].Direction.z = -1.0f;
	state.Lights[0].Diffuse.r = state.Lights[0].Diffuse.g = state.Lights[0].Diffuse.b = 1.0f;
	IndexedTriangleSubmission submission = {};
	submission.vertex_data = vertex;
	submission.vertex_data_size = sizeof(vertex);
	submission.vertex_format = 0x1d2U;
	submission.vertex_stride = sizeof(vertex);
	submission.vertex_capacity = 1;
	submission.world_transform = world;
	submission.draw_state = &state;
	float rgba[4] = {};
	auto matches = [&](float r, float g, float b, float a) {
		return Evaluate_Indexed_Primary_Color(submission, 0, rgba) &&
			std::fabs(rgba[0]-r) < 0.00001f && std::fabs(rgba[1]-g) < 0.00001f &&
			std::fabs(rgba[2]-b) < 0.00001f && std::fabs(rgba[3]-a) < 0.00001f;
	};
	Apply_DX8_Render_State(D3DRS_AMBIENT, 0U);
	Apply_DX8_Render_State(D3DRS_COLORVERTEX, 1U);
	Apply_DX8_Render_State(D3DRS_NORMALIZENORMALS, 0U);
	bool passed = matches(0.25f, 0.2f, 0.2f, 0.75f);
	Apply_DX8_Render_State(D3DRS_NORMALIZENORMALS, 1U);
	passed = matches(0.45f, 0.3f, 0.25f, 0.75f) && passed;
	state.material->Set_Diffuse_Color_Source(VertexMaterialClass::COLOR2);
	passed = matches(128.0f/255+0.05f, 96.0f/255+0.1f, 32.0f/255+0.15f, 64.0f/255) && passed;
	Apply_DX8_Render_State(D3DRS_COLORVERTEX, 0U);
	passed = matches(0.45f, 0.3f, 0.25f, 0.75f) && passed;
	Apply_DX8_Render_State(D3DRS_COLORVERTEX, 1U);
	state.material->Set_Lighting(false);
	passed = matches(64.0f/255, 32.0f/255, 16.0f/255, 128.0f/255) && passed;
	state.material->Set_Lighting(true);
	state.Lights[0].Type = D3DLIGHT_POINT;
	rgba[0] = -9.0f;
	passed = !Evaluate_Indexed_Primary_Color(submission, 0, rgba) && rgba[0] == -9.0f && passed;
	passed = !Evaluate_Indexed_Primary_Color(submission, 1, rgba) && passed;
	Apply_DX8_Render_State(D3DRS_NORMALIZENORMALS, 0U);
	std::printf("indexed primary color: material sources, scaled normals, unlit and rejection %s\n", passed ? "PASS" : "FAIL");
	return passed;
}

struct OriginalLightStateProbe : DX8Wrapper {
	static unsigned Ambient() { return RenderStates[D3DRS_AMBIENT]; }
};

static bool Check_Original_Light_Environment()
{
	LightEnvironmentClass environment;
	const Matrix3D camera(true);
	const Vector3 center(0.0f, 0.0f, 0.0f);
	const Vector3 ambient(0.125f, 0.25f, 0.5f);
	for (int count = 4; count >= 0; --count) {
		environment.Reset(center, ambient);
		for (int index = 0; index < count; ++index) {
			LightClass light(LightClass::DIRECTIONAL);
			light.Set_Diffuse(Vector3(0.5f, 0.75f, 1.0f));
			light.Set_Intensity(1.0f);
			environment.Add_Light(light);
		}
		environment.Pre_Render_Update(camera);
		if (environment.Get_Light_Count() != count) return false;
		DX8Wrapper::Set_Light_Environment(&environment);
		if (OriginalLightStateProbe::Ambient() != DX8Wrapper::Convert_Color(
			environment.Get_Equivalent_Ambient(), 0.0f)) return false;
		for (int index = 0; index < 4; ++index) {
			if (DX8Wrapper::Is_Light_Enabled(index) != (index < count)) return false;
			if (index >= count) continue;
			const D3DLIGHT8 &actual = DX8Wrapper::Peek_Light(index);
			const Vector3 &diffuse = environment.Get_Light_Diffuse(index);
			const Vector3 direction = -environment.Get_Light_Direction(index);
			if (actual.Type != D3DLIGHT_DIRECTIONAL || actual.Diffuse.r != diffuse.X ||
				actual.Diffuse.g != diffuse.Y || actual.Diffuse.b != diffuse.Z ||
				actual.Direction.x != direction.X || actual.Direction.y != direction.Y ||
				actual.Direction.z != direction.Z || actual.Diffuse.a != 0.0f) return false;
		}
	}
	// The original null-environment path intentionally retains prior light state.
	D3DLIGHT8 sentinel = {};
	sentinel.Type = D3DLIGHT_DIRECTIONAL;
	sentinel.Diffuse.r = 0.75f;
	DX8Wrapper::Set_Light(2, &sentinel);
	DX8Wrapper::Set_Light_Environment(NULL);
	const bool retained = DX8Wrapper::Is_Light_Enabled(2) &&
		DX8Wrapper::Peek_Light(2).Diffuse.r == sentinel.Diffuse.r;
	for (int index = 0; index < 4; ++index) DX8Wrapper::Set_Light(index, NULL);
	std::printf("original light environment: four-to-zero slots and null retention %s\n",
		retained ? "PASS" : "FAIL");
	return Check_Indexed_Primary_Color() && retained;
}
