# Dev108: dialog UTF-16 boundary and original checkpoint input

Dev107 canonical failed at UBSan host menu labels, not ASan: both ASan
interactive runs passed two complete in-process M00 cycles, including the
leak-enabled run. UBSan loaded all six translations correctly but original
dialog controls retained IDS_ descriptors. The parser still used libc wcsstr
on engine UTF-16 data, and its non-Vita translation copy used libc wcscpy.

## Changes

- Deterministic patch 147 routes original dialog title/control lookup, custom
  control-class searches and non-Vita translation copy through existing
  rv_utf16 helpers. Original TranslateDB and dialog ownership remain unchanged.
- Existing emulator step helper adds bounded QuickSave (Right Shift+Z,
  Vita Select+Square), with reverse-order releases in finally and per-key
  receipts. No global keyboard injection or foreground requirement. Queuing
  messages does not prove the original game consumed or saved them.
- Dev108 retains Dev107 singular user/save bootstrap correction.

## Evidence at resume

- Dev106 prior retry reached at least frame 70,800, pistol acquired, then the
  runner's 1800-second limit terminated the owned process at 23:32:11 UTC.
  This is TIMEOUT_UNASSESSED, not a recorded crash or M00 completion.
- No files found in original user/save; prior progress has no saved checkpoint.
- Last telemetry averaged about 40.7 FPS; no 60 FPS acceptance or controlled
  before/after benchmark. Last missing-file/error entries in the retained
  stdout occur during startup/loading at 18:03:01 local, not continuously
  throughout the 30-minute run.
- Runtime-after SHA: ee10bb619b0eefb8fb96bf91ce9fd4c25e9c176962a8b021a5ed03f1de1a9ddd.
- Dev106 first-run archive-handle failure remains open despite successful retry.

## Next

Correct stale canonical inventory with user direction, then establish an
actual original checkpoint and load it before another long tutorial run;
then complete M00, observe fade/thank-you/credits and safe exit. No physical
tests, retail distribution, fabricated saves, or release acceptance claim.

## Build/runtime return, approximately 00:40 UTC

- Fast ARM/package PASS; artifacts retained in
  build/dev108-host-evidence/fast-candidate, SELF digest in fast-self.sha256.
- Initial driver copy used the wrong managed dist root, so canonical had not
  started. Copied from the workspace dist path reported by the fast build and
  launched canonical separately; no concurrent staging/build writers.
- Canonical passed ASan and leak-enabled original M00 two-cycle runtime,
  targeted UBSan original M00/M01/City two-cycle runtime, and 148 host tests.
- Canonical then failed tools/generate_integration_report.py:122: patch count
  147 versus expected 145. Coordinator disclosed missed inventory maintenance
  and asked whether to correct it. No canonical closure claimed.
- Emulator run Dev106-checkpoint-20260909T002750Z, PID 5112, progressed to
  difficulty selection but title-owned key messages thereafter did not reliably
  activate a choice. Native cursor responds to background mouse movement;
  activation and QuickSave remain unproven. Do not confuse queued input with
  consumed input or the earlier menu transition with a deterministic route.
- WM focus/activation messages and a temporary candidate-thread SetFocus attempt
  did not establish a reliable route. The latter recorded foreground unchanged,
  released X and detached its input-thread attachment. No emulator fork or
  global keyboard injection. Capture receipts remain in the run directory.
- Run deadline is approximately 00:57:50 UTC. No real save or M00 ending return.
