# M02 readiness (source + retail-data evidence)

2026-10-07. This is based on host source inspection and a read-only scan of
retail `M02.mix` (the Vita3K ux0 copy; its hash is in
`CAMPAIGN_SOURCE_MAP_RECONCILIATION.md`). Nothing was built, Vita3K was not
launched and there is no physical evidence. This report does not prove that
M02 completes on hardware, and the physical gates remain open.

## Objective chain to `Mission_Complete(true)`

All line numbers refer to `staging/scripts/Mission02.cpp` unless another file
is named.

1. `M02_Objective_Controller::Created` (59-97) runs on object 1111112
   (`M02_OBJCONTROLLER`, `mission2.h:48`). It starts the music, turns off
   hibernation, sets primary 201 to pending and tertiary 222/223 to hidden,
   and starts timer 201, which plays `M02_PRIMARY_01_START`.
2. Zones and units activate area objectives 202-221 with
   `Send_Custom_Event(.., id, 0)`. `Add_An_Objective` (343) indexes
   `Objective_Radar_Locations[id-202]`, which has 20 entries
   (`mission2.h:53`). Every activated id is in 202..221, so the index stays in
   bounds. Completions arrive as `(id, 1)`: Obelisk 202 (3935/4007), Dam MCT
   203 (4072) and helipad 206 (4090).
3. Keycard gate: zone 301601 (552) checks `Has_Key(STAR, 6)`.
4. Midtro: zone 400193 (838-852) does the following:
   - creates `Invisible_Object`;
   - disables star control;
   - starts zone timer 9 (1 s);
   - sends controller custom 1000/1002 with a 25 s delay, which gives
     `Level_01_Keycard` (195);
   - attaches `Test_Cinematic` with `X2K_Midtro.txt`.
5. Zone timer 9 (1821-1875) does the following:
   - teleports the star to the rooftop and re-enables control;
   - spawns `Nod_Jet` with `M02_Nod_Jet_Waypath`;
   - completes 201 and activates final primary 205 (timer 205 plays
     `M02_PRIMARY_04_START`, with a 120 s reminder);
   - wakes A21;
   - creates Mendoza (`Nod_FlameThrower_3Boss` + `M02_Mendoza`) and sends his
     ID to end zone 400194 as custom 999.
6. Mendoza (5059+): when his armor runs out he runs to (1260,535,18) and
   starts `XG_ROPE_EVAC_F.txt`. At frame -194 that cinematic runs
   `Send_Custom, 400194, 999, 999`, which makes zone 400194 destroy the
   scripted Mendoza (1965-1987).
7. **Completion**: entering zone 400194 (854-866) sends 205 accomplished and
   calls `Commands->Mission_Complete(true)`. The `was_entered` flag makes this
   happen only once. Entering the zone is enough: Mendoza's evac is not a
   prerequisite. After that, `CombatManager::Mission_Complete` calls the
   native handler, which calls `Run_Original_Campaign_Intermission`
   (`MISSION_COMPLETION_OWNER_REVIEW.md`).

The critical path has these single points of failure:
- `Invisible_Object` must be created at 400193. If creation returns NULL,
  control is never disabled, timer 9 never starts and 205 never activates.
- Level objects 400193, 400194 and 1111112 must exist with their
  `M02_Objective_Zone` and controller scripts.

## Retail M02.mix evidence

- **Cinematic commands:** `M02.mix` contains 54 cinematic `.txt` files
  (175,829 bytes). They use 15 commands:

  | Command | Count |
  |---|---:|
  | play_animation | 986 |
  | destroy_object | 432 |
  | create_object | 353 |
  | attach_to_bone | 272 |
  | play_audio | 191 |
  | create_real_object | 147 |
  | attach_script | 114 |
  | move_slot | 71 |
  | set_primary | 30 |
  | sniper_control | 22 |
  | set_screen_fade_opacity | 4 |
  | control_camera | 3 |
  | enable_letterbox | 2 |
  | set_screen_fade_color | 2 |
  | send_custom | 1 |

  All 15 are handled by the original `Test_Cinematic::Parse_Command` dispatch,
  with no Vita stubs. `Cinematic_Sniper_Control`, letterbox and fades go to
  the original `CCameraClass` and `ScreenFadeManager`.
