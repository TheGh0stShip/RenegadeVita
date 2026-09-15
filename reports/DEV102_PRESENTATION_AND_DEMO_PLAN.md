# Dev102 presentation and M00 demo plan

## Scope and estimate

Continue toward the complete native Renegade port. The selectable M00-only
demo is an interim community showcase, not a permanent engine restriction.
The earlier 1-3-day estimate was not supported by measured remaining work and
is withdrawn following user correction. Target a usable M00 alpha this working
session, not 48 hours. Prioritize reported presentation blockers and authentic
tutorial completion; defer optional optimization and release polish. Publish
the next concrete result within 30 minutes, without promising unobserved full
completion. PS Vita/PSTV release acceptance remains separate and held.

## Returned evidence

Dev101 fast and canonical build commands completed successfully. The observed
emulator run used the separate fast SELF
`ab45fb918cd9e209e63e76b1d618ac8864398886cf41580ec986bb4fde2dada5`,
not an assumed canonical-identical binary. Evidence root:
`D:\Vita3K\RenegadeEvidence\Dev101-fast-20260908T202935Z`.
Runtime log SHA-256:
`e021641d5aecde033d31df26c21d1fe77cc9ebb4a01b09cb69ab77fd2b3043bd`.

User reports first movie black, second blue instead of orange, and empty
main-menu selection boxes. All 15 font probes pass; menu strings are nonempty.
No text-atlas upload diagnostics appear. The original lite DX8 initialization
leaves the desktop initialized flag false, so Render2DSentence returns before
building its textures. Ordinary Render2D boxes do not use that guard.

EA_WW decoded 230 frames but uploaded only one, dropping 229 after cold first
draw work made the early-armed clock late. R_Intro uploaded 472 of 475 frames.
The color defect remains user-observed; packed RGB565 upload is the current
boundary hypothesis. Both movies and shared MIX resources are present. Loose
root misses before MIX fallback do not prove the entire retail dataset absent.
The previous automated screenshot selected the launcher, not the game; it is
not visual acceptance evidence.

## Current changes and build state

Native DX8 readiness follows the initialized Vita renderer, preserving desktop
semantics and the original sentence owner. Movie clock starts after first
glEnd; audio waits for that epoch. Explicit RGBA8888 removes packed RGB565
channel ambiguity, doubling movie upload bytes at the unchanged 320x240 cap.
This is a correctness tradeoff, not a performance claim. Zero-video EOF fails
cleanly. Capture helper now selects only the run-owned foreground game window.

Initial Dev102 fast attempt reused staging and failed with no declaration for
Is_Native_Device_Ready. The focused test independently failed on the missing
staged accessor. Retry uses RENEGADE_FAST_RESTAGE=1, with readiness and demo
policy executable checks integrated into both build paths. Preserve failed logs
under `build/dev102-host-evidence/`; no new runtime correctness is claimed.

## Execution plan

1. Restage and close Dev102 fast package; canonical follows in background.
2. Retain exact fast ELF/SELF/VPK/map/symbols/identity and dependency provenance.
3. Title-scoped Vita3K install with backup and bounded intro/menu capture.
4. Establish readable menu, tutorial entry, loading text and progress.
5. Run authentic M00 objectives, dialogue, combat, interaction and HMVV route.
6. Reach original success without bypassing scripts; observe slow fade, exact
   thank-you, project/dependency credits, and clean teardown without M01.
7. Repeat route for frame-time/memory evidence; adopt only demonstrated
   bottleneck fixes. 60 FPS+ remains unproven, not replaced by a lower target.
8. Present major local progress before requesting physical acceptance cycles
   on both PS Vita and PSTV. Neither emulator nor build closure substitutes.

Canonical compilation is not waiting work: use its time for matching emulator
setup, retained evidence, and independent route planning. Do not package retail
data/fonts or access hardware during the hold.
