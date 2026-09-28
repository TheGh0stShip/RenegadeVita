# Further missing-content sweep — 2026-09-27

This extends [the cross-system audit](CROSS_SYSTEM_DEEP_AUDIT.md). It is a
source/data investigation, not a repair or native acceptance. No C++ build,
game launch, server interaction, device action or retail/save write occurred.
The inspected executable remains Dev207; local script-selection corrections
have not been compiled. Vita remains little-endian ARMv7 ILP32; the new W3D
parser uses explicit little-endian 32-bit headers and fixed on-disk widths.

## Newly established gaps and more precise consequences

### Original particle startup state is also missing

Restoring the four prototype registrations identified previously is insufficient.
Original `staging/commando/init.cpp:873` sets
`ParticleEmitterClass::Set_Default_Remove_On_Complete(false)` and then applies
17 particle LOD screen-size thresholds. Neither setter has a call in the native
port sources. The original initializer is not the native startup owner.

`staging/ww3d2/part_emt.cpp:65` defaults the lifetime flag to **true**, copied
into each emitter at construction. `part_buf.cpp:70` defaults all 17 thresholds
to **NO_MAX_SCREEN_SIZE**, whereas Commando initializes a graduated table
(`init.cpp:159`). Thus native startup retains different lifetime and LOD
defaults. This is a source-confirmed semantic difference; which effects are
affected, visual consequences and cost require runtime evidence. Restore the
original initialization, without inventing performance thresholds.

### Mission ranks and replay unlocks lack durable storage

`scorescreen.cpp:178` writes the completed mission rank through
`LoadSPGameMenuClass::Set_Game_Rank`. `dlgloadspgame.cpp:274–350` consults that
rank to allow Mxx.MIX replay entries. The score owner **is selected** and the
campaign's Score/Replay branches call its original Save_Stats/activation path.

The rank is stored only through RegistryClass. Its native replacement in
`port/filesystem/renegade_registry.cpp` uses a process-local array; load/save
registry methods at 308–313 are empty. No separate mission-rank persistence
was found in the port. Earned ranks/replay availability therefore lack a
durable restart path. This concerns profile progression, not the contents of
ordinary save files. Audio/performance options have separate native persistence
and must not be conflated with this finding.

### Multiplayer round restart exits instead of continuing

`messages.cpp:1157` and `:1285` set `g_b_core_restart` for map/round progression.
The original handler in `combatgmode.cpp:1483–1526` is excluded by the active
`RENEGADE_VITA_FRONTEND_SINGLEPLAYER` flag. Native runtime at
`port/platform/vita/a31_vita_runtime.cpp:4383` explicitly treats that flag as a
reason to leave the remote world and return to the menu, clearing it before
exit. This is additional to the previously documented START-button exit.
It prevents that path from providing seamless remote round continuation.
Practice's local restart consumer is also excluded; its exact end-of-round
behavior still needs a complete local control-flow/runtime trace.

### Radio input handling is excluded along with its display

The guard at `combatgmode.cpp:261–341` removes more than informational dialogs:
it removes the 30-radio-command input loop, CSAnnouncement creation, multiplayer
player-list cycling and original public/team chat-popup entry. A source search
found no replacement radio-command sender in the native platform files.
Replicated incoming chat remains a distinct implemented capability. Do not
equate network event presence with availability of the original input/UI route.

### Render-to-texture projectors remain unsupported

`port/renderer/vita/ww3d_dx8_boundary.cpp:2340` returns NULL from
DX8Wrapper::Create_Render_Target. The boundary Set_Render_Target overloads in
`a31_gameplay_boundary.cpp:1427` reject non-default targets. Original
`ww3d2/texproject.cpp:1115` and `wwphys/pscene_projectors.cpp` depend on these
targets for their offscreen projector rendering. The original allocation
fallback avoids submitting such a draw; this is missing rendering capability,
not proof of a crash or that every shadow/projector is absent. Texture-based
dynamic projection needs a real native provider and visual validation.

