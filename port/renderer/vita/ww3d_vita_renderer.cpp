#include "ww3d_vita_renderer.h"

#include "camera.h"
#include "mesh.h"
#include "meshmdl.h"
#include "matrix4.h"
#include "rendobj.h"
#include "rinfo.h"
#include "shader.h"
#include "tri.h"
#include "ww3d_vita_render_state_contract.h"

#include <stddef.h>
#include <stdio.h>
#include <string.h>

#if defined(__vita__)
#include "vita_runtime_log.h"

#include <psp2/io/stat.h>
#include <psp2/kernel/sysmem.h>
#include <vitaGL.h>
#endif

namespace RenegadeVitaRenderer {
namespace {

Statistics g_statistics = {};
BackendLifecycleStatistics g_lifecycle = {};
bool g_logged_first_unsupported = false;
bool g_logged_first_indexed_rejection = false;

#if defined(__vita__)
bool g_logged_first_frame = false;
bool g_logged_first_present = false;
bool g_logged_first_mesh = false;
bool g_shader_compiler_available = false;
unsigned g_shader_init_calls = 0;
int g_shader_init_last_result = -1;

GLenum To_GL_Depth_Function(ShaderClass::DepthCompareType function)
{
	switch (function) {
	case ShaderClass::PASS_NEVER: return GL_NEVER;
	case ShaderClass::PASS_LESS: return GL_LESS;
	case ShaderClass::PASS_EQUAL: return GL_EQUAL;
	case ShaderClass::PASS_LEQUAL: return GL_LEQUAL;
	case ShaderClass::PASS_GREATER: return GL_GREATER;
	case ShaderClass::PASS_NOTEQUAL: return GL_NOTEQUAL;
	case ShaderClass::PASS_GEQUAL: return GL_GEQUAL;
	case ShaderClass::PASS_ALWAYS: return GL_ALWAYS;
	default: return GL_LEQUAL;
	}
}

GLenum To_GL_Source_Blend(ShaderClass::SrcBlendFuncType function)
{
	switch (function) {
	case ShaderClass::SRCBLEND_ZERO: return GL_ZERO;
	case ShaderClass::SRCBLEND_ONE: return GL_ONE;
	case ShaderClass::SRCBLEND_SRC_ALPHA: return GL_SRC_ALPHA;
	case ShaderClass::SRCBLEND_ONE_MINUS_SRC_ALPHA: return GL_ONE_MINUS_SRC_ALPHA;
	default: return GL_ONE;
	}
}

GLenum To_GL_Destination_Blend(ShaderClass::DstBlendFuncType function)
{
	switch (function) {
	case ShaderClass::DSTBLEND_ZERO: return GL_ZERO;
	case ShaderClass::DSTBLEND_ONE: return GL_ONE;
	case ShaderClass::DSTBLEND_SRC_COLOR: return GL_SRC_COLOR;
	case ShaderClass::DSTBLEND_ONE_MINUS_SRC_COLOR: return GL_ONE_MINUS_SRC_COLOR;
	case ShaderClass::DSTBLEND_SRC_ALPHA: return GL_SRC_ALPHA;
	case ShaderClass::DSTBLEND_ONE_MINUS_SRC_ALPHA: return GL_ONE_MINUS_SRC_ALPHA;
	default: return GL_ZERO;
	}
}

void Apply_Original_Shader_State(const ShaderClass &shader)
{
	const ShaderStateContract state = Translate_Shader_State(shader);
	if (state.alpha_test) {
		glEnable(GL_ALPHA_TEST);
		glAlphaFunc(GL_GREATER, 0.0f);
	} else {
		glDisable(GL_ALPHA_TEST);
	}
	const GLenum source = To_GL_Source_Blend(shader.Get_Src_Blend_Func());
	const GLenum destination = To_GL_Destination_Blend(shader.Get_Dst_Blend_Func());
	if (!state.blend) glDisable(GL_BLEND);
	else {
		glEnable(GL_BLEND);
		glBlendFunc(source, destination);
	}
	glDepthFunc(To_GL_Depth_Function(state.depth_compare));
	glDepthMask(state.depth_write ? GL_TRUE : GL_FALSE);
	glColorMask(state.color_write ? GL_TRUE : GL_FALSE, state.color_write ? GL_TRUE : GL_FALSE,
		state.color_write ? GL_TRUE : GL_FALSE, state.color_write ? GL_TRUE : GL_FALSE);
	if (state.cull) {
		glEnable(GL_CULL_FACE);
		glCullFace(GL_BACK);
	} else glDisable(GL_CULL_FACE);
	++g_statistics.state_changes;
}

void Log_System_Memory(const char *stage)
{
	SceKernelFreeMemorySizeInfo memory = {};
	memory.size = sizeof(memory);
	const int result = sceKernelGetFreeMemorySize(&memory);
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"free memory %s: rc=%08X user=%d cdram=%d phycont=%d",
		stage, static_cast<unsigned>(result), memory.size_user,
		memory.size_cdram, memory.size_phycont);
}

void Log_Shader_Module(const char *label, const char *path)
{
	SceIoStat status = {};
	const int result = sceIoGetstat(path, &status);
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"libshacccg %s: path=%s stat_rc=%08X size=%llu",
		label, path, static_cast<unsigned>(result),
		result >= 0 ? static_cast<unsigned long long>(status.st_size) : 0ULL);
}

const char *Shark_Level_Name(shark_log_level level)
{
	switch (level) {
	case SHARK_LOG_INFO:
		return "INFO";
	case SHARK_LOG_WARNING:
		return "WARNING";
	case SHARK_LOG_ERROR:
		return "ERROR";
	default:
		return "UNKNOWN";
	}
}

void Shark_Log_Callback(const char *message, shark_log_level level, int line)
{
	Vita_Append_A22_Runtime_Breadcrumb("shader-compiler",
		"level=%s(%d) line=%d message=%s", Shark_Level_Name(level),
		static_cast<int>(level), line, message != NULL ? message : "(null)");
}

GLenum Log_GL_Result(const char *operation)
{
	const GLenum error = glGetError();
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"%s return: glGetError=%08X", operation, static_cast<unsigned>(error));
	return error;
}

