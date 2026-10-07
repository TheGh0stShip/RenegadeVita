# Objective / HUD / radar / encyclopedia state across Vita lifecycle paths (2026-10-07)

Evidence class: host source trace of `staging/` (post-patch) against `upstream/`, plus
`python3 -m unittest tools.test_objective_state_lifecycle` (9 source-contract tests) and
`arm-vita-eabi-g++ -fsyntax-only` of the two changed translation units (rc 0). Nothing was built,
linked, installed, run in Vita3K or run on a Vita. Every behavioural statement below is a source
derivation, not an observation. Line numbers refer to this commit.

Question: does objective and HUD progression state survive, reset or leak correctly across
quicksave/load, level-start autosave load, player death then Restart, mission failure then retry, and
the session handoff between missions?

## Verdict

- **No Vita-side defect in the session or restart plumbing.** Every static that carries objective
  state is either reset by an original owner on each path or rebuilt from `ObjectiveManager` every frame.
- **Two latent original defects were fixed** with fuzz-0 staging patches (they bite harder on ARM than
  on x86 because stale pointers data-abort):
  1. The HUD pog index could outlive the pending HUD objectives (F1).
  2. An encyclopedia save omitted the most recently revealed bit (F2).
- **One high-priority open risk** (F4): unwinding a *rejected* load destroys unlinked `GameObjReference`
  members, including `Objective::Object`. It was introduced by the a36 post-load discard and needs a
  fault-injection test before anyone relies on rejected-load recovery.
- Original-behaviour quirks that are deliberately left unchanged are listed in F3 and F5 to F8.

## Where objective-related state lives and what resets it

| State | Owner | Created / reset | Saved in `.sav`? |
|---|---|---|---|
| `ObjectiveList` (ID, type, status, text IDs, sound, pog texture, HUD message ID, priority, position, age, `Object` ref) | `ObjectiveManager` (objectives.cpp) | `Reset()` in `CombatManager::Unload_Level` (combat.cpp:645, after `GameObjManager::Shutdown`) and again in `Shutdown()` (combat.cpp:256) | Yes: one chunk per objective, every field required (objectives.cpp:256-340), plus manager variables |
| `NumSpecifiedTertiaryObjectives` | same | `Init()` (objectives.cpp:369, once per Vita session). **Not** cleared by `Reset()` | Yes |
| `HUDUpdate`, `DebugMode`, `Viewer` text window | same | `Init()` sets `HUDUpdate`; `Viewer` is rebuilt by `EvaSettingsDefClass::On_Post_Load -> Reload_Viewer` on every definitions load | No (rebuilt by `Viewer.Update()` after any mutation or load) |
| Pog arrows, pog renderers, `CurrentObjectiveIndex`, `CurrentObjective`, cached range | `hud.cpp` statics | `Objective_Init` at `HUDClass::Init` (once per session); recomputed every `HUDClass::Think` from the manager | No (only the HUD enable flag is saved, hud.cpp `HUDClass::Save`) |
| Object-attached objective blip (shape/colour on the target `PhysicalGameObj`) | `PhysicalGameObj` | `Objective::Update_Object_Blip` / `Set_Object`; destroyed with the object | Yes, in the object's own chunk, so it stays consistent with the objective |
| Position blips (`Add_Radar_Marker`, M04) | `RadarManager::Markers` | `RadarManager::Shutdown` from `Core_Shutdown`; not cleared by `Init` on purpose (radar.cpp:202) | Yes (marker chunks) |
| Encyclopedia known bits | `EncyclopediaMgrClass::KnownObjectVector` | `Shutdown` clears them at session end; `Initialize` or `Restore_Data` at session start | Yes (4 bit arrays) |
| Encyclopedia level-start copy | `CopyOfKnownObjectVector` | Written by `Initialize` and `cGod::Store_Inventory` (`GameInitMgr::End_Game`); never cleared | No |

## Path-by-path trace

Legend: OK = source trace found no defect. Fn = see finding.

