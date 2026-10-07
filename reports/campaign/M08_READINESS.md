# Mission 08 readiness — 2026-10-07

Evidence class: source inspection, read-only retail metadata audit, staging
replay, host and ARM single-file syntax checks, Python source contracts. No
build, no emulator or Vita run. Native M08 completion is **not** accepted yet.

## Source identity and case

- Shipped unit is lower-case `Code/Scripts/mission08.cpp` (Scripts.dsp:
  `SOURCE=.\mission08.cpp`); staging, `CMakeLists.txt:366` (campaign
  inventory, Scripts.dsp-checked) and `:659` (M08 call-defaults include) all
  use the same lower-case name. Its `#include "mission8.h"` resolves through
  the staged lower-case alias of upstream `Mission8.h`. No case defect.
- All 44 Scripts.dsp units link into the executable (not a static library),
  so every `DECLARE_SCRIPT` registrant in `mission08.cpp` is present.
- `RaveshawBossGameObj`, `SakuraBossGameObj` and `MendozaBossGameObj` are
  compiled (`cmake/A35MultiplayerBuildingSources.cmake:16-18`) and
  force-linked (`staging/combat/objlibrary.cpp:137-139`).

## Objective chain to success (staged line numbers)

| Step | Owner | Location |
|---|---|---|
| Controller adds 801/808/809; music | `M08_Objective_Controller` on serialized 100002 | `mission08.cpp:58-69` |
| Havoc start state (pistol, key 10) | `M08_Havoc_DLS` = level combat start script | `mission08.cpp:285-296` |
| 801 done, 802 added after M08_CON001 | `M08_Activate_Objective_802` zone | `mission08.cpp:383-386` |
| 803 added | `M08_Activate_Objective_803` (2 zones) | `mission08.cpp:393, 445` |
| Midtro starts, Havoc moved to 111994 | `M08_Activate_Midtro` on zone 1500225 | `mission08.cpp:6813-6846` |
| Frame 1940 `Send_Custom 100002, 8047` | retail `x8a_midtro.txt:69` (M08.mix) | Test_Cinematic |
| 803 accomplished, relocate Havoc | controller `M08_RELOCATE` | `mission08.cpp:264-272` |
| Havoc to 108819, 805 added, boss music, `Create_Object("Raveshaw")` | `M08_Havoc_DLS::Custom` | `mission08.cpp:300-320` |
| Boss death sequence (circling catwalk, health <= 20) | `RaveshawBossGameObjClass::Apply_Damage_Extended` | `raveshawbossgameobj.cpp:1162-1200` |
| **`CombatManager::Mission_Complete(true)`** 2 s after landing | `STATE_IMPL_THINK(RAVESHAW_STATE_DEATH_LANDING)` | `raveshawbossgameobj.cpp:2801-2810` |
| Latch to original campaign intermission | `A31VitaCombatMiscHandler` | `port/platform/a31_gameplay_boundary.cpp:418-424` |

The controller's own `Mission_Complete(true)` (`mission08.cpp:235-238`, on
805/1) is reachable only from `M08_Raveshaw::Killed`. That script has no
binding in M08 level data or on the `Raveshaw` preset, so retail success comes
from the boss class. The latch keeps the first result, so the boss calling it
every think tick after the timer is safe.

Retail metadata (`tools/audit_mission_content_bindings.py --map M08.mix`):
790 serialized objects, 82 spawners, 714 level bindings, 96 discovered
scripts, 0 binding decode findings, 0 unknown scripts, 0 missing literal
presets, 0 missing texts. Every ID on the chain above is serialized (100002,
108360, 108361, 108818, 108819, 111994, 1500225). The `Raveshaw` preset
82160001 uses the Raveshaw boss persist chunk `0x0004014C`, which a host
compile of `combatchunkid.h` confirmed. `Raveshaw Boss Fodder`, `Arc Effect`,
`Explosion_Raveshaw_Bodyslam`, `Raveshaw Boss Override` and
`Mutant_3Boss_Raveshaw` all exist. The 19 not-located definition IDs are
weapon/twiddler typed-field leads, the same class already recorded for other
maps.

## Sakura