- **Parser bounds:**
  - The longest line is 116 characters, below the 199-byte `line_data`
    buffer.
  - The highest slot is 17, below `NUM_SLOTS` (40).
  - The largest file is `x2k_midtro.txt` with 101 commands.
  - The 30 `destroy_object` lines timed at `1000000` seconds are the original
    `LAST_VALID_TIMESTAMP` tail that runs only when the primary is killed.
    Controllers destroy themselves when only those lines remain, so drop
    controllers do not pile up.
- **Cinematic scripts:**
  - `M02_*`, `M00_Disable_Loiter_DAY` (Test_DAY.cpp),
    `M07_Disable_Hibernation` and `MDD_Nod_Soldier` (MissionDemo.cpp) are all
    in Scripts.dsp sources linked by the static registry.
  - `DLS_Where_Am_I` (`x2k_midtro.txt` slot 1) is not declared anywhere in
    the EA source. The original `Attach_Script` logs it and ignores the NULL
    `Create_Script` result. Retail behaves the same way, so this is not a
    blocker.
- **Level data (`m02.ldd`):** it references 29 script names. All are declared
  in Scripts.dsp owners (Mission02, Mission00/M00_*, M01_Barn_Truck_JDG,
  M03_SAM_Site_Logic), and none falls outside the static registry. The other
  `M02_*` strings are conversation names.
- **Presets:** `Warm_Level_Cinematic_Preset_Models` warms 21
  `Create_Real_Object` presets plus 8 script literals
  (`kM02ScriptSpawnPresets`, `a31_vita_runtime.cpp:3341`), and stops if free
  memory would drop below 24 MiB.

## Blockers found / fixed

- No source-level completion blocker was found.
- Fixed a diagnostic gap in the Vita trace for slow cinematic commands:
  - **Problem:** the filter in
    `port/patches/scripts-a35-cinematic-command-timing.patch` matched only
    M13/M01 file names (`X00_`, `MX0_`, `X0`, `X1`, `XG_M01`). A slow command
    in an M02 cinematic (`X2*`) or a shared `XG_*` cinematic (rope evac,
    reinforcement drops) was therefore never logged.
  - **Change:** the filter now also matches `X2` and `XG_`. `XG_` covers the
    old `XG_M01` entry, and the existing `X0` entry already covers `X00_`.
  - **Unchanged:** the line count, the 100 ms threshold and the cap of 48
    reports.
  - **Validation:** the staged file and the `staging/PATCH_INVENTORY.json`
    receipt were updated, and `renegade_patch_inventory.py --check-staging`
    passes (506 patches).
  - **Not run:** the full `stage_sources.sh`, because worktree isolation
    refused the script. The hunk has no context lines, the line count is
    unchanged, and no other patch references these lines.

## Risks (unverified on hardware)

- **Performance:** M02 is the heaviest cinematic mission. Reinforcement drops
  (`X2I_Drop0*/Para03_Area*`, `X2I_GDI_Drop*`) create 147 real objects in
  total during combat. Loading a model outside the warmed set for the first
  time may cause a hitch. The `A4 slow campaign cinematic command` log lines
  will now show where these happen.
- **Sniper zoom:** `X2K_Midtro.txt` (~39 s) runs 21 `sniper_control` zoom
  steps through the original sniper HUD and zoom. Whether the sniper overlay
  draws correctly on the physical Vita is still an open item in KNOWN_GAPS.
  Source trace, input-leak audit and the hand-off fix are in
  `M02_SNIPER_CONTROL.md`.
- **Input during the midtro:** timer 9 re-enables star control at 1 s while
  the midtro camera still has control. This is the original ordering; confirm
  that player input does not leak through during the cinematic.
- **Textures:** the M02 texture fallback (`l02_ice`) and the DDS format rows
  are still open gap items.
- **Stale tests:** the pinned-hash tests in
  `tools/test_cinematic_filename_diagnostics.py` were already failing before
  this change (stale hashes, and they need upstream).

## Physical test route

1. Start M02 from the campaign. Check that the controller conversation
   `M02_PRIMARY_01_START` plays and objective 201 appears on the HUD.
2. Clear the areas toward the Obelisk and the dam. Watch the drop cinematics,
   and grep the log for `A4 slow campaign cinematic command: file=X2`.
