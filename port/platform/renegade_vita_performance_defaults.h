#pragma once

// First-run Performance defaults for the Vita, expressed only in values the
// original option system can hold. On the PC, WWConfig's AutoConfigSettings
// (Code/Tools/WWConfig/PerformanceConfigDialog.cpp) wrote the System Settings
// registry values once from the detected hardware class, and the in-game
// Performance tab (dlgconfigperformancetab.cpp) overrode them afterwards.
// The Vita has no WWConfig run, so a missing Performance record resolves to
// the values below; a record saved by the original Performance tab always
// wins. Engine-independent so host tests can check it without WW3D/WWPhys.
#include "renegade_vita_user_settings.h"

// Optional build overrides, each limited to an original option value:
//   RENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL  original Geometry detail slider
//     (0=Low, 1=Medium, 2=High); unset uses the AutoConfigSettings budget.
//   RENEGADE_VITA_DEFAULT_SURFACE_EFFECT_DETAIL  SurfaceEffectsManager mode
//     (0=Off, 1=No Emitters, 2=Full).
#ifndef RENEGADE_VITA_DEFAULT_SURFACE_EFFECT_DETAIL
#define RENEGADE_VITA_DEFAULT_SURFACE_EFFECT_DETAIL 2
#endif
static_assert(RENEGADE_VITA_DEFAULT_SURFACE_EFFECT_DETAIL >= 0 &&
	RENEGADE_VITA_DEFAULT_SURFACE_EFFECT_DETAIL <= 2, "original surface effect mode");
#if defined(RENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL)
static_assert(RENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL >= 0 &&
	RENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL <= 2, "original geometry detail position");
#endif

namespace RenegadeVitaPerformanceDefaults {

// Hardware facts consumed by the original AutoConfigSettings.
struct OriginalAutoConfigInputs {
	bool dxtc;               // caps.Support_DXTC()
	bool hardware_tnl;       // caps.Support_TnL()
	bool high_end_processor; // SSE, or AMD Athlon or later
	bool render_to_texture;  // caps.Support_Render_To_Texture_Format(display)
};

// System Settings registry values written by the original AutoConfigSettings.
struct OriginalAutoConfig {
	int texture_resolution;  // Texture_Resolution (WW3D texture reduction)
	int dynamic_lod_budget;  // Dynamic_LOD_Budget
	int static_lod_budget;   // Static_LOD_Budget
	int shadow_mode;         // Shadow_Mode
	int static_shadows;      // Static_Projectors
	int surface_effect;      // Surface_Effect_Detail
	int particle_detail;     // Particle_Detail
};

// Transcription of the original decision table, kept branch-for-branch.
inline OriginalAutoConfig Original_Auto_Config(const OriginalAutoConfigInputs &in)
{
	OriginalAutoConfig out = {};
	out.texture_resolution = in.dxtc ? 0 : 1;
	if (in.hardware_tnl) {
		out.dynamic_lod_budget = out.static_lod_budget = 10000;
	} else if (in.high_end_processor) {
		out.dynamic_lod_budget = out.static_lod_budget = 5000;
	} else {
		out.dynamic_lod_budget = out.static_lod_budget = 0;
	}
	if (in.render_to_texture) {
		out.shadow_mode = in.hardware_tnl ? 3 : 2;
		out.static_shadows = in.hardware_tnl ? 1 : 0;
	} else {
		out.static_shadows = 0;
		out.shadow_mode = in.high_end_processor ? 1 : 0;
	}
	if (in.hardware_tnl) out.surface_effect = 2;
	else out.surface_effect = in.high_end_processor ? 1 : 0;
	if (in.hardware_tnl && in.high_end_processor) out.particle_detail = 2;
	else if (in.hardware_tnl || in.high_end_processor) out.particle_detail = 1;
	else out.particle_detail = 0;
	return out;
}

// The Vita classified against those inputs: DXT upload and render targets
// exist at the DX8 boundary; measured frames are CPU-bound in the mesh/skin
// boundary, so neither hardware T&L headroom nor an SSE-class CPU applies.
inline OriginalAutoConfigInputs Vita_Auto_Config_Inputs()
{
	const OriginalAutoConfigInputs in = {true, false, false, true};
	return in;
}

// Original Performance tab Geometry detail -> budget (MAX_LOD_LOW/MED/HIGH),
// written to both the static and dynamic budget like the original On_Apply.
inline int Original_Geometry_Detail_Budget(int geometry_detail)
{
	return geometry_detail <= 0 ? 0 : (geometry_detail == 1 ? 5000 : 10000);
}

// Fields of the persisted Performance record (value[9..12]).
struct Performance {
	unsigned static_budget;
	unsigned dynamic_budget;
	unsigned texture_reduction;
	unsigned surface_effect_mode;
};

inline Performance Vita_Default()
{
	const OriginalAutoConfig original = Original_Auto_Config(Vita_Auto_Config_Inputs());
	Performance p = {};
#if defined(RENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL)
	const int budget = Original_Geometry_Detail_Budget(RENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL);
	p.static_budget = static_cast<unsigned>(budget);
	p.dynamic_budget = static_cast<unsigned>(budget);
#else
	p.static_budget = static_cast<unsigned>(original.static_lod_budget);
	p.dynamic_budget = static_cast<unsigned>(original.dynamic_lod_budget);
#endif
	p.texture_reduction = static_cast<unsigned>(original.texture_resolution);
	// Off would also silence footstep/impact/tread sounds and decals, so the
	// engine's own MODE_FULL initializer stays unless deliberately changed.
	p.surface_effect_mode = RENEGADE_VITA_DEFAULT_SURFACE_EFFECT_DETAIL;
	return p;
}

// A saved Performance record always overrides the first-run defaults.
inline Performance Effective(const RenegadeVitaUserSettings::Record &r)
{
	if ((r.value[0] & RenegadeVitaUserSettings::Performance) == 0) return Vita_Default();
	Performance p = {r.value[9], r.value[10], r.value[11], r.value[12]};
	return p;
}

} // namespace RenegadeVitaPerformanceDefaults
