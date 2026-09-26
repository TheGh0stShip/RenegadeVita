#pragma once

namespace RenegadeVitaRenderer {

inline void Build_DX8_Texture_Source(bool passthrough_uv2, float s, float t,
	float r, float q, float source[4])
{
	source[0] = s;
	source[1] = t;
	source[2] = passthrough_uv2 ? 1.0f : r;
	source[3] = passthrough_uv2 ? 0.0f : q;
}

} // namespace RenegadeVitaRenderer
