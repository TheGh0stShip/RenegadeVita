# Demo continuation corrections

## Applied follow-up

The ending now uses the tutorial-source admission result captured before loading.
This accepts both the original tutorial MIX and saves whose original metadata
identifies M00, without inspecting the save filename at mission completion.
The redundant mission-mode assignment was removed: original Initialize_SP
continues to own mission setup. A single checkpoint diagnostic now reports the
local ID, player pointer, active player count, star pointer and control owner
before the unchanged restoration checks. Runtime proof is still pending.

The recent continuation messages overstated several conclusions. This note
records source and command evidence already obtained, without another build poll.

## Build identity and checkpoint coverage

Session 76532 was launched with plain `bash ./tools/build.sh`, with output
redirected to `build/dev114-canonical.log`. Its actual compiler invocation uses
`build/vita-a35-dev110-candidate-20260909-091907` and
`RENEGADE_VITA_DEVELOPMENT_CHECKPOINT=0`. The log filename does not establish
Dev114 identity. This configuration cannot exercise the opt-in checkpoint
startup request. Terminal build status has not been collected.

The runtime source was edited during the build. Before retaining a candidate,
the source identity captured by that build must be reconciled with the compiled
runtime object and final artifact. Do not deploy it as an evidenced Dev114.

## Ending regression

The added `A31Demo::IsTutorialMap(load_source)` success guard compares the load
filename with `m00_tutorial.mix`. A restored tutorial uses a save filename and
therefore fails this comparison. Successful checkpoint play would skip the
fade, thank-you message and credits. This guard is not a completed release gate.
Correct it using the validated map identity from the original save metadata,
which the existing `A4_Frontend_Is_Tutorial_Source` admission path already uses.

## Saved-player hypothesis remains unproven

`GameInitMgrClass::Initialize_SP()` already sets `GAMETYPE_MISSION` before the
load. No evidence yet shows a later mode reset causing the identity failure.
Reasserting the same value is an unproven hypothesis, not a demonstrated fix.
The failing check combines player lookup, active player count, star pointer and
control owner. Runtime evidence must distinguish these conditions before the
cause can be assigned to player removal.

## Pause presentation trace

`MenuGameModeClass2::Render()` is intentionally empty. Its caller,
`GameModeManager::Render()`, calls `DialogMgrClass::Render()` after game modes,
message window and objective viewer. `MenuDialogClass::Render()` draws the
backdrop followed by the dialog controls when active or transitioning.
Consequently, a missing dialog render invocation is not established as the
cause of blank EVA controls. Next inspect dialog activation, transition-hidden
controls and child-dialog construction using the retained emulator evidence.

The exact requested thank-you text and timed ending already exist in source.
Authentic M00 completion and visible ending presentation remain unproven.
