# Dev195 Public Publication

Updated: 2026-09-26. This records publication, not additional gameplay testing.

## Source And Package

- Source/tag commit: `e7f48758ddaa5d535c4fb6ddc3dacaf7b086a52a`.
- [Source CI](https://github.com/TheGh0stShip/RenegadeVita/actions/runs/36273078667): passed.
- [Development prerelease](https://github.com/TheGh0stShip/RenegadeVita/releases/tag/A3.5-dev195): published, explicitly experimental.
- Release assets: `RenegadeVita-A3.5-dev195.vpk` and `SHA256SUMS.txt` only.
- Downloaded the uploaded assets back from GitHub and checked SHA-256:
  `04f4615dc9d9f891c2f36d8782f41b66580de35b6c90346a0cea0e5d417eaf61`.
- VPK inventory: `eboot.bin` and `sce_sys/param.sfo`; no retail/server assets,
  saves, credentials, private logs or handoff notes.

The runtime binary is unchanged from the installed, tested Dev195 checkpoint.
[Runtime evidence](DEV195_RENCORNER_NATIVE_JOIN.md) remains the authority for
what was actually observed. This publication does not establish canonical or
physical acceptance, full campaign completion, or complete multiplayer.

## Public Surfaces

README, current status, installation, multiplayer setup, building, quickstart,
architecture, controls, troubleshooting, changelog, roadmap and repository
description now reflect Dev195. Historical evidence is retained and labelled.
The separate tutorial-demo repository was not changed.

[PR #2](https://github.com/TheGh0stShip/RenegadeVita/pull/2) was closed as
superseded after retaining its useful installation and evidence corrections.
[Issue #1](https://github.com/TheGh0stShip/RenegadeVita/issues/1) received a
candidate-specific reply and remains open for unresolved PSTV progression and
save/load reports; the multiplayer result is not represented as their fix.

The [public video page](https://thegh0stship.github.io/RenegadeVita/) now links
the current build and distinguishes its historical Dev87 recording from Dev195.
Its previously mismatched video filename is repaired. Original recording bytes
and SHA-256 are unchanged. Page and video endpoints returned successfully.

- Video-page commit: `334b4f701defebb0adc49c04ad00d6d7db837ca4`.
- [Page/immutable-media validation](https://github.com/TheGh0stShip/RenegadeVita/actions/runs/36273171585): passed.
- [Pages build and deployment](https://github.com/TheGh0stShip/RenegadeVita/actions/runs/36273172553): passed.

## Publication Checks

The exact staged tree and resulting source commit were checked independently
with `tools/verify_publication_snapshot.py`, not just the working directory.
It materializes a clean Git archive and runs the same documentation, hygiene
and regression checks as GitHub Actions. All 19 public documents passed link
and status checks; 13 publication-guard tests passed. Twelve focused build-stamp,
loading-screen and target-ABI tests also passed; the 266-patch registry matched.

Current-candidate metadata replaces obsolete literal Dev93 requirements.
Regression checks reject stale status, missing reports, broken local links,
private identity files and tracked handoff notes. Machine-specific report paths
use portable evidence-root placeholders. Local handoff files remain on disk;
their removal from current Git does not rewrite historical commits.
