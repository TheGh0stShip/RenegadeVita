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
Ion-beacon event and mission transition. Practice mode and the reported
frame drops remain separate unverified issue items. Issue #1 stays open.

## Physical PSTV return

The user installed Dev197 on PSTV 3.65 Enso and confirmed the diagnostic
pre-Ion M13 save loaded correctly and EVA exit returned to the main menu.
The installed `eboot.bin` SHA-256 matched the packaged SELF:
`4d81003ab8fcf4dbe8a958623e83600ce4b8ac468f22971e907b65a723bde831`.
The matching PSTV log records original `load-game-return`, Combat post-load
completion, saved object/player/camera reuse, 15 interactive frames, EVA exit,
clean session teardown, and a new original main-menu dialog. The retained
flight recorder and title-owned captures are local physical evidence, not
retail data or release assets.

This is a **passed bounded physical PSTV save-load/menu-return check**. It is
not full physical candidate acceptance: the user reported a long load, and
the log measured 12,443 ms for M13 dependency preparation. The first 15
gameplay frames were dominated by startup work (p50 146 ms, p95 473 ms,
worst 2,216 ms); this short sample cannot establish steady-state FPS.
The original loading-screen and EVA confirmation captures were inspected.
Ion-beacon completion, subsequent mission progression, Practice, and the
reporter's other PSTV symptoms remain unverified on this build.
