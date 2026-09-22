# Dev165: M13 Mission Inventory Tooling

Status: source/tooling candidate, not a runtime acceptance.

Dev165 adds `tools/renegade_cinematic_dependency_scan.py`, a read-only,
metadata-only inventory tool for user-owned mission MIX archives. It does not
export retail payloads. For `M13.mix`, it now records archive entries, all
mission `.txt` cinematic command dependencies, referenced script names, and
static source coverage for the M13/MX0/X00/M00 script surface.

Current M13 inventory from `build/dev136-host/retail/Data/M13.mix`:

- Archive entries: 137 total; 62 `.w3d`, 48 `.dds`, 22 `.txt`, plus one each
  `.dep`, `.ldd`, `.lsd`, `.wlt`, `.max`.
- Cinematic text scripts: 22.
- Parsed cinematic commands: 760 records.
- Command classes: `create_object`, `create_real_object`, `play_animation`,
  `play_audio`, `attach_script`, `attach_to_bone`, `destroy_object`,
  `send_custom`, camera/fade/letterbox, movement and primary-target commands.
- Text dependency totals: 53 cinematic models, 27 real-object presets,
  92 animation names, 5 audio cue names, 15 script classes.
- Static source check: all 15 data-referenced script class names have matching
  source `DECLARE_SCRIPT` names.
- Binary chunk inventory: `m13.ldd` is 277,965 bytes with 4,490 chunk headers,
  max depth 14, and the expected top-level `0x3c51c460` level-info chunk plus
  `0x3c51c461` level-data chunk. The level-info microchunk 1 names `M13.lsd`.
  `m13.lsd` is 888,276 bytes with 19,316 chunk headers, max depth 13, and six
  top-level save subsystems: `0x00020000`, `0x00020001`, `0x00030005`,
  `0x00040126`, `0x00040147`, and `0x00040800`.

The intro-specific gate also compares `x00_intro.txt` dependencies against the
runtime M13 preparation arrays. A broad runtime preparation experiment for all
intro models/animations was rejected because the Vita SELF conversion failed
with the same 3936-byte segment overlap seen before. The packageable Dev165
candidate therefore keeps the prior narrow runtime preparation and records the
gap explicitly: 3 prepared render models, 15 missing authored intro render
models, 36 missing authored intro animations, and 16 missing authored
real-object presets.

Build/package evidence:

- ARM ELF: `51f768c9fe4e45cafc329df149833271657732db347f85f7e6decaf859178594`
- SELF: `e10b7b56606a839933e18710a8b1c85bf3021c1fc00cd49093ab1e5f0be07ed8`
- VPK: `b31e23bd707eb7ce3f4d5293e54c9596241a1a29e66d383cf6ed531a661f38d2`
- No Vita3K or physical runtime acceptance is claimed for this candidate.

Known limits remain explicit:

- LDD/LSD chunk structure is inventoried, but object graph semantics, factory
  ownership, pointer fixups, and script observer state are not decoded yet.
- W3D internal texture/material/subobject references are not inventoried yet.
- DDB preset transitive references are not inventoried yet.
- Static source matching does not prove compiled linkage or runtime execution.

Next executable step: add binary mission graph and W3D/preset transitive
inventory, then use that output to drive M13 runtime preparation and campaign
mission gates before another broad Vita3K performance run.
