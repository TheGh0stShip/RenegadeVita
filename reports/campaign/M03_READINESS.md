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
   unreachable in the retail game.** Correction (2026-10-07 full audit):
   `M03_Commando_Script` *is* live. `M03_Initial_Powerups` on 1100004
   attaches it to the star (:3049). The sender, `M03_Chinook_Spawned_Soldier_GDI`,
   is the dead side. Only `M03_Chinook_Drop_Soldiers_GDI` attaches it, on a
   type >4000 custom. That script is not bound anywhere, and
   `X3I_TroopDrop1.txt` sends its `4001` events to 1140011, which does not
   exist in M03. No other M03 sender targets the star with type 3000. The
   other 3000 senders (:1015-1021 → 1000001..3, absent; :3559; the
   `RMV_Trigger_Zone`/`RMV_Trigger_Poked` level bindings → 1122334/1141141)
   reach receivers that only compare or range-check values (:3406, :4012).

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

## Full audit (2026-10-07)

Scope: M03 scripts in `staging/scripts/Mission03.cpp`, excluding `M10_*`, plus
the shared helpers and commands they reach. Inputs were the unchanged Vita3K
retail data, a fresh `tools/audit_mission_content_bindings.py --map M03.mix`
receipt (private `build/`), the retained `live_script_bindings.json`,
`live_script_parameters.json` and `script_parameter_reads.json`, and an ARM
`-fsyntax-only` pass of the patched file. Nothing was built, launched or run.
Line numbers refer to staged lines after all patches.

### Results by area

1. **Bindings and parameters.** 549/549 bindings are registered:
   81 definition, 438 persisted, 30 spawner, 0 unknown. 313 have an equal
   parameter count. 235 are one empty value against a `""` descriptor, which
   is benign. The single short binding is the known `M03_Killed_Sound` (`"0,0"`
   against 2 descriptors on most bindings). `Get_Parameter` returns `""` for
   index -1 or an out-of-range index (scripts.cpp:444-450), so the absent-name
   reads are safe: `Killable_ByNotStar` in `M00_Damage_Modifier_DME` and
   `Offset` in `M00_Play_Sound_Object_Bone_DAY`. Both behave as on retail PC.
2. **Events, timers and IDs.** Of 134 literal `Find_Object` IDs, 114 are
   serialized in `m03.ldd`/`m03.lsd`. The misses are all NULL-safe no-ops and
   match retail:
   - 600042/600056-600065 and 600067-600071 are `Destroy_Object` targets in
     the announce controllers.
   - 1141168 is the `M03_Commando_Script` tailgun hack.
   - 2016365 is a `Join_Conversation` participant.
   - 1000001-1000003 are gunboat 3000 sends.
   - 1140011 is the `X3I_TroopDrop1.txt` `Send_Custom` target.

   The 100018 (M06) and 2000010 (M09) hits are comments or guarded code.
   Spawners 2018880 and 2018881 are present. Every progression custom has a
   bound receiver:
   - intro `300,3`/`301,3`
   - big guns `306,1`
   - hovercraft `600` → 1212283/1212284
   - crash `500,500` → 1001001
   - `310,3`
   - the `COMM_KILLED`/`MCT_ACCESSED` and 2009818 pair

   Timer IDs are self-scoped and checked.
3. **Retail names.** No new progression miss. New retail-identical misses:
   `M03_Initial_Powerups` gives "Shotgun/Sniper/Remote Mine Weapon 1 Clip PU",
   and none of the three exists in `objects.ddb` or the M03 overlays. The
   original `Give_PowerUp` logs and skips them (scriptcommands.cpp:1985-1990).
   The paradrop models and animations (X5D_Chinookfly, X5D_Parachute,
   X5D_Box01-03, H_A_X5D_ParaT_*) are present in always.dat, and `cave_lift`
   is present in M03.mix. Global weapon eject and muzzle-flash definition IDs
   2163-3413 are not located. They are shared by every map and not M03-owned.
