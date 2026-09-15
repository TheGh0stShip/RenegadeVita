# Prepared local development controller channel

## Scope and status

Latest: Dev108 canonical r3 finished BUILD SUCCESS. DirectInput integration is
now applied and Dev109 fast build launched; earlier prepared-only descriptions
below are historical. Compilation and native runtime consumption are pending.

Prepared renegade_vita_dev_input.h and tools/vita3k_native_input.py while
Dev108 canonical r3 compiles. They are NOT wired into DirectInput yet and have
not been compiled or exercised. Do not claim native input or checkpoint proof.
Dev108 compiling sources were not changed; integration is the next work unit
after that build stops. No Vita3K code, Windows focus requirement or physical
device mutation is involved.

The channel only supplies raw buttons/axes below original DirectInput. Original
WWUI, Input, Combat, scripts and SaveGameManager continue owning all behavior.
There is no world-state manipulation, alternate loop or fabricated save.

## Bounds

- Requires exact local user/config/dev-input-enable.flag marker at initialization.
- Disabled path does not poll files or read clocks during frames.
- A new native RTC token rejects commands from prior sessions; sequences reject
  replayed commands. Commands are local files, not a network service.
- Holds expire independently after at most 3000 ms. Physical Start aborts the
  channel. Removing the marker disables it on its next one-second enabled check.
- Only ordinary Vita game buttons and 8-bit axes are admitted; no PS button.
- Recording/replay and live development input must be mutually exclusive.
- Polling is development-only and disqualifies these runs as FPS benchmarks.
- Sender records native acceptance/release separately from gameplay evidence.
- No marker, command file, session file or user data belongs in the public VPK.

## Integration plan

Include the header in renegade_directinput.cpp inside its native-only include
block. Initialize after Initialize_Route_Mode with MODE_PASSTHROUGH admission;
Shutdown alongside native route cleanup. Apply immediately after the replay
sample and before Record_Sample/button translation. Preserve original raw
controller failure/flush behavior and physical abort ownership.

Then close focused ARM/build checks, enable on the emulator only, demonstrate
original menu movement/activation without Windows focus, and create/load an
original M00 save. A native acknowledgment alone is not that proof. Synthetic
Start in this seam is not proof of the outer runtime's physical Start exit.

Prepared tools/vita3k_tutorial_quicksave.py requests the existing Select+Square
original quicksave chord through the local sender. It retains sender output,
native acknowledgment and before/after save-file hashes separately, and waits
for a nonempty changed quicksave file to settle. It never labels file appearance
as successful deserialization, segment completion or a proven checkpoint.
It does not copy saves into distribution or modify retail data. This helper is
not executed or validated yet; use only after native channel integration.
