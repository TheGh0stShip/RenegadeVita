#pragma once

#include "dx8wrapper.h"
#include "lightenvironment.h"
#include "light.h"
#include <cstdio>

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
	return retained;
}
