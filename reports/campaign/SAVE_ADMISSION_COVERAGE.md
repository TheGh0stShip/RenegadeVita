# Campaign quicksave vs a36 load-admission coverage (2026-10-07)

Evidence class: static source review of `staging/` (post-patch) against
`upstream/CnC_Renegade/Code`, plus the retail-derived per-map factory
inventory in `reports/generated/sweeps/level_persist_closure.json`. Nothing was
built or run. No host save/load round trip, Vita3K run or hardware run backs
this report.

Question: could a quicksave taken mid-mission in M01-M11 be rejected on load
because an a36 admission rule requires state that the original writer omits?
That happens when the writer emits a chunk conditionally or leaves it out, or
emits a chunk the reader rejects.

## Result

**No definite over-strict rule was found for any campaign object type.** No
code change was made. Every required-state list (the `READ_REQUIRED_*` masks,
`*_seen` predicates and strict `default:` branches) was paired with its
writer. In each case the required item is written unconditionally, or the
requirement is conditional in the same way as the writer. The residual risks
are listed below and need a save/load repro before anyone changes semantics.

## Object and subsystem types per mission

Counts are LSD/LDD factory instances from the closure sweep. Types that exist
only at runtime are marked "rt".

| Type (factory) | M01 | M02 | M03 | M04 | M05 | M06 | M07 | M08 | M09 | M10 | M11 | Admission verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SoldierGameObj (+SoldierObserver) | 152 | 268 | 110 | 134 | 134 | 199 | 140 | 223 | 130 | 155 | 149 | OK. Same loader path M13 reloaded on PSTV in Dev197, which predates most a36 admission patches. |
| VehicleGameObj (Tracked/Wheeled/VTOL phys) | 16 | 48 | 15 | 3 | 27 | 17 | 43 | 35 | 34 | 48 | 19 | OK. `SeatOccupants` are remapped to saved soldiers. |
| BuildingGameObj / BuildingAggregate | 4 | 7 | 3 | 1 | 0 | 1 | 1 | 1 | 0 | 11 | 0 | OK. `BuildingMonitorClass` is a non-persistent observer, but it is only attached through `BaseControllerClass` (gdcnc/gdskirmish), never in the campaign. |
| ElevatorPhys / DoorPhys / StaticAnimPhys | 6/31/58 | 15/41/17 | 7/21/88 | 7/41/2 | 0/2/50 | 0/50/2 | 3/8/50 | 8/82/1 | 0/20/8 | 16/61/14 | 4/39/6 | OK. All have `Has_Dynamic_State()`, so the old pointer is always registered. `Carrier` and `PathAction::Mechanism` only point at them. `Load_State` cannot reject. |
| TransitionGameObj (ladders/entries) | 24 | 16 | 10 | 0 | 0 | 2 | 0 | 0 | 0 | 6 | 0 | OK |
| ScriptZone / DamageZone / PowerUp / Simple | all | all | all | all | all | all | all | all | all | all | all | OK. Lenient `default:` branches. |
| Spawners (SpawnerClass) | yes | yes | yes | yes | 56 | yes | 83 | yes | yes | yes | yes | OK. Strict 7-value mask, all written unconditionally. See R2. |
| Bosses: Sakura (VTOL), Mendoza, Raveshaw | – | Sakura, Mendoza | Sakura | – | Mendoza | Mendoza | – | Raveshaw, Sakura | – | – | – | OK. All factories are linked (`BOSS_CLASS_SUPPORT.md`). `TiberiumEffect` is constructed in the ctor, so its chunk is admissible. |
| CinematicGameObj (rt) | all | all | all | all | all | all | all | all | all | all | all | OK. Parent-status only. |
| BeaconGameObj (rt, M10 drop, player beacons) | – | – | – | – | – | – | – | – | – | yes | (yes) | OK. Lenient loader. An unresolved legacy arming beacon is deleted post-load, not rejected. |
| C4 / SAMSite / SpecialEffects (rt) | as used | | | | | | | | | | | OK. Parent-status only. |
| Conversations (ConversationMgr, ActiveConversation, Orator) | all | all | all | all | all | all | all | all | all | all | all | OK. Exactly one category chunk, written as `CATEGORY_LEVEL` by `savegame.cpp:225`. `ConversationActionCode` pointer, see R4. |
| Encyclopedia | all | all | all | all | all | all | all | all | all | all | all | OK. Writer always emits `TYPE_COUNT` type chunks plus variables. Bit-vector size is fixed by INI at `init.cpp:1013`, and `Reveal_Object` never grows it. |
| CombatSaveLoad 15 manager chunks | all | | | | | | | | | | | OK. All 15 chunks are written unconditionally. `CombatManager` difficulty/first-person bits are required only when `!first_load`, which matches the writer. |
| Audio dynamic scene, physics LDD | all | | | | | | | | | | | OK. Audio needs both children or neither, which matches the writer. Physics needs variables only. |
| Script state (ScriptManager) | all | | | | | | | | | | | OK. A missing script registers its observer pointer as NULL. Unknown variable ids are ignored. Gaps are in `SCRIPT_SAVE_STATE_GAPS.md`. |

