// Fake GL models object-owned sampler parameters, stage-owned bindings and
// unit-owned texture environments. The test driver inserts the actual
// production functions, including __vita__.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <string>

using GLenum = unsigned;
using GLint = int;
using GLuint = unsigned;
using GLfloat = float;
enum : unsigned {
	GL_NO_ERROR, GL_TEXTURE0 = 100, GL_TEXTURE_2D = 200,
	GL_CLAMP_TO_EDGE, GL_REPEAT, GL_NEAREST, GL_LINEAR,
	GL_NEAREST_MIPMAP_NEAREST, GL_LINEAR_MIPMAP_NEAREST,
	GL_NEAREST_MIPMAP_LINEAR, GL_LINEAR_MIPMAP_LINEAR,
	GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_TEXTURE_MIN_FILTER,
	GL_TEXTURE_MAG_FILTER,
	GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_TEXTURE_ENV_COLOR,
	GL_COMBINE_RGB, GL_SRC0_RGB, GL_SRC1_RGB, GL_SRC2_RGB,
	GL_OPERAND0_RGB, GL_OPERAND1_RGB, GL_OPERAND2_RGB,
	GL_COMBINE_ALPHA, GL_SRC0_ALPHA, GL_SRC1_ALPHA, GL_SRC2_ALPHA,
	GL_OPERAND0_ALPHA, GL_OPERAND1_ALPHA, GL_OPERAND2_ALPHA,
	GL_COMBINE, GL_REPLACE, GL_MODULATE, GL_ADD, GL_INTERPOLATE, GL_SUBTRACT,
	GL_SRC_COLOR, GL_SRC_ALPHA, GL_CONSTANT, GL_PREVIOUS, GL_TEXTURE,
	GL_PRIMARY_COLOR
};
enum : unsigned {
	D3DTOP_DISABLE = 1, D3DTOP_SELECTARG1 = 2, D3DTOP_SELECTARG2 = 3,
	D3DTOP_MODULATE = 4, D3DTOP_ADD = 7, D3DTOP_SUBTRACT = 10,
	D3DTOP_ADDSMOOTH = 11, D3DTOP_BLENDTEXTUREALPHA = 13,
	D3DTOP_BLENDCURRENTALPHA = 16,
	D3DTA_DIFFUSE = 0, D3DTA_CURRENT = 1, D3DTA_TEXTURE = 2
};
struct MeshMatDescClass { static const unsigned MAX_TEX_STAGES = 2; };

