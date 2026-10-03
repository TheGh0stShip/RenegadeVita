# Cinematic callers and custom-event routing — 2026-10-03

Primary-death source review distinguishes notification and parser reentrancy.
The helper sets its saved custom_sent latch before dispatch in both Killed and
Destroyed. The controller sets PrimaryKilled before calling Parse_Commands;
that prevents repeated primary notifications, but is not a general parser
entry guard. Zero-delay Send_Custom_Event dispatch is synchronous. An outer
parser invokes each command before removing its current head, so nested
callbacks can encounter the same list. A reachable same-controller chain is
not established by these facts alone and remains a runtime/source-flow lead.
Remove_Head_Control_Line guards null and advances before freeing, so a nested
pass that drains the list does not by itself establish a double free. Likewise,
Destroy_Object only marks deletion pending; immediate destruction must not be
invented as a trigger. No parser scheduling or authored command changes were
made. A source contract retains these distinctions for future investigation.

The read-only tracer now joins normal Set_Primary and Attach_Script records by
their possible creation producers, retaining before/after ordering and explicit
live-identity uncertainty. Reanalysis of the retained authored chronology
receipts found1/10/10 primary routes for Tutorial/M13/M01. Only M13 has an
attachment after primary selection sharing a creation candidate: its helicopter
helper has no direct Apply_Damage call in Created. M01's hovercraft helper is
attached before primary selection. Thus this narrow join finds no immediate
Created-damage attachment on an already-selected primary candidate. Later
callbacks, external actor references, failed/reused creations, primary-death
tails and actual reentrant delivery remain open. Input receipt hashes and
joined metadata stay private in
`build/cinematic-primary-actor-routes-20261003.json`; no retail files changed.

The deeper Tutorial/M13/M01 sweep retains 1,140 original source event-call
sites and 3,231 authored/unbound binding contexts. No resolved event type in
this inspected scope is a cinematic slot-fill candidate. Five contexts remain
unresolved by the narrow parser. This is source/data evidence, not proof that
no external writer exists or that the four prior slot leads are harmless.

The read-only tool is `tools/audit_mission_event_routes.py`. It includes all
scripts in each map's mission source unit, discovered helpers, definition and
level parameters, and normal/primary-death cinematic attachment candidates.
Unbound mission scripts remain visible. Tail attachments never establish a
normal-timeline actor or slot lifetime.

## Source values and caller scope

Numeric values are derived from original enum initializers/increments and
single numeric/alias defines. Index comments are not values:

- M00_SEND_OBJECT_ID is **9035**, not the nearby comment's index 35.
- M00_CUSTOM_CINEMATIC_PRIMARY_KILLED is 9023.
- M00_CUSTOM_CINEMATIC_SET_SLOT is 10000; the original handler has 40 slots.

The slot handler subtracts 10000 from the custom **type**, accepts indices
below 40, and writes the custom **parameter** only when that slot's existing
numeric object ID is zero. This means a parameter such as 11 or 13 sent with
M00_SEND_OBJECT_ID is not a cinematic slot-fill message.

Quoted header discovery follows the actual source links, including Test_RAD's
MissionX0.h and M01's Mission1.h. Canonical filename case is retained. Unknown
preprocessor alternatives, conflicts, unsupported expressions, other headers
and C++ dataflow remain outside the grammar. Same-script assignments supply
possible values only; shadowing and cross-callback writes keep them unresolved.
No numeric ID is treated as a pointer, and overflowing int32 values stay open.

| Map | Source event sites | Binding contexts | Resolved slot-fill candidates | Unresolved type contexts | Cinematic caller sites | Text custom events |
|---|---:|---:|---:|---:|---:|---:|
| Tutorial | 147 | 1,834 | 0 | 1 | 1 | 0 |
| M13 / Scorpion Hunters | 242 | 508 | 0 | 3 | 23 | 7 |
| M01 | 751 | 889 | 0 | 1 | 42 | 3 |

Source sites and authored contexts are different counts: multiple instructor
zones can configure one original callback. Caller sites include dynamic
filename expressions. Their presence does not prove target identity, controller
creation or execution. All ten inspected cinematic-text custom events have
types outside the slot-fill window; their targets and delivery remain unproved.

The five unresolved parser contexts are Test_Cinematic's parsed `type` in
each map, plus two MX0_MissionStart_DME forwarding calls. Manual source review
finds the latter guarded by types 223 and 224, below the slot-fill range.
The text-event check resolves the inspected control-file candidates only;
uninspected/computed files, re-entrant events and restored slots remain open.
No claim of complete event-graph closure follows from these observations.

The three callers relevant to the four slot leads are:

