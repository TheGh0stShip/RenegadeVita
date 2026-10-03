# Mission conversation coverage — 2026-10-03

Deeper follow-up: [soldier dialogue and event routes](MISSION_VOICE_ROUTE_COVERAGE.md)
adds weighted preset/serialized option provenance and original event callers.
It narrows global voice leads without claiming missing gameplay or playback.

Follow-up: [direct text, control hints and computed dialogue](MISSION_TEXT_AND_PROMPT_COVERAGE.md)
adds original HUD/objective lookup tracing, eleven missing prompt replacements
and additional absent-name leads from variable/cinematic parameters. Counts
below describe this earlier conversation-record sweep.

The conversation sweep exposed a missing original startup operation: neither
the native bootstrap nor the retained interactive host route loaded
`CONV10.CDB`. The inspected retail database contains 3,606 global conversations.
Both routes now load it through the existing original filesystem, save/load
system and ConversationMgr before Combat initialization. This C++ change is
uncompiled; runtime speech, memory cost and physical correctness remain open.

## Original ownership and startup restoration

Original `Commando/init.cpp:144` names `CONV10.CDB`. Core_Init at lines 921–934
borrows the file through `_TheFileFactory`, loads it with
`SaveLoadSystemClass::Load`, closes it and returns it before Combat initialization.
The port replaces that desktop bootstrap, so selecting the conversation source
files alone did not execute this operation. `CombatManager::Init` calls
`ConversationMgrClass::Initialize`, whose original inline body is empty; it
does not discover or load the global database.

The shared `A31_Interactive_Load_Global_Conversations` helper now performs the
original load through the caller's existing factory. It refuses use with active
conversations, checks open/load success and a nonempty global category, and
returns the borrowed file on each path. Rejected loads clear partial global
records. Native startup additionally probes the database as a required file.
The success threshold is nonempty, not a hard-coded count of 3,606.

Normal Combat shutdown owns conversation teardown. Both bootstraps also release
the loaded lists if startup fails before Combat initialization. Source review
checked FileFactoryList's unconditional return ownership and ConversationMgr's
list/refcount cleanup; no compiled failure or cleanup test has run. Original
global/level categories, conversation IDs, pointer remapping, script names and
chunk formats retain their original owners. No alternate dialogue system or
retail-file rewrite was introduced.

Expected future native breadcrumb, before any mission scripts run:

```text
A3.5 conversations: global database load=1 name=CONV10.CDB records=<count>
```

Matching input hashes, successful load, retained global records after Combat
initialization, ordinary level reload/save behavior and failure cleanup must
still be verified in compiled and native evidence. File existence does not
prove audible speech or visible subtitles.

## Read-only authored records

The scanner starts from every authored conversation in the inspected level
files, plus every record in the global database. These conservative roots
include unused or test records; they do not establish which branches execute.
Map and objects.ddb hashes match the prior
[binding audit](AUTHORED_MISSION_BINDINGS.md).

| Map | Level conversations | Remarks | Orators | Source name leads | Computed conversation calls |
|---|---:|---:|---:|---:|---:|
| Tutorial | 65 | 228 | 129 | 57 | 2 |
| M13 / Scorpion Hunters | 570 | 582 | 577 | 117 | 28 |
| M01 | 89 | 147 | 134 | 94 | 0 |

The global database has 3,606 conversations, 3,605 remarks and 3,606 orators.
No invalid remark/orator ordinal was found in these records. Source name leads
include direct calls and exact known names in tables/helper arguments; a known
string is not proof that a helper uses it. Computed calls remain open even
when some array entries have been located. Unlocated direct names are retained
even when their script is outside discovered bindings.

Two independent `strings.tdb` candidates were found:

| Archive | Translation objects | SHA-256 |
|---|---:|---|
| always.dat | 11,655 | `c2b396d11d4d99f6e83c16b726a1d682883e64eebf7d892de88041696bb922af` |
| always.dbs | 11,678 | `61195381b30605a9dc5278d529cfc7d4a0c01666534519b4f3ece5e6196ce374` |

The `always.dbs:conv10.cdb` SHA-256 is
`0282515b06c81c1a7ff0aab885ca3604621ef7ce9ddee92ab8a61afbae24dcdf`.
Both translation candidates resolve all conversation text IDs in this scope.
The scanner follows each candidate separately and retains every located
archive/loose-file alternative; it does not infer runtime mount precedence.

