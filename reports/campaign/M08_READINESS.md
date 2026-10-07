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
  assets, and original static-scene `Collect_Objects`. `Prepare_Arc_Effect_Data`
  dereferences `Arc Effect` objects without a null check (original). If the
  preset failed to create on Vita, this would crash at boss spawn.
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
