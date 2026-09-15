# Dev117 Refinery-transition hang — 2026-09-14

User completed the Weapons Factory/tank-navigation segment and reported a
freeze while following Logan toward the Refinery. Retained emulator evidence
is under `build/dev117-refinery-freeze/`. This is a hang, not a demonstrated
native crash or physical-Vita result.

Original mission log: MTU_LOGAN_WHATSNEXT at frames 38168–38169, then objective
4 pending at 38170; movement/control/rendering still advance through frame
38400. Original Mission00 action-completion code sets the Refinery objective
and Logan's move at this handoff. The captured final image shows the Refinery
POG beside the Weapons Factory. The conversation transition itself executed.

The runtime remains exactly 2186916 bytes with SHA-256
194008c164719f03c4c6e86402e7e0056334290e8220b08459f501a333358299
across separated observations. Installed SELF matches Dev117:
5d2ecfa964d72ab0a2902307dcb4c9c55f9158549af6e54a3c8b1c64eb45cd50.
Window remains responsive; three Windows thread samples show continuing
emulator/driver CPU activity, not guest frame progress. Bounded non-invasive
CDB stack collection and a follow-up were detached without raw memory dumps.
RNEGA3101 and vitaGL Garbage Collector host threads wait inside Vita3K;
Qt event dispatch remains alive. Exact guest wait/ARM PC is unavailable:
this run had gdbstub disabled, and matching Vita3K symbols were not found.
Do not infer a semaphore deadlock, GPU fault or game-code root cause from
these unsymbolicated host frames alone.

No post-tank save exists. Latest immutable save is Hotwire/WF, 97500 bytes,
SHA-256 ea6e0bc1d2e7c36795fc25071ee3dee41ac31266ee07418956fdce63ad5473e6.
The user requested Hotwire or Gunner reload to show the visual defects. After
evidence retention, normal close failed to exit in five seconds, so exact
owned PID 10604 was force-stopped; this is not clean native teardown.
Restored Hotwire unchanged into new dev117-hotwire-recovery-20260914.sav and
queued the original one-shot checkpoint load. Master/Mobius saves untouched.

Recovery r1 enabled the optional gdbstub with wait-for-debugger false only in
the run-owned config. That run stalled at module loading and subsequently
ended, with unchanged native runtime and unconsumed checkpoint request.
Debugger connection attempts failed; this is not a working guest-debug route.
Its receipt and connection logs are retained. Original global config unchanged.

Current recovery run:
`D:/Vita3K/RenegadeEvidence/Dev117-hotwire-recovery-20260914-r2`, same Dev117
SELF, bounded to 1800 seconds, ordinary debugger-disabled settings. Original
Hotwire request remains queued. No gameplay input sent. User owns navigation
and defect-view selection. Reload now passes: the native log names the exact
Hotwire slot, reactivates the original player/star, preserves the saved camera,
and advances through frame 240 at (2.466,-19.925,0.119), health 100. Owned
PID is 17392; runner session 72933. Captured visible view without gameplay
input in `visible-20260914T184247536Z.png`. No full-M00 acceptance claim.

Next: collect user-positioned sky/elevator
views. Establish a working guest-debug route separately before another hang
replay; guest thread PC/wait evidence needs matching Dev117 ELF. Keep Dev118 objective-text correction separate:
it has source/test/ARM-object evidence, but is not installed or a hang fix.