| State | Quicksave / load mid-mission | Level-start autosave load | Death -> Restart | Failure -> Retry | Session handoff |
|---|---|---|---|---|---|
| Objective list contents | OK. Loaded from the save into an empty list (new session, `Unload_Level` had reset it). Created is not re-run on a non-first load, and `Add_Objective` rejects duplicate IDs anyway (objectives.cpp:`Add_Objective`) | OK, same loader. The autosave is written on the first `Think` after observers started, so it already holds the start-script objectives | OK. `cGod::Restart -> Core_Restart -> Core_Shutdown -> Unload_Level` resets the list, `Load_Level` re-runs the first-load Created scripts (combatgmode.cpp:1378-1383, 841) | Same code path as death (`cGod::Mission_Failed` opens the Failed popup, Restart calls `cGod::Request_Restart`) | OK. Session teardown runs `Unload_Level` + `CombatManager::Shutdown` -> `ObjectiveManager::Shutdown` (a31_vita_runtime.cpp:6962, 7035) |
| Completed/failed status shown on the HUD pog | F1 | F1 | F1 (stale index after the list is rebuilt) | F1 | OK (`Objective_Init` resets index) |
| Radar blips on objects | OK. Object blip fields are in the object chunk; `Objective::Object` is restored through remap + post-load relink (reflist.cpp) | OK | OK. `~Objective` calls `Set_Object(NULL)` after the objects are already freed, so there is nothing to reset and no dangling write | OK | OK |
| Radar position markers | OK (saved/loaded, `Markers` empty at load) | OK | OK (cleared by `RadarManager::Shutdown` in `Core_Shutdown`, repopulated by Created) | OK | OK, see F9 |
| EVA objectives tab / objectives overlay | OK. The tab is rebuilt from the manager each time it opens (`Fill_Objectives_List`); the overlay is refreshed by `Viewer.Update()` at the end of `ObjectiveManager::Load` | OK | OK. `Reload_Viewer` runs when definitions reload; suspension hides the overlay | OK | OK |
| Encyclopedia unlocks | F2 (last bit lost) | F2, and F3 | F3 | F3 | OK. `Store_Data` at `End_Game`, `Restore_Data` in the next session (a31_vita_runtime.cpp:5027) |
| `NumSpecifiedTertiaryObjectives` | OK. Restored from the save | OK | F6 | F6 | OK. Reset by `Init` each session |

## Findings

### F1. HUD pog index can point at a completed or stale objective (original bug, fixed)

`Objective_Update` (hud.cpp:2044) keeps `CurrentObjectiveIndex` and `CurrentObjective` across frames.
`Get_Num_HUD_Objectives` counts only pending objectives with `HUDPriority > 0`, which
`Sort_Objectives` places first, but the index was never compared to that count. It was used raw in
`Get_Objective( idx )` (hud.cpp:2068), `Get_HUD_Objectives_Location( idx )` (:2181) and the message
lookup.

- **Completed pog.** Pending `[A, B, C]`, the player cycles with SELECT (`INPUT_FUNCTION_CYCLE_POG`
  is SELECT on Vita, renegade_vita_control_labels.h:54) to `C` at index 2, and `C` completes. The sort
  keeps `C` at index 2, so `Get_Objective(2) == CurrentObjective` and the "reset the index" test
  does not fire. The HUD count is now 2. The arrow, range and message keep showing the completed `C`
  until the player cycles again. When the first or a middle pog completes, the pointer test does reset
  the index, so only the last pending pog is affected.
- **Restart.** The index is not reset by `Core_Restart`. After the list is deleted and rebuilt, an
  index beyond the new HUD count reads `ObjectiveList[idx]`. `SimpleDynVecClass::operator[]` uses plain
  `assert`, which `NDEBUG=1` removes (CMakeLists.txt:573), so this is a silent out-of-range read.
  `Delete` shrinks the array as it empties (`Resize(0)` frees it), and each regrow is a fresh
  `new Objective*[n]` with indeterminate contents, so a stale slot can hold the old pointer by heap reuse. If it matches, the index is kept and
  `Get_HUD_Objectives_Location` dereferences a freed `Objective`. This is plausible, not proven.

Fix: `port/patches/combat-a37-hud-objective-index-bounds.patch` resets index and pointer and forces a
pog rebuild when `CurrentObjectiveIndex >= objective_count`, before any list indexing. One existing
behaviour is unchanged: the pointer test still handles the other reorder cases.

### F2. Encyclopedia save omits the newest revealed bit (original bug, fixed)

`BooleanVectorClass` keeps the most recently indexed bit in a write-back cache (`Copy`, `LastIndex`,
vector.cpp `Fixup`). `Reveal_Object` writes through `KnownObjectVector[type][id] = true`, which leaves
the bit dirty in the cache. `EncyclopediaMgrClass::Save` wrote `Get_Bit_Array()` directly. That
accessor (vector.h:1025) does not flush, and the `Fixup` header says to flush before touching the raw
array. So a quicksave or autosave taken before any other index of that type is touched loses the last
reveal.