void Log_VitaGL_Memory()
{
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"vitaGL pools bytes total/free: RAM=%llu/%llu VRAM=%llu/%llu SLOW=%llu/%llu BUDGET=%llu/%llu ALL=%llu/%llu",
		static_cast<unsigned long long>(vglMemTotal(VGL_MEM_RAM)),
		static_cast<unsigned long long>(vglMemFree(VGL_MEM_RAM)),
		static_cast<unsigned long long>(vglMemTotal(VGL_MEM_VRAM)),
		static_cast<unsigned long long>(vglMemFree(VGL_MEM_VRAM)),
		static_cast<unsigned long long>(vglMemTotal(VGL_MEM_SLOW)),
		static_cast<unsigned long long>(vglMemFree(VGL_MEM_SLOW)),
		static_cast<unsigned long long>(vglMemTotal(VGL_MEM_BUDGET)),
		static_cast<unsigned long long>(vglMemFree(VGL_MEM_BUDGET)),
		static_cast<unsigned long long>(vglMemTotal(VGL_MEM_ALL)),
		static_cast<unsigned long long>(vglMemFree(VGL_MEM_ALL)));
}
#endif

bool Reactivate_Native_Backend_State()
{
#if defined(__vita__)
	Vita_Append_A22_Runtime_Breadcrumb("renderer-lifecycle",
		"logical session reactivation entry: native_calls=%u prior_sessions=%u",
		g_lifecycle.native_initialization_calls,
		g_lifecycle.logical_sessions);
	(void)glGetError();
	glViewport(0, 0, static_cast<GLsizei>(DISPLAY_WIDTH),
		static_cast<GLsizei>(DISPLAY_HEIGHT));
	glDepthRangef(0.0f, 1.0f);
	glEnable(GL_DEPTH_TEST);
	glDepthFunc(GL_LEQUAL);
	glDisable(GL_CULL_FACE);
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	const GLenum error = glGetError();
	Vita_Append_A22_Runtime_Breadcrumb("renderer-lifecycle",
		"logical session reactivation return: glGetError=%08X native_calls=%u",
		static_cast<unsigned>(error),
		g_lifecycle.native_initialization_calls);
	if (error != GL_NO_ERROR) {
		return false;
	}
	g_logged_first_frame = false;
	g_logged_first_present = false;
	g_logged_first_mesh = false;
#endif
	return true;
}

uint32_t Mix_Checksum(uint32_t value, uint32_t word)
{
	return (value ^ word) * 16777619U;
}

bool Is_Zero_Matrix(const float *matrix)
{
	if (matrix == NULL) {
		return true;
	}
	for (unsigned index = 0; index < 16; ++index) {
		if (matrix[index] != 0.0f) {
			return false;
		}
	}
	return true;
}

uint32_t Float_Bits(float value)
{
	uint32_t bits = 0;
	memcpy(&bits, &value, sizeof(bits));
	return bits;
}

void Log_Indexed_Rejection(const char *reason, uint32_t vertex_format)
{
	if (g_logged_first_indexed_rejection) {
		return;
	}
#if defined(__vita__)
	Vita_Append_A22_Runtime_Breadcrumb("indexed-submit",
		"first rejected original DX8Wrapper draw: reason=%s fvf=%08X",
		reason != NULL ? reason : "(unknown)", vertex_format);
#else
	fprintf(stderr,
		"A3.0 first rejected original DX8Wrapper draw: reason=%s fvf=%08X\n",
		reason != NULL ? reason : "(unknown)", vertex_format);
#endif
	g_logged_first_indexed_rejection = true;
}

} // namespace

bool Build_Indexed_Transform_Matrices(const float *world_transform,
	const float *view_transform, const float *projection_transform,
	IndexedTransformMatrices &matrices)
{
	if (Is_Zero_Matrix(world_transform) || Is_Zero_Matrix(view_transform) ||
		Is_Zero_Matrix(projection_transform)) {
		return false;
	}

	// DX8Wrapper stores the transposes of WWMath's column-vector matrices.
	// For an original p * Dworld * Dview operation, glLoadMatrixf must receive
	// Dworld * Dview: vitaGL transposes that row-major memory internally and
	// consequently evaluates V * W * p in its fixed-function vertex shader.
	for (unsigned row = 0; row < 4U; ++row) {
		for (unsigned column = 0; column < 4U; ++column) {
			float value = 0.0f;
			for (unsigned inner = 0; inner < 4U; ++inner) {
				value += world_transform[row * 4U + inner] *
					view_transform[inner * 4U + column];
			}
			matrices.modelview[row * 4U + column] = value;
		}
	}

	memcpy(matrices.projection, projection_transform,
		sizeof(matrices.projection));
	for (unsigned row = 0; row < 4U; ++row) {
		// Direct3D clip depth is 0..W; OpenGL/vitaGL clip depth is -W..W.
		// In row-vector memory this is Dprojection * transpose(C), where
		// C maps (x,y,z,w) to (x,y,2z-w,w).
		matrices.projection[row * 4U + 2U] =
			2.0f * projection_transform[row * 4U + 2U] -
			projection_transform[row * 4U + 3U];
	}
	return true;
}

bool Build_Native_Viewport(uint32_t d3d_x, uint32_t d3d_y,
	uint32_t width, uint32_t height, float min_depth, float max_depth,
	NativeViewport &viewport)
{
	if (width == 0U || height == 0U || d3d_x > DISPLAY_WIDTH ||
		d3d_y > DISPLAY_HEIGHT || width > DISPLAY_WIDTH - d3d_x ||
		height > DISPLAY_HEIGHT - d3d_y || min_depth < 0.0f ||
		max_depth > 1.0f || min_depth > max_depth) {
		return false;
	}

	viewport.x = d3d_x;
	viewport.y = DISPLAY_HEIGHT - d3d_y - height;
	viewport.width = width;
	viewport.height = height;
	viewport.min_depth = min_depth;
	viewport.max_depth = max_depth;
	return true;
}

