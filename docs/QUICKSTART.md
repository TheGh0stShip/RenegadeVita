# Quickstart

This path produces a local native Vita candidate without copying, packaging, or publishing retail game data.

## Prerequisites

- Linux or WSL2 Ubuntu with VitaSDK. Set `RENEGADE_VITASDK` when it is not at `/usr/local/vitasdk`.
- `git`, `cmake`, `ninja`, `python3`, `patch`, `zip`, `unzip`, `sha256sum`, and `ccache`.
- A legally owned retail Renegade installation for host validation and a Vita with the same user-owned data for physical testing.
- On Vita, the vitaGL shader compiler dependency `ur0:/data/libshacccg.suprx`.

## Clone

```bash
git clone --recurse-submodules https://github.com/TheGh0stShip/RenegadeVita.git
cd RenegadeVita
git submodule update --init --recursive
```

Do not edit `upstream/CnC_Renegade/`. Portability changes belong in `port/` or in deterministic zero-fuzz patches under `port/patches/`.

## Build

Run the canonical candidate build:

```bash
bash ./tools/build.sh
```

For an iteration build only:

```bash
RENEGADE_FAST_SCOPE=compile bash ./tools/build_fast_candidate.sh
RENEGADE_FAST_SCOPE=package bash ./tools/build_fast_candidate.sh
```

Fast output is not hardware-candidate evidence. Run the canonical builder before a physical handoff.

Useful variables:

```bash
export RENEGADE_VITASDK=/path/to/vitasdk
export RENEGADE_RETAIL_ROOT=/path/to/Renegade
export RENEGADE_CANDIDATE_LABEL=A3.5-devNN
export RENEGADE_BUILD_JOBS=8
```

The builder uses the managed builder root when available; otherwise it writes to local `build/`, `dist/`, and `logs/`. Those directories are intentionally ignored by Git.

## Verify the candidate

Before making any hardware claim, retain the matching VPK, SELF/ELF, map, symbols, SHA-256 manifest, compiler/host logs, and diagnostics bundle.

```bash
python3 tools/verify_repo_hygiene.py --root .
```

Check [Building](BUILDING.md) for the complete closure and [Current status](CURRENT_STATUS.md) for the active physical blockers.

## Install only with a bounded test plan

The VPK contains only the executable and package metadata. It expects user-owned retail data at:

```text
ux0:data/renegade/retail/Data/
```

Writable logs, caches, captures, and saves belong under:

```text
ux0:data/renegade/user/
```

Use [Installing on Vita](INSTALLING.md) for manual installation and evidence custody. A local build is never permission to overwrite a Vita installation.
