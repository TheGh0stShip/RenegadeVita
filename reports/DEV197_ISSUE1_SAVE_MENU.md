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
No Dev197 gameplay launch, save reload or PSTV result is claimed here.

Next experiment: launch Dev197 in Vita3K, load `savegame03`, verify M13
position, inventory and objectives, then complete the Ion-beacon event.
Choose EVA exit and verify return to the main menu without app termination.
Repeat on PSTV before closing issue #1 as resolved. Practice mode and the
reported frame drops remain separate unverified issue items.
