# Campaign source map reconciliation

Follow-up: [static linkage and mission ranks](STATIC_SCRIPT_LINK_AND_MISSION_RANKS.md)
documents the trim-symbol collision exposed by joining the DLL code, stronger
actual-target selection checks and integration-report expansion. These changes
remain uncompiled.

[Authored mission bindings](AUTHORED_MISSION_BINDINGS.md) follows Tutorial,
M13 and M01 level parameters, spawner IDs and cinematic attachments. It records
cross-mission helpers, unresolved lookup lifetimes and named effect/audio
definition leads without claiming compiled or runtime coverage.

## Result

The supplied mission map was checked against the checked-out
`electronicarts/CnC_Renegade` source and the active native and retained host
CMake source graphs. The source counts for all 13 campaign units match: 1,370
declared scripts across 101,508 newline-terminated source lines. The 13 files
use 143 distinct `Commands` methods from the 202-entry ScriptCommands table.
The per-mission numeric `Find_Object` ID counts match the supplied map. These
are source references; they do not prove that retail LDD files contain and
preserve those IDs.

The check found a major source-closure hole: both target graphs omitted
Mission02.cpp, Mission04.cpp, Mission05.cpp, Mission06.cpp, Mission07.cpp,
Mission09.cpp and Mission10.cpp. Native and host targets now draw their script
translation units from the original `Scripts.dsp` inventory instead of
maintaining separate hand-picked lists. That inventory contains 45 `.cpp`
files; the 44 code units are selected and `DLLmain.cpp` is excluded because
the existing `renegade_script_static_provider.cpp` replaces the DLL entry
point for static registration. The 13 campaign files are also pinned by a
CMake count check.

| Campaign area | Source file | Lines | Declared scripts | Unique literal object IDs | `.txt` names | `.mp3` names |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Tutorial | `Mission00.cpp` | 4,825 | 22 | 0 | 1 | 0 |
| Mission 0 / M13 | `MissionX0.cpp` | 3,346 | 31 | 15 | 9 | 3 |
| Mission 01 | `Mission01.cpp` | 22,059 | 289 | 101 | 149 | 0 |
| Mission 02 | `Mission02.cpp` | 5,380 | 26 | 187 | 43 | 1 |
| Mission 03 | `Mission03.cpp` | 7,143 | 86 | 57 | 16 | 2 |
| Mission 04 | `Mission04.cpp` | 10,518 | 138 | 72 | 1 | 0 |
| Mission 05 | `Mission05.cpp` | 7,858 | 111 | 59 | 45 | 2 |
| Mission 06 | `Mission06.cpp` | 5,710 | 85 | 91 | 17 | 1 |
| Mission 07 | `Mission07.cpp` | 6,733 | 122 | 56 | 21 | 1 |
| Mission 08 | `mission08.cpp` | 7,184 | 114 | 59 | 24 | 2 |
| Mission 09 | `Mission09.cpp` | 4,706 | 96 | 57 | 10 | 0 |
| Mission 10 | `Mission10.cpp` | 4,779 | 79 | 77 | 17 | 0 |
| Mission 11 | `Mission11.cpp` | 11,267 | 171 | 76 | 12 | 0 |

The `.txt`/`.mp3` columns count unique quoted literal references within that
source file; they do not include names supplied through retail level data.

The directory has 54 `.cpp` files. Nine are outside `Scripts.dsp`, and remain
excluded as the original project did: `Common.cpp`, `Group.cpp`,
`GroupControl.cpp`, `GroupScript.cpp`, `unitcombat.cpp`, `MissionS04.cpp`,
`PRDemo.cpp`, `Test_DEL.cpp` and `Test_DLS_M03.cpp`. This avoids treating
every test/demo source as shipped campaign content while including all 45
original project entries.

## Reproduced facts and discrepancies