enum { NAMES = 16, ENV_NAMES = 256 };
struct Texture { unsigned u, v, min, mag; bool live; };
Texture textures[NAMES] = {};
unsigned bindings[2] = {};
bool unit_enabled[2] = {};
GLint unit_env[2][ENV_NAMES] = {};
bool unit_env_color[2] = {};
unsigned active_stage = 0, bind_calls = 0, parameter_calls = 0, env_calls = 0;
unsigned pending_error = 0;
bool fail_parameter = false;
struct {
	unsigned texture_stage_enable_skips, state_changes, texture_invalid_binds;
	unsigned texture_bind_skips, texture_binds, texture_sampler_skips;
	unsigned texture_sampler_updates, backend_errors, texture_unsupported_stages;
	unsigned texture_sampler_parameter_writes, texture_combiner_skips;
} g_statistics = {};
bool g_logged_first_state_cache_skip = false;
void Vita_Append_A22_Runtime_Breadcrumb(const char *, const char *, ...) {}
void Record_Texture_Unsupported_Stage(unsigned) { ++g_statistics.texture_unsupported_stages; }
void Invalidate_Original_Shader_State_Cache() {}
void glActiveTexture(unsigned unit) { active_stage = unit - GL_TEXTURE0; assert(active_stage < 2); }
void glEnable(unsigned cap) { assert(cap == GL_TEXTURE_2D); unit_enabled[active_stage] = true; }
void glDisable(unsigned cap) { assert(cap == GL_TEXTURE_2D); unit_enabled[active_stage] = false; }
void glBindTexture(unsigned, unsigned texture) {
	assert(texture < NAMES);
	bindings[active_stage] = texture;
	++bind_calls;
}
void glTexParameteri(unsigned, unsigned key, unsigned value) {
	++parameter_calls;
	if (fail_parameter) { fail_parameter = false; pending_error = 1; return; }
	Texture &texture = textures[bindings[active_stage]];
	if (key == GL_TEXTURE_WRAP_S) texture.u = value;
	if (key == GL_TEXTURE_WRAP_T) texture.v = value;
	if (key == GL_TEXTURE_MIN_FILTER) texture.min = value;
	if (key == GL_TEXTURE_MAG_FILTER) texture.mag = value;
}
void glTexEnvi(unsigned target, unsigned name, GLint value) {
	assert(target == GL_TEXTURE_ENV && name < ENV_NAMES);
	unit_env[active_stage][name] = value;
	++env_calls;
}
void glTexEnvfv(unsigned target, unsigned name, GLfloat *value) {
	assert(target == GL_TEXTURE_ENV && name == GL_TEXTURE_ENV_COLOR);
	unit_env_color[active_stage] = value[0] == 1.0f && value[1] == 1.0f &&
		value[2] == 1.0f && value[3] == 1.0f;
	++env_calls;
}
unsigned glGetError() { unsigned error = pending_error; pending_error = 0; return error; }
// vitaGL hands out the lowest free name with LINEAR/REPEAT defaults.
void glGenTextures(unsigned count, unsigned *ids) {
	for (unsigned i = 0; i < count; ++i) {
		ids[i] = 0;
		for (unsigned name = 1; name < NAMES; ++name) {
			if (!textures[name].live) {
				textures[name] = { GL_REPEAT, GL_REPEAT, GL_LINEAR, GL_LINEAR, true };
				ids[i] = name;
				break;
			}
		}
	}
}
void glDeleteTextures(unsigned count, const unsigned *ids) {
	for (unsigned i = 0; i < count; ++i) {
		textures[ids[i]] = {};
		for (unsigned &binding : bindings) if (binding == ids[i]) binding = 0;
	}
}
bool Bind_Texture_Stage(uint32_t, uint32_t, bool);
bool Configure_Texture_Sampler_Stage(uint32_t, uint32_t, bool,
	uint32_t, uint32_t, uint32_t, uint32_t, uint32_t);
void Begin_Texture_Sampler_Batch();
void End_Texture_Sampler_Batch();
void Release_Texture(uint32_t);

#include "sampler-production.inc"

bool configure(unsigned stage, unsigned texture, unsigned address = 1,
	unsigned min = 2, unsigned mip = 0) {
	return Configure_Texture_Sampler_Stage(stage, texture, true,
		address, address, min, 2, mip);
}

// --- Randomized equivalence -------------------------------------------------

struct SamplerRequest { unsigned u, v, min, mag, mip; };
struct Expected { unsigned u, v, min, mag; };
uint64_t rng_state = 1;
unsigned rnd(unsigned bound) {
	rng_state ^= rng_state << 13; rng_state ^= rng_state >> 7; rng_state ^= rng_state << 17;
	return static_cast<unsigned>(rng_state % bound);
}
// Immediate-semantics oracle for binding, enable and object parameters.
std::map<unsigned, Expected> expected_params;
unsigned expected_binding[2] = {};
bool expected_enabled[2] = {};
Expected Translate(const SamplerRequest &r) {
	Expected e;
	e.u = r.u == 3U ? GL_CLAMP_TO_EDGE : GL_REPEAT;
	e.v = r.v == 3U ? GL_CLAMP_TO_EDGE : GL_REPEAT;
	const bool point = r.min == 1U;
	e.min = point ? GL_NEAREST : GL_LINEAR;
	if (r.mip == 1U) e.min = point ? GL_NEAREST_MIPMAP_NEAREST : GL_LINEAR_MIPMAP_NEAREST;
	else if (r.mip == 2U || r.mip == 3U) e.min = point ? GL_NEAREST_MIPMAP_LINEAR : GL_LINEAR_MIPMAP_LINEAR;
	e.mag = r.mag == 1U ? GL_NEAREST : GL_LINEAR;
	return e;
}
SamplerRequest random_request() {
	return { 1U + rnd(3U), 1U + rnd(3U), 1U + rnd(2U), 1U + rnd(2U), rnd(4U) };
}
void oracle_configure(unsigned stage, unsigned texture, const SamplerRequest &r) {
	expected_params[texture] = Translate(r);
	expected_binding[stage] = texture;
}
void oracle_bind(unsigned stage, unsigned texture) {
	expected_binding[stage] = texture;
	expected_enabled[stage] = true;
}
void oracle_release(unsigned texture) {
	expected_params.erase(texture);
	for (unsigned &binding : expected_binding) if (binding == texture) binding = 0;
}
unsigned live_textures[NAMES] = {};
unsigned live_count = 0;
SamplerRequest stage_request[2] = { { 1, 1, 2, 2, 0 }, { 1, 1, 2, 2, 0 } };
SamplerRequest own_request[NAMES] = {};
uint32_t trace = 2166136261U;
unsigned draws = 0;
void mix(uint32_t value) { trace = (trace ^ value) * 16777619U; }

