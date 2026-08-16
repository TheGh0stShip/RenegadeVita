# A3.1 HUD stabilization regression

This regression is intentionally hardware-equivalent: the Vita platform
boundary reports legacy Font3D unavailable, shared policy selects
`CombatManager::Init(false)`, M00 post-load restores serialized HUD enabled
state, original cGod creates the player/Commando, and the first shared
simulation frame executes `CombatManager::Think`.

## Negative proof (before central resource gates)

On 2026-08-15, a disposable generated-staging probe removed only the central
`_HUDRenderResourcesAvailable` checks from `HUDClass::Think` and
`Is_HUD_Displayed`. It retained the maintained source patch untouched. ASan
then failed on the first original frame:

```
AddressSanitizer: SEGV
Info_Update  staging/combat/hud.cpp:2523
HUDClass::Think  staging/combat/hud.cpp:2971
CombatManager::Think  staging/combat/combat.cpp:747
A31_Interactive_Run_Simulation_Frame  port/platform/a31_gameplay_boundary.cpp:175
```

The state immediately before the fault was `serialized_enabled=true`,
`resources_available=false`, and `effectively_displayable=false`. This is the
same causal resource state as the A3.1.2 Vita `InfoRenderer == NULL` crash.

## Maintained repair proof

Deterministic `tools/stage_sources.sh` restored the 59-patch maintained staging
set. The exact ASan invocation then passed two complete in-process cycles:

- 120 original Time/Input/Generate_Control/cNetwork/Combat frames each;
- `WW3D::Begin_Render`, shared `CombatManager::Render`, and `End_Render` each frame;
- original player and Commando present in each cycle;
- post-load HUD serialized enabled with render resources unavailable in each cycle;
- clean Combat, cGod, network, input, asset, WW3D, WWPhys, WWSaveLoad teardown.

No sanitizer diagnostic occurred in the maintained run. The upstream source
tree remained pristine and generated staging has no `.orig` or `.rej` residue.

## UBSan audit

UBSan also exposed the original unaligned `StringClass` hash dword load, a
zero-count `memcpy` with a null old definition-array pointer, and M00
Encyclopedia SaveLoad forming `&bit_array[0]` for a zero-length serialized
chunk. Each was repaired at its owning original boundary: the hash now uses
byte-preserving `memcpy`, the definition-array copy is skipped at count zero,
and the Encyclopedia loader does not form an element-zero reference unless it
actually reads bytes. A targeted A3.1.4 two-cycle 120-frame run now passes
UBSan over the same visible interactive path with alignment, signed-wrap, and
shift diagnostics explicitly disabled because they are documented historical
desktop/x64 behavior outside the Vita ILP32 contract. Those exclusions remain
follow-up portability work and are not represented as a broad desktop-UBSan
claim.
