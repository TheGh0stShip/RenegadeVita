# Dev175 M13 Duncan Beacon Handoff

Date: 2026-09-23
Candidate: A3.5-dev175
Profile: `RENEGADE_VITA_M00_DEMO=0`

## Result

Dev175 hardens the original first campaign mission's Duncan/ion-cannon-beacon
handoff path in `Mission01.cpp`. The first retail mission is M13 in campaign
data, but its script implementation lives in `Mission01.cpp`; no separate
`m13.cpp` exists in the checked-out source.

The fix keeps the original conversation and animation path as the primary
route. When `M01_GDI04_Conversation_01` ends, Duncan still starts the authored
handoff animation and the normal `ACTION_COMPLETE_NORMAL` callback grants the
original `POW_IonCannonBeacon_Player`. A bounded delayed fallback now grants
the same original beacon if the nonessential animation-complete callback is
missed. The fallback is guarded by `gaveIonBeacon`, does not mark objectives
complete, and does not advance the mission by itself.

Bounded diagnostics were added for the shack-zone commander clearance path,
Duncan creation, POW-rescued signal, GDI04 conversation start/end, normal
animation-complete handoff, fallback handoff, and duplicate-skip protection.

## Evidence

- `python3 -m tools.test_development_checkpoint`: PASS.
- `python3 -m tools.test_mission_conversation_diagnostics_contract`: PASS.
- `python3 -m tools.test_vita_m13_cinematic_preparation`: PASS.
- `bash ./tools/stage_sources.sh`: PASS, 198 zero-fuzz ordered patches,
  registry `2f6db3a5593a373a7f1992ed8d68f4116dbbd43a3a826a99972d49d107619c24`.
- Full `bash ./tools/build.sh` candidate closure: PASS.
- Build log:
  `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder/logs/a35-dev175-20260923-081947-build.log`.
- VPK:
  `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder/dist/RenegadeVita-A3.5-dev175.vpk`
  SHA-256 `11b26fdd8bb80cd40de7c0701b2a1303912951b84f72011dd880fb7289dae205`.
- ELF SHA-256:
  `e160bd63e12cca60713fbd9656ac203e2ac22f54ae89eabe5f1b69b928e2fc29`.
- Diagnostics ZIP:
  `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder/dist/A3.5-dev175-BUILD-DIAGNOSTICS-20260923-081947.zip`
  SHA-256 `142c8e11b94c83cc70b8c06d34108168e74a245b8c86a64507c2ac2b676cc09b`.

## Runtime Status

No Vita3K or physical Vita mission-route acceptance is claimed for the beacon
handoff yet. The next M13 run should verify one of:

- `A4 M01 Duncan: beacon handoff reason=animation-complete`
- `A4 M01 Duncan: beacon handoff reason=animation-timeout`

and then confirm normal objective progression after the rocket launcher /
vehicle-kill segment provides the ion cannon beacon through gameplay.

No Vita filesystem was accessed and no deployment was attempted.
