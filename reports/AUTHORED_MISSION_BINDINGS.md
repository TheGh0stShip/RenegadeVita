# Authored mission bindings and unresolved ID leads — 2026-10-03

The Tutorial, M13/Scorpion Hunters and M01 sweep now retains script parameters,
spawner instance IDs and cinematic attachment provenance. The previous parser
kept script names and owner tokens but dropped those fields. The new read-only
tool starts from actual serialized attachments and follows typed/literal
dependencies rather than seeding every script with a mission prefix.
No engine code was built or launched, and no retail file was modified.

## Evidence and scope

The three inspected archives match the hashes already recorded in
[campaign reconciliation](CAMPAIGN_SOURCE_MAP_RECONCILIATION.md). The global
objects.ddb SHA-256 is
`98253406ee8e99f86db6593e360bf68424ffb432580354038f08838ee5ec94cb`, also matching
the earlier Tutorial audit. Detailed parameter tables remain private under
`build/dev208-authored-bindings-20261003/`; no retail payloads are published.

| Map | Serialized GameObjs | Spawners | Level bindings | Bindings including reached definitions | Discovered scripts | Cinematic file candidates | Unlocated definition-reference IDs |
|---|---:|---:|---:|---:|---:|---:|---:|
| Tutorial | 74 | 9 | 60 | 72 | 25 | 1 | 11 |
| M13 | 159 | 12 | 100 | 144 | 67 | 18 | 20 |
| M01 | 482 | 16 | 528 | 573 | 275 | 147 | 14 |

All authored parameter vectors decoded with matching name/value counts.
No discovered binding names are absent from the original shipped source
inventory, and no literal created preset is unresolved in this scope.
Definition-reference and object-ID differences remain leads requiring owner,
branch and lifecycle review; they are not automatically port defects.
The reference gate remains incomplete for every map.

These counts differ from earlier prefix-seeded/conservative envelopes because
their roots and reachability rules differ. Neither set proves complete mission
execution. Computed names, engine-created roots, conditional definitions,
runtime-generated IDs and non-literal attachments remain outside complete proof.
The new tool preserves lookup leads from the mission's source even when their
script was not discovered; lack of discovery does not prove unreachability.

## Findings that change the next investigation

- `mx0_a03_nod_ledgedrop.txt` attaches `M08_Petra_C_Helo` at line 65. This is a
  concrete M13 dependency on `mission08.cpp`, beyond the MissionX0 inventory.
  Its `Killed` callback looks up 100389, the Mission 08 Petra C controller ID,
  which is absent from the inspected M13 serialized IDs. Original
  `scriptcommands.cpp:639` rejects a null destination before event delivery.
  This is a cross-map callback requiring runtime/lifecycle assessment; it does
  not justify inventing a M13 controller or changing the shared script.
- M13 lookups of 1200017 occur in the engineers' `KILL` handlers. The source
  controller forwards that event after `KILL_SNIPER`; the only literal sender
  found in MissionX0 is `MX0_Kill_Sniper`, which was not discovered from these
  bindings. Current sniper creation stores dynamic IDs separately. The absent
  static ID therefore remains a branch/lifetime lead, rather than permission
  to alias it to a dynamic sniper. The old 1400035 Humvee lookup is also retained
  from `DAK_MX0_Sec_3_Humvee`, outside this discovered closure.
- M01 retains 18 unlocated literal IDs used by discovered scripts. Examples
  include the guarded Barn buddy lookup 101658 and evacuation-controller IDs
  103380/103381. Source presence and serialized ID absence alone do not prove
  these callbacks execute or affect current progression. The private receipt
  records every caller and source line for targeted review.
- M01's `M01_ConDropZone_JDG` is actually serialized on object 119825. Its
  original source attaches `X01_ConYardDrop.txt` when the player enters. That
  filename remains unresolved in the inspected mission/global archives. This
  strengthens the authored-route evidence for the existing missing-file lead;
  no replacement sequence or filename alias was introduced.

The unlocated definition IDs were also traced to their named serialized fields,
rather than treated as missing soldiers or mission controllers:

| Map | Shell-eject physics references | Muzzle-flash physics references | Sound-twiddler alternatives |
|---|---:|---:|---:|
| Tutorial | 4 | 6 | 1 |
| M13 | 6 | 10 | 4 |
| M01 | 6 | 7 | 1 |

