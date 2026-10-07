# FPS round 4: game-thread overhead (instrumentation + heap churn)

Source only. Nothing here was measured on hardware. Every gain below is an estimate.

## Hypothesis
1. The default-on frame profiler reads the clock twice and calls `sceKernelGetThreadId` for every
   WWPROFILE/RENEGADE_FRAME_PROFILE scope. Original scopes sit on per-wheel, per-integration-evaluation,
   per-soldier-move, per-cull-box, per-mesh and per-draw paths, so a busy M13 frame opens thousands of them.
2. Per-frame heap allocation on the game thread takes newlib's global malloc lock, which the mixer,
   vitaGL GC and log threads also use.

## Evidence
- Clock API: `sceKernelGetProcessTimeWide` and `sceKernelGetThreadId` are SceLibKernel imports
  (libSceLibKernel_stub.a). `sceKernelGetSystemTimeWide` is a direct SceThreadmgr import. The cost of
  each per call on retail firmware is unknown (believed to be a kernel entry for the time reads, unverified).
  VitaSDK newlib `clock_gettime(CLOCK_MONOTONIC)` is `sceKernelGetProcessTimeWide` plus a software 64-bit
  `__aeabi_uldivmod` (disassembled from libc.a `lib_a-clock.o`). `CLOCK_REALTIME`/`gettimeofday` use RTC calls.
- There are 354 WWPROFILE sites in staging. Hot ones: `wwphys/wheel.cpp:689,703,785,824,903` (5 per
  wheel per derivative evaluation), `wwphys/rbody.cpp:1155,1224,1673` (Midpoint integration = 2 evaluations
  per step), `wwphys/phys3.cpp:1081-1536` and `humanphys.cpp:196-369` (about 8-10 per soldier),
  `wwmath/cullsys.cpp:66` (every moved cullable) and `ww3d2/mesh.cpp:705` (every mesh). Port per-draw
  scopes from eb5d22c: `ww3d_vita_renderer.cpp:2310,3727,3935,4337` and `ww3d_dx8_boundary.cpp:2496,3093`.
- Static scope estimate for the M13 ambush (about 15 active vehicles, 20 soldiers): vehicles about 60-140
  scopes each (W wheels: about 10+10W per integration step), soldiers about 15-25 each, render about 3-4 per
  mesh/batch. Total about 1,500-4,000 scopes, so 3,000-8,000 clock reads plus the same number of thread-id
  calls per frame. No frame-profile line exists in any device log yet (the profiler postdates dev238).

## Changes (commits on this branch)
1. Profiler (`port/platform/vita/renegade_vita_frame_profile.cpp`, `port/compatibility/include/renegade_vita_frame_profile.h`):
   - Every scope entry is still counted. Only the first `kExactCallsPerFrame=2` entries per scope name per
     frame are timed. Later entries are timed with probability 1/16 (LCG). Frame time = exact part +
     sampled mean x remaining calls (VFP double, rounded; no software 64-bit divide); with no sample, the
     exact mean is used. Once- and twice-per-frame subsystem scopes stay exact. The untimed path is about
     40 Thumb-2 instructions (checked in the ARM disassembly). The slot lookup moved to Begin. The scope holds one 64-bit token
     (slot+1, sampled bit, 32-bit start).
   - Profiled-thread test: the game thread's validated stack range (`sceKernelGetThreadInfo`, accepted only
     if it contains the configuring frame). It costs no kernel call per scope. It falls back to the thread id.
   - Disabled profiling: one load+branch in the ctor and a token test in the dtor. No clock read.
   - Clock source unchanged and consistent: `sceKernelGetProcessTimeWide`, the same as all frame and stage timers.
   - New one-time line: `A3.6 frame-profile: clock-cost calls=256 process_time_wide_ns= process_time_low_ns=
     system_time_wide_ns= thread_id_ns= profiled_thread_test_ns=`. It measures the real per-call costs on hardware.
   - Window line is now `version=2`. New fields: `timed_per_frame exact_calls sample clock_ns est_clock_us`.
     The old fields keep their meaning. `avg_us` (and the worst-frame `scope_us`) of a scope entered more
     than 2 times per frame is now an unbiased estimate, not a full sum. `scopes_per_frame` still counts
     all entries.
