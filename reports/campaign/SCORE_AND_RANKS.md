# Score-screen stats and mission-rank persistence across session handoff (2026-10-07)

Evidence class: host source review only. Nothing here was ARM-built, installed in
Vita3K or run on hardware. The one host unit test touched
(`tools.test_vita_mission_ranks`, 2 tests) passes but exercises only the store.

Question: after a mission, does the original score screen see correct per-mission
stats when the campaign continues into a new Vita session, and is the rank store
written once per completed mission for every campaign mission?

## Result

No functional defect found in the stat-collection or rank-write path. One
evidence gap was closed: the runtime log could not show which mission key was
written, so "one write per mission" was not checkable from a physical-Vita log.
`Report_Mission_Rank_Write` now logs `op`, `key` and `value`
(`port/filesystem/renegade_registry.cpp`).

## Stat collection (original owners, unchanged)

| Step | Owner | Notes |
| --- | --- | --- |
| Per-frame play time | `soldier.cpp:2490` `Stats_Add_Game_Time(frame seconds)` | Star only; other counters via `PlayerDataClass::Stats_Add_*` |
| Reset | `PlayerDataClass` constructor -> `Stats_Reset()` (`playerdata.cpp:57`, `:407`); `cPlayerManager::Reset_Players` for non-reloaded missions (`gamedata.cpp:320`); `cGod::Restart` after death (`god.cpp:608`) | Each Vita session builds a new player, so no counter carries over |
| Snapshot | `ScoreScreenGameModeClass::Save_Stats` (`scorescreen.cpp:84`) from `CampaignManager::Continue` before `End_Game` (`campaign.cpp:387-404`; replay `:338-356`) | Runs in the same session as the mission, while `COMBAT_STAR` is alive |
| Rank submit | `ScoreScreenDialogClass::On_Init_Dialog` -> `LoadSPGameMenuClass::Set_Game_Rank(_SSStats_map_name, overall_stars)` (`scorescreen.cpp:185`) | Key = map name minus 4-character extension; keeps max(old, new) |
| Advance | `ScoreScreenDialogClass::On_Destroy` -> `CampaignManager::Continue` (`scorescreen.cpp:332`); skipped under `Set_Forced_Teardown` | Patch `commando-a36-score-forced-teardown.patch` |

`Save_Stats` reassigns every `_SSStats_*` global on each call (the first nine
at the top, the rest from `CombatManager`, `CheatMgrClass` and
`ObjectiveManager`), so a stale value from the previous mission cannot survive
into the next score screen.

## What crosses the Vita session boundary

`a30_main.cpp:226-247` and `:353-367` pass only the next source name (96 bytes)
and a `CampaignManager::Save` chunk (about 20 of 64 bytes: State, BackdropIndex)
between sessions. The chunk is written at `a31_vita_runtime.cpp:4465-4480` and
restored at `:4941-4977`. Everything else is either rebuilt per session or is a
process static that the original code also carries between levels.

| Item | Where it lives | Next-session behaviour |
| --- | --- | --- |
| Play time, kills, hits, vehicles, buildings | `PlayerDataClass` of the new session's player | Zero. Correct per mission |
| Reload count | `CombatManager::ReloadCount` static (`combat.cpp:162`) | A first-load level LSD sets it to 0 (`combat.cpp:1028-1030`). A loaded save increments it (`:1033`). Matches original; not runtime-proven on Vita |
| Cheat flag | `CheatMgrClass` history | `Reset_History()` on first load (`combat.cpp:1031`) |
| Secondary/tertiary objectives | `ObjectiveManager` | `Reset()` in level unload (`combat.cpp:645`) |
| Difficulty (Level-of-Play stars) | `CombatManager::DifficultyLevel` static (`combat.cpp:141`) | Not in the 64-byte chunk. Kept because first-load keeps the current static (`legacy_dificulty_level = DifficultyLevel`, `combat.cpp:941/1029`) and nothing in `port/` writes it. Replay sets it explicitly; saves carry it. Correct inside one process |
| Mission-complete latch | `g_mission_completion_latch` | Reset at observation start (`a31_gameplay_boundary.cpp:603-611`) |
| ScoreScreen game mode | session-local stack object | Added when absent in every session including restored ones (`a31_vita_runtime.cpp:5007`), so `Save_Stats` always has a target |
| `_SSStats_*` | process globals | Fully overwritten at the next `Save_Stats` |

