# M09 readiness — 2026-10-07

Evidence class: source review plus host parsing of retail metadata. Nothing was
built or run. Host and Vita3K evidence cannot prove physical acceptance, and
M09 has not been run on the native runtime.

Retail input: Vita3K `Data/M09.mix`, SHA-256
`059fc7de0c06c31e2aa69e1ab7768de81f3377e18c971ba8f98f41e15f1705c1`. That is the
Steam backup identity in `CAMPAIGN_SOURCE_MAP_RECONCILIATION.md`. Its level
members hash to m09.ldd `0067465c…` and m09.lsd `c8c3cd7c…`. The older sweeps
(`live_script_bindings.json`, `definition_instances.json`) used a different
input, `3132c754…`, with different level members (`ee7ae7cf…`/`77fa1e7c…`).
Every check below was re-run against the Vita3K copy. The physical Vita copy
has not been hashed, so it is unknown which edition it holds.

## Objective chain (staging/scripts/Mission09.cpp)

| Step | Owner (file:line) | Trigger | Effect |
|---|---|---|---|
| 0 | `M09_Objective_Controller` 46 on object 2000071 (placed, m09.ldd) | Custom `(id, 3/1/2)` | Add/accomplish/fail objectives 900–904 (110–198, 263–284) |
| 1 | `M09_Mobius_Initial_Conversation` 798 on 2000010 (placed) | Created → 5 s timer | Adds 900 (816); `IDS_M09_D07` (823) → `IDS_M09_P01` (846) |
| 2 | same, `Action_Complete(903)` 879–895 | P01 ends | Adds 901; attaches `M09_Mobius_Follow` (910); FOLLOW 2001012 |
| 3 | `M09_Mobius_Suit_Objective` 357 on zone 2000612 | First entry | X9C_MIDTRO cinematic (403), 901 → accomplished, 902 added (409–410) |
| 4 | `M09_Surface_Objective` 471 on zones 2000614/2000954 | First entry | 902 → accomplished, 903 added, flyover; both zones destroyed (493–501) |
| 5 | `M09_Evac_Point_Objective` 515 on zone 1202054 | STAR and Mobius both inside (546–578) | 1 s timer `M09_MISSION_COMPLETE` |
| 6 | same, `Timer_Expired` 610–613 | timer | **`Commands->Mission_Complete(true)`** |

Failure exits: `Mission_Complete(false)` when Mobius is killed
(`M09_Mobius_Follow::Killed`, 993; controller timer 40, 313) or the evac
helicopter is killed (`M09_Evac_Helicopter::Killed`, 3980). Objectives 900 and
903 are never set to accomplished; completion depends only on the step 5
evac zone. This is retail behavior.

## Checks performed

| Item | Result |
|---|---|
| Script names in level data resolve via the static registry | Vita3K input: all 523/523 persisted script records are in the 1,636-name host registry, and the parser reported 0 binding issues. The older input (`live_script_bindings.json`) also showed 574/574 bindings with none missing (531 persisted, 41 definition, 2 spawner). Each chain owner above is bound exactly once, except the surface objective, which is bound twice. |
| Objective object IDs | Objects 2000071, 2000010, 2002239, 2000955, 2000969, 1100497, 2000279, 2001012, 2000614 and 2000954 are all placed in m09.ldd. 2000275 is a waypath ID. 2000259 is used only on the unreachable `TIMER_RESET` path. |
| Conversations | All 15 names used in the script (`IDS_M09_D01…D19`, `IDS_M09_P01`, `M09CON014`) exist in `m09.ldd`. None come from `conv10.cdb`. |
| Cinematics | `X9C_MIDTRO.txt` and the `X9A_Apache_00–03`/`X9A_Trnspt_00–03` files are in M09.mix. `M09_XG_EV4.txt` is missing from all archives, but only the unreachable `TIMER_RESET` branch references it (no live `Start_Timer`). |
| Script-created presets | Generic_Cinematic, Invisible_Object, Level_01/02_Keycard, M08_Rubble_Stub, Nod_Chinook and Nod_Stealth_Tank all resolve in objects.ddb. `Health/Armor 025 PowerUp` are missing, but they appear only in commented-out code (1388–1449). |
| Placed definitions | All 986 placed object, spawner and physics definition IDs resolve. Factories present: powerup, simple, script zone, soldier, vehicle, damage zone, spawner. |
| Lock 10 | Granted by `M09_Level10Key` zones (4617; 7 occurrences in level data). `M09_Lab_Powerup` (4186) grants it to NPCs. `M09_Havoc_Script` has no binding, so it does not need to run. |
| Array bounds | Camera overrun already fixed (`port/patches/scripts-a35-m09-camera-bounds.patch`). `CRandom::Get_Int(min,max)` returns values in [min, max), so `exp_point[Get_Random_Int(0,5)]` (4271) and `ambients[Get_Random_Int(0,7)]` (4248) stay in bounds. The retail `Anim_num` values are 0,1,3,5,6,8, which fit `elevators[9]`. `target[10]` loop (4563) is in bounds. |
| Unknown script name | `M09_Nod_Damage_Mod_1` (2225) is not declared anywhere. This is an authoring defect from the original source. `Attach_Script` logs it and returns null (`scriptcommands.cpp:551`). This is retail behavior and does not affect progression; left unchanged. |

