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
