# Renegade Vita

Renegade Vita is a native PlayStation Vita port of *Command & Conquer:
Renegade*, built from EA's officially released source and Vita-specific
boundary implementations. It preserves the original engine and retail-data
loading architecture; it is not an asset conversion project or replacement
game engine.

## Repository layout

- `upstream/CnC_Renegade` is the pinned EA source submodule.
- `port/` contains Vita platform, renderer, filesystem, compatibility, and
  deterministic patch material.
- `staging/` is generated from the upstream submodule by
  `tools/stage_sources.sh`; do not edit it as the source of record.
- `tools/` contains the canonical Bash build, host validation, staging, and
  crash-symbolication tooling.
- `reports/` contains the durable status, decision, performance, hardware,
  and crash-evidence records.

## Current engineering state

The accepted physical baselines are documented in
[`reports/milestones/`](reports/milestones/). A3.5 remains an internal
developer stream, not a public release: the physical A3.5-dev3 dump is
symbolicated at `PersistentGameObjObserverManager::Load` while entering
`ChunkLoadClass::Open_Chunk`. The current tree adds bounded diagnostics and a
host contract; it does **not** establish the physical root cause or supersede
the hardware gate. See [`reports/LIVE_PROGRESS.md`](reports/LIVE_PROGRESS.md)
and [`reports/generated/A35_OBSERVER_LOADER_IMPLEMENTATION.md`](reports/generated/A35_OBSERVER_LOADER_IMPLEMENTATION.md).

## Clone and prepare

```bash
git clone --recurse-submodules <your-fork-url> RenegadeVita
cd RenegadeVita
git submodule update --init --recursive
```

The expected upstream pin is recorded in `.gitmodules` and must remain clean.
The build requires a local, user-owned retail PC installation for host
validation. Retail game files, saves, credentials, screenshots, Vita dumps,
and generated packages are intentionally excluded from Git.

By default, build scripts use a writable managed directory only when it exists
for the current WSL user; otherwise they keep output under the checkout. To
choose an explicit external output location, set `RENEGADE_BUILDER_ROOT`:

```bash
export RENEGADE_BUILDER_ROOT="$HOME/RenegadeVitaBuilder"
```

## Build and test

WSL with VitaSDK is the supported workflow. The canonical entry point is:

```bash
bash ./tools/build.sh
```

For an internal candidate label, use only a `A<major>.<minor>-dev<build>`
label, for example:

```bash
RENEGADE_CANDIDATE_LABEL=A3.5-dev4 bash ./tools/build.sh
```

This creates artifacts under the managed `dist/` directory and never deploys
to a Vita automatically. Install a candidate manually only when its associated
hardware-test instructions and evidence archive have been produced.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for patch/staging/test rules and
[`VERSIONING.md`](VERSIONING.md) for milestone and evidence semantics.

Repository hygiene check:

```bash
python3 tools/verify_repo_hygiene.py
```

The check is deterministic and tracks only Git-indexed files. It fails on tracked
artifacts, secrets, machine-absolute paths, machine-specific symlinks, and
tracked build/log/retail directories.

## License and retail-data notice

EA's released Renegade source is GPLv3 with additional terms. The complete
upstream notice is in
[`upstream/CnC_Renegade/LICENSE.md`](upstream/CnC_Renegade/LICENSE.md) after
submodule initialization. This port's modifications are intended to be
distributed under the same applicable terms. You must own the retail game to
use its data; no retail data is included in this repository or its releases.
