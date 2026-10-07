# M10 completion readiness (source + retail-data trace)

Evidence class: staged source inspection and read-only host parsing of the
user's Vita3K retail copy (`M10.mix` SHA-256 `c9bdaa94…3720ec`, matching
CAMPAIGN_SOURCE_MAP_RECONCILIATION). No build, emulator, device or network
action. No retail content is copied here; only names, IDs and counts.

Verdict: no source defect blocks the authored M10 completion chain. No code
change was needed. Native completion is still unproven; it needs a physical run.

## Objective chain to `Mission_Complete(true)`

All `staging/scripts/Mission10.cpp` unless noted. Controller object `1100154`
(preset `Daves Arrow`, def 81960001) carries `M10_Objective_Controller` as a
persisted level script in `m10.ldd`.

1. `Created` → `HAVOCS_SCRIPT` timer (0.5 s) at :61; `Timer_Expired` adds
   pending objective 1003 and attaches `M10_Havoc_Script` to STAR (:566-580).
2. `Custom(type 1000-1025, param 1)` marks accomplished and counts primaries:
   `type < 1008 || type == 1012` (:532-552). Eight primary IDs exist; 1003 is
   only sent last.
3. Six primary senders. Each sender is the conversation *monitor*, and it
   reports from `Action_Complete` when that conversation ends:
   - 1001 Power Plant (obj 1153931): Killed → M10CON014 → :720-728
   - 1002 Con Yard (1153933): Killed → M10CON005 (action 100005) → :755-762
   - 1004 Comm Center (1153932): Killed → M10CON011 (100011) → :891-899
   - 1005 / 1007 / 1006 gates: `M10_Gate_Check` on 1100166 / 1100169 / 2017706
     (level params `1005,…`, `1007,…`, `1006,…`), `Poked` with key 1
     (:2683-2747) plus conversation ends 100002/100008/100017 (:2661-2679)
4. 1012 Level-1 key: `M10_Refinery_Key_Grant` on 2000890, Killed → creates
   `Level_01_Keycard` + `M10_Refinery_Keycard` (:2631-2642). Pickup →
   `CUSTOM_EVENT_POWERUP_GRANTED` → 1012 (:3355-3366).
5. When the seventh primary is reached, M10CON019 plays and an
   `Invisible_Object` runs `Test_Cinematic` `X10I_GDI_Drop_PowerUp.txt`
   (:536-545). That file is in `always.dat`, not in `M10.mix`. This explains
   "no .txt in its MIX": global cinematics are not a gap. At frame 145 it
   creates `POW_IonCannonBeacon_Player_Grant` on bone `Box01` and attaches
   `M10_Ion_Cannon`.
6. Beacon pickup → `PowerUpGameObj::Grant` (`staging/combat/powerup.cpp:738-760`,
   byte-identical to upstream) → `M10_Ion_Cannon::Custom` (:602-611) → 1003
   param 1 → `primary_count >= 7 && type == 1003` → 5 s `MISSION_COMPLETE` timer
   (:547-549) → `Commands->Mission_Complete(true)` (:595-597).

## Data/registry closure (host parse, `tools/audit_m13_level_owners.py` helpers)

- `m10.ldd`: 628 script bindings, 70 unique names. All 70 resolve in the
  static registry: 1,697 `DECLARE_SCRIPT` names from the 44 Scripts.dsp
  sources. `m10.lsd` has none.
- All 70 placed/spawner preset definitions exist in `always.dbs` `objects.ddb`.
- All 13 literal `Create_Object` presets and the cinematic beacon preset exist.
- All 57 `Create_Conversation` names exist except `M03CON068`. Its only use is
  `M10_Radar_Scramble::Entered` (:4367), which is not on the completion chain.
  `Create_Conversation` returns 0 when it is missing (scriptcommands.cpp:2464-2469),
  so retail PC behaves the same way.
- Cinematics: seven of the files the script references are in `always.dat`.
  The ten `X10A_Apache_0x` / `X10A_Trnspt_0x` flyovers (:3425-3435) are missing
  from every retail archive. `Test_Cinematic` logs the failed open and
  destroys its controller (Test_Cinematic.cpp:209-216, :1074-1079). This matches
  retail and is not a blocker.

## Audio dependence

- `M10_Ion_Cannon_Detector` (:2024-2060) depends on a DESIGNER07 *logical*
  sound. That sound only exists if a real audible sound plays
  (`AudibleSound.cpp:514-525`, `:1846-1867`). However, no retail M10
  level or preset binds this script, so the dependency is unreachable.
- The real dependency is on conversation end. Five building/gate primaries,
  which can supply six counts, complete only when their monitored conversation
  ends (`activeconversation.cpp:1069-1092`). The remark timer comes from speech
  `Get_Duration`. It falls back to 2.0 s when no speech object is created
  (`soldier.cpp:3570`, `:3599-3601`), so missing audio delays dialogue but does
  not stall progression. Residual risk is the known zero-duration speech case in
  KNOWN_GAPS (immediate advance, which is still terminating).

## Risks (open, not fixed)

- `primary_count` counts sends, not distinct objectives. Repeat sends
  are original behaviour (e.g. the 1006 gate paths and the 1007 detector path).
- If 1003 arrives before seven other primaries, completion never fires.
  The authored data prevents this, because the beacon spawns only after count 7.
- Beacon delivery needs the drop cinematic to reach frame 145, the `Box01` bone
  to resolve on the slot-6 model, the powerup to be grantable, and the weapon
  bag move to succeed, which is required for the `STATE_GRANTING` event.
- Conversation `Action_Complete` delivery requires the killed building to stay
  a live monitor. Buildings persist after destruction, but this is unverified
  on Vita. Source trace of delivery, zero-length
  speech and save/load: [CONVERSATION_COMPLETION.md](CONVERSATION_COMPLETION.md).
- Large-base performance, Obelisk/Apache/SAM behaviour, M08/M10 Apache callback
  reachability (KNOWN_GAPS 2026-10-04) and save/reload mid-mission are not
  covered here.

## Physical test route

1. Start M10 from a campaign save or the dev launcher. Confirm that objective
   1003 appears about 0.5 s in and that M10CON064 plays.
2. Kill the Refinery key carrier (2000890), pick up the Level-1 key, and confirm
   1012.
3. Use the key on the SE, NW and NE gate consoles in turn. Confirm M10CON002,
   then M10CON008, then 1005, 1007 and 1006 completing.
4. Destroy the Power Plant (M10CON014 → 1001), the Comm Center (M10CON011 →
   1004) and the Con Yard (M10CON005 → 1002). Let each conversation finish.
5. On the seventh primary, confirm M10CON019 and the GDI drop cinematic, and
   that the Ion Cannon beacon powerup appears.
6. Pick up the beacon. Mission success should follow about 5 s later, then score
   and the M11 handoff.
   Capture runtime log breadcrumbs: conversation transition/monitor
   telemetry, `Text_File_Open` of `X10I_GDI_Drop_PowerUp.txt`, and the
   campaign flight recorder's mission-complete event.
