# Dev114 checkpoint session trace

## Source-backed next action

The original `cPlayer` save/load implementation preserves ID, name, kills,
deaths, team, parent player data and a pointer-remap token. It does not save
`IsActive`. That member is a `cBoolean`, whose default constructor initializes
it to false. `cPlayer::Load` does not activate the loaded player.

The native restore guard currently requires an active-player lookup and a
count of one before continuing. Therefore a normally loaded inactive player
can fail this guard even when original deserialization and pointer remapping
succeeded. This is a stronger source-backed explanation than the previously
unproven mission-mode-reset theory, but it does not identify every field of
the observed Dev113 combined identity failure.

Original `cGod::Create_Player` first searches active players by name, then
inactive players. In the inactive case it reuses the existing object, restores
session ID/in-game state and activates it; it does not create a new player or
spawn a soldier. Its active-name branch can delete player objects, so blindly
calling it before checking identity is unsafe.

Original `SmartGameObj::Load` restores control owner and requests remapping of
its player-data pointer. Its post-load callback binds the existing player and
game object in both directions. Preserve those bindings and the loaded star.

Next runtime decision: inspect Dev114's separate local ID, player pointer,
active count, star pointer and control-owner fields. If the loaded player is
inactive, establish a unique existing player/star binding before invoking the
original inactive-player reactivation path. Reject ambiguous identities and
retain checks that no new player or soldier was introduced.

## Diagnostic limits

A read-only recursive save probe aborted on a container boundary assertion.
Its generic traversal cannot safely interpret every original persistence
container. `build/dev114-save-identity-preflight.json` is empty, not valid
evidence. No save bytes were changed and no saved-player ID was established
by that probe. The archived post-Sydney manifest remains the source of its
recorded save hash; reload remains unproven.

HUD follow-up: health/ammo bitmap text uses original `FONT12x16.TGA` and
`FONT6x8.TGA` through Font3D surface repacking, not the loose Arial TTF path.
The native surface copier currently supports matching formats or 32-bit
ARGB/XRGB to A4R4G4B4 conversion. Original surface loading also normalizes
several 16-bit/palette formats. Establish actual font source formats before
adopting a conversion change; no HUD correction is claimed from this trace.
