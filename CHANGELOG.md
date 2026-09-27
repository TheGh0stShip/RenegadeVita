# Changelog

This changelog records public-facing source, process, and evidence changes. It does not turn a build into a physical acceptance claim.

## A3.5-dev202 - 2026-09-27

- Routed original loading-backdrop selection by full-port mode: Practice uses
  96, remote C&C multiplayer uses 94, and campaign keeps its mission backdrop.
- Linked the original MultiHUD owner for the full port. The separate tutorial
  demo profile remains unchanged.
- Passed 177 focused tests, fast ARM package identity and Vita3K install/readback.
  A later bounded run selected original Practice, showed loading backdrop 96,
  rendered `Skirmish00.mix` and accepted brief movement. A silent 35-second
  Vita3K clip and build-labelled screenshots are published; full Practice
  gameplay, natural exit and physical Vita acceptance are not claimed.
- Published the matching
  [Dev202 prerelease](https://github.com/TheGh0stShip/RenegadeVita/releases/tag/A3.5-dev202)
  and updated source, setup and status documentation. The VPK SHA-256 is
  `d0b0eb1b803ec07d8ee17e1f361a5a10684ecee8b66a86126abdf229c7025f28`.

## Dev200-Dev201 multiplayer evidence - 2026-09-27

- Dev200 joined RenCorner Glacier in Vita3K, rendered the original purchase
  dialog and received a successful server purchase response. The public list
  still displayed `PSVita`; complete multiplayer behavior is not accepted.
- Dev201 corrected ARM UTF-16 player/chat varargs calls and added a scoped
  fallback to unchanged user-owned retail `M02.mix` for a Glacier ice texture.
  It joined Skatepark after map rotation, so Glacier terrain and player-name
  appearance remain unverified. These changes are carried into Dev202.

## A3.5-dev195 - 2026-09-26

- Published the native ARM RenCorner join checkpoint: TT admission, validated
  HTTPS package downloads, original archive mounting and network replication.
- Vita3K evidence covers City_U1 rendering, bounded movement, and clean session
  teardown. The public list showed `PSVita`, not the requested spaced name.
- Integrated six missing original Combat factory owners and verified state
  machine callbacks/save-load and loaded replication with sanitizers.
- Kept the demo/full-port split. Campaign fixes remain under validation;
  multiplayer purchase UI, text, complete gameplay, and physical acceptance
  are still open. See the [Dev195 report](reports/DEV195_RENCORNER_NATIVE_JOIN.md).
- Refreshed public setup/status/build documentation and CI publication checks.
  Private handoff notes, credentials, retail/server assets, and raw logs stay local.

## Historical documentation and Dev85-Dev88 work

### Documentation and repository

- Rebuilt the public README and documentation navigation around the accepted A3.1.4 baseline, Dev87 physical frontend failure, and Dev88 local-only candidate.
- Added an explicit evidence/capture policy, security policy, contributor conduct policy, GitHub issue forms, and repository-hygiene documentation checks.
- Clarified that the historical gallery contains reviewed evidence rather than a synchronized same-camera benchmark. Six Dev87 recorder-derived stills were subsequently recovered; Dev88 has no physical capture.
- Clarified the difference between VitaCompanion panel power control, the optional MP4 recorder, and the not-yet-installed VDB framebuffer provider.

### A3.5-dev85 through dev88

- Dev85 restored the original frontend path after a Vita-only console-exclusivity suppression; its physical return still failed with very slow/buzzy intro A/V and missing menu items.
- Dev86 restored original menu-transition placement and added bounded startup/BINK diagnostics; its physical return still failed the same frontend usability gate.
- Dev87 restored the Vita allocation path for original procedural glyph textures and reduced BINK upload bandwidth through unchanged retail movie data; its physical return still had missing menu/dialogue text and slow/buzzy intro A/V.
- Dev88 applies original texture-stage state to dynamic menu/dialogue glyph draws and reserves three real BINK audio buffers before output. Canonical source/ARM/package validation passed; no Dev88 physical test has occurred.

## Accepted physical baselines

- **A2.0** — native bootstrap; see [milestone record](reports/milestones/A2.0-HARDWARE-VALIDATION.md).
- **A2.1** — original filesystem/MIX path; see [milestone record](reports/milestones/A2.1-HARDWARE-VALIDATION.md).
- **A2.2** — original visual pipeline; see [milestone record](reports/milestones/A2.2-HARDWARE-VISUAL-VALIDATION.md).
- **A3.0** — original M00 world runtime; see [milestone record](reports/milestones/A3.0-HARDWARE-M00-WORLD-VALIDATION.md).
- **A3.1.3** — interactive lifecycle evidence; see [milestone record](reports/milestones/A3.1.3-HARDWARE-INTERACTIVE-LIFECYCLE-VALIDATION.md).
- **A3.1.4** — current accepted physical interactive baseline; see [program charter](reports/PROGRAM_CHARTER.md).
