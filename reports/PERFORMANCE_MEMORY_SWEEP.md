# Performance and memory inventory (S7)

The initial denominator contains 80 rows: 43 historical ledger sections,
23 table data rows, nine required cost families and five physical budget gates.
All 80 are `unknown`; the sweep is incomplete. Section and table records overlap
and are not counts of unique defects.

Run `python3 -m tools.audit_sweep_performance --output reports/generated/sweeps/performance.json`.
The generator preserves ledger line ranges/content hashes, original source-owner
candidates and source locations of clock/memory instrumentation. Two parser tests
cover table/header distinctions, section bounds and repeated headings. Generated
output reproduces byte for byte. No C++ behavior changed.

Historical ledger evidence includes physical M00 loading/pacing observations and
Vita3K M13 aggregate-creation timings. This inventory does not independently
revalidate their raw logs, executable identity or controlled-route comparability.
It therefore does not promote historical prose to verified measurements.

Required families cover synchronous asset loads, allocations, pathfinding,
visibility/culling, sorting, particles, audio decoding, lock contention and
first-frame/long-load stalls. Owner candidates establish investigation locations,
not causal attribution. Costs outside the ledger remain an explicit coverage risk.

The current physical budget still needs available app cores/actual clock,
free user RAM and CDRAM with high-water tracking, draw calls at 960x544, and
median/p95/p99/worst frame time on fixed content/camera/input routes. A 444 MHz
clock request and memory API call sites do not prove actual operating conditions.
Host and emulator results cannot close these gates.

Provisional profiling order is M05 town square, M10 open base, M06 collapse and
M08 canyon. This covers different workload risks; it is not a measured ranking.
No optimization, reduced content, physical session or emulator launch was made.
