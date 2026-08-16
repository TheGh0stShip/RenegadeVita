# Performance baseline

Performance changes are authorized only after a measured hypothesis and an A/B
comparison using the same content, replay/camera route, build mode, and
settings. A3.2 records CPU wall-time and
presentation wait separately for input, game/network update, PhysicsScene
pre-render, Combat render, traversal/submission, and capture/archive overhead.
Reports require sample count, min, median, mean, p95, p99, max, and slowest
frame. GPU time is never inferred from CPU timing.

Returned capture bundles are compared with
`python3 tools/compare_capture_bundles.py BEFORE AFTER`. The comparison reads
the retained `frames.csv` rather than log text and reports ordinary-frame
sample count, min/mean/median/p95/p99/max, mean FPS, 16.7/33.3 ms slow-frame
counts, capture-readback stall, and mean/p95 for input, game update, physics,
camera, visibility, render submission, present, and housekeeping. It also
compares renderer/resource counters and memory snapshots. No device
performance assertion is made until a returned A3.2-dev1 capture exists.

The A3.1.4 physical geometry evidence is retained as a pre-texture baseline:
first interactive frame 205 meshes, 12,426 vertices, 8,661 triangles; total
1,226 frames, 43,031 meshes, 3,726,647 vertices, 3,140,658 triangles; zero
rejected/unsupported submissions. It is not a texture or frame-time result.

The frozen A3.2-dev1 runtime log at frame 2400 records 39.418 average FPS,
21.874/24.446 ms p50/p95 ordinary-frame time, 231 frames over 33.3 ms,
6.427 ms simulation, and 18.938 ms rendering. It records 249,616 cumulative
mesh submissions, 14,009,711 triangles, 216,621 texture binds, 16,800 state
changes, and zero indexed submissions. These values identify rendering as the
largest measured CPU stage in that failed build only. They are not a
post-correction benchmark and cannot justify a performance claim until the
corrected candidate produces a matching capture/replay.

The returned A3.2-dev1 runtime log contains 282 deferred no-output WWAudio
messages. A3.5-dev1 rate-limits that diagnostic boundary to first occurrence
and powers of two per operation; it does not create synthetic sound objects or
claim an audio-performance improvement without a matching hardware capture.
