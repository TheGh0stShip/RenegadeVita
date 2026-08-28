# Codex Engineering Handoff

## 2026-08-28 Retail Frontend Integration Candidate

Branch: `feature/a35-dev82-retail-frontend`

Worktree:
`/home/steve/projects/RenegadeVitaBuilder/workspace/retail-frontend-a35-dev82`

Integration base: `4feabddfbf8c619be37d32e2326d3e6164d6f505`, a local
snapshot of the active dev82 tree made so this worker did not edit
`/home/steve/projects/RenegadeVitaBuilder/workspace/active` while another
session owned core M00 work. Upstream public baseline below that snapshot:
`de85435` (`origin/main`).

Status: source/build candidate only. No physical Vita acceptance is claimed, no
Vita deployment was attempted, and no retail data or movie files were
transferred.

Validation completed in this branch:

- `bash ./tools/stage_sources.sh`: pass; deterministic zero-fuzz staging
  applies the two new A4 frontend patches and leaves no `.orig`/`.rej` debris.
- `python3 -m unittest tools.test_vita_loading_screen_contract
  tools.test_stage_sources_incremental_contract
  tools.test_mission_conversation_diagnostics_contract
  tools.test_a4_original_frontend_contract`: pass, 30 tests.
- `python3 tools/generate_integration_report.py --root . --output
  /tmp/a4-source-report.json --milestone A3.5-dev82`: pass;
  `original_source_files_compiled=508`, `a4_frontend_boundary_files=6`,
  `patch_count=129`.
- Host frontend runtime link: `cmake --build
  build/host-a30-definitions-frontend --target a31_interactive_runtime
  --parallel $(nproc)`: pass.
- `bash ./tools/build_fast_candidate.sh`: pass.
- Canonical `bash ./tools/build.sh` with retained host-validation log reuse:
  pass. Local retail data was not copied or transferred; the full host runtime
  was not rerun in this isolated worktree because no local retail root was
  available.

Canonical artifacts:

- VPK:
  `dist/RenegadeVita-A3.5-dev82.vpk`
  SHA-256 `a00d6021581d95272519c8084f592fc0435866412c5df92765749295fdae90d0`
- ELF:
  `dist/RenegadeVita-A3.5-dev82.elf`
  SHA-256 `6884c0c665aeb543ee68a5109fc724f2f158e94aa0f991e71d76ee22692a9580`
- Diagnostics:
  `dist/A3.5-dev82-BUILD-DIAGNOSTICS-20260828-160320.zip`
  SHA-256 `6e330166e45fd993a1040a4c8284496d7f780cdca4deb64e0772f75fe2b0e559`
- VPK inventory: `sce_sys/param.sfo`, `eboot.bin`; retail data packaged:
  none.

Implemented frontend path:

- `RENEGADE_A4_ORIGINAL_FRONTEND` admits the original Commando/WWUI frontend
  owners into the Vita source closure: `MovieGameModeClass`,
  `MenuGameModeClass2`, `RenegadeDialogMgrClass`, `MainMenuDialogClass`,
  Start-SP/Difficulty/Load-SP dialog surfaces, `DialogMgrClass`, `WWUIInput`,
  `MenuDialog`, list/button/text controls, `StyleMgrClass`, and the existing
  dialog resource provider.
- Startup movie requests stay under original `MovieGameModeClass` ownership.
  `BINKMovie` is a platform boundary for this pass; it logs requested movies,
  records traceable skips, imports no proprietary RAD code, and packages no
  retail movie assets.
- Vita menu navigation uses the existing DirectInput/WWUI path. While the A4
  frontend menu loop is active, D-pad buttons emit WWUI virtual arrow keys,
  Cross emits `VK_RETURN`, Circle emits `VK_ESCAPE`, and Select emits `VK_TAB`.
  After menu handoff, the current dev82 gameplay D-pad weapon/zoom mapping,
  Triangle use, Square reload, and shoulders remain unchanged.
- Tutorial selection from original `StartSPGameDialogClass` still calls
  original `GameInitMgrClass::Start_Game("M00_Tutorial.mix", -1, 0)`. The
  Vita boundary latches that request and then reuses the existing direct M00
  route until the full original menu-to-combat route is proven equivalent.

Deterministic staged-source patches added:

- `port/patches/commando-a4-gameinitmgr-frontend-start-latch.patch`
- `port/patches/commando-a4-movie-vita-provider-boundary.patch`

Validation to rerun before merge:

- `bash ./tools/stage_sources.sh`
- `python3 -m unittest tools.test_vita_loading_screen_contract`
- `python3 -m unittest tools.test_stage_sources_incremental_contract`
- `python3 -m unittest tools.test_a4_original_frontend_contract`
- `bash ./tools/build_fast_candidate.sh`
- `bash ./tools/build.sh`

Open integration cautions:

- Bink movie decode/playback remains fail-closed. A real decoder must be added
  only below the original movie/Bink abstraction with documented licensing and
  build impact.
- Physical menu rendering, focus behavior, back/quit behavior, options/load
  surfaces, and tutorial handoff have not been accepted on Vita.
- `reports/CODEX_HANDOFF.md` existed in the active tree but was not tracked in
  the isolated worktree base; this branch adds it explicitly for merge.
