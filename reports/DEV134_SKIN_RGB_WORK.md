# Dev134 discarded character RGB work

| Field | Value |
| --- | --- |
| Candidate | A3.5-dev134 |
| Change type | Measured renderer optimization |
| Decision | Adopted in source; hardware benefit unaccepted |
| Physical status | Not tested in this report |
| Release gates | 0/10 |

## Scope and hypothesis

Latest user steering: physical Vita tests after the next milestone. The milestone
is Dev134 canonical closure, verified package identity and matching Vita3K visual
regression. Physical testing remains held until those pass, then title-scoped
testing and actual hardware frame-time measurements are authorized. Earlier
indefinite-hold language below describes the prior scope.

Native Vita render work continues after Dev133 menu corrections. The current
textured-skin path evaluates material lighting and then overwrites RGB with
white. Only diffuse alpha reaches glColor from that evaluation. This is a
demonstrated redundant calculation inside the measured slow render subsystem;
Dev126 physical render/simulation cumulative means were 59.7/16.5 ms. Those
physical observations are not a fixed-scene before/after benchmark.

## Implementation and safeguards

Dev134 skips discarded RGB calculations after first-color diagnostics have
collected their full original values. Original diffuse alpha still comes from
COLOR1/COLOR2 or material opacity, with the same absent-array fallback. Rigid,
untextured and diagnostic draws retain the full evaluator. Original skin
deformation, materials, UVs, draw order, texture filtering and pixel resolution
are unchanged. RVRC1's existing material-work bit controls the shortcut; clearing
mask 0x2 restores the complete evaluation. Sampled skin_rgb_skips counts actual use.
No extra allocation; one 64-bit counter. Existing scratch high-water unchanged.

## Validation and measurements

Validation: build/dev134-render-focused.log passes 24 checks. Production material
code passes 192000 full-color comparisons, 96000 submitted-skin comparisons and
15360 exhaustive alpha/source/fallback comparisons. The production mesh loop
compares 1425120 corners across 40 cases plus 72000 generic indexed corners,
including texture/material changes, rigid/skin, diagnostics, inherited final
attributes and bounded flushes. ASan/UBSan pass in
build/dev134-material-mesh-final-sanitizers.log.

Fixed CPU fixture: same 4096 vertices plus final inherited attribute, four
lights, original source arrays, 80 trials. Final unsanitized host timings in
build/dev134-render-focused.log, median/p95/p99/worst microseconds:

| Mode | Median | p95 | p99 | Worst | Full evaluations | Skipped RGB |
|---|---:|---:|---:|---:|---:|---:|
| Existing evaluated-then-white | 164.5 | 221.1 | 317.0 | 317.0 | 327680 | 0 |
| Preserve alpha, skip discarded RGB | 19.6 | 21.8 | 29.9 | 29.9 | 0 | 327760 |

An earlier run under emulator contention measured 285.2/386.1/697.3/697.3 versus
30.5/51.7/110.9/110.9 us; retained separately in dev134-material-prototype.log.
Host scratch high-water is 655360 bytes in both variants (the fixture previously
allocated 8192 cache slots); native layout differs. No GPU or hardware memory
high-water, frame-time gain or visual acceptance follows from these host numbers.

## Decision and remaining routes

Decision: adopt as a correctness-tested native candidate; hardware benefit
unaccepted. Risk is accidentally applying the shortcut where RGB is used, or
losing original transparency. The production draw and alpha checks cover those
branches; first diagnostics retain the full calculation. ARM/canonical closure
and fixed-checkpoint native functional comparison are next. No physical test or
emulator performance tuning is authorized by this result.

Other routes remain open: persistent GPU geometry with original mutation and
retirement ownership, immutable render handoff, Bink YUV presentation, measured
frame pacing and diagnostic sampling. No claim that routes are exhausted or
that the demo reaches native 60 FPS. Populated Vehicle/Building and visible
objective cycling checks remain; Dev133 controller Delete now passes native
SELECT, SELECT, Cross, Right, Cross. Its independent 56-file return is at
build/dev133-discovery-return/return-receipt.json, clean Exit, all 14 saves intact.

Canonical attempt one stopped in the older A2 asset host target: Dev132's
renderer included the Vita text-entry header unconditionally even though only
the native presentation path uses it. The include now lives with the other
native-only headers. No broad host include-path change. Failed console retained
at build/dev134-canonical-console.log; retry follows the same canonical gates.

Canonical attempt2 PASS, build/dev134-canonical-console2.log. Original M00
ASan, leak and UBSan two-cycle runs pass; M01 and C&C_City original two-cycle
host smoke pass. 179 Python checks, 182 zero-fuzz patches, 565 ARM build actions,
ELF/SELF/VPK identity and SHA manifest pass. Frozen closure:
build/dev134-closed-canonical/receipt.json (38 files), SELF
55ec5e560eed2ca94a4ab06d8b10e6f7039c19b8d6c79353f5a63f3ea1e7e385.
Matching Vita3K visual regression is the last prerequisite to physical testing.

Milestone PASS: matching Dev134 refinery run retains 42 files at
build/dev134-refinery-return/return-receipt.json. Mobius, weapon and world are
visually consistent with Dev133 at the same original checkpoint. Map imagery,
statistics text and Vita Help labels are visible. Resume advances gameplay to
2180 frames; native END clean, unforced owned process stop. Five native inputs
and four touches released; all 14 original saves unchanged. Wrapper reports
PROCESS_FAILED/null after native clean exit; this is preserved separately.
No physical FPS or complete pause-menu acceptance follows from emulator images.

Physical admission now authorized by the user's milestone instruction. Next:
read-only identity/capability check at 10.0.0.202:1337, predecessor backup,
title-scoped deployment and bounded hardware test if connection/control permits.

Audit finding for next candidate: two prewarm A30_Vita_Log sites in
a31_vita_runtime.cpp use %u with uint64_t renderer counters. Their displayed
backend_errors values are shifted ARM varargs, not valid error observations.
Original lines are retained. Gameplay's correctly typed counters and final
render_error are zero, and deformation failures are zero. Do not silently use
malformed prewarm values in a performance or error summary.
