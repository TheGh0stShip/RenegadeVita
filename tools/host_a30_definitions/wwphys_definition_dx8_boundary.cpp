// Host-only link boundary for the A3.0 non-rendering world-load runtime proof.
//
// Loading Objects.DDB and M00_Tutorial.lsd must instantiate original engine
// objects, but this host semantic probe must not submit graphics. The original
// WWPhys
// translation-unit cluster nevertheless retains references to its DX8 terrain
// rendering edge.  These definitions make that platform boundary explicit and
// deliberately fail fast if database loading accidentally crosses it.  They
// are not linked into the Vita application and are not a renderer substitute.

#include "dx8indexbuffer.h"
#include "dx8vertexbuffer.h"
#include "dx8wrapper.h"
#include "sortingrenderer.h"

#include <stdio.h>
#include <stdlib.h>

namespace {

unsigned g_unsupported_gpu_calls = 0;
unsigned g_default_render_target_resets = 0;

[[noreturn]] void Unsupported_GPU_Call(const char *operation)
{
	++g_unsupported_gpu_calls;
	fprintf(stderr,
		"A3.0 world-load host boundary entered unexpectedly: %s\n",
		operation);
	fflush(stderr);
	abort();
}

} // namespace

extern "C" unsigned Renegade_A30_Host_Unsupported_GPU_Call_Count()
{
	return g_unsupported_gpu_calls;
}

extern "C" unsigned Renegade_A30_Host_Default_Render_Target_Reset_Count()
{
	return g_default_render_target_resets;
}

unsigned int DX8Wrapper::Convert_Color_Clamp(const Vector4 &color)
{
	// The non-MSVC branch of the original header supplies Convert_Color but
	// accidentally omits this companion definition.  Preserve the original
	// scalar algorithm here; it is a CPU utility, not a simulated GPU call.
	Vector4 clamped(color);
	for (unsigned component = 0; component < 4; ++component) {
		if (clamped[component] < 0.0f) {
			clamped[component] = 0.0f;
		} else if (clamped[component] > 1.0f) {
			clamped[component] = 1.0f;
		}
	}
	return D3DCOLOR_COLORVALUE(clamped.X, clamped.Y, clamped.Z, clamped.W);
}

// Create_Render_Target is supplied by the shared Vita DX8 boundary.  Its
// truthful NULL result is the original projector caller's allocation-failure
// path; this host probe must link the same boundary rather than shadow it.

void DX8Wrapper::Set_Render_Target(TextureClass *texture)
{
	if (texture == NULL) {
		++g_default_render_target_resets;
		return;
	}
	Unsupported_GPU_Call("DX8Wrapper::Set_Render_Target(TextureClass*)");
}

void DX8Wrapper::Set_Render_Target(IDirect3DSurface8 *surface, bool)
{
	/* Apply_Projectors unconditionally restores the default target with NULL,
	** even when its projector lists are empty. A NULL restore has no offscreen
	** resource to emulate on this host; every non-default surface stays fatal. */
	if (surface == NULL) {
		++g_default_render_target_resets;
		return;
	}
	Unsupported_GPU_Call("DX8Wrapper::Set_Render_Target(IDirect3DSurface8*,bool)");
}

void DX8Wrapper::Set_Light_Environment(LightEnvironmentClass *)
{
	Unsupported_GPU_Call("DX8Wrapper::Set_Light_Environment");
}

void SortingRendererClass::Insert_Triangles(const SphereClass &,
	unsigned short, unsigned short, unsigned short, unsigned short)
{
	Unsupported_GPU_Call("SortingRendererClass::Insert_Triangles(SphereClass,...)");
}

void SortingRendererClass::Insert_Triangles(unsigned short, unsigned short,
	unsigned short, unsigned short)
{
	Unsupported_GPU_Call("SortingRendererClass::Insert_Triangles");
}