void upload_new() {
	// Mirrors the DX8 boundary creation sequence (active unit 0).
	unsigned name = 0;
	glGenTextures(1, &name);
	if (name == 0) return;
	glBindTexture(GL_TEXTURE_2D, name);
	Invalidate_Texture_State_Cache();
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	expected_params[name] = { GL_REPEAT, GL_REPEAT, GL_LINEAR, GL_LINEAR };
	expected_binding[0] = name;
	live_textures[live_count++] = name;
	own_request[name] = random_request();
}
void reupload(unsigned name) {
	glBindTexture(GL_TEXTURE_2D, name);
	Invalidate_Texture_State_Cache();
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
	expected_params[name] = { GL_REPEAT, GL_REPEAT, GL_LINEAR_MIPMAP_LINEAR, GL_LINEAR };
	expected_binding[0] = name;
}
void release(unsigned index) {
	const unsigned name = live_textures[index];
	live_textures[index] = live_textures[--live_count];
	Release_Texture(name);
	oracle_release(name);
}
void random_combiner(unsigned stage, bool enabled) {
	static const unsigned ops[] = { D3DTOP_DISABLE, D3DTOP_SELECTARG1, D3DTOP_SELECTARG2,
		D3DTOP_MODULATE, D3DTOP_ADD, D3DTOP_SUBTRACT, D3DTOP_ADDSMOOTH,
		D3DTOP_BLENDTEXTUREALPHA, D3DTOP_BLENDCURRENTALPHA };
	static const unsigned args[] = { D3DTA_DIFFUSE, D3DTA_CURRENT, D3DTA_TEXTURE };
	// Few distinct states, so caches both hit and miss.
	const unsigned color = rnd(3U) ? ops[rnd(4U)] : ops[rnd(9U)];
	const unsigned alpha = rnd(3U) ? ops[rnd(4U)] : ops[rnd(9U)];
	Apply_DX8_Texture_Stage_State(stage, color, args[2], args[rnd(2U)],
		alpha, args[2], args[rnd(3U)], enabled);
	expected_enabled[stage] = enabled;
}
// Mirrors the texture part of Apply_Original_Shader_State.
void shader_env_mode() {
	static const GLint modes[] = { GL_REPLACE, GL_ADD, GL_MODULATE };
	const bool texturing = rnd(4U) != 0U;
	glActiveTexture(GL_TEXTURE0);
	if (texturing) {
		glEnable(GL_TEXTURE_2D);
		Set_Texture_Env(0U, GL_TEXTURE_ENV_MODE, modes[rnd(3U)]);
	} else {
		glDisable(GL_TEXTURE_2D);
		Set_Texture_Env(0U, GL_TEXTURE_ENV_MODE, GL_MODULATE);
	}
	g_texture_stage_cache[0].enabled_known = true;
	g_texture_stage_cache[0].enabled = texturing;
	g_texture_stage_cache[0].combiner_known = false;
	expected_enabled[0] = texturing;
}
// One original TextureClass::Apply as the DX8 boundary sees it.
bool use_batches = true;
void apply_texture(unsigned stage, unsigned name) {
	if (use_batches) Begin_Texture_Sampler_Batch();
	assert(Bind_Texture_Stage(stage, name, true));
	oracle_bind(stage, name);
	Configure_Texture_Sampler_Stage(stage, name, true, stage_request[stage].u,
		stage_request[stage].v, stage_request[stage].min, stage_request[stage].mag,
		stage_request[stage].mip);
	oracle_configure(stage, name, stage_request[stage]);
	random_combiner(stage, true);
	unsigned *own = &own_request[name].u, *current = &stage_request[stage].u;
	for (unsigned field = 0; field < 5U; ++field) {
		if (rnd(16U) == 0U) {
			// Perturbations the batch must order correctly.
			const unsigned kind = rnd(4U);
			if (kind == 3U && live_count > 1U) {
				// A request for an object this stage does not bind yet.
				const unsigned other = live_textures[rnd(live_count)];
				if (other != name) {
					const SamplerRequest request = random_request();
					Configure_Texture_Sampler_Stage(stage, other, true, request.u,
						request.v, request.min, request.mag, request.mip);
					oracle_configure(stage, other, request);
					Bind_Texture_Stage(stage, name, true);
					oracle_bind(stage, name);
				}
			} else if (kind == 0U) {
				const unsigned other_stage = stage ^ 1U;
				const SamplerRequest request = random_request();
				Bind_Texture_Stage(other_stage, name, true);
				oracle_bind(other_stage, name);
				Configure_Texture_Sampler_Stage(other_stage, name, true, request.u,
					request.v, request.min, request.mag, request.mip);
				oracle_configure(other_stage, name, request);
				stage_request[other_stage] = request;
			} else if (kind == 1U && live_count > 1U) {
				unsigned other = live_textures[rnd(live_count)];
				if (other != name) {
					Bind_Texture_Stage(stage, other, true);
					oracle_bind(stage, other);
					if (rnd(2U) == 0U) {
						// The stage leaves the pending object behind.
						if (use_batches) End_Texture_Sampler_Batch();
						return;
					}
					Bind_Texture_Stage(stage, name, true);
					oracle_bind(stage, name);
				}
			} else {
				for (unsigned index = 0; index < live_count; ++index) {
					if (live_textures[index] == name) { release(index); break; }
				}
				if (use_batches) End_Texture_Sampler_Batch();
				return;
			}
		}
		const unsigned order = (field + rnd(5U)) % 5U;
		if (current[order] == own[order]) continue;
		current[order] = own[order];
		Configure_Texture_Sampler_Stage(stage, name, true, stage_request[stage].u,
			stage_request[stage].v, stage_request[stage].min, stage_request[stage].mag,
			stage_request[stage].mip);
		oracle_configure(stage, name, stage_request[stage]);
	}
	if (use_batches) End_Texture_Sampler_Batch();
}
void draw() {
	++draws;
	assert(active_stage == 0);
	for (unsigned stage = 0; stage < 2; ++stage) {
		assert(unit_enabled[stage] == expected_enabled[stage]);
		mix(unit_enabled[stage]);
		if (!unit_enabled[stage]) continue;
		assert(bindings[stage] == expected_binding[stage]);
		mix(bindings[stage]);
		if (bindings[stage] == 0U) continue;
		const Texture &t = textures[bindings[stage]];
		const auto found = expected_params.find(bindings[stage]);
		assert(found != expected_params.end());
		assert(t.u == found->second.u && t.v == found->second.v &&
			t.min == found->second.min && t.mag == found->second.mag);
		for (unsigned value : { t.u, t.v, t.min, t.mag }) mix(value);
	}
	// Every live object, bound or not, and every unit environment.
	for (unsigned name = 1; name < NAMES; ++name) {
		const Texture &t = textures[name];
		for (unsigned value : { t.u, t.v, t.min, t.mag, unsigned(t.live) }) mix(value);
	}
	for (unsigned stage = 0; stage < 2; ++stage) {
		for (unsigned name = 0; name < ENV_NAMES; ++name) mix(static_cast<uint32_t>(unit_env[stage][name]));
		mix(unit_env_color[stage]);
	}
}

