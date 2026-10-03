# Direct text, control prompts and computed dialogue — 2026-10-03

The follow-up sweep found eleven missing English Vita control hints: all four
M13 HUD help IDs and seven additional M01 IDs. They now use the existing
presentation adapter and current input mappings. The C++ change and extended
compiled hint test remain uncompiled/unrun under the build/launch hold.

The new read-only scanner also finds dialogue names supplied by variables,
arrays and cinematic script parameters. The previous conversation audit kept
known table strings as leads, which could hide absent entries. The expanded
discovery retains unknown names and provenance; it does not claim C++ dataflow,
branch reachability or mission completion.

## Control hint restoration

| Original IDs | Vita hint behavior |
|---|---|
| MX0_HELPTEXT_01 / 8576 | Right stick to look |
| MX0_HELPTEXT_02 / 8577 | Left stick to move |
| MX0_HELPTEXT_03 / 8578 | Start to open EVA |
| MX0_HELPTEXT_04 / 8579 | R to fire |
| M01 DSGN0516 / 8273 | Start, then EVA Objectives |
| M01 DSGN0517 / 8274 | Start, then EVA Map |
| M01 DSGN0520 / 8277 | D-pad Left/Right to cycle weapons |
| M01 DSGN0521 / 8279 | L to toggle the sniper scope |
| M01 DSGN0522 / 8280 | D-pad Up/Down to zoom |
| M01 DSGN0523 / 8281 | R to place C4 |
| M01 DSGN0524 / 8282 | L to detonate Remote C4 |

Source review matched the mappings in renegade_directinput.cpp and
A31_Interactive_Configure_Original_Input. Start requests the original outer
EVA presenter; Objectives and Map are menu selections, not newly invented
direct hotkeys. Original scripts, trigger conditions, HUD ownership, sounds
and retail files remain unchanged. Other languages retain TranslateDB data.
The adapter covers short HUD hints and the existing in-memory English caption
replacement route; voiced PC instructions remain a separate audio/timing gap.
No claim that English control guidance is exhaustive or physically validated.

## Direct text and objective media

Roots are actual discovered bindings plus the map's original mission source.
Unbound mission-file scripts remain conservative leads, including MSK primer
scripts inside Mission00.cpp. They are not proved unreachable or active.

| Map | Direct text argument references | Unique non-clear text IDs | Objective texture calls | Missing text IDs in either TDB candidate | Missing texture candidates |
|---|---:|---:|---:|---:|---:|
| Tutorial | 98 | 54 | 6 | 0 | 0 |
| M13 / Scorpion Hunters | 5 | 5 | 0 | 0 | 0 |
| M01 | 76 | 54 | 16 | 0 | 0 |

All source text expressions in this scope resolve. Text arguments are selected
by the original command signature: objective IDs remain distinct from short,
long and HUD text IDs. Set_HUD_Help_Text(0) is a clear operation. Direct HUD
text does not automatically play the translation object's voice sound.

The objective texture names use `.tga` in scripts but the located retail files
use `.dds`. Original DDSFileClass replaces the last three filename characters,
and the native DX8 boundary attempts DDS before its Targa fallback. The scanner
now records those original lookup alternatives with archive/member/hash and
lookup role. This avoids reporting all 18 distinct image names as missing.
M01 also references `POG_M02_2_01`, a real cross-mission image in always.dat.
Presence does not prove texture decoding or visible HUD rendering.

Tutorial's six objectives store the same description-sound name, with no exact
definition-name match located. Original ObjectiveManager stores this field;
the inspected current sources do not consume it for playback. It is retained
as a stored-field lead, not declared a missing spoken objective or renamed.
Input archive/database hashes match
[conversation coverage](MISSION_CONVERSATION_COVERAGE.md).

## Additional dialogue leads

M13 has 28 computed conversation calls. Candidate discovery now includes 207
same-script assignment leads and 27 cinematic parameter leads, plus 12 direct
literal arguments. All computed calls have at least one candidate, but none
is thereby established as fully resolved or executed.

