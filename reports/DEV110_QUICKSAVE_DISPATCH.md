# Original quicksave dispatch gap

## Current evidence

At user request, two bounded quicksave attempts targeted the owned Dev109
Vita3K PID 2804. The first used owned-window key messages; the second used a
250-ms foreground keyboard chord, released both keys and restored the prior
foreground window. Receipts are under Dev109-native-20260909T011450Z. Neither
created a .sav file in the original user/save directory. Do not claim a saved
checkpoint or infer actual game-key consumption from injection receipts.

## Native owner trace

DirectInput maps Select+Square to DIK_F5. A31 control configuration binds F5 to
INPUT_FUNCTION_QUICKSAVE. Original CombatGameModeClass::Combat_Keyboard checks
that action and IS_MISSION before calling its static Quick_Save method.

A31_Interactive_Run_Simulation_Frame calls Input::Update, checks active Combat,
then directly calls CombatManager::Generate_Control, cNetwork::Update and
CombatManager::Think. It does not call original CombatGameModeClass::Think or
its Combat_Keyboard. Consequently binding the key did not connect the original
save operation to this native frame path. This is a concrete missing dispatch;
it does not independently prove the emulator consumed either attempted chord.

## Prepared correction, not integrated

build/dev110-host-evidence/native-quicksave-dispatch.patch connects that same
original input action and mission guard to CombatGameModeClass::Quick_Save
after the existing active-mode check, before control/simulation. Native-only
and original-game-mode guards preserve headless host linkage. A request-only
breadcrumb makes dispatch distinguishable from injection and save success.

Original Quick_Save remains owner of slot rotation, descriptions, registry
state, SaveGameManager serialization and HUD notification. No replacement
save format, fabricated state or forced mission progression is introduced.
Full game-mode restoration remains separate; blindly calling the whole mode
would also activate unrelated frontend/network/debug behavior.

Dev109 canonical source is frozen while compiling, so this is a next-batch
proposal only. Apply to the port source after closure, not to pristine upstream
or the staging-only patch registry. Then require native dispatch evidence,
an actual original M00 save, metadata inspection and a successful original load.
Preserve the user's current run and progress. No physical-device access.
