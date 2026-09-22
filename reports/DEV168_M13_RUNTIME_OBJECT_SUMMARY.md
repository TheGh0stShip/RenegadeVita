# Dev168 M13 Runtime Object Summary

Renegade Vita - v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

## Purpose

Dev168 stops another blind M13 runtime loop by adding bounded runtime evidence
at the original mission object loader boundary. It also fixes a source/staging
drift in the runtime log contract so reset/startup logging keeps the persistent
append handle semantics introduced by the recent M13 runs.

This is not a gameplay or performance acceptance build. It does not claim that
the M13 ambush stall, audio/video sync, missing Havoc helicopter exit, stuck
shotgunner, death/reload crash, cinematic bars, or campaign progression are
fixed. It gives the next M13 run an object/script/cinematic summary to compare
against the mission-wide inventory before changing behavior again.

## Source Changes

- `port/platform/vita/a30_vita_runtime.cpp`: `A30_Vita_Log_Reset()` now closes
  any previous handle, reopens the runtime log in append mode, writes the
  lifecycle `START` line through the shared writer, and syncs without
  truncating prior evidence.
- `port/patches/dev168-m13-loader-summary.patch`: adds campaign-profile
  diagnostics guarded by `!RENEGADE_VITA_M00_DEMO`.
- `staging/combat/gameobjmanager.cpp`: logs one bounded summary after
  `GameObjManager::Load`, including total object counts, physical/smart/
  scriptable counts, soldier/vehicle/simple/powerup/script-zone/cinematic
  counts, observer reference count, cinematic-freeze state, and up to 24
  selected object samples.
- `staging/scripts/Test_Cinematic.cpp`: traces selected M13 X00_Intro
  cinematic object, real object, and model operations.
- `staging/PATCH_INVENTORY.json`: records 196 deterministic zero-fuzz patches,
  registry `3eac24d0025e9fbfacb07483543e2f7d22113fcc461b0b0dee00ce8e2b73a3a1`.

## Evidence

- `bash ./tools/stage_sources.sh`: PASS.
- `python3 -m unittest tools.test_runtime_log_contract tools.test_vita_mesh_batch`: PASS.
- `python3 -m tools.test_development_checkpoint`: PASS.
- Direct execution of all functions in
  `tools/test_vita_m13_cinematic_preparation.py`: PASS.
- `git diff --check`: PASS.
- `find staging -name '*.rej' -o -name '*.orig'`: no output.
- Canonical default package build: `bash ./tools/build.sh` PASS for
  `A3.5-dev110`, default `RENEGADE_VITA_M00_DEMO=1`.
  - VPK `88c291ee464585c777f2ef08cddb49840cb06665ae74123b7d79a706f3e303f4`
  - ELF `09d7d354139af42a8cc47658d9f9f9051d53e35eeedf8971ea2bec7d7cf58262`
  - diagnostics ZIP `a14abb3b4b2c8b3b6f44b1ebc6644dcdc91b6ebf322b8351fbcb0efe08ca5ad8`
- Full-port campaign-profile incremental build in existing
  `build/vita-dev135-campaign` PASS with `RENEGADE_VITA_M00_DEMO=0`,
  title `RNEGC3101`.
  - VPK `fff51c9d26fa63b0cfbf9e5717523d7c109403455e839ae803a89c50c2c86181`
  - ELF `2e805d4f19b64eda0ccb4697d1c50e673d442ad896d98a9e6002d93ffab779a7`
  - SELF `54d502b1dec7e89914715785f310e3ef60509de23555093b55c6b1bde7495858`
  - map `7a0d0b32227e6dc1c293ba5220f5243d72f46d3200366eeac5744bc6b891058f`

## Runtime Status

No Vita3K launch, visual check, audio-sync check, M13 objective check,
death/reload check, transition check, or physical Vita acceptance was performed
for Dev168. No Vita filesystem was touched.

## Next

Run the full-port campaign package through the launch-proof Vita3K runner on
the M13 route and compare:

- `A4 mission object summary`
- `A4 mission object sample`
- `A4 M13 cinematic object create/model`
- `A4 M13 real object create`
- existing script timer/post-think/frame timing records

Use the first mismatched or unexpectedly absent original object/script/cinematic
state to drive the next behavior fix.