M08 has no Sakura boss encounter. `M08_Sakura` (spawner 100773, spawned by
`M08_Activate_Sakura`) is a friendly GDI-team soldier escort in Petra canyon
(`mission08.cpp:5683-5845`). The only `SakuraBoss` definitions are `Boss`
(82120001, `Sakura_Killed`) and `M03_Cinematic_Boss`, and M08 reaches neither.
`M08_Sakura` sends its ID to 100356, which is absent from the retail data, so
`M08_Move_Sakura` (zone 109604) never learns her ID and her second move does
not happen. This is retail behaviour, it is not on the completion path, and the
port leaves it alone.

## Defects fixed

1. **`M08_Mobile_Vehicle` out-of-bounds slot read**: 7 retail bindings.
   `Created` seeds `loc = 100` and only the first 1 s `GOTO_LOC` timer selects
   a slot. If `Enemy_Seen` arrives earlier, or the timer finds no location
   under 1000 m, `attack_loc[100]` reads 89 ints past an 11-int member array.
   On Vita that is heap UB. New patch
   `port/patches/scripts-a36-m08-mobile-vehicle-attack-slot.patch`, applied
   after the Apache bounds patch, adds `Current_Attack_Location_ID()`, which
   returns 0 (no such object) for an unselected slot. Behaviour stays the same:
   before the timer, action 10 does not exist yet, so original `Modify_Action`
   (`scriptcommands.cpp:127-140`) already does nothing, and an unresolved ID
   moves the vehicle to `Get_Position(NULL)` exactly as before. Staging replay:
   inventory PASS, 507 ordered patches. Host and `arm-vita-eabi-g++`
   `-fsyntax-only` pass. `tools/test_m08_readiness.py` passes (5 tests).
2. The audit tool now maps `M08.mix` to `mission08.cpp`, so literal lookups
   are classified for every M08 script, not only the discovered closure.

Earlier fixes still apply: Apache controller bounds
(`scripts-a35-apache-controller-bounds.patch`), Raveshaw and Sakura
save/load status propagation (`combat-a36-boss-*-status.patch`) and
cinematic command bounds/timing.

## Remaining risks (no source defect proven)

- Raveshaw needs `DamageableStaticPhys` lightning rods with bone `BBZZZT`
  within 40 m of `TIBERIUM_POS`, the `CAMBONE` and `bluetibeffect.tga`
  assets, and original static-scene `Collect_Objects`. Upstream
  `Prepare_Arc_Effect_Data` dereferenced `Arc Effect` objects without a null
  check; `combat-a36-raveshaw-arc-effect-null-guards.patch` now skips the
  cosmetic lightning effect when the helper objects, their models, or fewer
  than two lightning rods are missing (behaviour unchanged when they exist).
  ARM syntax-checked only; not exercised on the Vita.
- Death needs the boss to reach `MOVE_STATE_CIRCLE_CATWALK` with health <= 20,
  and a 1-in-5 random roll per hit. Untested on Vita physics or pathfinding.
- The midtro is 1945 cinematic frames. Relocation depends on Test_Cinematic
  reaching frame 1940. Under-speed only delays it, but a stalled cinematic
  would block 805.
- `Remove_Pog(805/806)` clear the wrong POG IDs. This is a cosmetic original
  bug and is kept.
- Not checked here: M08 placement in retail `campaign.ini`, and the M08→M09
  handoff (campaign data owns these). 100389 (Petra C controller) is still
  absent, as already recorded for the M13 cross-map lead.
- Saving or loading inside the boss arena is covered only by the boss
  save-status source patches. Restore of a mid-fight save has not been run.

## Physical test route

1. Start M08 from New Campaign or Mission Replay. Expect `08-Sniper.mp3`,
   pistol only, objective 801 shown.
2. Leave the prison with the warden's Level 2 keycard. Enter the 802 zone.
   Expect M08_CON001, 801 accomplished, 802 added.
3. Cross Petra canyon. The Apache waves and the Sakura escort are optional.
   Enter the research facility (803 zone, M08_CON002).
4. Ride the elevator into the midtro zone. Watch X8A_MIDTRO through to fade.
   Expect 803 accomplished, Havoc relocated, 805 added,
   `Raveshaw_Act on Instinct.mp3`.
5. Fight Raveshaw until he collapses from the catwalk circle. About 2 s after
   landing, expect the success flow and the campaign intermission or score
   screen.