- `MX0_A02_ACTOR` assigns `MX0_A02_SPEECH_WRONGWAY_01` through `_03` in
  Test_RAD.cpp:2884/2889/2894. These names are absent from the inspected
  global/M13 conversation records. The source chain starts a wrong-way timer
  at line 854, cycles registered unit indices 2–4, and sends the wrong-way
  custom event at line 1230. Actor logic additionally checks player distance
  and active_actor. This is a conditional source/data gap, not new runtime
  failure evidence or authorization to fabricate dialogue.
- The same helper initializes `MX0_A02_PREAMB_01` at line 2598 as a default
  name before its speech switch. It is also absent; validity/reachability of
  default speech IDs needs separate investigation.
- M13's reached `x00_intro.txt` attaches M00_Generic_Conv_DME with
  `MX0_GDITROOPER4_HIT6` at line 468, an unlocated conversation name. The
  reference is an active parsed control-file line; object-slot lifetime and
  execution remain unverified. The generic helper's other cinematic values
  resolve, including intro and finale lines. Commented attachments are excluded.
- The prior `MX0_ENGINEER1_048` sniper/STAY_HERE lead remains open.
- Tutorial's MSK source yields 24 unlocated nonempty primer names and an empty
  default candidate. Both callers are outside the inspected Tutorial binding
  closure. Do not describe those as 25 demonstrated Tutorial defects or import
  primer data without confirming the intended map/route.
- M01 retains the unbound TurnOverTank conversation lead from the prior report.

The global 439 sound-definition IDs/four voice-file leads, missing M01 ConYard
cinematic, and callback/object-ID lifetimes remain open. This sweep does not
close those findings or the build/launch hold.

## Discovery rules and validation

The scanner masks comments and quoted call examples while preserving offsets,
splits nested arguments, resolves a limited numeric/alias grammar without
executing source, and follows same-script literal assignments/aliases/arrays.
It retains all authored parameter values, matching names case-insensitively
without erasing underscores or inventing missing defaults. Reached cinematic
variants keep parameter values, source line, slot, time token and matching
hash. Narrow adjacent literals and C-string termination are handled;
unsupported encodings/escapes remain unresolved. Shadowing, index ranges,
function returns, member expressions, formatting and unknown branches need
separate evidence. Finding a candidate never clears computed-call uncertainty.
Receipts also record SHA-256 identities for the original string-ID header and
the current English hint adapter.

IDs preserve original 32-bit semantics on LP64/LLP64 hosts. Native remains
little-endian ARMv7-A ILP32; this Python audit proves no target ABI, linked code
or physical behavior. Detailed metadata stays in ignored build/, without
subtitle or audio payloads.

```sh
python3 -m tools.audit_mission_text_routes \
  --data /absolute/path/to/user-owned/retail/Data \
  --output-directory build/dev208-text-routes-20261003
python3 -m unittest tools.test_mission_text_routes tools.test_mission_conversations \
  tools.test_mission_content_bindings tools.test_m13_level_owners \
  tools.test_deep_content_audit tools.test_requested_mission_owner_contract \
  tools.test_m13_mission_inventory tools.test_m13_script_coverage \
  tools.test_script_provider_contract
```

93 focused Python/source tests pass. New counterexamples cover nested/quoted
commas, malformed delimiters, aliases/cycles/shadowing, absent array names,
exact parameter binding origins, numeric IDs/sentinels, literal concatenation,
unsupported escapes, original DDS/Targa alternatives, cinematic comments/
commas/hash changes, separate TDB candidates and private output enforcement.
The compiled Vita hint test is extended but was not run. Both build entry
points select the new asset-free suite for future builds. Shell/Python syntax
and diff checks pass; 32 publication guards and 24-document validation pass.

| Private receipt | SHA-256 |
|---|---|
| m00_tutorial-text-routes.json | `4da99646f9ca69cb59d5a92072a0da3110e34b7a68886eeaa0043971967b94e9` |
| m13-text-routes.json | `8c6aac774b868a38956b16191a08a17e9b26c225e07238f149210a03c3650aa4` |
| m01-text-routes.json | `d71d3c9d876be1f203f5d382fbfde0b1fc02ded9e2ea3d1416de6c0ec0810e10` |

No C++ build, package, installation, launch, device action or retail/save
modification occurred. All native mission/runtime evidence gates remain open.