bool Apply_Viewport(uint32_t d3d_x, uint32_t d3d_y, uint32_t width,
	uint32_t height, float min_depth, float max_depth)
{
	NativeViewport viewport = {};
	if (!Build_Native_Viewport(d3d_x, d3d_y, width, height, min_depth,
		max_depth, viewport)) {
		return false;
	}

#if defined(__vita__)
	if (!g_statistics.initialized) {
		return false;
	}
	// Consume an older error before issuing the two camera-owned operations so
	// the return value describes this viewport transition, not unrelated state.
	const GLenum prior_error = glGetError();
	glViewport(static_cast<GLint>(viewport.x),
		static_cast<GLint>(viewport.y), static_cast<GLsizei>(viewport.width),
		static_cast<GLsizei>(viewport.height));
	glDepthRangef(viewport.min_depth, viewport.max_depth);
	const GLenum operation_error = glGetError();
	++g_statistics.state_changes;
	if (operation_error != GL_NO_ERROR) {
		++g_statistics.backend_errors;
	}
	static bool logged_first_camera_viewport = false;
	if (!logged_first_camera_viewport) {
		Vita_Append_A22_Runtime_Breadcrumb("camera-state",
			"original CameraClass viewport: d3d=%u,%u %ux%u native=%u,%u %ux%u depth=%.6f..%.6f prior_gl=%08X gl=%08X",
			d3d_x, d3d_y, width, height, viewport.x, viewport.y,
			viewport.width, viewport.height, viewport.min_depth,
			viewport.max_depth, static_cast<unsigned>(prior_error),
			static_cast<unsigned>(operation_error));
		logged_first_camera_viewport = true;
	}
	return operation_error == GL_NO_ERROR;
#else
	return true;
#endif
}

#if defined(__vita__)
extern "C" int __real_shark_init(const char *path);

extern "C" int __wrap_shark_init(const char *path)
{
	Vita_Append_A22_Runtime_Breadcrumb("shader-compiler",
		"shark_init entry: call=%u path=%s", g_shader_init_calls + 1,
		path != NULL ? path : "(default ur0:/data/libshacccg.suprx)");
	const int result = __real_shark_init(path);
	++g_shader_init_calls;
	g_shader_init_last_result = result;
	if (result >= 0) {
		g_shader_compiler_available = true;
	}
	Vita_Append_A22_Runtime_Breadcrumb("shader-compiler",
		"shark_init return: call=%u rc=%08X available=%d", g_shader_init_calls,
		static_cast<unsigned>(result), g_shader_compiler_available ? 1 : 0);
	return result;
}
#endif

bool Initialize()
{
	if (g_statistics.initialized) {
		return true;
	}
	if (g_lifecycle.native_initialization_attempted) {
		if (!g_lifecycle.native_backend_ready) {
#if defined(__vita__)
			Vita_Append_A22_Runtime_Breadcrumb("renderer-lifecycle",
				"logical session rejected: first native initialization failed; vglInit retry prohibited");
#endif
			return false;
		}
		if (!Reactivate_Native_Backend_State()) {
			return false;
		}
		g_statistics.initialized = true;
		g_lifecycle.logical_session_active = true;
		++g_lifecycle.logical_sessions;
#if defined(__vita__)
		Vita_Append_A22_Runtime_Breadcrumb("renderer-lifecycle",
			"logical session reactivated: session=%u native_calls=%u",
			g_lifecycle.logical_sessions,
			g_lifecycle.native_initialization_calls);
#endif
		return true;
	}

	g_lifecycle.native_initialization_attempted = true;
	++g_lifecycle.native_initialization_calls;
#if defined(__vita__)
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"entry: backend=vitaGL commit=6e7fe40 API=vglInit native_call=%u",
		g_lifecycle.native_initialization_calls);
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"display request: 960x544 buffers=3 color=SCE_GXM_COLOR_FORMAT_A8B8G8R8 depth=SCE_GXM_DEPTH_STENCIL_FORMAT_DF32M_S8 msaa=SCE_GXM_MULTISAMPLE_4X");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"memory policy: legacy_pool=4194304 circular_pool=33554432 ram_reserve=16777216 cdram_reserve=0 phycont_reserve=0 cdlg_pool=0");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"GXM defaults: parameter=16777216 vdm=131072 vertex=2097152 fragment=524288 fragment_usse=16384 shader_patcher=1048576/1048576/1048576 vertex_attrib=262144/65536");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"shader compiler config: vitaShaRK default=ur0:/data/libshacccg.suprx fallback=ur0:data/external/libshacccg.suprx opt=FAST fastmath=1 fastprecision=0 fastint=1");
	Log_System_Memory("before vglInit");
	Log_Shader_Module("default", "ur0:/data/libshacccg.suprx");
	Log_Shader_Module("fallback", "ur0:data/external/libshacccg.suprx");
	shark_install_log_cb(Shark_Log_Callback);
	shark_set_warnings_level(SHARK_WARN_HIGH);
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"vitaShaRK diagnostic callback installation: complete");
	g_shader_compiler_available = false;
	g_shader_init_calls = 0;
	g_shader_init_last_result = -1;

	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "vglInit entry");
	const GLboolean resolution_fallback = vglInit(4 * 1024 * 1024);
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"vglInit return: raw=%d semantic=resolution_fallback call_completed=1",
		static_cast<int>(resolution_fallback));
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"internal stages reached before vglInit return: GXM/context/framebuffer/depth/shader-patcher/clear-program/index-buffer/texture0 attempted; installed NO_DEBUG archive does not expose their individual return codes");
	Log_System_Memory("after vglInit");
	Log_VitaGL_Memory();
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"shader compiler init summary: calls=%u last_rc=%08X available=%d",
		g_shader_init_calls, static_cast<unsigned>(g_shader_init_last_result),
		g_shader_compiler_available ? 1 : 0);

	GLint initial_viewport[4] = {};
	glGetIntegerv(GL_VIEWPORT, initial_viewport);
	const GLenum query_error = Log_GL_Result("viewport query");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"framebuffer/display query: viewport=%d,%d %dx%d expected=960x544",
		initial_viewport[0], initial_viewport[1], initial_viewport[2], initial_viewport[3]);

	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "glViewport entry");
	glViewport(0, 0, 960, 544);
	const GLenum viewport_error = Log_GL_Result("glViewport");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "depth buffer state entry");
	glEnable(GL_DEPTH_TEST);
	glDepthFunc(GL_LEQUAL);
	const GLenum depth_error = Log_GL_Result("depth enable/function");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "raster state-cache entry");
	glDisable(GL_CULL_FACE);
	const GLenum raster_error = Log_GL_Result("cull disable/state cache");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "projection state entry");
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	const GLenum projection_error = Log_GL_Result("projection identity");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init", "modelview state entry");
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	const GLenum modelview_error = Log_GL_Result("modelview identity");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"vertex/index/texture backend state: vglInit path returned after immediate-pool/default-index/texture0 setup; FFP programs are lazy at first mesh");

	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"first clear entry: color=0.035,0.055,0.085,1 depth=1");
	glClearColor(0.035f, 0.055f, 0.085f, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	const GLenum clear_error = Log_GL_Result("first clear/framebuffer scene reset");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"first present entry: frame_before=%u", vglGetFrameNumber());
	vglSwapBuffers(GL_FALSE);
	const GLenum present_error = Log_GL_Result("first vglSwapBuffers");
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"first present return: frame_after=%u splash_transition_requested=1",
		vglGetFrameNumber());

	const bool display_ready = initial_viewport[2] > 0 && initial_viewport[3] > 0;
	const bool gl_ready = query_error == GL_NO_ERROR && viewport_error == GL_NO_ERROR &&
		depth_error == GL_NO_ERROR && raster_error == GL_NO_ERROR &&
		projection_error == GL_NO_ERROR && modelview_error == GL_NO_ERROR &&
		clear_error == GL_NO_ERROR && present_error == GL_NO_ERROR;
	if (!g_shader_compiler_available || !display_ready || !gl_ready) {
		Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
			"failure return: shader_available=%d last_rc=%08X display_ready=%d gl_ready=%d",
			g_shader_compiler_available ? 1 : 0,
			static_cast<unsigned>(g_shader_init_last_result), display_ready ? 1 : 0,
			gl_ready ? 1 : 0);
		return false;
	}
	g_logged_first_frame = false;
	g_logged_first_present = false;
	g_logged_first_mesh = false;