- Source order is tutorial `Mission00.cpp`, opening mission `MissionX0.cpp`,
  campaign `Mission01.cpp` through `Mission11.cpp`; Mission 08 is lowercase
  `mission08.cpp`. No `Mission12.cpp` or `Mission13.cpp` exists; `Mission12.h`
  does. Do not synthesize mission source for either absent file.
- The source contains 365 distinct quoted `.txt` cinematic-control filenames
  and 12 distinct quoted `.mp3` filenames. This is a lower bound: level data
  supplies additional script parameters, presets, sounds and media.
- The source parser counts 3,480 `Commands->Find_Object(...)` call expressions.
  The supplied overview says 3,478. Per-file unique numeric-ID counts match;
  the two-call total difference remains unresolved and is retained as a
  discrepancy, not silently normalized.
- `Combat/scripts.cpp` loads `scripts.dll` using the Windows loader API, while
  the Vita graph uses the static provider. `Commando/campaign.cpp` names
  `campaign.ini` and contains the M13 autosave exception. The exact retail
  campaign sequence and M13 opener identity were subsequently confirmed
  against the user's retail campaign.ini, as recorded below. No retail
  payloads were copied into the repository.

## Systems implied by the map

Compiling mission scripts is only one closure layer. Their runtime needs the
original ScriptCommands, script state/timer/custom-event/save machinery,
zone callbacks, toolkit and designer scripts, AI observer and hibernation
behavior, action/path-action/vehicle behavior, pathfinding data, conversation
and translated-string systems, cinematic parser, objectives/HUD/radar,
building and weapon behavior, and boss classes. Media dependencies cross the
WW3D renderer, Miles audio boundary, movie player and weather/effects paths.
The supplied map identifies these as required owners; it does not establish
their current Vita correctness. Static map and manifest checks do not validate
script registration, ABI/build success, mission progression, visual/audio
fidelity, or hardware performance.

## Retail install spot-check

The user's unchanged E: Steam Data tree was inspected in place. Its
`always.dat` contains `campaign.ini`; that file has 36 ordered flow entries,
the expected `M13.mix` opener followed by `M01.mix` through `M11.mix`, and
movie entries for missions 01–11 plus the finale. The tutorial map is not a
campaign-flow entry. The retail tree's top-level listing lacks M09.mix, but a
read-only search found it in Steam backup snapshots; the audited snapshot is
identified by its archive hash below. Thus the source and campaign.ini
sequence agree; the M13 opener is confirmed by the actual flow data.
The inspected `always.dat` SHA-256 is
`f1fa13ed10d0b09fea999660cff71dc784a01a22cdc3e4f0041720ca67dfa29a`.

For each mission, the source's unique literal object-ID lookups were compared
with instance IDs parsed from LDD/LSD `BaseGameObj` records. Many IDs do not
appear as placed objects (for example M13 IDs 1200017 and 1400035), and most
maps have similar apparent differences. Some are intentionally runtime
spawns, waypoint/spawner IDs, IDs owned by other scripts or definitions, or
lookups whose execution depends on a branch. Therefore this comparison is a
candidate set for call-site review, not a list of proven missing level
objects. The low-level chunk inventory does not yet follow every pointer
token, spawner record, generated object or cross-map/shared script reference.
Do not call these differences silent mission failures without resolving the
specific ID's authored owner and runtime lifecycle.

The archive receipt uses size and SHA-256 only; no retail members or asset
payloads were copied to the repository. Mission archive hashes:

