#pragma once

#include "shader.h"

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
