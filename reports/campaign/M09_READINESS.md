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

## Full audit — 2026-10-07

Evidence class: source review, host parsing of the Vita3K retail copy
(M09.mix `059fc7de…`, objects.ddb `98253406…`) with the existing
`tools/audit_mission_content_bindings.py` and
`tools/renegade_cinematic_dependency_scan.py`, `arm-vita-eabi-g++
-fsyntax-only` on the two patched files, and `nm` on the existing
fast-candidate `Mission09.cpp.obj`. Nothing was built, linked, packaged or
run. Detailed receipts stay under the ignored `build/m09audit/`.

### 1. Script bindings and parameters

- 564 bindings (523 persisted in m09.ldd, 39 definition, 2 spawner) name 56
  scripts. All 56 are in the 1,636-name host registry and their sources are in
  the compiled set (`Mission09.cpp.obj` carries 96 `ScriptRegistrant<M09_*>`,
  one per `DECLARE_SCRIPT`). No unknown shipped script, 0 binding decode
  findings.
- Parameter shape: 235 bindings match their descriptor count exactly; 329
  pass a single `"0"` to an empty descriptor (never read). No binding passes
  fewer values than its descriptor. Every `Attach_Script` call outside comments
  (45; two pass a formatted object id) matches its descriptor count, except `M09_Nod_Damage_Mod_1`
  (`Mission09.cpp:2227`), which is undeclared in the original source and
  returns null without effect (retail behaviour).

### 2. Events, timers and object IDs

- Every custom type sent on the chain has a receiver: 900–904 and
  `check`/`MOBIUS_KILLED`/`BLOCK_ON/OFF` (controller 2000071), `FOLLOW`,
  `ELEVATOR(_DOWN)`, `ELEVATOR_EXIT`, `NO_FOLLOW` and the 901–903 replies
  (Mobius 2000010), `SET_STAR`/`SET_MOBIUS`/`CHECK_STAR`/`STAR_STATUS`
  (controllers), `CHECK`/`COUNT`/`KEY_COUNTER` (2000452 and the keycard zone),
  `FLYOVER` (2000955), `8888` and `666` from `X9C_MIDTRO.txt` (2000612 suit
  zone, 1202323 `M09_PSuitAnim`; both placed). Every timer id started is handled in the same script.
- Literal `Find_Object` IDs not placed in m09.ldd: 2000259 (unreachable
  `TIMER_RESET`), 2000599/2000607 (compared against the controller's own id
  only; neither controller exists, so the generic branch always runs), and
  2000626 (`M09_Mutant_Attack` attack target; `Set_Attack(NULL)` falls back to
  a location attack). All retail-identical, none on the objective chain.
- Parameter-supplied IDs: every `M09_Mobius_Goto`, `M09_Elevator_Exit`,
  `M09_Zone_Enabled_Mobius`, lift waypoint and zone→controller target is a
  placed object. Controller 2000592 (`Anim_num` 1, waypoint 2000593, lift
  2051108) is orphaned: no zone names it, and neither 2000593 nor static
  object 2051108 exists, so its `Created` lift call is a no-op. Its `Custom`
  table typo `res_elev01.res_elev01` (no such `.w3d` in any archive) is
  therefore unreachable. Unplaced IDs 1101300/1101301 (cameras) and
  1101835–1101837 (innate targets) hit null-safe commands.
- `M09_Key_Box` `FOLLOW 2000860` (unplaced) is unreachable: `VERIFY GO` is
  only sent from commented-out code.

### 3. Assets

All cinematic and script dependencies resolve in M09.mix/always.dat/
Always2.dat: X9C models, facial/body animations and camera; the eight
X9A flyover files and their models; `c_ag_gdi_pmob`, `h_a_a0a0_l26d*`,
`XG_TransprtBone`/`XG_EV2_*`, `v_GDI_trnspt` and `h_a_x9c_suit`. Presets,
sound and explosion definitions (`GDI_Transport_Helicopter`,
`GDI_RocketSoldier_2SF`, `Nod_Apache`, `Nod_Transport_Helicopter`,
`POW_LaserChaingun_AI`, `Air Explosions Twiddler`, the seven ambient sounds,
`09_A`, three `M09DSGN_*_SND`) are in objects.ddb. `POG_M09_1_0*.tga` and
`POG_M08_1_03.tga` ship as `.dds`. Lift animations for `Anim_num`
0/3/5/6/8 resolve; `cent_elev01` (7) and `res_elev01` are absent from retail
and unused by live bindings. Retail-identical misses: `M09_XG_EV4.txt`
(unreachable) and 15 weapon eject/muzzle-flash and twiddler definition IDs
in the global objects.ddb (not M09-specific).

### 4. Defects and fixes

