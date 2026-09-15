# Dev107: host UTF-16 and original save-directory bootstrap

## Retained failures and evidence

- Dev106 canonical log: build/dev106-host-evidence/canonical-build.log.
- ASan heap-buffer-overflow in host Wide_Text_Length, a31_interactive_main.cpp:144,
  via libc wcslen while validating original translated menu text. Host target uses
  -fshort-wchar; host libc/sanitizer wide routines do not use that engine ABI.
- Dev106 fast SELF: 0882db5d1510b32359ed454b4e303b499173c6a9fa3aea52e594982bbb6fd8db.
- Emulator first run: D:/Vita3K/RenegadeEvidence/Dev106-probes-20260908T225541Z.
- Always2.dat was opened at 17:55:48.530 local, then sceIoGetstatByFd and sceIoRead
  returned 0x80010051. Startup archive gate reported 3/4, causing controlled exit
  before movies/menu/gameplay. This is not a demonstrated missing-file condition.
- All three runtime retail read probes passed. Native skip counters reached
  71 availability / 20 open calls, but startup failure prevents adopting any
  performance claim. Dev105 gameplay remains the last usable emulator evidence.
- Dev105 updated run: 20,175 frames, clean Start-triggered teardown, no renderer
  error and no mission completion. No physical acceptance inferred.

## Changes

- Use existing rv_utf16_length/compare/strstr in the host translated-text checks.
  Keep all menu validity checks and sanitizer instrumentation enabled.
- Add ux0:data/renegade/user/save to Vita directory bootstrap. Original save
  routing uses singular save; preserve the existing plural saves directory.
- Emulator singular directory created locally, action recorded at
  build/dev106-host-evidence/emulator-save-directory-action.txt.
- Candidate labels advance to Dev107; failed Dev106 evidence is not overwritten.

## Pending

Canonical Dev107 closure, intermittent archive-handle diagnosis, original
quicksave/load proof, then comparable gameplay probe-rate measurement.
No fabricated checkpoint, retail rewrite, emulator fork, hardware test, or
full-demo acceptance. Full release gates remain 0/10.

## Same-SELF retry return, 23:03 UTC

- Run: D:/Vita3K/RenegadeEvidence/Dev106-probes-retry-20260908T230209Z,
  PID 22268, 1800-second bound. No reinstall or filesystem source alteration.
- Startup passed and user-driven gameplay reached the original jump segment.
- Focus-free PrintWindow captures inspected: step-20260908T230252897Z.png
  shows loading text and percentage; step-20260908T230354177Z.png shows the
  crate/jump segment and readable instruction. One loading image is not proof
  of progress animation. HUD edge/glyph artifacts remain visible.
- Log window 18:02:11.169 to 18:03:51.469 local: 28 missing-file/0x80010002
  entries and no 0x80010051. Retained at
  build/dev106-host-evidence/retry-probe-window-tail.log.
- At frame 1200 native probe skip counters were 1747 availability / 28 open.
  Gameplay renderer reported zero rejected submissions/backend errors; visual
  acceptance is separate. FPS telemetry was about 26 with a host build running.
- Earlier Dev105 1340-entry/60-second sample is a different uncontrolled route;
  no controlled before/after FPS or performance adoption claim.
- No synthetic gameplay input sent by this continuation; capture calls used
  Key None. Preserve user progress and the first failed return alike.