Why this is reachable on Vita: `Store_Data` and `Restore_Data` copy the cache with the array
(`operator=` copies `Copy` and `LastIndex`), so a bit left dirty at the end of one mission is still
dirty in the next session. The level-start autosave (AUTOSAVE_CHAIN.md) is written on the first
`Think`, before gameplay is likely to touch that vector, and then misses the previous mission's final
reveal for that type. Loading the autosave then drops the entry from the EVA encyclopedia.

Fix: `port/patches/combat-a37-encyclopedia-save-bit-cache-flush.patch` adds a file-local
`Flush_Bit_Cache` that indexes bits 0 and 1 through the public interface (each index change writes the
previous cached bit back) and calls it before each `Get_Bit_Array()` in `Save`. The shared
`wwlib/vector.h` is left byte-identical to the copied `wwaudio/Vector.H`.

### F3. Restart after loading a save resets the encyclopedia to blank (original semantics, not changed)

`dlgloadspgame.cpp:604` calls `cGod::Reset_Inventory()` after a load request (AUTOSAVE_CHAIN.md notes the
weapon consequence). Each Vita load is a new session whose `else` branch calls `Initialize`, which runs
`Store_Data` on a blank vector. A later death Restart runs `cGod::Restore_Inventory`, whose
`EncyclopediaMgrClass::Restore_Data` copies that blank copy over the loaded discoveries. So after
"load, then die, then Restart" the EVA encyclopedia loses everything the save held, as does the
inventory. A freshly launched PC process behaves the same way. A longer-lived PC process would have kept
the copy from its last `End_Game`. Handoff sessions are unaffected: `Restore_Data` runs instead of
`Initialize` (a31_vita_runtime.cpp:5027-5032), and Restart there returns to level-start discoveries.

Not changed because the correct target state is a design choice (match a fresh PC process or snapshot
the loaded discoveries as the level-start copy). A snapshot would be a one-line `Store_Data` after a
successful non-handoff save load. Flagged for a decision.

### F4. Unwinding a rejected load may crash on unlinked `GameObjReference` members (fixed in staging, see `reports/REJECTED_LOAD_DISCARD.md`)

The a36 rejected-load patches remap pointer tokens but then `Discard_Post_Load_Callbacks()`
(saveload.cpp:140) so `ReferencerClass::On_Post_Load` never relinks. Each non-null
`ReferencerClass` loaded from the save keeps `ReferenceTarget` set to a remapped
`ReferenceableClass*` while `TargetReferencerListNext == NULL` and the referencer is **not** in the
target's list. `Objective::Object` is one of about forty such members (`GameObjReference` users:
actions, weapons, soldiers, vehicles, conversations).

Cleanup then runs `GameObjManager::Shutdown` and `ObjectiveManager::Reset` (combat.cpp:586-645).
`~Objective` calls `Set_Object(NULL)`, which calls `Object.Get_Ptr()` and dereferences the target. If
the target was already freed, that is a use after free. `~ReferencerClass` then runs
`operator=(NULL)` (reflist.cpp), which walks the target's list looking for `this`, never finds it, and
reads `NULL->TargetReferencerListNext`. The asserts that would catch this are compiled out.
In the original, post-load always ran, so every referencer was linked before it could be destroyed.

Why it is only flagged: it is general (not objective specific), I could not exercise it without a build,
and it needs a fault-injection host test. Proposed minimal fix, same hook the a36 patch already uses
"while every registered object is alive": give `PostLoadableClass` a virtual
`On_Post_Load_Discarded()` (default no-op), call it from `Discard_Post_Load_Callbacks`, and override it
in `ReferencerClass` to set `ReferenceTarget = NULL`. A registered referencer is by construction unlinked
(`Load` asserts both link fields are NULL on entry), so nulling the target is exact.

### F5. Objective radar blip quirks (original, unchanged)

- `Set_Objective_Radar_Blip(id, PhysicalGameObj*)` calls `Set_Object` only (objectives.cpp:639) and
  leaves `DrawBlip` and `Position` from an earlier position blip, so a script that sets a position blip
  and later an object blip for the same id draws both. Radar.cpp:611 draws `Position`, not
  `Get_Position()`.
- If the tracked object is destroyed while the objective is pending, `Object.Get_Ptr()` is NULL and the
  HUD arrow falls back to `Position`, which is whatever was last stored (often `0,0,0`).
- The save writes the object chunk only when `Get_Ptr() != NULL`, so a destroyed target is saved as no
  target. Save and load agree.

