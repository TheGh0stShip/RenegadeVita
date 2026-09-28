# The Scorpion Hunters: video-driven coverage correction

Follow-up: [level/preset audit](M13_ADDITIONAL_SOURCE_OWNERS.md) found three
additional missing owners and expands the required closure to 75 scripts.
The 62-script results below remain historical bounded evidence, not full
M13 dependency closure. Those three further files are not yet source-selected.

2026-09-27. Source changes and Python/static checks only. No compilation,
game execution, package, installation or deployment. Existing binaries are
unchanged and still lack the registrations identified below.

## Reference and review

User reference: https://www.youtube.com/watch?v=fHR-BlCfE60 and
`E:\CC Renegade - M01 The Scorpion Hunters Commando.mp4`.
Local file: 327.587120 seconds, 1920x1080 H.264/AAC, SHA-256
`b1dfd1c87c9c4d156f9267d8500aa1e29fe4adfab50bc05dbc42bace1daad265`.

Review used sequential two-second frame samples across the full linked video,
captions, and denser one-second frames from the local file at 02:50–03:25.
This is visual sequence inspection, not continuous audiovisual playback or
an A/V timing assessment. The ending is visible; the creator outro follows.
No footage, subtitles or retail payloads are committed or packaged.

The video's display label **M01** denotes the first campaign mission, The
Scorpion Hunters. Its retail engine map is **M13.mix**, with **MX0** scripts.
The existing engine **M01.mix** beach-mission replays are a different mission.

## Confirmed implementation omission

Both original source lists omitted **Test_RAD.cpp**, which owns all nine
`MX0_A02_*` registrations: the controller, actors, startup/default zones,
helicopters and damaged/player vehicle behavior. Its engineer timer replaces
the damaged tank with `GDI_Medium_Tank_Player`; its player-entry callback
advances Area 3 and the controller demolishes the blockage. These are original
gameplay events, not decoration or optional diagnostic content.

Following original literal attachments and all 15 script names in the retail
M13 archive's 22 text files exposed four more absent units:

| Original owner | Missing required behavior/factories |
| --- | --- |
| `Toolkit.cpp` | `M00_Damage_Modifier_DME`, `M00_Generic_Conv_DME` |
| `Toolkit_Objects.cpp` | `M00_Send_Object_ID` actor/vehicle controller handoffs |
| `Test_DAY.cpp` | `M00_Cinematic_Kill_Object_DAY`, `M00_Disable_Loiter_DAY` |
| `mission08.cpp` | `M08_Petra_C_Helo`, referenced by `MX0_A03_NOD_LedgeDrop.txt` |

The five omitted units account for **15 missing factory methods out of 62
required by this conservative M13 source/text closure**, in both inspected
existing executables. This is independently confirmed by demangled defined
symbols, not merely by searching source filenames. Other functions selected
from these units are not proof of their respective missions working.

The old host executable inspected here has SHA-256
`75d47864c48120597f3633ea8bcc806c07c8152c629ed366d8820a40f60a875c`.
The existing Dev207 ARM ELF has SHA-256
`187cfec06117cd0549a8fbb3df387bc5f90908bbb25fe650b84bb6630f95db9d`.
Neither was rebuilt or launched. Earlier reports naming other host executable
hashes do not establish the identity of this inspected file.

## Sequence acceptance map

Times are approximate observations, not simulation deadlines. Every row needs
matching native visual/gameplay evidence; a prior intro test closes none of
the later rows. Source-selected means uncompiled/unverified in this correction.

