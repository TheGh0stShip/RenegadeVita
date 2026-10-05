# Original restart loading presentation source wiring

Status: local/uncommitted/unvalidated. Source inspection and edits only;
no staging, patch execution, tests, build, emulator/device or commit/push work.
Full campaign and repeated Skirmish completion remain unaccepted.

## Retained first-load presentation

The direct native runtime constructed A31VitaLoadingPresenter and its callback
inside the session's do/while block. Their scope enclosed the gameplay loop,
not only initial loading and presentation preparation. The initial original
LoadingScreenClass therefore retained its model/font references during gameplay
and later in-place reload. Its progress state could already be at completion.

SaveLoadStatus::Set_Status_Text and Inc_Status_Count notify the same native
loading callback. Those methods are not restricted to level loading. During
gameplay or restart they could render the retained first-load screen, subject
to the existing 50 ms status-callback throttle. This is source evidence of a
stale presentation route; it is not physical evidence of the save freeze or
proof of a particular on-screen symptom.

The full port now disarms that callback and releases the original loading
screen after all initial texture/model and M00 presentation preparation, before
gameplay begins. Both operations are idempotent; ordinary scope destruction
still handles early failure. No later gameplay path uses that released screen.
The demo keeps its existing callback/screen lifetime.

## Borrow original Combat loading's fresh screen

Original CombatGameModeClass::Load_Level already constructs its own stack
LoadingScreenClass. The new selected
port/patches/commando-a36-reload-loading-presentation.patch binds a native
borrowed-screen callback immediately after that construction. The scope is
destroyed before the screen, including the existing required-load failure
return. It restores the previous borrowed pointer and does not delete or retain
the screen, construct another screen, or replace original level loading.

Native synchronous loader and SaveLoadStatus callbacks render this current
original screen while the borrow is active. Existing recursion protection and
50 ms throttling for status updates remain. Loader milestone minimums retain
original Combat progress semantics; chunk counts are not converted to percent.
With no active screen, full-port gameplay status callbacks do not draw or log
each save chunk. Explicit nonnegative loader milestones remain diagnostic.

The native between-frame local restart envelope now scopes the established
loading logical resolution/presentation rectangle around original cGod restart
or Process_Core_Restart_Request. This precedes original screen construction.
The scope restores its prior resolution/rectangle before the existing native
gameplay rebind. The new screen's model, text, animation, progress, rendering
and destruction remain owned by original LoadingScreenClass.

No map-cycle rule, scoring, script callback, save format or serialized reason
changed. The class stores only a process-local pointer at the platform boundary.
ARMv7-A little-endian ILP32 and existing ABI gates remain the target; no ABI
artifact was rebuilt. Current Vita Combat loader executes its original routine
synchronously on the renderer thread. This callback borrow does not establish
safe rendering from future worker-thread callbacks.

## Evidence index

- port/platform/vita/a31_vita_runtime.{cpp,h}: first presenter/callback lifetime,
  disarm/release, borrowed-screen scope, native callback and restart envelope.
- port/patches/commando-a36-reload-loading-presentation.patch: original load seam;
  selected before the overlay-owner patch in tools/stage_sources.sh. Neither application nor coordinates
  have executed validation under the hold.
- staging/commando/combatgmode.cpp: Core_Restart and Load_Level stack screen;
  pending required-reload guard remains part of the selected patch sequence.
- staging/commando/loadingscreen.{cpp,h}: original backdrop/font ownership,
  per-instance progress state and presentation clock.
- staging/combat/combat.cpp: synchronous native Load_Level_Threaded boundary and
  loading milestone callbacks.
- staging/wwsaveload/saveloadstatus.cpp: status text/count notification callers.
- port/renderer/vita/ww3d_dx8_boundary.cpp: logical resolution/viewport and
  texture-transform cache invalidation at Set_Device_Resolution.

Staging/upstream were read only. No retail data, saves or dumps were changed.

## Remaining acceptance

Validate initial load and early failure cleanup, no loading draws during normal
manual/quicksave status updates, fresh zero-based reload progress, original
Practice backdrop, correct logical text layout and gameplay rectangle restore.
Verify required-load early return disarms before screen destruction, recursion
guard behavior, repeat same-map rounds and changed-map rounds, campaign death
restart, held input, and menu return/exit after failure. Observe model/font and
GPU memory across repeated transitions, rather than inferring leak freedom from
pointer release. Host, ARM, emulator and matching physical Vita/PSTV evidence
remain separate and pending.

The reported serialization freeze and combat performance are not fixed by this
change. Archive replacement still precedes original Core_Shutdown; its lookup
and worker ordering remain open. Remote round restart remains a separate gap.
