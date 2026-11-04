# Retail gameplay and content parity contract

User requirement clarified 2026-11-04: earlier builds omitted substantial real
gameplay that was discovered only when the user compared them with retail.
Prevent recurrence by auditing what the game contains, independently of what
the port currently happens to compile. The user is not the missing-content QA
or discovery mechanism. This contract applies to the full game.

## Independent denominator

Establish a versioned retail baseline using read-only user-owned data and
retained retail gameplay/reference evidence. Record retail executable/data
identity and differences between that baseline, the released source, and any
comparison project. Do not assume they implement identical behavior.

Build the catalogue from all retail mission/progression records, level and
preset bindings, cinematic control files, conversations/objectives, resources,
original engine entry points and complete reference sequences. Start from these
inputs, not from selected CMake files or the functions already implemented.
Source counts, a map load, an intro replay, a build, factory presence or object
counts are supporting evidence; none establishes the content denominator.

The catalogue must cover:

- Tutorial and every campaign mission: all areas, mandatory and optional
  objectives, encounters/waves, triggers, branches, scripted destruction,
  cinematics, camera/control handbacks, reinforcements, rescue/escort/repair,
  vehicle and weapon handoffs, bosses, mission failure and completion.
- Shared gameplay: movement/actions, weapons/ammunition/reloads, targeting,
  damage/armor/death, AI/actions/pathing, interactions, elevators/doors,
  vehicles, pickups, stealth, environmental effects and difficulty behavior.
- Player presentation: original frontend/options, HUD/EVA/datalinks, mission
  text/prompts, conversations/voices, music/effects, movies/subtitles,
  animation/material effects, score/ranks/credits and unlockable presentation.
- Persistent and cross-mode behavior: checkpoints/save/load/retry, restored
  script state and objectives, campaign transitions, repeated sessions, Practice
  and original supported network gameplay/provider-dependent surfaces.

This list is an audit structure, not a declaration of exhaustive enumeration.
Each category still needs a concrete baseline-derived feature/sequence list.

## Required trace for each feature or sequence

Record a stable ID, retail mission/area/trigger and expected visible/audible
behavior, with baseline evidence. Trace the authored records and dependencies
to original script factories, command callbacks and engine owners, then to the
actual native selection, linked registrations and reachable implementation.
Include assets, event/timer chains, object-ID handoffs, prerequisite state,
completion callbacks and save/reload consequences. Follow indirect and dynamic
attachments, cross-mission helpers and failure/alternate branches.

Review the behavior behind each boundary. A symbol that returns success,
ignores parameters, silently drops events, skips a missing resource, substitutes
an unrelated result or is never reached cannot close the feature. Audit every
stub, weak fallback, disabled branch and unsupported asset/effect/provider in
terms of the gameplay it removes, not only whether the executable survives.

Mark source/selection/link/semantic evidence separately from runtime evidence.
During the play-test hold, runtime acceptance remains explicitly unverified.
Never replace natural progression with forced wins/debug jumps when claiming
coverage of a sequence. Later regression checks must cover the feature itself,
not an unrelated intro or generic frame-count checkpoint.

## Discrepancies and admission

Every missing, unclassified or unverifiable content path is OPEN. Absence from
the released source does not prove absence from retail. A null-safe call or
graceful failure does not prove that missing behavior is optional. Claims such
as "retail PC also lacks this" need matching retail behavior/binary evidence,
not inference from the same incomplete source being ported.

Record affected gameplay, root owner, required correction and evidence for each
discrepancy. An exclusion needs an explicit content-impact rationale; "unused",
"obsolete" or "desktop-only" cannot hide a player-facing capability. Preserve
original owners and data semantics when fixing it.

Development compilation and focused non-play checks may proceed. Do not label
a build content-complete or present it for play testing while the catalogue is
incomplete or required content has unknown/missing/stubbed coverage. The current
user hold remains active until remaining implementation and the full content
inventory close. That source milestone still does not establish physical parity.

Source/flag/provider/resource changes must invalidate affected coverage and
re-run its admission checks. Both canonical and fast workflows must eventually
consume the same feature/sequence requirements; a narrow M13-only gate cannot
certify the whole game. A written catalogue without those enforced checks is
insufficient closure. The shared machine-readable catalogue and all-mission
checks remain to be implemented; this contract is not their completion receipt.

## Initial re-audit priorities

Historical evidence: CAMPAIGN_SOURCE_MAP_RECONCILIATION.md records omitted
mission units; M13_VIDEO_COVERAGE_AUDIT.md records absent Area 2 battle,
engineer/tank handoff and cross-mission helper dependencies. Use these as
regression incident classes across every mission, not isolated one-off fixes.
Revalidate the existing campaign readiness reports against this contract,
especially assertions of retail-equivalent missing references or behavior.
The 1,490-file inventory supports this audit; it is not the content catalogue.