## Residual risks (ranked; none confirmed)

- **R1 (medium, structural).** An unresolved pointer remap is now fatal
  (`wwsaveload-a36-unresolved-remap-admission.patch`). Upstream NULLed the
  pointer and asserted only in debug builds. The original does tolerate one
  case on purpose: `ScriptableGameObj::On_Post_Load` purges NULL observers.
  Every campaign observer type is registered: scripts (including NULL
  registration for unrecreatable scripts), `PersistentGameObjObserver` and
  `SoldierObserver`. Not individually traced:
  `pilot.cpp`/`vehicledriver.cpp` `m_CurrentPath` (M03/M08 VTOL and AI
  drivers), `action.cpp` `PathSolver`, `weapons.cpp`/`soldier.cpp` weapon
  models, `animcontrol` `Model`, `ccamera` `HostModel`, `weaponview`
  `HandsPhysObj` and Raveshaw `ArcObjects`/`ThrownObject` (M08). Each would
  also have hit `WWASSERT(0)` in the original debug build. If a mid-mission
  reload fails with `ok=false` after
  `PointerRemapper.Process()`, look here first. Capture the
  `Failed to re-map pointer` file/line before relaxing anything.
- **R2 (low).** Spawner script name/parameter strings are capped at 256 bytes
  including the NUL (`spawn.cpp` load). Upstream read an unbounded WWString.
  Retail level data goes through the same `SpawnerClass::Load` at level start,
  and spawner script lists do not change at runtime. Every map that loads
  therefore already proves its spawners fit.
- **R3 (low).** `Load_Static_Object_States` now rejects a saved static-object
  id that no longer resolves. Upstream logged and skipped it. Static objects
  are only added from level data, and nothing in combat, commando or scripts
  removes them. IDs are stable across reload.
- **R4 (none in practice).** `ConversationActionCode::Save` writes its
  `ActiveConversation*` only when `Find_Conversation(active->Get_ID())`
  matches. Active ids start at 1000 and level conversation ids at 1, so the
  pointer is effectively never written and cannot fail a remap.
  `PhysicalGameObj::ActiveConversation` is cleared by `Free_Orator_List` on
  every `Stop_Conversation`, the only path that sets `STATE_FINISHED`.

## Recommended validation (when building is allowed)

Run one quicksave/reload per mission at these points: in a vehicle
(M02/M07), riding an elevator (M10/M11), with an AI escort on an elevator
path action (M09 Mobius, M11 Sydney), mid-conversation, and mid-boss for
Sakura (M03), Mendoza (M05/M06) and Raveshaw (M08). Log the first rejecting
loader and any remap-failure file/line. Physical gating is unchanged.
