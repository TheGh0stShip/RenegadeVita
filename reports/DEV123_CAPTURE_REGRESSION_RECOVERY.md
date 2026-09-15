# Dev123 capture regression recovery

Connection recovery found Dev122's supposedly active run had already failed
and Dev121 had been restored. Installed Dev121 SELF was rehashed before action:
`7f79e0016d2d09bd65242370c6ac99fa51f505ba27b557bd7b270b9a7a43e0b4`.
No Vita3K process was active and the native input enable flag was absent.

Dev122's matching Windows log reports EXCEPTION_ACCESS_VIOLATION, reading
0x860AA1200, immediately after the native level-ready milestone and before
loading-capture return. Preserve this as emulator evidence, not a Vita crash
or verified guest stack. Frozen logs/window/receipt and SHA-256 inventory:
`build/dev122-resume-failure-return/receipt.json`.

Dev121 control used the identical Hotwire save (SHA-256
`ea6e0bc1d2e7c36795fc25071ee3dee41ac31266ee07418956fdce63ad5473e6`),
the same pinned emulator and Vulkan backend, a 90-second bound, and no synthetic
input. It reached visible Weapons Factory gameplay. Evidence:
`build/dev121-resume-control-return/receipt.json`, including inspected
`window-030.png`. Watchdog termination is not clean lifecycle acceptance.

The comparison implicates Dev122's GPU transfer capture path. Pinned vitaGL
`framebuffers.c` passes a negative display row stride to sceGxmTransferCopy;
this is a plausible emulator failure mechanism, not a verified stack diagnosis.
Dev123 removes that experimental transfer/allocation/synchronization path,
retains explicit front/back selection, and zeroes the caller buffer before
the prior RGBA8888 CPU readback. No upstream or retail source is modified.

Nine focused production readback/loading tests pass. Dev123 incremental
package passes all 134 focused checks and ARM/ELF/SELF/VPK closure in
`build/dev123-fast-console.log`. Installed with Dev121 backup; runtime
validation now reaches visible Hotwire gameplay. Native readback remains
black in previous emulator tests; Vulkan F12 screenshots are a separate working
capture source. No capture synchronization or visual correctness gate is closed.

Artifact SHA-256:
- SELF: `5b033c8ae067910a03df1345574e2e89d97e8bd14d5b54afc71040c59cb634df`
- ELF: `f7febfe8d8169e9e48f1bf391e36fa823140393c53ae5f8235a035eead275318`
- VPK: `e98ddb2fbb6c9d76e9a283642ef1d83329845eac7ee855204ac55e669c846a70`

Runtime closed at its 90-second watchdog at 20:10:21 UTC. Matching Vulkan F12
image is nonblack and visually shows Hotwire, weapon and readable HUD. Hashed
return: `build/dev123-recovery-return/receipt.json`. The sole synthetic action
was F12, released according to the step and terminal receipts. Owned emulator
terminated. This is loading-regression recovery, not clean-exit, fixed-camera
performance, native readback, or whole-demo acceptance.

Next: diagnose credits cutoff through original sentence/atlas ownership and
continue wall/sky/elevator,
credits cutoff, and repeated lifecycle checks. Final user playthrough and
physical PS Vita/PSTV testing remain held.
