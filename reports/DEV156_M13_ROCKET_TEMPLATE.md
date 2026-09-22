# Dev156: retained M13 rocket aggregate

Dev156 extends the proven Dev155 aggregate-template mechanism to the measured
`ag_rocketl` effect. It remains full-port-only and is prepared only while M13
is loading. The original aggregate is retained within its definition and each
runtime request receives a fresh original `Clone()` instance. Cleanup releases
both retained definitions. The demo profile is unchanged.

In matching final-hash Vita3K/OpenGL evidence, loading preparation cost
7,509,119 us for `X00_AG_Explode` and 134,190 us for `ag_rocketl`. During
the first ambush rocket, `X00_AG_Explode` cloned in 5,879 us and original
script `Set_Model` completed in 7,090 us. Two `ag_RocketL` live instances
cloned in 162 us and 81 us. Dev155's uncached rocket creates were about
101-151 ms. An attempted `ag_fiery_ex06` template did not use the aggregate
path, added loading cost, and did not reduce live creation; it was removed
before the final candidate. Its original path remains untouched.

This is an event-local win only. Final Dev156 cumulative frame-480
p50/p95/p99/worst were 90.3/412.9/449.4/2846.0 ms, not a whole-route
improvement over Dev155. `ag_fiery_ex06` still took 117-197 ms per live
create. A/V synchronization, actor sequencing, full cinematic progression,
memory high-water, 60 FPS and physical Vita acceptance remain unverified.
The bounded run ended `TIMEOUT_UNASSESSED`.

Evidence: managed AppData `campaign-dev156-final-m13-1/`; 194 ordered
staging patches and ARM SELF/VPK pass. SELF SHA-256
`f738f786a2dabe07cb701e77b14a436494f1bb32de981c297a722766a2192001`;
asset-free VPK SHA-256
`8079be905602ad33e0c6a0406784f49c422b792369035305ab559508ae664058`.

Next: identify the non-aggregate fiery-effect clone path and the remaining
simulation owners before considering another cache, then obtain matching
physical Vita visual/audio evidence for Dev155 or later.
