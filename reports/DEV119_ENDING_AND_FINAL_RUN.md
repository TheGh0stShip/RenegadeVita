# Dev119 ending, loading presentation and full tutorial run

Dev118 Power Plant reload through original M00 success is confirmed in Vita3K.
User reports Maus appeared correctly, killed both Nod officers, saw thank-you
text and credits, then game closed. Retained screenshots show both ending
pages; native lifecycle ends clean. Evidence: build/dev118-finale-return/.
No assault quicksave was created; prior live quicksave restored offline from
its verified backup. Immutable Power Plant and earlier checkpoints retained.
Emulator shell PID 3148 closed cleanly after game teardown.

User requests:
- Return to original main menu after credits instead of closing the title.
- Polished credits with imagery, larger text and intentional centered layout.
- Loading progress bar that fills incrementally instead of percentage text only.
- A final user-controlled run from startup through tutorial completion, including
  menu navigation, with gameplay capture, profiling and framebuffer inspection.
- Continue autonomously without approval questions. User controls the final run.

Plan:
1. Complete Dev119 credits using original MenuBackDrop/WW3D imagery and original
   sentence rendering; no packaged retail assets or substitute scene renderer.
2. Return to the original frontend after clean owned session teardown, skip
   startup movies on return, and permit fresh tutorial selection. Validate
   repeated lifecycle and explicit menu exit. Initial source changes are pending
   tests; reinitialization must not be called accepted from source alone.
3. Add a readable actual fill bar in the original loading presenter using its
   existing progress value; preserve load-phase ownership and monotonic progress.
4. Focused checks, affected ARM objects, consolidated incremental package.
5. Prepare bounded full-run recording and native screenshot capture where
   supported, alongside candidate logs and frame-time profiling. Window captures
   remain a separate evidence class; do not label them framebuffer proof.
6. User navigates full tutorial. Retain each returned defect and finish fixes;
   sky rectangles/elevator black geometry remain unresolved. No release claim.

User clarification: the final playthrough occurs only after remaining known
issues have been fixed. Do not hand over a candidate with known unresolved
sky/elevator/loading/credits/menu-return issues for that final run. Engineering
tests and bounded capture/profiling preparation may proceed autonomously.

Current source: lifecycle reentry, main-menu routing, original animated menu
backdrop credits with centered title/body text, and monotonic interpolated
loading fill bar implemented. Staging passes 167 patches. Focused executable
checks cover actual lifecycle loop success/failure return and loading fill.
15 focused checks pass in build/dev119-ending-focused.log; a30_main,
a31_vita_runtime and original loadingscreen ARM objects compile successfully
in build/dev119-presentation-arm.log. These do not prove repeated engine
initialization or visuals. Next: consolidated engineering package and bounded
credits/main-menu/restart runtime test, separate from the held final playthrough.
Dev118 remains the installed, immutable successful finale candidate. No Dev119
build or runtime proof yet. Physical PS Vita/PSTV access remains held.

## Dev119 engineering package (supersedes installed/build statement above)

131 focused fast contracts pass. ARM/SELF/VPK closure passes after updating
the old runtime symbol signature gate to its new `(int, bool)` interface.
Closure reused passed tests and existing objects. Retained logs:
build/dev119-fast-console.log, build/dev119-fast-closure.log.

SELF b8b06f858a8e7e6e5841b7301e9083cded2442a4f45e141ce8165ad7a60efbeb
VPK 4bf1ac5d93adfd9efbabae7a8a5609767391d442ccb3120fd4088b2152e3d4d3
ELF 8378d0a497cbdc8a46dafd89559ad149427b0005449eb9338d8cb56f628e83c6

Matching artifacts, source hashes and diagnostics-only ZIP retained in dist/.
Dev119 installed with verified Dev118 title backup by prepare_vita3k_demo.py;
setup receipt A3.5-dev119-setup-20260914T191359742228Z under D:/Vita3K/
RenegadeEvidence. Original Power Plant save restored unchanged into fresh slot
dev119-powerplant-engineering-20260914.sav; queued with original reload checks.
Launching Dev119-powerplant-engineering-20260914-r1, runner 50246, 1800-second
bound, native screenshots enabled via F12, native input enabled for bounded
engineering actions. Runtime validation pending. Final user run remains held.

Capture preparation: Windows FFmpeg is available via the user's WinGet link
and supports gdigrab HWND input. Any retained recording must target only the
validated game window and must be classified as window video, not native
framebuffer proof. Native F12 screenshots require separate output validation.
