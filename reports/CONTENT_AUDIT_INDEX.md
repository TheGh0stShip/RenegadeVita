# Content coverage audit index

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

Five previously omitted script units are source-selected with scoped bridges:
Test_RAD.cpp, Test_DAY.cpp, Toolkit.cpp, Toolkit_Objects.cpp and mission08.cpp.
These changes remain uncompiled and unexecuted. Five further required script
owners and three W3D owners remain unintegrated. The reports distinguish source
selection, historical executable evidence and runtime acceptance.

No build, game launch, installation, retail/save modification or new native
acceptance occurred during these sweeps. Local asset-derived receipts remain
under build/; published material contains source, tests and findings rather
than retail assets or saves.

## Repository status

Publication review: [PR #3](https://github.com/TheGh0stShip/RenegadeVita/pull/3).
The user requested the work on both main and
audit/deep-content-coverage-20260927. Publication does not promote untested
source to a validated hardware candidate.

The main branch protection was configured and read back on September 27:
force pushes and deletion are blocked, including for administrators. Normal
pushes/merges remain permitted; required reviews and status checks are not
configured. These are repository settings, not source-controlled enforcement.