6. Pull `ux0:data/renegade/user/logs/` and record cinematic frame progress,
   the mission-completion latch and any PSP2 dump. Quicksave once before step 4
   and once inside the arena, then reload both.

## Full audit — 2026-10-07

Evidence class: read-only retail metadata (`tools/audit_mission_content_bindings.py
--map M08.mix`, `tools/audit_mission_conversations.py --map M08.mix`, MIX
index lookups through `renegade_cinematic_dependency_scan.MixArchive`),
`reports/generated/sweeps/live_script_parameters.json`, manual source review,
zero-fuzz staging replay (527 ordered patches, inventory PASS), ARM
`-fsyntax-only` of `raveshawbossgameobj.cpp`, `tools/test_m08_readiness.py`
(8 tests). No build, emulator or Vita run. Detailed receipts stay under the
ignored `build/m08-audit/`.

### 1. Script bindings and parameter counts

- 766 discovered bindings (714 level, 52 definition), 80 distinct bound
  scripts, 96 scripts in the discovered closure, 0 unknown/unregistered, 0
  binding decode findings. Owners: `mission08.cpp`, Toolkit*, Test_DAK/DAY/RMV,
  `Mission05.cpp` (`M05_APC_Deploy`) and `Test_Cinematic.cpp`; all are
  Scripts.dsp units linked into the executable.
- Positional shape (sweep row `M08.mix`): 344 equal, 421 "excess" and 1
  unrecorded, 0 fewer. Every excess row is one placeholder value on a
  zero-parameter descriptor, the editor pattern seen in all 27 maps, and is
  never read. The unrecorded row is `M08_Havoc_DLS`, the combat start script,
  which has no parameters.
- Index-like parameters are in range: `M08_Elevator_Movement_Zone` (zone
  108588) passes `Anim_num=0` into `elevators[1]`.
  `M08_Mobile_Vehicle` slots are bounded by the earlier patch.

### 2. Custom events, timers and hard-coded IDs

- Completion chain receivers are present: 802/803 zones → controller
  100002 (`801/802/803`, params 1/3 after M08_CON001/M08_CON002 end).
  Retail `x8a_midtro.txt:69` sends `100002, 8047, 0`, which reaches the
  controller's `M08_RELOCATE`. That handler sends `803,1` to itself and
  `M08_RELOCATE` to STAR, and `M08_Havoc_DLS` (the combat start script) handles
  it.
- Retail-identical unreceived events, both harmless: `M08_STAR_IMMORTAL` to
  STAR (`M08_Immortal_Star_DLS` is not bound or attached anywhere), and the
  controller's `HAVOCS_SCRIPT` timer, which has no `Timer_Expired` (the base
  no-op).
- 119 literal `Find_Object` IDs. Not serialized: 100326/100327
  (`M08_Activate_Convoy`), 100262/100289 (`M08_Activate_PetraA21`), 100347,
  100362 and 100436. These are all in scripts outside the bound closure.
  In-closure misses 100389 (Petra C) and 100356 (Sakura) were already
  recorded. Every use goes through `SCRIPT_PTR_CHECK` NULL-tolerant commands,
  so none is a crash risk.

### 3. Content resolution

- Cinematics: all 19 closure `.txt` resolve (10 `M08.mix`, 9 `always.dat`),
  and so do `X8D_CHTroopdrop1/2.txt`. `X8I_TroopDrop1/2/3.txt`
  (`mission08.cpp:1480, 2138, 2149`) are absent from every retail archive.
  Only unbound scripts (`M08_Activate_PetraA21`,
  `M08_Archaelogical_Site_Controller`) reference them. This is a
  retail-PC-identical miss.
- Cinematic dependencies: all 24 models present. 51 of 52 animations are
  present. `s_a_human.H_A_X8A_MLoop` (`x8a_midtro.txt:100`, slot 2
  `Commando_Desert_Midtro`, frames 795–1599) is in no retail archive. This is
  retail-identical. `AnimChannelClass::Set_Animation`
  (`animcontrol.cpp:183-193`) tolerates the NULL `Get_HAnim`, so the midtro
  still runs to frame 1940. It is cosmetic only. The 17 cinematic real-object
  presets (including `Nod_Stealth_Tank` and `Mutant_3Boss_Raveshaw`) and all
  literal script presets resolve (0 missing).
