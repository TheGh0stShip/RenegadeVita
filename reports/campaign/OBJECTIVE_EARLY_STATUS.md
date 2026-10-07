# Objective status set before the objective is added (2026-10-07)

Evidence class: host only. The checks are `python3 -m unittest tools.test_objective_early_status`
(4 tests), which compiles the staged `combat/objectives.cpp` and its pre-patch form on the host with
the real wwlib chunk and string code and runs them, plus `arm-vita-eabi-g++ -fsyntax-only` of the
changed translation unit with the `vita-fast-candidate` compdb flags (rc 0, only warnings that were
already there). `bash tools/stage_sources.sh` applies the patch with zero fuzz and reproduces the
committed staging output. Nothing was built, linked, installed, run in Vita3K or run on a Vita.
Line numbers refer to the staged `combat/objectives.cpp` in this commit.

## Problem

`ObjectiveManager::Set_Objective_Status` on an ID that has not been added did nothing. Many missions
report an objective's outcome from a target or zone script, but add the objective from a
conversation-end callback or a briefing zone. When the player finishes the objective first, the
completion is dropped. The later `Add_Objective(id, ..., PENDING)` then leaves the objective pending
for the rest of the mission: on the HUD pog and radar blip, in the EVA objectives tab, in the
objectives viewer, and on the score screen (`Get_Num_Completed_Objectives`). Retail PC has the same
behaviour. Scripts cannot read objective status (`scriptcommands.cpp` exposes no getter), so the
status only drives presentation and score, never mission flow.

## Fix: `port/patches/combat-a38-objective-early-status.patch`

- **Table.** A file-local table holds up to 32 `{ID, Status, Replayed}` entries (`:77-153`). When
  it is full, the oldest entry is evicted and logged. `Reset` clears it (`:474`), and `Reset` runs
  on level unload, restart and session shutdown (`combat.cpp:645`, `:256`).
- **Remember** (`:762`, `Early_Status_Remember` `:144`). An unknown ID with ID > 0 that is set to
  ACCOMPLISHED or FAILED is recorded, and the latest status wins. A PENDING or HIDDEN report for an
  unknown ID clears the entry, so the later add keeps its own status. IDs of 0 or less are never
  recorded, because `Objective::Load` rejects them.
- **Replay** (`:626-634`, `:670-678`).
  - Any add that creates the ID consumes the entry.
  - Only an add that requests PENDING applies it. It does so by calling the original
    `Set_Objective_Status` after the original "new objective" message and HUD add. So the player sees
    "New … Objective" and then "… Objective Accomplished/Failed", and the OBCO/OBFA diag log, the
    blip reset and the sort all run as if the add had come first.
  - An add that requests HIDDEN or a terminal status keeps that status and drops the entry.
  - A duplicate add is still a no-op.
- **Repeat absorption** (`:710-719`, `:949-954`).
  - After a replay, a replay marker stays in the table until the next `ObjectiveManager::Update`
    (once per combat think).
  - While it is there, one `Set_Objective_Status` to the same status on that ID is skipped
    (no message, no log).
  - This covers the script-level late-add fixes that credit the objective themselves right after
    the add (`scripts-a38-m03-*-objective-late-add`, `scripts-a38-m04-torpedo-objective-race`). Without
    it they would announce the completion twice.
  - A different status, or any call after the next `Update`, goes through unchanged.
- **Remove** (`:683`). `Remove_Objective` forgets any entry for the ID.
- **Added first.** When the objective already exists, `Set_Objective_Status` finds no entry and runs
  the original code unchanged. Repeats still announce, as in the original, and the test checks this.
- **Runtime breadcrumb.** `A4 objective early status: remember|replay|evict id=… status=… entries=…`
  is written to the Vita log, at most 64 lines per level.

## Save compatibility

- **Format.** Unreplayed entries are written as micro-chunk 2 (`MICROCHUNKID_EARLY_OBJECTIVE_STATUS`,
  8 bytes `{int ID, int Status}`, one per entry) inside the existing `CHUNKID_MANAGER_VARIABLES`
  chunk (`:491`, `:510-517`). The chunk IDs and the existing tertiary micro-chunk are unchanged. Replay
  markers are transient and not saved.
- **Older loaders.** Older loaders, including the pre-patch Vita build, reach the `default:` micro-chunk
  case and ignore the entries. The test loads a new save with the reverse-applied pre-patch
  `objectives.cpp`: the load succeeds and the late add stays pending, as before.
- **Older saves.** Older saves have no micro-chunk 2. They load with an empty table, so the behaviour
  matches the unpatched build.
