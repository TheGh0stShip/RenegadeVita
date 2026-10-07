# TUT-R1-15 — Tutorial developer checkpoints (RVTC1)

Tutorial Round 1, agent TUT-R1-15. Base: `tutorial-r1/base` at 45c6cf5.
**Nothing was compiled or run on Vita3K or hardware.** Only pure-Python tests
ran, plus read-only checks against the local checkpoint vault and an existing
Vita3K run log.

Setup note: `git merge --ff-only tutorial-r1/base` failed. The worktree was
created from `main` at cde0b86, which has campaign commits that came after the
base's merge point (6528a8e). My worktree branch had no commits of its own, so
I reset it to `tutorial-r1/base`. HEAD is 45c6cf5, as the coordinator expects.

## Goal

A tester should be able to boot straight into a named late tutorial segment
(Gunner range, Mobius, Hotwire/vehicles, power plant, final assault) from an
**original save file**. That means no skipped script, no made-up state and no
change to the save's bytes. Today, reaching those segments means replaying
15–30 minutes.

## Findings (file:line evidence)

1. **The startup route already exists.** `Try_Latch_Development_Save`
   (`port/platform/vita/a31_vita_runtime.cpp:3072`) reads
   `user/config/dev-checkpoint-launch-v1.txt` (`RVCP1 <slot>.sav`). It checks
   the save through the original `SaveGameManager::Peek_Map_Name` resolvers
   (`port/platform/a4_frontend_lifecycle_boundary.cpp:289-345`), deletes the
   request, and latches the original frontend Start_Game handoff. It is
   compiled in only with `RENEGADE_DEVELOPMENT_CHECKPOINT=1`
   (`CMakeLists.txt:51-57`, `tools/build.sh:22`). The request is one-shot.
   Re-entering the same segment therefore needs a host round trip on every
   boot, and on hardware that means a manual FTP or VitaShell copy.
2. **Save layout and native admission.** The original save is a `LEVEL_INFO`
   chunk followed by a `LEVEL_DATA` chunk (`staging/combat/savegame.cpp:85-103`
   and `217-224`). The Vita admission code (`savegame.cpp:105-189`) accepts a
   save only if it has:
   - exactly those two chunks, in that order;
   - each of the map, mission and description microchunks exactly once;
   - a NUL-terminated map name ending in `.LSD`;
   - a UTF-16 description terminated by one NUL code unit.
3. **Host-tool gap: it accepted saves the device rejects.** The old
   `tools/tutorial_checkpoints.py` accepted all of these, and the device
   rejects every one:
   - a map name ending in `.mix`;
   - unknown top-level chunks, or duplicate or out-of-order ones;
   - missing mission or description microchunks.

   The old unit-test fixture was itself such a save: it had a `.mix` map and
   only the map microchunk.
4. **Host-tool gap: slot names the device cannot launch.** `restore` allowed
   `[A-Za-z0-9_-]+\.sav` up to 85 characters. The native request parser
   (`port/platform/a31_development_checkpoint.h:16-41`) requires a letter or
   digit first and a stem of at most 64 characters. So `restore` could
   create slots that the launch route always refuses.
5. **Host-tool gap: no relaunch.** `restore` always did an exclusive create, so
   every relaunch needed a new slot name.
6. **Host-tool gap: no catalogue.** Every F5 save is described "Quicksave A" or
   "Quicksave B" (`staging/commando/combatgmode.cpp:1798-1822`). The original
   Load menu shows only time, date and description
   (`staging/commando/dlgloadspgame.cpp:174-249`). Copies are therefore
   indistinguishable in the original UI.
7. **The save records objective state.** The path is `LEVEL_DATA` >
   `CHUNKID_COMBAT` (0x40000) > `CHUNKID_OBJECTIVES` (916991662,
   `staging/combat/combatsaveload.cpp:63-81,107`) > `OBJECTIVE_ENTRY` >
   variables. The variables hold ID, type, status and Age microchunks
   (`staging/combat/objectives.cpp:208-244,393-418`). Age resets when an
   objective leaves HIDDEN (`objectives.cpp:558-580`) and grows with game
   time while the objective is visible (`objectives.cpp:787-793`). The
   youngest visible objective is therefore the most recent objective event,
   read directly from the save.
