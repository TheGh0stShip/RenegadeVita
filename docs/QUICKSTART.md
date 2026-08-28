# Quickstart

This guide gets a fresh checkout to a buildable VPK without changing the
architecture or copying retail data into Git.

## Requirements

- Windows with WSL2 Ubuntu, or Linux with VitaSDK installed.
- VitaSDK at `/usr/local/vitasdk`, or set `RENEGADE_VITASDK`.
- Host tools: `git`, `cmake`, `ninja`, `python3`, `patch`, `zip`, `unzip`,
  `sha256sum`, `ccache`.
- A PlayStation Vita capable of installing homebrew VPKs.
- `ur0:/data/libshacccg.suprx` installed on the Vita for vitaGL shader
  compilation.
- A legally owned retail Renegade installation. Retail data is not included.

## Clone

```bash
git clone --recurse-submodules <repo-url> RenegadeVita
cd RenegadeVita
git submodule update --init --recursive
```

If the submodule is missing, the build will fail early. The upstream revision
is pinned by `.gitmodules` and the canonical build script.

## Optional Output Root

By default, scripts use the managed builder root when it exists and is
writable. Otherwise they write `build/`, `dist/`, and `logs/` under the
checkout.

To force a location:

```bash
export RENEGADE_BUILDER_ROOT="$HOME/RenegadeVitaBuilder"
```

## Build

```bash
bash ./tools/build.sh
```

Useful knobs:

```bash
RENEGADE_BUILD_JOBS=8 bash ./tools/build.sh
RENEGADE_CANDIDATE_LABEL=A3.5-dev79 bash ./tools/build.sh
RENEGADE_FAST_SCOPE=compile bash ./tools/build_fast_candidate.sh
```

The canonical build performs host validation, deterministic staging, source
integration reporting, Vita ARM build/link, VPK packaging, identity checks,
retail-exclusion checks, and diagnostics packaging.

## Install

Install the newest `dist/RenegadeVita-A*.vpk` with VitaShell. The VPK contains
only executable/package metadata and expects retail data already on the Vita:

```text
ux0:data/renegade/retail/Data/
```

For FTP upload to a VitaShell-accessible folder:

```bash
bash ./tools/upload_vpk_ftp.sh <vita-ip> dist/RenegadeVita-A3.5-dev79.vpk
```

Then install the VPK from VitaShell on the device.

## Runtime Logs

Runtime logs are written on the Vita under:

```text
ux0:data/renegade/user/logs/
```

For the current candidate:

```text
ux0:data/renegade/user/logs/a35-dev79-runtime.log
```

Return that log, screenshots, captures, and any `psp2core-*.psp2dmp` after a
physical test.
