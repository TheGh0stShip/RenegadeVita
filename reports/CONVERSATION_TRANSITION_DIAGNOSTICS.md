# Original conversation transition diagnostics

The existing script-coverage opt-in now collects scheduled remarks and owner
completion transitions from original ActiveConversation code. Collection is
disabled by default. Numeric instance token, active conversation ID, action
ID, remark index, text ID, duration and completion reason remain distinct.
No dialogue text, audio payload, pointer or retail file is exported.

Producers enqueue into a mutex-protected fixed128-record queue. They never
access the flight recorder. Its owner thread drains with trylock each frame,
on mission snapshots and at flush. Queue overflow has a saturating explicit
count. Original timestamps are retained; event sequence describes insertion
into the flight recorder, not chronological order across all categories.
Frame0 means unavailable for these transitions. Recorder ring eviction and
queue loss prevent absence from proving an event never happened.

A native-only diagnostic member receives a process-local64-bit token during
construction. The counter is protected by the queue mutex, survives recorder
resets and returns unknown0 on exhaustion. The token is absent from original
save/load chunks; loading constructs a new instance even when an engine ID is
restored. Tokens have no identity across application launches. Source changes
are staged through a SHA-anchored zero-fuzz patch; upstream remains pristine.

Owner completion is recorded before monitor observers are called. It proves
neither monitor registration nor callback delivery. Existing recorder reset
and shutdown require quiescent old mission work; queue locking does not make
every flight-recorder method thread-safe. Fatal snapshots can skip a busy queue.
Six focused source checks pass, including zero-fuzz replay, numeric identity,
save exclusion, mutex/owner boundaries, overflow and default opt-in. C++
concurrency, native layout, performance and actual callback outcomes remain
unverified under the build/launch hold. Native mission/runtime gates remain0/10.

The existing C++ recorder regression now includes concurrent producers sharing
engine/action IDs but using different instance tokens, exact queue capacity,
overflow count, completion after draining, default-disabled collection and
token survival across resets. These cases are prepared only: they have not
been compiled or run. Source checks cannot establish their runtime result.

Offline assessment is available through
`python3 tools/analyze_conversation_transitions.py <events.jsonl>`.
Validate the complete matching flight bundle first with the existing bundle
validator. Supply one process capture; the reader does not infer launch or
session identity from reused candidate names. It preserves transitions rather
than pairing through missing reset/load evidence. Nonpositive remark timers,
unknown instance tokens, nonfinite timers and explicit queue loss remain
observations. Eight synthetic counterexamples pass; no current runtime capture
has been assessed with the new collector. Detailed output stays in private
candidate evidence, not a public asset or dialogue report.
