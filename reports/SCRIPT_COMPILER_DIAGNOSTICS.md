# Script compiler diagnostic sweep

Dev223 refresh:the original Mission09 camera overrun is reproduced by its
registered callback and corrected with a five-slot loop bound. All44 selected
units recompile and the aggressive-loop warning disappears. Five review
warnings remain.15 authored camera bindings are retained across27 maps.
Host/ARM compile/link and actual callback sanitizers pass;camera presentation
and full native mission acceptance remain open. Historical discovery below
describes the pre-correction six-warning result. See
[fix receipt](generated/sweeps/m09_camera_bounds_fix.json).

The current host runtime's actual Ninja compile commands enumerate 44 of the
45 original Scripts.dsp units. All 44 compile successfully with optimization
and uninitialized/maybe-uninitialized/return-type warnings enabled. GCC JSON
diagnostics parse successfully for every compiled unit. DLLmain.cpp remains
unselected; port/platform/renegade_script_static_provider.cpp replaces the DLL
provider boundary. This run does not test that provider's initialization.

Every unit remains `unknown` for behavioral acceptance. No uninitialized or
return-type warning was emitted. A deliberately uninitialized test fixture
verifies that the diagnostic command reports such a read; compiler silence
does not prove initialization correctness, especially for script members.

The public [inventory](generated/sweeps/script_compiler_diagnostics.json)
retains source/object hashes, warning counts and scoped review locations.
Raw commands, object files and complete diagnostics stay in the ignored
build/script-compiler-diagnostics directory. The installed compiler version
is explicitly labeled as observed when summarizing the receipt.

Six review warnings identify these original owners:

- Mission09.cpp:4608: M09_Camera_Activate declares camera[5], initializes and
  saves five entries, but Entered iterates x < 10. Source confirms an array
  overrun after the five authored cameras. GCC reports undefined behavior on
  iteration five. This is an original-source defect, not an LP64-only defect;
  authored activation and actual runtime consequences remain unverified.
- Mission10.cpp:1309 and mission08.cpp:6404: Replace_Apache formats an int into
  char[10]. GCC's full-int range exceeds the buffer; caller bounds and retail
  parameter provenance must be established before claiming reachable overflow.
- Test_PDS.cpp:761: CUSTOM_HAS_MEDKIT interprets an integer as an output pointer.
  The sender and lifetime require tracing before adopting host token handling.
- Test_RMV_Toolkit.cpp:195,218: technician animation parameters cross integer
  and pointer representations. One reconstructed pointer is immediately
  overwritten by a literal; the other route and saved lifetime need review.

All other diagnostics, including inherited header warnings and isolated
legacy permissive conversions, remain counted. Seven tooling tests pass,
including actual GCC execution. Runtime C++ and ARM artifacts are unchanged;
Dev222 remains the current compile-only candidate. No game/emulator/device
session occurred. Physical acceptance remains 0/10.

The refreshed consolidated gap register retains the45 unit rows and five
nested review candidates plus27 camera binding-map rows. It now contains
53,166 overlapping evidence records, including52,885 unknowns; these are not
distinct defect counts.48 focused tests cover diagnostic, binding, consolidation
and source/staging contracts, including warning-partition rejection.

Reproduce the diagnostic run from the configured host runtime:

```bash
ninja -C build/host-a30-definitions -t compdb \
  CXX_COMPILER__a31_interactive_runtime_unscanned_RelWithDebInfo \
  > build/script-compile-commands.json
python3 -m tools.audit_script_compiler_diagnostics \
  --compdb build/script-compile-commands.json \
  --work-directory build/script-compiler-diagnostics \
  --output reports/generated/sweeps/script_compiler_diagnostics.json
python3 -m unittest tools.test_script_compiler_diagnostics
```

The sweep preserves per-unit defines, includes and compatibility flags and
redirects outputs/dependencies away from the runtime build. Host LP64 warnings
are separate evidence from ARMv7 ILP32 behavior. Transitive include coverage,
preprocessor alternatives, full dataflow and actual all-map callbacks remain
open. Next: confirm the camera activation bindings and exercise the actual
callback under a sanitizer, then review parameter ranges and pointer senders
as a coherent behavior cluster.