| Reference | Observed content | Original owners | Current corrected-source / native status |
| --- | --- | --- | --- |
| 00:00–01:11 | Recon convoy, ambush, transport, rappel, camera handback | `MissionX0`, `Test_Cinematic`, `Test_DAY` | Source-selected / unverified |
| 01:11–02:54 | Rescue battle, infantry/snipers, helicopter waves, retreat | `Test_RAD`, `MissionX0` | Previously omitted Area 2 now source-selected / unverified |
| 02:54–03:20 | Squad acknowledgement, engineer repairs, tank handoff/entry, blockage explosion | `Test_RAD`, `Toolkit_Objects` | Previously omitted owners now source-selected / unverified |
| 03:20–03:50 | Tank advance, reinforcements, harvester/Orca encounter | `MissionX0`, toolkit helpers, cinematic dependencies | Source-selected / unverified |
| 03:50–04:27 | Hidden base, defenses, aircraft loss, both SAMs destroyed | `Test_DLS`, `Test_Cinematic`, `Test_DAY` | Source-selected / unverified |
| 04:27–05:02 | Failed airstrike, command dialogue, Ion strike/whiteout | Same Area 4/cinematic owners | Source-selected / unverified |
| 05:02–05:15 | Finale camera, actors, mission-accomplished presentation | Same owners plus generic conversation helper | Source-selected / unverified |

Normal score-screen/next-mission transition, saving and reloading at each
phase, optional routes, and repeated mission teardown remain separate gates.
This video does not show the score screen or the next mission. Its route also
does not establish every possible beacon interaction or alternative trigger.

## Changes and why previous checks failed

Both Vita and host source lists now select the five original files. Shared
callback-default adapters are used where sufficient; Test_RAD and mission08
have scoped adapters preserving original callback arity and defaults. No
replacement mission logic, forced success, authored-data edit or ABI-layout
change was introduced. These additions are not yet compiled or executed.

The prior runtime inventory required cinematic text script names plus
`MX0_MissionStart_DME`. Short intro/saved replays could pass without exercising
the absent Area 2 controller, and the full inventory gate was not required by
the candidate build scripts. An all-text inventory on disk was not a runtime
coverage gate. Earlier 120-frame object counts and later intro replay passes
must not be used as whole-mission evidence.

`tools/check_m13_script_coverage.py` now derives a conservative closure from
all original MX0/DAK_MX0 registrations plus the retained retail-text names in
`tools/m13_reference_coverage.json`, then follows literal attachments. Both
canonical and fast build scripts require source selection and, after linking,
defined factory methods for all 62 scripts. The runtime inventory checker now
requires that full dependency inventory and rejects old partial scan files.
Factories being linked still does not establish their registration execution,
object attachments, callbacks, visuals or successful progression.

## Evidence and remaining work

28 Python tests pass, including cyclic attachment closure, missing helper
owners, rejection of the old incomplete registry, and rejection of undefined
factory symbols. Both build scripts pass shell syntax checks; diff whitespace
checks pass. Read-only M13 archive inventory completes. Existing host and ARM
binaries fail the new factory gate as expected, each missing the same 15.

Retained local receipts:

- `build/dev208-m13-video-baseline-source-coverage.json`
- `build/dev208-m13-video-source-coverage.json`
- `build/dev208-m13-video-mission-inventory.json`
- `build/dev208-m13-video-existing-{host,arm}-coverage.json`
- `build/dev208-m13-video-existing-{host,arm}-symbols.txt`

Target prerequisite remains ARMv7-A little-endian ILP32. Installed compiler
reports `arm-vita-eabi`; the existing ELF is ELF32 ARM hard-float, and installed
vitaGL reports ARMv7/VFP-register arguments. No host-pointer or serialized
layout changes are involved. New object-level ABI checks are still pending.

The user's prior no-build/no-launch restriction remains in force. Once lifted,
compile the original additions and scoped bridges, validate the actual runtime
registry and authored preset attachments, and exercise the complete sequence
above with the restored Area 2 behavior. Reassess freezes and pacing under the
restored workload; earlier measurements of incomplete gameplay are insufficient.
Retain phase saves and matching native recordings, then verify ordinary mission
success and M13-to-M01 transition. No new physical acceptance gate is closed.
