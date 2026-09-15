// Fake GL models object-owned sampler parameters and stage-owned bindings.
// The test driver inserts the actual production functions, including __vita__.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>

using GLenum = unsigned;
enum : unsigned {
	GL_NO_ERROR, GL_TEXTURE0 = 100, GL_TEXTURE_2D = 200,
	GL_CLAMP_TO_EDGE, GL_REPEAT, GL_NEAREST, GL_LINEAR,
	GL_NEAREST_MIPMAP_NEAREST, GL_LINEAR_MIPMAP_NEAREST,
	GL_NEAREST_MIPMAP_LINEAR, GL_LINEAR_MIPMAP_LINEAR,
	GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_TEXTURE_MIN_FILTER,
	GL_TEXTURE_MAG_FILTER
};
struct MeshMatDescClass { static const unsigned MAX_TEX_STAGES = 2; };
struct Texture { unsigned u, v, min, mag; };
Texture textures[16] = {};
unsigned bindings[2] = {};
unsigned active_stage = 0, bind_calls = 0, parameter_calls = 0, pending_error = 0;
bool fail_parameter = false;
struct {
	unsigned texture_stage_enable_skips, state_changes, texture_invalid_binds;
	unsigned texture_bind_skips, texture_binds, texture_sampler_skips;
	unsigned texture_sampler_updates, backend_errors, texture_unsupported_stages;
	unsigned texture_sampler_parameter_writes;
} g_statistics = {};
bool g_logged_first_state_cache_skip = false;
void Vita_Append_A22_Runtime_Breadcrumb(const char *, const char *, ...) {}
void Record_Texture_Unsupported_Stage(unsigned) { ++g_statistics.texture_unsupported_stages; }
void Invalidate_Original_Shader_State_Cache() {}
void glActiveTexture(unsigned unit) { active_stage = unit - GL_TEXTURE0; assert(active_stage < 2); }
void glEnable(unsigned) {}
void glDisable(unsigned) {}
void glBindTexture(unsigned, unsigned texture) {
	assert(texture < 16);
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
unsigned glGetError() { unsigned error = pending_error; pending_error = 0; return error; }
void glDeleteTextures(unsigned count, const unsigned *ids) {
	for (unsigned i = 0; i < count; ++i) {
		textures[ids[i]] = {};
		for (unsigned &binding : bindings) if (binding == ids[i]) binding = 0;
	}
}
bool Bind_Texture_Stage(uint32_t, uint32_t, bool);
bool Configure_Texture_Sampler_Stage(uint32_t, uint32_t, bool,
	uint32_t, uint32_t, uint32_t, uint32_t, uint32_t);

#include "sampler-production.inc"

bool configure(unsigned stage, unsigned texture, unsigned address = 1,
	unsigned min = 2, unsigned mip = 0) {
	return Configure_Texture_Sampler_Stage(stage, texture, true,
		address, address, min, 2, mip);
}

int main(int argc, char **argv) {
	assert(argc == 2 || argc == 3);
	if (argc == 3) {
		assert(!std::strcmp(argv[2], "0") || !std::strcmp(argv[2], "1"));
		g_render_work_cache_mode = !std::strcmp(argv[2], "1") ? 1U : 0U;
	}
	const char *test = argv[1];
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
