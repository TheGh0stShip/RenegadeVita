# Campaign difficulty chain (Recruit / Soldier / Commando)

Evidence class: source and staged-tree review only (2026-10-07). No build,
no Vita3K run, and no physical Vita evidence. Nothing here is physically
accepted until a Vita log shows the breadcrumbs listed under "Hardware checks".

## Owner

`CombatManager::DifficultyLevel` (`Combat/combat.cpp`, static, initial value 1)
is the only store. Every consumer reads it through
`CombatManager::Get_Difficulty_Level()`; scripts reach it through
`Commands->Get_Difficulty_Level` (`staging/combat/scriptcommands.cpp:2389`, bound
at `:3597`). No Vita port code writes it: there are no `Set_Difficulty_Level` or
`DifficultyLevel` writes in `port/platform`, and the only patch that touches it is
`combat-a36-combat-manager-admission.patch` (described under save/load below).

Original writers:

| Writer | When |
|---|---|
| `CampaignManager::Start_Campaign(d)` | New campaign from `DifficultyMenuClass` |
| `CampaignManager::Replay_Level(map, d)` | Replaying a mission |
| `CombatManager::Load` (save game, `first_load == false`) | Loading a save |
| `SystemSettingEntryDifficulty::Set_Enum` | `difficulty N` console command |

`Start_Campaign` also sends `difficulty %d` to `ConsoleFunctionManager::Parse_Input`.
On Vita that call is a no-op adapter (`port/platform/a4_frontend_lifecycle_boundary.cpp`).
This loses nothing, because the original console path ends in the same
`Set_Difficulty_Level(d)` that has already run.

## Selection

`DifficultyMenuClass::On_Command` maps buttons 01–04 to difficulty 0–3:

- **New campaign:** the original `Initialize_SP` plus `Start_Campaign(d)` run unchanged, so the difficulty is set before `Continue()` latches the first `Level` start.
- **Replay** (`commando-a36-original-replay-flow.patch`): `A4_Frontend_Latch_Replay_Level(map, d)` accepts 0–3 and only non-save single-player archives. Only after the old session has been torn down does `Run_Original_Frontend_Intro_And_Menu` call the original `CampaignManager::Replay_Level(map, d)` (`a31_vita_runtime.cpp` around line 4300). `Replay_Level` sets the difficulty before `Start_Game`.
- **Load menu:** a completed-mission entry (`Get_Game_Rank > 0`) opens `DifficultyMenuClass::Set_Replay`, the same as on PC. Cancelling leaves the suspended campaign's inventory alone, because `Reset_Inventory` runs only on a committed request.

## Session handoffs (`a30_main.cpp` loop)

Each handoff tears down the interactive runtime and starts a new pass in the
same process:

- **Campaign continue (mission success → intermission → next level):** the runtime serializes only the original `CampaignManager::Save` chunk (up to 64 bytes; it holds State and BackdropIndex, not difficulty). The next pass runs `CampaignManager::Init` and `CampaignManager::Load`, then latches the next source. None of `CampaignManager::Init/Load`, `CombatManager::Init/Shutdown/Unload_Level`, `GameInitMgrClass::Initialize_SP/End_Game` or the port teardown writes `DifficultyLevel`. The process-lifetime static therefore carries the selection across the handoff, as it does on PC, where these are also process statics.
- **Pause or death replay:** `reload_replay_difficulty` is copied from the frontend trace, then into `pending_replay_difficulty`, then into the next pass's `reload_replay_difficulty`. There it is validated (0–3, non-save) and re-latched, and `Replay_Level` applies it.
- **Pause or death load of a save:** `pending_replay_difficulty = -1`. The difficulty comes from the save file (see below).
- **Return to the main menu, followed by a new campaign or replay:** the new selection overwrites the old one through `Start_Campaign` or `Replay_Level`.

## Save and load

