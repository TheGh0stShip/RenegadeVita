# FPS round 4 — AUDIO_STALLS (Miles provider game-thread stalls)

Source and host evidence only. Nothing here was measured on a Vita or in Vita3K.
All gains below are estimates.

## Hypothesis

The game thread waits on the recursive provider lock `g_mutex` while the mixer
holds it for a whole 1024-frame mix. MPEG window refills inside that mix make
the hold longer, and the per-frame `AIL_set_3D_position` calls are the most
likely to run into it.

## Evidence

- `Output_Thread` holds `g_mutex` for all of `Mix_Locked`
  (renegade_miles_provider.cpp ~1006-1013). MPEG decoding happens inside it,
  through `Sample()` refills (renegade_wave_decoder.cpp:832+).
- WWAudio holds `AIL_lock()` itself, through `MMSLockClass` (staging/wwaudio/Utils.h:76),
  around these functions: `Initialize_Miles_Handle` (AudibleSound.cpp:767), `Play`, `Stop`,
  `Set_Volume`/`Internal_Set_Volume`, `Set_Pan`, the pseudo-3D volume/pan updates
  (SoundPseudo3D.cpp:138/179/208) and `Set_Velocity` (Sound3D.cpp:440).
  Consequence: every sample-file set and stream open
  (`Sound{2D,3D,Stream}HandleClass::Initialize`) already runs under the lock. The
  provider's "prepare outside the lock" only drops its own recursion level; the mixer
  still cannot run. Moving work out of the provider lock does not reach those paths.
  Only lock-free calls such as `AIL_set_3D_position` benefit.
- Per-frame calls on the game thread:
  - `Sound3DClass::Update_Miles_Transform` and `Set_Position` (Sound3D.cpp:362/423), through
    `Set_Listener_Transform`/`Set_Transform`. These call `AIL_set_3D_position` for each
    3D sound whenever the listener or the sound moves, with no WWAudio lock.
    `AIL_set_3D_orientation` and `AIL_set_3D_velocity_vector` are no-ops in the provider.
  - Under `MMSLockClass`, and so still blocking: `Update_Edge_Volume` (falloff band only),
    `Update_Fade`, and pseudo-3D `Update_Pseudo_Volume`/`Update_Pseudo_Pan`.
  - `AudibleSoundClass::Update_Play_Position` makes no AIL calls; it uses timeGetTime.
- Loop wrap is not the worst case. `Advance_Loop` sets the cursor to 0. Seeking to frame 0
  has no preceding frames to pre-roll (mpg123 `ignoreframe` clamps at 0), so a wrap costs one
  window decode, the same as a sequential refill. The 16-frame pre-roll
  (decoder.cpp:793) applies only to arbitrary seeks: `AIL_set_sample_ms_position`/`Seek`, the 3D
  offset, or resuming a bumped sound. MPEG_DECODE_COST.md overstates the cost of a wrap.
- mpg123 on the Vita link: the VitaSDK prebuilt `libmpg123.a` 1.33.5 (API 49), linked by
  `CMakeLists.txt:691` (`mpg123`). It is a multi-decoder build: `generic`, `generic_dither`
  and `NEON` (`INT123_synth_1to1_neon`, `_stereo_neon`, `dct64_neon`), with runtime
  detection by `INT123_getcpuflags` (getcpuflags_arm SIGILL probe of
  `INT123_check_neon`). With the default `auto`, NEON is selected on the Cortex-A9.
  Decoding is floating point, not the fixed-point build. Not verified at runtime: logging
  `mpg123_current_decoder()` once would confirm it.

## Changes

1. **MPEG span accessor (exact).** Commit dfd70ad. New `MpegPlayback::Resident_Window()`
   (decoder.h:24, decoder.cpp:823) returns the frames that `Sample()` serves from `pcm[]`
   without a refill, clamped to `Frame_Count()`. `Mix_Mpeg_Voice` (provider.cpp:801) reads
   in place when both `first` and `second` are resident. Otherwise it calls `Sample()` four
   times, in the original order, then refreshes the window. `Sample()` has no side effects on
   resident frames, so the refill sequence (sequential reads and seeks), the PCM values, the
   float expressions and the cursor stay identical. The number of virtual calls drops from 4
   per output frame to about 1 per window refill.
2. **MPEG sample-file open before the provider lock.** `AIL_set_named_sample_file` and
   `AIL_set_3D_sample_file_bounded` call `Prepare_Sample_Mpeg` (provider.cpp:424) before
   `AIL_lock()`, then publish under the lock. Errors and statistics are unchanged.
   Limitation: WWAudio's `MMSLockClass` still covers this path in the game (see Evidence).
   Stream opens now hand their file image to the playback (`Open_Mpeg_Playback(unique_ptr)`)
   instead of copying it. That saves one full-file memcpy under WWAudio's lock and halves peak
   memory for each music open. `mpg123_scan` is kept: skipping it can change mpg123's
   gapless end trimming, and that cannot be shown to be bit-identical without the retail files.