3. Reach zone 400193 (the dam rooftop approach). The midtro should play with
   letterbox, fades and sniper zoom. Afterwards the star should be on the
   rooftop, 201 done, 205 shown, and the keycard granted at about 25 s.
4. Fight Mendoza until he runs and is evacuated by the rope cinematic.
5. Enter end zone 400194. Expect Mission_Complete, then score/intermission,
   then the M03 handoff. Pull the runtime log and any `psp2core-*.psp2dmp`.

## Full audit (2026-10-07)

Host-only static audit of the M02 completion path. Nothing was built, linked,
packaged or run in Vita3K or on hardware. Retail input was the read-only copy
`local-builder/retail-host/Data/M02.mix` (sha256 `f098e919…64b3a1`) plus
`always.dat`, `Always2.dat`, `always3.dat` and `always.dbs` (`objects.ddb`
sha256 `98253406…ec94cb`). Detailed receipts stay in the ignored
`build/m02audit/`.

Tools reused: `audit_mission_content_bindings --map M02.mix`,
`audit_mission_conversations --map M02.mix`,
`renegade_cinematic_dependency_scan --mission-inventory` and the
`audit_archive_literal_references` matcher. The checks that pair names with
archive members, timers with receivers, and script commands with null guards
were small one-off scans of the same data.

### 1. Script bindings and parameters

- `m02.ldd` has 685 bindings (684 persisted, plus `M02_Commando_Start`), and
  `objects.ddb` adds 55 definition bindings. They use 30 script names, and
  every name is declared in a Scripts.dsp source, so `unknown_shipped_scripts`
  is empty.
- Parameter counts match the descriptors. Scripts with no parameters carry the
  usual single empty value. `M02_Nod_Soldier` 3/3, `M00_BuildingStateSoundSpeaker`
  14/14, `M00_Play_Sound` 6/6, `M02_GDI_Soldier` 2/2, and every `Area_ID` or
  `Objective_ID` script is 1/1.
- All 30 `Get_*_Parameter("…")` reads in `Mission02.cpp` name a field of the
  script that makes the read.
- The 17 runtime `Attach_Script` calls pass the expected field counts.
- Cinematic `attach_script` lines use 8 script names. `x2i_gdi_drop03_minigunner.txt`
  passes `M02_GDI_Soldier "9"`, which is one of two fields. The missing value
  falls back to `""`, which `atoi` turns into 0, matching the descriptor
  default (`ScriptImpClass::Get_Parameter` bounds-checks the index).
- `DLS_Where_Am_I` is not declared anywhere and was already noted as identical
  to retail PC.

### 2. Custom events, timers and Find_Object IDs

- **Objective activations.** Every `(id, 0)` sent to the controller is in
  202..221, which keeps `Objective_Radar_Locations[id-202]` (20 entries) in
  bounds. `M02_Destroy_Objective` values in the level are 204, 212, 214–216,
  218–220, 222 and 223, and that script only ever sends `(id, 1)`.
- **Timers.** Every `Start_Timer` id has a matching `Timer_Expired` case, with
  one exception: controller timer 11 (started in case 411) and the completion
  timers with no conversation fall through. They still run the original
  `Stop_All_Conversations`. This is the same as retail.
- **Respawn-controller customs.** Customs 101–116 all have handlers. The
  literal area parameters are all in 0..25.
- **Area 99 defect (fixed below).** The level binds `M02_Nod_Soldier "99,0,2"`
  to 401002 and 401003. These two soldiers send custom 103 when their timer
  fires and custom 101 when they self-destruct, both with area 99.
  `M02_Stationary_Vehicle 99` (400985) sends no area custom.
- **Find_Object IDs.** 256 of the 281 literal `Find_Object` IDs are serialized
  level objects. The 25 misses (400288, 400348, 400412, 400414, 400452,
  400500, 400504, 400507–400509, 401025, 401048, 401055, 401059, 401061,
  401128 and 401146) are all wake-up `Send_Custom_Event(obj, Find_Object(id), 0, 0)`
  calls. `Send_Custom_Event` returns early on a NULL target
  (`SCRIPT_PTR_CHECK(to)`), so these lookups are no-ops, the same as on retail
  PC.
- **Critical-path objects** are all present:
  - 1111112 (both controllers), zones 301601, 400193 and 400194, and SAM
    sites 1100085/94/120/130 (`M03_SAM_Site_Logic` and
    `M02_Destroy_Objective`) each own their scripts;
  - 1111116, 474463, 400510, 401028 and 401036 are serialized level objects.

