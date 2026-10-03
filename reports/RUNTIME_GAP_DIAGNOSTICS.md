# Runtime gap diagnostics

2026-10-03: [script lookup diagnostics](SCRIPT_LOOKUP_DIAGNOSTICS.md) now have
source hooks for factory, object, conversation-name and text-file availability
observations during original threaded loading and gameplay. Opt-in bounded
collection and a load-only analyzer are implemented but uncompiled; neither
lookup success nor absence proves a complete route. Native gates remain open.

These tools pair source/data coverage reports with bounded original-runtime
evidence. They report which route milestones the retained evidence proves and
which it does not observe. “Not observed” means evidence is absent for that
session; it does not mean the retail content or implementation is missing.

## Commands

Pull the current Renegade log and flight sidecars from a paired PSTV using
authenticated VDB1. The collector reads the device model, verifies the
installed `RNEGA3101` executable hash supplied for the candidate, then pulls
only that candidate’s runtime log and the four bounded flight-recorder
sidecars. Each file is checked against its device-side SHA-256. It does not
launch the game or change device state.

```sh
python3 tools/collect_pstv_runtime_log.py \
  --vdb-src /path/to/VitaDevBridge/src \
  --profile /path/to/paired-pstv-profile.toml \
  --candidate A3.5-dev197 \
  --expected-eboot-sha256 4d81003ab8fcf4dbe8a958623e83600ce4b8ac468f22971e907b65a723bde831 \
  --output-dir build/device-evidence/dev197-pstv-return
```

Pair a returned sidecar bundle with a named route definition and optional
candidate runtime log:

```sh
python3 tools/analyze_runtime_gaps.py \
  build/device-evidence/dev197-pstv-return \
  --candidate A3.5-dev197 --archive M01.mix \
  --runtime-log build/device-evidence/dev197-pstv-return/a35-dev197-runtime.log \
  --output build/device-evidence/dev197-pstv-return/m01-gap-analysis.json
```

The M13 route definition is `tools/m13_reference_coverage.json`. Other maps or
routes can use the same `segments` schema: each segment has an `id`, a behavior
description, and optional original source `owners`. A runtime segment becomes
observed only when its flight events contain an explicit `category=route`
event whose `name` equals the segment ID. The current recorder does not emit
those semantic route markers yet, so its reports conservatively show mission
state, checkpoint/frame scope, conversations and explicit completion markers
without inferring whole sequences from file presence or actor inventory.

## Dev197 PSTV exercise, 2026-10-03

The connected unit reported model `pstv`, firmware 3.74. The installed SELF
SHA-256 matched the requested Dev197 identity:
`4d81003ab8fcf4dbe8a958623e83600ce4b8ac468f22971e907b65a723bde831`.
The VDB collector retrieved the candidate runtime log and all four flight
sidecars. Device and local hashes match. The retained receipt and returned
files are in the ignored `build/device-evidence/dev197-pstv-gap-tooling-20261002/tool-sidecars/`
directory; no save, screenshot or retail asset was transferred, and no
executable bytes or device files were modified by this collection. The
installed executable was checked by SHA-256 only.

The live flight sidecars identify `M01.mix`, contain six frames and eight
events, and reach the original `M01_Press_F1_Conversation`. They show no
objectives and no explicit later route marker. The analyzer therefore reports
the opening conversation observed and subsequent M01 campaign route
unobserved. It does not infer mission failure from the short recorder window.

The persistent runtime log is longer and includes several sessions. It has an
M13 completion marker at frame 249, while the retained M13 sidecar bundle is a
separate 15-frame pre-Ion save-reload session. The tool reports candidate-log
markers separately and does not merge them into that short sidecar session.
For the M13 reference route, none of the seven named sequences is proven by
the 15-frame sidecars. The later completion marker does not by itself prove
intro, rescue, repair/handoff, Tiberium, base/SAM, Ion-strike or ending visual
correctness. The separately retained report makes this session boundary
explicit instead of presenting mixed evidence as one playthrough.

## Limits and next diagnostic step

The current flight recorder observes lifecycle, mission-state deltas, frame
timing, resource counters and a bounded log tail. It does not yet record
semantic markers at original mission trigger/objective transitions. Add those
markers at the original owners after mapping each route segment to its actual
callback; do not infer progress from elapsed time, loaded presets or cinematic
file preparation. Preserve candidate, archive and session identity on every
marker. Until then, this tooling can expose evidence gaps and separate static
source/data findings from runtime proof, but cannot declare an unobserved
segment to be a missing game feature.