| Defect | Location | Severity | Fix |
|---|---|---|---|
| Gunner id formatted into `char param1[10]`; dynamic ids are 10 digits, so the write is 11 bytes | `Mission09.cpp:3935` (`M09_Evac_Transport::Entered`, on the evac path) | Medium (UB on the completion path; in the current fast-candidate frame the extra NUL lands in padding at `sp+26`) | `scripts-a36-m09-evac-gunner-param-buffer.patch` (16 bytes + `snprintf`, same text) |
| `Static_Anim_Phys_Goto_Last_Frame` dereferences `Peek_Animation()` unchecked | `scriptcommands.cpp:2279` (every M09 lift `Created`, `ACTIVATEDOWN`) | Medium-latent (all live M09 names resolve; a failed on-demand load on Vita would crash) | `combat-a36-scriptcommands-null-guards.patch` (skip only the target when no animation; unchanged when it loads) |

Both patches are registered last in `tools/stage_sources.sh`; staging exited
0 at zero fuzz and no existing anchor moved.

### 5. Objective chain

Re-verified: 900 (Mobius created) → D07/P01 → 901 + `M09_Mobius_Follow` →
suit zone 2000612 (X9C midtro, 901 done, 902) → surface zones
2000614/2000954 (902 done, 903, flyover) → evac zone 1202054 with STAR and
Mobius → 1 s → `Mission_Complete(true)`. Every hop's object is placed and
its script bound. Repeated `Mission_Complete` calls keep the first terminal
result (`MISSION_FAILURE_PATHS.md`).

### 6. Deferred (retail-identical, no change)

- `M09_Innate_Enable_Zone::all_checked_in` (`:4122`, assigned only in
  commented-out code) is never initialised;
  the 4 s second innate pulse is indeterminate.
- `M09_Gunner::full_health` is not saved; after a load during the evac
  window `Damaged` restores an indeterminate value (gunner only).
- `M09_Chinook_ParaDrop` has the same `char params[10]` pattern (`:2324`) but
  is not bound in M09 and formats its placed owner id (7 digits).
- `M09_Objective_Controller` `BLOCK_ON` requires all four block ids non-zero,
  so rubble is never spawned (original logic).
- `tools/test_m09_camera.py` already fails at HEAD: it expects the staged
  file to equal upstream plus the camera fix only, which stopped being true
  with the keycard and objective-save patches. Not changed here.
  `test_script_load_capacity` and `test_logical_stimulus_telemetry` also fail
  with the HEAD `scriptcommands.cpp` restored (checked), so they predate this
  audit.

No runtime, visual or physical claim follows from this audit.

## Soft-lock hunt — 2026-10-07

Evidence class: staged-source review; host parsing of the Vita3K copy (M09.mix
`059fc7de…`, always.dbs `objects.ddb`) for conversation flags, zone and powerup
definitions, and level bindings (receipt under the ignored `build/m09softlock/`);
`bash tools/stage_sources.sh` exit 0 (545 patches, zero fuzz);
`arm-vita-eabi-g++ -fsyntax-only` on the patched `Mission09.cpp` (0 errors, only
pre-existing warnings). Nothing was built, linked, packaged or run. Line numbers
are the staged file after this pass.

### Data facts used

- `m09.ldd` conversation `IsKey`: D07, P01, D01–D04, D10, D12–D14, D17, D18
  are key. D05, D06, D08, D09, D11, D15, D16, D19, D20 and M09CON014 are not.
- Zone definitions: 519 is `Script_Zone_Star` (stars only). The evac zone
  1202054 is 82060002 `Script_Zone_All`, so Mobius's own entry registers. Every
  other chain zone (suit, surface, keycard, lift, exit, Goto) is star-only.
- `Level_01_Keycard`/`Level_02_Keycard`: `Persistent` 0, `AlwaysAllowGrant` 1,
  `GrantKey` 1/2. Only human soldiers collect powerups
  (`SoldierGameObj::Wants_Powerups`).
- Scripted lifts: only `M09_Elevator_All_Zone` (6) and `_Controller` (7) are
  bound. `M09_Elevator_Movement_Zone` is unbound.

### Findings

