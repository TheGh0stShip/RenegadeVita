# Dev104: native readback contract and original checkpoints

Dev103 fast package closure passed. Dev102 focus-free Windows HWND messages
with scan codes activated original Single Player and Tutorial, and PrintWindow
captured the game without foreground focus. The route then failed in Vita3K
with host EXCEPTION_ACCESS_VIOLATION after level_ready, before the mandatory
loading capture. This is emulator evidence, not a PSP2 dump or hardware result.

The next native operation passed a malloc-owned buffer to vglReadPixels. The
pinned VitaGL header requires a GPU-mapped destination for that extension, and
its implementation submits the caller's pointer directly to sceGxmTransfer.
Dev104 uses standard glReadPixels for CPU-owned RGBA output; the inspected
implementation synchronizes the source and uses CPU copy for this format.
This corrects a native API contract, not an emulator fork. It remains a causal
hypothesis for the observed host crash until a matching rerun.

Original SaveGameManager writes save/*.sav through the user-rooted writing
factory, but unqualified save/ reads previously resolved to retail. Dev104
routes both directions to user/save, maps Select+Square to original Quicksave,
admits only saves whose original map metadata identifies M00, and forwards the
selected save into the original threaded loader rather than hardcoding a fresh
M00 MIX. Renderer, mission scripts, serialization and object ownership remain
original. No saved segment or cross-build load is claimed yet.

The local checkpoint vault tool preserves byte-identical masters, creating-build
provenance, operator-supplied retail identity, explicit compatibility epoch and
passed-segment evidence. Restores require an offline game and create a new slot;
they never overwrite an existing save or claim a restored segment passed.
See `docs/TUTORIAL_CHECKPOINTS.md`. The final full M00 run is still required.

Status superseded by Dev105: Dev104 fast package passed 126 contracts. Matching
Vita3K run completed loading capture and all 60 scene prewarm frames, then
exited through native controlled-failure teardown. The first gameplay frame
counted a failed shadow render-target allocation probe as a rejected draw.
No repeat host access violation appears in this return. Retained runtime and
emulator logs: build/dev104-host-evidence/runtime-return-20260908T2200Z/.

The user explicitly authorized the saved-player reuse correction. Dev105
reuses the original restored local player/star and preserves saved camera mode;
incompatible identity fails closed without entering Create_Player's destructive
rejoin path. No checkpoint master or save/load round trip is proven yet.

Initial Dev104 fast tests failed two literal-source checks after the reload
condition gained the quicksave exclusion. The logically equivalent condition
was reordered to retain the existing checked expression plus the exclusion;
tests were not weakened. Background fast retry uses fast-build-r2.log.
