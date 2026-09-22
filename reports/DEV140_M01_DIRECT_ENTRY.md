# Dev140 M01 direct-entry and prewarm boundary

The full-port development flag now accepts a one-shot `RVMS1 Mdd.mix` request
from `ux0:data/renegade/user/config/dev-mission-launch-v1.txt`. It uses the
original MIX resolver and gameplay loader. This path is diagnostic only: it
does not initialize normal campaign progression or count as an M13-to-M01
transition. The flag is OFF in the published package, and the M00 demo profile
does not call this route. Parser and frontend contract tests: 18 passed.

An isolated Vita3K direct-entry M01 trial loaded `M01.ldd`, registered 357
original scripts, and created 467 active script instances, but crashed during
the M00-specific eager texture prewarm before its first gameplay frame.
The guest PC `0x815082d2` symbolized to `pte_osAtomicCompareExchange`; the
emulator reported an invalid read at `0x88046adc` and later a host access
violation. This locates the failure during prewarm, not its ultimate cause.

The next diagnostic build kept original lazy texture loading for M01 and
skipped only that M00 eager prewarm. Vita3K trial 2 loaded M01 and rendered a
first gameplay frame: 21 meshes, 2,228 vertices, 2,204 triangles, zero
rejected/unsupported submissions. A window capture shows the original beach,
weapon, HUD, and radar. The player moved from `(153.480,-49.438,-8.049)` to
`(148.950,-52.608,-7.911)` after bounded W input; bounded E input fired two
pistol rounds (12 to 10). The run passed over 3,900 frames before its
240-second watchdog. Both inputs were released. Objectives and mission
completion were not tested. Evidence is in managed AppData
`campaign-dev140-m01-diagnostic-trial-{1,2}/`.

The first public-build M13 trial used a broad non-M00 prewarm skip. It reached
the original M13 first frame (108 meshes), then Vita3K reported a host read
violation at `0x48` and exited. The skip was narrowed so M13 keeps its
previously working prewarm, while M01 and later campaign maps use lazy
textures. The narrowed public build passed ARM ELF/SELF/VPK creation, package
inventory, 18 focused tests, hygiene, and public-doc checks. A second M13
trial stopped at startup preflight because `Always2.dat` was transiently
reported invalid; the unchanged file remains present with SHA-256
`6cec7388c51b5b8591d8aa0cce974243621701990576574eda28dcd03c5e1611`.
This second failure is not evidence about the narrowed prewarm branch.

| Artifact | SHA-256 |
| --- | --- |
| Public VPK | `818f10dca9c1ec86cd68f5807f22b5d7c82bbee18c5094720424c1c4f63b68c0` |
| Public SELF | `02bb4080b7c1f6013af01278d405fad24d1640f0bccae80e2b4da589c1701d9a` |
| Public ELF | `a3335040a5f08d3ec8a569e0d4f72c48dec6bb4af601ff8d84859669160e3c5c` |

| Mission ID | Initialization | Required gameplay/objectives | Normal transition | Save/load | Build/evidence |
| --- | --- | --- | --- | --- | --- |
| M13 | passed in Dev138 Vita3K | unverified | unverified | implemented but untested | Dev140 narrowed build needs runtime retest |
| M01 | passed via diagnostic Vita3K entry | movement/fire passed; objectives unverified | unverified | unverified | Dev140 diagnostic trial 2 |

Next: retest the narrowed public M13 prewarm on Vita3K, isolate the transient
`Always2.dat` preflight failure if repeated, then connect original Combat
completion to Score/Movie/M01 without resetting campaign state or double
unloading the level. No physical-Vita result is claimed.
