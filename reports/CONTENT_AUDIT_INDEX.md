# Content coverage audit index

Latest text/prompt work: [direct text and computed dialogue](MISSION_TEXT_AND_PROMPT_COVERAGE.md)
restores eleven English M13/M01 control hints in source and checks HUD/objective
IDs, original DDS lookup alternatives and cinematic script parameters. Absent
M13 dialogue candidates remain open. 93 Python/source checks pass; C++ and
physical behavior remain unverified.

Latest conversation work: [global startup and voice dependencies](MISSION_CONVERSATION_COVERAGE.md)
restores a missing original CONV10.CDB load in source and traces Tutorial,
M13 and M01 conversation records through both translation candidates. 74
Python/source checks pass. Global sound/name leads and runtime evidence remain
open; the C++ restoration is uncompiled.

Latest authored-data work: [mission bindings and ID leads](AUTHORED_MISSION_BINDINGS.md)
retains parameters, spawner IDs and cinematic script provenance for Tutorial,
M13 and M01. 55 Python/source checks pass; unresolved reference/route evidence
remains open. Detailed retail-derived parameter tables stay private.

Latest integration follow-up: [static linkage and mission ranks](STATIC_SCRIPT_LINK_AND_MISSION_RANKS.md)
records the original trim-symbol collision, strengthened target-selection
checks and rank-specific user storage. 41 static/diagnostic checks pass; the
C++ changes and prepared restart/sanitizer probes remain uncompiled/unrun.

Latest 2026-10-03 work: [campaign source map reconciliation](CAMPAIGN_SOURCE_MAP_RECONCILIATION.md)
adds a source-derived 13-mission inventory and closes seven omitted mission
translation units in native/host source selection. It records static evidence
and open retail/runtime checks. [Runtime gap diagnostics](RUNTIME_GAP_DIAGNOSTICS.md)
documents the PSTV VDB collector and candidate-scoped flight evidence.

The September 27, 2026 audit series covers Tutorial, Multiplayer Practice,
main menu, load/save, pause, multiplayer, options, Scorpion Hunters and M01.
Scorpion Hunters is retail M13; the engine's M01 is the following mission.

## Current findings

Read these in order:

1. [Follow-up sweep](DEEP_AUDIT_FOLLOWUP.md): particle startup defaults,
   mission-rank persistence, round transitions, radio input, projector render
   targets and nested asset references.
2. [Cross-system deep audit](CROSS_SYSTEM_DEEP_AUDIT.md): shared loader,
   script, frontend, save and multiplayer omissions across 17 maps.
3. [Reproduction instructions](../tools/DEEP_AUDIT.md): static audit tools,
   validation and the deliberately failing broader coverage guard.

Earlier evidence, retained as historical snapshots:

- [Video-driven M13 coverage correction](M13_VIDEO_COVERAGE_AUDIT.md)
- [Additional M13 source owners](M13_ADDITIONAL_SOURCE_OWNERS.md)
- [Aggressive M13 discovery](M13_AGGRESSIVE_DISCOVERY.md)
- [Tutorial discovery](M00_AGGRESSIVE_DISCOVERY.md)

Later reports supersede earlier scope/counts. The follow-up records 81 passing
Python checks. The broader standalone coverage guard remains INCOMPLETE with
73 grouped findings; additional semantic findings are documented separately.

## Source and runtime status

The October 3 campaign sweep now selects all 44 original Scripts.dsp code
units, including every campaign mission, with a static provider replacing the
DLL entrypoint. The integration follow-up isolates the two original trim
symbols and adds mission-rank storage beneath RegistryClass. Earlier source
work selected five additional required script units
(Mission03.cpp, Mission11.cpp, Test_DAK.cpp, Test_RMV_Toolkit.cpp and
Toolkit_Sounds.cpp), plus the sphere, ring and sound-render-object owners. The
native runtime now registers the four original prototype loaders and applies
the original particle lifetime and 17 LOD defaults. Static closure checks find
no remaining unselected script or persistence-factory owners for the 17 maps.
The source changes have not been compiled or executed. The historical Dev207
symbol inventory is not evidence for the current source graph. M01 still has
an attached but unavailable `X01_ConYardDrop.txt` sequence; frontend/options,
save/load and multiplayer gaps remain in the audit reports. The original
Options template and its supported Tech Options route are now source-selected;
unsupported Controls, Movies, Credits and Multiplayer Options entries are
hidden pending their original owners and routes.

No C++ build, game launch, installation, retail/save modification or new
native acceptance occurred during this source-only continuation. The latest
93 focused Python/source tests pass. Local asset-derived receipts remain under
build/; published material contains source, tests and findings rather than
retail assets or saves.

## Repository status

Publication review: [PR #3](https://github.com/TheGh0stShip/RenegadeVita/pull/3).
The user requested the work on both main and
audit/deep-content-coverage-20260927. Publication does not promote untested
source to a validated hardware candidate.

The main branch protection was configured and read back on September 27:
force pushes and deletion are blocked, including for administrators. Normal
pushes/merges remain permitted; required reviews and status checks are not
configured. These are repository settings, not source-controlled enforcement.