- Media: `08-Sniper.mp3` and `Raveshaw_Act on Instinct.mp3` are in
  `always.dat`. The `POG_M08_*.tga` literals resolve as `.dds` in
  `always.dat` through the original tga→dds lookup. Conversations: 41 level
  conversations, all 40 literal name leads located, 0 invalid orator indices.
  Missing texts: 0.

### 4. Crash-prone code — defects fixed (one patch each)

1. **Raveshaw lightning-strike modulo by zero** (crash, boss arena):
   `STATE_IMPL_THINK(LIGHTNING_ROD_STATE_ACTIVE)` truncates
   `(StarPos - TIBERIUM_POS).Length ()` to `int` and calls
   `FreeRandom.Get_Int (star_dist)`. This is `% max`, guarded only by a
   compiled-out WWASSERT, so it divides by zero when the player is within 1 m
   of `TIBERIUM_POS`. New `combat-a36-raveshaw-star-dist-modulo-guard.patch`
   skips the roll when `star_dist == 0`, at staged
   `raveshawbossgameobj.cpp:3661`. `Get_Int (1)` never returns 1, so the
   original odds are unchanged at every reachable distance.
2. **Unchecked `Raveshaw Boss Fodder` create** (crash if the preset ever fails
   or is not a soldier): `Create_Stealth_Soldier` dereferenced the result
   with only a WWASSERT. New
   `combat-a36-raveshaw-stealth-soldier-create-guard.patch` (staged
   `:3829-3845`) leaves `StealthSoldier` empty instead, after deleting a
   non-soldier object. The caller, `STATE_IMPL_BEGIN(STEALTH_SOLDIER_STATE_DISPLAY)`,
   already handles a NULL `Peek_Stealth_Soldier ()` by roaring and choosing a
   new overall state. The retail preset exists, so normal behaviour is
   unchanged.

Both patches apply after `combat-a36-boss-waypath-release-guard.patch` and
staging replays with zero fuzz.

Reviewed with no defect found: the `Prisoner_Conv_Table` index (bounded to
10–19/20–29 of 30); the flyover index (`Get_Random_Int (0, 7)` into 8); every
`Get_Random_Int` range in `mission08.cpp` is non-empty;
`M08_Nod_Stealth_Tank` (`Action_Attack (NULL)` is the original stop idiom);
`Find_Object_To_Throw` NULL handling; the boss think stops when
`COMBAT_STAR` is NULL or dead; the lightning-rod count >= 2 guard.

### 5. Objective chain

The chain is intact, as in the table above. 801→802 and 802→803 need the
two conversations to end, 803 and 805 come from the midtro relocate, and
`Mission_Complete (true)` comes from `RAVESHAW_STATE_DEATH_LANDING`. None of
the fixes changes the chain.

### 6. Port patches touching M08

The following stage cleanly, in the order recorded in `tools/stage_sources.sh`:

- `scripts-a35-apache-controller-bounds.patch`
- `scripts-a36-m08-mobile-vehicle-attack-slot.patch`
- `combat-a36-boss-save-status.patch`
- `combat-a36-boss-load-status.patch`
- `combat-a36-raveshaw-arc-effect-null-guards.patch`
- `combat-a36-boss-waypath-release-guard.patch`
- the two new guards above

The waypath and arc guards only skip cosmetic work or keep the previous
position when data is missing. They do not alter behaviour when retail data
is present.

### Deferred

- `audit_mission_event_routes.py` needs all-map binding receipts and was not
  run. Custom and timer receivers were traced by hand for the completion
  chain and the boss only, not for all 80 bound scripts.
- Shared Toolkit scripts (M00_*) were not re-audited here for `Get_Random_Int`
  ranges with `min == max`.
- Not checked: a mid-fight save/restore, and the boss landing on Vita
  physics. Both need hardware.

## Soft-lock hunt — 2026-10-07

