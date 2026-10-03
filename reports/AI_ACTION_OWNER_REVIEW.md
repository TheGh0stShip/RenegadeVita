# AI hibernation and action callback ownership

2026-10-03 source review; no compilation, launch or device action. Native
mission/runtime gates remain0/10.

Original GameObjManager skips ordinary Think for hibernating objects; its
Post_Think also requires eligibility and respects cinematic freeze. SmartGameObj
Begin_Hibernation resets the physical controller, removes its logical-sound
listener from the sound scene and forwards to the current action. End_Hibernation
re-adds the listener and forwards wake-up to the action. Movement action code
sets FirstCall and returns its PathSolver on hibernation. Sleeping actors therefore
do not merely consume fewer frames: listener participation and path lifetime
change through original owners. Preserve these transitions.

Original ActionClass::Request_Action accepts equal or greater priority. Replacing
an existing action notifies its former observer with ACTION_COMPLETE_LOW_PRIORITY.
A rejected lower-priority request notifies the requesting observer with the same
reason, deletes the proposed action and returns false. A LOW_PRIORITY callback
alone does not distinguish replacement from rejection; it is not a generic
missing-action failure. Done clears priority, shuts down/defer-deletes the action
code, then notifies the observer.

Notify_Completed uses numeric ObserverID, ActionID and reason. ObserverID0 skips
notification. Other IDs are matched against the object's current observer list;
each match receives Action_Complete synchronously. An absent observer has no
general diagnostic in the inspected path. Existing native request/completion
logs are bounded to Logan object400005, not every mission actor. Timer expiry
miss observations and conversation observer attempts are separate mechanisms
and do not establish action delivery. This is a coverage gap, not evidence
that an absent observer occurs in any particular mission.

The native M13 Area3 diagnostic setup explicitly changes camera/freeze/control,
position and script events. Its arming path requires the development-checkpoint
build, M13 source, a valid explicit request file and successful request removal.
The call is additionally under the non-demo development guard. It is an opt-in
diagnostic setup, not ordinary mission wake-up or natural Area3 progression
evidence. Runs using it cannot prove the preceding conversation/zone chain.
No diagnostic request was created or consumed during this review.

The absent-observer branch now has an opt-in source hook, uncompiled. A
SHA-anchored staging patch marks matches before original callbacks and queues a
miss only when no callback matched. ObserverID0 still skips notification. It
does not read actors after delivered callbacks or change Request_Action.
The existing mutex-protected128-record queue exports category `script_action`,
event `observer_absent_at_completion`, with signed32 object/observer/action/reason
IDs. Owner-thread draining handles this kind before conversation monitor-name
indexing. Queue overflow remains shared with conversation/timer events and
cannot be attributed to action alone. Collection is off by default.

Eleven focused source checks pass, including zero-fuzz, zero-offset patch replay
and original request-action body preservation. They do not compile or execute
the collector. Offline `analyze_conversation_transitions` now interprets the
action category into separate `action_misses`, with strict bounded numeric
parsing and shared capture identity checks. Five additional counterexamples
cover malformed/oversized fields, all signed32 widths, mixed identities,
unknown event names and repeated IDs without pairing or deduplication.
Missing observers do not themselves establish
a mission failure. Staging receipt intentionally remains stale under the hold.

The C++ encoding fixture includes a prepared action-record case; it has not
been compiled or run. Both future build entry points select the source hook
checks; neither entry point was executed. The offline parser is for a single
process capture and does not validate the whole flight bundle: run the existing
bundle identity/sequence validator separately before interpreting events.
Shared overflow is not attributable to this event type.

Next verify native collection and add request-outcome coverage, preserving
priority and synchronous callback semantics.
Runtime evidence must distinguish scheduling, request acceptance, movement/
attack execution, completion reason, observer delivery and subsequent mission
event. Native AI/pathfinding, logical-sound stimuli and area wake/sleep behavior
remain unverified under the build/launch hold.

## Action request outcome and M13 engineer query

Original script Action_Goto returns void and discards ActionClass::Goto's bool.
Get_Action_Params copies current stored parameters and resolves object references;
it does not certify action execution. Request_Action installs accepted parameters
and initializes the new code before notifying the previous observer synchronously.
That callback precedes the true return. Acceptance therefore cannot establish
that the same action remains current afterward; no concrete failing reentrant
chain is claimed. Rejection also notifies synchronously before deleting the
proposed code. Preserve this order when adding future request observations.

Original Is_Performing_Pathfind_Action initializes retval=false and calls
Is_Busy without assigning its result. Its normal return is always false in the
inspected original and retained staged implementation. The original command
table selects this function. This is an existing source defect, not a newly
introduced platform omission. Preserving it is the project's compatibility
decision; the source does not establish designer intent.

MissionX0 has two calls, in MX0_Engineer1 and MX0_Engineer2 Action_Complete.
Both require ENGINEER_GOTO, a different current action ID and the negated query;
the first additionally requires LOW_PRIORITY, the second allows LOW_PRIORITY or
PATH_BAD_DEST. They schedule RESEND_GOTO after five seconds. The constant false
query makes its negation pass; it does not remove the other conditions. This
review does not establish the full escort recovery mechanism or actual timer,
pathfinding and observer delivery. Tutorial and M01 have no direct calls to this
query in their inspected mission units. No behavior correction was applied.

