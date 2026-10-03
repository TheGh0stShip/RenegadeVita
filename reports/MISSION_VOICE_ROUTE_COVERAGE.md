# Soldier dialogue and voice-reference coverage — 2026-10-03

The global voice findings now have concrete preset and serialized-record
links for Tutorial, M13 and M01. This is a deeper read-only metadata audit,
not evidence that every linked bark plays or fails. The existing build/launch
hold remains; no C++ compilation, game, emulator or device action occurred.

The [earlier conversation sweep](MISSION_CONVERSATION_COVERAGE.md) found
499 global text-reference findings involving 439 unlocated sound-definition
IDs, plus four unlocated filenames. Authored level conversation remarks all
resolved. This follow-up adds original soldier dialogue tables, which are a
different route into the global conversation pool. Neither result supersedes
the other's scope or establishes complete voice coverage.

## Original owners and parsing

Original SoldierGameObjDef saves/loads DialogList entries in event order;
SoldierGameObj copies those defaults and separately serializes its own list.
DialogueClass stores silence weight plus an ordered list of weighted
conversation-ID options. Say_Dialogue selects an ID and starts a conversation
only when that signed ID is positive. Original ConversationMgr, translation,
WWAudio and definition-manager ownership remains unchanged.

`tools/audit_mission_voice_routes.py` derives chunk IDs, factory IDs and the
20 event ordinals from the original source. It accepts the exact soldier
factory/definition-manager hierarchy and direct dialogue children; reused IDs
in unrelated factories or nested decoys do not become dialogue entries.
Options and duplicate weights retain their original ordinals. Repeated known
scalar writes retain original last-write behavior. Absent fields are marked
as absent with constructor defaults, rather than invented serialized values.
Excess event tables are recorded as ignored by the original bounded loader.

Float32 bit patterns and signed/unsigned 32-bit IDs are explicit little-endian
values. Zero, negative and nonfinite weights remain metadata candidates; no
Python simulation of random selection or ARM floating-point behavior is used.
Zero serialized object IDs retain separate member/offset identities, because
assignment and live lookup membership have not been established. They are
not discarded or counted as one demonstrated live object.

The existing authored-binding scanner now exposes its partial discovered
definition-ID set. That set is tied to the actual always.dbs objects.ddb and
map overlay/member hashes. It is a conservative partial dependency set,
not proof of spawning, execution, probability or absence outside that set.

## Findings across the inspected data

Both strings.tdb candidates produce the same findings in this scope. The
explicit definition scope uses the audited always.dbs objects.ddb plus the
map overlays in the binding audit's order. Other always-archive definition
candidates are inventoried without merging them into one answer or claiming
runtime mount precedence. Global/string candidates remain separate, and
duplicate conversation IDs retain every candidate without choosing a winner.
No conversation-ID collision or unlocated positive conversation ID was found
among these option references.

Across 217 soldier definitions, 8,111 option records reference 2,025 positive
conversation IDs. Of those, 1,231 option records in 92 definitions reference
244 conversations with voice findings. These are repeated references, not
1,231 unique missing sounds. All observed affected option weights are positive.
The affected event tables contain 1,222 DIE options, six IDLE_TO_SEARCH options
and three TAKE_DAMAGE_FROM_ENEMY options. The four previously unlocated voice
filenames do not occur in these soldier-option chains; their wider global
reference/branch questions remain open.

| Map | Soldier definitions in partial binding set | Options in that set | Options with voice findings | Affected conversation IDs |
|---|---:|---:|---:|---:|
| Tutorial | 12 | 335 | 42 | 42 |
| M13 / Scorpion Hunters | 18 | 1,340 | 170 | 113 |
| M01 | 24 | 1,082 | 155 | 127 |

Tutorial's affected partial-set options are all DIE. M13 has 168 DIE options
and two IDLE_TO_SEARCH options. M01 has 154 DIE options and one IDLE_TO_SEARCH
option. A preset in the partial set need not have an identical serialized
instance list or execute any of those events.