#endif
	g_lifecycle.native_backend_ready = true;
	g_statistics.initialized = true;
	g_lifecycle.logical_session_active = true;
	++g_lifecycle.logical_sessions;
#if defined(__vita__)
	Vita_Append_A22_Runtime_Breadcrumb("renderer-init",
		"successful renderer initialization return: initialized=1 resolution_fallback=%d native_calls=%u logical_session=%u",
		static_cast<int>(resolution_fallback),
		g_lifecycle.native_initialization_calls,
		g_lifecycle.logical_sessions);
#endif
	return true;
}

void Shutdown()
{
	// vitaGL does not expose a process-lifetime shutdown call. The application
	// owns it until clean process exit.  This ends only WW3D's logical session.
	if (g_statistics.initialized || g_lifecycle.logical_session_active) {
		++g_lifecycle.logical_shutdowns;
	}
	g_statistics.initialized = false;
	g_lifecycle.logical_session_active = false;
#if defined(__vita__)
	Vita_Append_A22_Runtime_Breadcrumb("renderer-lifecycle",
		"logical shutdown: shutdowns=%u sessions=%u native_calls=%u native_ready=%d",
		g_lifecycle.logical_shutdowns, g_lifecycle.logical_sessions,
		g_lifecycle.native_initialization_calls,
		g_lifecycle.native_backend_ready ? 1 : 0);
#endif
}

void Begin_Frame(float red, float green, float blue)
{
	if (!g_statistics.initialized) {
		return;
	}
	++g_statistics.frames;
#if defined(__vita__)
	if (!g_logged_first_frame) {
		Vita_Append_A22_Runtime_Breadcrumb("render-frame",
			"WW3D first Begin_Frame entry: clear=(%.3f,%.3f,%.3f)", red, green, blue);
	}
	glClearColor(red, green, blue, 1.0f);
	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
	if (!g_logged_first_frame) {
		const GLenum error = glGetError();
		Vita_Append_A22_Runtime_Breadcrumb("render-frame",
			"WW3D first Begin_Frame return: glGetError=%08X frame=%u",
			static_cast<unsigned>(error), vglGetFrameNumber());
		g_logged_first_frame = true;
	}
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	g_statistics.state_changes += 5U;
#else
	(void)red;
	(void)green;
	(void)blue;
#endif
}

void End_Frame(bool present)
{
#if defined(__vita__)
	if (g_statistics.initialized && present) {
		if (!g_logged_first_present) {
			Vita_Append_A22_Runtime_Breadcrumb("render-frame",
				"WW3D first End_Frame present entry: frame_before=%u", vglGetFrameNumber());
		}
		vglSwapBuffers(GL_FALSE);
		const GLenum present_error = glGetError();
		if (present_error != GL_NO_ERROR) {
			++g_statistics.backend_errors;
		}
		if (!g_logged_first_present) {
			Vita_Append_A22_Runtime_Breadcrumb("render-frame",
				"WW3D first End_Frame present return: frame_after=%u glGetError=%08X",
				vglGetFrameNumber(), static_cast<unsigned>(present_error));
			g_logged_first_present = true;
		}
	}
#else
	(void)present;
#endif
}

void Record_Texture_Request()
{
	++g_statistics.texture_requests;
}

void Record_Texture_Decode()
{
	++g_statistics.texture_decodes;
}

void Record_Texture_Missing()
{
	++g_statistics.texture_missing;
}

void Record_Texture_Source_Missing()
{
	++g_statistics.texture_missing;
	++g_statistics.texture_source_missing;
}

void Record_Texture_Invalid_Data()
{
	++g_statistics.texture_missing;
	++g_statistics.texture_invalid_data;
}

void Record_Texture_Unsupported_Format()
{
	++g_statistics.texture_missing;
	++g_statistics.texture_unsupported_formats;
}

