# Dev134 milestone and physical handoff

| Field | Value |
| --- | --- |
| Candidate | A3.5-dev134 |
| Platform | Native ARM PlayStation Vita |
| Status | Milestone prerequisite PASS; physical acceptance OPEN |
| Evidence classes | Host, Vita3K, physical deployment/readback |
| Release gates | 0/10 |

## Result

The user's next-milestone condition is satisfied: canonical host/sanitizer/ARM
closure, matching package identity and matching Vita3K visual regression PASS.
This does not earn physical release acceptance or a native FPS claim.

## Artifacts and identity

Canonical artifacts: build/dev134-closed-canonical/receipt.json, 38 files.
Emulator return: build/dev134-refinery-return/return-receipt.json, 42 files.
The same original refinery checkpoint preserves Mobius, skin/weapon and world
appearance against Dev133. Map imagery, statistics text and Vita Help labels
are visible. Resume reaches frame2180, native END clean, owned process stopped
unforced. Five native commands and four touches released; all14 saves unchanged.
The runner's PROCESS_FAILED/null result is retained separately from native exit.

## Physical deployment

Physical admission at 10.0.0.202:1337 identifies the exact installed Dev126 SELF:
75bdae5d5d6bd837e3e8670a9481392a2d9c5cf0b15bffc489a48daf72dc1935.
Candidate-scoped backup and receipt:
build/device-evidence/dev134-admission-20260915T024412Z/admission.json.

Physical deployment PASS, including executable and VPK readback:
build/device-evidence/dev134-deployment-20260915T024507Z/deployment.json.
Only ux0:/app/RNEGA3101/eboot.bin and the matching VPK under user/ were written.
Original retail data, saves, plugins, firmware and SFO were unchanged. No
checkpoint/input override was installed. The existing dev79 bubble runs Dev134.

SELF: 55ec5e560eed2ca94a4ab06d8b10e6f7039c19b8d6c79353f5a63f3ea1e7e385.
VPK: 1f0b0fb569d47c6fff31504bd890cc2a8910a2d248e4c510155416d49b67002e.

## Blockers and next gate

External blocker: FTP works; remote command port1338 refuses connections.
VDB doctor/capability receipts are build/dev134-physical-vdb-*.json. User was
instructed to launch the existing bubble once. No permission re-request is
needed. Five-minute read-only log monitor is build/watch-dev134-physical.py;
results belong beside the deployment receipt. Never label deployment as runtime
or hardware performance acceptance.

The separate authenticated VDB gateway also refuses port31337; confirmed by
debug capabilities and a sequential debug targets retry. The first parallel
targets query reported the client's device lock busy, retained separately;
that lock result is not treated as a network diagnosis. Receipts are
build/dev134-physical-debug-*.json. No remote launch provider is available.

At 02:51:08 UTC the 300-second monitor completed: FTP remained available, no
Dev134 candidate log returned. monitor-return.json beside deployment retains
all30 observations; this is an external launch/return blocker. No physical
runtime, visual, audio or FPS test has been claimed. No process remains running.

On physical return, inspect candidate boot/runtime identity first. Assess movie
decode, convert/upload, scheduling and audio-output failures; then gameplay
frame-time distribution, render/simulation timings, memory and pause/exit.
Dev126 cumulative FPS is contextual failure evidence, not a fixed-camera A/B
baseline. Establish the same physical checkpoint/camera before claiming gains.
Logs alone do not establish audible movie sound or visual correctness.

## Post-freeze source follow-up

Local source follow-up, not in deployed Dev134: corrected two prewarm printf
sites using %u for uint64_t counters. Original native compilation with
-Werror=format fails on ten mismatches; corrected production ARM translation
unit passes. All eight existing loading-screen contracts pass, and the edited
file passes git diff --check. Evidence: build/dev135-prewarm-format/baseline.json and
corrected.json, with logs. This removes shifted prewarm counter output; the
Dev134 gameplay/performance counter formatting was already correct. No gameplay
or rendering behavior changed. A future candidate must package this separately.
Frozen Dev134 binaries, source identity and emulator return remain intact.

Remaining work: physical intro/audio/FPS and complete demo; naturally populated
Vehicle/Building pages, visible objective cycling, prior intermittent pause
hang, and the native YUV/persistent-geometry/sampling optimization routes in
DEV134_NEXT_RENDER_ROUTES.md. No routes-exhausted or 60 FPS claim.