Evidence class: read-only retail metadata (`m08.ldd` in `M08.mix` and the
global `conv10.cdb` in `always.dbs`, `ConversationClass` micro-chunk 13 =
`VARID_ISKEY`; the same parser reproduces the 23 key conversations recorded
for M10), MIX index lookups, manual staged-source review, zero-fuzz staging
replay (544 ordered patches, inventory PASS, only `raveshawbossgameobj.cpp`
changes), ARM `-fsyntax-only` of the patched file (exit 0, no warnings on the
new lines), `tools/test_m08_readiness.py` (8 tests OK). No build, emulator or
Vita run. Staged line numbers.

### Conversation-drop pattern (M10) — not reachable in M08

- 801→802 (`M08_CON001`, `mission08.cpp:356-363`) and 802→803
  (`M08_CON002`, `:415-422`) call `Start_Conversation` before
  `Monitor_Conversation`, the same order as M10. All 41 `M08_CON*` in
  `m08.ldd` are **not key** (IsKey 0, stored priority 30), and none of the
  3,606 global conversations is key. `ActiveConversationClass::Start_Conversation`
  (activeconversation.cpp:386-401) can therefore never stop them before the
  monitor is registered. Every later stop (AI-state interrupt, audience,
  timeout, key preemption) runs after registration, and both scripts accept
  ENDED and INTERRUPTED. No fix.
- Even a lost callback would not block completion: the midtro zone
  (`M08_Activate_Midtro`, `:6813-6846`) and the boss do not read objective
  state, and `Mission_Complete (true)` comes from the boss class.

### Fixed (one patch)

**Raveshaw jump never lands → boss frozen, death unreachable**
(`combat-a38-raveshaw-jump-grounded-landing.patch`, staged
`raveshawbossgameobj.cpp:3036-3070`). `JUMP_STATE_JUMPING` only ends when a
think sees `velocity.Z < 0` within 2 m of the ground. `PhysicsSceneClass`
splits any frame longer than 1/15 s (`pscene.cpp:138, 353`; frames are clamped
at 1/5 s) into several timesteps. If touchdown is not the last of them, the
following grounded `Normal_Move` leaves `velocity.Z` at exactly 0 while he
stands still (`humanphys.cpp:422-425`), so the window is never seen.
`JumpState` then stays JUMPING for ever. `Jump_To_Point` only starts from
NONE, the action stays paused, `OVERALL_STATE_CHASE_STAR` cannot grab
(`:1352` needs NONE), and `MOVE_STATE_JUMP_TO_CATWALK` never reaches
`MOVE_STATE_CIRCLE_CATWALK`. Health is floored at 1 and death needs that state
(`:1201`), so the mission cannot complete. Reachability: the boss arena on
Vita, during a hitch of more than 67 ms that coincides with a landing. Fast
downward jumps (jump-down from the catwalk, jump-to-star) are the most
exposed. Severity: hard soft-lock (retail PC rarely runs below 15 fps). The
port's `Jump_To_Point` no-flight-solution early return leaves the same
grounded state. Fix: after the unchanged original test, a grounded think
(`Is_In_Contact ()`) with `velocity.Z <= 0` also enters
`JUMP_STATE_LANDING`. Launches with any horizontal component have
`velocity.Z > 0`, and the original test runs first, so normal jumps are
unchanged. It is idempotent: it is evaluated per think and only from
JUMPING. Breadcrumb (at most 4 per run): `A3.8 Raveshaw jump: grounded
landing fallback`.

### Reviewed — no blocker (retail-identical or recoverable)

- (b) Midtro relocate: `x8a_midtro.txt` sends `100002, 8047` at frame 1940
  and `Test_Cinematic` saves and restores Time and slots, so a save during the
  midtro still relocates. 803 is added (CON002 end) long before the 65 s
  midtro reaches 1940. Even reversed, only the 803 objective status would be
  wrong. Completion does not depend on it.
- (c) No counter on the M08 completion path. The Level 2 keycard drops from
  `Killed` (`:937-940`, `:5884-5889`), which is retail behaviour.
- (d) One-shot zones (802, both 803 zones, midtro) latch `already_entered` and
  save it. The elevator zone (`:6902-6930`) re-fires harmlessly (blocker and
  no-fall-damage script per entry).
