# Dev106: avoid redundant failed native retail probes

User reports continuous Vita3K 0x80010002 output during playable M00. Dev105
already established complete current Steam source coverage, valid MIX indexes
and original reticle/config reads. Its updated-emulator capture at
Dev105-updated-20260908T223341Z/step-20260908T223558578Z.png shows M00 with
readable HUD and Logan targeting. This is not a full tutorial or FPS pass.

Demonstrated algorithmic defect: rooted path resolution scans directories to
find the original filename case. Even after that scan proves a loose file
absent, Is_Available/Open repeat native stat/open failures before original MIX
fallback. Missing parents are also reopened while resolving their descendants.

Dev106 records confirmed absence only for a successful scan or ENOENT/ENOTDIR,
not permission or other directory-read errors. It stops descending an unresolved
parent and skips native file probes for confirmed read-only misses. The same
false return values, failure counters and original archive fallback remain.
No emulator logger is muted and no missing asset is represented as loaded.

Writes and writable namespaces bypass the shortcut. Original forced checks
carry through nested virtual Open calls and clear a negative observation after
success. No new session-global cache or retail mutation is introduced; the
shortcut uses the existing per-file prepared path and immutable-retail contract.

Added sampled availability/open skip counters. Host contracts cover missing
retail files, forced discovery of a newly created fixture, and writable-file
visibility after an earlier miss. All 22 filesystem checks, 126 fast contracts
and 11 DDS alias checks passed. Fast ARM/ELF/SELF/VPK closure passed; immutable
copies are retained under build/dev106-host-evidence/fast-candidate/. Canonical
build is running in the background. Matching runtime comparison remains pending.

Dev105 uncontrolled user-run baseline retained 1340 missing-file error entries
between 17:43:36.230 and 17:44:36.739 local emulator-log time. Sample:
build/dev105-host-evidence/missing-probe-baseline-tail.log. This quantifies the
observed log stream, not its CPU cost or an FPS improvement.
No median/p95/p99/worst FPS improvement is claimed without a fixed-route return.
Dev105 remains the installed playable emulator candidate while Dev106 builds;
do not replace it during the user's active tutorial run. No physical access.
