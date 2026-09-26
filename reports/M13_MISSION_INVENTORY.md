# M13 mission inventory

2026-09-24 correction: the counts below are historical. The previous host
target omitted MissionX0, Mission01 and cinematic object factories even
though Vita linked them. Current host source includes them; a new registry
check requires runtime-linked factories, not merely source declarations.
The expanded runtime exposed and fixed host file-pointer truncation while
reading X00_Intro.txt, then reached an unsupported host SortingRenderer
submission. Full-script census and 80-second intro probe remain incomplete.
Do not use the old census to claim intro/NPC coverage. Asset scan results
remain useful. User requested pause before the next boundary fix.

Status: source/host inventory, not gameplay or visual acceptance. Retail
payloads and local generated inventories stay under `build/host-m13-diagnostic/`;
none belong in a VPK or GitHub.

## Reproduce

```sh
python3 tools/renegade_cinematic_dependency_scan.py --archive build/host-m13-diagnostic/retail/Data/M13.mix --mission-inventory --project-root . --output build/host-m13-diagnostic/m13-mission-inventory.json --preset-list-output build/host-m13-diagnostic/m13-cinematic-presets.txt --asset-list-output build/host-m13-diagnostic/m13-level-assets.txt --quiet
cmake --build build/host-a30-definitions --target a31_interactive_runtime -j4
RENEGADE_M13_PRESET_LIST=build/host-m13-diagnostic/m13-cinematic-presets.txt RENEGADE_M13_ASSET_LIST=build/host-m13-diagnostic/m13-level-assets.txt build/host-a30-definitions/a31_m00_interactive_runtime build/host-m13-diagnostic/retail build/host-m13-diagnostic/user build/host-m13-diagnostic/cache build/host-m13-diagnostic/mods M13.mix M13_INVENTORY > build/host-m13-diagnostic/m13-runtime-inventory.log
python3 tools/check_m13_mission_inventory.py build/host-m13-diagnostic/m13-mission-inventory.json build/host-m13-diagnostic/m13-runtime-inventory.log --output build/host-m13-diagnostic/m13-inventory-summary.json
```

## Current evidence

- `M13.mix`: 137 entries, including 62 W3D, 48 DDS, 22 text, one LDD,
  and one LSD. All 22 text files are scanned, not only `X00_Intro.txt`.
- Original `M13.dep` declares 315 preload records: 294 W3D-shaped names
  and 21 literal `.w3d` placeholders. There are 251 distinct names across
  its records. This is the original level asset-dependency file, not a
  guessed filename list.
- Text dependencies: 53 cinematic models, 92 animation names, 27 real-object
  presets, 15 script names, five audio names, and two custom messages.
  Script-name registrations match the checked-out source. The 27 presets
  all resolve through the original loaded definition manager.
- After 120 original-engine host frames: 152 game objects, 136 physical
  objects, and 28 attached observers. The runtime census records each
  object's ID, definition/class IDs, name, render model, killed-explosion
  ID, and observer ID/name. Both in-process cycles agree after accounting
  for expected generated network-ID differences.
- Westwood's original `Get_W3D_Dependencies` scans the 62 in-archive W3Ds,
  valid `M13.dep` names, and their W3D references: 259 unique W3D names
  and 405 edges. Of these edges, 163 resolve by raw name and 241 `.tga`
  names resolve through the original `.dds` alias convention. Separate
  `UNNAMED.w3d` and `L00_TEMP.w3d` files cannot be opened, and the raw
  `l00.w3d` reference to `l00_temp.w3d` remains unresolved. The level
  still loads in the host route; these are lookup findings, not yet
  evidence of missing visible assets.
- Original M13 host prewarm smoke separately resolves the authored intro
  models/animations, validates Havoc and engineer attachment bones, and
  kills both retail SAMs through original scripts. The Havoc trajectory
  moves `BN_Havoc` downward by 13.48 Z units over frames 0-200.

Validation: two inventory cycles and `check_m13_mission_inventory.py` pass;
three focused `.dep`/runtime-census unit tests and 21 M13 source contracts
pass. `git diff --check` is clean. No raw retail files or memory dumps are
included in this report.

## Ownership and gaps

`a31_interactive_main.cpp` is the original-runtime test entry point, not a
place to duplicate every retail asset name. It invokes the bounded census
in `m13_runtime_inventory.h`; the MIX scanner inventories authored data,
and `check_m13_mission_inventory.py` reconciles both evidence classes.

This is not an exhaustive live-mission object graph. The LDD/LSD chunk
inventory has not reconstructed every reference/fixup; DDB transitive
definition references beyond initialized objects and cinematic presets
remain open. The 120-frame census does not include later scripted spawns,
NPC action state, dialogue progress, or mission transitions. Pointer
addresses are process-specific; stable IDs and observer references are the
useful cross-run identities. W3D dependency resolution does not prove
materials render correctly, that the barrel shroud is lit/textured, or that
Havoc's body visibly rappels on Vita.

Next: extend original-engine definition/reference traversal and sample
scripted phase boundaries, then compare the same M13 route on Vita3K and
physical Vita for effects, actors, tank treads, audio drift, memory, and
frame-time distribution. No newer VPK or Vita3K install was produced by
this inventory work.
