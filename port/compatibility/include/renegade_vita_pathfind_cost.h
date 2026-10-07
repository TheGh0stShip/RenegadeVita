#pragma once

// RVPF1: AI/pathfinding CPU-cost switches for the Vita game thread.
//
// ux0:data/renegade/user/config/pathfind-cost-v1.flag containing exactly
// "RVPF1 <hex digit>\n" selects a mask. The file is read once, on first use
// (the first awake soldier Think); a missing or malformed file keeps the
// default mask.
//
//   bit 0 (default on): SoldierGameObj::Think evaluates its coordination
//     zone every frame and otherwise calls Is_Safe_To_Disable_Ghost_Collision,
//     a dynamic-scene Collect_Objects personal-space probe, only to pass the
//     answer to Enable_Ghost_Collision(false). That call returns at once
//     unless the soldier is in SOLDIER_GHOST_COLLISION_GROUP, so for an
//     unghosted soldier the probe result is unused. With bit 0 the probe is
//     skipped exactly then. The probe only writes the culling system's
//     transient collection list (every reader resets it first) and a scratch
//     list that it frees, so engine state is unchanged.
//     "RVPF1 0\n" restores the unconditional original probe for A/B.
//
// Census: one "A3.5 pathfind-cost: census" line per 16384 coordination-zone
// evaluations (about 25 s with 20 awake soldiers at 30 FPS), at most
// kRenegadeVitaPathfindCostCensusLines lines per process (none in the M00
// demo profile, whose log writes are synchronous).

#include <stdio.h>
#include <string.h>

int A30_Vita_Log(const char *format, ...) __attribute__((format(printf, 1, 2)));

enum {
	RENEGADE_VITA_PATHFIND_COST_SKIP_UNGHOSTED_PROBE = 1U,
	RENEGADE_VITA_PATHFIND_COST_KNOWN_BITS = 1U,
	RENEGADE_VITA_PATHFIND_COST_DEFAULT = 0U
};

static const unsigned kRenegadeVitaPathfindCostCensusPeriod = 16384U;
#if defined(RENEGADE_VITA_M00_DEMO) && RENEGADE_VITA_M00_DEMO
// The demo profile writes and syncs every log line on the calling thread.
static const unsigned kRenegadeVitaPathfindCostCensusLines = 0U;
#else
static const unsigned kRenegadeVitaPathfindCostCensusLines = 128U;
#endif

struct RenegadeVitaPathfindCostState {
	unsigned mask;
	unsigned zone_entries;   // soldier inside a coordination zone (ghost on)
	unsigned probes;         // original personal-space probe performed
	unsigned skipped;        // probe skipped: soldier not ghosted
	unsigned evaluations;    // since the previous census line
	unsigned census_lines;
	bool configured;
};

// Constant-initialised: no guard, no static constructor.
inline RenegadeVitaPathfindCostState &Renegade_Vita_Pathfind_Cost_State()
{
	static RenegadeVitaPathfindCostState state = { 0U, 0U, 0U, 0U, 0U, 0U, false };
	return state;
}

// Returns the mask for an exact 8-byte "RVPF1 <hex>\n" record, else -1.
inline int Renegade_Vita_Pathfind_Cost_Parse(const char *value, size_t size)
{
	if (value == NULL || size != 8U || memcmp(value, "RVPF1 ", 6U) != 0 ||
		value[7] != '\n') {
		return -1;
	}
	const char digit = value[6];
	int nibble = -1;
	if (digit >= '0' && digit <= '9') nibble = digit - '0';
	else if (digit >= 'a' && digit <= 'f') nibble = digit - 'a' + 10;
	else if (digit >= 'A' && digit <= 'F') nibble = digit - 'A' + 10;
	if (nibble < 0) return -1;
	return nibble & static_cast<int>(RENEGADE_VITA_PATHFIND_COST_KNOWN_BITS);
}

inline void Renegade_Vita_Pathfind_Cost_Configure(RenegadeVitaPathfindCostState &state)
{
	state.mask = RENEGADE_VITA_PATHFIND_COST_DEFAULT;
	const char *source = "default";
	FILE *file = fopen("ux0:data/renegade/user/config/pathfind-cost-v1.flag", "rb");
	if (file != NULL) {
		char value[9] = {};
		const size_t size = fread(value, 1U, sizeof(value), file);
		const bool read_ok = !ferror(file);
		fclose(file);
		const int parsed = read_ok ? Renegade_Vita_Pathfind_Cost_Parse(value, size) : -1;
		if (parsed >= 0) {
			state.mask = static_cast<unsigned>(parsed);
			source = "file";
		} else {
			source = "malformed";
		}
	}
	state.configured = true;
	A30_Vita_Log("A3.5 pathfind-cost: configured version=1 mask=%X source=%s skip_unghosted_probe=%d\n",
		state.mask, source,
		(state.mask & RENEGADE_VITA_PATHFIND_COST_SKIP_UNGHOSTED_PROBE) != 0U ? 1 : 0);
}

inline RenegadeVitaPathfindCostState &Renegade_Vita_Pathfind_Cost_Configured_State()
{
	RenegadeVitaPathfindCostState &state = Renegade_Vita_Pathfind_Cost_State();
	if (!state.configured) Renegade_Vita_Pathfind_Cost_Configure(state);
	return state;
}

inline void Renegade_Vita_Pathfind_Cost_Census(RenegadeVitaPathfindCostState &state)
{
	if (++state.evaluations < kRenegadeVitaPathfindCostCensusPeriod) return;
	state.evaluations = 0U;
	if (state.census_lines >= kRenegadeVitaPathfindCostCensusLines) return;
	++state.census_lines;
	A30_Vita_Log("A3.5 pathfind-cost: census mask=%X zone_entries=%u probes=%u skipped=%u\n",
		state.mask, state.zone_entries, state.probes, state.skipped);
}

// Soldier is inside a coordination zone (original ghost-on branch).
inline void Renegade_Vita_Pathfind_Cost_Note_Zone()
{
	RenegadeVitaPathfindCostState &state = Renegade_Vita_Pathfind_Cost_Configured_State();
	++state.zone_entries;
	Renegade_Vita_Pathfind_Cost_Census(state);
}

// Outside every coordination zone: true skips the personal-space probe.
// Skips only when the soldier is not ghosted, where the original
// Enable_Ghost_Collision(false) would return without using the answer.
inline bool Renegade_Vita_Pathfind_Cost_Skip_Probe(bool ghosted)
{
	RenegadeVitaPathfindCostState &state = Renegade_Vita_Pathfind_Cost_Configured_State();
	const bool skip = !ghosted &&
		(state.mask & RENEGADE_VITA_PATHFIND_COST_SKIP_UNGHOSTED_PROBE) != 0U;
	if (skip) ++state.skipped;
	else ++state.probes;
	Renegade_Vita_Pathfind_Cost_Census(state);
	return skip;
}
