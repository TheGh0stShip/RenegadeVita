# Dev118 visual-defect work — 2026-09-14

User reports in the Dev117 progression session: rectangular sky artifacts,
moving jagged black rectangles/triangles in elevators, and squares in the
subtitle/message region after Gunner directs the player to Logan at the
Weapons Factory. All three remain visual acceptance failures.

## Objective-message ABI correction

Both Add_Objective and hidden-to-visible Set_Objective_Status passed a
non-trivial WideStringClass description through Format's varargs as if it
were a UTF-16 pointer. Explicit const WCHAR pointer conversion now preserves
the translated description and original ObjectiveManager/MessageWindow owners.
This is a demonstrated source defect consistent with the reported squares,
not yet confirmation of visual resolution.

Evidence: original production expressions execute through WideStringClass in
`tools/test_objective_message_abi.py`; both produce the complete expected
Weapons Factory/Logan message. `build/dev118-objective-focused.log` passes.
Zero-fuzz staging passes with 166 ordered patches in
`build/dev118-objective-staging.log`. The affected objectives ARM object
compiles in the existing fast tree (`build/dev118-objective-arm.log`, exit 0).
No canonical rebuild, new package or installation was performed.
The combined objective/tutorial/weapon ABI and incremental-staging contracts
pass 7/7 in `build/dev118-visual-focused.log`; shell/JSON syntax and
`git diff --check` pass. The objective regression is registered in the fast
candidate contract list.

## Sky and elevators

Subsequent user-positioned captures obtained in
D:/Vita3K/RenegadeEvidence/Dev117-hotwire-recovery-20260914-r2:
visible-20260914T184247536Z.png shows broad angular/rectangular sky regions;
visible-20260914T184455479Z.png, visible-20260914T184516855Z.png,
visible-20260914T184542933Z.png and visible-20260914T184607000Z.png show
the elevator structure and sharp black intrusions from several user views.
User clarifies the defect appears on the elevator itself, not the walls.
These are retained window captures, not framebuffer readback. Root cause
remains unconfirmed; trace elevator geometry/transparency/depth ownership.
This supersedes the missing-view statement below. Finale movement currently
takes priority; no additional positioning request is needed for these views.

The previous culling correction is already in Dev117; the new user report
means it cannot be treated as resolution. Current runtime font probes report
valid large/subtitle glyph rasterization, but neither these nor zero backend
errors prove visuals. Existing inspected session captures do not clearly show
the reported sky rectangles or elevator intrusions. window-190.png shows
outdoors near the Weapons Factory with a limited sky region; it is not a
controlled sky test. No speculative texture replacement, near-plane adjustment
or triangle suppression has been applied.
Optional independent CloudLayer image inspection could not run because the
system Python lacks PIL; this is not evidence of a missing/broken retail file.

Next: one user-positioned capture of the defect, then trace original texture
identity/alpha, draw state, camera/geometry and depth against that view. User
retains navigation; no automated movement or checkpoint reload interruption.
Physical Vita/PSTV access remains held.

## Hotwire checkpoint

At the user's reported Hotwire/Weapons Factory position, verified owned
Vita3K PID 10604/start and installed Dev117 SELF
5d2ecfa964d72ab0a2902307dcb4c9c55f9158549af6e54a3c8b1c64eb45cd50.
Backed up and hashed the existing quicksave before clearing the live slot to
avoid the known shorter-overwrite failure. Sent only original Select+Square;
the input receipt confirms both keys released. Immutable original M00 save:
`build/tutorial-checkpoints/m00-hotwire-dev117/checkpoint.sav`, SHA-256
ea6e0bc1d2e7c36795fc25071ee3dee41ac31266ee07418956fdce63ad5473e6.
Strict structure validation passed. Location is user reported; reload and
segment completion remain unassessed. Mobius master remains unchanged.
