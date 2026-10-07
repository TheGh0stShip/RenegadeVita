# FPS round 4 — integrated candidate A3.5-dev240

Status: 20 parallel agent work items integrated, host-tested on the combined
tree, ARM-built, packaged and installed into Vita3K (hash-verified, not
launched). **No physical Vita run and no Vita3K launch.** Every gain below is
an unmeasured estimate. Per-item detail: `reports/FPS_R4_<SLUG>.md`.

## Candidate identity

| Item | Value |
| --- | --- |
| Label | `A3.5-dev240` (fast candidate, campaign profile, `RENEGADE_M00_DEMO=0`) |
| Source tree | git tree `6f8848d0976f6bb0380b799b1cc77314d4578e72` (branch `fps-r4/integration`, before this report) |
| Upstream | `3e00c3a1b97381bb28be89a35b856375e0629a08` |
| Staging | 546 ordered patches, inventory PASS, `--fuzz=0`, regeneration leaves tracked staging byte-identical |
| VPK SHA-256 | `4ded7a621d7787ca12a2571f0634794f213c55238a3ca3c09665ba975deb4180` |
| ELF SHA-256 | `ecba4a0fdbafa12651663bebdb7cbff1e582a47c51f5ac18d6740ef317bccec2` |
| VPK contents | `eboot.bin`, `sce_sys/param.sfo` and LiveArea art only — no retail data |
| Vita3K | `INSTALLED_NOT_LAUNCHED`, installed SELF hash verified |
| Artifacts | `local-builder/dist/*A3.5-dev240*` (+ `A3.5-dev240-vita3k-receipt/`) |
| Runtime log | `ux0:data/renegade/user/logs/a35-dev240-runtime.log` |

## Changes (all default-on unless noted; every switch is a file under `ux0:data/renegade/user/config/`)

| Area | Change | Switch | Est. gain |
| --- | --- | --- | --- |
| Mesh submission | Per-frame (non-static-cache) batches, skins and lit instances, drawn from client vertex arrays, one `glDrawElements` per batch | `vertex-array-v1.flag` `RVVA1 0` | 1–4 ms; risk: per-draw vertex-program re-patch |
| DX8 boundary | Particles/sorted/HUD/2D/decal vertices appended as packed records via new vitaGL patch `vitagl-immediate-vertex-records` | `RVRC1 7` (bit 8 off) | 0.5–3 ms in HUD/particle-heavy frames |
| Static mesh cache | Lit instances keyed per instance, VOLATILE recovery with backoff, oversize separated, rebuild-reason telemetry | `static-mesh-cache-v1.flag` `RVSM1 0` | 0–3 ms where lit copies repeat |
| Skin | Verified per-frame deformation reuse across material passes / cameras | `skin-deform-cache-v1.flag` `RVSD1 0` | ≤0.5 ms |
| GL state | Exact shadow for raster state and transforms (−31 % GL calls in sim) | `gl-state-shadow-v1.flag` `RVGS1 0` | 0.5–1.5 ms |
| Texture state | Sampler requests coalesced per `TextureClass::Apply`, texenv shadow, narrow delete invalidation | `RVRC1 E` (bit 0 off) | 0.05–0.2 ms |
| HUD/text | Help/objective text rebuilt only on change (new patch `combat-a36-hud-text-build-once`); HUD glyphs pre-rasterised while loading | — | removes ~1 atlas upload/frame in those windows |
| LOD | No saved Performance record → original slow-PC auto-config: geometry budget 0/0 (was 4000/4000); surface effects kept Full | in-game Performance options; build `RENEGADE_VITA_DEFAULT_GEOMETRY_DETAIL` | 1–4 ms sparse scenes; visibly lower LOD heads/weapons |
| Internal resolution | Display scan-out scaling 75/67/50 % or auto (HUD also lower-res) | `internal-resolution-v1.flag` `RVIR1 100\|75\|67\|50\|auto` — **default off** | only if GPU-bound |
| Loading prewarm | Soldier animations, effect PCM and nearest static geometry pre-built on the loading screen | `preload-v1.flag` `RVPL1 0..7` | removes first-use hitches |
| Shader cache | FFP GXP cache moved to `ux0:data/renegade/cache/ffp-…`, validated reads, `uint8` wrap fix, record + boot pre-warm (new patch `vitagl-ffp-program-cache`) | `ffp-prewarm-v1.flag` `RVPW1 0` | removes 20–200 ms compile hitches from 2nd launch; **1st launch recompiles all** |
| Audio | MPEG span reads, MPEG opens before the provider lock, no stream image copy; `AIL_set_3D_position` queues instead of waiting on the mixer | — | 0.1–0.4 ms + less jitter |
| WWMath / animation | Inline exact Floor/Ceil, int range checks, single-precision quaternion→matrix; inlined raw-animation sampler (all proven bit-identical) | — | 0.2–0.7 ms |
| Profiler | Hot scopes sampled (first 2 per name per frame exact), stack-range thread test, clock-cost log; **engine WWPROFILE scopes now actually compiled in** (staged `wwdebug` include was missing); wheel.cpp opted out | `frame-profile-v1.flag` `RVFP1 0` | −1…−8 ms vs unsampled live scopes; adds its own cost vs dev238 where engine scopes were absent |
| Diagnostics | VIS census, vitaGL pool high-water/overrun, Combat cast counters, awake/hibernating soldiers, texture-state / gl-state-shadow / skin / vertex-array lines | `vitagl-sizing-v1.flag` `RVGX1 …` (sizing A/B only) | — |
| Codegen | `RENEGADE_VITA_SIM_O3` option, **default OFF** (no hot-function gain shown) | build option | — |
| Heap | Material-pass task free list, static remark copy, WWAudio completed-list retain patch | — | small |

