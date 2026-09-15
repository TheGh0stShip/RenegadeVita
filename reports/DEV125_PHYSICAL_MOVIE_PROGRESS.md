# Dev125 physical movie progress work

User physical observation on Dev124: intros play at less than 1 FPS. Dev124
does reach movies after recovery with plugins reportedly disabled. Startup
hang cause is not established and no movie timing log has returned yet.

Independent source reproduction found an algorithmic starvation defect in
Drop_Pending_Video_If_Late: a decoder taking 50 ms for a 33 ms source frame
never catches the wall clock, so every subsequent image can be discarded.
Production-function probe discarded 120 consecutive frames without updating
the initial image. Receipt: build/dev125-bink-starvation-reproduction.log.
This is host scheduler evidence, not a measured physical decoder duration.

Correction: when two source-frame intervals elapse without a successful upload,
present the next due frame instead of dropping it. Early frames remain queued;
normal pacing and bounded compressed-packet order are preserved. This guard
does not cap normal FPS or accept a reduced performance target. It prevents
indefinite stale presentation under sustained lateness.

Diagnostics: prior video/audio decode timings covered receive but excluded
avcodec_send_packet, where FFmpeg may decode synchronously. Separate bounded
send and draw totals/worst/call counts now appear in the per-movie summary.
No per-frame file logging was added. Existing receive timing includes scaling.

Nineteen focused checks pass with scheduler ASan/UBSan, including 120 slow
frames making presentation progress, early-frame retention, ordered playback,
queue/byte bounds, allocation failure and skip. build/dev125-bink-focused.log.
Incremental full-demo package passes 135 focused checks and ARM/ELF/SELF/VPK
closure in build/dev125-fast-console.log. Checkpoint startup remains disabled.
Dev124 user playthrough is not interrupted; do not deploy until FTP returns.
Next: retain physical Dev124 logs, inspect timing/counters, finish Dev125
artifact closure, then physical comparison. Performance adoption remains
pending matched physical evidence.

Performance decision record:
- Hypothesis: sustained lateness can suppress all new video presentation;
  physical uploaded/dropped counters will determine whether it occurred here.
- Risk: forced presentation of a due but late frame can expose video/audio
  drift when decoding itself is too slow. The guard does not repair decoder
  throughput; new send/draw timers distinguish that cost.
- Before: physical user observation below 1 FPS; source probe 120 consecutive
  drops. Physical median/p95/p99/worst, subsystem timing and memory high-water
  are pending returned logs, not inferred from this host probe.
- After: host progress invariant passes. Physical timing, visual fidelity,
  audio synchronization and memory comparison are pending.
- Decision: candidate for physical comparison; no accepted performance gain.