4. **Crash review.** Mission03 dereferences no raw pointers outside the three
   pointer exchanges. Every other access goes through `Commands->`. All but
   five commands null-check their `GameObject*` arguments. The five unchecked
   ones are `Create_3D_Sound_At_Bone`, `Create_3D_WAV_Sound_At_Bone`,
   `Monitor_Sound`, `Create_Sound` (the creator is optional) and
   `Innate_Disable`/`Enable` (these delegate to a checked function). The M03
   calls to the unchecked ones pass the callback owner, or the result of
   creating a present preset.

   Bounds checked:
   - SAM ignore list (<10)
   - lava-ball switch (clamped to 19)
   - `exploc[Get_Int_Random(0,15)]` (the helper clamps to the maximum)
   - flyovers[17]
   - announce controllers: every branch that sends `play_klaxon` sets
     `klaxon`, and `sound` indices are within 19/28/15
   - `M03_Beach_Radio` conv[3]
   - Reinforce_Area 8000 params (0..2 from the level)

   The `% target_count` divisor is ≥3 or set to 1000, never 0. The 5000/6300
   receivers in `M03_Reinforce_Area` write through the parameter without a
   NULL check. Only same-object synchronous sends reach them. The only other
   5000 senders target 1100004, which compares values, and 1141168, which is
   absent.
5. **Objective chain.** The chain is unchanged and intact. Exit zone 2000817
   runs `M03_Mission_Complete_Zone` → `Mission_Complete(true)`. 1100004
   carries the controller, tracker and initial power-ups. The terminal
   1100009 carries `M03_Mct_Poke`, `RMV_M03_Comm_Center_Terminal` and
   `RMV_Trigger_Poked`. 1150002 carries `M03_Comm_Killed`. Volcano 1001001,
   Sakura `Boss` → crash controller, `DLS_Volcano_Active` 1300001.
6. **Port patches on Mission03.** Three patches touch the file:
   - `scripts-a35-host-m03-pointer-exchange.patch` is host-only under
     `RENEGADE_HOST_ABI_TEST`. The ARM build keeps the original `(int)&`.
   - `scripts-a36-m03-save-variable-ids.patch` (count2 ID 2→3) is correct.
   - `scripts-a36-m03-paradrop-param-buffer.patch` is new.

### Defect fixed

- **Mission03.cpp:4712-4713 (`M03_Chinook_ParaDrop::Created`)**, high
  severity (stack overflow on the beach/inlet path).
  `char params[10]; sprintf(params,"%d",Get_ID(obj))`. The owner is always a
  runtime-created `Invisible_Object` from `M03_Beach_Reinforce` (2018061) or
  `M03_Inlet_Nod_Reinforcements` (1141180), so its ID is a dynamic ID
  (≥1500000000, networkobjectmgr.h:58). Formatting it writes 11 bytes into a
  10-byte buffer. Fix: `port/patches/scripts-a36-m03-paradrop-param-buffer.patch`
  (16 bytes, `snprintf`), registered after the M03 save-ID patch. It applies
  at zero fuzz, staging exited 0 with 526 patches, and ARM `-fsyntax-only`
  exits 0. Output text is unchanged.

### Deferred or open (no change)

- **Announce controllers.** The three announce controllers on
  1100009/1150003/1144606 dispatch on `param` only, not on `type`. `sound` and
  `klaxon` are uninitialized until the first `pick_sound`. Any external custom
  event with param 23 or 24 that arrives before then would index with garbage.
  No such sender was found in M03. This is original behavior and is left
  as-is.
- **Re-attached commando script.** `M03_Commando_Script::Destroyed` →
  `12176` re-arms `M03_Initial_Powerups`, which re-attaches the script and
  re-grants keys. This is original behavior. Save/load and respawn interaction
  is unmeasured.
- **Runtime evidence.** The paradrop, the `Create_3D_Sound_At_Bone` lifetime
  and the conversation callbacks still need Vita3K and physical runs. Nothing
  here proves runtime or visual correctness.

## Soft-lock hunt (2026-10-07)