The weapon references are the original `EjectPhysDefID` and
`MuzzleFlashPhysDefID` fields. `WeaponClass::Make_Shell_Eject` at
`Combat/weapons.cpp:1228` and `Do_Firing_Effects` at line 1031 check for a null
definition before creating an effect. The muzzle-flash branch excludes the
player's first-person view; shell ejection also depends on the firing owner,
model and eject bone. This narrows the leads to conditional presentation
effects, while their visual/runtime impact remains unverified.

The other references are one `Death Cries Twiddler` alternative in each map
and three `Small Explosion Sounds Twiddler` alternatives reached in M13.
`wwsaveload/twiddler.cpp:106` randomly selects one alternative and returns the
result of `Find_Definition`; a null result does not select a replacement.
These remain possible missing-effect/audio leads in unchanged retail data,
not permission to invent replacements or remove original random alternatives.
The archive inspection found `objects.ddb` only in `always.dbs`, with no
additional DDB members in the other inspected global `always*` archives.

## Parser corrections and invariants

Original ScriptManager header fields are name 1, parameters 2, observer token
3, owner token 4 and script ID 5. Scriptable definitions retain repeated
name/parameter fields 2/3; spawner definitions use 18/19. Spawner instances use
ID 1, definition ID 3 and repeated script fields 10/11. Pairing follows the
original loaders' parallel-vector ordinals, including empty values. Mismatched
counts retain unmatched values and make the reference gate fail.

All binary IDs/tokens remain explicit unsigned little-endian 32-bit fields,
independent of host LP64/LLP64. Tokens are never treated as host pointers.
Spawner IDs remain a separate namespace: original `Find_Object` searches
ScriptableGameObjs, not the spawner list. Nonzero serialized object IDs are
preserved by original BaseGameObj loading, but metadata presence does not prove
live ScriptableGameObj membership or a successful lookup at a specific time.
Native remains little-endian ARMv7-A ILP32, not AArch64; no ABI gate is closed
by this Python audit.

Source tracing masks comments/strings for numeric call detection and preserves
source lines. It filters provably disabled `#if 0`/`#if 1` alternatives while
retaining unknown preprocessor branches conservatively. This prevents an old
disabled BMG test block from becoming a false duplicate-registration finding.
The resulting original DSP inventory has 1,636 declarations under these rules;
that is source evidence, not a compiled/runtime registration count.

Parameter annotation preserves original names, underscores and misspellings,
splits on commas as the runtime does, and does not invent absent defaults.
Exact preset/script tokens in parameters are followed as conservative leads.
Cinematic collision alternatives retain archive/member/hash and script-source
edges; runtime mount order or executed variants are not inferred.

The cinematic discovery parser also now accepts finite fractional/scientific
time tokens. Original Test_Cinematic parses positive tokens as seconds and
negative tokens as frames at 30 Hz. The legacy receipt field `frame` remains
the raw token value; explicit timing-unit metadata prevents interpreting every
positive token as a frame number. No fractional-time lines were found in the
166 inspected candidates, so this correction broadens discovery without
claiming a newly restored sequence in these maps.

## Reproduction and validation

```sh
python3 -m tools.audit_mission_content_bindings \
  --data /absolute/path/to/user-owned/retail/Data \
  --output-directory build/dev208-authored-bindings-20261003
```

The CLI refuses detailed receipts outside the private build directory. It
generates findings; successful tool execution is not a mission pass. The
three local receipt SHA-256 values are:

| Receipt | SHA-256 |
|---|---|
| m00_tutorial-bindings.json | `f9f463d7cb0dbab226c53c1338a3fa833993782aa875f4dbbc6f7bbe84d14bb7` |
| m13-bindings.json | `fa8cc8510799e5cb945e4854cfaddae417785e8ba76c5f76bb5008562cea4c2d` |
| m01-bindings.json | `03743c33520218128cd621d81c57bcbe0dc248d87254bd695cd564d0e05eccf4` |

55 Python/source checks pass across the binding, level-owner, deep-content,
requested-owner, M13 inventory, script-coverage and provider suites. Controls
cover missing/mismatched parameters, high-bit 32-bit tokens, disabled/orphan
scripts, comments/string false positives, separate ID namespaces, text
collisions, fractional timing, private-output enforcement and an end-to-end
parameter-text-preset-script chain with an unknown-script negative control.
Both build entry points include the new asset-free contracts for future use.
The 32 publication-guard tests, 24-document validator, repository hygiene,
Python/shell syntax and diff checks also pass.

Compiled factory registration, semantic mission milestones, complete routes,
visual/audio correctness and physical performance remain unverified. Continue
branch/lifecycle classification and prepare candidate-bound runtime
lookup evidence while the existing build/launch hold remains active.
