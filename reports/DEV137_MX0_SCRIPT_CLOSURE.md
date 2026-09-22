# Dev137 M13 original script closure

## Change

Retail `M13.mix` contains references to `MX0_*` and `M00_*` scripts. Dev135
linked M00 but omitted the original `MissionX0.cpp` translation unit, so
rendered M13 geometry alone could not establish authentic mission scripting.
Dev137 links `MissionX0.cpp` only in the full-port profile. The demo source
selection is unchanged. A compatibility include alias handles the source's
`missionX0.h` spelling on case-sensitive filesystems. A zero-fuzz staging
patch supplies nine documented original MSVC default arguments at callback
call sites without changing the script command table or serialized layout.

An attempted all-mission source compile exposed broader old-C++ failures in
other original scripts (`slist.h` private-node access and callback-default
macro collisions). That unaccepted broad source selection was narrowed to
the M13 family; no failed all-mission candidate was packaged or published.

## Verification

- `bash tools/stage_sources.sh` completed with the new patch and no reject or
  backup debris. The staged `MissionX0.cpp` contains the nine explicit calls.
- The full-port ARM ELF, SELF, and VPK built. `arm-vita-eabi-nm -C` finds
  `_MX0_MissionStart_DMERegistrant` and `_MX0_A03_HUMVEERegistrant` in the
  linked ELF. The package contains only `eboot.bin` and `sce_sys/param.sfo`.
- In isolated Vita3K v0.2.1 Vulkan, original Single Player -> Soldier selected
  `M13.mix`. The runtime reported `provider_active=1 registered=68 active=31`,
  versus Dev135's `registered=37 active=12`, then rendered its first M13
  gameplay frame with 108 meshes, 10560 vertices, 7116 triangles. Sampled
  render checkpoints reported `backend_errors=0`. `window-291.png` shows the
  desert scene and HUD. The 300-second watchdog terminated only the owned
  emulator process and released synthetic input.
- No objective was present at the first sampled frame, and no required
  objective, script sequence, save roundtrip, mission completion, normal
  transition, clean in-app exit, or physical Vita result is claimed.

VPK SHA-256: `fc75c2045c5692ba91dfdfde8912efd181f11c2eb7bba5022429e93995ef5892`.
SELF SHA-256: `e7b2ac612f622410bffd66d0559892da9a9eb3fee866bfc7122a49f86abe37bb`.
ELF SHA-256: `3351d998c67096d84cb431b4c44da85633c5d73f318ce9ca9a63f0e56b35592f`.
Trial evidence is candidate-scoped under managed AppData
`campaign-dev137-trial-1/`; no retail files are included in the package.

## Mission status

| Mission | Initialization | Required gameplay/objectives | Normal transition | Save/load | Build/evidence |
| --- | --- | --- | --- | --- | --- |
| M00 Tutorial | passed previously | partial, unverified completion | unverified | previous demo evidence | Dev134 physical deployment, earlier M00 runtime evidence |
| M13 | passed in Vita3K | original MX0 registration/instances passed; objectives unverified | unverified | Dev136 implemented but untested | Dev137 Vita3K trial 1 |
| M01-M11 | unverified in Vita runtime | scripts not yet linked | unverified | unverified | original retail flow traced; no campaign gameplay result |

Next executable step: add original campaign script units through specific
compatibility patches, then restore original pending-campaign continuation
without re-entrant level teardown. Repeat M13 with objective/event tracing
and a real save/reload before claiming a playable mission.
