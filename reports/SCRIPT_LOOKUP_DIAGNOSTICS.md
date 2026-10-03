# Script lookup diagnostics — 2026-10-03

The recorder previously reset after loading and player creation. It could not
retain failures in the original threaded level-load path. Source now starts it
before `Pre_Load_Level`, keeps that same session through gameplay, and adds an
opt-in bounded collector for lookup observations. This is uncompiled source,
not a new native candidate or proof that any mission is complete.

## Original owners and collection scope

| Channel | Observation after the original operation | Preserved behavior |
|---|---|---|
| Script factory | Static provider's `ScriptRegistrar::CreateScript` returns a script or null | Original script pointer, construction, IDs, observers and destruction |
| Object | Script command's `GameObjManager::Find_ScriptableGameObj` returns an object or null | Exact numeric ID and original returned object |
| Conversation name | `ConversationMgrClass::Find_Conversation` returns a definition or null | Original active-conversation creation and reference releases |
| Text-file availability | `Text_File_Open` keeps a file after original availability checks or returns null | Original open/check/return behavior and host pointer-token bridge |

The last channel reports availability, not successful opening, parsing or
playback. A found conversation does not prove active-conversation creation or
speech. A returned script/object does not prove the intended actor, callback,
attachment or route. Script creation disabled by the original manager does not
invoke the provider and is outside its attempts counter.

The native runtime checks the existing writable user tree for
`ux0:data/renegade/user/config/script-coverage.flag`. Presence opts the selected
session into collection; the runtime does not create or remove the flag.
Collection is off by default. No device flag was created during this work.
Load context includes preload, loader work, post-load processing, player
creation and remote-player replication before the first gameplay simulation.
Gameplay context names the attempted frame, including an unfinished frame.
Startup before this reset and teardown after shutdown are outside the scope.

## Bounds, threading and identity

The collector uses a lock-free 32-bit atomic gate, a pthread mutex and fixed
storage. Worker hooks never write the recorder, allocate memory, perform file
I/O or call game code while holding the collector mutex. Each channel retains
the first 16 missing samples independently, so object polling cannot consume
the factory or conversation channel's slots. Repeated exact keys accumulate
counts and first/last phase/frame. Other attempts have explicit unretained
counts. ID0 and empty-name misses have separate counters and no samples.

Names retain at most 95 printable ASCII bytes. Truncated or sanitized keys are
marked lossy and never deduplicated, even when their displayed prefixes match.
Samples therefore are not a distinct-content count. Counters saturate at
`UINT32_MAX`; a saturation flag makes them lower bounds. One collector snapshot
is asserted at most 10 KiB; collector state plus the recorder's snapshot copy
remain at most 20 KiB. These are source bounds, not measured runtime memory costs.

Reset and disable synchronize collector state under the mutex. Epoch changes
reject a hook waiting across reset; epoch exhaustion disables further sessions
instead of wrapping. Session reset remains owned by the original lifecycle,
with previous game/loader work quiescent. This instrumentation does not replace
the original thread completion contract or establish loader correctness.

The main thread copies snapshots with `pthread_mutex_trylock`, releases the
lock, then writes the existing flight summary. Busy/error snapshots expose no
stale counts. Load polling flushes at five-second intervals only when opted
in; load-boundary and existing gameplay checkpoints also retain summaries.
Shutdown stops collection before final persistence and normal teardown. The
ready event now uses microseconds rather than the frame-sync millisecond base.

The nested `lookup_diagnostics` schema is version 1; legacy flight fields and
four sidecar filenames remain intact. Candidate, archive and load source remain
owned by the enclosing session summary. Numeric game IDs are explicitly
`int32_t`; telemetry counters use `uint32_t`. No game pointers are serialized,
and original host pointer tokens are preserved. The Vita target remains
little-endian ARMv7-A/Cortex-A9 ILP32; host probes remain separate evidence.

## Analysis and reproduction

`tools/analyze_script_lookups.py` accepts a summary even if loading failed
before the first frame. It validates all four channels, key roles, widths,
phase/frame ordering, capacity, disabled state and unsaturated counter totals.
Unavailable, disabled and legacy-not-recorded states remain distinct. It
does not replace `validate_campaign_flight_bundle.py`, which still rejects
zero-frame timing bundles. Normal runtime-gap analysis includes validated
lookup observations without adding route-completion markers.

```sh
python3 tools/analyze_script_lookups.py \
  build/device-evidence/RETURNED_SESSION/campaign-flight-summary.json \
  --candidate MATCHING_CANDIDATE --archive M13.mix \
  --output build/device-evidence/RETURNED_SESSION/script-lookups.json
python3 -m unittest tools.test_script_lookup_telemetry \
  tools.test_analyze_runtime_gaps tools.test_validate_campaign_flight_bundle
```

Detailed CLI output is restricted to private `build/`; stdout contains counts
only. Captured names are local diagnostic metadata and require review before
sharing. No names, dialogue payloads, parameters, assets, saves or credentials
from returned sessions were added to GitHub.

21 new Python source/analyzer checks pass, including a zero-fuzz application
to a temporary Combat source copy, preserved ownership/host-token checks,
disabled/legacy/busy/error states, bounds, lossy names, saturation, phase
ordering and private-output enforcement. Two runtime-gap regression cases
prove that lookup observations neither invent route markers nor bypass invalid
counters. The broader focused suite passes 157 checks. Four existing flight
source-contract functions also pass. Five incremental-staging contracts pass.

The C++ worker aggregation, reset, capacity and serialization probes are
prepared and selected in the host graph but were not compiled or run. Native
and host source graphs select the collector. The new Combat patch is last in
the ordered staging chain, after existing hash anchors and before final content
comparison; upstream and current staged source were not rewritten. The patch
inventory has 291 ordered patches. The retained Dev197 M01 summary reports
`not_recorded` under the new analyzer; old captures gain no invented lookup
evidence. No build, packaging, launch, device action,
retail modification or native evidence gate occurred. Native mission/runtime
gates remain at 0/10 completed under the existing build/launch hold.

Next: compile these probes and the ARM integration after the hold is lifted;
return matching candidate evidence for Tutorial/M13/M01. Correlate observed
misses with the retained conditional ID, conversation and cinematic leads,
then map semantic route markers to actual original callbacks. Lookup absence
alone is insufficient to classify a port defect or close a content gate.
