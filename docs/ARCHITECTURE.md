# Architecture

Renegade Vita is a source port with narrow Vita boundary replacements. Original EA/Westwood code remains the owner of game rules, scripts, MIX/archive lookup, W3D loading, scene traversal, physics, animation, camera, combat, HUD, audio object ownership, and session lifecycle.

```text
Unchanged retail Renegade data
  -> original FileFactory / MIX / definitions / W3D owners
  -> original WW3D / WWPhys / Combat / Commando owners
  -> narrow Vita platform and DX8 boundary implementations
  -> vitaGL / SceAudio / SceCtrl / Vita filesystem
```

The port must never introduce a replacement game loop, world format, scene graph, physics engine, PSP target, or bundled retail conversion runtime.

## Source and staging

- `upstream/CnC_Renegade/` is the pinned released source and must remain pristine.
- `port/patches/` contains deterministic zero-fuzz patches applied only to staging.
- `staging/` is generated from upstream plus those patches; it is not a source of record.
- `port/` contains Vita compatibility, filesystem, lifecycle, renderer, audio, input, and validation boundaries.

## Evidence boundary

The runtime is an original-owner port, but each claim still needs its own evidence:

- host tests establish source semantics and regression contracts;
- Vita3K can shorten iteration;
- matching physical Vita evidence establishes panel output, controls, audio, pacing, storage, suspend/resume, and lifecycle behavior.

See [Evidence and capture policy](EVIDENCE.md), [Development](DEVELOPMENT.md), and the durable [source integration report](../reports/SOURCE_INTEGRATION_REPORT.json).
