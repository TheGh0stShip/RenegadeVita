#pragma once

#include "d3d8.h"
#include "shader.h"

#include <stdint.h>
#include <string.h>

namespace RenegadeVitaRenderer {

enum BlendFactorContract {
	BLEND_FACTOR_ZERO,
	BLEND_FACTOR_ONE,
	BLEND_FACTOR_SRC_COLOR,
	BLEND_FACTOR_ONE_MINUS_SRC_COLOR,
	BLEND_FACTOR_SRC_ALPHA,
	BLEND_FACTOR_ONE_MINUS_SRC_ALPHA
};

struct ShaderStateContract {
	bool alpha_test;
	unsigned char alpha_reference;
	ShaderClass::DepthCompareType alpha_compare;
	bool blend;
	BlendFactorContract source_blend;
	BlendFactorContract destination_blend;
	ShaderClass::DepthCompareType depth_compare;
	bool depth_write;
	bool color_write;
	bool cull;
};

struct FogStateContract {
	bool enabled;
	uint32_t color;
	float start;
	float end;
};

inline FogStateContract Default_Fog_State()
{
	FogStateContract state = {};
	state.enabled = false;
	state.color = 0U;
	state.start = 0.0f;
	state.end = 1000.0f;
	return state;
}

inline float Decode_DX8_Float_Render_State(uint32_t value)
{
	float decoded = 0.0f;
	memcpy(&decoded, &value, sizeof(decoded));
	return decoded;
}

inline bool Update_Fog_State_From_DX8_Render_State(uint32_t render_state,
	uint32_t value, FogStateContract &state)
{
	switch (render_state) {
	case D3DRS_FOGENABLE:
		state.enabled = value != 0U;
		return true;
	case D3DRS_FOGCOLOR:
		state.color = value;
		return true;
	case D3DRS_FOGSTART:
		state.start = Decode_DX8_Float_Render_State(value);
		return true;
	case D3DRS_FOGEND:
		state.end = Decode_DX8_Float_Render_State(value);
		return true;
	default:
		return false;
	}
}

inline float D3D_Color_Red_Unit(uint32_t color)
{
	return static_cast<float>((color >> 16U) & 0xffU) / 255.0f;
}

inline float D3D_Color_Green_Unit(uint32_t color)
{
	return static_cast<float>((color >> 8U) & 0xffU) / 255.0f;
}

inline float D3D_Color_Blue_Unit(uint32_t color)
{
	return static_cast<float>(color & 0xffU) / 255.0f;
}

inline bool Update_Ambient_State_From_DX8_Render_State(uint32_t render_state,
	uint32_t value, uint32_t &ambient_color)
{
	if (render_state != D3DRS_AMBIENT) {
		return false;
	}
	ambient_color = value;
	return true;
}

inline BlendFactorContract Translate_Source_Blend(ShaderClass::SrcBlendFuncType value)
{
	switch (value) {
	case ShaderClass::SRCBLEND_ZERO: return BLEND_FACTOR_ZERO;
	case ShaderClass::SRCBLEND_ONE: return BLEND_FACTOR_ONE;
	case ShaderClass::SRCBLEND_SRC_ALPHA: return BLEND_FACTOR_SRC_ALPHA;
	case ShaderClass::SRCBLEND_ONE_MINUS_SRC_ALPHA: return BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
	default: return BLEND_FACTOR_ONE;
	}
}

inline BlendFactorContract Translate_Destination_Blend(ShaderClass::DstBlendFuncType value)
{
	switch (value) {
	case ShaderClass::DSTBLEND_ZERO: return BLEND_FACTOR_ZERO;
	case ShaderClass::DSTBLEND_ONE: return BLEND_FACTOR_ONE;
	case ShaderClass::DSTBLEND_SRC_COLOR: return BLEND_FACTOR_SRC_COLOR;
	case ShaderClass::DSTBLEND_ONE_MINUS_SRC_COLOR: return BLEND_FACTOR_ONE_MINUS_SRC_COLOR;
	case ShaderClass::DSTBLEND_SRC_ALPHA: return BLEND_FACTOR_SRC_ALPHA;
	case ShaderClass::DSTBLEND_ONE_MINUS_SRC_ALPHA: return BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
	default: return BLEND_FACTOR_ZERO;
	}
}

inline ShaderStateContract Translate_Shader_State(const ShaderClass &shader)
{
	ShaderStateContract state = {};
	state.alpha_test = shader.Get_Alpha_Test() == ShaderClass::ALPHATEST_ENABLE;
	state.source_blend = Translate_Source_Blend(shader.Get_Src_Blend_Func());
	state.destination_blend = Translate_Destination_Blend(shader.Get_Dst_Blend_Func());
	state.alpha_reference = 0U;
	state.alpha_compare = ShaderClass::PASS_ALWAYS;
	if (state.alpha_test) {
		const unsigned char reference = 0x60U;
		if (state.source_blend == BLEND_FACTOR_ONE_MINUS_SRC_ALPHA) {
			state.alpha_reference = static_cast<unsigned char>(0xffU - reference);
			state.alpha_compare = ShaderClass::PASS_LEQUAL;
		} else {
			state.alpha_reference = reference;
			state.alpha_compare = ShaderClass::PASS_GEQUAL;
		}
	}
	state.blend = !(state.source_blend == BLEND_FACTOR_ONE &&
		state.destination_blend == BLEND_FACTOR_ZERO);
	state.depth_compare = shader.Get_Depth_Compare();
	state.depth_write = shader.Get_Depth_Mask() == ShaderClass::DEPTH_WRITE_ENABLE;
	state.color_write = shader.Get_Color_Mask() == ShaderClass::COLOR_WRITE_ENABLE;
	state.cull = shader.Get_Cull_Mode() == ShaderClass::CULL_MODE_ENABLE;
	return state;
}

} // namespace RenegadeVitaRenderer
