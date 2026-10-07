# M03 readiness: source and retail-data trace

Status: source and retail-metadata inspection only. Nothing was built, staged,
launched or run on hardware. The traced chain has no known source blocker, but
Mission 03 is **not accepted**. It needs a Vita3K run and a physical Vita run.
Evidence class: host Python readers over unchanged Vita3K retail data
(`M03.mix`, `always.dat`, `always.dbs`) plus staged source
(`staging/scripts/Mission03.cpp`, line numbers include the selected patches).

## Completion owner

`Mission_Complete(true)` has exactly one live owner in retail M03:

- `M03_Mission_Complete_Zone` (Mission03.cpp:5920-5947). It calls
  `Commands->Mission_Complete(true)` at :5944 the first time anything enters the
  zone. In `m03.ldd`, the zone is level object **2000817**. Nothing in the
  script requires any objective to be finished.
- `M03_Outro_Cinematic` (:1273-1317) is defined, along with its "Finale
  Controller" → `x3_finale.txt` path, but it is **not bound** in `m03.ldd`,
  `m03.lsd` or `objects.ddb`, and nothing attaches it at runtime. This is dead
  in the retail game, so objective 1010 never receives `310,1` there. That
  matches original behavior; it is not a port defect.
- The failure owner is `M03_CommCenter_Arrow` (:6075-6145, object 2009818). If
  the Comm Center (1150002) or the power plant dies before the MCT is poked, a
  4 s `MISSION_FAIL` timer calls `Mission_Complete(false)` (:6095).

`Mission_Complete` goes to the original `CombatManager::Mission_Complete`
(staging/combat/scriptcommands.cpp:1970-1973). Shared campaign continuation is
described in `reports/SINGLE_PLAYER_COMPLETION_WIRING.md`.

## Objective chain (controller 1100004)

The level binds four scripts to 1100004: `M00_Put_Script_On_Commando`,
`M03_Initial_Powerups`, `M03_Objective_Controller` and `M03_Objective_Tracker`.
Custom events of type 300..312 map to objective IDs 1000..1012, and the
parameter selects the action: 1 complete, 2 fail, 3 add, 4 unhide (:185-197).

| Step | Sender (evidence) | Effect |
|---|---|---|
| Intro | `x3_intro.txt` frame 1466 `Send_Custom 1100004,300,3`; frame 1586 `301,3` | Adds 1000 "Locate Comm Center" (:354) and 1001 beachhead (:372) |
| Beach | gunboat 1100003 `M03_Gunboat_Controller_RMV` (:820), `x3b_hoverxplode.txt` → 1212283/1212284 | Completing 1001 drops a power-up and sends gunboat `2000,1` (:634-651) |
| SAMs | `M03_SAM_Site_Logic` (:5009) → 302/304; `x3c_bigguns*.txt` → `306,1` | 1002/1004 counters (:574-632) |
| Base entry | type `300,1` → `Complete_Mission_Objective(1000)` sends `BASE_ENTERED` to 1150002 (:524-528) | Comm Center stops self-healing (:6188-6201) |
| Con yard | zone 1144636 `RMV_Trigger_Zone 1100004,308,3` | Adds 1008 "Access mainframe" (:431) |
| Terminal | 1100009 `RMV_M03_Comm_Center_Terminal::Poked` sends `308,1` (:1339) and starts M03CON008; `M03_Mct_Poke` sends `MCT_ACCESSED` to 2009818 (:6166) | When the conversation ends: `SAKURA_DOGFIGHT`, `Grant_Key(5)`, creates "Boss" (:1349-1367) |
| Sakura | "Boss" preset (objects.ddb) carries `Sakura_Killed` (:1235) | When killed: creates "Sakura Crash Controller" (`x3d_sakuracrash.txt`, always.dat) |
| Volcano | `x3d_sakuracrash.txt` frame 356 `Send_Custom 1001001,500,500` | `RMV_Volcano_And_Lava_Ball_Creator` (object 1001001) starts M03CON010, "Volcano Controller" and the lava timer (:1395-1432) |
| Escape | M03CON010 ends → `310,3` (:1439) | Adds 1010 "Escape" (:449-458) |
| Comm Center destroyed | `M03_Comm_Killed` (1150002) → `COMM_KILLED` → 2009818 | With the MCT accessed: `312,1`; otherwise fail (:6113-6143) |
| **Exit** | player enters zone 2000817 | **`Mission_Complete(true)`** (:5944) |

### Lava balls

Timer 1001 picks one of the presets `LavaBall01`..`LavaBall20` and re-arms
itself every 5-7 s (:1442-1563). The index is clamped to 19, and `++x %= 20` is
well defined in C++11. All 20 presets exist exactly once as named records in
`always.dbs:objects.ddb`.

## Retail name resolution audit

A host reader extracted every non-comment string literal in Mission03.cpp
(184 references) and checked each against the unchanged retail archives:

- **Preset names, 63 `Create_Object` + 1 `At_Bone` + 8 explosions:** all
  present in `objects.ddb`. This covers LavaBall01-20, Finale/Sakura
  Crash/Volcano Controller, Boss and Invisible_Object.
- **37 runtime `Attach_Script` names:** all present in the retained live host
  registry (`reports/generated/sweeps/host_script_registry.json`).