| Original source caller | Control file | Source observation |
|---|---|---|
| MissionX0.cpp:71, MX0_MissionStart_DME::Created | X00_Intro.txt | Creates an Invisible_Object and attaches the cinematic; no direct caller slot fill |
| Mission01.cpp:21723, M01_Base_GDI_Minigunner_JDG::Custom | X01D_C130Troopdrop.txt | Creates/faces a controller and attaches the cinematic; no direct caller slot fill |
| Mission01.cpp:1573, M01_Mission_Controller_JDG::Custom | X1Z_Finale.txt | Creates a controller and attaches the cinematic; schedules original completion separately |

Multiple same-script controller assignments are retained as candidates; they
are not mistaken for a single proved object. The prior normal slot leads at
x00_intro:203/455, x01d_c130troopdrop:39 and x1z_finale:139 remain open.
The explicit SET_SLOT sender search across original DSP sources finds two M10
calls using type 10003. Those are outside these maps and do not establish an
external fill for the four leads. No aliases, actors or retail edits were added.

## Original callback and actor lifetime rules

Original Attach_Script creates the script, assigns parameters and calls
Add_Observer. Add_Observer inserts it and synchronously calls Created when
observers are active. Definition scripts are initially inserted without this
call; Start_Observers supplies their original creation callbacks. A successful
Create_Object calls Start_Observers before returning to its caller.

Original Send_Custom_Event invokes current observers synchronously when delay
is at or below zero. A positive delay creates the original custom timer.
Test_Cinematic::Created zeroes its slots before loading/parsing the file.
Consequently, a nested creation/custom callback can interleave with cinematic
dispatch. A source caller appearing after Attach_Script cannot be assumed to
have filled slots before the cinematic's first synchronous parsing pass.

Death, deletion and conversation lifetime are separate. Find_ScriptableGameObj
searches object-list membership and numeric ID; it does not filter by soldier
health. Soldier death enters the original death state, with later corpse
destruction/removal paths. ActiveConversation::Think interrupts a conversation
whose soldier orator is dead or destroyed. An ID that remains findable does
not therefore prove that its speaker will deliver a line.

This narrows the M13 HIT6 investigation: its original kill helper applies
damage in Created before the later generic-conversation attachment. Creation,
damage modifiers, armor/warhead rules, death state, script attachment and voice
delivery still need evidence. The absent conversation candidate is not a
newly proved audible omission. The primary-death helper can synchronously send
its callback while Killed/Destroyed runs; death-tail slot snapshots stay unknown.

These are retained original-source rules. No game callback, queue, damage
behavior or retail content was changed in this unit.

## Identity and validation

Before using authored parameter contexts, the tool rechecks the current
objects.ddb hash inside always.dbs, the mission archive hash, and every reached
cinematic member hash. A changed/missing definition identity now invalidates
the analysis. This closes a validation gap in the new event audit: a matching
mission archive alone cannot validate definition-attached parameters.
Original owner/header hashes and binding-receipt identity accompany each
private output. Retail payloads and detailed parameter tables stay unpublished.

| Private receipt | SHA-256 |
|---|---|
| m00_tutorial-event-routes.json | `564156d57a2e30748bef236e650380b0a8478c3fdb6fab6b574c7800f5be7797` |
| m13-event-routes.json | `991a7e008192d5f97ae477a00cb30c1ee589883cd9e591fd0d14ec0df14c4743` |
| m01-event-routes.json | `40ff3fd68357bb140f28703126578dc83f4a2ced09403d0833829e5355114282` |

```sh
python3 -m tools.audit_mission_event_routes \
  --data /absolute/path/to/user-owned/retail/Data \
  --bindings-directory build/dev208-authored-bindings-20261003 \
  --output-directory build/dev208-event-routes-20261003
python3 -m unittest tools.test_mission_event_routes
```

All 21 new asset-free counterexamples and the 191-check focused source/Python
suite pass. Both future build entry points select the new suite. No C++ was
compiled, no build script was executed and no game/device was launched or
modified. Native remains little-endian ARMv7-A/Cortex-A9 ARM/Thumb ILP32;
read-only toolchain/pthread inspection reports ARMv7 and VFP-register arguments.
Source/LP64 host analysis proves neither target execution nor physical behavior.
Native mission/runtime gates remain 0/10 under the existing build/launch hold.

Next: retain candidate-bound command/slot/actor-lifetime evidence after the
hold, while continuing global voice, unresolved content and command behavior
investigation. See [slot lifetimes](CINEMATIC_SLOT_LIFETIMES.md) and the
[full mission review](MISSION_RESEARCH_REVIEW.md) for the unchanged open scope.
