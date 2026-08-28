#include "shader.h"
#include "ww3d_vita_render_state_contract.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

static bool Check(bool value, const char *label, unsigned &checks)
{
	++checks;
	if (!value) fprintf(stderr, "FAIL: %s\n", label);
	return value;
}

static uint32_t Float_Bits(float value)
{
	uint32_t bits = 0U;
	memcpy(&bits, &value, sizeof(bits));
	return bits;
}

int main()
{
	using namespace RenegadeVitaRenderer;
	unsigned checks = 0U;
	unsigned failures = 0U;
	ShaderClass opaque;
	ShaderStateContract state = Translate_Shader_State(opaque);
	failures += !Check(!state.alpha_test && !state.blend && state.depth_write &&
		state.color_write && state.cull, "opaque default", checks);
	ShaderClass cutout;
	cutout.Set_Alpha_Test(ShaderClass::ALPHATEST_ENABLE);
	state = Translate_Shader_State(cutout);
	failures += !Check(state.alpha_test && !state.blend &&
		state.alpha_reference == 0x60U &&
		state.alpha_compare == ShaderClass::PASS_GEQUAL,
		"alpha cutout", checks);
	ShaderClass inverse_cutout;
	inverse_cutout.Set_Alpha_Test(ShaderClass::ALPHATEST_ENABLE);
	inverse_cutout.Set_Src_Blend_Func(ShaderClass::SRCBLEND_ONE_MINUS_SRC_ALPHA);
	state = Translate_Shader_State(inverse_cutout);
	failures += !Check(state.alpha_test &&
		state.alpha_reference == static_cast<unsigned char>(0xffU - 0x60U) &&
		state.alpha_compare == ShaderClass::PASS_LEQUAL,
		"inverse alpha cutout", checks);
	ShaderClass alpha;
	alpha.Set_Src_Blend_Func(ShaderClass::SRCBLEND_SRC_ALPHA);
	alpha.Set_Dst_Blend_Func(ShaderClass::DSTBLEND_ONE_MINUS_SRC_ALPHA);
	alpha.Set_Depth_Mask(ShaderClass::DEPTH_WRITE_DISABLE);
	state = Translate_Shader_State(alpha);
	failures += !Check(state.blend && state.source_blend == BLEND_FACTOR_SRC_ALPHA &&
		state.destination_blend == BLEND_FACTOR_ONE_MINUS_SRC_ALPHA && !state.depth_write,
		"standard alpha", checks);
	ShaderClass additive;
	additive.Set_Src_Blend_Func(ShaderClass::SRCBLEND_ONE);
	additive.Set_Dst_Blend_Func(ShaderClass::DSTBLEND_ONE);
	additive.Set_Cull_Mode(ShaderClass::CULL_MODE_DISABLE);
	state = Translate_Shader_State(additive);
	failures += !Check(state.blend && state.source_blend == BLEND_FACTOR_ONE &&
		state.destination_blend == BLEND_FACTOR_ONE && !state.cull, "additive", checks);
	FogStateContract fog = Default_Fog_State();
	failures += !Check(!fog.enabled && fog.color == 0U &&
		fog.start == 0.0f && fog.end == 1000.0f, "default fog disabled", checks);
	failures += !Check(Update_Fog_State_From_DX8_Render_State(D3DRS_FOGENABLE,
		1U, fog) && fog.enabled, "fog enable state", checks);
	failures += !Check(Update_Fog_State_From_DX8_Render_State(D3DRS_FOGCOLOR,
		0x00123456U, fog) && fog.color == 0x00123456U &&
		D3D_Color_Red_Unit(fog.color) > 0.070f &&
		D3D_Color_Green_Unit(fog.color) > 0.200f &&
		D3D_Color_Blue_Unit(fog.color) > 0.330f, "fog color state", checks);
	failures += !Check(Update_Fog_State_From_DX8_Render_State(D3DRS_FOGSTART,
		Float_Bits(12.5f), fog) && fog.start == 12.5f,
		"fog start state", checks);
	failures += !Check(Update_Fog_State_From_DX8_Render_State(D3DRS_FOGEND,
		Float_Bits(250.0f), fog) && fog.end == 250.0f,
		"fog end state", checks);
	failures += !Check(!Update_Fog_State_From_DX8_Render_State(D3DRS_AMBIENT,
		0x00ffffffU, fog), "non-fog render state ignored", checks);
	printf("A3.5 Vita ShaderClass render-state contract: %u checks, %u failures\n", checks, failures);
	return failures == 0U ? 0 : 1;
}
