# Dev175 M13 Duncan Beacon

Historical candidate: A3.5-dev175, 2026-09-23, full-port profile.
This public milestone summary preserves the evidence from the local work notes.

The first retail campaign mission uses M13 data and `Mission01.cpp` scripts.
Dev175 retained Duncan's original conversation and animation-complete beacon
grant, adding a bounded fallback when the presentation callback is missed.
The `gaveIonBeacon` guard prevents duplicate grants. The fallback does not
complete objectives or advance the mission.

Development checkpoint, conversation diagnostics, and cinematic preparation
contracts passed. Canonical build closure passed with 198 zero-fuzz patches;
registry SHA-256: `2f6db3a5593a373a7f1992ed8d68f4116dbbd43a3a826a99972d49d107619c24`.

| Artifact | SHA-256 |
| --- | --- |
| RenegadeVita-A3.5-dev175.vpk | `11b26fdd8bb80cd40de7c0701b2a1303912951b84f72011dd880fb7289dae205` |
| ELF | `e160bd63e12cca60713fbd9656ac203e2ac22f54ae89eabe5f1b69b928e2fc29` |
| A3.5-dev175-BUILD-DIAGNOSTICS-20260923-081947.zip | `142c8e11b94c83cc70b8c06d34108168e74a245b8c86a64507c2ac2b676cc09b` |

The local build log is
`<managed-log-root>/a35-dev175-20260923-081947-build.log`; artifacts are under
`<managed-dist>/`. No runtime acceptance or physical deployment was claimed at
this checkpoint. Normal conversation, beacon grant and gameplay progression
still required candidate-matched testing.