Consequence: an app relaunch mid-campaign drops the in-memory campaign state and
the difficulty static, exactly as a relaunch loses the original in-process
campaign. Progress is then recovered through saves/autosave, which carry
difficulty and reload count.

## Rank store

- Store: `port/filesystem/renegade_mission_ranks.h`, file
  `ux0:data/renegade/user/config/mission-ranks-v1.cfg`, bound to registry key
  `Software\Westwood\Renegade\Ranks` (`APPLICATION_SUB_KEY_NAME_MISSION_RANKS`).
- `RenegadeMissionRanks::Configure` runs at the start of every session
  (`a31_vita_runtime.cpp:4765`), re-reading the file, so session N+1 sees the
  write from session N. A corrupt file disables writes and is left untouched.
- Key derivation: campaign flow (retail `campaign.ini`, see
  `CAMPAIGN_CHAIN_READINESS.md`) has 12 `Level` entries each followed by
  `Score`: `M13.mix`, then `M01.mix` to `M11.mix`. `Set_Game_Rank` strips the last
  four characters, giving `M13`, `M01` ... `M11`. All fit the store's name rule
  (letters, digits, `_ - .`, under 96 characters) and the replay menu reads the
  same names (`Get_Game_Rank(find_info.cFileName)`, `dlgloadspgame.cpp:204`,
  and the `Mxx.MIX` allow test at `:300`). Lookup is case-insensitive.
- Mission number for the par-time table: `Get_Mission_Number_From_Map_Name`
  parses `atoi(name + 1)` (`gamedata.cpp:2108`), clamped to 0..13
  (`scorescreen.cpp:120-131`). M13 maps to the "Mission 0" row (index 13),
  M01-M11 to indices 1-11.
- Writes per mission: one `Set_Game_Rank` per score dialog init. `Set` returns
  early without touching disk when the stored value already equals the new one,
  so a repeat or lower-star replay does not rewrite the file. The max rule keeps
  a better earlier rank.
- Saved-game completion: `The_Game()->Get_Map_Name()` is the save path, and
  `Save_Stats` replaces it with the map name inside the save via
  `SaveGameManager::Peek_Map_Name` (`scorescreen.cpp:112-116`), normally
  `Mxx.lsd`. The same call is used at session start
  (`A4_Frontend_Resolve_Single_Player_Archive`), so it reads the same file.

## Residual risks (not changed)

1. If `Peek_Map_Name` ever failed for a loaded save, the map name would remain
   `save/xxx.sav`: the rank key would fail the name rule (write rejected,
   `write=0`) and the mission number would parse as 0. No path to this is known,
   and the fix would be a new upstream patch to `scorescreen.cpp`, so it is
   recorded rather than patched.
2. `write=1` is logged even when `Set` skipped the disk write because the value
   was unchanged. The new `value=` field makes that visible.
3. Difficulty continuity depends on the process static (see table).

## Change made

`port/filesystem/renegade_registry.cpp`: `Report_Mission_Rank_Write(ok, op, name,
value)` now logs

```
A3.5 mission ranks: write=1 op=set key=M01 value=4 entries=2 error=0 original_registry=1
```

Port-owned file only; no upstream or staging change, no patch inventory change.

## Physical verification to request (not yet done)

After a full campaign the log should contain exactly 12 `op=set` lines whose keys
are, in order, `M13`, `M01` through `M11`, each with `write=1` and
`value` between 1 and 5, and `entries` rising by one per mission. On the next
launch, `A3.5 mission ranks: load=1 entries=12`. Repeating a mission with a
lower score must show the earlier, higher `value`. Any `write=0` or an
`entries` count that does not rise needs the preceding `A4 campaign:` lines.
