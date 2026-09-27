# Installing on Vita

This guide covers the full-port development candidate, currently
[Dev202](https://github.com/TheGh0stShip/RenegadeVita/releases/tag/A3.5-dev202).
It is experimental, not a completed campaign or multiplayer release. The
separate [tutorial demo guide](https://github.com/TheGh0stShip/Renegade-Vita-Demo)
remains specific to that demo.
Dev202 passed a fast ARM build and Vita3K installation; a bounded emulator run
also captured Practice loading and spawn. It is not a canonical build or
physical gameplay acceptance. Dev197 has the latest
bounded PSTV save-load/menu-return evidence.

The VPK deliberately contains only the executable and package metadata. It never includes retail data, saves, configuration, logs, screenshots, videos, or crash dumps.

## Filesystem boundary

Copy your own complete, patched retail `Data/` directory unchanged to:

```text
ux0:data/renegade/retail/Data/
```

Also retain the loose retail fonts at the retail root:

```text
ux0:data/renegade/retail/54251___.TTF
ux0:data/renegade/retail/ARI_____.TTF
```

Required loose configuration files belong in `Data/`, alongside `always.dat`,
`always.dbs`, `Always2.dat`, and all original mission archives:

```text
ux0:data/renegade/retail/Data/stylemgr.ini
ux0:data/renegade/retail/Data/WWAudio.ini
```

The Dev134 startup probes open both `.ini` files before the menu. The original
eight-file public setup list omitted them, and its `always.dat` SHA-256 omitted
the final `a`. The verified Steam digest is
`f1fa13ed10d0b09fea999660cff71dc784a01a22cdc3e4f0041720ca67dfa29a`.
That hash is for the verified Steam file, not a claim that every retail edition
is identical. An unpatched CD installation without `Always2.dat` cannot satisfy
this build. A CD tester in [issue #1](https://github.com/TheGh0stShip/RenegadeVita/issues/1)
obtained the file with the Renegade 1.037 English patch and copied BIK files from
disc 2 to `Movies`. Those are user-reported setup steps, not campaign acceptance.

Preserve the installation's movies at `ux0:data/renegade/retail/Data/Movies/`.
The original PC demo and the Vita tutorial-demo subset are not full-port data.
Do not rename missions, edit retail archives, or supply third-party game downloads.

Saves, settings, and logs belong below:

```text
ux0:data/renegade/user/
```

Do not copy generated caches, logs, saves, or modified data into `retail/`.
Experimental multiplayer also downloads server-provided assets into the separate
`ux0:data/renegade/cache/ttfs/` directory. See [Multiplayer](MULTIPLAYER.md) for
private identity, trust-bundle, and one-shot launch setup.

## Before installation

1. Download the development VPK and verify its published SHA-256, or build a new candidate with an unused `RENEGADE_CANDIDATE_LABEL`. Canonical `bash ./tools/build.sh` closure is required before physical acceptance; Dev202 has fast-build/package and bounded Vita3K Practice evidence only. Dev197 passed a canonical build and a bounded PSTV checkpoint test, not full physical acceptance.
2. Retain its VPK, packaged SELF, map, symbols, SHA-256 manifest, and build log together.
3. Verify the VPK contains no retail data.
4. Review [Current status](CURRENT_STATUS.md) and use a bounded physical test plan.
5. Keep a hash-verified backup of the currently installed title executable before replacing it.

A local build or upload receipt is not visual or gameplay acceptance.

## Manual VitaShell installation

1. Copy the selected `RenegadeVita-<candidate>.vpk` to a VitaShell-visible location, for example `ux0:data/renegade/user/`.
2. Install it in VitaShell.
3. Confirm `ur0:/data/libshacccg.suprx` is available before launch.
4. Verify the installed executable hash against the candidate's packaged SELF.
5. Launch only under the approved test plan. Preserve the matching runtime log and any returned diagnostics after the run.

## Optional FTP upload

The helper uploads only the VPK you name; it does not install, launch, alter retail data, or collect personal media.

```bash
bash ./tools/upload_vpk_ftp.sh <vita-ip> dist/RenegadeVita-<candidate>.vpk
```

The default destination is:

```text
ux0:/data/renegade/user/<vpk-file-name>
```

## Evidence after a test

Keep each item bound to the exact candidate hash:

- runtime log under `ux0:data/renegade/user/logs/`;
- for Dev202, `a35-dev202-runtime.log` and matching startup diagnostics from
  that directory (use the matching label for other candidates);
- title-owned captures under `ux0:data/renegade/user/captures/`;
- a PSP2 dump if a crash occurred; and
- a finalized recorder MP4 only when its own file/hash can be established.

Never commit retail data, raw dumps, arbitrary personal media, pairing material, or private device configuration. See [Evidence and capture policy](EVIDENCE.md).