## Nested asset scan

Added `tools/audit_nested_w3d_references.py`. It recursively validates bounded
W3D chunks using the container flag and extracts texture-name and HLOD-subobject
records according to `ww3d2/w3d_file.h`. Across the same **3,330 archive entries**:

- **53,284 texture-reference occurrences**.
- **32,516 HLOD-subobject-reference occurrences**.
- **Zero malformed nested chunks or invalid HLOD record widths**.
- **297 texture occurrences / 14 unique names** without an exact filename or
  DDS sibling in the inspected retail root or readable archive indexes.

All unresolved occurrences are in always.dat:

| Texture name | Occurrences |
| --- | ---: |
| green_line.tga | 280 |
| in_static01.tga | 3 |
| in_grad2.tga | 3 |
| if_screen01.tga, if_screen02.tga, if_screen03.tga | 1 each |
| pattern1.tga | 1 |
| in_noise00.tga, in_noise01.tga, in_noise02.tga, in_noise04.tga, in_noise07.tga | 1 each |
| loadmenu.tga | 1 |
| 19_grngoop1.tga | 1 |

These are **unresolved leads**, not confirmed missing port code or proof that
retail data is damaged. Archive-wide references can be unused; runtime may
substitute textures. Searching all archives is deliberately permissive and
does not establish that a matching file is mounted on a particular map.
The HLOD census records names; it does not resolve every named prototype,
hierarchy, aggregate, animation or emitter texture dependency.

Local metadata receipt: `build/dev208-nested-w3d.json`. No model/texture bytes
are exported. Reproduce with:

```bash
python3 -m tools.audit_nested_w3d_references --data build/host-m13-diagnostic/retail/Data --output build/dev208-nested-w3d.json
python3 -m unittest tools.test_nested_w3d_references
```

## Cleared suspicions and narrowed findings

- The manual **NetworkGameObjectFactoryClass** in `combat/basegameobj.cpp:54`
  was outside the earlier macro census. Its factory instance, Create method
  and vtable are present in Dev207. No additional missing manual factory was
  found by searching the staged C++ NetworkObjectFactoryClass declarations.
- MovieGameModeClass::Start_Movie and ModPackageMgrClass::Set_Current_Package
  have original defined methods in Dev207. Their fallback substitutes are
  excluded by the full-port configuration; do not list them as missing.
- Campaign difficulty is explicitly set before the empty console-parser call
  (`campaign.cpp:203`); the empty parser does not establish broken difficulty.
- Original AudioTextCallback is a debug-text callback (`init.cpp:366`). Its
  missing native registration does not establish missing conversation subtitles.
- MPSettingsMgrClass::Load_Settings has no native startup call, but it mixes
  retired WOL account settings with option flags. This remains a settings
  review lead, not a requirement to revive WOL or persist obsolete credentials.

## Validation and remaining work

Four new asset-free parser tests cover nested references, parent bounds,
32-bit disk record widths and non-container leaves. Combined with the prior
77 Python checks, **81 checks pass**. The previous coverage guard remains
INCOMPLETE with 73 grouped entries; the new semantic findings above are not
automatically represented by that gate. Do not read its count as comprehensive.

This pass investigated startup/substitute semantics, campaign score/replay,
round/radio paths, a manual network factory and nested W3D records. It did not
exhaustively classify all 158 unselected files or 90 empty methods, prove all
parameter-driven script targets, reconstruct every mission trigger/optional
objective chain, resolve all nested asset types or perform save round trips.
Those remain open, together with actual UI interaction, rendering/audio and
physical-device validation. No new native evidence gate is closed.

Next restoration priorities: original loader and particle bootstrap state;
required script owners; death/load/save/profile persistence; full options and
multiplayer route/round ownership; native projector capability. Keep original
owners above the platform boundaries throughout.