- **Save:** the original `CombatManager::Save` writes `MICROCHUNKID_DIFFICULTY_LEVEL` whenever observers are active, which is true for every in-game save.
- **Load** (patched admission): values are read into locals and committed only after the whole chunk is admitted.
  - When `is_first_load` is false, all 8 values (mask 255) are required, including difficulty. That difficulty is then committed, matching the original.
  - When `is_first_load` is true (retail level `.ldd` data), difficulty is not required, and `DifficultyLevel = legacy_dificulty_level` is restored, as in the original. Level data therefore never overrides the selected difficulty.
- **Rejected chunk:** if the chunk fails admission, nothing is committed (`DifficultyLevel` is unchanged), and `combatsaveload.cpp` (`LOAD_REQUIRED_COMBAT_CHUNK`) rejects the load.

## Difficulty-dependent level data and presets

Retail spawners carry no difficulty flag. `SpawnerDefClass`/`SpawnerClass` have
no difficulty field. Difficulty-dependent placement is done in scripts that read
the difficulty in `Created`/`Custom` during level load. Those run after
`Set_Difficulty_Level`, because both `Start_Campaign` and `Replay_Level` set the
difficulty before `Start_Game`, and a save load restores it through
`CombatManager::Load`. A save also restores the scripts' own saved state, so
`Created` does not run again.

Consumers checked in staged sources:

- **M04 prisoner rule** (`staging/scripts/Mission04.cpp`, upstream ~9424): on easy (0), all three `prisonerNN_at_rallypoint` flags are pre-set. The other two sites gate the engine-room sniper (destroyed on easy) and the hard-mode delay timer of 90.
- **Mission01:** easy-spawned guys and the easy home range, aggression and take-cover values.
- **Mission03:** wave counts based on `DIFFICULTY + n`.
- **Mission09:** checkpoint paratrooper count, `(out-1) == DIFFICULTY`.
- **Mission11:** powerup manager.
- **`Toolkit_Powerup`:** drop chance and lifespan.
- **Engine:**
  - damage scaling to the star (`damage.cpp`)
  - star starting health (`god.cpp`)
  - powerup amounts (`powerup.cpp`)
  - AI aggressiveness and aim error (`soldierobserver.cpp`, `action.cpp`)
  - easy-mode camera assist (`ccamera.cpp`)
  - score-screen label (`scorescreen.cpp`)

All of these are original code, compiled unchanged with respect to difficulty.

## Defects found

None in the difficulty chain, so no code was changed.

## Residual risk (needs runtime evidence)

1. `combat-a36-combat-manager-admission.patch` requires `MICROCHUNKID_CHEAT_HISTORY` (bit 64) for first-load level data too, using an exact mask of 125. The original writer omits that micro-chunk when built with `PARAM_EDITING_ON`. If LevelEdit's `.ldd` files were written that way, every level load would be rejected. A retail `.ldd` exported by LevelEdit could also contain a difficulty chunk while flagged `first_load`, and the exact-mask check would reject that case too. Retail data was not available on this host to confirm. The fact that M00 and campaign levels already load on Vita suggests the mask matches retail, but no audit report records it. If a Vita log shows a CombatSaveLoad admission failure on a retail level, relax only the first-load mask to treat bit 64 (and bit 2) as optional. The original semantics are unaffected, because both values are discarded on first load.
2. The 4th difficulty button (index 3) is accepted, matching `IDC_MENU_DIFFCULTY04_BUTTON`. Retail menus show only three buttons.

## Hardware checks (log breadcrumbs)

- **New campaign on Commando:** Mission01 enemy behaviour differs from Recruit. The M04 prisoner objective completes without escort only on Recruit.
- **Replay on each difficulty from the load menu:** `A4 replay: original CampaignManager started source=<map> difficulty=<0..2>`.
- **Pause or death replay:** `A4 load: clean session released; entering original source=<map> replay_difficulty=<d>`, followed by the replay line above with the same `d`.
- **Campaign continue:** `A4 campaign: restored original CampaignManager chunk bytes=...`. Afterwards the next mission's score screen shows the originally selected difficulty label.
- **Save on Commando, then load from a Recruit session:** the score screen and AI show Commando.