## Search-start hack (savegame.cpp Pre_Load_Game 327–331 / 357–361)

M09.mix and always.dat both contain `res_vis.w3d`, with different contents.
Only the M09 copy has the `LAB_VIZ_10/11` meshes. This is the only
same-name member in M09.mix that differs from Always/Always2/always.dbs. The
hack puts M09.mix first in the search order so its copy is used.

On Vita, `a31_vita_runtime.cpp:4816` registers the mission factory under the
bare `selected_archive` name, and `Set_Search_Start` compares names without
case, so the hack applies. The factory is added before `Load_Level`, which
calls `Pre_Load_Game` (`combat.cpp:433`). Death-restart and save-load both go
back through `Pre_Load_Game` and re-apply it. M08 also references `res_vis`.
`Free_Assets` runs on level release (`combat.cpp:659`, `level.cpp:80`) and
clears both the prototypes and the Vita unresolved-name cache, so a
prototype loaded from always.dat in M08 cannot carry over into M09.

## Mendoza boss

This item does not apply to M09. No `MendozaBossGameObj` definition
(objects.ddb ID 82150001, "Mendoza Boss", factory `0x0004014A`) is placed in
M09, and the string does not appear in M09.mix. `Mission06.cpp:497` creates
it, so Mendoza support should be reviewed in M06 readiness. M09 also places
no Sakura or Raveshaw definitions.

## Level-data audio dependence

M09 has 5 authored conversation remarks that use WAVs with oversized RIFF
declarations or trailing chunks (`ALL_ARCHIVE_WAVE_SWEEP.md`). Progression
does wait on `ACTION_COMPLETE_CONVERSATION_ENDED` for D07/P01 (step 1–2) and
D11 (Mobius suit, 439–462). However, a failed wave or a zero-duration wave
falls back to the whole-conversation duration or an early advance
(`KNOWN_GAPS.md` audio timing entry). A broken wave should cut a line short
rather than stop the conversation from ending. This is a fidelity risk, not
a confirmed blocker, and needs native evidence.

## Blockers

Found and fixed in this pass: none. The only confirmed M09 source defect,
the camera overrun, was already corrected. No new code change is justified
without native evidence.

## Remaining risks

1. Mobius escort pathing, elevators (`M09_Elevator_All_Controller`, 3327) and
   the X9C_MIDTRO midtro/teleport (+7 Z) have never run natively. A stuck
   Mobius stops step 5.
2. The evac zone needs both actors inside together. If physics or pathing
   leaves Mobius outside, completion depends on the FOLLOW 2000969 retry (566).
3. Remark audio fidelity, as described in the audio section above.
4. Physical M09.mix identity is unverified. Two retail editions with
   different level data are known (see Retail input above). Hash the
   physical file before the run.
5. No runtime log reports the search-start index. The proof that the M09
   `res_vis.w3d` is used is visual only: the lab geometry.

## Physical test route

1. Load M09 from the frontend. Confirm the log has no
   `A4 campaign: original mission MIX unavailable` line, which means the
   mount succeeded. Visually check the lab
   geometry: the `LAB_VIZ_10/11` meshes come only from the M09 copy of
   `res_vis.w3d`.
2. Wait about 5 s. D07 and then P01 should play, and objectives 900 and 901
   should appear. Mobius should start following.
3. Escort Mobius through the lab, elevators and the key-10 doors to the suit
   zone. X9C midtro should play, 901 should complete and 902 should appear.
4. Escort to the surface zone. 902 should complete, 903 should appear and
   the flyover should start.
5. Bring Havoc and Mobius into the evac zone at 2000969. The mission should
   complete after 1 s. Capture the log, the score screen, and the transition
   to M10.
6. Negative check: let Mobius die. `Mission_Complete(false)` should fire and
   the replay prompt should appear.