| Map | Serialized soldier records | Records with zero ID | Serialized options | Options with voice findings | Affected conversation IDs |
|---|---:|---:|---:|---:|---:|
| Tutorial | 22 | 13 | 1,521 | 196 | 28 |
| M13 | 13 | 9 | 1,267 | 168 | 28 |
| M01 | 152 | 40 | 13,588 | 1,863 | 127 |

All Tutorial/M13 affected serialized options are DIE. M01 has 1,862 DIE
options and one IDLE_TO_SEARCH option. Its latter record is object 106050,
preset M01_Capt_Duncan, conversation ID 103104, text ID 10810 and sound ID
163842970, which is not located in the inspected definition scope. This is
a concrete authored link requiring trigger/actor/voice evidence; it is not
a confirmed native regression, missing dialogue replacement or alias request.

## Event callers and sound sentinels

The simple-expression source scan finds 12 Say_Dialogue call sites in staged
Combat C++: 11 literal event arguments and one unresolved variable argument.
Original SoldierObserver calls IDLE_TO_SEARCH when appropriate AI state
changes occur. The canonical Combat search finds no direct DIE event caller.
The original soldier death path instead resolves DeathSoundPresetID, falls
back to GlobalSettings' death sound, stops current speech and uses
Create_Instant_Sound. Its later variable dialogue_id call is retained as
unresolved by this narrow scanner; manual source inspection shows it receives
damage-from-friend/enemy values in that function. This is source evidence,
not a whole-program proof that every DIE-table reference is unreachable.

The metadata also preserves an original API distinction: soldier speech
casts a translation sound ID to signed 32-bit and attempts playback only
when positive. Get_Conversation_Time tests an unsigned ID against zero, so
negative/default-minus-one bit patterns can still produce duration queries.
Such a query is not counted as missing speech. Absent, explicit zero,
positive and negative serialized states remain separate. No source behavior
or retail sentinel was normalized.

## Validation and retained evidence

All 22 new asset-free counterexamples and 220 focused Python/source checks
pass. Controls include factory/chunk scope, instance overrides, zero IDs,
duplicate options and conversation candidates, event limits, malformed widths,
nonfinite weights, sound sentinels, unknown callers, database identity and
private output restrictions. Both future build entry points select the suite;
their shell syntax passes without execution.

The 32 publication guards, six future-build entry source contracts and
validation of 24 public documents pass. State counts match the fresh receipts.

```sh
python3 -m tools.audit_mission_voice_routes \
  --data /absolute/path/to/user-owned/retail/Data \
  --output-directory build/dev208-voice-routes-20261003
python3 -m unittest tools.test_mission_voice_routes
```

Detailed tables and filenames remain private under ignored build/. Receipt
hashes, in Tutorial/M13/M01 order:

| Private receipt | SHA-256 |
|---|---|
| m00_tutorial-voice-routes.json | `9346803791ee3860624379d88a227f26a821693029dd7f7d2a3d295b9db21a72` |
| m13-voice-routes.json | `43362803832d4c2a939b5dd6ab1813112692a4a2b46919011d0b7e131fb82118` |
| m01-voice-routes.json | `c472adb4263dbaedace3104d53c39e5d6bec2fab3c46e2a7f7aef32706513866` |

Native remains little-endian ARMv7-A/Cortex-A9 ARM/Thumb ILP32, not AArch64.
Earlier read-only arm-vita-eabi/pthread inspection reported v7 and VFP-register
arguments; this metadata work closes no ABI, decode, playback or physical gate.
Native mission/runtime gates remain 0/10. Retail files remain unchanged.

Next: trace the remaining conditional source/dialogue routes and command
behavior, preserving the four cinematic slot leads, source-count discrepancies
and wider global voice findings. Candidate-bound speech, death-preset,
AI-state, duration, input-lock and complete mission evidence still require
an authorized compiled/runtime cycle after the existing hold.
