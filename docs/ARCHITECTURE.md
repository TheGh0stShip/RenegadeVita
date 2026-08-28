# Architecture

Renegade Vita is a source port with narrow platform-boundary replacements.
The original engine remains the owner of game rules, mission scripts,
filesystem/archive lookup, W3D loading, scene traversal, physics, animation,
camera behavior, combat, HUD, audio object ownership, and session lifecycle.

## Runtime Shape

```text
Retail Renegade Data
  -> original FileFactory/MIX/resource systems
  -> original W3D and definition loaders
  -> original WW3D/WWPhys/Combat/Commando owners
  -> Vita boundary implementations
  -> vitaGL/SceAudio/SceCtrl/Vita filesystem
```

The port must not introduce a custom runtime world format, replacement physics
engine, replacement scene graph, replacement game loop, PSP target, or bundled
retail asset conversion.

## Upstream And Staging

`upstream/CnC_Renegade/` is the pinned official source. Keep it clean.

`staging/` is generated from upstream plus deterministic patches. It exists so
the Vita build can compile GCC/Vita-compatible source without editing the
submodule in place.

The normal upstream-change workflow is:

```bash
edit or add port/patches/<module>-<topic>.patch
register it in tools/stage_sources.sh
bash ./tools/stage_sources.sh
```

Patch application must be deterministic and zero-fuzz.

## Port Boundaries

- `port/compatibility/`: MSVC/Win32/compiler compatibility shims.
- `port/filesystem/`: retail-root path translation, writable-user routing,
  POSIX/Vita file behavior, cache health, find-file compatibility.
- `port/platform/`: input, runtime lifecycle, optional service stubs,
  script/static providers, UI/resource boundaries.
- `port/renderer/vita/`: DX8-facing WW3D backend replacement over vitaGL.
- `port/audio/vita/`: Miles-compatible provider over decoded WAVE data and
  Vita audio output.
- `port/validation/`: host/Vita contracts that prevent boundary regressions.

## Current Source Integration

A3.5-dev79 currently records:

- 1,490 original EA/Westwood source files discovered.
- 452 original source files compiled.
- 1 staged original-owner extraction for the shared loading-screen path.
- 26 Vita platform/renderer/validation/developer translation units.
- 52 compatibility headers.
- 121 deterministic staging patches.

See `reports/SOURCE_INTEGRATION_REPORT.json` for the exact source list.
