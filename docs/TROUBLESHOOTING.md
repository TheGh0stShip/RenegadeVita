# Troubleshooting

## Build Fails Before CMake

Check the basics:

```bash
git submodule update --init --recursive
git -C upstream/CnC_Renegade status --short
/usr/local/vitasdk/bin/arm-vita-eabi-g++ --version
python3 --version
```

If VitaSDK is installed elsewhere, set:

```bash
export RENEGADE_VITASDK=/path/to/vitasdk
```

## Retail Data Is Missing

Host validation needs a retail install or an explicit retained validation log.
For a fresh host with retail files available, set:

```bash
export RENEGADE_RETAIL_ROOT=/path/to/Command_and_Conquer_Renegade
```

On Vita, the runtime expects:

```text
ux0:data/renegade/retail/Data/always.dat
ux0:data/renegade/retail/Data/Always2.dat
ux0:data/renegade/retail/Data/M00_Tutorial.mix
```

Do not commit or package these files.

## VPK Launches But Graphics Are Broken

Confirm `ur0:/data/libshacccg.suprx` exists. Then return:

- the runtime log;
- a screenshot or capture of the bad frame;
- the VPK SHA-256 from the matching `dist/<candidate>-SHA256SUMS.txt`;
- any `checker_bind`, `invalid_bind`, `unsupported_stages`, texture-load, fog,
  ambient, material, or loading-screen breadcrumbs from the log.

## No Audio Or Missing Dialogue Text

Return the runtime log and note the exact mission moment. For Logan dialogue,
the useful log areas are active conversation state, speech object state,
stream bytes/frames/mix/output counters, WAVE fact/trim metadata, and
TextDisplay/HUD breadcrumbs.

## Crash Or Freeze

Preserve the current VPK/ELF/map/symbol set. Return:

- `ux0:data/renegade/user/logs/<candidate>-runtime.log`
- any `psp2core-*.psp2dmp`
- what input was pressed and what was visible before the freeze

Use matching artifacts only when symbolicating. Do not symbolicate a dump with
an ELF from a different candidate.

## Hygiene Check Fails

Run:

```bash
python3 tools/verify_repo_hygiene.py --root .
```

Tracked build products, local profile paths, generated logs, retail data,
credentials, and crash dumps should be removed from the index, not moved into
another tracked directory.
