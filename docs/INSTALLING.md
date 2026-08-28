# Installing

The VPK is intentionally small. It does not include retail data, saves,
configuration, screenshots, logs, or crash dumps.

## Vita Filesystem Contract

Retail files must already exist here:

```text
ux0:data/renegade/retail/Data/
```

The game writes only under:

```text
ux0:data/renegade/user/
```

Do not place generated caches, logs, or saves under `retail/`.

## Manual VitaShell Install

1. Build the VPK with `bash ./tools/build.sh`.
2. Copy `RenegadeVita-<candidate>.vpk` to any convenient VitaShell-visible
   folder, such as `ux0:data/renegade/user/`.
3. On the Vita, open VitaShell and install the VPK.
4. Confirm `ur0:/data/libshacccg.suprx` exists before launching.
5. Launch the bubble and preserve the runtime log after testing.

## VitaShell FTP Upload

Start VitaShell FTP on the Vita, then run:

```bash
bash ./tools/upload_vpk_ftp.sh <vita-ip> dist/RenegadeVita-A3.5-dev79.vpk
```

Default upload target:

```text
ux0:/data/renegade/user/<vpk-file-name>
```

You can choose a different remote directory:

```bash
bash ./tools/upload_vpk_ftp.sh <vita-ip> dist/RenegadeVita-A3.5-dev79.vpk ux0:/VPK
```

The helper only uploads the selected VPK. It does not install it, launch it,
or copy retail data.

## After A Physical Test

Return these if available:

- `ux0:data/renegade/user/logs/a35-dev79-runtime.log`
- any files under `ux0:data/renegade/user/captures/`
- screenshots made by VitaShell or the system
- any `psp2core-*.psp2dmp`

Match every returned log or dump to the VPK hash from
`dist/<candidate>-SHA256SUMS.txt`.
