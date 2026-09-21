# Dev135 original campaign trial

## Scope and build

Dev135 extends the full-port profile (`RENEGADE_M00_DEMO=0`) from the original
Single Player menu into a selected campaign archive. The demo profile and
published demo repository were not changed. `RNEGC3101` is a distinct Vita
title ID from the demo's `RNEGA3101`; no Vita filesystem was touched.

The frontend resolves original `Mdd.mix` selections and original save-map
`Mdd.lsd` references to the mission MIX. The runtime adds that MIX to the
existing original file-factory list and passes the selected source to the
original Combat loader. ScoreScreen is registered for original menu mode
lookup, but its presentation remains an explicitly logged placeholder.

Build: CMake full-port profile in `build/vita-dev135-campaign/`, candidate
`A3.5-dev135`, content ID `EP9000-RNEGC3101_00-RENEGADEVITA0110`.
The VPK contains only `eboot.bin` and `sce_sys/param.sfo`; no retail assets,
saves, credentials, or user files are packaged.

| Artifact | SHA-256 |
| --- | --- |
| `RenegadeVita-A3.5-dev135.vpk` | `37b6b42a1f5728364d0596a718ca2741d86daba93df96b7b8d32ff695f7b5fc9` |
| `eboot.bin` | `12f24de9108001ccb324e5cd17450d9ada910197c37e71541b0fc1709bb2239c` |
| `RenegadeVitaA31` ELF | `fe24b1f7af3f7d036255f965d052ec27d4d8b29109fa19250fab5d4984732bb3` |

## Evidence

- Host original M13 harness completed two load/update/render/teardown cycles,
  120 frames each, with player and camera present. It reported 108 meshes,
  423 static and 136 dynamic objects, 7263 triangles, and no rejected draws.
  The `fresh_m00_original_script_weapon_discovery=false` field is specific to
  M00 and does not describe this M13 trial.
- Focused checks: 152 pass. ARM ELF, SELF, and VPK built. This is an
  incremental campaign build, not canonical physical closure.
- Vita3K v0.2.1 Vulkan trial 5 accidentally selected M00. Trial 6 selected
  original Single Player -> Soldier and logged `map=M13.mix`, then
  `source=M13.mix archive=M13.mix save=0 mix_valid=1`, and an original
  Combat load with `source=M13.mix`. The `A3.5 M00 load` log prefix is stale;
  its source value and M13 scene are decisive. The persistent runtime log
  includes both trials, so use the later M13 lines, not the earlier M00 ones.
- Trial 6 `window-210.png` visibly shows the M13 desert in first person with
  HUD, pistol, and radar. The runtime identifies `Commando_Desert`, original
  player object 1500000006. Bounded W input changed position from
  (-162.561,-62.586) to (-158.717,-58.006). Bounded E input increased
  `fired_total` to 2 and reduced pistol rounds from 12 to 10. Start opened
  original EVA pause. Later M13 checkpoints reported `backend_errors=0`.
- The trial reached its 300-second watchdog while paused. Inputs were released
  and only the owned Vita3K process was terminated. Neither native clean exit
  nor mission completion/transition is evidenced.

The isolated Vita3K test used user-owned unchanged retail data and fonts.
The retail `M13.mix` SHA-256 was
`54d41ea011bf7c4d273064422de961af76ccc38f32dd9b5368ebfbca365bbfc4`.
Trial screenshots, input receipts, runtime log, and runner receipt are under
`campaign-dev135-trial-6/` in managed AppData.
These local traces are not release payloads.

## Limits and next test

This is a bounded Vita3K campaign-map trial, not a complete campaign mission
or physical Vita result. ScoreScreen presentation, objectives, mission-end
handoff, later map transition, save re-entry, clean in-app exit, and device
performance remain unverified or incomplete. The campaign app still uses the
established `ux0:data/renegade/retail/Data/` and
`ux0:data/renegade/user/` roots; separate title ID alone does not isolate
writable state from a demo installed on the same Vita.

Next: trace the original M13 completion/objective path through Combat and
Commando, implement the narrow missing transition boundary, then repeat
M13 gameplay and clean exit before a candidate-scoped physical test.
