# Troubleshooting

## Build stops before CMake

```bash
git submodule update --init --recursive
git -C upstream/CnC_Renegade status --short
${RENEGADE_VITASDK:-/usr/local/vitasdk}/bin/arm-vita-eabi-g++ --version
python3 --version
```

Set `RENEGADE_VITASDK` if VitaSDK is elsewhere. Do not edit the pinned upstream tree to work around a missing tool.

## Retail validation data is unavailable

Set a local, user-owned root for host validation:

```bash
export RENEGADE_RETAIL_ROOT=/path/to/Command_and_Conquer_Renegade
```

On Vita, retail data belongs below `ux0:data/renegade/retail/Data/`. Never commit or package it.

## The VPK launches but output is wrong

Confirm `ur0:/data/libshacccg.suprx` exists, then retain the matching candidate identity and runtime log. Record the exact visible state—intro, menu, loading, dialogue, HUD, world, or exit—not merely “graphics broken.”

A log is not visual proof. Use a reviewed screenshot or future VDB framebuffer capture for panel-content discussion.

## Missing text or audio

State the exact scene and interaction. For frontend text, dialogue text, and BINK audio, retain candidate identity and the relevant bounded runtime timing/glyph diagnostics. Do not substitute strings, overlays, or converted retail movies as a diagnostic shortcut.

## Crash or freeze

Preserve the matching VPK, ELF, map, symbols, runtime log, and any `psp2core-*.psp2dmp`. Note the input and the last visible state. Symbolicate only with the exact candidate artifacts.

## No recorder video appears

A red `R` marks recorder start, not a committed MP4. A crash can prevent finalization. Search only the recorder's expected `ux0:/video` output scope and retain a negative receipt when no MP4 exists. See [Evidence capture](DEMO_CAPTURE.md).

## Hygiene check fails

```bash
python3 tools/verify_repo_hygiene.py --root .
python3 tools/verify_public_docs.py --root .
```

Remove accidental tracked build products, retail data, raw dumps, credentials, or unrelated personal media from the index rather than moving them into another tracked location.
