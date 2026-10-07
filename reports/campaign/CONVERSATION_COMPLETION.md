# Conversation completion callbacks (source trace)

Evidence class: staged-source inspection against pristine upstream
(`upstream/CnC_Renegade/Code/Combat`) and the port patch set. No build,
emulator, device, network or retail-file action. Native delivery is still
unproven; the physical signature to look for is at the end.

Verdict: no source defect found that drops an `ACTION_COMPLETE_CONVERSATION_*`
callback. No code change was made. Every port patch that touches this path
preserves the original delivery rule (below). Retail-parity hazards and
one corrupt-state hardening candidate are recorded, none fixed on purpose.

Line numbers refer to `staging/combat/` unless stated.

## Delivery rule (unchanged from retail)

`ActiveConversationClass::Stop_Conversation` (activeconversation.cpp:1249-1293)
is the only producer. It sets `STATE_FINISHED`, frees orators, records
telemetry, then calls `Notify_Monitors_On_End` (:1069-1092). That walks
`MonitorArray[10]` (`GameObjReference`, i.e. `ReferencerClass`) and calls
`Action_Complete(obj, ActionID, reason)` on every observer of each live
monitor. Scripts are themselves `GameObjObserverClass` observers
(`staging/scripts/scripts.h:148`), so the DECLARE_SCRIPT `Action_Complete`
runs synchronously. The reason is never checked by the M10 scripts, so ENDED,
INTERRUPTED and UNABLE_TO_INIT all count.

Callers that end a conversation, all through `Stop_Conversation`:
remark list exhausted (:552, ENDED); audience gone (:451); orator dead
(:429); init timeout (:464); key-conversation preemption (:400 and
conversationmgr.cpp Think, ENDED by default argument); script
`Stop_Conversation` (scriptcommands.cpp:2609); `Reset_Active_Conversations`
(conversationmgr.cpp:192, INTERRUPTED).

## 1. Destroyed-building monitor

PASS by source.

- `BuildingGameObj::On_Destroyed` (building.cpp:1129-1150) only sets
  `IsDestroyed`, notifies the base controller and the encyclopedia. It does not
  call `Set_Delete_Pending`. `building.cpp` is byte-identical to upstream in
  observer/reference code.
- The delivery path needs the monitor slot non-null and the object's observer
  list intact. `ReferenceableClass::~ReferenceableClass` (reflist.h) nulls the
  slot only when the object is really deleted. A killed building is not.
- The M10 monitor objects are the buildings themselves
  (`Monitor_Conversation(obj, id)` inside `Killed`, Mission10.cpp:720-728 and
  siblings). `Mission10.cpp` destroys other objects (1203589, 2014793, ...)
  but never the monitored buildings 1153931/1153932/1153933.
- `Notify_Monitors_On_End` has no `Is_Destroyed` / `Is_Delete_Pending` filter.
  Even a delete-pending monitor still gets the callback until it is truly
  freed (`ScriptableGameObj::Set_Delete_Pending` only calls `Destroyed`).
- Same as retail: if a monitored object is actually deleted before the
  conversation ends, the slot is nulled and the callback is silently skipped.

## 2. Zero-length or failed speech

PASS by source. Conversation advance is timer-only; it never waits for audio.

`Say_Next_Remark` (:480-556) sets `NextRemarkTimer` to the value returned by
`SoldierGameObj::Say_Dynamic_Dialogue` (soldier.cpp:3563-3650):

| Case | Duration | Result |
|---|---|---|
| Text ID missing in translation DB | 2.0 s default | advances, ends |
| `sound_def_id == 0` | 2.0 s | advances, ends |
| `Create_Sound` returns NULL (decode/open fail) | 2.0 s | advances, ends |
| Sound created, duration 0 (empty/failed wave) | 0 | advances next `Think`, ends |
| Playback fails after creation | unchanged | timer unaffected |
| Remark has orator id out of range | timer unchanged (<= 0) | skipped, advances each frame, ends |
| Zero remarks | n/a | `Stop_Conversation(ENDED)` first call (:552) |

Duration plumbing is finite. `SoundBufferClass::Determine_Stats`
(wwaudio/SoundBuffer.cpp:117-155) divides by `bytes_sec` only when the port's
`Inspect_Wave` accepted the header; that validator
(`port/audio/vita/renegade_wave_decoder.cpp`) requires channels 1-2 and rate
8000-192000, so no divide-by-zero or inf-to-unsigned saturation. The provider's
`AIL_sample_ms_position` (renegade_miles_provider.cpp:1213-1228) returns 0 for
an empty sample and clamps to `INT32_MAX`. A rejected wave gives duration 0, not
a huge value. The nonfinite-timer stall (`NaN <= 0` is false) is not reachable
because the source is an integer millisecond count divided by 1000.0F.

NULL-orator conversations (`Join_Conversation(NULL, id)`, the M10 pattern)
skip the whole position setup in `Start_Conversation` and satisfy
`Is_Audience_In_Place` trivially (:565-610 skips NULL orators), so they reach
TALKING on the first `Think`.

## 3. Save/load interruption

PASS by source for the supported order; one pre-existing ordering effect is
documented.

- Save (:680-715) writes variables (state, remark, timer, ID, action ID,
  conversation ID, priority, central pos, old-pointer token), one `MONITOR`
  chunk per non-null slot via `ReferencerClass::Save`, and one chunk per orator.
  The port adds only error propagation. The diagnostic instance token
  (`DiagnosticInstance`) is not written.
