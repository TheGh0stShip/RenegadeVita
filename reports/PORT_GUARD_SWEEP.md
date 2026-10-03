# S1 port guards and stubs — inventory in progress

This is a partial source inventory, not a completed sweep or runtime acceptance.
It establishes explicit denominators before further behavior fixes. The current
source contains 3,531 records with 11 fallback/diagnostic functions reviewed as
`stubbed_or_noop`, 1 capability constructor as `boundary_replaced`, and 3,519
records still `unknown`. All statuses reconcile to the total.

| Inventory kind | Records |
| --- | ---: |
| Changed patch guards, including removals | 513 |
| Current port/staged source guards | 816 |
| Port function and lambda definitions | 1,643 |
| Port macro definitions | 486 |
| Syntax parse uncertainties | 69 |
| Linker wrapper references | 4 |

The 310 patch files and 307 literal staging references are separate inventories.
Three files have no staging reference; they remain visible without being called
retail exclusions. Historical hunk coordinates are not current staged line
proof. Comments, strings, raw strings and continued comments are masked while
retaining physical positions. Native `__vita__` guards are included.

Function records retain signature/scope, byte positions, whole-definition and
body hashes, literal and nonfinal return candidates, empty-body and unsupported
markers, call syntax and surrounding preprocessor branches. These are discovery
signals, not automatic stub verdicts or a resolved call graph. Macros are retained
because unexpanded syntax cannot enumerate every generated definition.

Reviewed entries and risks:

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
  classification and physical appearance remain open.
- Native-profile preprocessing and configured graph evidence select original
  audio and seven nonempty movie-provider methods. Header parse uncertainties
  prevent treating syntax absence alone as complete exclusion or playback proof.

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

Twenty-five parser/review tests pass locally. CI includes the pinned parser
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