int run_random(unsigned seed) {
	rng_state = 0x9E3779B97F4A7C15ULL ^ (static_cast<uint64_t>(seed) * 0x100000001B3ULL);
	for (unsigned i = 0; i < 4; ++i) upload_new();
	for (unsigned step = 0; step < 600; ++step) {
		const unsigned op = rnd(100U);
		if (op < 40U && live_count != 0U) {
			apply_texture(rnd(2U), live_textures[rnd(live_count)]);
		} else if (op < 50U) {
			random_combiner(rnd(2U), rnd(4U) != 0U);
		} else if (op < 58U) {
			shader_env_mode();
		} else if (op < 62U) {
			const unsigned stage = rnd(2U);
			Disable_Texture_Stage(stage);
			expected_enabled[stage] = false;
		} else if (op < 66U && live_count < NAMES - 2U) {
			upload_new();
		} else if (op < 69U && live_count != 0U) {
			reupload(live_textures[rnd(live_count)]);
		} else if (op < 73U && live_count > 1U) {
			release(rnd(live_count));
		} else if (op < 75U) {
			Invalidate_Texture_State_Cache();
		} else {
			draw();
		}
	}
	std::printf("random seed=%u draws=%u trace=%08X parameter_calls=%u env_calls=%u bind_calls=%u\n",
		seed, draws, trace, parameter_calls, env_calls, bind_calls);
	return 0;
}