- Load (:716-775) restores monitors into slots 0..n-1 and registers the
  conversation's old pointer. `ReferencerClass::Load` (patched reflist.cpp:57-100)
  reads a 32-bit token, requests a pointer remap and registers `On_Post_Load`,
  which relinks to the live object. Token width equals the retail ILP32 pointer
  width, and `ScriptableGameObj::Save/Load` registers the same
  `ReferenceableGameObj *` token, so the remap target exists.
- After load, `State`, `CurrentRemark` and `NextRemarkTimer` continue from the
  saved values. `CurrentSound` is not restored, which is retail behavior: the
  line is silent but the timer runs, the next remark plays, and the conversation
  ends through `Stop_Conversation` with monitors relinked.
- Global conversations are not saved (`SaveCategoryID` is set to LEVEL by
  `SaveGameManager`, savegame.cpp:225). An active conversation that uses a
  global one resolves it by ID in `Load_Variables`
  (`Find_Conversation(id)`) from the startup-loaded global database
  (`A31_Interactive_Load_Global_Conversations`, a31_gameplay_boundary.cpp:92).
  Nothing resets global conversations during a savegame load.
- Pre-load callbacks, same as retail: `LevelManager::Release_Level`
  (`staging/commando/level.cpp`, byte-identical to upstream) calls
  `ConversationMgrClass::Reset_Active_Conversations()` before
  `GameObjManager::Destroy_All()`. Every live conversation therefore delivers
  `Action_Complete(INTERRUPTED)` to the old world's scripts while it is being
  torn down. `ConversationMgrClass::Load` calls it again (:418) but the list is
  already empty. Those callbacks run on objects about to be destroyed, so their
  custom events are discarded. A script that mutated persistent state directly
  from `Action_Complete` would behave the same as retail.
- Saving itself never stops a conversation and never fires callbacks.

## 4. Port patch audit

Staged diffs against upstream, conversation-related only
(`activeconversation.cpp/.h`, `conversationmgr.cpp/.h`, `conversation.cpp`,
`reflist.cpp`):

- Telemetry hooks (`a35-conversation-transition-telemetry`,
  `-diagnostics`): called immediately before the original loop and observer
  call, never alter control flow, never read the object after the callback.
- `a35-conversation-reentrant-think` and `a35-conversation-guard-release`:
  hold a local `Add_Ref`, find the same object by pointer instead of a stale
  index, and release list ownership. A finished conversation is always removed
  after `Think`/`Stop_Conversation`. The refreshed `count` after a removal lets a
  conversation started by a callback receive one `Think` in the same frame;
  upstream deferred it one frame. This changes timing by at most one frame and
  drops nothing.
- `a36-active-conversation-monitor-admission`: load validation only. The new
  `default:` branch rejects chunk IDs the original `Save` never writes
  (`VARIABLES`, `MONITOR`, `ORATOR` only), so valid saves are unaffected. A
  rejected conversation is kept alive until the whole load fails.
- `a36-conversation-object-admission`, `a31-conversation-loop-scope`: bounds,
  category and index-scope fixes. `Register_Monitor` and `Notify_Monitors_On_End`
  are otherwise byte-identical to upstream.
- Save returns `!csave.Has_Error()`; load returns false on malformed input. Both
  fail the save/load, never silently dropping a monitor.

No patch removes, defers, filters or replaces the observer call.

## Open items (not defects introduced by the port)

1. Monitor registered after the conversation already ended (retail ordering
   hazard). M10 scripts call `Create`, `Join(NULL)`, `Start`, then
   `Monitor_Conversation`. `Start_Conversation` ends the conversation
   immediately with INTERRUPTED if a key conversation is playing
   (:399-401). Nobody is registered yet, and `Register_Monitor` on a finished
   conversation never fires. Retail does the same, so that primary would not
   count. Not changed: adding a late delivery would depart from original
   behavior. Whether M10CON005/011/014 are key conversations was not parsed here.
   Telemetry signature: monitor outcome kind 0 for an `ActionID` whose
   transition-end record has an earlier timestamp and no kind-3 observer call.
2. Unresolved conversation on a corrupt save. `Load_Variables` leaves
   `Conversation == NULL` if the ID cannot be resolved, and
   `Stop_Conversation` (:1262), `Say_Next_Remark` (:484),
   `Is_Audience_In_Place` (:575) and
   `ConversationMgrClass::Is_Key_Conversation_Playing` (conversationmgr.cpp:1116)
   then dereference it. This
   needs a corrupt or foreign save, since valid saves always carry the category.
   Hardening (guard in `Think`/`Stop_Conversation`, end with UNABLE_TO_INIT) was
   not applied: it needs a new SHA-anchored staging patch, stage-script entry and
   inventory regeneration, and no valid path reaches it.
3. `ConversationMgrClass::Think` keeps the original fixed `count` while a
   conversation stays unfinished, and refreshes it only after a removal. Original
   has the same property; a callback that shrinks the list without finishing the
   current conversation is not a known path.

## Physical validation signature (M10)

For each of 1001, 1002, 1004 expect, in order: Killed on the building; monitor
registration with outcome 0 and the building's object ID; remark transitions;
`transition end` with reason ENDED; a kind-3 observer call with the same
`ActionID` (100014, 100005, 100011) and object ID; then the objective custom
event. Absence of the kind-3 record with a recorded end is the hazard in item 1.
For save/load, quick-save mid-line, load, and expect the end record to carry the
saved `ActionID` with a new instance token and a kind-3 call after the relink.
