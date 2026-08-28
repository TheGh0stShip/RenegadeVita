# Changelog

All notable port changes are recorded here from the local Git bootstrap on
2026-08-16 onward. Earlier engineering and physical-baseline history is
preserved in [`reports/milestones/`](reports/milestones/) and the living
records in [`reports/`](reports/); it has not been retroactively fabricated as
Git commits.

## Unreleased

### Added

- Human-facing documentation for quickstart, building, installing, architecture,
  development workflow, controls, troubleshooting, and current A3.5-dev79
  status.
- GitHub issue and pull-request templates for physical test reports, build
  bugs, evidence, and validation.
- `tools/upload_vpk_ftp.sh`, a manual VitaShell FTP upload helper for VPKs.
- Local Git history with the EA source registered as a pinned submodule at
  `3e00c3a1b97381bb28be89a35b856375e0629a08`.
- Deterministic A3.5 observer-loader breadcrumbs and the focused host contract
  recorded in the initial repository history.
- Root contributor, versioning, publication, and license-notice documentation.

### Fixed

- Helper scripts no longer hardcode a specific Windows profile path for `dist/`;
  they honor `RENEGADE_BUILDER_ROOT` or `RENEGADE_DIST_ROOT`.
- `.gitignore` now excludes generated `dist/` artifacts, local automation
  state, VPK/ELF/SELF packages, ZIP diagnostics, and Vita crash dumps.
- `PersistentGameObjObserverManager::Load` now handles failure to open its
  required observer root and a wrong root chunk ID without dereferencing
  unavailable root metadata. It preserves chunk balance when a wrong root was
  opened and reports bounded diagnostics.

### Verification

- Repository hygiene, shell syntax, and JSON syntax are expected to pass after
  the documentation overhaul.
- The observer diagnostic patch applies from pristine upstream with
  `--fuzz=0` and its staged result matches.
- The focused loader contract passes 27 checks; the patched Combat translation
  unit compiles in the A3.1 gameplay-seed host target.
- This is not a physical-crash root-cause finding or a hardware release.

## Accepted physical baselines

- **A2.0** — native bootstrap; see
  [`reports/milestones/A2.0-HARDWARE-VALIDATION.md`](reports/milestones/A2.0-HARDWARE-VALIDATION.md).
- **A2.1** — original filesystem/MIX path; see
  [`reports/milestones/A2.1-HARDWARE-VALIDATION.md`](reports/milestones/A2.1-HARDWARE-VALIDATION.md).
- **A2.2** — original visual pipeline; see
  [`reports/milestones/A2.2-HARDWARE-VISUAL-VALIDATION.md`](reports/milestones/A2.2-HARDWARE-VISUAL-VALIDATION.md).
- **A3.0** — original M00 world runtime; see
  [`reports/milestones/A3.0-HARDWARE-M00-WORLD-VALIDATION.md`](reports/milestones/A3.0-HARDWARE-M00-WORLD-VALIDATION.md).
- **A3.1.3** — interactive lifecycle evidence; see
  [`reports/milestones/A3.1.3-HARDWARE-INTERACTIVE-LIFECYCLE-VALIDATION.md`](reports/milestones/A3.1.3-HARDWARE-INTERACTIVE-LIFECYCLE-VALIDATION.md).