- (e) Boss loop review. Retail animations `rav_death/jump/heal/grabthrow/
  throw`, `h_a_bodyslam`, `stl_struggle`, `h_a_fly1-4`, `h_a_a0d0` and
  `h_c_a0a0_l07` are all in `always.dat`. `ANIM_MODE_TARGET` snaps to the
  target frame, and a NULL animation reports complete, so the DYING (frame
  43), LANDING, BODYSLAM (174) and DEATH_LANDING (`:2828`) waits terminate.
  The FALL state falls monotonically to hard-coded floor Z. A ROAR during a
  jump re-runs `JUMPING` Begin on resume, which re-launches. Throwing with no
  `(Raveshaw Ammo)` left (`AC Unit`/`Plastic Drum` presets) falls back to
  CHASE_STAR.
- Player out of reach (deferred, retail-identical and player-recoverable):
  `OVERALL_STATE_CHASE_STAR` sets `OverallStateTimer` (`:1333`) but never reads
  it. Its only exit is a grab at ≤1.95 m (3D), and the jump-to-star needs more
  than 8 m. A player standing 2–8 m away but unreachable (for example above
  him) keeps him chasing, and at ≤5 % health he only retreats to the catwalk
  after a grab or throw ends. Moving away more than 8 m or down to him
  resumes the fight. Adding a timeout would change retail pacing.
- (f) Save/load: all nine state machines (with `IsHalted`), timers,
  `StartTimer`, `LastMeleeAnimFrame` and the jump target are saved. Load
  re-collects rods and re-applies the anim override. A save during
  `HAVOC_STATE_GRABBED` restores the state, and `FLYING` re-enables control on
  release. Death/restart reloads the level, and the boss has no static
  gameplay state.

### Deferred

- `ThrownObject` is a raw `SimpleGameObj *` with no liveness check
  (`:1752-1757`, `:3493-3520`). If a player destroys the `(Raveshaw Ammo)`
  object Raveshaw is walking to or holding, that is a use-after-free. The
  `AC Unit`/`Plastic Drum` health and skin were not decoded, so it is not
  known whether this can happen. This is a crash risk, not a soft-lock.
- HAVOC_STATE_FLYING and the thrown-object flight end only on a `Fly_Move`
  hit. The arena is enclosed, so this is retail-identical.
- Physical check: in the boss fight, look for the fallback breadcrumb and
  confirm that the catwalk retreat, the collapse and the success flow follow.

## Follow-up fixes — 2026-10-07

Evidence class: read-only retail metadata (`objects.ddb` in `always.dbs`,
`M08.mix` overlays and `m08.ldd`, `armor.ini` in `always.dat`, all through
`MixArchive`), manual staged-source review, zero-fuzz staging replay (572
ordered patches, inventory PASS, only the files below change), ARM
`-fsyntax-only` of both patched files (exit 0, no warnings on changed lines),
`tools/test_m08_readiness.py` (14 tests) and the conversation-gate,
objective-lifecycle, script-portability, warning-route and sweep-link suites
(59 tests OK). No build, emulator or Vita run. Staged line numbers.

### 1. Raveshaw `ThrownObject` use-after-free — guarded (defensive)

- Destructibility: `AC Unit (Raveshaw Ammo)` (81960250) and `Plastic Drum
  (Raveshaw Ammo)` (81960251) have health 1000, skin Blamo and a 1000 Blamo
  shield. `[Scale_Blamo]` is 0 for every warhead except `BlamoKiller`
  (×10000) and the healing `Repair`/`RegenHealth`. Only
  `Ammo_SAM_Site_Blamo_Killer` and `Ammo_UltimateWeapon` carry BlamoKiller,
  so normal play cannot destroy them. No M08 overlay overrides them.
- Retail M08 does not place them at all: their definition IDs do not occur in
  `m08.ldd` (no 0x4010A instance, no spawner) or any M08 member, and no
  cinematic or script names them. `Find_Object_To_Throw` therefore returns
  NULL and `OVERALL_STATE_THROWING_OBJECT` always falls back to CHASE_STAR.
  The UAF is unreachable on retail data on both counts.
