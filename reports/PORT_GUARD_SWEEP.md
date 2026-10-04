# S1 port guards and stubs — inventory in progress

2026-10-04 Dev222 refresh:3,597 source records retain51 stubs, one patched,
two replaced boundaries, six disabled guards and3,537 unknown. The312-entry
stage registry includes the three host-only Mission03 pointer exchanges;
native preprocessing remains unchanged. Reviewed bodies and caller hashes
reconcile after checking the prior Load_Data capacity-only delta. Seventy-three
focused checks and485 fast contracts pass; this does not close S1 classification
or native acceptance. See [script cluster](SCRIPT_LAYER_SWEEP.md).

This is a partial source inventory, not a completed sweep or runtime acceptance.
It establishes explicit denominators before further behavior fixes. The current
source contains 3,574 records with 51 fallback/diagnostic functions reviewed as
`stubbed_or_noop`, 1 original light-state method as `original_patched`,
1 capability constructor as `boundary_replaced`, 6
guards as `disabled_by_port_guard`, and 3,515
records still `unknown`. All statuses reconcile to the total.

| Inventory kind | Records |
| --- | ---: |
| Changed patch guards, including removals | 519 |
| Current port/staged source guards | 840 |
| Port function and lambda definitions | 1,656 |
| Port macro definitions | 486 |
| Syntax parse uncertainties | 69 |
| Linker wrapper references | 4 |

The 312 patch files and 309 literal staging references are separate inventories.
Three files have no staging reference; they remain visible without being called
retail exclusions. Historical hunk coordinates are not current staged line
proof. Comments, strings, raw strings and continued comments are masked while
retaining physical positions. Native `__vita__` guards and every `RENEGADE_*`
family are included. The broader family adds guards for original sorting,
manual Miles mixing and ABI/profile choices omitted by the earlier filter.
Two statistics stubs are removed: the original owner now records texture and
sorting counters, with host sanitizer coverage of frame reset and snapshots.

Function records retain signature/scope, byte positions, whole-definition and
body hashes, literal and nonfinal return candidates, empty-body and unsupported
markers, call syntax and surrounding preprocessor branches. These are discovery
signals, not automatic stub verdicts or a resolved call graph. Macros are retained
because unexpanded syntax cannot enumerate every generated definition.

Reviewed entries and risks:

- Four render-target binding overloads only diagnose nonnull targets; restoring
  the default target is also a no-op. These join allocation, projector draw and
  restoration in one dependency cluster. The two light-environment methods are
  empty. Ordinary native mesh submission separately uses engine light state
  for CPU colors; these stubs do not establish that all lighting is missing.
- Nine Miles provider methods are empty: provider close, speaker type,
  orientation, velocity, effects level, stream loop block, sample processor,
  timer stop and timer release. Reviews retain their original callers and
  activation conditions. Sound3D supplies listener-space positions; automatic
  velocity generation is originally disabled. The inspected stream loop-block
  call requests the full stream, while native whole-sample looping exists.
  Reverb processing is gated off by missing filter enumeration, so enumeration
  and processing must be restored together. The inspected update timer is
  initialized to -1 with no start assignment; timer stubs alone do not establish
  an active timer failure. None of these is classified as a proven exclusion.

The 15 additional reviews bind current definitions, preprocessor context and
original caller hashes. The generator reports zero review identity issues;
18 inventory/review and nine parser tests pass. Dev212's 634-action ARM link
already compiles these unchanged boundary bodies. This is source and compile
evidence, with no new native execution or pixel acceptance.

The renderer dependency review retains original material-task reference
ownership, rigid/skin ordering, deformation and delayed-pass flushing. Native
Flush currently retains decal work without the original procedural queues.
Restoring only transition push/pop could suppress base geometry while still
omitting procedural effects. The complete queue/material/draw-state cluster
must be restored before those guards can be removed safely. The unselected
original dx8renderer.cpp also fails isolated ARM compilation at six GCC syntax
sites: two MSVC for-scope dependencies and four multiword functional casts.
A private minimal syntax-only copy compiles as an ARM object; it is not selected,
linked or a renderer fix. Integration and host behavior checks remain open.

All four linker wrapper references remain in the denominator. Source inspection
distinguishes shader diagnostics around original shark_init from host-only thread
failure injection and fixed-clock movie capture. Their row classifications remain
unknown until wrapper identity/build-profile reviews are integrated. Empty bodies,
macros, hidden generated implementations and runtime call reachability still need
separate review; the 15 classifications do not close this sweep.

- Render-target creation always returns NULL. Original projector allocation
  callers are recorded; render-to-texture restoration remains open.
