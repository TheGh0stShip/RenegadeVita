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