void Record_Texture_Decode_Failure()
{
	++g_statistics.texture_missing;
	++g_statistics.texture_decode_failures;
}

void Record_Texture_Upload_Failure()
{
	++g_statistics.texture_missing;
	++g_statistics.texture_upload_failures;
}

void Record_Texture_Checkerboard_Fallback()
{
	++g_statistics.texture_checkerboard_fallbacks;
}

void Record_Texture_Upload(uint64_t resident_bytes)
{
	++g_statistics.texture_uploads;
	++g_statistics.texture_resident;
	g_statistics.texture_bytes_resident += resident_bytes;
}

void Record_Texture_Release(uint64_t resident_bytes)
{
	if (g_statistics.texture_resident != 0U) --g_statistics.texture_resident;
	if (resident_bytes <= g_statistics.texture_bytes_resident) {
		g_statistics.texture_bytes_resident -= resident_bytes;
	} else {
		g_statistics.texture_bytes_resident = 0U;
	}
}

bool Bind_Texture(uint32_t native_texture, bool valid)
{
	if (!valid || native_texture == 0U) {
		++g_statistics.texture_invalid_binds;
#if defined(__vita__)
		glDisable(GL_TEXTURE_2D);
#endif
		return false;
	}
	++g_statistics.texture_binds;
#if defined(__vita__)
	glEnable(GL_TEXTURE_2D);
	glBindTexture(GL_TEXTURE_2D, native_texture);
#endif
	return true;
}

bool Configure_Texture_Sampler(uint32_t native_texture, bool valid,
	uint32_t address_u, uint32_t address_v, uint32_t min_filter,
	uint32_t mag_filter, uint32_t mip_filter)
{
	if (!valid || native_texture == 0U) {
		++g_statistics.texture_invalid_binds;
		return false;
	}
	++g_statistics.texture_sampler_updates;
#if defined(__vita__)
	// D3D8's TextureClass owns the state choices.  This narrow translation only
	// maps its established address/filter contract to VitaGL; it does not add a
	// Vita sensitivity, cache, or material policy of its own.
	const GLenum wrap_u = address_u == 3U ? GL_CLAMP_TO_EDGE : GL_REPEAT;
	const GLenum wrap_v = address_v == 3U ? GL_CLAMP_TO_EDGE : GL_REPEAT;
	const bool point_min = min_filter == 1U;
	GLenum native_min = point_min ? GL_NEAREST : GL_LINEAR;
	if (mip_filter == 1U) {
		native_min = point_min ? GL_NEAREST_MIPMAP_NEAREST : GL_LINEAR_MIPMAP_NEAREST;
	} else if (mip_filter == 2U || mip_filter == 3U) {
		native_min = point_min ? GL_NEAREST_MIPMAP_LINEAR : GL_LINEAR_MIPMAP_LINEAR;
	}
	glBindTexture(GL_TEXTURE_2D, native_texture);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap_u);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap_v);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, native_min);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
		mag_filter == 1U ? GL_NEAREST : GL_LINEAR);
	if (glGetError() != GL_NO_ERROR) {
		++g_statistics.backend_errors;
		return false;
	}
#else
	(void)address_u;
	(void)address_v;
	(void)min_filter;
	(void)mag_filter;
	(void)mip_filter;
#endif
	return true;
}

void Record_Texture_Unsupported_Stage(uint32_t stage)
{
	if (stage != 0U) ++g_statistics.texture_unsupported_stages;
}

void Release_Texture(uint32_t native_texture)
{
#if defined(__vita__)
	if (native_texture != 0U) glDeleteTextures(1, &native_texture);
#else
	(void)native_texture;
#endif
}