- Unsupported object submission records diagnostics without rendering extra
  mesh material passes or enabled box-display geometry. Per-map instances and
  box-display settings remain unverified.
- The decal diagnostic helper is a stub, but current callers are guarded for
  the non-native host profile. Its presence does not establish that native
  decal bodies remain disabled. Queue execution, depth bias and pixels remain
  open native gates.
- Native DX8 capability enumeration is replaced by a conservative description.
  Its unavailable capabilities must be reconciled against S2 feature and S4
  all-map effect inventories; this is not renderer completeness.
- Dazzle compile/link evidence exists in the compile ledger. Its current guard
  and the two decal render-body guards are reviewed: only port profiles lacking
  `__vita__` take the early returns. Native takes the original bodies. Physical
  appearance, traversal/flush execution and decal depth bias remain open.
- Native-profile preprocessing and configured graph evidence select original
  audio and seven nonempty movie-provider methods. Header parse uncertainties
  prevent treating syntax absence alone as complete exclusion or playback proof.
- Twenty no-output audio methods are source-reviewed stubs: initialization,
  shutdown, device selection, settings persistence, frame update, playback
  creation and four sound-scene serializers. The serializers return success
  without consuming or emitting chunks. The current full native configuration
  defines `RENEGADE_A35_ORIGINAL_WWAUDIO` and excludes these fallback bodies.
  Logical listener/sound creation and stateful settings methods remain separate
  unclassified rows; they were not labeled stubs from the enclosing guard.
  Exact overload and indirect caller resolution remains open. Original command
  references include `scriptcommands.cpp:935`, `:950`, `:995` and `:1029`.

Movie reviews now also pin current build definitions and original movie/dialog
caller sources. A matching method signature in another preprocessor branch
cannot inherit a review: the body and optional definition hash must match.

The three additional material guards are native omissions, unlike the three
headless presentation guards. Transition Render_Push/Render_Pop return before
original mapper/material/base-override work; MeshClass replaces procedural task
registration with diagnostic-only submission. Original producers include spawn
(`physicalgameobj.cpp:317`), death (`powerup.cpp:875`), healing (`soldier.cpp:3747`)
and electrocution (`soldier.cpp:4738`). Stealth pushes an additional pass and can
suppress base geometry (`stealtheffect.cpp:230-234`). Thus suppressed-base
geometry has no effect submission in this inspected native path. This is a
source defect, not an observed physical disappearance. Per-map occurrence,
original deferred ordering, skin/cull/translucent semantics and native pixels
remain acceptance requirements. No repair is included in this inventory batch.

Reviews invalidate when their recorded function or caller/context identity
changes. Constructor initializers belong to definition identity. The tool
rejects inconsistent totals, invalid status/evidence fields and duplicate source
locations, while keeping `complete: false`.

Reproduce after deterministic source staging:

```sh
python3 -m venv build/sweep-parser-venv
build/sweep-parser-venv/bin/python -m pip install -r tools/sweep-parser-requirements.txt
build/sweep-parser-venv/bin/python -m unittest discover -s tools -p test_audit_sweep_port_guards.py
build/sweep-parser-venv/bin/python -m unittest discover -s tools -p test_sweep_cpp_functions.py
build/sweep-parser-venv/bin/python tools/audit_sweep_port_guards.py --include-functions --output reports/generated/sweeps/port_guards.json
```

Six original mesh-debugger methods and two Debug_Statistics accounting methods
are empty in the native boundary. Original console output, enable/disable
commands and game-mode frame updates reference the debugger; statistics macros
reference the counters. Exact macro/build reachability and equivalence with
native telemetry remain open. These are diagnostic gaps, not established retail
gameplay omissions or proven exclusions.

Twenty-seven parser/review tests pass locally. Function reviews bind their
preprocessor context, preventing an unchanged body moved into another build
branch from retaining its old profile verdict. Generator, function-parser and
pinned dependency-file hashes are included in inventory input identity.
Guard reviews additionally require
the exact directive, unique source location and an unchanged whole-source hash.
CI includes the pinned parser
setup, these tests and an artifact of its partial inventory. Evidence remains
source/tool validation; no additional physical gate is closed.

The coverage question is still open: what can exist outside these denominators?
Current risks include macros and generated sources outside the scanned trees,
patch hunks starting within omitted lexical context, unresolved parse nodes,
nonliteral build selection, indirect/virtual call resolution and retail-authored
references. Every row still needs original-owner, skipped-behavior, caller and
affected mission/mode classification. Full S1 closure, S2–S8, the consolidated
gap register and mission/device acceptance remain required.

Machine-readable inventory: [port_guards.json](generated/sweeps/port_guards.json).