8. **Which script line owns each objective** (`staging/scripts/Mission00.cpp`;
   objectives are added hidden at 132-137):

   | ID | Revealed by | Completed by | Derived segment names |
   |---|---|---|---|
   | 1 | MTU_LOGAN_EVA 2373-2376 | MTU_SYDNEY_START 1955-1958 | to-sydney / sydney-hud-lesson |
   | 2 | MTU_SYDNEY_RADAR 2503-2507 | MTU_GUNNER_START 2000-2003 | to-gunner / gunner-range |
   | 3 | MTU_GUNNER_ENDING 2531-2539 | MTU_HOTWIRE_INTRO 2078-2081 | to-hotwire / hotwire-vehicles |
   | 4 | MTU_LOGAN_WHATSNEXT 2404-2407 | MTU_MOBIUS_REFINERY 2144-2148 | to-mobius / mobius-refinery |
   | 5 | MTU_LOGAN_PREPARE_POWER 2413-2416 | MTU_PETROVA_POWER 2155-2159 | to-petrova / petrova-power-plant |
   | 6 | MTU_LIEUTENANT_AFTER 2670-2673 | COUNT_OFFICERS>1 1194-1199, then Mission_Complete 275 | to-officers / mission-end |

   If every objective is still hidden, the segment is `logan-course`.
9. **Progress does not have to follow the script order.** All 10 local vault
   masters pass the strict envelope check. One of them, `m00-petrova-dev111`,
   has objective 5 accomplished while objective 2 is still pending and
   objectives 3 and 4 are hidden. Trigger zones complete objectives directly.
   So segments are named from the youngest objective, not from a linear
   index. `m00-refinery-dev117` comes out as `hotwire-vehicles` (objective 3,
   541 s earlier), because Logan's refinery introduction does not change any
   objective. The label marks the last objective event. It is not a
   position.
10. **Runtime logs can be matched to saves.** `Log_Mission_Progress`
    (`a31_vita_runtime.cpp:2318`) prints `status_1_6=` every time the state
    changes (call at 7087). Each atomic save write logs
    `A3.5 save write: path=… bytes=… success=` (5107). I ran the new
    `verify-log` against the existing Vita3K log
    `build/dev130-mobius-return/runtime-this-run.log` (read-only). It found
    the RVCP1 handoff and a frame-0 vector `1/1/1/1/3/3`. That confirms the
    parser reads real log text. It says nothing about which save bytes that
    run loaded.

## Changes

- `tools/tutorial_checkpoints.py` (extended, CLI-compatible):
  - **Strict parser:** a native-envelope parser that mirrors `savegame.cpp`
    (finding 3), plus an objective reader (finding 7).
  - **`derive_segment`:** names the segment from the youngest visible
    objective.
  - **New actions:**
    - `catalog`: lists user/vault/file saves. With `--log`, it matches each
      save to its last logged write, records whether the byte counts agree,
      and records whether the logged objective vector agrees.
    - `launch`: restores the save, then queues the RVCP1 request (or RVTC1
      with `--sticky`). `--segment NAME` picks the one vault master with that
      derived segment and refuses if the choice is ambiguous.
    - `verify-log`: compares the first progress line after a handoff with the
      save's objectives.
  - **`restore`:** uses the native slot grammar and reuses a byte-identical
    slot. It still refuses to overwrite anything else.
  - **`capture`:** records `derived_segment` and `derived_status_1_6` in the
    manifest (additive; schema 1 unchanged).
  - **`--content-id`:** can come from `RENEGADE_RETAIL_CONTENT_ID`.
- `tools/request_tutorial_checkpoint.py`:
  - `--sticky` writes `config/tutorial-checkpoint-v1.flag` and replaces only
    an existing RVTC1 flag, atomically. It first checks the save is an
    original M00 save.
  - `--clear-sticky` removes only an RVTC1 flag.
  - One-shot behaviour is unchanged.
- `port/platform/a31_development_checkpoint.h`: the slot parser now takes the
  prefix as a parameter. `Parse` (RVCP1) behaves exactly as before. New
  `Parse_Tutorial_Sticky` (RVTC1).
- `port/platform/vita/a31_vita_runtime.cpp`:
  - New `Try_Latch_Sticky_Tutorial_Checkpoint` (3126). It never deletes the
    flag. M00 demo builds require `A4_Frontend_Is_Tutorial_Source`. Full
    builds require a resolved save whose archive is `M00_Tutorial.mix`.
  - New `Try_Latch_Startup_Development_Checkpoint` (3168): the one-shot
    request wins; the sticky flag is honoured only at the first frontend
    entry of the process.
  - In practice, re-entries carry `start_at_main_menu` or a pending source
    and never reach this chain (`port/platform/vita/a30_main.cpp:235-377`). The static guard is
    a backstop.