int main(int argc, char **argv) {
	assert(argc >= 2 && argc <= 4);
	if (argc >= 3) {
		// "1n": cache bit set, TextureClass applies not bracketed by a batch.
		assert(!std::strcmp(argv[2], "0") || !std::strcmp(argv[2], "1") ||
			!std::strcmp(argv[2], "1n"));
		g_render_work_cache_mode = argv[2][0] == '1' ? 1U : 0U;
		use_batches = std::strcmp(argv[2], "1n") != 0;
	}
	const char *test = argv[1];
	if (!std::strcmp(test, "random")) {
		assert(argc == 4);
		return run_random(static_cast<unsigned>(std::atoi(argv[3])));
	}
	for (unsigned name = 1; name < NAMES; ++name) textures[name].live = true;
	if (!std::strcmp(test, "shared-object")) {
		assert(configure(0, 1, 1));
		assert(configure(1, 1, 3));
		assert(textures[1].u == GL_CLAMP_TO_EDGE);
		assert(configure(0, 1, 1));
		assert(textures[1].u == GL_REPEAT);
		assert(parameter_calls == (g_render_work_cache_mode ? 8U : 12U));
	} else if (!std::strcmp(test, "binding-restoration")) {
		assert(configure(0, 1));
		assert(Bind_Texture_Stage(0, 2, true));
		assert(configure(0, 1));
		assert(bindings[0] == 1);
	} else if (!std::strcmp(test, "redundant-bind")) {
		assert(Bind_Texture_Stage(0, 1, true));
		assert(configure(0, 1));
		assert(bind_calls == 1);
		assert(g_statistics.texture_binds == bind_calls);
		assert(configure(0, 1));
		assert(parameter_calls == 4);
		assert(g_statistics.texture_sampler_skips == 1);
	} else if (!std::strcmp(test, "failed-write")) {
		fail_parameter = true;
		assert(!configure(0, 1, 3));
		assert(configure(0, 1, 3));
		assert(textures[1].u == GL_CLAMP_TO_EDGE);
		assert(parameter_calls == 8);
		assert(g_statistics.backend_errors == 1);
	} else if (!std::strcmp(test, "failed-alias-write")) {
		assert(configure(0, 1));
		fail_parameter = true;
		assert(!configure(1, 1, 3));
		assert(configure(0, 1));
		assert(textures[1].u == GL_REPEAT && textures[1].v == GL_REPEAT);
	} else if (!std::strcmp(test, "unrelated-object")) {
		assert(configure(0, 1));
		assert(configure(1, 2, 3));
		assert(configure(0, 1));
		assert(parameter_calls == 8);
	} else if (!std::strcmp(test, "delete-reuse")) {
		assert(configure(0, 1));
		Release_Texture(1);
		assert(configure(0, 1));
		assert(textures[1].u == GL_REPEAT);
		assert(bindings[0] == 1 && parameter_calls == 8);
	} else if (!std::strcmp(test, "external-invalidation")) {
		assert(configure(0, 1));
		textures[1].u = GL_CLAMP_TO_EDGE;
		Invalidate_Texture_State_Cache();
		assert(configure(0, 1));
		assert(textures[1].u == GL_REPEAT && parameter_calls == 8);
	} else if (!std::strcmp(test, "invalid-stage")) {
		assert(!configure(2, 1));
		assert(!configure(0, 0));
		assert(!Configure_Texture_Sampler_Stage(0, 1, false, 1, 1, 2, 2, 0));
		assert(bind_calls == 0 && parameter_calls == 0);
	} else if (!std::strcmp(test, "filter-translation")) {
		assert(configure(1, 1, 3, 1, 1));
		assert(textures[1].min == GL_NEAREST_MIPMAP_NEAREST);
		assert(configure(1, 1, 1, 2, 2));
		assert(textures[1].min == GL_LINEAR_MIPMAP_LINEAR);
		assert(active_stage == 0);
	} else if (!std::strcmp(test, "batch-final-request")) {
		// TextureClass::Apply: bind, previous stage state, then field updates.
		assert(Bind_Texture_Stage(0, 1, true));
		assert(configure(0, 1, 1));
		const unsigned base = parameter_calls;
		assert(Bind_Texture_Stage(0, 2, true));
		assert(configure(0, 2, 3));
		assert(textures[2].u == GL_CLAMP_TO_EDGE);
		const unsigned before = parameter_calls;
		Begin_Texture_Sampler_Batch();
		assert(Bind_Texture_Stage(0, 1, true));
		assert(configure(0, 1, 3));               // stale stage request
		assert(Configure_Texture_Sampler_Stage(0, 1, true, 1, 3, 2, 2, 0));
		assert(configure(0, 1, 1));               // object's own final request
		if (g_render_work_cache_mode) assert(parameter_calls == before);
		End_Texture_Sampler_Batch();
		assert(bindings[0] == 1 && active_stage == 0);
		assert(textures[1].u == GL_REPEAT && textures[1].v == GL_REPEAT);
		assert(textures[2].u == GL_CLAMP_TO_EDGE);
		if (g_render_work_cache_mode) assert(parameter_calls == before);
		else assert(parameter_calls > before && base > 0);
	} else if (!std::strcmp(test, "batch-cross-stage-order")) {
		Begin_Texture_Sampler_Batch();
		assert(Bind_Texture_Stage(0, 1, true));
		assert(configure(0, 1, 3));
		assert(Bind_Texture_Stage(1, 1, true));
		assert(configure(1, 1, 1));   // later request for the same object wins
		assert(Bind_Texture_Stage(0, 2, true));   // stage moves on
		assert(configure(0, 2, 3));
		End_Texture_Sampler_Batch();
		assert(textures[1].u == GL_REPEAT && textures[2].u == GL_CLAMP_TO_EDGE);
		assert(bindings[0] == 2 && bindings[1] == 1);
	} else if (!std::strcmp(test, "batch-release")) {
		assert(Bind_Texture_Stage(0, 1, true));
		Begin_Texture_Sampler_Batch();
		assert(configure(0, 1, 3));
		Release_Texture(1);
		const unsigned before = parameter_calls;
		End_Texture_Sampler_Batch();
		if (g_render_work_cache_mode) assert(parameter_calls == before);
		textures[1] = { GL_REPEAT, GL_REPEAT, GL_LINEAR, GL_LINEAR, true };
		assert(Bind_Texture_Stage(0, 1, true));   // recycled name
		assert(configure(0, 1, 3));
		assert(textures[1].u == GL_CLAMP_TO_EDGE && textures[1].v == GL_CLAMP_TO_EDGE);
	} else if (!std::strcmp(test, "release-scope")) {
		assert(Bind_Texture_Stage(0, 1, true));
		assert(configure(0, 1));
		assert(Bind_Texture_Stage(1, 2, true));
		assert(configure(1, 2));
		Apply_DX8_Texture_Stage_State(0, D3DTOP_MODULATE, D3DTA_TEXTURE,
			D3DTA_DIFFUSE, D3DTOP_MODULATE, D3DTA_TEXTURE, D3DTA_DIFFUSE, true);
		const unsigned binds = bind_calls, parameters = parameter_calls, envs = env_calls;
		Release_Texture(2);
		// Stage 0's binding, sampler and combiner memos are unaffected.
		assert(Bind_Texture_Stage(0, 1, true));
		assert(configure(0, 1));
		Apply_DX8_Texture_Stage_State(0, D3DTOP_MODULATE, D3DTA_TEXTURE,
			D3DTA_DIFFUSE, D3DTOP_MODULATE, D3DTA_TEXTURE, D3DTA_DIFFUSE, true);
		assert(bind_calls == binds && parameter_calls == parameters && env_calls == envs);
		assert(bindings[1] == 0);
		assert(Bind_Texture_Stage(1, 2, true));
		assert(bindings[1] == 2);
	} else if (!std::strcmp(test, "texenv-shadow")) {
		Apply_DX8_Texture_Stage_State(0, D3DTOP_ADDSMOOTH, D3DTA_TEXTURE,
			D3DTA_DIFFUSE, D3DTOP_MODULATE, D3DTA_TEXTURE, D3DTA_DIFFUSE, true);
		const unsigned first = env_calls;
		assert(unit_env[0][GL_TEXTURE_ENV_MODE] == GL_COMBINE && unit_env_color[0]);
		// Original shader state rewrites only the mode and drops the memo.
		glActiveTexture(GL_TEXTURE0);
		Set_Texture_Env(0U, GL_TEXTURE_ENV_MODE, GL_REPLACE);
		g_texture_stage_cache[0].combiner_known = false;
		assert(unit_env[0][GL_TEXTURE_ENV_MODE] == GL_REPLACE);
		const unsigned second = env_calls;
		Apply_DX8_Texture_Stage_State(0, D3DTOP_ADDSMOOTH, D3DTA_TEXTURE,
			D3DTA_DIFFUSE, D3DTOP_MODULATE, D3DTA_TEXTURE, D3DTA_DIFFUSE, true);
		assert(unit_env[0][GL_TEXTURE_ENV_MODE] == GL_COMBINE);
		assert(unit_env[0][GL_COMBINE_RGB] == GL_INTERPOLATE);
		assert(env_calls - second == (g_render_work_cache_mode ? 1U : first));
		// Units are independent.
		Apply_DX8_Texture_Stage_State(1, D3DTOP_ADDSMOOTH, D3DTA_TEXTURE,
			D3DTA_DIFFUSE, D3DTOP_MODULATE, D3DTA_TEXTURE, D3DTA_DIFFUSE, true);
		assert(unit_env[1][GL_COMBINE_RGB] == GL_INTERPOLATE && unit_env_color[1]);
		assert(active_stage == 0);
		Invalidate_Texture_State_Cache();
		const unsigned third = env_calls;
		Apply_DX8_Texture_Stage_State(0, D3DTOP_ADDSMOOTH, D3DTA_TEXTURE,
			D3DTA_DIFFUSE, D3DTOP_MODULATE, D3DTA_TEXTURE, D3DTA_DIFFUSE, true);
		assert(env_calls - third == first);
	} else if (!std::strcmp(test, "benchmark")) {
		uint32_t fingerprint = 2166136261U;
		for (unsigned frame = 0; frame < 600; ++frame) {
			for (unsigned stage = 0; stage < 2; ++stage) {
				unsigned id = 1 + stage * 3 + frame % 3;
				assert(Bind_Texture_Stage(stage, id, true));
				assert(configure(stage, id, frame % 2 ? 3 : 1));
				const Texture &texture = textures[bindings[stage]];
				for (unsigned value : {bindings[stage], texture.u, texture.v, texture.min, texture.mag})
					fingerprint = (fingerprint ^ value) * 16777619U;
			}
		}
		std::printf("sampler-replay frames=600 stages=2 native_binds=%u parameter_calls=%u fingerprint=%08X\n",
			bind_calls, parameter_calls, fingerprint);
	} else { return 2; }
	std::printf("sampler_cache=%s PASS\n", test);
}
