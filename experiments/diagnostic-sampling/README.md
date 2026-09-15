# Diagnostic sampling experiment

Unintegrated prototype. Not selected by CMake, staged, compiled, tested or
benchmarked. Dev111 does not call it. Default construction requests baseline
collection on every frame. No runtime selector or production code is changed.

## Demonstrated source cost

The native render trace counts complete static and dynamic Phys lists on every
rendered frame. Runtime also collects detailed mission/conversation diagnostics
before change detection. Large worlds amplify these diagnostic costs even when
no corresponding capture or report is emitted.

## Proposed integration boundary

- Wrap only expensive diagnostic collection, never Combat Think, scripts,
  physics, animation, input, player-control admission or mission completion.
- Supply a lifecycle generation incremented at every original load/unload,
  not a scene pointer which can be reused. Reset on session replacement.
- Always collect a fresh full snapshot for explicit captures/checkpoints.
- Commit the policy only after a complete snapshot. Retain the actual snapshot
  alongside its generation and sample frame; the policy owns no object pointers.
- Keep cheap player/control/renderer-error fields current every frame.
- Emit explicit sample age with reused expensive values. Do not present a
  sampled object count or conversation snapshot as frame-current evidence.
- Select the experiment once at startup with its own versioned default-off
  configuration. Do not add hot-loop file reads or reinterpret RVRC1 bits.

The policy handles initial collection, explicit capture, epoch changes, frame
counter rollback and elapsed-frame intervals. Invalid sample age is represented
by UINT64_MAX. The policy is deliberately single-threaded and allocation-free.

## Required later checks

Before integration, exercise baseline and sampled modes, failed collection,
capture forcing, unload/reload with reused pointers, frame rollback and counter
boundaries. On a matching real checkpoint/route, compare diagnostic CPU time,
frame median/p95/p99/worst and capture accuracy. Acceptance must retain all
original gameplay and mission-completion behavior. No FPS gain is claimed.