Private source identities: `build/action-request-and-engineer-query-20261003.json`.
Source inspection only; no build, launch or new native acceptance.

## Tutorial startup and input-follow discovery

The binding audit previously omitted CombatManager's serialized start/respawn
script fields. These are consumed by original cGod lifecycle code, independently
of placed-object or preset script attachments. The scanner now follows the
CombatSaveLoad subsystem, direct CombatManager owner and direct variable chunk;
it rejects ambiguous owners/variables, duplicate fields and malformed names.
Empty names remain no attachment. Pointer tokens or a placed owner are not
invented, and absent parameter strings remain unknown.

A fresh Tutorial/M13/M01 scan retains original source and archive/member/global
definition hashes. Tutorial gains MTU_Commando_Startup and MTU_Commando in the
discovered dependency closure, increasing25 to27 scripts. The original startup
Created callback attaches MTU_Commando. No nonempty additional Combat start or
respawn root was found for M13 or M01. Detailed receipts remain private in
`build/dev208-combat-script-roots-20261003/`; this is not runtime registration
or reachability proof. Existing missing definition/media/object-ID leads remain
open; a larger discovered closure does not establish mission completeness.

Original cGod::Think creates the campaign commando and attaches Get_Start_Script.
The native runtime calls that owner for a fresh local player. MTU_Commando's
control-enable event re-enables Smart control and requests Action_Follow_Input
at priority100. That original action reads Input functions into ControlClass;
vehicle turn functions inherit movement/turn values in original Input. The
vehicle copies its non-transitioning driver's controls and retains original
target steering/gunner handling. Control generation and control application are
separate owners; script registration alone proves neither. No replacement input
action or vehicle controller was introduced.

Thirty-seven focused Python checks pass, including valid start/respawn roots,
unanchored bytes, empty names and ambiguous/malformed metadata counterexamples.
Native instructor control restoration, vehicle entry/exit, action acceptance and
save/load during training remain unverified. No build, launch or retail mutation.
# Logical hearing and M01 prisoner progression — 2026-10-03

Source-only diagnostics now record the two original detention stimulus types at
configuration before scene insertion and SmartGameObj hearing-callback entry.
The numeric payload retains sound ID, type, receiver/creator IDs and observer
activity. Hooks run before original scene insertion/observer callbacks, with no
post-callback object inspection. Ordinary combat sound types are filtered out.
The existing opt-in, mutex-protected128-entry queue, owner-thread drain and
saturating overflow counter are reused. Queue/ring loss prevents absence claims.
No save fields or original listener scheduling change. Both source files have
SHA-anchored zero-fuzz staging registration;302 patches are registered. Nine
focused source checks pass; C++ compilation and native delivery remain open.
Entry events never prove prisoner callback completion.

A focused ordered replay from pristine upstream also passes for scriptcommands,
smartgameobj and Test_Cinematic:18 selected patches, three verified late input
SHA-256 anchors and zero fuzz. The replay reproduces the staging-owned trailing
newline transformation in temporary files. Historical patch offsets are retained
in the private receipt; the new logical hooks and primary-ID buffer patch apply
without offsets. This establishes composition for these three files only, not
full staging or compilation. Active staging and its receipt remain unchanged.
Receipt: `build/logical-diagnostic-source-patch-chain-20261003.json`.

The offline analyzer now retains typed logical stimulus records separately from
conversation, timer and action records. It checks bounded signed32-bit fields,
the two focused event types, boolean observer activity, creation-record shape
and shared candidate/archive/load identity. Repeated IDs are not paired or
deduplicated. Unknown event names remain findings, and inactive observers are
reported at hearing entry without inferring a failed mission. Shared overflow
remains unattributed; resets, loads, ring eviction and opt-out prevent absence
claims. Forty-two consumer/source/bundle checks pass. No synthetic fixture is
treated as a native callback or prisoner-progression result.

Original Create_Logical_Sound creates a single-shot scene stimulus with creator
reference, type, position and radius; it does not require audible playback.
Original WWAudio collects logical sounds on its primary sound page. SoundScene
processes up to four queued listeners per frame and performs scaled-radius
checks before notification. SmartGameObj converts the event to CombatSound and
notifies all observers when observers are active; SoldierObserver separately
applies hibernation and innate-hearing conditions. LogicalSound, LogicalListener
and SoundScene are selected in the native original-source list. Existing removal
lifetime corrections remain distinct from proving callback delivery.

M01's three direct logical-sound calls use mission event types400004/400005 for
detention gate/SAM state. GDI and civilian prisoner Sound_Heard handlers consume
them, update gate/SAM flags, reset actions and issue evacuation approach moves.
These are mission callbacks, not audible sound IDs or only innate reactions.
No substitution with audible playback or a generic AI state change is valid.
The private source-hash/binding receipt is
`build/m01-prisoner-logical-stimulus-owner-20261003.json`. Eventual listener
delivery, radius/position, single-shot lifetime, action completion and full
rescue progression remain native runtime gates. No build/launch occurred.
