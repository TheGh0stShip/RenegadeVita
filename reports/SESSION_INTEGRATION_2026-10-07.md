# Cross-session integration — A3.5-dev241 (2026-10-07)

Status: the work from three concurrent sessions is integrated onto one tree.
That tree has been ARM-built, packaged and installed into Vita3K (installed
SELF hash verified, not launched). **No physical Vita run.** Nothing here is
physical acceptance.

## Sessions evaluated

| Session | Work | Disposition |
| --- | --- | --- |
| Campaign development (M01–M13 readiness, pushes 1–5) | ~120 agent commits | Already on `main` (`abdae90`). Agent tips whose subjects differ from main were checked by content. They landed reworded (e.g. ledger audit `f7c904b`, M09 evac buffer `8fbe400`, log cap `c639b6a`, M07 audit `5fb1cdf`). |
| FPS optimization (round 4, A3.5-dev240) | 20 items squash-integrated on `fps-r4/integration` | Merged. Only report-touchup commits were left on agent branches. Round-3 WIPs and `candidate/skin-*` prototypes are superseded by round 4 (`FPS_R3_RECOVERY_INVENTORY.md`). |
| Tutorial optimization (round 1) | 20 items on `tutorial-r1/integration` (built on dev240) | Merged; see `reports/tutorial/TUT_R1_INTEGRATION.md`. |

Three un-landed early campaign-agent commits were deliberately **not** taken:

- FreeType face `std::deque` (no caller holds a face pointer across lookups).
- Target-box diagnostic pre-check (the callee already returns once its budget is spent).
- Clearing the LSD name on a failed save peek (changes original error-path behaviour without a demonstrated defect).

Other branches with no unique work: `feature/a35-dev82-retail-frontend`
(historical), `gh-pages` (site), `d3dvita-demo` (separate variant).

## Integration fixes

- Merge of `main` into `tutorial-r1/integration`:
  - Kept both resume counters: the RVCK1 clock watchdog, and the app-resume frame-clock rebase.
  - Ordered main's sha-anchored staging block before the tutorial patches.
  - Staging: 623 patches, inventory PASS.
  - Restored the 755 staged-file modes. They were lost because a fresh upstream clone checks out as 644 and `cp` carries that mode over.
- Host-test regressions from the tutorial round:
  - Bink audio harness: stubbed RVCK1 thread placement.
  - ADPCM baseline: added the include path for `renegade_audio_cost.h`.
  - `renegade_load_io.h`: fixed the `-Wextra` enum/unsigned ternary.
- Host-test regression from campaign push 5: the M09 camera probe now links with a host `A30_Vita_Log`.
- Host build of `ww3d_dx8_boundary.cpp` / `ww3d_vita_renderer.cpp` (shared with the canonical `a22_asset_selftest` target):
  - Frame-profile header include moved outside the Vita guard.
  - Host no-op added for `Invalidate_Native_State_Cache`.

## Evidence

| Item | Value |
| --- | --- |
| Label | `A3.5-dev241` (fast candidate, campaign profile, `RENEGADE_M00_DEMO=0`) |
| VPK SHA-256 | `67860e22f64b496a80ccae531fc0f250a645fd35f804a0044740c3a892952603` |
| ELF SHA-256 | `5d6348ca9220cc844cc1e5d8eb44375df015b8307702010144b2f16939755b62` |
| VPK contents | `eboot.bin`, `sce_sys/param.sfo`, LiveArea art only |
| Vita3K | `INSTALLED_NOT_LAUNCHED`, SELF hash verified |
| Artifacts | `local-builder/dist/*A3.5-dev241*` |
| Runtime log | `ux0:data/renegade/user/logs/a35-dev241-runtime.log` |
| Pure host lane | 176 modules PASS (5 known failures) |
| Compiled/sanitizer lanes (97 modules touched by the delta) | PASS, except the pre-existing failures below |

Pre-existing failures, all also failing on `main`:

- `test_vita_mesh_batch`: anchor stale since dev4 (`26c5160`).
- `test_vitagl_dds_chain`: `Probed_Upload_DXT_Chain` extraction stale.
- `test_renegade_file_factory_availability`: the TSan variant exits 66 on this WSL kernel.
- The five failures listed in `tools/host_test_known_failures.json`.

## Known gap: the canonical builder

`bash ./tools/build.sh` has not been used since about dev116. Every candidate
since then, including dev225–dev240, came from `tools/build_fast_candidate.sh`.
Its host `a22_asset_selftest` target no longer links. The missing symbols
include `AnimatedSoundMgrClass`, `Debug_Statistics::Record_Texture`,
`PointGroupClass::_Init/_Shutdown` and `RenegadeVita_Release_DX8_Render_Target`.
Restoring the canonical builder is a separate work item.

## Known gap: M00 demo build profile

A `RENEGADE_M00_DEMO=1` compile check of this tree fails in several files.
It fails the same way on `main`; this merge did not cause it.

- `renegade_directinput.cpp`: the camera chord uses `The_Game`/`IS_MISSION`
  without `gamedata.h` (since `17d6d5f`).
- `a31_client_connect_boundary.cpp`: `A4_Frontend_Resolve_Skirmish_Archive`.
- `a31_vita_runtime.cpp`, which hits several separate errors:
  - Twiddler definition IDs.
  - `Get_Killed_Explosion_ID`.
  - Direct client text.
  - Local load-failure recovery.
  - Variables that only exist in the campaign build (`selected_archive`, `world_first_render_pending`).

The tutorial round's `Read_Vsync_Enabled` fix is necessary but not sufficient.
The published demo VPKs (Renegade-Vita-Demo) are unaffected. Restoring the
demo profile is a separate work item.

## Hardware plan

Use the dev240 plan in `FPS_ROUND4_INTEGRATION.md`, plus the tutorial
benchmark/A-B in `tutorial/TUT_R1_INTEGRATION.md`. Launch twice: the first
launch rebuilds the FFP shader cache.

## Follow-up: A3.5-dev242

dev241 never reached the frontend in Vita3K: it stopped at the global
conversation load (`CONV10.CDB records=0`).

- **Cause:** the A36 chunk structural-admission patch made a speculative
  `Peek_Next_Chunk` set the sticky load error. The legacy one-byte category
  probe in `Read_Conversation_Category` performs exactly that peek, so the
  retail database was rejected.
- **Fix:** `wwlib-a39-peek-next-chunk-speculative.patch`, plus the
  `tools.test_chunk_peek_speculative` host test.
- **Artifacts:** VPK `681d74368a8ad0425958d7634b2323c2abd009b5f892eb7a5b50f0ac6b5af706`;
  installed eboot `0abef9f9c4847c2c2d48e7aede8b76afab1e0bacc8f7215671c721e8ae41059c`.
- **Deployment:** Vita3K and the physical Vita were both updated, and neither was launched.
  Receipt: `build/device-backups/A3.5-dev242-20261007/`.