- **Admission** (`:550-563`, `:596-609`). This follows the a36 load-admission style: the loader rejects
  anything the saver cannot write.
  - Rejected: a wrong length, an ID of 0 or less, a non-terminal status, more than 32 entries, a
    duplicate ID, or an ID that is already in the loaded objective list.
  - The table is replaced only after a fully admitted load.
  - A rejected load leaves the table to the owner's `Reset`.

## Mission cases covered

Each case below is a status report that reaches `Set_Objective_Status` before `Add_Objective`.
After this patch the objective is added already accomplished or failed instead of staying pending.

| Mission | Objective(s) | Ordering (from the readiness reports) | Previous handling |
|---|---|---|---|
| M02 | 203 (primary, Dam MCT), 202, 217, 213 (convoy count) | Controller `(id,1)` (`Mission02.cpp:118-123`) or convoy count (`:130-142`) before zone 400269/400188 sends `(id,0)` | None, pending forever (M02_READINESS (b)) |
| M02 | other controller-added secondaries 204-221 | Same controller `(id,1)` before `(id,0)` path | None |
| M03 | 1007 keycard, 1008 mainframe, 1004 shore SAMs, 1002 village SAMs | Pickup, poke or SAM kills before the key-conversation or zone add | Script patches `scripts-a38-m03-*-late-add`. The engine now replays the status and absorbs the script's own credit, so there is one announcement |
| M04 | 400 torpedoes | `550` (`Mission04.cpp:667`) before announce `450` | `scripts-a38-m04-torpedo-objective-race` (soft-lock). The engine replay plus absorption gives one announcement |
| M06 | 609 alarm (secondary) | `609,1` (`:1474`) before CON060 adds it (`:5696-5701`). The stale HUD pog goes away because the objective is no longer pending | None |
| M06 | 603 rescue scientists, 601 war room | `603,1` (`:471`) before the hack adds 603. Hack before CON059 adds 601 | None |
| M07 | 704-708 (secondary briefings), 703, 710 | Accomplished before the briefing zone or the `703,3` add (`Mission07.cpp:6031`) | None |
| M05 | 513 | `:1412` sets the status, but the add at `:1286` is commented out | Entry stays unused until level unload (harmless) |

Not covered:

- **604 (M06).** It is added but never completed, because the boss class, not the script, completes
  the mission.
- **710 (M07).** It stays pending when the SAMs are captured before the nuke impact. The status call
  is never made, so there is nothing to remember.

## Radar blip, HUD info and type changes for unknown IDs (not remembered)

`Set_Objective_Radar_Blip` (both overloads), `Set_Objective_HUD_Info` (both overloads) and
`Change_Objective_Type` also drop calls for unknown IDs. They are deliberately left unchanged:

- For an objective whose status is replayed as accomplished or failed, they have no visible effect.
  - Position blips draw only for pending objectives (`radar.cpp:614`).
  - Object blips are reset for non-pending objectives (`Update_Object_Blip`).
  - HUD pogs count only pending objectives (`Get_Num_HUD_Objectives`).
- A source scan of `staging/scripts/*.cpp` found no blip or HUD-info call that is followed by its
  `Add_Objective` within 25 lines. The calls without a nearby preceding add are updates to
  objectives that already exist (for example the M03 `Remove_Pog` priority -1 calls and the M04
  pog re-pointing).
- Remembering object blips would need a saved `GameObjReference` in a static table, with pointer
  remap. That carries the rejected-load unlink risk in OBJECTIVE_STATE_LIFECYCLE.md F4.
  It is not worth taking without an observed case.

## Residual risk

- **Announcement timing.** The completion is announced at add time ("New" then "Accomplished"
  together) instead of never. This is presentation only.
- **Absorbed repeat.** If a script repeats the same status on the same ID before the next `Update`
  for its own reasons, that repeat is absorbed. Only IDs that went through a replay are affected.
- **Eviction.** Above 32 outstanding unknown-ID reports in one level, the oldest is dropped and
  logged, which is the original behaviour for that ID. No mission has more than about 25 objective
  IDs.
- **Unsaved replay marker.** A save taken between a replay and the next `Update` cannot happen from
  script code, because saves run between thinks. If it did, the marker would be lost and a later
  repeat would announce again.
- **No device evidence.** All of this is host and source evidence. The HUD, EVA and score
  presentation needs a Vita or Vita3K check (for example M02: destroy the Dam MCT before crossing
  zone 400269, then check that 203 shows accomplished on the HUD, the EVA tab and the score screen,
  and that the log has `A4 objective early status: replay id=203`).
