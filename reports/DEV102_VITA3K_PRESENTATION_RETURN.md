# Dev102 Vita3K presentation return, 2026-09-08

## Matching candidate

Fast ARM/package closure passed all 126 focused tests. The canonical build
continues separately in the background; do not assume its binary is identical.
Observed fast SELF SHA-256:
`de37445b1cc7c244ba6e0358de999b7946fe466a2090b758cb0ae7e7d967741b`.
Fast VPK SHA-256:
`c67f1a3a677f5bd75ad910768dfb2c6ebd6adfd6b9ae85308e5651ecdcc335d0`.
Fast ELF SHA-256:
`a45865df99a8462abf18c773713f82a5c84c566b9647fac634118b501a81876c`.
Matching artifacts and full manifest are retained under
`build/dev102-host-evidence/fast-candidate/` and its sibling SHA manifest.

## Observed results

Run: `D:\Vita3K\RenegadeEvidence\Dev102-fast-20260908T205616Z`.
The title-owned runner has a 600-second deadline and owns only its child PID.

1. Capture `step-20260908T205703218Z.png` visibly shows the Renegade intro in
   orange/red rather than the previously reported blue. This is one emulator
   frame, not complete audio/pacing or physical acceptance.
2. Capture `step-20260908T205729772Z.png` visibly shows all six original menu
   labels, including Single Player, Options and Quit. Native readiness logs
   ready=1 despite desktop_initialized=0; original text atlas diagnostics now
   execute with nonzero alpha, matching the source-level readiness diagnosis.
3. EA_WW completed in 15,519 ms, with 195 uploaded / 35 dropped frames from 230
   decoded, versus the Dev101 one-upload black-intro failure. First-movie visual
   and audible acceptance remains open; logs alone do not establish it.
4. R_Intro completed in 32,043 ms with 350 uploaded / 125 dropped frames from
   475 decoded. Color correction is observed; remaining drops and audible
   pacing must not be called flawless. Concurrent build load is uncontrolled,
   so this is not a fixed-route performance comparison or a 60 FPS result.

## Immediate continuation

Automated X/confirm attempts were refused by the foreground safety guard; no
input was sent. Windows foreground activation failed even with AppActivate.
The user was asked to click the owned game window once. Continue into original
Single Player and Tutorial, observe loading/HUD, and progress M00 when focus is
available. Do not bypass original mission scripts to fabricate completion.

Automatic runner captures were skipped when the game was not foreground; the
two step captures above explicitly selected and captured the owned game window.
Separate step JSON receipts retain actions and release status. No physical Vita
or PSTV access occurred. No full tutorial/ending or release acceptance claimed.
The unsupported days estimate is withdrawn; target usable alpha this session,
prioritizing demonstrated blockers rather than optional optimization/polish.
