# Dev112 native compile preflight

This is an isolated source compile using retained dev111 compiler commands,
with checkpoint launch explicitly enabled and object outputs redirected to
`build/dev112-native-preflight/objects/`. It is not canonical candidate closure,
link validation, a new VPK, or emulator evidence. Installed dev111 is unchanged.

## Result

- `renegade_directinput.cpp`: compiled before the runtime compile failure.
- `ww3d_vita_renderer.cpp`: compiled before the runtime compile failure.
- `a31_vita_runtime.cpp`: failed at the new pause helper's private API call.
- `a31_gameplay_boundary.cpp`: compiled in the follow-up invocation.
- `a4_frontend_lifecycle_boundary.cpp`: compiled in the follow-up invocation.

Evidence: `build/dev112-native-preflight/compile.log`, `compile.exit`,
`remaining-compile.log`, and `remaining-compile.exit`. Both invocations are
terminal. No build process is still running from this preflight.

## Corrected private-method call

The agent-added `DialogMgrClass::Reset_Inputs()` call is illegal because the
original method is private. Original `DialogMgrClass::Register_Dialog` already
calls it when registering a new dialog; unregistration and rendering also reset
the cached mouse states. Remove the redundant direct call rather than exposing
the private method or adding a replacement input owner. Keep the separate
native key-edge priming used to avoid immediately closing EVA with held Start.

The user authorized resumption and correction. The redundant direct call has
been removed; original dialog registration remains responsible for the reset.
The runtime recompile result must be retained separately. Fresh host, staging,
ARM/link and packaging evidence remain necessary before checkpoint reload or
pause tests in Vita3K.
