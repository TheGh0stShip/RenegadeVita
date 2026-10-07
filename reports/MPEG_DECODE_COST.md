# MPEG (mpg123) decode cost in the Vita mixer — analysis (report-only)

Status: static analysis + estimate. No build, no hardware measurement. Numbers
below are estimates and must be replaced by a measured trace before any change
is adopted (per charter performance rules).

## Code path

- `MemoryMpegPlayback` (port/audio/vita/renegade_wave_decoder.cpp:663-764):
  fixed PCM window `int16_t pcm[8192]` (:671) = 4096 mono / 2048 stereo frames.
- `Sample()` (:738-763): on a window miss it either continues sequentially or
  calls `mpg123_seek` (:749) then `mpg123_read(..., sizeof(pcm))` (:754),
  decoding a whole 16 KiB window synchronously.
- `MPG123_PREFRAMES 16` (:705) — every non-sequential seek decodes up to 16
  extra MPEG frames of pre-roll.
- Caller: `Mix_Mpeg_Voice` (port/audio/vita/renegade_miles_provider.cpp:684-713)
  calls `mpeg.Sample()` 4x per output frame (2 channels x first/second; virtual).
- `Mix_Locked` (renegade_miles_provider.cpp:715) runs from `Output_Thread`
  (:851-889) only after `pthread_mutex_trylock(&g_mutex)` succeeds (:860), and
  holds `g_mutex` for the whole mix (:866-868). Mix buffer `kOutputFrames=1024`
  (:93) = 21.3 ms at 48 kHz.
- `g_mutex` is the recursive Miles lock; the game thread takes it through
  `AIL_lock()` (:1036-1040) in every AIL_* entry point (:1028, 1059, 1075 ...).
- Open: `Open_Mpeg_Playback` (decoder.cpp:768) runs `mpg123_scan` (:727) over the
  whole file. Called from `Decode_Into_Sample` (provider.cpp:341, under lock) and
  from the prepare path (provider.cpp:406, intended off-lock).

## Answer: is decode under the lock the game thread takes?

Yes. All mpg123 decoding in steady state happens inside `Mix_Locked` while the
mixer holds `g_mutex`. The mixer itself never blocks (trylock -> silence,
counted in `g_output_lock_starvation_buffers`), but the game thread uses a
blocking `pthread_mutex_lock` in `AIL_lock`, so any AIL_* call issued during a
window refill stalls the game thread for the full decode time.

## Cost estimate (Cortex-A9 @ 444 MHz, 1 core)

Assumptions: 44.1 kHz stereo 128-192 kbps Layer III; mpg123 ARM build. Public
figures put mpg123 at roughly 4-8 % of a ~1 GHz A8/A9 core for real-time stereo
with the NEON synth, 2-3x that with the generic C/fixed path. Scaled to 444 MHz:

| Item | NEON synth | generic synth |
|---|---|---|
| One MPEG frame (1152 samples, 26.1 ms audio) | ~1.0-2.0 ms | ~2.5-5 ms |
| Audio needed per 1024-frame mix (48k out, 44.1k src: ~941 src frames) | ~0.8 MPEG frame | same |
| Amortized decode per mix buffer | **~0.8-1.7 ms (4-8 % of 21.3 ms)** | **~2-4 ms (10-20 %)** |
| Actual burst per window refill (2048 stereo frames ≈ 1.8 MPEG frames, every ~2 mix buffers) | ~2-3.5 ms | ~4.5-9 ms |
| Non-sequential seek / loop wrap (seek + up to 16 pre-roll + 1.8 frames) | **~18-36 ms** | **~45-90 ms** |
| `Sample()` overhead: 4096 virtual calls + range checks per buffer | ~0.1-0.2 ms | same |

Mono assets halve the per-frame synth cost and double window frames (4096), so
refills are rarer. Which mpg123 decoder variant the Vita link uses is not
verified here — check `mpg123_current_decoder()` in a trace.

Implications:
1. Steady state: game thread can stall ~2-9 ms on an unlucky AIL_* call during a
   refill (one per ~43 ms per MP3 voice). Multiple MP3 voices stack.
2. Loop wrap / seek (`Wrap_Voice` -> cursor reset -> non-sequential miss) is the
   worst case: tens of ms under lock, enough to blow both the 21.3 ms audio
   deadline (audible gap; the mixer itself is late) and a game frame.
3. `Decode_Into_Sample` (provider.cpp:341) runs `mpg123_scan` over the entire
   file under `g_mutex` on the game thread; for a multi-MB music track this is
   a one-off stall of tens of ms that also starves the mixer (silence buffers).

## Proposed mitigations (in priority order)

1. **Decode-ahead ring outside the lock.** Give each MP3 voice an SPSC ring of
   decoded PCM (e.g. 3-4 x 2048 frames). A dedicated low-priority decoder thread
   (or the output thread *before* `trylock`) fills it with `mpg123_read` without
   holding `g_mutex`; `Mix_Locked` only copies from the ring. Seeks/loop points
   are posted as commands with a generation counter; the mixer emits from the
   ring only when its generation matches. Preserves the original request order
   because the ring is sequential and the cursor still drives consumption.
2. **Pre-decode loop start.** For looping voices keep the first window decoded
   (captured once at open), so the wrap does not hit the seek + 16-frame pre-roll
   path. The `previous[]` cache (:672) already handles the 1-frame back-step.
3. **Larger window** as a cheap interim: raise `pcm[8192]` to 32768 int16
   (64 KiB per voice). Fewer refills but longer bursts — it reduces frequency,
   not worst-case stall, so only useful combined with (1) or as a stopgap.
4. **Move `mpg123_scan` off-lock**: route all MP3 opens through the prepare
   path (provider.cpp:406) so `Decode_Into_Sample` never scans under lock; or
   skip full scan and use `MPG123_GAPLESS` + Xing/LAME length where present.
5. **Batch `Sample()`**: replace 4 virtual calls per frame with a span accessor
   (`const int16_t* Window(size_t first, size_t &count)`) — small win (~0.1 ms).
6. **Verify decoder variant**: ensure the Vita mpg123 build uses the NEON synth
   (`--with-cpu=neon`), not generic/fixed; 2-3x difference.

## Measurement plan before adopting

Add sampled trace counters: per-buffer `Mix_Locked` duration, per-refill
`mpg123_read` duration, seek count/duration, game-thread `AIL_lock` wait time
(max/p99), and `g_output_lock_starvation_buffers`. Run a fixed M00 replay with
music looping; record median/p95/p99/worst before/after.