### F6. `NumSpecifiedTertiaryObjectives` survives `Reset()` (original, benign)

Only `Init()` clears it. A Restart keeps the value, and the Created script sets it again
(Mission03.cpp:73 = 4, Mission09.cpp:69 = 1, Mission10.cpp:59 = 2), so the value is the same. A PC
process that never re-inits would carry M03's 4 into later missions that never set it. The Vita runs
`Init()` per session, so it reports the true count and differs from PC there.

### F7. Objective list is only sorted on status/HUD-info changes (original, benign)

`Add_Objective` appends without sorting. The HUD relies on pending-with-priority objectives being first
(comment in `Get_Num_HUD_Objectives`), which holds because `Set_Objective_HUD_Info` and
`Set_Objective_Status` sort and priority starts at 0. `Change_Objective_Type` does not sort, but type is
not a sort key. The save writes list order and the load restores it, so the invariant survives a
reload. `qsort` is unstable, so equal-status, equal-priority objectives may swap order on a different C
library; only the pog order is affected.

### F8. EVA objectives tab with only hidden objectives (original, unverified)

`Fill_Objectives_List` calls `Set_Curr_Sel(0)` whenever `count > 0`, even if every entry was hidden and
the list is empty. Not traced into WWUI, so it is recorded, not claimed.

### F9. Checked and found safe

- Radar `Markers` could leak across sessions only if teardown skipped `Core_Shutdown` while Combat was
  active. The teardown deactivates the retained Combat mode first, which runs `Core_Shutdown ->
  RadarManager::Shutdown` (a31_vita_runtime.cpp:6920-6927), so no reachable path was found.
- `ObjectiveManager::Load` is the only loader. It has no toast or EVA message, so loading never replays
  "new objective" popups. `HUDClass::Add_Objective` is called from `Add_Objective` and unhide only.
- `Objective::Load` requires all 13 micro-chunks and equal `Age`/`HUD_AGE`. Empty strings are written as
  one NUL byte (`WRITE_MICRO_CHUNK_WWSTRING`, chunkio.h:319), so the `length == 0` rejection never hits
  an empty sound or pog name.
- The mission-failure latch, restart observer re-arm and `result.*` clears are covered in
  MISSION_FAILURE_PATHS.md and `tools/test_mission_completion_contract.py`.

## Changes in this unit

| File | Change |
|---|---|
| `port/patches/combat-a37-hud-objective-index-bounds.patch` | new, F1 |
| `port/patches/combat-a37-encyclopedia-save-bit-cache-flush.patch` | new, F2 |
| `tools/stage_sources.sh` | registers both, after `combat-a37-screen-overlay-opacity-clamp.patch` (no anchor touched) |
| `staging/combat/hud.cpp`, `staging/combat/encyclopediamgr.cpp`, `staging/PATCH_INVENTORY.json` | regenerated by the staging script |
| `tools/test_objective_state_lifecycle.py` | new, 9 source-contract tests |

Validation:

- `bash tools/stage_sources.sh` with a temporary symlink to `workspace/active/upstream/CnC_Renegade`:
  exit 0, 545 ordered patches, and the only staging differences from HEAD are the two files above and
  the inventory. The symlink was removed and the empty submodule directory restored.
- `python3 -m unittest tools.test_objective_state_lifecycle` passes (9). The neighbouring suites
  `test_campaign_discovery_handoff`, `test_hud_powerup_text_once`, `test_mission_completion_contract`
  and `test_campaign_autosave_chain` still pass (20 tests).
- `arm-vita-eabi-g++ -fsyntax-only` with the `vita-fast-candidate` compdb flags and the worktree
  include roots: `hud.cpp` rc 0, `encyclopediamgr.cpp` rc 0.

## Needs runtime evidence (no build allowed in this unit)

1. F1: on M05 to M10, cycle with SELECT to the last HUD pog, complete that objective, and confirm the
   arrow and message move to the first remaining pog. Then die with the pog index above 0 and Restart,
   confirming no crash and a reset arrow.
2. F2: reveal an encyclopedia entry by script or pickup, quicksave at once, reload in a new session, and
   confirm the entry is present in the EVA tab. Repeat for the level-start autosave after a mission with
   a last-moment reveal.
3. F3: decide whether Restart after a load should keep the loaded discoveries.
4. F4: add a fault-injection host test (reject a load after `ObjectiveManager::Load` with a non-null
   `Object`) before relying on rejected-load recovery.
