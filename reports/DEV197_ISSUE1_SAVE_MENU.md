# Dev197 campaign save/menu checkpoint

Dev197 addresses the Vita frontend handoff observed while triaging GitHub issue
#1. In Dev196, an M13 save was written before the Ion beacon, but choosing EVA's
exit command shut down the application instead of reopening the main menu.
The matching runtime log records `A4 pause: original EVA left; resumed=0 exit=1`,
then complete Combat/session teardown and a clean process exit. The save at
`ux0:data/renegade/user/save/savegame03.sav` was 293216 bytes, SHA-256
`dacea97fe270ec506022993e724f1ba0ae9cd4896502c18125a547d18eee5bf4`
when inspected; its existence is not reload proof. It is user data and is not
included in the package or repository.

Cause: the original EVA callback uses `Stop_Main_Loop` as a safe way to leave
the current world. The Vita outer loop cleaned up that world but lacked the
`return_to_menu_requested` handoff, so it exited the app. Dev197 sets that
handoff for a confirmed EVA exit, leaving save reload and diagnostic replay
abort distinct. The outer loop already reopens the original frontend after
clean session teardown when that flag is set.

Evidence: focused frontend contract tests pass (15); the canonical host,
ARM, ELF/SELF/VPK and hash gates pass; Dev197 is installed and hash-verified
in Vita3K. VPK SHA-256:
`b01c61f254edaeff1ce49e9d73424ac3c33e15ac6912023cff57c19d94304cdb`.
The subsequent user-driven Dev197 Vita3K run loaded `savegame03.sav` and the
user confirmed the restored state was correct. The matching log records the
save selection, original `load-game-return`, Combat post-load completion,
reused saved player/camera, 31 interactive frames, EVA exit, complete session
teardown, and the original frontend reopening. This passes the bounded M13
save-reload and exit-to-menu check in Vita3K; it does not prove later Ion-beacon
progression, full save-state coverage, or physical PSTV behavior.

Next experiment: continue from the restored M13 checkpoint through the
Ion-beacon event and mission transition, then repeat save/reload and EVA
menu return on PSTV. Practice mode and the reported frame drops remain
separate unverified issue items. Issue #1 stays open.
