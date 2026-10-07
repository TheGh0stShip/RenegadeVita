// One run of tools/vita_render_state_shadow_test.cpp: a GL shim holding
// vitaGL's observable state plus the renderer code extracted by
// tools/test_vita_render_state_shadow.py. Included once per namespace.
namespace RUN_NAMESPACE {

GLModel g_gl = {};
GLenum g_dx8_alpha_function = GL_ALWAYS;
float g_dx8_alpha_reference = 0.0f;
GLenum g_dx8_source_blend = GL_ONE;
GLenum g_dx8_destination_blend = GL_ZERO;

bool *Cap(GLenum cap)
{
	switch (cap) {
	case GL_BLEND: return &g_gl.blend;
	case GL_ALPHA_TEST: return &g_gl.alpha_test;
	case GL_CULL_FACE: return &g_gl.cull;
	case GL_DEPTH_TEST: return &g_gl.depth_test;
	case GL_POLYGON_OFFSET_FILL: return &g_gl.polygon_offset_fill;
	default:
		fprintf(stderr, "unexpected capability %04X\n", cap);
		abort();
	}
}

void glEnable(GLenum cap) { ++g_gl.calls; *Cap(cap) = true; }
void glDisable(GLenum cap) { ++g_gl.calls; *Cap(cap) = false; }
void glBlendFunc(GLenum source, GLenum destination)
{
	++g_gl.calls;
	g_gl.blend_source = source;
	g_gl.blend_destination = destination;
}
void glAlphaFunc(GLenum function, GLfloat reference)
{
	++g_gl.calls;
	g_gl.alpha_function = function;
	g_gl.alpha_reference = reference;
}
void glDepthFunc(GLenum function) { ++g_gl.calls; g_gl.depth_function = function; }
void glDepthMask(GLboolean mask) { ++g_gl.calls; g_gl.depth_mask = mask; }
void glColorMask(GLboolean red, GLboolean green, GLboolean blue, GLboolean alpha)
{
	++g_gl.calls;
	g_gl.color_mask[0] = red;
	g_gl.color_mask[1] = green;
	g_gl.color_mask[2] = blue;
	g_gl.color_mask[3] = alpha;
}
void glCullFace(GLenum face) { ++g_gl.calls; g_gl.cull_face = face; }
void glPolygonOffset(GLfloat factor, GLfloat units)
{
	++g_gl.calls;
	g_gl.polygon_offset_factor = factor;
	g_gl.polygon_offset_units = units;
}
void glPolygonMode(GLenum face, GLenum mode)
{
	++g_gl.calls;
	if (face != GL_FRONT_AND_BACK) abort();
	g_gl.polygon_mode = mode;
}
void glMatrixMode(GLenum mode) { ++g_gl.calls; g_gl.matrix_mode = mode; }
void glActiveTexture(GLenum unit)
{
	++g_gl.calls;
	g_gl.active_unit = unit - GL_TEXTURE0;
	if (g_gl.active_unit > 1U) abort();
}
GLfloat *Current_Matrix()
{
	switch (g_gl.matrix_mode) {
	case GL_PROJECTION: return g_gl.projection;
	case GL_MODELVIEW: return g_gl.modelview;
	case GL_TEXTURE: return g_gl.texture[g_gl.active_unit];
	default: abort();
	}
}
void glLoadMatrixf(const GLfloat *matrix)
{
	++g_gl.calls;
	memcpy(Current_Matrix(), matrix, 16U * sizeof(GLfloat));
}
void glLoadIdentity()
{
	++g_gl.calls;
	GLfloat *matrix = Current_Matrix();
	memset(matrix, 0, 16U * sizeof(GLfloat));
	matrix[0] = matrix[5] = matrix[10] = matrix[15] = 1.0f;
}
void RenegadeVita_Invalidate_DX8_Texture_Stage_Transform(unsigned) {}

#include "shadow_block.inc"
#include "reset_texture_matrix_stage.inc"
#include "dx8_translators.inc"

bool Harness_DX8_Render_State(uint32_t state, uint32_t value)
{
	bool handled = true;
	bool shader_state_overlap = false;
#include "dx8_render_state_switch.inc"
	(void)shader_state_overlap;
	return handled;
}

void Configure() { g_gl_state_shadow_enabled = RUN_ENABLED; }

}  // namespace RUN_NAMESPACE