### 3. Content resolution

These names resolve against the mounted archives:

- all 21 `create_real_object` presets;
- the 15 Mission02 source presets (`Invisible_Object`, `Nod_Jet`,
  `Nod_FlameThrower_3Boss`, `GDI_Transport_Helicopter`, the vehicles and the
  `POW_*` powerups);
- all 43 cinematic `.txt` names in the source, with `X2I_GDI_Drop_HummVee.txt`
  coming from `always.dat`;
- the `POG_*.tga` objective icons, as `.dds`;
- `H_A_J27C` and the other source animations;
- the 15 `play_audio` names.

Conversations: 64 source leads. `M02_HIDDEN_02_FINISH` (`Mission02.cpp:3244`,
silo-pair bonus) is missing from the retail conversation DB. In that case
`Create_Conversation` returns -1, and Join and Start look it up and find
nothing, so nothing plays. Retail PC behaves the same way.

These cinematic dependencies are missing from every mounted archive, and all
of the misses are identical to retail PC:

- `XG_HD_Transport.w3d` (animation `v_GDI_trnspt.XG_HD_Transport`) is used by
  `x2i_gdi_drop_mediumtank.txt`, which `Mission02.cpp` reaches. The literal
  appears only in `.txt` files, so the transport plays no animation for that
  command.
- The `x2c_mammothdlv.txt` set (`X2C_*` models and animations, plus the
  `v_gdi_mammoth` preset/model), `xg_democam.txt` and
  `x2i_gdi_drop_mammoth.txt` are not referenced by M02 scripts or level
  bindings. Those cinematics are dead content.

### 4. Crash-prone code on the M02 path

- `Mission02.cpp` contains no raw `->` dereference, division, `sprintf` or
  fixed character buffer. Every created object is null-checked before
  `Attach_Script`.
- Every `Commands->` function that `Mission02.cpp` calls guards its object
  pointer with `SCRIPT_PTR_CHECK` or an explicit test, except
  `Has_Key(STAR, 6)` (zone 301601, `:556`). `STAR` is NULL only when there is
  no human soldier. Script zones default to `CheckStarsOnly`, so the enterer
  is the star itself. This is a lead only and was not patched.
- A missing `WaypathID` (Sakura 400397, the apaches and the jet 403389) is
  safe because `PathClass::Initialize` handles a NULL waypath.
- **Defect, fixed.** `M02_Respawn_Controller::Custom` (`Mission02.cpp:3136`)
  indexed its 26-entry arrays with area 99. `area_unit_count[99]` lands in the
  high byte of `area_officer[11]` inside the same script object, so this was
  an out-of-bounds write that stayed inside the object. It does not crash. It
  changes area 11's officer ID for a short time, which can skip area 11
  respawn checks. Fix: `scripts-a36-m02-respawn-area-bounds.patch` ignores
  area-indexed customs (101–109, 114) whose area is outside
  `[0, M02_AREACOUNT)`.
- **Original behaviour, kept.**
  - `M02_Mendoza::Timer_Expired` creates one extra `MX2DSGN_DSGN0019` active
    conversation every 7 s that is never started, so a small number of them
    pile up until the boss leaves.
  - Zone 400193 has no `was_entered` latch. Timer 9 destroys the zone 1 s
    after entry, and star control is already disabled by then.

### 5. Objective chain

The chain is the same as in the section above. Zone 400193 starts the midtro
and timer 9. Timer 9 completes 201, activates 205 and creates Mendoza. Zone
400194 sends `205` accomplished and calls `Mission_Complete(true)` once.
Neither new patch is on this path: the area guard returns only for
out-of-range area customs, and the chain's 104/105 customs use area 21.

### 6. Port patches touching M02

- `scripts-a36-m02-objective-controller-speech-save.patch`: save id 4 is
  unique within the controller. Correct.
- `combat-a47-ccamera-cinematic-sniper-handoff.patch`: the early return for a
  host-owned camera comes after the cinematic sniper-zoom step and the sniper
  block. Dropping the host clears `CinematicSnipingEnabled` and restores the
  saved zoom. This is correct when read against the staged
  `CCameraClass::Handle_Input`.
- `scripts-a35-cinematic-command-timing.patch`: the X2/XG filter is present,
  as recorded above.
