# Campaign autosave chain (source audit, 2026-10-07)

Evidence class: host source review plus source-contract tests
(`python3 tools/test_campaign_autosave_chain.py`, 7 tests). This is not a
runtime pass. No Vita3K or physical autosave for M01 to M11 has been observed.

## Timeline: Level directive to autosave.sav

| # | What happens | Owner (file:line) |
| --- | --- | --- |
| 1 | Mission success. The intermission calls `CampaignManager::Continue`. The Score step suspends Combat and calls `End_Game`. Combat is suspended, not inactive, so the Vita menu-loop early return does not fire. `End_Game` stores the live star's inventory (`cGod::Store_Inventory`, which also stores encyclopedia discoveries), then runs `cGod::Reset` and sets God to UNINITIALIZED. | a31_vita_runtime.cpp:6383; gameinitmgr.cpp:306,340,453 |
| 2 | Movie step, then Level step (no-op `End_Game`), `Select_Backdrop`, campaign mark, `Start_Game` latch, then `Request_Autosave()` unless the map is M13. | campaign.cpp:406-427 |
| 3 | The intermission sees the latch with `campaign_level_start`. It writes the CampaignManager chunk to RAM (State = the Level index), sets `campaign_handoff_completed`, and the session ends. The static `AutosaveRequested` flag and `cGod::LevelStartInventory` stay in process memory. | a31_vita_runtime.cpp:4465-4481 |
| 4 | Next session: `Initialize_SP` (so `Remember_Inventory` is true), CampaignManager chunk loaded and checked against the archive, `EncyclopediaMgr::Restore_Data`, then level load. | a31_vita_runtime.cpp:4941-4985, 5117 |
| 5 | Load finalization calls `cGod::Think` directly. UNINITIALIZED moves to SINGLE_INIT. `Create_Commando` then runs `cGod::Restore_Inventory` (weapons, ammo, health, shield, discoveries). The start script is attached and God moves to SINGLE_RUNNING. | a31_vita_runtime.cpp:5667; god.cpp:184-192, 400-404 |
| 6 | **First gameplay simulation frame**: `CombatManager::Think`, then `Process_Autosave_Request`. The gate `Can_Save_Current_State` (SINGLE_RUNNING) is true, the flag is cleared, and `Save_Game("save\\autosave.sav")` runs. Upstream comments this "after one run through main loop", so the timing matches. | a31_gameplay_boundary.cpp:797,820; combatgmode.cpp:1659-1677 |

So the autosave is written after the level loads and after the commando is
created, at the end of the first Combat Think. It is not written during
loading. While Combat is suspended, the frame returns early, so the save
waits. The write costs a one-time hitch on that frame, as on PC.

## Atomic writer

`_TheWritingFileFactory` is `RenegadeRootedFileFactoryClass` (a31_vita_runtime.cpp:4657).
The bare name `save\autosave.sav` maps to `ux0:data/renegade/user/save/autosave.sav`
(renegade_paths.cpp:296-326). A write-only open stages the data in memory and
writes `autosave.sav.pending`. On close, `Renegade_Replace_File` moves the old
file aside and renames the new one into place, so a failed write leaves the
previous autosave intact (renegade_file_factory.cpp:110-160, 366-383).
`Save_Game` aborts the write when any subsystem fails, and `Process_Autosave_Request`
logs if the write cannot be confirmed (`Last_Save_Write_Succeeded`). Each
commit or failure logs `A3.5 save write: path=... success=`.

## What the autosave contains

- The full level dynamic state. This includes the star soldier with the inventory carried
  over from step 5, plus any weapons the start script grants on creation.
- The `CHUNKID_GOD` chunk, holding State = SINGLE_RUNNING (the only state the Vita accepts on load).
- The `CHUNKID_CAMPAIGN` chunk, holding State = this Level's flow index, and BackdropIndex.
- Difficulty (combat.cpp:904), discoveries, conversations, map, and audio.
- `cGod::LevelStartInventory` is **not** saved. This matches upstream.

## Loading the autosave from the Load menu

The Load menu sends the bare name `autosave.sav`. The latch prefixes `save\`
(a4_frontend_lifecycle_boundary.cpp:375). The resolver reads the `.lsd` map from the
header and picks `Mxx.mix`. A new session loads the save, and CampaignManager State is
restored from the save. Then `Loaded_Save_State_Matches_Archive` requires the flow entry
at State to be `Level <that archive>`, or the load is rejected and cleaned up
(a31_vita_runtime.cpp:5406; campaign.cpp:204). The star comes from the save with
its carried inventory. God is SINGLE_RUNNING, so it creates no second commando. On
success, `Continue` advances State+1, which is the Score step, and the chain resumes.

`dlgloadspgame.cpp:604` calls `cGod::Reset_Inventory()` after the load request,
as upstream does (upstream dlgloadspgame.cpp:581). A death **Restart** after
loading an autosave therefore restarts the mission without the carried
weapons. A Restart in a campaign-handoff session keeps them. This is original
behaviour, so it was left unchanged.

## Defect fixed

**An unconsumed autosave request leaked into later sessions.**
`A31_Interactive_Run_Simulation_Frame` returns early on MENU_TOGGLE before
`CombatManager::Think` and `Process_Autosave_Request` (a31_gameplay_boundary.cpp:740).
A power resume can also open EVA before the first Think. If the player opened
the pause menu on the first frame of a handoff level and chose Load or Quit,
the request outlived the session. It then overwrote `autosave.sav` on the first
frame of the next unrelated world: a loaded manual save, or a new campaign's M13.

Fix (Vita code only, no upstream or patch change): at the end of
`A31_Vita_Run_Interactive_Runtime`, a pending request is cleared and logged
(`A4 campaign: cleared unconsumed autosave request at session end`) unless
the session ended with `campaign_handoff_completed`. That is the only
legitimate crossing. The existing handoff-failure and load-failure clears remain.

## Open (needs runtime evidence)

- A Vita3K or physical `A3.5 save write: path=.../user/save/autosave.sav success=1`
  line on the first frame of M01 to M11 after a handoff.
- Loading that autosave in a fresh process and finishing the mission through to the next Level.
- Comparing the carried inventory (weapon list and ammo) with the end of the previous mission.
- `tools/test_cinematic_save.py` needs `upstream/` and was not run in this
  worktree. It is unrelated to this change.