For each map and each translation candidate, there are **zero unresolved text,
sound-definition or voice-file findings for authored level remarks**. The
global pool has 499 text-reference findings involving 439 distinct unlocated
sound-definition IDs, plus four unlocated voice filenames. Those global
findings are identical across both translation candidates and all three maps.
They require reference/branch investigation; they are not 503 demonstrated
gameplay failures. The four filenames relate to translation IDs 8173–8176.
Detailed filenames, paths and dependency chains remain in private receipts.

## Source names requiring further investigation

- M13: `MX0_MissionStart_DME` calls `MX0_ENGINEER1_048` at MissionX0.cpp:97;
  no such conversation name was located in the inspected global/level records.
  The source path is concrete: `MX0_KillNotify::Killed` sends SNIPER1KILLED
  to controller 1200001 when the player kills the first spawned sniper (line
  1364); its creation attaches MX0_KillNotify at line 126. The
  controller schedules STAY_HERE after three seconds while SniperNotify is
  false (lines 181–191), then calls the unresolved name. Another custom event
  sets SniperNotify true at line 398. Whether the unresolved branch occurs in
  ordinary play remains unverified; original Create_Conversation returns -1
  when the name lookup fails. No alias or replacement was added.
- Tutorial: `MSK_Controller` calls `MSK_MP_STARTUP_DESC` at Mission00.cpp:3872.
  It is outside the inspected Tutorial binding closure and belongs to the
  multiplayer-primer source. Its absence here does not prove unreachability
  or a missing Tutorial line; inspect the Practice data separately.
- M01: `M01_TurretBeach_GDI_Guy_01_JDG` calls
  `M01_TurretBeach_TurnOverTank_Conversation` at Mission01.cpp:8069. The script
  is outside this discovered binding closure. Retain the source/data lead
  until attachment and event conditions are established.

The previously unresolved M01 `X01_ConYardDrop.txt`, callback/object-ID lifetime
leads and conditional effect references remain open in the binding report.
This conversation sweep does not supersede those gaps.

## Decoder invariants and validation

Conversation parsing now follows the actual manager/category/conversation/
orator/remark hierarchy, including legacy inline remarks in original order.
Retail categories require four-byte fields; the existing bounded one-byte
save compatibility remains separate. IDs and old pointer tokens are explicit
little-endian 32-bit values, never actual host pointers. Orator indices are
array ordinals, not orator IDs. Native remains ARMv7-A ILP32, not AArch64;
Python metadata decoding closes no target ABI or hardware gate.

Translation decoding preserves UTF-16LE byte counts and hashes without exporting
subtitle text. Absent sound fields, zero and signed -1 remain distinct.
Audible sound filenames follow the original basename rule. Sound twiddler
alternatives retain duplicate entries and ordinal weights; cycles and missing
definitions/files have separate findings. Source scanning preserves line numbers,
ignores quoted call examples, and handles quotes inside C++ character literals.

```sh
python3 -m tools.audit_mission_conversations \
  --data /absolute/path/to/user-owned/retail/Data \
  --output-directory build/dev208-conversations-20261003
python3 -m unittest tools.test_mission_conversations \
  tools.test_mission_content_bindings tools.test_m13_level_owners \
  tools.test_deep_content_audit tools.test_requested_mission_owner_contract \
  tools.test_m13_mission_inventory tools.test_m13_script_coverage \
  tools.test_script_provider_contract
```

74 focused Python/source tests pass. Controls cover malformed layouts, high-bit
tokens, ordinal ordering, category widths, independent translation candidates,
UTF-16LE errors, sound sentinels, twiddler cycles/weights, archive collisions,
outside-root loose symlinks, computed/literal source names, missing bootstrap
hooks/cleanup and private output enforcement. Both build entry points include
the new asset-free suite for future builds. Shell/Python syntax checks pass.
The 32 publication-guard tests and validation of 24 public documents also pass.

Detailed receipts are restricted to ignored build/. Their SHA-256 values:

| Receipt | SHA-256 |
|---|---|
| m00_tutorial-conversations.json | `2175db9c7a2969149952fc0de4416789c6c283ff7cbbc62943fce13478d2a01d` |
| m13-conversations.json | `1b3b18f96746040fe31f16aca5f602974e51f1db60de3f28eb9dd590fb0390cc` |
| m01-conversations.json | `bb1795cda6797a7ee47dfb3fad323b89069e2b6547d4b6efbf1ee0d1478f0de1` |

The tool always retains incomplete mission closure and no runtime acceptance.
Direct HUD/objective text, animation/viseme assets, active saved conversations,
computed/helper routes, decoding, playback and timing need separate evidence.
No C++ compile, package, install, game launch, device action or retail/save
modification occurred. The build/launch hold remains; native mission/runtime
evidence gates remain 0/10.