| Map | Archive SHA-256 |
| --- | --- |
| M00_Tutorial.mix | `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438` |
| M13.mix | `54d41ea011bf7c4d273064422de961af76ccc38f32dd9b5368ebfbca365bbfc4` |
| M01.mix | `3d814a11fb306b425da74d40648f17053644e6a58ce521182d7c178683b354eb` |
| M02.mix | `f098e9190802dba8c9b453e479cb393a0e4777c5f5b038c3bb0376010d64b3a1` |
| M03.mix | `e49d5a6233635228ad91c73cd2614f3f33e09cbc37d0650eb79683f35aa47d79` |
| M04.mix | `1d084c9088474c6664dcb30eb08cd7fc86a265e200fbfcebb606ac56e9530ffa` |
| M05.mix | `d3b38752890e0d2102a5ba8f57d10c832b8b60749afc4d0512333ca3f64446ca` |
| M06.mix | `cf98d879ac8cf23e60589407b61eb4c2a43c238c979b54485a25938f7679573a` |
| M07.mix | `479f72c76ec145c0289f331a856201d0f4249fa86854a5d664c6e8d4edc08664` |
| M08.mix | `b95c738add5ce7887ec386d839838d595986a05c2f5240b90fe2cebaa7075429` |
| M09.mix (Steam backup snapshot) | `059fc7de0c06c31e2aa69e1ab7768de81f3377e18c971ba8f98f41e15f1705c1` |
| M10.mix | `c9bdaa94686f29a69a16c148671c7a6c05c617f61694fb4aec01185e4c3720ec` |
| M11.mix | `f29a8a4bf4e94d928b8e49c0d4eecade0d35f54ff683ec0fd5b2e4bedbac80eb` |

## How the supplied recommendations apply here

The source inventory is useful dependency evidence. Its implementation and
performance suggestions still need comparison with the existing port:

- Preserve the retail `M00_Damage_Modifier_DME` parameter mismatch:
  `Toolkit.cpp:1824` declares `Killable_by_NotStar`, while line 1849 reads
  `Killable_ByNotStar`. Case-insensitive lookup does not erase underscores.
  Other serialized misspellings, including `Aggessiveness`, remain exact.
- Original `Combat/scriptcommands.cpp:108` already guards `Debug_Message`
  with `WWDEBUG`. Do not delete mission calls as a new portability change.
  Candidate diagnostics retain their existing bounded recording policy.
- The movie boundary already uses FFmpeg to decode unchanged retail BINK data
  (`port/platform/a4_binkmovie_boundary.cpp`). The suggested MP4 conversion
  does not become a new retail-data requirement or campaign-flow rewrite.
- The current renderer's compressed DDS upload branch explicitly admits
  DXT1/DXT5 (`port/renderer/vita/ww3d_dx8_boundary.cpp:1114`). The broad DXT1/3/5
  statement is not proof that every format uses that path or renders correctly
  on hardware; keep format/fallback and visual checks separate.
- Time-slicing pathfinding, trimming visibility data, limiting flyovers or
  particles, changing aim behavior and suppressing voiced keyboard prompts
  require their own correctness and measured-impact evidence. The mission map
  alone does not justify changing original semantics or removing content.
- Conversation keys resolve through `ConversationMgrClass`; conversation
  remarks then resolve translation objects and sound-definition IDs. The
  level parser intentionally skips the category-prefixed conversation
  subsystem rather than guessing its chunk layout. Complete conversation,
  string, voice, animation and objective-image closure remains separate work.

The overview's remaining aggregate conversation/string/image/preset counts
have not been independently certified by this source-manifest audit. Literal
counts are discovery bounds; authored parameters and runtime-generated names
require additional tracing. Floating-point differences also need correctness
checks where they can alter gameplay, persistence or networking.

## Validation and open evidence

The new generated inventory is
[`generated/campaign_mission_source_surface.json`](generated/campaign_mission_source_surface.json).
The audit and CMake manifest test assert all 13 mission declarations, 143/202
command coverage, 45/44 DSP inventory, the exact nine out-of-project sources,
and selection in both CMake graphs. CMake script-mode testing validates the
manifest parser only. No native or host C++ target was compiled or linked for
this work unit, and no game was launched. The seven newly selected files
therefore remain uncompiled and unregistered-by-runtime until those later
gates run. Physical mission coverage remains open.

The retail-data checks still needed are: resolve every apparent ID difference
to its authored/runtime owner; enumerate level-attached script names and their
parameters; and resolve all archive-provided cinematic, model, animation,
sound, string and objective-image references across every map. Runtime checks
still need to execute each route with session-matched semantic markers. These
are distinct from source closure.
