# Dev169: M13 render-cost reduction and actor snapshots

Renegade Vita - v3.5 active
`[░░░░░░░░░░] 0/10 release acceptance gates complete`

## Result

`A3.5-dev169` is an ARM package candidate built from the full-port campaign
profile. It is not runtime-accepted, Vita3K-accepted, or physical-Vita
accepted.

## Changes

- Added a bounded renderer fast path for unlit vertex materials whose diffuse,
  ambient, emissive, and opacity inputs are constant for the material. Lit and
  vertex-color-source materials still use the original per-vertex evaluator.
- Added M13-only actor-neighborhood snapshots at the existing 120-frame
  checkpoint. The log records Havoc position, nearby soldiers/vehicles,
  definitions, object IDs, positions, distances, velocity, action active/busy
  state, human state, health, and cinematic-freeze status.
- Reduced runtime diagnostic flood from weapon-view fire/idle chatter so M13
  stalls are easier to read and less likely to distort frame pacing.

## Evidence

- `python3 -m tools.test_development_checkpoint`: PASS.
- `python3 -m tools.test_mission_conversation_diagnostics_contract`: PASS.
- `python3 -m tools.test_vita_material_cache`: PASS.
- `bash ./tools/build.sh` with `RENEGADE_CANDIDATE_LABEL=A3.5-dev169`,
  `RENEGADE_M00_DEMO=0`, `RENEGADE_DEVELOPMENT_CHECKPOINT=1`: PASS.
- Host validation in the final build passed retained A2/A3 checks, M00, M01,
  City smoke, renderer lifecycle, input, shader state, texture upload, audio,
  MIX/index, material-cache, ASan, LeakSanitizer, and targeted UBSan checks.
- VPK archive validation and candidate identity verification: PASS.

Final artifact hashes:

- VPK: `042c1f7a67f6cfbb1764520f31162e8bdda3d290951dea08e1ad9cd7e7e3afc4`
- ELF: `4e20eb40c5c58abd7a8d1e9e17e1189159d2e15ff22471deb4146a9eac761a80`
- Diagnostics ZIP:
  `1d675da9786ca3eaf414272cb7c7e9b148c4e30b7ccbef7f55f559e48dc0e4b1`

Artifacts:

- `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder/dist/RenegadeVita-A3.5-dev169.vpk`
- `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder/dist/A3.5-dev169-BUILD-DIAGNOSTICS-20260922-201213.zip`
- Build log:
  `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder/logs/a35-dev169-20260922-201213-build.log`

## Runtime status

No Vita3K run, physical Vita run, visual correctness check, M13 audio/video
sync check, stuck rocket-soldier check, tiberium-field freeze check, objective
completion, death/reload, transition, or campaign acceptance is claimed for
dev169.

## Next experiment

Run M13 with `a35-dev169-runtime.log` and compare against the preserved dev168
freeze evidence. The first pass should inspect:

- renderer material counters and cache hits around the ambush;
- whether weapon-view fire/idle log spam is removed;
- `A4 M13 actor snapshot` and `A4 M13 actor nearby` records near the single
  GDI rocket soldier and near the tiberium-field freeze;
- timing windows around first rocket launch, ambush initiation, and the last
  frame before any stall.

Keep the renderer fast path only if runtime material counters and visual checks
do not expose a material-color regression.