Scope: `M03_*` scripts, `Sakura_Killed`, `RMV_M03_Comm_Center_Terminal`,
`RMV_Volcano_And_Lava_Ball_Creator`, `DLS_Volcano_Active` and the M03
cinematics. The `M10_*` scripts in Mission03.cpp were left alone. Evidence
class: staged source plus read-only host parsing of the unchanged Vita3K
retail `M03.mix`/`always.dbs`/`always.dat`. Checks run: ARM `-fsyntax-only`
of the patched file (exit 0, 139 warnings, the same count as the unpatched
file) and host `tools.test_m03_pointer_exchange` plus
`tools.test_custom_event_delivery` (OK). Nothing was built, launched or run on
a device. Line numbers are staged lines after all patches.

### Completion path and conversation key flags

- `Mission_Complete(true)` has one owner: star-only zone 2000817 (definition
  519, `check_stars_only`) at (-298.3, 78.2, 6.3), :6033. No objective gates
  it. The only locked door between the base and that area is the key-6 door
  (definition 328960015) at (-159.8, 61.7, 8.8). Key 6 comes only from
  `Sakura_Killed::Killed` (:1358). Sakura's "Boss" is created only when
  M03CON008 ends (`RMV_M03_Comm_Center_Terminal`, :1430-1456). M03CON008 is
  started by the first star poke of terminal 1100009. Basement doors use
  keys 1/2 (key-1 door at (-102.8, 33.7, -2.0), under the Comm Center at
  (-104.2, 38.3)). Key 1 comes only from officer 1144682's `Level_01_Keycard`
  drop (:4732).
- Key flags from `m03.ldd` (`ConversationClass` `VARID_ISKEY` = 13). **Key:**
  M03CON001-008, 010, 012 and 026. **Not key:** 009, 011, 013-025, 027-054
  and 061-068. M03CON008 and M03CON010 are key, so `Start_Conversation`
  never pre-empts them, and their handlers ignore the reason. A later key
  conversation stops them through `ConversationMgrClass::Think` with ENDED,
  which still notifies the monitor. The hard chain has **no reachable
  conversation drop**.
- Sakura can be finished only by star damage (`Damaged` heals below 5 HP for
  other damagers). M03 places no drivable vehicle and creates none at runtime
  (only the AI gunboat, harvester and turrets), so a vehicle damager cannot
  occur.
- `Level_01_Keycard` never expires. `PowerUpGameObj::Expire` is reached only
  through the script command, and M03 never calls it.

### Fixed (one patch per issue, registered after the M03 paradrop patch)

Each fix stores state in a new saved controller variable on 1100004 (ids
9-12). Saves without those ids load with the flag clear, which is the
original behaviour. On the normal ordering the new branch is never taken.
Staging: 548 ordered patches, zero fuzz, exit 0.

| Patch | Issue | Site | Reachability | Severity |
|---|---|---|---|---|
| `scripts-a38-m03-keycard-objective-late-add` | Keycard pickup (307,1) arrives while key conversation M03CON004 still plays, before its end callback adds 1007 (307,3). The completion is dropped and primary 1007 stays pending. | add :458-470, complete :637-640 | Plausible: officer already dead near the basement-door zone (2013086/2013087). Killing the officer *during* M03CON004 is safe, because M03CON005 (key) stops M03CON004 with ENDED first. | Medium (primary objective) |
| `scripts-a38-m03-mainframe-objective-late-add` | Terminal poke (308,1) before any 308,3. Zones 1144502 and 1100005 delete themselves through their own `RMV_Trigger_Zone` on the same entry, so the M03CON003 → M03CON002 → 308,3 callback chain and the 2 s M03CON002 timer never run. After a west-elevator entry, 308,3 comes only from con-yard zone 1144636 (x = -131.7, between the elevator and the key-6 door). | add :484-496, complete :642-645 | Plausible: elevator to Comm Center, poke, then cross 1144636 heading west. Placement relative to the elevator exit is not derived. | Medium (primary objective) |
| `scripts-a38-m03-shore-sam-objective-late-add` | Both shore SAMs (300058/300059, 304,1) die before key conversation M03CON026 (zone 1100007/1100015) ends and adds 1004. | add :127-140, count :683-686 | Reachable: SAMs killed from range or by the gunboat (`cannon_targets`) before the zone, or during the conversation. | Low (secondary objective) |
| `scripts-a38-m03-village-sam-objective-late-add` | Both village SAMs (300056/1100020, 302,1) die and M03CON020 finishes before zone 1100006 → `M03_Chinook_Fodder_Creator` sends 302,3 (add). | add :421-433, report :161 | Reachable: SAMs killed by the gunboat at the village or from range before the zone. | Low (secondary objective) |
| `scripts-a38-m03-village-sam-report-fallback` | Completion of 1002 is only the end callback (100020) of **non-key** M03CON020 (:661). A key conversation that is playing (M03CON026 or M03CON005) pre-empts it before `Monitor_Conversation`. | timer :666-669, :325-328, `Report_Village_Sams` :734-743 | Narrow: the second village SAM dies while a key line plays. 30 s fallback; the two-remark conversation reports first on the normal path. | Low (secondary objective) |

