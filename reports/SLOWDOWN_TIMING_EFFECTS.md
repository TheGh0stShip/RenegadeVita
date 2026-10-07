# Slowdown timing effects on conversations and cinematics (analysis only)

Static source analysis; no build, no host or Vita run.

## Clamp constant
- `staging/combat/timemgr.cpp:71` `#define SLOWEST_FPS 5`; line 176
  `FrameTicks = MIN(FrameTicks, TICKS_PER_SECOND / SLOWEST_FPS)` caps the sim step at **200 ms**.
- The Vita port did **not** change it. No `port/patches/*.patch` touches `SLOWEST_FPS`.
  `a31_vita_runtime.cpp:2437` relies on the cap to absorb suspend/resume gaps.
- **At ~15 FPS (~67 ms/frame) the clamp never applies.** Sim time equals real time.
  Drift starts only when frames take more than 200 ms (below 5 FPS), for example hitches, loads or resume.
  So steady 15 FPS by itself does not desync dialogue from audio. Only frames over 200 ms lose sim time:
  the lost amount is `real - 200 ms` per frame.

## ActiveConversationClass (activeconversation.cpp)
- Remark pacing: `NextRemarkTimer = duration` (line 543), where duration comes from
  `Say_Dynamic_Dialogue` (the sound duration in seconds). The timer then decrements by
  `TimeManager::Get_Frame_Seconds()` (line 443), which is clamped sim time.
- Under clamping, the next remark starts **late**. Audio finishes in real time, then a gap
  follows. Lines **do not overlap** and **are not cut**, because the timer can only run
  slower than the audio. Long silences between lines can appear during hitch bursts.
- `InitializingTimeLeft` (line 462) uses the same clamped decrement, so it only delays the start.
- The orator animation starts with the line (`Set_Animation`, line 537) and advances on sim time.
  Under clamping, mouth or gesture animation lags the real-time audio by the clamped deficit.
  This is a cosmetic desync within a line and does not carry over to the next line.

## Test_Cinematic (staging/scripts/Test_Cinematic.cpp)
- Command timestamps are compared against `Time`, which is driven by `Get_Sync_Time()`/timers
  (TimeManager sim time). Line 1062 runs every due control. `FrameSync = (Time - Controls->Time)*30`
  fast-forwards the started animation by the overshoot, so a late frame keeps animations
  aligned with the **sim** timeline.
- Sounds started by the script play in real time. Under clamping (frames >200 ms), later
  commands, animations and camera cuts fall behind already-playing audio. A long voice
  track can run ahead of its animation, and the next cue starts late. Audio is not cut. Sim lag makes cues start
  later, so overlap between cues becomes less likely, not more likely.
- Port patch `scripts-a35-cinematic-time-budget-only.patch` processes due commands in a
  4 ms real-time budget per callback, and the remainder is deferred. Deferred commands get a
  larger `FrameSync` on the next pass, so animations catch up. The command-count cap of 2 was
  removed to stop the sim clock lagging behind audio.

## Conclusion
At a steady ~15 FPS, nothing is clamped: no overlap, no cuts, no systematic desync. Risk
appears only on frames over 200 ms. Effects then: gaps between conversation lines grow
(never overlap or cut), lip/gesture animation lags audio within a line, and cinematic
cues/animations lag real-time audio by the total deficit. Hardware evidence for this would
be the per-frame `Frame_Seconds` vs `Frame_Real_Seconds` telemetry already emitted at
`a31_gameplay_boundary.cpp:845-847`.