2. `QueryPerformanceCounter` (`win32_compat.h:536`): on Vita it returns `sceKernelGetProcessTimeWide()*1000`.
   This is bit-identical to the old `tv_sec*1e9+tv_nsec` from newlib (proof plus a 10k-sample check in the
   test), with no 64-bit division. Users: the pathfinder budget loops `pathsolve.cpp:393` (one read per A*
   node) and `pathmgr.cpp:388`.
3. Heap retention:
   - `ww3d_dx8_boundary.cpp:120` native material-pass queue: task storage is recycled through a bounded
     free list (256) instead of new/delete per additional pass per frame. Add_Ref/Release_Ref order is unchanged.
   - `a31_gameplay_boundary.cpp:685` mission-progress diagnostic: the `ConversationRemarkClass` copy is
     static, so its `StringClass AnimationName` buffer is reused. It was allocated and freed every frame
     while a remark was current.
   - `staging/wwaudio/WWAudio.cpp:1334` + `port/patches/wwaudio-a36-completed-sounds-retain.patch`
     (registered after `wwaudio-a35-flush-enqueue-order.patch`): `m_CompletedSounds.Delete_All()` freed
     and reallocated the whole array (vector.h:874) on every frame where a sound completed. Elements are
     raw `AudibleSoundClass*`, so `Reset_Active()` leaves identical count/capacity/state. Guarded by
     `RENEGADE_VITA_PORT`. `patch -p1 -F0 --dry-run` is clean against the pre-change staged file.

## Ranked sites
| # | Site | Frequency | Status | Est. per-frame cost before -> after (unmeasured) |
|---|---|---|---|---|
| 1 | WWPROFILE/RENEGADE_FRAME_PROFILE scopes (all sites above) | 1.5k-4k/frame (M13) | fixed: sampling + stack test | 2 x N clock reads + N thread-id calls -> about 250-400 timed scopes + about 40-80 cycles per untimed scope; at 0.3-1 us per read: about 1-8 ms -> about 0.3-1.2 ms |
| 2 | Pathfinder `Get_Time` per A* node (pathsolve.cpp:393) | per node while solving | fixed: no 64-bit divide | about 0.2-0.6 us per node saved, inside a time budget (more nodes per budget) |
| 3 | `m_CompletedSounds.Delete_All` (WWAudio.cpp:1330) | frames with a completed sound | fixed | 1 free + 1 new[] (2 lock round-trips) -> 0 |
| 4 | Material-pass task new/delete (ww3d_dx8_boundary.cpp) | per additional pass (stealth etc.) | fixed | 2 heap ops per pass -> 0 after warm-up |
| 5 | Remark copy in progress poll (a31_gameplay_boundary.cpp:685) | per frame during conversations | fixed | 1 malloc + 1 free -> 0 |
| 6 | Stage timers: `frame_begin`/`simulation_begin` back to back (a31_vita_runtime.cpp:6212/6243) plus `frame_start_us` (a31_gameplay_boundary.cpp:713); 8 stage reads overlap 6 sim profile scopes (12 reads) | about 22 reads/frame | not fixed (shared loop file; low value) | about 10-40 us |
| 7 | `timeGetTime` on main (bc88fcb): `clock_gettime` -> 64-bit div; `sceKernelGetProcessTimeWide()/1000` is bit-identical (floor(t/1e6)*1000+floor((t%1e6)/1000) = floor(t/1000)) | tens/frame (SysTimeClass users) | not fixed (not in this base; conflicts) | about 0.2-0.5 us per call |
| 8 | Flight recorder `Monotonic_Us` (a35_campaign_flight_recorder.cpp:173) / capture telemetry: `clock_gettime` + 2 divides | opt-in events only | not fixed | negligible unless enabled |
| 9 | Mesh-boundary 1/16 sampling, draw-end timing (ww3d_vita_renderer.cpp:3742/4041/4219) | per mesh | already compiled out (`RENEGADE_VITA_DETAILED_TIMING` undefined) | 0 |
| 10 | PostThink 1/16 sampled object timing; Copy_Flight_Memory every 30 frames; census every 120 | per object/frame | already sampled | small |