void Submit_Mesh(MeshClass &mesh, RenderInfoClass &render_info)
{
	MeshModelClass *model = mesh.Peek_Model();
	if (!g_statistics.initialized || model == NULL) {
		return;
	}

	const int vertex_count = model->Get_Vertex_Count();
	const int triangle_count = model->Get_Polygon_Count();
	const Vector3 *vertices = model->Get_Vertex_Array();
	const Vector3 *normals = model->Get_Vertex_Normal_Array();
	const TriIndex *triangles = model->Get_Polygon_Array();
	if (vertices == NULL || triangles == NULL || vertex_count <= 0 || triangle_count <= 0) {
		return;
	}

	++g_statistics.mesh_submissions;
	g_statistics.vertex_submissions += static_cast<uint32_t>(vertex_count);
	g_statistics.triangle_submissions += static_cast<uint32_t>(triangle_count);
	g_statistics.geometry_checksum = Mix_Checksum(g_statistics.geometry_checksum,
		static_cast<uint32_t>(vertex_count));
	g_statistics.geometry_checksum = Mix_Checksum(g_statistics.geometry_checksum,
		static_cast<uint32_t>(triangle_count));
	const int pass_count = model->Get_Pass_Count();
	g_statistics.material_passes +=
		static_cast<uint64_t>(pass_count > 0 ? pass_count : 1);

#if !defined(__vita__)
	// The host target has no Vita framebuffer, but it must still execute the
	// same original material-to-TextureClass boundary as the physical path.
	// This validates archive lookup, DDS decode, upload representation, bind
	// ownership, and repeat lifecycle teardown rather than mistaking a
	// geometry-only headless frame for a textured-frame proof.
	TextureClass *bound_texture = NULL;
	for (int triangle_index = 0; triangle_index < triangle_count; ++triangle_index) {
		TextureClass *texture = model->Peek_Texture(triangle_index, 0, 0);
		if (texture != bound_texture) {
			bound_texture = texture;
			if (bound_texture != NULL) bound_texture->Apply_For_Platform_Boundary(0U);
			else Bind_Texture(0U, false);
		}
	}
#endif

#if defined(__vita__)
	/*
	 * Keep the original object, view, and D3D projection transforms intact
	 * until vitaGL's vertex stage.  The former path called Camera::Project on
	 * the CPU and then submitted divided coordinates under identity matrices;
	 * that discarded homogeneous W and made texture interpolation affine.
	 */
	const Matrix4 world_transform(mesh.Get_Transform());
	const Matrix4 view_transform(render_info.Camera.Get_View_Matrix());
	Matrix4 d3d_projection;
	render_info.Camera.Get_D3D_Projection_Matrix(&d3d_projection);
	const Matrix4 dx8_world = world_transform.Transpose();
	const Matrix4 dx8_view = view_transform.Transpose();
	const Matrix4 dx8_projection = d3d_projection.Transpose();
	IndexedTransformMatrices transform_matrices = {};
	if (!Build_Indexed_Transform_Matrices(&dx8_world[0][0], &dx8_view[0][0],
		&dx8_projection[0][0], transform_matrices)) {
		++g_statistics.backend_errors;
		Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
			"original MeshClass transform conversion failed");
		return;
	}
	glMatrixMode(GL_PROJECTION);
	glLoadMatrixf(transform_matrices.projection);
	glMatrixMode(GL_MODELVIEW);
	glLoadMatrixf(transform_matrices.modelview);
	g_statistics.state_changes += 4U;
	if (!g_logged_first_mesh) {
		Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
			"first original MeshClass submission entry: vertices=%d triangles=%d",
			vertex_count, triangle_count);
	}
	const Vector2 *uvs = model->Get_UV_Array(0, 0);
	TextureClass *bound_texture = NULL;
	unsigned current_shader_bits = 0xffffffffU;
	bool primitive_open = false;
	for (int triangle_index = 0; triangle_index < triangle_count; ++triangle_index) {
		TextureClass *triangle_texture = model->Peek_Texture(triangle_index, 0, 0);
		const ShaderClass triangle_shader = model->Get_Shader(triangle_index, 0);
		const unsigned triangle_shader_bits = triangle_shader.Get_Bits();
		if (triangle_texture != bound_texture ||
			triangle_shader_bits != current_shader_bits || !primitive_open) {
			if (primitive_open) glEnd();
			bound_texture = triangle_texture;
			current_shader_bits = triangle_shader_bits;
			// ShaderClass remains the authoritative original material policy.
			// Translate only the fixed-function state VitaGL exposes here; this
			// preserves alpha-cutout, conventional transparency and additive fire.
			Apply_Original_Shader_State(triangle_shader);
			if (bound_texture != NULL) {
				// Retain TextureClass as the resource/lifetime owner and invoke its
				// original filter, mip, wrap, and bind sequence through the narrow
				// platform bridge.
				bound_texture->Apply_For_Platform_Boundary(0U);
			} else {
				Bind_Texture(0U, false);
			}
			glBegin(GL_TRIANGLES);
			primitive_open = true;
		}
		const TriIndex &triangle = triangles[triangle_index];
		unsigned vertex_indices[3] = {
			static_cast<unsigned>(vertex_count), static_cast<unsigned>(vertex_count),
			static_cast<unsigned>(vertex_count)
		};
		for (int corner = 0; corner < 3; ++corner) {
			const unsigned vertex_index = triangle[corner];
			if (vertex_index >= static_cast<unsigned>(vertex_count)) {
				vertex_indices[corner] = static_cast<unsigned>(vertex_count);
				break;
			}
			vertex_indices[corner] = vertex_index;
		}
		if (vertex_indices[0] >= static_cast<unsigned>(vertex_count) ||
			vertex_indices[1] >= static_cast<unsigned>(vertex_count) ||
			vertex_indices[2] >= static_cast<unsigned>(vertex_count)) {
			continue;
		}
		for (int corner = 0; corner < 3; ++corner) {
			const unsigned vertex_index = vertex_indices[corner];
			if (uvs != NULL && bound_texture != NULL) {
				// DDS source rows are flipped at upload to retain original D3D
				// UV semantics without changing engine-owned coordinates.
				glTexCoord2f(uvs[vertex_index].X, uvs[vertex_index].Y);
			}
			if (normals != NULL) {
				const Vector3 &normal = normals[vertex_index];
				glColor3f(0.35f + 0.35f * (normal.X + 1.0f) * 0.5f,
					0.45f + 0.35f * (normal.Y + 1.0f) * 0.5f,
					0.50f + 0.35f * (normal.Z + 1.0f) * 0.5f);
			} else {
				glColor3f(0.65f, 0.72f, 0.78f);
			}
			glVertex3f(vertices[vertex_index].X, vertices[vertex_index].Y,
				vertices[vertex_index].Z);
		}
	}
	if (primitive_open) glEnd();
	// Submit_Indexed_Triangles may be used later in the same frame by HUD or
	// native DX8 boundary callers. Restore its explicit identity baseline only
	// after this homogeneous mesh submission is complete.
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	g_statistics.state_changes += 4U;
	if (!g_logged_first_mesh) {
		const GLenum error = glGetError();
		Vita_Append_A22_Runtime_Breadcrumb("mesh-submit",
			"first original MeshClass submission return: glGetError=%08X",
			static_cast<unsigned>(error));
		g_logged_first_mesh = true;
	}
#else
	(void)render_info;
#endif
}

