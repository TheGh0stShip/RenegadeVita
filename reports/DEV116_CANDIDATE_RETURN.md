# Dev116 candidate return

Canonical retry completed successfully. The first failed attempt remains
retained separately; no frozen prior evidence was overwritten.

- VPK SHA256: `4ed1280a7cb9dbadae3d77957c52a48f5522eba0a1eda5ac7a862873fc59f211`.
- ELF SHA256: `60fdcc2c4545601b6cf5c2234a591da6f9f6ac090b6b22789914a552948fd444`.
- SELF SHA256: `5c9102d72098fcad8fade3f7cb1385814422fd58f50f9fa20850bcdac369f3c7`.
- Identity verification: `dist/A3.5-dev116-IDENTITY-VERIFICATION.json`, PASS.
- Canonical log: `build/dev116-canonical-retry.log`.
- Diagnostic bundle: `dist/A3.5-dev116-BUILD-DIAGNOSTICS-20260909-102424.zip`.

VPK inventory is exactly eboot.bin and sce_sys/param.sfo. Retail assets and
saves are not included. Packaged SELF matches the verified native SELF.

Both HUD digit atlas comparisons passed in the integrated host tests. Original
M00 host runtime passed two in-process cycles. These do not establish native
visual correctness or complete tutorial playthrough.

Vita3K setup was started for this exact package. The original checkpoint and
fresh quicksave comparison are prepared as recorded in DEV116_RUNTIME_PLAN.md.
Native runtime results remain pending. Physical acceptance remains unchanged.

## First Vita3K return

Matching setup receipt:
`D:/Vita3K/RenegadeEvidence/A3.5-dev116-setup-20260909T154009416848Z/setup-receipt.json`.
Run directory: `D:/Vita3K/RenegadeEvidence/Dev116-checkpoint-20260909T154023Z`.

The original inactive player was reactivated and the saved star/camera reused;
the original session reached gameplay. `step-20260909T154116505Z.png` shows
readable health digits rather than the earlier scrambled atlas. Weapon/ammo
digits remain unassessed because this checkpoint is unarmed.

`step-20260909T154148383Z.png` shows the original EVA Objectives screen with
readable text and a dimmed, still-visible Options label. `window-010.png`
shows loading status text; one image alone does not prove bar animation or
the absence of a late-loading hitch.

Fresh original quicksave creation passed the strict M00 structure validator
and was archived unchanged at
`build/tutorial-checkpoints/m00-reloaded-dev116-fresh`.
Size: 96524 bytes. SHA256:
`b762da3e439e8cb347e484e5f8100dedaf4407663e1ef77fbbf5a14faf081d50`.
Receipt: `build/dev116-fresh-quicksave/`.
Reload of this newly written save and existing-slot overwrites remain unproven.

## First run termination: Windows Qt failure

The runner reported PROCESS_FAILED at 2026-09-09T15:42:07Z. Native resume
input was not acknowledged, so Dev116 pause/resume is not passed.

Windows Application event 1000 identifies process 0x5718 (22296), matching
this run, with faulting module Qt6Core.dll 6.11.0.0, exception 0xc0000409,
offset 0x1cf68. Event 1001 reports BEX64 with subcode 7. Report ID:
7804ee64-8a36-495d-9eb8-1216cefbd787. Application: Vita3K.exe 0.2.1.4093.

This is a Windows emulator-process failure, not a PSP2 crash dump. It does
not prove physical stability or identify the trigger inside the emulator.
No emulator or game-code workaround was applied. A second run of the same
verified package was requested to load the newly created quicksave directly;
receipt: `build/dev116-fresh-reload-request.json`.

## Fresh-save original reload passed

Second run: `D:/Vita3K/RenegadeEvidence/Dev116-fresh-reload-20260909T154355Z`.
Its separate stdout confirms original opens of quicksaveA.sav. The native
runtime log contains multiple runs: the new section begins its checkpoint
handoff at line 2002, explicitly naming save/quicksaveA.sav, followed by saved
player/star reuse at 2967-2970 and original session ready at 3345. Do not use
the earlier dev116-post-sydney.sav entries as evidence for this reload.

`step-20260909T154456299Z.png` shows gameplay with readable 050 health and
050 armor. This closes fresh original save creation, strict archive validation,
and original-engine reload for the retained b762da3e... checkpoint. It does
not close existing-slot overwrite reliability or full M00 completion.

The second run subsequently exited in the same Windows Qt failure during
gameplay, not pause. Event 1000 matches PID 7344, Qt6Core.dll offset 0x1cf68,
exception 0xc0000409, report ID 1d346863-5656-4d47-97b5-7358a3ebb42b.
Both failures occurred about 100 seconds after launch. The new save reload
was observed before the failure; sustained runtime stability is not passed.

A bounded 180-second comparison of the same SELF and checkpoint was launched
without the PrintWindow helper. Existing runner foreground screen captures
remain enabled. This tests a possible capture-harness contribution without
changing game or emulator code. Outcome is pending.

## Capture comparison return

The no-PrintWindow run survived its full 180-second bound. The runner reported
TIMEOUT_UNASSESSED, then terminated its owned process normally. The same short
turn/forward movement was acknowledged and released. Native receipt paths:
`build/dev116-no-printwindow-move-01.json` and `-02.json`.
No automatic screen capture was available because the game was not foreground.
Thus this is bounded process survival, not visual or mission-completion proof.

The contrast implicates the capture/foreground path but does not isolate
PrintWindow conclusively. The step helper now avoids PrintWindow and copies
screen pixels only when the owned game is already foreground, without forcing
focus. Background input remains available. A run-local optional F12 binding
allows testing Vita3K's built-in screenshot path without global config changes.

Runner input summaries now report unknown when only external native-command
receipts exist; they no longer infer "no input" from an empty window-step
inventory. Earlier immutable runner receipts must be interpreted alongside
the separate native receipts named in these reports.

## Focus-independent visible capture

Vita3K's run-local F12 screenshot command was consumed and wrote a JPG, but
the inspected image was black. File creation is not visual success.

`tools/capture_vita3k_visible_windows.ps1` instead exposes only the verified
owned game window with NOACTIVATE, copies its screen rectangle, and restores
window order in finally. It never uses PrintWindow or SetForegroundWindow.
In run `Dev116-native-capture-20260909T155157Z`, capture
`visible-20260909T155403492Z.png` visibly shows outdoor gameplay; its receipt
records foreground unchanged and window order restored. The same process had
survived beyond the earlier roughly 100-second failure point by this capture.
Continue assessing stability; this does not establish long-term or physical
acceptance.

## Gunner milestone

The original route reached Gunner and the Auto-Pistol instruction, captured
at `visible-20260909T155550413Z.png`. D-pad Right/Left cycled the original
weapons. Subsequent captures show readable 100 rifle ammo and 012 pistol
ammo, with original weapon labels and icons.

Fresh quicksaveB.sav was structurally validated and archived unchanged at
`build/tutorial-checkpoints/m00-gunner-weapons-dev116` (113687 bytes), SHA256
`4526385983138b19c24eeae9e3eccf36ccc6710133d918cefe71b1c72a381d97`.
This checkpoint has not yet been reloaded. The earlier validated fresh-save
master remains intact. Original firing-range completion is next.

New release gap: authored tutorial text still instructs PC keys such as
"Press 1" despite the functioning Vita weapon-cycle controls. Correct these
platform-specific prompts without replacing original tutorial scripts.
