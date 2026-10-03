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
