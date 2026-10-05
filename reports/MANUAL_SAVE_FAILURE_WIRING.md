# Manual save failure and restored-player source review

Status: source inspection and local edits only. Uncommitted/unvalidated;
no staging, patch execution, tests, build, emulator, device or commit/push work.
Complete-game, quicksave reliability and physical acceptance remain open.

## Original manual save route

The full runtime source lists already select original dlgsavegame.cpp. Original
EVAEncyclopediaMenuClass opens SaveGameMenuClass in the mission pause menu.
Save button, description-field Enter, and confirmed overwrite all reach its
Save_Game method. Original SaveGameManager and _CommandoSaveLoad retain file,
object/script, conversation and campaign serialization ownership.

That method previously called End_Dialog unconditionally after Save_Game.
The selected native SaveGameManager write-status addition already observes
creation/open/write/close failure, but this manual caller did not consume it.
It therefore dismissed the save screen on a failed write as well as success.

Selected commando-a36-manual-save-write-status.patch now checks
Last_Save_Write_Succeeded before the original End_Dialog. Failed attempts keep
the original SaveGameMenu alive and show an original DlgMsgBox with a retry
message. The popup uses the existing WCHAR text overload and no notification
observer, so its OK does not authorize an overwrite or delete. Successful writes
continue through the original close path. Existing overwrite confirmation and
save slot/description behavior remain the owners; no save format changed.

The new-slot search also stops when its writing factory or returned file is
missing, leaving an empty output filename. Previously a null returned file
left done=false and kept probing forever. The caller now rejects that empty
filename and shows the same original error-popup mechanism. Existing native
free-space query failure receives a message; the original low-space translated
popup and two-megabyte pre-check remain unchanged. A missing overwrite filename
token returns before dereference. No slot limit, forced success or replacement
save UI was added.

Save button ID1316 is distinct from back/cancel. Original DialogBase dispatches
the original default command handler; the handler closes on back/cancel and
does not close the manual Save button. Description Enter calls Save_Game
directly; overwrite confirmation calls it with prompt=false.

## Restored-player binding failure handoff

The current native checkpoint route already rejects invalid local player/star
identity, unsafe inactive-player reuse and a changed binding after cGod::Think.
Those four rejection exits previously ended with neither ordinary success nor
guarded menu recovery. They now call the existing local failure-recovery helper
with appended process-local diagnostic code11, PLAYER_BINDING_FAILED.

Admission checks, original inactive-player activation and source object identity
are unchanged. The port does not synthesize a replacement soldier, alter save
inventory or report a successful restore. Recovery uses the original cleanup
and the existing independent resource-release gate before original menu reentry.
Demo policy remains separate. Code11 changes no saved/wire fields and does not
prove every malformed player or script state is detected.

## Terminal-state save admission

Original CommandoSaveLoad writes cGod through its GOD chunk. cGod saves only
its integer State; both Star_Killed and Mission_Failed change SINGLE_RUNNING
to SINGLE_DEAD before opening different original popup classes. No popup reason
is serialized there. The selected save-state admission patch therefore exposes
`cGod::Can_Save_Current_State` and admits serialization only while the original
single-player state is `SINGLE_RUNNING`.

Manual save reports the existing Vita WWUI failure popup and remains open;
Quick_Save returns before slot selection/write; pending autosave waits for a
running state; and `cGod::Save` independently rejects terminal serialization.
Original SoldierGameObj post-load and terminal callbacks remain unchanged.

This deliberately avoids adding a death/failure reason to the original save
format or synthesizing a terminal callback during load. Existing legacy saves
that already contain SINGLE_DEAD remain subject to load admission and cannot be
claimed reconstructable. Runtime reachability and physical popup behavior are
still unverified, but creation of new terminal-state saves is closed in source.

## Evidence and acceptance limits

Read-only original sources: staging/commando/dlgsavegame.{cpp,h},
dlgevaencyclopedia.cpp, DlgMessageBox.{cpp,h}, renegadedialogmgr.cpp,
commandosaveload.cpp, god.cpp and combatgmode.cpp; staging/wwui/dialogbase.cpp;
staging/combat/soldier.{cpp,h}, scriptablegameobj.cpp and combat.cpp.
Current owners: port/platform/vita/a31_vita_runtime.cpp and
port/platform/a31_gameplay_boundary.cpp. Native status declaration:
port/platform/vita/a35_level_load_status.h.

Prerequisites: selected combat-a36-save-write-status.patch and
wwlib-a36-write-failure-status.patch; original manual dialog/WWUI/resource graph;
the existing native filesystem provider and failed-load cleanup gate. The new
manual patch is selected before the reload-loading presentation patch in
tools/stage_sources.sh. No new ABI artifact
exists; all pending interface changes require coherent compilation.

Write completion is not proof of structural validity, reload fidelity, atomic
replacement, or power-loss durability. A failure can leave a partial file;
this change does not guarantee preservation of an overwritten save. The error
popup appears only if the writer returns: it does not repair the reported
conversation-serialization freeze or make saving asynchronous.

The subsequent loading-lifetime correction disarms the initial loading callback
before full-port gameplay, so ordinary save status changes no longer target
that retained screen. This remains source-only and is not serialization-hang
recovery. See RELOAD_LOADING_PRESENTATION_WIRING.md.

Pending focused evidence: new slot and confirmed/cancelled overwrite, name edit
and Enter, failed factory/open/write/close, free-space query failure, popup OK
and retry, no success dismissal on failure, subsequent valid load, held controls,
terminal-state rejection, legacy terminal-save handling, and repeated
save/load/resource cleanup. Host, ARM,
emulator and matching physical Vita/PSTV evidence remain separate; none ran.
