# Dev157 M13 Fiery HLOD Template

## Scope

Dev157 is a full-port-only M13 performance experiment. It does not modify the
M00 demo profile. The candidate retains one original `ag_fiery_ex06` HLOD
template after loading-time construction and returns fresh `Clone()` instances
for later creates.

This is not a campaign, audio-sync, or physical-performance acceptance build.

## Evidence

- Candidate: `A3.5-dev157`
- Profile: `RENEGADE_VITA_M00_DEMO=OFF`
- Title ID: `RNEGC3101`
- ARM/package: pass
- SELF SHA-256: `de39b87f8e55c616891835db8f6f35013e93891ff18e3cbf80d4b89f48a4f714`
- VPK SHA-256: `f5ab774d87c50cf80f74fe9e6e057d2b727bc0090f836d8457e98eb272b7bd8c`
- Vita3K evidence: managed AppData `campaign-dev157-fiery-hlod-m13-1/`
- Runtime log SHA-256: `f1ed16493bb4c8a885949091ccdd003272f16eea5ea5f1fad7d7ce5600909986`
- Receipt SHA-256: `deb186f6c0a78936ff6ead4624427e03e4be1cd4b159372b562b88062ed6cf5f`
- Receipt status: `TIMEOUT_UNASSESSED`
- Physical acceptance: false

## Result

The targeted HLOD preparation behaved as intended for the narrow asset:

| Event | Dev156 | Dev157 |
| --- | ---: | ---: |
| `ag_fiery_ex06` live slow create | 117-196 ms | no later slow-create record |
| `ag_fiery_ex06` loading preparation | not retained | 92.263 ms |

This is only a small event-local improvement. The route remains far from the
60 FPS goal and still desynchronizes audio because ordinary M13 frames are
too slow.

Dev157 M13 frame timing:

| Frame | Avg FPS | p50 / p95 / p99 / worst |
| --- | ---: | --- |
| 120 | 21.435 | 18.475 / 81.598 / 171.730 / 1927.981 ms |
| 240 | 19.657 | 42.051 / 142.718 / 252.349 / 1927.981 ms |
| 360 | 20.231 | 39.777 / 82.160 / 104.003 / 1927.981 ms |
| 480 | 19.378 | 46.707 / 77.160 / 239.958 / 1927.981 ms |
| 600 | 18.991 | 53.538 / 75.876 / 80.394 / 1927.981 ms |
| 720 | 18.744 | 44.333 / 137.973 / 148.609 / 1927.981 ms |

Slow-frame records still include frame 784 at 642.050 ms. The active stream
reported during checkpoints remained `11-ambient beach.mp3` until the later
original M13 music handoff; the file exists in `M13.mix`, so the issue is not
cross-map asset leakage by filename. The problem remains M13 cinematic pacing
and audio mixing/start timing under severe frame loss.

## Decision

Keep Dev157 only as a narrow retained-template improvement. Do not claim it
fixes the ambush freeze, intro A/V sync, scripting, or physical performance.

Next work must target the measured route-level blockers:

- renderer/scene traversal CPU cost during the M13 intro;
- audio stream timing/mixing while the cinematic is frame-starved;
- remaining live asset creates such as sniper/HLOD actors;
- scripted actor sequencing after frame pacing improves.