- Fix anyway (cheap, retail-neutral):
  `combat-a38-raveshaw-thrown-object-liveness.patch` (applied after the
  grounded-landing patch; touches `raveshawbossgameobj.h:195, 437` and the
  `.cpp`). A `GameObjReference ThrownObjectRef` is set alongside the pointer
  (`:1315`). The engine clears it on destruction, and `Verify_Thrown_Object`
  (`:1141`) drops the stale pointer at the start of each think (`:1033`) and
  before saving (`:687`), so no dangling pointer is saved or remapped. The
  walk-to think takes the original nothing-to-throw branch, CHASE_STAR
  (`:1807`). FLYING begin/think are NULL-safe (`:3579`, `:3610`). PICKUP and
  the hand link were already NULL-safe. `Find_Object_To_Throw` skips
  delete-pending objects (`:4280`). The save format is unchanged: the pointer
  is still saved and remapped, and `On_Post_Load` rebuilds the reference
  (`:872`). Breadcrumb (at most 4): `A3.8 Raveshaw thrown object: destroyed
  before landing; dropped stale pointer`.

### 2. The five REVIEW gates — receivers resolved

All four zone gates send to 100002, where `M08_Objective_Controller::Custom`
handles them (param 3 → `Add_An_Objective`, param 1 → accomplished). The
co-attached `M08_Flyover_Controller` has no `Custom`.

| Gate | Effect | Class |
|---|---|---|
| `M08_Activate_Objective_802` (zone 100007, `M08_CON001`) | add primary 802, accomplish primary 801 | fixed (defensive) |
| `M08_Activate_Objective_803` (zones 100008/100009, `M08_CON002`) | add primary 803 (also revokes key 10), accomplish 802 | fixed (defensive) |
| `M08_Activate_Objective_804` (zones 100003/100004, `M08_CON003`) | add secondary 804 | fixed (defensive) |
| `M08_Activate_Objective_806` (zone 100018, `M08_CON004`) | add secondaries 806 and 807 | fixed (defensive) |
| `M08_Warden_Announcement1` (zone 100049, `M08_CON006`) | none: the zone's only script has no `Action_Complete`, and the conversation's 300502 completion is delivered only to 100049 | NO EFFECT (the tool's approximate cross-script match is a false positive) |

No gated objective is on the completion path, because
`Mission_Complete (true)` comes from the boss class, and no M08 or global
conversation is key. The key-preemption drop therefore cannot happen on
retail data. The M10 pattern is applied anyway:
`scripts-a38-m08-objective-conversation-monitor-first.patch` (applied after
the mobile-vehicle slot patch) moves `Monitor_Conversation` before
`Start_Conversation` (`mission08.cpp:368, 434, 501, 567`). It also adds an
`objective_sent` flag, saved with id 2 and value-initialised, so older saves
load it as false. With that flag each send happens exactly once
(`:389, 456, 524, 578`). Timing and effects are unchanged when no key
conversation plays. A scratch rerun of `tools.audit_conversation_gated_objectives
--mission M08` reports FIXED 4 / NO EFFECT 2 / REVIEW 1, and the remaining
REVIEW is Warden1. The shared `CONVERSATION_GATED_OBJECTIVES.md` was not
regenerated in this round.

### 3. CHASE_STAR never reads `OverallStateTimer` — assessed, no change

`STATE_IMPL_BEGIN(OVERALL_STATE_CHASE_STAR)` sets a 6–20 s timer (`:1382`)
that nothing reads. The state ends only on a grab within `ARMS_REACH`
(1.95 m 3D, `:1395`). `MOVE_STATE_FOLLOW_STAR` only jumps to a player more
than 8 m away (`:1919`), and the roar from `RAVESHAW_STATE_NOTHING` does not
re-decide. A player 2–8 m away but unreachable, for example standing on
geometry more than about 1.7 m above him, keeps him chasing. During that
time he cannot reach `MOVE_STATE_CIRCLE_CATWALK`, which death needs
(`:1249`), and the ≤5 % retreat (`:4337`) waits for the next decision. The
player can always break the chase, though: step down within reach, or move
more than 8 m away (1-in-5 jump roll every 0.75 s, then the normal decision
cycle). Nothing in the original state machine removes that option, so the
fight cannot become unwinnable. Adding a timeout would change retail pacing,
so no fallback was added. This stays retail-identical and deferred.

### Deferred

- Regenerate `CONVERSATION_GATED_OBJECTIVES.md` (needs a coordinated
  all-mission run).
- Hardware: an M08 run with a mid-fight save/reload. Expect no
  `Raveshaw thrown object` breadcrumb on retail data.