IndexedSubmissionResult Submit_Indexed_Triangles(
	const IndexedTriangleSubmission &submission)
{
	if (!g_statistics.initialized) {
		++g_statistics.rejected_indexed_submissions;
		Log_Indexed_Rejection("renderer is not initialized", submission.vertex_format);
		return INDEXED_SUBMISSION_NOT_INITIALIZED;
	}

	const uint32_t mesh_fvf = 0x00000152U; // XYZ | NORMAL | DIFFUSE | TEX1
	const uint32_t render2d_fvf = 0x00000252U; // legacy dynamic XYZ | N | D | TEX2
	const bool mesh_layout = submission.vertex_format == mesh_fvf &&
		submission.vertex_stride == 36U;
	const bool render2d_layout = submission.vertex_format == render2d_fvf &&
		submission.vertex_stride == 44U;
	if (!mesh_layout && !render2d_layout) {
		++g_statistics.unsupported_submissions;
		++g_statistics.rejected_indexed_submissions;
		static bool logged_rejected_layout = false;
		if (!logged_rejected_layout) {
			fprintf(stderr, "A4 indexed layout rejected: fvf=%08X stride=%u mesh=%d render2d=%d\n",
				submission.vertex_format, submission.vertex_stride,
				mesh_layout ? 1 : 0, render2d_layout ? 1 : 0);
			logged_rejected_layout = true;
		}
		Log_Indexed_Rejection("unsupported FVF/stride", submission.vertex_format);
		return INDEXED_SUBMISSION_UNSUPPORTED_FVF;
	}
	if (submission.vertex_data == NULL || submission.index_data == NULL ||
		submission.triangle_count == 0U || submission.vertex_count == 0U ||
		submission.vertex_stride == 0U ||
		submission.vertex_capacity > submission.vertex_data_size / submission.vertex_stride) {
		++g_statistics.rejected_indexed_submissions;
		Log_Indexed_Rejection("invalid buffer view", submission.vertex_format);
		return INDEXED_SUBMISSION_INVALID_ARGUMENT;
	}

	const uint32_t requested_indices = submission.triangle_count * 3U;
	if (submission.triangle_count > 0xffffffffU / 3U ||
		submission.first_index > submission.index_capacity ||
		requested_indices > submission.index_capacity - submission.first_index) {
		++g_statistics.rejected_indexed_submissions;
		Log_Indexed_Rejection("index buffer range", submission.vertex_format);
		return INDEXED_SUBMISSION_INDEX_RANGE_ERROR;
	}
	if (submission.min_vertex_index > 0xffffffffU - submission.vertex_count ||
		submission.base_vertex_index > submission.vertex_capacity) {
		++g_statistics.rejected_indexed_submissions;
		Log_Indexed_Rejection("declared vertex range", submission.vertex_format);
		return INDEXED_SUBMISSION_VERTEX_RANGE_ERROR;
	}

	const uint32_t declared_end = submission.min_vertex_index + submission.vertex_count;
	for (uint32_t offset = 0; offset < requested_indices; ++offset) {
		const uint32_t relative_index =
			submission.index_data[submission.first_index + offset];
		if (relative_index < submission.min_vertex_index || relative_index >= declared_end ||
			relative_index > 0xffffffffU - submission.base_vertex_index ||
			submission.base_vertex_index + relative_index >= submission.vertex_capacity) {
			++g_statistics.rejected_indexed_submissions;
			Log_Indexed_Rejection("referenced vertex range", submission.vertex_format);
			return INDEXED_SUBMISSION_VERTEX_RANGE_ERROR;
		}
	}
	IndexedTransformMatrices transform_matrices = {};
	if (!Build_Indexed_Transform_Matrices(submission.world_transform,
		submission.view_transform, submission.projection_transform,
		transform_matrices)) {
		++g_statistics.rejected_indexed_submissions;
		Log_Indexed_Rejection("world/view/projection transform unavailable",
			submission.vertex_format);
		return INDEXED_SUBMISSION_MISSING_TRANSFORM;
	}

	uint32_t checksum = g_statistics.indexed_geometry_checksum;
	checksum = Mix_Checksum(checksum, submission.vertex_format);
	checksum = Mix_Checksum(checksum, submission.vertex_stride);
	checksum = Mix_Checksum(checksum, submission.first_index);
	checksum = Mix_Checksum(checksum, submission.triangle_count);
	checksum = Mix_Checksum(checksum, submission.base_vertex_index);
	checksum = Mix_Checksum(checksum, submission.min_vertex_index);
	checksum = Mix_Checksum(checksum, submission.vertex_count);

	for (uint32_t offset = 0; offset < requested_indices; ++offset) {
		const uint32_t relative_index =
			submission.index_data[submission.first_index + offset];
		const uint32_t actual_index = submission.base_vertex_index + relative_index;
		const unsigned char *vertex = submission.vertex_data +
			actual_index * submission.vertex_stride;
		float position[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
		uint32_t diffuse = 0;
		memcpy(position, vertex, 3U * sizeof(float));
		const uint32_t diffuse_offset = 24U;
		memcpy(&diffuse, vertex + diffuse_offset, sizeof(diffuse));

		checksum = Mix_Checksum(checksum, relative_index);
		checksum = Mix_Checksum(checksum, actual_index);
		checksum = Mix_Checksum(checksum, Float_Bits(position[0]));
		checksum = Mix_Checksum(checksum, Float_Bits(position[1]));
		checksum = Mix_Checksum(checksum, Float_Bits(position[2]));
		checksum = Mix_Checksum(checksum, diffuse);
	}

#if defined(__vita__)
	// Let vitaGL's fixed-function vertex shader retain homogeneous W through
	// clipping and interpolation.  CPU-dividing to NDC here would turn W into
	// one, incorrectly draw behind-camera geometry and make UVs affine.
	glMatrixMode(GL_PROJECTION);
	glLoadMatrixf(transform_matrices.projection);
	glMatrixMode(GL_MODELVIEW);
	glLoadMatrixf(transform_matrices.modelview);

	glBegin(GL_TRIANGLES);
	for (uint32_t triangle = 0; triangle < submission.triangle_count; ++triangle) {
		for (uint32_t corner = 0; corner < 3U; ++corner) {
			const uint32_t index_offset = triangle * 3U + corner;
			const uint32_t relative_index = submission.index_data[
				submission.first_index + index_offset];
			const uint32_t actual_index = submission.base_vertex_index + relative_index;
			const unsigned char *vertex = submission.vertex_data +
				actual_index * submission.vertex_stride;
			float position[3];
			float uv[2];
			uint32_t diffuse = 0;
			memcpy(position, vertex, 3U * sizeof(float));
			/* Render2D's original dynamic FVF retains a second UV slot after
			 * the populated first UV. Its leading position/normal/diffuse
			 * layout is therefore identical to the mesh layout. */
			const uint32_t diffuse_offset = 24U;
			const uint32_t uv_offset = 28U;
			memcpy(&diffuse, vertex + diffuse_offset, sizeof(diffuse));
			memcpy(uv, vertex + uv_offset, 2U * sizeof(float));
			glColor4ub(static_cast<GLubyte>((diffuse >> 16U) & 0xffU),
				static_cast<GLubyte>((diffuse >> 8U) & 0xffU),
				static_cast<GLubyte>(diffuse & 0xffU),
				static_cast<GLubyte>((diffuse >> 24U) & 0xffU));
			if (mesh_layout || render2d_layout) {
				float normal[3];
				memcpy(normal, vertex + 12U, 3U * sizeof(float));
				glNormal3f(normal[0], normal[1], normal[2]);
			} else {
				glNormal3f(0.0f, 0.0f, 1.0f);
			}
			glTexCoord2f(uv[0], uv[1]);
			glVertex3f(position[0], position[1], position[2]);
		}
	}
	glEnd();
	const uint32_t emitted_triangles = submission.triangle_count;

	// The accepted A2.2 Submit_Mesh path emits already-projected coordinates
	// and deliberately remains unchanged.  Restore its identity convention in
	// case both original paths are traversed within one diagnostic frame.
	glMatrixMode(GL_PROJECTION);
	glLoadIdentity();
	glMatrixMode(GL_MODELVIEW);
	glLoadIdentity();
	g_statistics.state_changes += 4U;
#endif

	++g_statistics.indexed_submissions;
	++g_statistics.material_passes;
	g_statistics.indexed_vertex_references += requested_indices;
	g_statistics.indexed_triangle_submissions += submission.triangle_count;
	g_statistics.indexed_geometry_checksum = checksum;

#if defined(__vita__)
	static bool logged_first_indexed_submission = false;
	if (!logged_first_indexed_submission) {
		const GLenum error = glGetError();
		Vita_Append_A22_Runtime_Breadcrumb("indexed-submit",
			"first original DX8Wrapper indexed draw: fvf=%08X stride=%u first=%u triangles=%u emitted=%u base=%u min=%u vertices=%u checksum=%08X glGetError=%08X",
			submission.vertex_format, submission.vertex_stride,
			submission.first_index, submission.triangle_count,
			emitted_triangles,
			submission.base_vertex_index, submission.min_vertex_index,
			submission.vertex_count, checksum, static_cast<unsigned>(error));
		logged_first_indexed_submission = true;
	}
#endif
	return INDEXED_SUBMISSION_OK;
}

void Reject_Indexed_Submission(const char *reason, uint32_t vertex_format)
{
	++g_statistics.unsupported_submissions;
	++g_statistics.rejected_indexed_submissions;
	Log_Indexed_Rejection(reason, vertex_format);
}

void Submit_Unsupported(RenderObjClass *object)
{
	++g_statistics.unsupported_submissions;
	if (!g_logged_first_unsupported) {
		const char *name = object != NULL ? object->Get_Name() : "(null)";
		const int class_id = object != NULL ? object->Class_ID() : -1;
#if defined(__vita__)
		Vita_Append_A22_Runtime_Breadcrumb("unsupported-submit",
			"first unsupported RenderObj: name=%s class_id=%d",
			name != NULL ? name : "(null)", class_id);
#else
		fprintf(stderr, "A2.2 first unsupported RenderObj: name=%s class_id=%d\n",
			name != NULL ? name : "(null)", class_id);
#endif
		g_logged_first_unsupported = true;
	}
}

void Submit_Decals_Unsupported()
{
	++g_statistics.unsupported_submissions;
	if (!g_logged_first_unsupported) {
#if defined(__vita__)
		Vita_Append_A22_Runtime_Breadcrumb("unsupported-submit",
			"first unsupported operation: decal mesh render");
#else
		fprintf(stderr, "A2.2 first unsupported operation: decal mesh render\n");
#endif
		g_logged_first_unsupported = true;
	}
}

bool Capture_Resolved_Frame_RGBA(uint8_t *output, size_t output_bytes)
{
	const size_t required = static_cast<size_t>(DISPLAY_WIDTH) *
		static_cast<size_t>(DISPLAY_HEIGHT) * 4U;
	if (!g_statistics.initialized || output == NULL || output_bytes < required) {
		return false;
	}
#if defined(__vita__)
	(void)glGetError();
	/* vglReadPixels performs GPU-backed readback of the active resolved color
	** target. The runtime invokes this after original WW3D traversal and before
	** the swap, so the clean image is exactly the frame about to be presented. */
	vglReadPixels(0, 0, static_cast<GLsizei>(DISPLAY_WIDTH),
		static_cast<GLsizei>(DISPLAY_HEIGHT), GL_RGBA, GL_UNSIGNED_BYTE, output);
	const GLenum error = glGetError();
	if (error != GL_NO_ERROR) {
		++g_statistics.backend_errors;
		return false;
	}
#else
	memset(output, 0, required);
#endif
	return true;
}

bool Query_Backend_Memory(BackendMemoryStatistics &memory)
{
	memory = {};
#if defined(__vita__)
	SceKernelFreeMemorySizeInfo system = {};
	system.size = sizeof(system);
	if (sceKernelGetFreeMemorySize(&system) < 0) {
		return false;
	}
	memory.available = true;
	memory.system_user_free = system.size_user;
	memory.system_cdram_free = system.size_cdram;
	memory.system_phycont_free = system.size_phycont;
	memory.ram_total = vglMemTotal(VGL_MEM_RAM);
	memory.ram_free = vglMemFree(VGL_MEM_RAM);
	memory.vram_total = vglMemTotal(VGL_MEM_VRAM);
	memory.vram_free = vglMemFree(VGL_MEM_VRAM);
	memory.slow_total = vglMemTotal(VGL_MEM_SLOW);
	memory.slow_free = vglMemFree(VGL_MEM_SLOW);
	memory.all_total = vglMemTotal(VGL_MEM_ALL);
	memory.all_free = vglMemFree(VGL_MEM_ALL);
#endif
	return memory.available;
}

void Reset_Statistics()
{
	const bool initialized = g_statistics.initialized;
	g_statistics = {};
	g_statistics.initialized = initialized;
	g_logged_first_unsupported = false;
	g_logged_first_indexed_rejection = false;
}

const Statistics &Get_Statistics()
{
	return g_statistics;
}

const BackendLifecycleStatistics &Get_Backend_Lifecycle_Statistics()
{
	return g_lifecycle;
}

} // namespace RenegadeVitaRenderer