- **Level-authored bindings:** 549/549 registered, 0 unregistered
  (`live_script_bindings.json`). The one shape lead is `M03_Killed_Sound`,
  which has one value against two descriptors. Its second parameter falls back
  to the original empty-string → 0 behavior, which is not progression-relevant.
- **Cinematic text files:** all 12 referenced ones are present. X3C_Bigguns,
  X3C_Bigguns2, X3I_GDI_Drop_PowerUp, X3I_TroopDrop1, A-10_1..6 and Orca_1..6
  live in M03.mix or always.dat.
- **38 `Create_Conversation` names:** all present in `conv10.cdb` or the level
  data.
- **Two sound names miss an exact match. Both are cosmetic and behave the same
  as on retail PC:**
  - `earthquake_large_01` (:5540) resolves to `Earthquake_Large_01` because the
    original `Find_Named_Definition` compares with `stricmp`
    (staging/wwsaveload/definitionmgr.cpp:196).
  - `Explosion_Large_07` (:4159): the retail definition name carries a trailing
    space (`"Explosion_Large_07 "`). The lookup misses on PC too, so no sound
    plays. No change was made.

## Pointer-in-int exchanges

Three exchanges pass the address of a stack `int` through the 32-bit custom
event parameter (`port/patches/scripts-a35-host-m03-pointer-exchange.patch`).

- The Vita preprocessing keeps the original `(int)&x` / `(int *)param`. ILP32
  makes this lossless.
- The host-only token wrapper `renegade_script_pointer_exchange.h` exists only
  under `RENEGADE_HOST_ABI_TEST`. No CMake or build script defines that for the
  ARM target, so no host-width assumption leaks into the Vita build.

Why the exchanges are safe on Vita:

1. **Delivery is synchronous.** `Send_Custom_Event` with `delay <= 0` walks the
   observers and calls `Custom` directly (scriptcommands.cpp:650-673). The
   stack object outlives the receiver. None of the three exchanges uses a delay.
2. **The receivers only test for NULL or write through the pointer.** No
   receiver range-checks the parameter. Vita user stack addresses can have bit
   31 set, which makes them negative as an `int`, and that is harmless here.
3. **Collisions were audited.**
   - 5000/6300 are sent only obj→obj at :5881-5892. The sender is
     `M03_Area_Troop_Counter`, which shares object 1144444 with the receiver
     `M03_Reinforce_Area`; the level binds both there. The other 5000 receivers
     (`M03_Tailgun_Fodder_Zone` :4105, objective controller :200) only compare
     values.
   - The constants `UPDATE`, `BASE`, `INLET`, `BEACH` and `ENTERED` are all in
     the 40000 range and cannot alias 3000/5000/6300.
4. **The 3000 escort exchange (:3586-3593 → `M03_Commando_Script` :3094) is
   unreachable in the retail game.** Neither `M03_Commando_Script` nor
   `M03_Chinook_Spawned_Soldier_GDI` is bound in `m03.ldd`/`m03.lsd`/
   `objects.ddb`, or attached by Mission03.cpp or the troop-drop cinematics. The
   other 3000 senders (:1015-1021, :3559) carry `3000,3000` to receivers that
   only compare values (:3406, :4012).

## Defects found and fixed

None. The trace found no Vita-path defect blocking the
start → `Mission_Complete(true)` chain, so no source or patch change was made.
Earlier selected fixes that touch M03-adjacent code remain in place:

- the host pointer exchange
- the RMV engineer dead-pointer round trip
- cinematic dispatch, timing and lifetime patches
- script-timer save admission

## Risks (open)

- **No runtime evidence.** This is unbuilt metadata analysis. Native
  cinematics, lava-ball physics, Sakura's VTOL AI, the conversation callbacks
  and zone `Entered` delivery have not run on Vita3K or hardware.
- **Ordering-dependent failure.** Destroying the Comm Center or power plant
  before poking terminal 1100009 fails the mission by design. Testers must poke
  the MCT first.
- **Performance and memory.** The volcano phase runs the lava timer, ash
  weather, camera shake and "Volcano Controller" together. This phase has not
  been measured.
- **Possible soft locks.** The Sakura chain depends on the "Boss" VTOL dying
  and on frame 356 of the crash cinematic. If the cinematic stalls, the volcano
  chain and the Escape objective never start. Zone 2000817 still completes the
  mission, but its placement relative to objective target 1213908 was not
  derived.
- **Save/load.** Correctness after a mid-mission save (custom timers, lava timer
  re-arm, the `already_entered` flag) has not been tested.

## Physical test route

1. New campaign → M03, or a direct M03 entry if the profile allows it. Confirm
   the intro cinematic finishes and objectives 1000 and 1001 appear.
2. Clear the beach and destroy the village and shore SAMs. Power-up drops
   should appear, and the gunboat should come in.
3. Enter the Nod base. The con-yard zone should add objective 1008.
4. **Poke the Comm Center terminal (MCT) first.** Watch for the M03CON008 audio
   and the Sakura dogfight music.
5. Kill Sakura's VTOL. The crash cinematic should play, followed by the volcano
   (ash, rumble, lava balls every ~5-7 s), M03CON010, and the Escape objective.
6. Destroy the Comm Center (1150002). Expect no mission-fail message.
7. Follow the Escape marker and enter the exit zone (2000817). Expect the
   mission-complete screen and continuation to M04.
8. Return the runtime logs, the flight recorder, any `psp2core` dump, and a
   frame-time sample from the volcano phase.