Report-only findings: original VIS/PVS culling is already active (no gain
available); no derived-data disk cache is justified (card read ≈ recompute);
thread placement and vitaGL memory placement are already sound; DataSafe and
`HumanAnimControlClass` leads are not per-frame costs.

## Integration fixes made by the coordinator

- Duplicate `Build_Matrix3D` narrowing: kept the WWMath patch, dropped the
  animation agent's narrower duplicate, retargeted its identity test.
- Merged conflicting hunks in the renderer, runtime and `build_vitagl_demo.sh`
  (both new vitaGL patches applied in order; all eight apply at fuzz 0 to the
  pinned source).
- **Pre-existing link failure on main** (since `17d6d5f`): block-scope
  `extern` of `g_b_core_restart`/`g_client_quit` inside the runtime's anonymous
  namespace; fixed with file-scope declarations (also covers the new soldier
  counters).
- **Pre-existing stale build check**: both build scripts required the old
  8-argument `A31_Vita_Run_Interactive_Runtime` symbol; updated.
- Shader pre-warm flag prefix renamed `RVFP1` → `RVPW1` (collided with the
  frame-profile flag prefix).
- Four harnesses aligned with the combined renderer (gxm tuning, static mesh
  equivalence, vertex-array submission, indexed vertex records).

## Host evidence (combined tree)

24 new/updated modules pass, including bit-identity proofs (WWMath exhaustive
2^32, raw-animation 5 MB stream, audio mixer vs real mpg123), GL-shim
equivalence for vertex arrays / records / render-state / sampler / static
cache, and sanitizer runs. Two contract tests fail identically on the base
commit (pre-existing, stale text anchors):
`test_vita_m13_cinematic_preparation.test_m01_referenced_textures_prepare_before_first_world_frame`
and `test_vita_skin_submission_contract.test_vita_boundary_uses_original_material_color_with_textured_skin_passthrough`.

## Hardware measurement plan (fixed M13 ambush + M01 beach route)

1. Default run: frame p50/p95/p99/worst, `A3.6 frame-profile` (now incl.
   engine scopes), `A4 combat casts`, `vitagl-pools` (any
   `immediate_overruns` > 0 is a defect), `static-mesh-cache`,
   `vertex-array`, `gl-state-shadow`, `texture-state`, `ffp-program-cache`,
   `vis-census`, `frame-profile: clock-cost`.
2. A/B one switch at a time: `RVVA1 0`, `RVGS1 0`, `RVSM1 0`, `RVFP1 0`,
   `RVPL1 0`, `RVIR1 75`; visual check of skins, lit vehicles, decals,
   alpha-tested foliage, HUD text, movies.
3. Launch twice: the first launch rebuilds the FFP shader cache.
4. Fresh options file to confirm the Low-geometry default, then Geometry High.
