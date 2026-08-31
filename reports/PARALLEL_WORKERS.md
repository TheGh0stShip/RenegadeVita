# Parallel Worker Handoffs

## 2026-08-28 Retail Frontend And Intro Movies Worker

This prompt is intended for a separate Codex 5.5 Xtra High session. It is
recorded here so future sessions can resume or integrate that worker without
guessing at scope.

Status update from the worker, 2026-08-28: the worker selected the relevant
project skills in its session, read the repo contract/status files, observed
that `<workspace>` contains
substantial uncommitted dev82-era work, and correctly decided to create or use
an isolated branch/worktree rather than writing into active. It reported that
the current reports still name dev79 while active/handoff name dev82 in
progress, so it planned to inspect refs, staging patches, and frontend-linked
targets before creating the isolated workspace.

```text
You are working on the native PS Vita port of Command & Conquer: Renegade in:

<workspace>

Do not write directly into that active dev82 tree concurrently with the core M00
work. Create an isolated git worktree or branch, for example:

feature/a35-dev82-retail-frontend

Your goal is to build the retail frontend and intro movie path so it can be
placed directly into the existing A3.5-dev82 work. The core dev82 worker is
focused on M00 gameplay, HUD, loading, textures, reload animations, sniper
scope, cache/prewarm, and physical-test artifacts. Your work must complement
that, not fork or replace it.

Read these first:

- AGENTS.md
- reports/PROGRAM_CHARTER.md
- reports/PORT_STATUS.md
- reports/BUILD_STATE.json
- reports/CODEX_HANDOFF.md
- reports/MILESTONE_ROADMAP.md
- reports/CAPABILITY_MATRIX.md
- reports/KNOWN_GAPS.md
- reports/LIVE_PROGRESS.md

Architecture rules:

- This is a native Vita port of the original EA/Westwood Renegade source.
- Preserve original game/engine ownership above platform boundaries.
- Do not revive the abandoned A1/RVA/custom renderer/custom game-loop path.
- Keep upstream source pristine where possible.
- Use deterministic patches under port/patches/ or staged original-owner files.
- Do not package or copy retail data or retail movies into the VPK.
- Do not auto-deploy over USB or FTP.

Functional target:

- Reconnect the original Commando frontend/menu flow on Vita.
- Implement the startup sequence expected by the retail game:
  EA intro, Renegade intro, Westwood intro, then main menu.
- Implement the main menu so it behaves 1:1 with retail where practical:
  visual presentation, menu hierarchy, focus behavior, controller navigation,
  activate/back actions, New Tutorial/Mission start, Load, Options, Quit, and
  return paths.
- Reuse the existing dev82 direct M00 loading path for the tutorial entry point.
- Do not add a duplicate loader, duplicate HUD owner, duplicate input owner, or
  second loading progress bar.
- Preserve the existing Vita filesystem contract:
  ux0:data/renegade/retail/Data is the read-only retail install, writable files
  go under ux0:data/renegade/user, cache goes under ux0:data/renegade/cache.

Movie/Bink rules:

- The original source references Bink/RAD. Do not import proprietary RAD source,
  binaries, or incompatible code.
- If a legal decoder integration is feasible from available project code and
  dependencies, put it below the original movie boundary.
- If full movie playback is not feasible, implement a fail-closed Vita movie
  boundary that logs exactly which movie would have played and advances through
  the original startup/menu state without crashing.
- Do not break the future path for real playback.

Likely source areas to inspect:

- staging/commando and upstream/Commando frontend/menu/dialog sources
- movie/Bink abstractions and any existing stubs under port/stubs
- port/platform/vita startup/runtime owners
- port/platform input boundary and controller mapping
- current loading screen/HUD/dialogue patches under port/patches
- tools/stage_sources.sh
- CMakeLists.txt
- tools/build.sh
- tools/build_fast_candidate.sh
- existing host contract tests under tools/test_*.py

Expected deliverables:

- Branch/worktree name and exact base commit.
- Changed files and patch inventory.
- Any new deterministic port/patches entries.
- Focused host tests/contracts for menu navigation, startup movie sequencing,
  and tutorial-entry handoff.
- A canonical build if the branch reaches buildable state.
- Documentation updates in reports/ describing what was implemented, what is
  stubbed, and how the core dev82 worker should merge it.
- No claim of physical acceptance unless the user actually tests on Vita.
```
