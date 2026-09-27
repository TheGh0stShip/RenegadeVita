# Building

`tools/build.sh` is the canonical build path. Use it for every candidate that may be handed to physical hardware.
The current published candidate is
[A3.5-dev202](https://github.com/TheGh0stShip/RenegadeVita/releases/tag/A3.5-dev202).
The commands below intentionally use a fresh placeholder label rather than
reusing that release identity.

## Canonical build

```bash
RENEGADE_CANDIDATE_LABEL=A3.5-devNN RENEGADE_M00_DEMO=0 bash ./tools/build.sh
```

The canonical path checks host prerequisites, the pinned clean upstream source, retained host contracts, deterministic zero-fuzz staging, ARM ELF/SELF/VPK identity, VPK contents, SHA-256 manifests, diagnostics, and retail exclusion.

It produces a candidate-scoped VPK plus matching ELF, map, symbols, build report, compiler/host logs, source integration report, identity report, diagnostics bundle, and SHA-256 manifest. These generated artifacts remain outside Git.

The BINK dependency build is reproducible and limited to the FFmpeg pieces needed for Bink demux/video/audio decode, scaling, and resampling. It neither downloads RAD code nor packages a retail movie.

## Fast iteration

```bash
RENEGADE_CANDIDATE_LABEL=A3.5-devNN RENEGADE_M00_DEMO=0 \
RENEGADE_INCREMENTAL_STAGE=1 bash ./tools/build_fast_candidate.sh
```

Fast builds reduce iteration work but are not canonical evidence. Before a physical handoff, run the canonical build for the exact candidate.

Always set the candidate label explicitly; the legacy script default is not
the public current candidate. Replace `devNN` with a new unused number for
changed runtime code rather than replacing a published tag.
Do not restage sources while a compiler is running. Incremental staging
preserves unchanged file timestamps while applying the same zero-fuzz patches.

TTFS HTTPS uses project-local pinned curl/Mbed TLS libraries built by
`tools/build_ttfs_https_vita.sh`; it does not overwrite global SDK libraries.
Set `VITASDK` to the same root as `RENEGADE_VITASDK` for dependency scripts.
The fast path needs those dependencies prepared first on a fresh checkout.

## Configuration

| Variable | Purpose |
| --- | --- |
| `RENEGADE_VITASDK` | VitaSDK root; defaults to `/usr/local/vitasdk`. |
| `RENEGADE_BUILDER_ROOT` | Managed output root when writable. |
| `RENEGADE_DIST_ROOT` | Explicit artifact lookup/output override. |
| `RENEGADE_BUILD_JOBS` | Parallel build jobs. |
| `RENEGADE_CANDIDATE_LABEL` | Internal candidate identity such as `A3.5-devNN`. |
| `RENEGADE_RETAIL_ROOT` | Host retail root used only for validation. |
| `RENEGADE_SOURCE_CACHE` | Optional cache for pinned source dependencies. |

The PowerShell wrapper only invokes the same Bash builder through WSL. Prefer the Bash command for reproducible diagnostics.

## Before handoff

```bash
python3 tools/verify_repo_hygiene.py --root .
python3 tools/verify_public_docs.py --root .
python3 -m unittest tools.test_verify_public_docs tools.test_verify_repo_hygiene
```

Retain matching artifacts and read [Current status](CURRENT_STATUS.md). A successful build is not proof of physical gameplay.
