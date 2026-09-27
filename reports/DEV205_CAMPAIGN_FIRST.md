# Dev205 Campaign-first startup boundary

Issue #1's 2026-09-27 PSTV update reports that Dev204 crashes when Campaign is
selected before Tutorial, while Campaign can start after Tutorial but freezes
during the M01 scripted intro. It also reports save/load failure on that PSTV.
These are tester observations, not candidate-matched Dev205 results.

The original `CampaignManager::Start_Campaign` calls `Continue`, which calls
`GameInitMgrClass::End_Game` before the first M13 world exists. Original
`End_Game` bypasses its empty-game return whenever the game type is Mission.
The full-port Vita frontend now returns early only when its menu loop is active
and `Is_Game_In_Progress()` is false. Active gameplay teardown, the M00 demo,
and upstream source remain unchanged. This is a testable startup hypothesis,
not yet a proven root cause of the PSTV crash.

Evidence: deterministic zero-fuzz staging passed 268 patches. A host replay
entered the original Campaign manager before Tutorial, latched `M13.mix`, and
completed two in-process M01 cycles. The focused frontend suite passed 21
tests. The canonical Dev205 host, sanitizer, ARM, ELF/SELF/VPK, inventory, and
identity/hash gates passed. VPK SHA-256:
`18dfe3c86b0b320c8885f3d9341e33e0d64c5b22c67cfecc5ef947cf36f2ac24`.
It contains no retail assets. Vita3K installation/readback passed; installed
SELF SHA-256:
`6f9a0c41fdc1c9d2547a3f5843cfd6f70f26f3faafe7289b481d6b53dca97c7f`.
The canonical script returned nonzero only at its final install step because
`RENEGADE_VITA3K_VFS` was unset; the same title-scoped installer then passed
with the existing VFS path explicitly supplied. Install receipt is local at
`build/vita3k-backups/A3.5-dev205-setup-20260927T152819998709Z/setup-receipt.json`.

The bounded Dev205 Vita3K launch was refused because an existing Windows
Vita3K process was running. No process was stopped. Dev205 has **not** been
launched or tested on Vita3K or physical Vita/PSTV. The M01 intro freeze and
the reporter's save/load failure have not been fixed by this change. Earlier
Dev197 physical PSTV evidence passed one M13 pre-Ion save reload and menu
return, which does not supersede the reporter's broader failure.

Next: with an idle Vita3K instance, run Dev205 Campaign-first without Tutorial
and preserve the runtime log/capture. If it starts, replay M13-to-M01 and the
short M01 save, then inspect the last guest stage at the intro stop. Reproduce
save and load on the reporter's CD/1.037 setup or collect a matching log and
file-state receipt. Keep issue #1 open until those paths pass on physical PSTV.
