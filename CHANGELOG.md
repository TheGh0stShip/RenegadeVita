# Changelog

This changelog records public-facing source, process, and evidence changes. It does not turn a build into a physical acceptance claim.

## Unreleased

### Documentation and repository

- Rebuilt the public README and documentation navigation around the accepted A3.1.4 baseline, Dev87 physical frontend failure, and Dev88 local-only candidate.
- Added an explicit evidence/capture policy, security policy, contributor conduct policy, GitHub issue forms, and repository-hygiene documentation checks.
- Clarified that the historical gallery contains reviewed evidence rather than a synchronized same-camera benchmark; Dev87 has no recovered image and Dev88 has no physical capture.
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