Other agents' files, findings only (not edited): `Submit_Mesh_Internal` scopes at 3727 (per mesh) and
3935 (per pass, inside the batch loop) can be removed or merged once that work lands. They are now
sampled after 2 entries per frame. The DX8 strip path already reuses its expansion scratch
(`ww3d_dx8_boundary.cpp` `expanded_indices`). Renderer scratch (`Ensure_Deformed_Skin_Scratch`, the
material colour cache) is grow-only. `SoundScene` per-frame `AudibleInfoClass` and `MultiListNodeClass`
are original `AutoPoolClass` pools. Per-open `RenegadeRootedFileClass`/`strdup` (renegade_file_factory.cpp:98,619)
and wave-decoder scratch vectors are per open/decode, not per frame. HUD text (hud.cpp `WeaponChartIcons.Delete_All`)
belongs to the HUD agent.

## Risk and invalidation
- Profiler: diagnostic only, no engine state. Estimates are unbiased; per-frame worst-scope values for hot
  scopes are noisier (about 4-8 samples). Stack test risk: a wrong range. It is accepted only if it contains
  the game thread's own frame; other thread stacks are disjoint allocations.
- QPC: the value is identical by arithmetic (newlib's 32-bit `time_t` only wraps after 136 years). The old
  failure branch is unreachable on Vita.
- `Reset_Active`: pointer elements are trivially destructible. Delete_All reallocated the same `VectorMax`,
  with indeterminate contents beyond `Count`. Observable state is equal.
- Material pass pool: same constructor/destructor (reference) calls, same queue order. Memory goes back to
  the free list (bounded) instead of `free`. Game thread only, like the queue itself.
- Remark static: the value is overwritten before every read (`Get_Remark_Info`), and only `TextID` is read.

## Tests
- `python3 -m unittest tools.test_frame_profile` (new; ASan/UBSan C++ harness against fake psp2 clock/thread):
  disabled scopes read no clock; the once-per-frame scope is exact; hot/child estimates are 6974/6990 and
  2000/2000 us; 129 of 2001 entries are timed; other threads are ignored (stack-range and thread-id modes);
  out-of-frame scopes are discarded; the QPC identity holds. PASS (4 tests).
- `python3 -m unittest tools.test_game_thread_heap_retention` (new; ASan/UBSan): material-pass slots are
  reused with balanced refs and the 256 bound; `Reset_Active` matches `Delete_All` on the staged `vector.h`;
  patch registration. PASS (3).
- Existing: `tools.test_npc_path_frame`, `test_mission_conversation_diagnostics_contract`,
  `test_mission_completion_contract`, `test_original_decal_submission`, `test_vita_indexed_state_contract`,
  `test_mission_conversations`: 66 run, 2 pre-existing failures unrelated to this diff
  (dazzle-lifecycle identity per HOST_TEST_TRIAGE_2026-10-06; a directinput token assertion in an untouched file).
- ARM TU compiles (real VitaSDK flags, arm_tu_check.sh): all OK. They cover renegade_vita_frame_profile.cpp
  (-Wall -Wextra), ww3d_dx8_boundary.cpp, a31_gameplay_boundary.cpp, staging/wwaudio/WWAudio.cpp,
  staging/wwphys/wheel.cpp (WWPROFILE user of the new scope header) and staging/wwphys/pathsolve.cpp (QPC
  user). The QPC header also passes a C++ compile with the psp2 processmgr.h included before and after it.

## Switches
The profiler stays default-on (`RENEGADE_VITA_FRAME_PROFILE_DEFAULT`). Disable it at runtime with
`ux0:data/renegade/user/config/frame-profile-v1.flag` = `RVFP1 0\n`. The tunables are `kExactCallsPerFrame`
and `kSampleShift` in the profiler .cpp. The heap/QPC changes have no switch (they are value-identical).

## Hardware measurement to take
On the same M13 ambush route, record the `clock-cost` line (ns per read) and, from a frame-profile window
line, `scopes_per_frame`, `timed_per_frame` and `est_clock_us`. Old profiler overhead is about
`scopes_per_frame * (2*process_time_wide_ns + thread_id_ns)`. New overhead is about `est_clock_us` plus
untimed scopes. Then run A/B with `RVFP1 0` vs `RVFP1 1` on the same route and compare median/p95 frame and
sim/render stage times (`Log_Campaign_Simulation_Stages`). If `clock_ns` is small (<150 ns), lower the
sample shift for better per-frame accuracy.
