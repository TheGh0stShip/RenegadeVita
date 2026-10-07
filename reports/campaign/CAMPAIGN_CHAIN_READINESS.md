# Campaign chain readiness (source + retail-data audit, 2026-10-07)

Evidence class: host source review and a read-only check of retail data
(Vita3K retail tree). This is not a runtime pass. Earlier evidence still
applies: Dev144 Vita3K showed M13 Score into Movie with `R_L01.bik`
decoded. Movie to M01 and every later transition remain unproven on
Vita3K and on physical Vita.

Reproduce: `python3 tools/check_campaign_chain.py --retail-root <ux0>/data/renegade/retail`
(it reads campaign.ini from always.dat in memory and prints only names and status).

## Retail campaign.ini (always.dat)

The retail file has 36 `[Campaign]` flow entries. `0=Movie R_L00` is commented
out. The flow is `Level M13.mix`, Score, then for each of M01 to M11:
`Movie R_Lnn`, `Level Mnn.mix`, Score. The last entry is
`Movie R_Finale.bik IDS_Finale_Movie`. The retail file has no `Message`
directives. Backdrops 0, 1-11, 13, 90, 94 and 96 are present, and each Level has
a matching `Backdrop<n>` (M13 uses 13).

Walker result: 0 failures. All 12 Level archives exist. All 12 movies resolve
case-insensitively, for example `Data\Movies\R_L01.bik` resolves to
`Data/Movies/R_L01.BIK`. The tree has no `R_L00`, and campaign.ini comments it out.

## Per-step chain (`staging/commando/campaign.cpp`)

| Step | Owner (file:line) | Status |
| --- | --- | --- |
| New Campaign → `Start_Campaign` sets State=-1, difficulty, inventory reset, Continue | campaign.cpp:312 | OK (source) |
| First `End_Game` with no world returns early under the Vita menu loop | gameinitmgr.cpp:306 | OK (Dev205 host replay) |
| `Level` → End_Game, Select_Backdrop(mission), campaign mark, Start_Game latch, autosave except M13 | campaign.cpp:406-427 | OK. The mark is set at :420 and consumed at a4_frontend_lifecycle_boundary.cpp:367 |
| Mission success (any map) → intermission | a31_vita_runtime.cpp:6189-6197 | OK. The check is generic and not M13-gated |
| `Score` → Save_Stats before End_Game, ScoreScreen | campaign.cpp:387-404 | OK (Dev144 Vita3K for M13) |
| Score dismissal → `On_Destroy` → Continue | scorescreen.cpp:338 | OK (Dev144 Vita3K) |
| `Movie` → Movie mode, Start_Movie, unlock registry | campaign.cpp:429-463 | OK (R_L01 decoded in Dev144). Other movies: files present only |
| Movie path → BINK provider, case-insensitive resolve | a4_binkmovie_boundary.cpp:1115; renegade_paths.cpp:114,246 | OK. A missing or failed movie sets complete, so the chain does not stall |
| Movie end or skip → `Movie_Done` → Continue | movie.cpp:101,111,328 | OK (source). MovieStartupMode is OFF after startup and is never re-armed in restored sessions |
| Intermission pump exits on the Start_Game latch | a31_vita_runtime.cpp:4046-4080 | OK (source) |
| Campaign state saved to RAM chunk (about 20 of 64 bytes) | a31_vita_runtime.cpp:4118-4145 | OK (source) |
| Outer loop carries source + state into the next session | a30_main.cpp:353-367 | OK. Buffers are 96/64 on both sides (a31_vita_runtime.h:74-76) |
| Restored session: Init, catalog check, Load, `Current_Level_Matches_Archive` | a31_vita_runtime.cpp:4573-4627 | OK (source). Generic `Mxx.mix` resolver (a4_frontend_lifecycle_boundary.cpp:306) |
| Restored session latches the next source without startup movies | a31_vita_runtime.cpp:3837-3839 | OK (source) |
| Encyclopedia discoveries carried across sessions | a31_vita_runtime.cpp:4630-4636 | OK (source) |
| Autosave request survives only the campaign handoff and runs at the first Combat think | combatgmode.cpp:1659; cleared on failure and at any non-handoff session end (a31_vita_runtime.cpp:2892, 4362, 7041) | OK (source). See AUTOSAVE_CHAIN.md. Not runtime-verified for M01-M11 |
| Per-map script spawn presets exist for M13 and M01-M11 | a31_vita_runtime.cpp:3510-3534 | OK |
| After M11: Score → `Movie R_Finale` → Movie_Done → Continue | campaign.cpp:358 (State 35 >= Count-1) | OK (source) |
| End of campaign: State reset, End_Game (no-op), `Display_End_Game_Menu` → LOC_MAIN_MENU | campaign.cpp:358-365; gameinitmgr.cpp:499-509 | OK (source). The main menu is pumped by the intermission loop (owner count > 0) |
| End-menu choices: New Campaign → handoff (State 0, M13); Load/Replay → reload; Tutorial/Practice → deferred; LAN → menu return; Exit → clean process exit | a31_vita_runtime.cpp:4086-4148; a30_main.cpp:326-375 | OK (source) |

The original game has no separate credits step. The finale movie is the last
campaign directive, and credits are reachable from the main menu.

## Defects fixed in this unit

- `tools/test_campaign_discovery_handoff.py` asserted `if (!loaded) break;`.
  The runtime now classifies `A31_CAMPAIGN_HANDOFF_STATE_LOAD_FAILED` before it
  breaks. The assertion was updated to that structure, and 26 campaign and
  frontend contract tests pass.
- Added `tools/check_campaign_chain.py` so the retail chain can be re-audited
  deterministically.

No runtime code defect was found in the campaign chain by source review.

## Open (needs Vita3K/physical evidence)

- Movie → M01 entry, and every M01 → M11 handoff, at runtime.
- Finale movie → main menu → New Campaign or Exit.
- Repeated-session memory and resource behaviour across 12 handoffs.
- Physical Vita/PSTV movie decode for R_L02 to R_L11 and R_Finale.
