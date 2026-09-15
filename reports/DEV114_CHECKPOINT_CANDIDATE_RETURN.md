# Dev114 canonical checkpoint candidate

Canonical build completed successfully from
`build/vita-a35-dev114-candidate-20260909-093410/`, with
`RENEGADE_VITA_DEVELOPMENT_CHECKPOINT=1`. This is a developer checkpoint
candidate, not a public package. Terminal evidence:
`build/dev114-checkpoint-canonical.log`; retained build outputs: `dist/`.

## Matching identities

- VPK: `4c40bb90ee9b6bcb343b33da56f361c02080dd2d28620f206a1255fa5790142d`
- ELF: `c14c29ae6cb8861a60624d2d8a9a97ce0837ece2dba77d5e7dbb6f720a69139f`
- SELF: `c7d59fb7382d23fbb12eccc74979b936dda1503e683ed2717353f537bfa4b0dc`

`dist/A3.5-dev114-IDENTITY-VERIFICATION.json` passes candidate identity,
runtime breadcrumb and packaged-SELF matching checks. Canonical archive,
symbol and manifest gates passed. No retail assets are included in the VPK.

## Emulator cycle in progress

Installation completed with source-data coverage and title-scoped backups:
`D:/Vita3K/RenegadeEvidence/A3.5-dev114-setup-20260909T144933890544Z/setup-receipt.json`.

The one-shot checkpoint request was absent, so it was queued again without
changing the save. Receipt: `build/dev114-checkpoint-request.json`.
`save/dev112-post-sydney.sav` is 96,458 bytes and matches the archived hash
`f651d389877c6df19dc2fa95b1c636627a331e2f451d46f286599c56f8981ec7`.

The hash-gated Windows runner was launched with a 150-second bound and owns
termination of its exact child emulator process. Evidence directory:
`D:/Vita3K/RenegadeEvidence/Dev114-checkpoint-20260909T1450Z/`.
Native background-input support was enabled; no step was issued at launch.
Runtime restore failed at the active-player guard. Exact diagnostic:
`local_id=1 player=0x0 active_players=0 star=0x880a48f8 control_owner=1`.
The native port completed its controlled-failure teardown. Vita3K then logged
Windows `EXCEPTION_ACCESS_VIOLATION`, read at `0x48804E320`, while stopping
the game session. The Windows runner reports `PROCESS_FAILED` with a null
exit-code field, not clean termination. No inputs were issued.

This supports the source-traced missing inactive-player reactivation. Dev115
source now requires a unique loaded player, no active players, matching local
ID/control owner and reciprocal saved player/star links before invoking
original `cGod::Create_Player`'s inactive reuse path. It checks the same player
and star remain afterwards. It does not manually activate, respawn, reset the
camera, or replace saved mission state. Five checkpoint tests pass in
`build/dev115-checkpoint-contract.log`; the new guard-order test is a source
contract, not runtime proof. Dev115 canonical and emulator proof are next.

## Post-build source integration

Only after canonical process exit and terminal success, the tested EVA
generator and C++ contract patches were applied with zero fuzz. They add the
original shell and seven tabs, correct captionless control parsing and retain
original dimensions/IDs/styles. The integrated host contract passed:
`build/eva-integrated-twmhL1/host-contract.log`.

The source tree is therefore ahead of Dev114. Its immutable package does not
contain this EVA correction. Do not report Dev114 captures as validation of
the newly integrated source. Original temporary experiment validators apply
patches to the old baseline and should not be rerun against integrated source.

HUD font header inspection found 32-bit uncompressed TGA sources with alpha:
192x256 for FONT12x16 and 96x128 for FONT6x8, both in always.dat. The suspected
missing 16-bit conversion is not supported for those sources. Retained
metadata: `build/dev114-hud-font-headers.json`; no retail bytes extracted.