- `kM02ScriptSpawnPresets` (`a31_vita_runtime.cpp:3388`): all 8 names are
  retail definitions.

### Validation and deferred items

**Validation:**
- `bash tools/stage_sources.sh` exits 0 with the new patch (526 ordered
  patches, zero fuzz). Only `staging/scripts/Mission02.cpp` and
  `PATCH_INVENTORY.json` changed.
- `renegade_patch_inventory.py --check-staging` passes.
- `arm-vita-eabi-g++ -fsyntax-only` on the staged `Mission02.cpp` (compdb flags
  plus the frame-profile, LAN and MSAA defines) passes with no Mission02
  diagnostics.

**Deferred:**
- Live waypath-ID presence. It is not a crash risk.
- Whether zone 301601 has `CheckStarsOnly` set.
- All physical gates in the test route above.

## Soft-lock hunt (2026-10-07)

Host-only source and retail-data review of `staging/scripts/Mission02.cpp` and
the M02 cinematics. Nothing was built, staged, packaged or run. Retail input
was the read-only Vita3K copy (`M02.mix` sha256 `f098e919…`, `always.dbs`
sha256 `4ba605de…`). The parsers were small one-off scratch scans built on
`tools/audit_m13_level_owners.py` and `tools/audit_deep_saved_content.py`.

**Verdict:** no reachable completion blocker that needs mission-specific code.
No patch was added and staging is unchanged. M02's only `Mission_Complete(true)`
is the end zone 400194 (`:856-871`), and `CombatManager::Mission_Complete`
(combat.cpp:1094) does not check objective states. Pending or stuck
secondaries, and even a pending primary 203, cannot stop the mission ending.

### Critical path as it appears in level data

| Step | Evidence | Fallback / robustness |
|---|---|---|
| Key 6 (bay door) | Only `M02_Dam_MCT::Damaged` (`:4084`) on 1111116 (`Nod MasterControlTerminal`) grants it. The only lock-6 door is `NORADOOR` at (1119.3, 906.6, 33.2) in `m02.lsd`. | `DamageableGameObj::Apply_Damage` (damageablegameobj.cpp:322-334) calls `Damaged` before the death check, so `Set_Health(0.1)` keeps the MCT alive. Any damager counts, there is no `killer==STAR` filter, and the `destroyed` latch and `KeyRing` (soldier.cpp:649) are both saved. |
| Bay-door warning 301601 | (1116.6, 906.9, 36.0), def 519 `Script_Zone_Star`, `CheckStarsOnly=1` | Player-only, so the deferred question in the Full audit is now answered. It only plays `M02_BAY_DOOR_WARNING` and removes itself when the key is missing. The door's lock code is the real gate. `Has_Key` is null-safe (scriptcommands.cpp:2449). |
| Midtro 400193 | (1198.5, 563.4, 32.4), stars-only | Timer 9 is saved on the zone. The delayed custom 1000/1002 is held on the receiver as a `GameObjCustomTimerClass` with a `GameObjReference` sender (scriptablegameobj.cpp:229-262, 694). Both are saved, and both survive the zone's self-destruction at timer 9. |
| Key 1 (HoN doors) | Lock-1 doors: two `DR_1` at (1192.6, 555.9, 23.1) and (1192.7, 569.5, 23.1), plus `HND_FRNT_DOOR2` at (1214.1, 562.5, 25.6). The player's only key-1 source is `Give_PowerUp(STAR, "Level_01_Keycard")` (`:195-198`), 25 s after entering 400193. | The `Nod_Soldier` grant (`:3434`) is AI-only. The timer is saved, as described in the previous row. `Level_01_Keycard` has `AlwaysAllowGrant=1`. |
| End 400194 | (1162.5, 514.6, 19.7), stars-only, cargo plane | The `was_entered` flag is saved. Mendoza and his rope evac are not prerequisites. |

### Pattern results

- **(a) Conversation-end completion.** Not applicable. `Mission02.cpp` has no
  `Monitor_Conversation`, and no conversation-driven `Action_Complete`
  completes an objective. The only `Action_Complete` handlers are Mendoza's
  goto (`:5124`), the jet and helicopter despawns, and the GDI soldier
  "cover" line (`:4409`). `m02.ldd` defines 39 key conversations (all
  priority 30, interruptable). Those include `M02_PRIMARY_01/04_START`, most
  `SECONDARY_*_START/FINISH`, `M02_BAY_DOOR_WARNING`, `M02_EVAG_SECURE_WARNING`
  and `MX2DSGN_DSGN0001/0004/0009/0010/0011`. Pre-emption by these key
  conversations only cuts speech short.
