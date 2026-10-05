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
// Collection is enabled at startup (build default, overridable with
// ux0:data/renegade/user/config/frame-profile-v1.flag = "RVFP1 0|1\n").
// Every 120 profiled frames one "A3.6 frame-profile:" line reports the top
// scopes by window time plus the breakdown of the window's worst frame.

#include <stdint.h>

#if defined(RENEGADE_VITA_FRAME_PROFILE)

extern bool g_renegade_frame_profile_active;

uint64_t Renegade_Frame_Profile_Begin(void);
void Renegade_Frame_Profile_End(const char *name, uint64_t start_us);
// Reads the flag, records the calling thread as the profiled game thread.
void Renegade_Frame_Profile_Configure(void);
// Opens one game frame, discarding scopes recorded since the previous frame
// closed (loading, pause and skipped iterations are not attributed).
void Renegade_Frame_Profile_Begin_Frame(void);
// Closes one game frame; logs every 120 profiled frames.
void Renegade_Frame_Profile_End_Frame(uint32_t frame_us);

class RenegadeVitaFrameProfileScope {
public:
	explicit RenegadeVitaFrameProfileScope(const char *name)
		: Name(name),
		  Start(g_renegade_frame_profile_active ? Renegade_Frame_Profile_Begin() : 0U) {}
	~RenegadeVitaFrameProfileScope()
	{
		if (Start != 0U) Renegade_Frame_Profile_End(Name, Start);
	}

private:
	RenegadeVitaFrameProfileScope(const RenegadeVitaFrameProfileScope &);
	RenegadeVitaFrameProfileScope &operator=(const RenegadeVitaFrameProfileScope &);
	const char *Name;
	uint64_t Start;
};

#define RENEGADE_FRAME_PROFILE_CONCAT2(a, b) a##b
#define RENEGADE_FRAME_PROFILE_CONCAT(a, b) RENEGADE_FRAME_PROFILE_CONCAT2(a, b)
#define RENEGADE_FRAME_PROFILE(name) \
	RenegadeVitaFrameProfileScope RENEGADE_FRAME_PROFILE_CONCAT(_renegade_frame_profile_, __LINE__)(name)

#else

#define RENEGADE_FRAME_PROFILE(name) do {} while (0)

#endif
