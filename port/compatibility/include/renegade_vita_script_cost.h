#pragma once

// RVSC1 script-layer cost attribution (TUT-R1-03).
//
// The frame profiler's window report names only its top scopes, so the
// cheap, script-driven parts of CombatManager::Think never appear in it.
// ux0:data/renegade/user/config/script-cost-v1.flag = "RVSC1 1\n" enables:
//
// * scopes around the once-per-frame original calls that had none
//   (ObjectiveManager::Update, ConversationMgrClass::Think,
//   SpawnManager::Update); each opens a frame-profile scope only while RVSC1
//   and collection (RVFP1) are both on, otherwise one load and branch;
// * one "A3.6 script-cost:" line per profiler window listing those scopes and
//   the original script WWPROFILE scopes (ScriptZone Think, Scriptable
//   PostThink, ...) whatever their rank.
//
// Off by default. Diagnostics only: no call, order or game state changes.

#include "renegade_vita_frame_profile.h"

#if defined(RENEGADE_VITA_FRAME_PROFILE)

extern bool g_renegade_script_cost_active;

class RenegadeVitaScriptCostScope {
public:
	explicit RenegadeVitaScriptCostScope(const char *name)
		: Token(g_renegade_script_cost_active && g_renegade_frame_profile_active ?
			Renegade_Frame_Profile_Begin(name) : 0U) {}
	~RenegadeVitaScriptCostScope()
	{
		if (Token != 0U) Renegade_Frame_Profile_End(Token);
	}

private:
	RenegadeVitaScriptCostScope(const RenegadeVitaScriptCostScope &);
	RenegadeVitaScriptCostScope &operator=(const RenegadeVitaScriptCostScope &);
	uint64_t Token;
};

#define RENEGADE_SCRIPT_COST_SCOPE(name) \
	RenegadeVitaScriptCostScope RENEGADE_FRAME_PROFILE_CONCAT(_renegade_script_cost_, __LINE__)(name)

#else

#define RENEGADE_SCRIPT_COST_SCOPE(name) do {} while (0)

#endif
