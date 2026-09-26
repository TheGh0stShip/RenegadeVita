# Installing on Vita

For the short end-user path, use the public
[Renegade Vita Demo quick setup](https://github.com/TheGh0stShip/Renegade-Vita-Demo).
This document records the repository's installation and evidence procedure.

The VPK deliberately contains only the executable and package metadata. It never includes retail data, saves, configuration, logs, screenshots, videos, or crash dumps.

## Filesystem boundary

Retail files must already be present on the Vita:

```text
ux0:data/renegade/retail/Data/
```

The tutorial also needs the loose retail fonts at the retail root:

```text
ux0:data/renegade/retail/54251___.TTF
ux0:data/renegade/retail/ARI_____.TTF
```

The documented startup data includes these loose files in `Data/`, alongside
`always.dat`, `always.dbs`, `Always2.dat`, and `M00_Tutorial.mix` for the tutorial:

```text
ux0:data/renegade/retail/Data/stylemgr.ini
ux0:data/renegade/retail/Data/WWAudio.ini
```

The Dev134 startup probes established the two `.ini` requirements. The
original eight-file public setup list omitted them, and its `always.dat`
SHA-256 omitted the final `a`. The verified Steam digest is
`f1fa13ed10d0b09fea999660cff71dc784a01a22cdc3e4f0041720ca67dfa29a`.
Check the digest against the matching retail version; do not delete the final
character to match an older guide. An unpatched English CD installation
without `Always2.dat` cannot satisfy these requirements. A CD tester in
[issue #1](https://github.com/TheGh0stShip/RenegadeVita/issues/1) obtained
`Always2.dat` by applying the Renegade 1.037 English patch and copied the BIK
videos from disc 2 into `Movies`. These are reported CD setup steps, not a
verified fix for campaign progression or performance.

The full campaign needs its corresponding original mission data beyond M00;
use your own patched retail installation and consult the candidate's build
and validation records. The [Dev138 full-port profile](../reports/DEV138_M01_SCRIPT_INTEGRATION.md)
links original M01 scripts, while the M00 demo profile remains separate. Linking scripts does not
prove their runtime sequence or a complete playable campaign.

The port writes only below:

```text
ux0:data/renegade/user/
```

Do not copy generated caches, logs, saves, or modified data into `retail/`.

## Before installation

1. Build the exact candidate with `bash ./tools/build.sh`.
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
- for a Dev134 startup investigation specifically, `a35-dev134-runtime.log`
  and `a35-dev134-startup-precache.txt` from that directory; for later
  candidates, collect their candidate-matched runtime log and diagnostics;
- title-owned captures under `ux0:data/renegade/user/captures/`;
- a PSP2 dump if a crash occurred; and
- a finalized recorder MP4 only when its own file/hash can be established.

Never commit retail data, raw dumps, arbitrary personal media, pairing material, or private device configuration. See [Evidence and capture policy](EVIDENCE.md).