3. **Non-waiting `AIL_set_3D_position` (slice 2).** Commit 2113831. If `trylock(g_mutex)`
   fails, the position goes into a 256-slot queue guarded by `g_position_mutex`, which is
   held only for copies, and the call returns. `Apply_Pending_Positions_Locked`
   (provider.cpp:205) applies queued positions in call order with the original pan formula.
   It runs at the start of every `AIL_lock()` (:1188), before each mix (:1010) and before a
   direct set (:1529). `Release_Sample` and `AIL_shutdown` remove released samples from the
   queue. When the queue is full, the call waits as before. Lock order is `g_mutex` then
   `g_position_mutex`; the publishing path never takes `g_mutex` while holding the
   other.

Not done:
- **Head-window cache for looping voices.** Per the loop-wrap evidence, it saves one window
  decode per track loop. Resuming sequential decoding after a cached head would also need a
  second decoder or a pre-rolled seek, which is worse.
- **Decode-ahead outside the lock.** Prefetching moves the decoder position, which changes
  mpg123's `do_the_seek` shortcut choice, so exact output after a seek could not be proven.
- **Non-blocking volume/pan setters.** No gain: they run under `MMSLockClass`.

## Risk and invalidation argument

- Span: `Resident_Window` is valid until the next `Sample()` call, and the mixer refreshes it
  after every fallback. `Wrap_Voice` touches only sample fields. A stride/channel mismatch
  disables the window.
- Positions: a published position stays invisible until a `g_mutex` holder applies it, and
  every `g_mutex` holder applies pending positions first. Its pan is therefore computed with
  the `maximum_distance` that the original call order would have used: nothing changes that
  value without first applying the queue. Fields are mutex-guarded, so there is no data
  race. One residual: a position published concurrently from a second thread may be applied
  after that thread's locked operation on the same sample. That is a legal ordering, and only
  a WWAudio cross-thread race on one sound could expose it.

## Tests (host, x86-64)

- `python3 -m unittest tools.test_vita_audio_mixer_equivalence` (run alone): **OK**, 4 tests,
  ~218 s. Covers the original 1500/3000-scenario bit-identity, plus:
  - a windowed fake MPEG with the production window and previous-frame semantics that logs
    only refills, so the refill sequence must match;
  - a new production-mpg123 check: two playbacks of generated MP3s (stereo 44.1k, mono 22.05k
    32 kbps), windowed vs original per-frame mixer, 400 buffers with seeks, near-end wraps
    and rate changes, bit-identical output and cursor.
- Mutation checks (scratch copies): 4 injected window bugs are all caught, and 4 injected
  deferred-position bugs (no apply in `AIL_lock`, no release purge, publish disabled, wrong
  pan input) are all caught.
- `tools.test_vita_audio_deferred_position` (new, `-O1` ASan/UBSan and `-O3`): **OK**.
  Deterministic lock-holder thread covering: no blocking, ordering against distances/pan/init,
  mix output equal to a direct set, release purge, full-queue fallback, listener handle, and a
  free-running mixer thread vs 200k random calls checked against a sequential model.
  TSan is not used (it fails on this WSL kernel).
- `tools.test_vita_mp3_decode`, `tools.test_vita_audio_provider`,
  `test_bounded_3d_audio_contract...test_bounded_provider_uses_actual_size`: **OK**.
  The MP3 test's 6 one-LSB feeder/reader differences are pre-existing; the parent commit
  gives the same result.
- ARM TU (VitaSDK, current flags, `-O3`): `renegade_wave_decoder.cpp` **OK**, `renegade_miles_provider.cpp` **OK** (final code, both slices).
- `tools.test_vita_audio_mixer_equivalence` re-run alone after slice 2: **OK** (4 tests).

## Expected gain (unmeasured estimate)

- Span: about 0.1-0.2 ms less mixer time per buffer per MP3 voice.
- `AIL_set_3D_position`: removes the game-thread wait whenever a frame's position updates
  overlap a mix. That is roughly 5-15 % of frames, each waiting up to the remaining mix time
  (about 1-3 ms, or 2-9 ms during an MPEG refill). Average about 0.1-0.4 ms per frame, plus
  lower frame-time jitter. MMSLockClass paths (fades, pseudo-3D, opens) still wait.
- Stream open: one fewer memcpy of the MP3 image (about 3-8 ms for a 3-4 MB track).

## Switches

None. All changes are on by default. Reverting commit 2113831 restores the blocking setter.

## Hardware measurement to take

M13 ambush replay, music playing, same camera path, before and after: game-thread frame time
p50/p95/p99/max, `output_lock_starvation_buffers`, and the audio `mixed_buffers` rate. If the
frame profiler allows, add a scope around `SoundSceneClass::On_Frame_Update`, plus a sampled
count of `g_published_positions` and of `AIL_lock` wait time above 0.5 ms. Log
`mpg123_current_decoder()` once to confirm NEON.
