# Dev130 independent pause-menu validation

Native target: physical Vita ARM/GXM. Vita3K is a separate functional evidence
class; no emulator FPS tuning or physical acceptance. Release gates remain 0/10.

Build: 149 focused checks, original M00 host and retained UBSan two-cycle checks,
incremental ARM/ELF/SELF/VPK verification pass. Not a canonical build pass.
Frozen matching artifacts: `build/dev130-closed-incremental/receipt.json` (30 files).
SELF: `45d2bfd1832815c5acd0891d7518f0dac5d82cad301427ec26dd16d4fb7468ae`.

First runtime return: `build/dev130-fresh-return/return-receipt.json`, 200 files,
900-second owned run with matching guest debugger. Native Exit Yes completed
teardown and lifecycle END clean. Owned emulator shell stopped without force.
Runner labels PROCESS_FAILED with null exit code after external shell closure;
this is not a verified zero process exit. Native lifecycle evidence is distinct.

| Item | Observed result |
| --- | --- |
| Objectives | Original empty objective list at tutorial start; no invented objectives. |
| Map | Actual tutorial map visible, capture `step-20260915T001817558Z.png`. Zoom out/in changes scale correctly (`002454311Z`, `002513072Z`). |
| Data | Labels, values and elapsed game time visible, `001820971Z`. |
| Weapons | Fresh original tutorial reveals Automatic Pistol; name, model and description visible, `001803124Z`. |
| Characters / Vehicles / Buildings | All pages open. Lists empty at fresh tutorial start; populated model checks remain open. |
| Help | Original diagram and Vita captions visible; Circle returns. Cycle Objectives remains Unbound. |
| Audio / Video / Performance | All reachable. Native video caption and fixed capabilities visible. Original sliders apply. |
| Preferences | Native file write and replacement pass. Dialog volume 51%, surface mode 1 survive full Save/Load teardown and are visible in restored UI (`002158787Z`, `002204586Z`). Surface mode subsequently restored to 2. |
| Save | Original UI creates `savegame02.sav`; strict M00 chunks pass, 95,741 bytes, SHA256 `477c42378265dcc1b92d276419b6aba448c60a4d56ed41ce11f6574ed1a9ef32`. Private archive under `build/dev130-private-menu-save/`; never include save bytes in telemetry. |
| Load | Original list and controls visible. Actual `savegame02.sav` loads after complete original teardown. Matching saved position and gameplay visible `002138470Z`. |
| Delete | Save-page confirmation text and both buttons visible `002309344Z`. No preserves exact test-save hash; Yes removes it. All pre-existing saves unchanged (`delete-verified.json`). Load-page Delete still to test. |
| Exit | Text and Yes/No buttons visible `002344608Z`. No returns to EVA. Yes completes original native teardown with lifecycle END clean. |
| Resume | Returned to gameplay after second menu/settings sequence, responsive through frame 1672; further START and clean Exit passed. |

Save dates are 0/0/0 in Vita3K. Its own stdout explicitly reports
`Unimplemented sceRtcSetWin32FileTime import called`. The native firmware RTC
boundary is retained; date display is not validated by this emulator. No
emulator-specific replacement was added. Save description text entry still
needs a native keyboard boundary; new controller saves use "Manual save".

Second run: `D:/Vita3K/RenegadeEvidence/Dev130-mobius-pause-20260915-r2`, 1200-second
bound. START during Mobius remark 8 at frame 2; paused about 7m37s through Help,
all Options pages, Save, Exit No, Load/Delete and all tabs. After resuming, speech
completed at frame 637, gameplay continued to frame 9831, camera/movement/Action
worked, and Exit Yes completed native teardown. The previous hang did not
reproduce; its cause is not proven fixed and this is not physical acceptance.

Original Action on Mobius produced Data Link Updated. Characters then displays
Mobius, model and description (`step-20260915T003829474Z.png`). New original save
with that discovery is retained privately in
`build/dev130-r2-private-menu-save/discovery/`; current emulator `savegame02.sav`
is 96,033 bytes, SHA256 `8f7062bf603eca0b933fceed2631486ebfc5141971d44153797b0ce5bddc333d`.
Existing pre-run saves remain unchanged. Vehicle/building populated views remain open.

Controller defect reproduced: Right did not move Yes/No focus; Cross still chose
Yes and deleted only the disposable test save. Load Delete therefore passed its
Yes path, but directional button navigation failed. Dev131 adds a focused
original-dialog host test (baseline FAIL) and a native-scoped adaptation using
the original focus order. Its wrap scan skips hidden/disabled/static controls
and is bounded even when no control is eligible. Corrected host and retained
UBSan pass two original M00 cycles; 149 focused checks and incremental ARM
closure pass. Frozen artifacts: build/dev131-closed-incremental/receipt.json.

Dev131 runtime return: build/dev131-controller-return/return-receipt.json.
D-pad Right visibly selects No; Cross returns to EVA. Save creates a disposable
original M00 save. Delete No preserves SHA256
7dfe091a8421643c5410fe919d1f7df55353fc5a29b7c0c88036301113161625;
Delete Yes removes only that save. All pre-existing saves remain unchanged.
Directional wrap and Exit Yes pass. Mobius name/model/description survive an
original save reload (`step-20260915T005418527Z.png`). All 17 native input steps
released. Native END clean; owned emulator shell stopped without force. Wrapper
reports PROCESS_FAILED with null exit after separate close, not a zero-exit pass.

Next: remaining native text-entry, Cycle Objectives and representative populated
Vehicle/Building checks, followed by the continuing hardware optimization audit.
All physical testing remains held. Intro playback and native 60 FPS remain open.