- Tests:
  - `tools/test_tutorial_checkpoints.py`: rewritten fixture with the real
    chunk layout; 11 pure-Python tests.
  - `tools/test_development_checkpoint.py`: RVTC1 assertions added to the
    native parser test, which needs a C++ compiler and was **not run**.
- `docs/TUTORIAL_CHECKPOINTS.md`: tester workflow.
- `.gitignore`: `*.sav`, so original saves cannot be committed.

## Flag

`ux0:data/renegade/user/config/tutorial-checkpoint-v1.flag`, containing exactly
`RVTC1 <slot>.sav\n`. The `\r\n` and slot grammar match RVCP1.

**Default OFF:**
- The file is absent by default.
- The code is compiled only with `RENEGADE_DEVELOPMENT_CHECKPOINT=1`.
- In public builds the new function is `return false`, so startup behaves
  identically.
- In dev builds without the flag, the only difference is one failed `fopen`
  at the first frontend entry.

## Hypothesis ledger entry

- **Hypothesis:** with a sticky checkpoint, the time from app launch to
  player control at a late tutorial segment drops from about 15–30 minutes of
  replay to boot plus the original M00 save load. I estimate under 1 minute;
  this is not measured. It speeds up the developer/tester loop, not in-game
  performance.
- **Risk:**
  - A save from an older build may not load in a newer one. That is
    original-save compatibility, recorded as `cross_build_load_validated:
    false`.
  - A tester may forget the flag. The handoff is logged on every boot, and
    deleting the flag restores normal startup.
- **No gameplay, physics or asset semantics change.** The original
  SaveGameManager owns the load.
- **How to measure on the tutorial route:**
  1. Run 1: from a cold start, time Logan → Gunner range by hand. Note the
     wall time from launch to the `A3.5 mission progress: original player
     control available` line.
  2. Run 2: with the RVTC1 flag on a `gunner-range` checkpoint, take the
     same timestamps, from launch to the `A4 checkpoint: RVTC1 sticky
     tutorial handoff` line and then to player control.
  3. Repeat both runs 3 times. Compare medians.

## Verified vs unverified

**Verified:**
- 11 new pure-Python tests pass.
- These existing pure-Python tests pass:
  - the 4 non-compiling `test_development_checkpoint` tests;
  - all 21 `test_a4_original_frontend_contract` tests;
  - the clock-ownership source test in `test_vita_animation_clock`;
  - `test_campaign_flight_recorder_contract` and `test_runtime_log_contract`.
- `catalog` parses all 10 local vault masters.
- `verify-log` parses the real dev130 Vita3K log.

**Unverified:**
- Nothing is compiled: the C++ edits, the native RVTC1 parser test, and the
  ARM build.
- RVTC1 has never run on Vita3K or hardware.
- No save written by dev240 has been loaded.
- The earlier KNOWN_GAPS note "post-Sydney reload queued but unproven" is
  still open.

## Hardware A/B steps

1. Build with `RENEGADE_DEVELOPMENT_CHECKPOINT=1`; this is not a public
   package.
2. Play to the Gunner range and press Select+Square (original F5 quicksave).
   Pull `ux0:data/renegade/user/save/` and the runtime log (the startup
   screen shows its path as `Log:`).
3. On the PC, run `catalog --user-dir <pulled>/user --log <log>`. Expect
   `gunner-range` with `LOG_OBJECTIVES_AGREE`. Then run
   `capture --id m00-gunner-range-dev240 --slot quicksaveB.sav …`.
4. Run `launch --segment gunner-range --user-dir <staging>/user --offline
   --sticky`. Copy `save/rv_cp_m00-gunner-range-dev240.sav` and
   `config/tutorial-checkpoint-v1.flag` to `ux0:data/renegade/user/`.
5. Cold-boot. Expect these log lines:
   - `A4 checkpoint: RVTC1 sticky tutorial handoff latched=1 source=save/rv_cp_…sav; flag retained, once per process`
   - then `A3.5 mission progress: frame=0 … status_1_6=1/1/3/3/3/3`
6. Quit to the menu. It should stay there. Relaunch the app: it should land
   in the Gunner range again.
7. Pull the log and run `verify-log --id m00-gunner-range-dev240 --log
   <log>`. Expect `OBJECTIVES_MATCH_AFTER_LOAD`.
8. Check visually that Gunner's range script continues: targets appear and
   speech plays. Logs cannot show this.
9. Delete the flag, cold-boot, and confirm the startup movies and main menu
   return.
