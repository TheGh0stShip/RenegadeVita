// Original DX8Wrapper::Set_Light_Environment from EA's dx8wrapper.cpp.
// Only the MSVC for-scope declaration is moved for standard C++ compilation.
void DX8Wrapper::Set_Light_Environment(LightEnvironmentClass *light_env)
{
	if (light_env) {
		int light_count = light_env->Get_Light_Count();
		Set_DX8_Render_State(D3DRS_AMBIENT,
			Convert_Color(light_env->Get_Equivalent_Ambient(), 0.0f));

		D3DLIGHT8 light;
		::ZeroMemory(&light, sizeof(D3DLIGHT8));
		light.Type = D3DLIGHT_DIRECTIONAL;
		int l;
		for (l = 0; l < light_count; ++l) {
			(Vector3 &)light.Diffuse = light_env->Get_Light_Diffuse(l);
			Vector3 dir = -light_env->Get_Light_Direction(l);
			light.Direction = (const D3DVECTOR &)(dir);
			Set_Light(l, &light);
		}
		for (; l < 4; ++l) {
			Set_Light(l, NULL);
		}
	}
}