### Unreachable, retail-identical or deferred (no change)

- **Intro chain (`M03_Intro_Substitute`, :3837).** Objectives 1000 and 1001
  are added only through the end callback of non-key M03CON039, started by
  an 8.5 s timer. The chain is M03CON039 → M03CON001 → 300,3 → M03CON012 →
  301,3. No level, preset or cinematic data in `M03.mix`, `always.dbs` or
  `always.dat` references `x3_intro.txt`, so this chain is the only adder.
  That corrects the "Intro" row of the objective-chain table above.
  Pre-emption needs a key conversation within the first 8.5 s, and
  none can start that early (all key lines are base, cannon or terminal
  lines). Unreachable.
- **1000 / BASE_ENTERED on the west route.** The zone self-deletion above
  also drops conv-3's 300,1. After an elevator entry, 1000 completes and the
  Comm Center becomes damageable only when con-yard zone 1144636
  (`M03_ConYardSeen`) is crossed. The designers suppress that zone through
  900 from the east zone 1100005. Retail-identical. It is left alone because
  a fix would move 1000's completion earlier on the west route. Needs a
  route check on Vita3K.
- **Gunboat killed by anything except the shore cannon.** No
  `GUNBOAT_KILLED` is sent, so 1001, 1002 and 1004 are neither failed nor
  completable: 302/304 are dropped while 1100003 is gone (:203), and
  `M03_Beach_Scenario_Controller` needs the gunboat. This is a design rule
  (protect the gunboat), and the gunboat carries `M00_Damage_Modifier_DME`.
  Deferred.
- **Escape 1010.** Its only completer (310,1) is the unbound
  `M03_Outro_Cinematic`. This is retail-identical, and the exit zone
  completes the mission anyway.
- **Keycard placement.** `Level_01_Keycard` is created at the officer's
  death position + 0.5 m and has no alternative source, so a drop in an
  unreachable spot cannot be recovered. Retail-identical. Officer placement
  was not derived.
- **Key 5 revoke.** `Grant_Key(STAR,5,false)` (:1451) locks the east key-5
  door (-47.4, 44.4) after M03CON008. The exit route runs west through the
  key-6 door. Retail design.
- **Commando re-arm.** `M03_Commando_Script::Destroyed` → 12176 →
  `M03_Initial_Powerups` re-grants key 5 only to a live star. The star is
  destroyed only on death or teardown, so no live star is re-armed.
  Unreachable.
- **Counters.** The beach counter has exactly four senders (1144677, 1144448,
  1144731, 1144732; `RMV_Trigger_Killed`). The SAM counters have two senders
  each. None filters on the killer (`M00_Trigger_When_Killed_RMV` fires on
  any `Killed`). No undercount except the gunboat rule above.
- **Save/load.** Keys persist in `SoldierGameObj::KeyRing`. The runtime "Boss"
  and the active M03CON008 monitor are saved and relinked. Loading while
  M03CON008 plays delivers INTERRUPTED to the old world's terminal script
  during `Release_Level`, which creates a Boss that `Destroy_All` removes.
  This is retail-identical.

Physical signature for the fixes: an objective that is added already
accomplished prints a new-objective line followed by a status-changed line in
the same frame. If 1002 is reported by the fallback timer, the
`M03CON020` transition-end record has no kind-3 observer call, and 1002
becomes accomplished 30 s after the second village SAM dies.
