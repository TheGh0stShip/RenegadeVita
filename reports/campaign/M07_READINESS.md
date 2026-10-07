# M07 campaign readiness (source and retail-metadata review)

Evidence class: source inspection and a read-only host audit of user-owned
retail metadata. No build, emulator or physical Vita run. Nothing here proves
that M07 completes on Vita.

## Result

No M07-specific port defect was found. No source or patch change was made. The
success chain is complete in source, and every object it uses is present in the
retail `m07.ldd` with the expected script attached. All 567 M07 script bindings
resolve through the static registry. The two lookup leads below behave the same
way on retail PC and fail without crashing.

## Success chain (`staging/scripts/Mission07.cpp`)

1. The level start script `M07_Havoc_DLS` (`:332`) is the `combat_start_script`
   binding in `m07.ldd`. It gives the starting weapons and calls
   `Mission_Complete(false)` if Havoc dies (`:399`).
2. Placed object 100657 has `M07_Objective_Controller` (`:44`) attached.
   `Created` adds objective 709, then starts timers for the `M07_CON001`
   conversation (`:286`). When conversation 300701 ends (`:308`), it adds 701,
   starts the nuke countdown on 100663 and sends the Dead6 team to assembly.
3. Placed object 100663 has `M07_Cathedral_Controller` (`:1391`) attached. Its
   countdown runs about 2 minutes (`M07_CON003`–`M07_CON012`) and attaches
   `Test_Cinematic` `XG_NukeStrike.txt` (`:1479`). At impact it sends a logical
   sound, `M07_NUKE_IMPACT` (`:1529`). Havoc dies if he is still marked
   `nuke_blast` (`:364`). That flag is cleared by the in/out blast zones
   `M07_In_Nuke_Blast`/`M07_Out_Nuke_Blast` (`:1555`+). `ESCAPED` sends
   710/param 1 (`:1545-1549`).
4. Objective 703 is added (param 3) after conversation 300703 (`M07_CON017`)
   ends (`:5986-5989`). The trigger is the fifth Dead6 evacuation climb.
5. **Completion.** Placed objects 100796 and 100798 both have `M07_Park_SSM`
   (`:3354`, definition 82080098). Each one's `Killed` sends
   `M07_ARTILLERY_KILLED` to 100799 (`:3404`). Object 100799 has
   `M07_Park_Controller` (`:3322`). After the second kill it sends 703/param 1
   to 100657 with a 5 s delay (`:3346`). That delay goes through
   `Start_Custom_Timer` (`staging/combat/scriptcommands.cpp:671`). The
   controller's `Custom` handler then calls `Mission_Complete(true)` (`:237-239`).
   This does not depend on objective 703 having been added first.
6. These failure routes call `Mission_Complete(false)`: param 2 for 701, 702,
   709 or 710 (`:253-267`), and Havoc being killed.

## Data / registry checks

All of the following were run read-only against the user's retail data. The
receipt was written to the git-ignored `build/m07/` and is not committed.

- **Script bindings.** 567/567 bindings resolve:
  - 438 persisted
  - 83 spawner
  - 45 definition
  - 1 combat-start

  This matches the M07 row of `reports/generated/sweeps/live_script_bindings.json`.
- **Discovered closure.** 124 scripts, with no unknown shipped scripts and no
  binding decode findings.
- **Cinematic text files.** M07's cinematic text files (13 files) live in
  `always.dat`, not `M07.mix`. All 13 are present. In
  `host_retail_cinematic_parser.json` each one has `records_match: true`.
- **Scripts attached from those text files.** Eight scripts are attached from
  them, and all 8 are registered: `M07_Para_Drop_Unit`, `M07_Player_Vehicle`,
  `M07_V01_Unit`, `M07_V05_Unit`, `M07_Triangle_Unit`,
  `M07_Deadeye_Nod_Chinook`, `M08_Mobile_Vehicle` and
  `M00_No_Falling_Damage_DME`. The names that text `Create_Object` uses are
  W3D model names, not presets.
- **Literal `Find_Object` IDs.** Every literal ID in `Mission07.cpp` matches a
  serialized object except 100952. This includes the chain IDs 100657, 100663,
  100665, 100666, 100796, 100798, 100799 and 119890–119893.
- **Unresolved definition IDs.** 22 typed sub-definition IDs did not resolve.
  They are weapon eject/muzzle-flash physics defs and Small Explosion Sounds
  Twiddler choices. They are global `objects.ddb` gaps, not M07 owners, and
  they do not affect progression.

## Leads (not blockers, retail-identical)

- `M07_Activate_V01` (`:4255`) sends to 100952, which is not in M07's
  serialized IDs (100952 is an M04 spawner ID). `SCRIPT_PTR_CHECK(to)` returns
  early (`scriptcommands.cpp:657`). The optional V01 encounter will not start
  from that zone. 100953 (`:4380`) is the follow-on.
- `Create_Object("Ramjet_Weapon_Powerup")` (`:5024`): no preset has that name.
  The call returns NULL and the result is not used, so no powerup drops.

## Risks

- **Nuke-escape timing.** The player has about 2 minutes from the end of
  `M07_CON001`. Frame pacing, conversation timing and blast-zone `Entered`
  delivery are physical gates. If the player is still flagged in the blast at
  impact, the mission fails.
- **Objective 709/701 failure routes.** These depend on Dead6/Sydney AI pathing
  and survival. Any AI/pathfind regression turns into a mission failure, not a
  stall.
- **SSM targets.** The completion targets 100796 and 100798 must be damageable
  and killable. Their logical sounds `M07_SSM_DAMAGED`/`FIXED` drive the
  engineer repair AI, which can make the kills take longer.
- **Vehicle sections.** The player-vehicle drop (`M07_Activate_Present`
  `:2929`, `M07_Player_Vehicle` `:2968`, `M07_Vehicle_Drop_Controller` `:3008`)
  depends on Vita vehicle entry/exit and the drop cinematic. It is optional for
  completion, but it is the normal route to the park.
- The authored parameter surface has 331 excess-value bindings. These are
  common across maps and follow the original parser behavior.
- The general mission-complete handoff, autosave and save stall remain as in
  `reports/SINGLE_PLAYER_COMPLETION_WIRING.md`.

## Physical test route

1. Start M07 from campaign or the development launcher.
2. Confirm the `M07_CON001` audio/subtitles play and that objectives 709, 701
   and 710 appear.
3. Leave the blast radius before impact. Confirm the nuke cinematic, the
   ash/wind and that Havoc survives. Objective 710 should be accomplished.
4. Continue through the SAM and inn-evac sections until `M07_CON017` adds 703.
5. Optionally collect the vehicle drop at the `M07_Activate_Present` zone.
6. Destroy both park SSM launchers (100796 and 100798).
7. Expect `Mission_Complete(true)` about 5 s after the second kill, followed by
   the score screen and the M08 handoff.
8. Capture the runtime log for "native provider missing script" (expect none
   for M07) and the NULL Script Ptr lines (expect the 100952 one only if that
   zone is entered).
