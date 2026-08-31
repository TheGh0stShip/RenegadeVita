# Historical In-Game Capture Campaign

## Purpose

Complete the historical screenshot timeline with one reviewed, actual M00
gameplay frame for every retained historical candidate that can reach the
defined tutorial checkpoint. This is a capture campaign, not a rebuild or a
visual-correctness acceptance test.

No retail data, save, dump, VPK, executable, raw video, device address, or
credential belongs in GitHub. Only reviewed, de-identified PNG derivatives and
their candidate/hash provenance will be published.

## Retained candidates

The local archive contains reusable VPKs for A3.1 through A3.1.4, A3.2-dev1,
and every A3.5 candidate from dev1 through dev89. The archive therefore does
not require a rebuild for this campaign. A candidate is eligible for a device
run only after the session-specific preflight verifies its VPK contents, VPK
SHA-256, packaged `eboot.bin` SHA-256, and title identity against a retained
local receipt.

Multiple VPKs exist for some build labels. Those are distinct artifacts until
their hashes and receipts prove otherwise; the campaign will use the artifact
that matches the historical source/build record, never merely the newest file
with the same label.

## Comparable checkpoint

For each runnable candidate, the desired frame is captured only after all of
the following are visibly true:

1. M00 Tutorial is loaded and player control has been handed off.
2. The camera is stable in the world, with geometry and HUD present.
3. The first Logan/NPC focus or first action prompt is visible when that build
   reaches it without synthetic gameplay input.
4. The frame is post-render, not an engine-frame counter, loading-screen,
   black buffer, startup logo, or diagnostic surface.

The eventual VDB provider is the preferred capture route because it is an
exact-title, post-render framebuffer service. Older title-owned Select captures
may be used only when the scene is visibly settled and the returned image
meets the same criteria. A failed, loading-only, black, or crashed candidate
will be recorded as such; it will not receive a substitute screenshot.

## Run order

The first pass restores the timeline's known visual gaps while preserving the
currently installed candidate for rollback:

| Pass | Retained candidates | Reason |
| --- | --- | --- |
| Baseline | A3.1.4, dev5, dev7, dev13, dev16, dev17, dev18, dev19 | Establish the already-known M00 reference points with one consistently captured frame each. |
| Existing diagnostic-only | dev6, dev12, dev20, dev21, dev24, dev42–dev47, dev78, dev79, dev82, dev86 | Replace old loading/black/magenta-only evidence with an actual M00 frame where the build can reach one. |
| No-image historical groups | dev1–dev4, dev8–dev11, dev14–dev15, dev22–dev41, dev48–dev77, dev80–dev81, dev83–dev85, dev87 | Determine whether a genuine M00 frame can be retained; otherwise publish the verified outcome as no in-game frame. |
| Current/unvalidated local candidates | dev88–dev89 | Remain excluded until their separate physical test is explicitly authorized. |

The passes deliberately cover every retained historical A3.5 number from dev1
through dev87 exactly once. The row for dev88–dev89 stays local-only so the
campaign does not silently turn an unapproved current candidate into a hardware
test.

## Per-candidate procedure

1. Record current title state and hash the installed title executable. Create
   a local rollback receipt before replacing anything.
2. Verify the selected retained VPK and its packaged executable locally. Stage
   and read back only `ux0:/app/RNEGA3101/eboot.bin`; do not modify retail data,
   saves, firmware, unrelated titles, or capture providers.
3. Launch with all synthetic controls released. Wait for the user-visible
   checkpoint; no fixed frame-number or time-delay trigger is allowed.
4. Capture one labelled post-render frame. If a candidate cannot reach the
   checkpoint, retain its bounded crash/status/log evidence instead of a
   misleading image.
5. Stop cleanly when possible, pull the returned evidence only after the
   authorized session, restore the saved executable, and verify the readback
   hash.
6. Review every candidate PNG before publication. Update the timeline,
   manifest, inventory, and gallery only with the reviewed derivative.

## Completion rule

The timeline is complete when each eligible historical candidate has exactly
one of these evidence-backed states: a reviewed post-render M00 PNG, a
loading/diagnostic-only label, a verified pre-M00/crash result, or an explicit
local-only/not-run hold. It is not complete merely because every row has an
image.

Actual deployment, launch, capture-provider installation, and media retrieval
remain deferred until the user explicitly marks the physical session READY.