- **(b) Completion before activation.** This is reachable and identical to
  retail, but it does not block completion. The controller's `(id, 1)` case
  (`:118-123`) and the convoy count (`:130-142`) call `Set_Objective_Status`
  on an id that may not have been added yet. That call does nothing, and a
  later `(id, 0)` adds the objective as pending, where it stays.
  - Primary 203 (Dam MCT), secondaries 202 and 217, and convoy secondary 213
    are added only by zone 400269 at (775.6, 908.9) or zone 400188 at
    (597.7, 484.1).
  - If the player destroys the target before crossing that zone, the
    objective stays pending on the HUD and on the end screen.
  - Key 6 is still granted, so the run does not soft-lock.
  - Not patched: a fix would only change HUD and score presentation, not
    completion.
- **(c) N-of-M counters.** None of them is on the completion path. Each count
  is listed below with the event that sends it. None of them filters on the
  killer.

  | Counter | Sent from |
  |---|---|
  | Convoy, 3 trucks (400202-400204), custom 900/3 | `Killed` (`:4187`) |
  | Bridge SAMs 215/216, custom 115 | Vehicle drop only (`:3231`) |
  | Hidden silos 222, custom 116 | `Killed` |
  | Rocket and minigunner reinforcement `count_dead*` | Spawns only |
  | Area unit counts 101/103 | Spawns only. The area-99 fix is already in `scripts-a36-m02-respawn-area-bounds.patch`. |

  A truck removed without `Killed` would leave 213 pending. No script
  destroys 400202-400204.
- **(d) One-shot triggers.**
  - 301601 is player-only and advisory, as covered in the table above.
  - 400193 has no latch. Re-entry within the 1 s before timer 9 would need
    the star to leave and re-enter the 1.5 × 2.3 × 1.3 m box while control is
    disabled. That would start a second midtro and grant a second keycard,
    which is harmless. The second timer 9 dies with the zone, and the first
    timer re-enables control. This is retail-identical and not patched.
  - 400194 latches once and is saved.
- **(e) Required actors.** None on the path.
  - Mendoza is invulnerable (`Set_Health(start_health)`) and optional.
  - The engineers 400199 and 400200 only repair the Power Plant and Obelisk.
  - The keycards are granted directly, not dropped. No escort, vehicle or
    pickup is required.
- **(f) Save/load and death.**
  - Every critical-path latch is a registered variable: `was_entered`,
    `mendoza_id`, `destroyed`, `convoy_trucks` and `count_dead*`.
  - Zone timers, the receiver-held delayed custom, the zone `InsideList` and
    the star's `KeyRing` are all saved by the engine.
  - M02 has no `Mission_Failed`. Death uses the normal reload or restart, and
    either one restores a consistent state.
  - Saving mid-midtro (control returns at 1 s, and `Control_Camera -1`
    arrives at frame 1170) is cinematic and camera persistence that all
    missions share. It is tracked in `M02_SNIPER_CONTROL.md` and
    CINEMATIC_PRESENTATION, not here.

### Deferred

- **Pending objectives at mission end (b).** This is cosmetic and identical to
  retail PC. If it is wanted, a presentation-only fix would latch early
  completions in the controller and re-apply them when the objective is
  activated.
- **Map route reachability.** It is not known whether 400193 or 400194 can be
  reached without `NORADOOR` or the lock-1 doors. That needs geometry and
  navigation, and only a physical route can show it.
- **Physical gates.** All physical gates in the test route above are still
  open.

## Follow-up fixes (2026-10-07)

Evidence class: static source review, retail metadata (Vita3K retail copy,
read-only: `m02.ldd` conversation records), deterministic staging
(`bash tools/stage_sources.sh` rc 0, zero fuzz, 572 ordered patches, inventory
`bb6441b9…21d5`), `tools/audit_script_save_state_gaps.py` and
`arm-vita-eabi-g++ -fsyntax-only` of the patched `Mission02.cpp` (rc 0, no
Mission02 diagnostics). No build, no Vita3K, no hardware. Line numbers refer to
`staging/scripts/Mission02.cpp` after this change (SHA-256 `27eb945f…6293`).

