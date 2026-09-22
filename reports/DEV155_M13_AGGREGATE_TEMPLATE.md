# Dev155: retained M13 aggregate template

The full-port M13 loading route now creates original `X00_AG_Explode` once
after level load and retains the assembled WW3D render object within its
aggregate definition. Later `Create()` calls return fresh `Clone()` instances.
The template reference is released when that definition is destroyed or
reassigned. The M00 demo profile does not compile this path. Retail assets
are not modified or packaged.

The matching final-hash Vita3K/OpenGL direct-M13 run
`campaign-dev155-final-m13-1` recorded 8,268,161 us of loading preparation,
then a 7,837 us clone and 9,016 us total original script `Set_Model` at the
first ambush rocket. Dev154's comparable live `Set_Model` was 6,637,922 us;
this is a roughly 736x event-local reduction, paid for by longer loading
and one retained aggregate template. An earlier same-code run measured
8,829,998 us preparation and 7,942 us live `Set_Model`, and rendered M13
through frame 1320. The final-hash run reached frame 543 before its bounded
watchdog. Neither run proves the entire cinematic or mission.

The full-port M00 direct-entry hook now accepts the exact original
`M00_Tutorial.mix` source. Its parser test passes, and matching Vita3K
`campaign-dev155-final-m00-1` loaded the original tutorial and reached
360 frames. This is a smoke regression, not tutorial completion.

Before/after frame distributions are not a clean whole-route A/B because
the bounded runs reached different frames and still contain unrelated stalls.
In final-hash M13 at frame 480, cumulative frame p50/p95/p99/worst were
101.4/328.5/378.4/2559.1 ms. The specific six-second explosion-create
event is removed, but total frame pacing, A/V synchronization, other asset
creates, actor sequencing, memory high-water, 60 FPS, and physical Vita
acceptance remain open. The watchdog statuses are `TIMEOUT_UNASSESSED`.

Build: 193 ordered staging patches, ARM SELF/VPK pass; focused development
checkpoint parser tests pass. Matching SELF SHA-256
`980640b313ccca8a9dde948497296ee0681b6e3122f226a903aa7d721f8fc96f`;
asset-free VPK SHA-256
`4732eed934476d3ba1e0ce3ff9bfb510aa24a692026918c335265ccb5bba570c`.

Next: measure and reduce the remaining first-rocket/ambush asset-creation
spikes and slow simulation frames, then verify authored cinematic sequence
and audio alignment on a matching physical Vita candidate.