| # | Issue | Location | Reachability | Severity | Action |
|---|---|---|---|---|---|
| 1 | D07 (900) and P01 (903) continue only on `ENDED`. Being more than 200 m from the conversation centre (Mobius's start point, Z halved) at a remark boundary ends them `INTERRUPTED`. Objective 901 and `M09_Mobius_Follow` then never start. Mobius stays alive, so the mission can neither complete nor fail. | `Mission09.cpp:800-966` | Low: the player has to leave Mobius during the first minute | High if hit (hard soft-lock) | **Fixed** (`scripts-a38-m09-intro-conversation-resume.patch`) |
| 2 | Keycard-door wait loop (zone 2000458): `DIST_CHECK` re-tests the distance measured on entry and never re-measures it. A player who enters ahead of Mobius and waits never gets the door check. | `:4424` | Common, because Mobius trails | Medium (stepping out and back in recovers) | **Fixed** (`scripts-a38-m09-keycard-zone-distance-recheck.patch`) |
| 3 | M10-style key-preempts-non-key loss | n/a | Not present on the chain: D07/P01 are key, and key-on-key preemption ends the older one `ENDED`, so the chain advances. D11 (non-key, 901 → re-add 902) starts from the zone's `Animation_Complete`, which a script zone never receives, and 902 is already added in `Entered` (`:425`). Every other non-key conversation has no completion consequence. | None | No change |
| 4 | Completion before activation | `:246-287`, `:3485-3573`, `:2965-3046` | The key counter (2000452) exists from load and counts whether or not an objective is active. A lift moves only from `SET_MOBIUS`, which needs Mobius at the waypoint while STAR is inside, so a late Mobius does not move it, and STAR exiting and re-entering resends `ELEVATOR`. No lift is one-shot. `mobius_in_zone` stays set, but only that same `ACTIVATE` reads it. Objective order cannot block, because `Mission_Complete(true)` ignores objective status. With value-initialised scripts, `M09_Innate_Enable_Zone` now always sends its 4 s second pulse (enemy AI only). | None | No change |
| 5 | Counter under- or over-count | `:2965-3046`, `:4473-4519` | Each keycard grants once and is deleted. Mobius cannot consume one. The door opens on exactly 2, after which the count goes to 3 and is idle. CheckpointA feeds only the tertiary objective 904. | None | No change |
| 6 | Mobius left behind on a one-way lift (1265150, 1265149, 1265126; direction 0 only) if he is not carried during the ride | lift controllers `:3385-3577` | Physics only: script logic cannot move a lift without Mobius at its waypoint, and Havoc cannot ride one alone | High if hit; nothing in the game recovers it | Deferred (needs a hardware repro; a fallback would teleport Mobius to `Mobius_exit_goto`) |
| 7 | The `TOO_FAR` catch-up loop (5 s, at 25 m or more) dies for good after `NO_FOLLOW ON` (zone 1100238): it only re-arms while `!nofollow`, and `NO_FOLLOW OFF` (zone 2000991) does not restart it | `:1331-1348`, `:4384`, `:4755` | Every playthrough, unless OFF arrives within 5 s | Low (Mobius still follows the 56 re-firing `M09_Mobius_Goto` zones, the 4 exit zones, the suit-zone teleport resync `:386/:411` and the evac `FOLLOW` `:565`; walking back through the last Goto zone recovers him) | Deferred: matches retail, and a fix would change following on the normal path. Proposed if hardware shows a lost Mobius: restart `TOO_FAR` on `NO_FOLLOW OFF`. |
| 8 | Save/load and death | n/a | Chain state is saved: follow vars, evac flags, the suit/surface/exit/lift flags, the key counter, and the keycard-zone pointer refetch (a36). The new `escort_started` is save id 2; old saves read it as false, and P01 has already ended in them, so there is no double attach. The lift `mobius` pointers are never read. If a pending `ELEV_WAYPOINT` goto is lost across a load, the lift waits until STAR re-enters. Death restart reloads the level. | Low | No change |

### Fix details

- Intro resume: on `INTERRUPTED` or `UNABLE_TO_INIT` for 900 or 903, start a 1 s
  timer. The 900 path then starts P01 as the original does (P01 waits for the
  audience and has no timeout). The 903 path runs the original hand-off, moved
  unchanged into `Start_Escort`. Both are skipped if Mobius or Havoc is dead,
  and the hand-off runs once (saved flag). The timer, not a synchronous call,
  keeps level-release `Reset_Active_Conversations` (which also delivers
  `INTERRUPTED`) from acting on the outgoing world. The `ENDED` path is
  unchanged.
- Keycard re-check: refresh `mobius` and `mobius_distance` at the top of each
  `DIST_CHECK` pass. Entering with Mobius close, the reply handling and exit
  behaviour are unchanged.
- Both patches are registered after `combat-a37-screen-overlay-opacity-clamp`,
  behind a new anchor on the final pre-pass `Mission09.cpp` (`3674367e…`). No
  existing anchor moved.

### Hardware signatures

- Fix 1: a conversation transition end for action 900 or 903 with reason
  `INTERRUPTED`, followed about 1 s later by objective 901 and the
  `M09_Mobius_Follow` attach. It should never appear on a normal run.
- Fix 2: a `CHECK` from 2000458 to 2000452 while STAR is still inside the zone,
  2 s or more after entry.
- Deferred 6: STAR at the top of a lift while Mobius's Z stays at the lower
  floor after `Static_Anim_Phys_Goto_Frame`.

No runtime, visual or physical claim follows from this pass.