Patch: `port/patches/scripts-a38-m02-followup-midtro-mendoza-repair-latch.patch`.
It is registered after `scripts-a36-m02-respawn-area-bounds.patch`, which was
the last M02 patch.

### Fixed

1. **Midtro zone 400193 had no latch (:841-852).** Entering the zone again
   during the 1 s before timer 9 destroys it started a second
   `X2K_Midtro.txt` controller. It also queued a second delayed 1000/1002
   keycard custom and a second timer 9, which died with the zone. The case
   now returns early when `was_entered` is set. The flag is set only after
   the `Invisible_Object` is created. If creation fails, a re-entry retries,
   as before. `was_entered` is already saved (ID 3), and the 400193 instance
   used it for nothing else.
2. **Mendoza's extra conversations (:5181).** `M02_Mendoza::Timer_Expired`
   began every 7 s tick with
   `int id = Create_Conversation("MX2DSGN_DSGN0019", …)`. The `switch` then
   overwrote `id`, so that conversation was never joined or started.
   - `Create_New_Conversation` adds every conversation to
     `ActiveConversationList` (`staging/combat/conversationmgr.cpp:1289`).
   - A conversation that never starts stays in `STATE_INITIALIZING` until
     `InitializingTimeLeft` runs out. That timer starts at 60000 s
     (`activeconversation.cpp:104`, `:462`).
   - So the extras did not go away when Mendoza left, as earlier sections
     said. They stayed in the active list and in saves until the level ended.
   - The growth was about 514 per hour for as long as he fought (he is
     invulnerable and optional).
   - No conversation slots leaked: the list is a dynamic vector.
   - The only consumer of the active count is the innate-chatter check
     (`soldierobserver.cpp:949`), and it is compiled out because
     `ENABLE_INNATE_CONVERSATIONS` is undefined.
   - `MX2DSGN_DSGN0019` is non-key (1 remark), so the extras never cut off
     other speech.

   Fix: `id` starts at -1. Every `counter` value assigns `id`, and the
   removed conversation was never audible, so the taunts that play are
   unchanged.
3. **Unsaved repair-announcement latches.** `M02_Obelisk` and `M02_Power_Plant`
   had no `REGISTER_VARIABLES`, so `info_given` was indeterminate after a
   load. The one-time EVA repair line, together with its
   `Stop_All_Conversations`, could then replay or never play. Both now save
   `info_given` as ID 1 (:3911, :3994). `audit_script_save_state_gaps` now
   reports `gap_vars=0` for Mission02; it was 2.

### Completion before activation (203/202/217/213): not patched here

This is left to the ObjectiveManager early-status memory that is being added
in `objectives.cpp`. Mission02 changes would only duplicate it. The M02 path
that fix needs to cover:
- The controller's `(id, 1)` case (:118-123) calls `Set_Objective_Status`
  before the objective exists.
- The convoy count (:130-142) calls `Set_Objective_Status(213, ACCOMPLISHED)`
  directly.
- Zone 400269/400188 later send `(id, 0)`, which reaches `Add_An_Objective`.
  That function calls `Add_Objective(PENDING)`, then
  `Set_Objective_Radar_Blip` and `Set_Objective_HUD_Info_Position`.

Applying a remembered status inside `Add_Objective` is enough for M02, because
the radar (`radar.cpp:614`) and the HUD POG list (`objectives.cpp:723-730`)
show only pending objectives. One caveat for that fix:
`Get_Num_HUD_Objectives` assumes the pending objectives come first, and
`Add_Objective` does not call `Sort_Objectives`. The fix should therefore sort
after it applies a remembered status. The `(id, 1)` FINISH conversation timer
(id+200) still plays, unchanged.

### Deferred

- Saves made before this change keep the old behaviour: no latch is set for
  a pre-existing 400193 entry, and the extra Mendoza conversations already in
  the save remain until the level ends.
- Physical check:
  - Enter 400193 and step back out and in during the first second. Exactly
    one midtro should play, and the keycard should be granted once.
  - Fight Mendoza for several minutes, quicksave, and confirm the save loads.
  - Damage the Obelisk and the Power Plant after a load. The repair line
    should play at most once.
