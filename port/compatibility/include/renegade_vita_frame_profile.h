#pragma once

// Per-frame subsystem timing for the Vita game thread.
//
// The original engine already brackets its subsystems with WWPROFILE scopes
// (CombatManager::Think, Bullets, Game Obj Think, Scene, Soldier Think,
// PhysicsScene, WWAudio, ...). Desktop builds compiled them only with
// WWDEBUG into a hierarchical, single-threaded profiler. On Vita the staged
// wwprofile.h routes them here instead: a flat, inclusive, main-thread-only
// accumulator keyed by the scope's name pointer. Nested scopes therefore
// each report their own inclusive time; children are not subtracted.
//
// Many original scopes sit on per-object, per-wheel, per-integration-step or
// per-draw paths, so one frame can open thousands of them. Every scope is
// counted, but only the first few calls of a scope in a frame are timed
// exactly; later calls are timed with probability 1/16 and the scope's frame
// time is the exact part plus the sampled mean times the remaining calls.
// Once-per-frame subsystem scopes therefore stay exact, while the clock (a
// kernel call on Vita) is read for a bounded share of hot scopes.
//
// Collection is enabled at startup (build default, overridable with
// ux0:data/renegade/user/config/frame-profile-v1.flag = "RVFP1 0|1\n").
// Every 120 profiled frames one "A3.6 frame-profile:" line reports the top
// scopes by window time plus the breakdown of the window's worst frame.
// Disabled collection costs one load and branch per scope.

#include <stdint.h>

#if defined(RENEGADE_VITA_FRAME_PROFILE)

extern bool g_renegade_frame_profile_active;

// Counts one scope entry on the profiled thread. Returns 0 when this entry
// is not timed, otherwise an opaque token to pass to End.
uint64_t Renegade_Frame_Profile_Begin(const char *name);
void Renegade_Frame_Profile_End(uint64_t token);
// Reads the flag, records the calling thread as the profiled game thread and
// logs the measured cost of the candidate clock reads once.
void Renegade_Frame_Profile_Configure(void);
// Opens one game frame, discarding scopes recorded since the previous frame
// closed (loading, pause and skipped iterations are not attributed).
void Renegade_Frame_Profile_Begin_Frame(void);
// Closes one game frame; logs every 120 profiled frames.
void Renegade_Frame_Profile_End_Frame(uint32_t frame_us);

class RenegadeVitaFrameProfileScope {
public:
	explicit RenegadeVitaFrameProfileScope(const char *name)
		: Token(g_renegade_frame_profile_active ? Renegade_Frame_Profile_Begin(name) : 0U) {}
	~RenegadeVitaFrameProfileScope()
	{
		if (Token != 0U) Renegade_Frame_Profile_End(Token);
	}

private:
	RenegadeVitaFrameProfileScope(const RenegadeVitaFrameProfileScope &);
	RenegadeVitaFrameProfileScope &operator=(const RenegadeVitaFrameProfileScope &);
	uint64_t Token;
};

#define RENEGADE_FRAME_PROFILE_CONCAT2(a, b) a##b
#define RENEGADE_FRAME_PROFILE_CONCAT(a, b) RENEGADE_FRAME_PROFILE_CONCAT2(a, b)
#define RENEGADE_FRAME_PROFILE(name) \
	RenegadeVitaFrameProfileScope RENEGADE_FRAME_PROFILE_CONCAT(_renegade_frame_profile_, __LINE__)(name)

#else

#define RENEGADE_FRAME_PROFILE(name) do {} while (0)

#endif
