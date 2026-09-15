# Dev116 next runtime work unit

## Prepared state

Vita3K was confirmed absent before changing the development save setup.
Existing quicksaveA.sav and quicksaveB.sav were moved, not discarded, into
`build/dev116-quicksave-before-fresh-test/`. Their original-path hashes are
recorded in `original-sha256.txt`. No retail files were changed.

The unchanged original post-Sydney checkpoint was restored into a new slot,
`save/dev116-post-sydney.sav`, and queued for native validation and reload.
Receipt: `build/dev116-checkpoint-request.json`.
Save hash: `f651d389877c6df19dc2fa95b1c636627a331e2f451d46f286599c56f8981ec7`.

The next quicksave will therefore create a fresh slot rather than overwrite
the known failed one. A fresh-save pass alone will not close the overwrite
failure. Keep the strict archive validator and original save bytes unchanged.

## Runtime order after matching artifact closure

1. Install the completed Dev116 artifact with identity and retail reconciliation.
2. Confirm the original checkpoint reload and inspect numeric HUD rendering.
3. Inspect original EVA Objectives and Map; confirm unsupported demo Options
   is visible but inactive, then return to gameplay.
4. Create and strictly validate a fresh original quicksave; retain its bytes.
5. Repeat original quicksaves across both slots, retaining each result, to
   distinguish fresh creation from shorter overwrite failure.
6. Follow the original barracks/weapon-training objectives through M00 end.
7. Observe the full fade, exact thank-you, credits and safe termination.
8. Close the owned emulator and retain matching logs/captures/receipts.

The dev116 canonical retry remains in progress; none of these new runtime
checks is claimed complete. Existing Dev115 checkpoint reload and one
pause/resume cycle remain separate evidence.
