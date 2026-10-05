# Original gameplay overlay update and render source wiring

Status: local/uncommitted/unvalidated. Source inspection and edits only;
no staging, patch execution, tests, builds, emulator/device or commit/push work.
Neither a complete Skirmish round nor full multiplayer/campaign is accepted.

## Missing native frame consumers

Original CombatGameModeClass::Think updates MultiHUD, cPlayerManager and
cTeamManager after Combat simulation. Original CombatGameModeClass::Render
renders MultiHUD, bandwidth graph, player/team lists and The_Game presentation
after world rendering. The native frame explicitly calls CombatManager rather
than those full mode methods, so those overlay callers were bypassed.

The full native build already selects original multihud.cpp, player/team manager
and game-data sources. This source selection and MultiHUD initialization did
not establish that name/list geometry was updated or submitted. Original
MultiHUD Think resets/builds projected player-name geometry; manager Think
builds or clears their original cached lists. The_Game Render owns limits,
intermission countdown and gameplay-pending labels. These are presentation
owners, not a replacement scoreboard or simulation.

Source selection also did not invoke the desktop Game_Init process-lifetime
initializers for cPlayerManager, cTeamManager, cGameData or cBandwidthGraph.
Their player/team/game-data text renderers could therefore remain null even once
the frame callers were restored; cPlayerManager Think asserts when MultiHUD is
on and its renderer is absent. Native startup now invokes those four original
initializers after a successful frontend handoff under gameplay HUD coordinates,
before gameplay/session initialization. Teardown invokes their original shutdown
methods while StyleMgr and the asset manager are still alive. The bandwidth
graph provider remains the existing no-op boundary, but its lifecycle contract
is preserved with the group.

## Shared original hooks

The selected commando-a36-original-overlay-owner.patch extracts the existing
call groups as CombatGameModeClass::Process_Overlay_Update and Render_Overlays.
The original desktop mode calls those same methods at its existing locations.
All original call order, list formatting, visibility checks, data ownership and
game-data virtual dispatch remain in the original implementations.

The full native simulation calls the update hook after CombatManager::Think
and before its existing autosave and dialog update. Its existing inactive-mode
early return remains. The existing native gameplay HUD resolution scope covers
name/list geometry generation. The native render calls the original render
hook after world rendering, before message/objective/radio/dialog/text overlays,
inside the existing gameplay HUD presentation scope. Because the native render
entry also serves loading/prewarm frames, it applies the original Combat
renderer active-mode guard specifically to this overlay group. The separate
native world prewarm remains available while Combat is inactive.

This does not call original mode Think again, add another simulation pass,
double network updates, or create players from the presentation boundary.
Radio and original dialog hooks remain separate and occur once. Demo and
headless host gameplay routes retain their previous call policy. Host original
mode uses the shared extracted methods and its existing provider choices.

The original player-list format action was also trapped inside Combat_Keyboard,
which the native frame does not invoke. The selected player-list input patch
extracts that action into a shared CombatGameMode helper. Desktop keeps its
existing EVA/objectives binding. On Vita, a chord-free Select release already
feeds the original CyclePog action; in non-mission games only, the helper also
uses that otherwise inactive edge to call MultiHUDClass::Next_Playerlist_Format.
Mission POG cycling remains unchanged, and the existing Select radio/chat chord
suppression prevents those commands from also changing list format.

Activating the original name overlay exposed one title-service assumption that
was previously dormant: MultiHUD dereferenced GameModeManager's WOL result while
deciding whether to append the original online "recruit" tag. Direct-IP and
Practice intentionally register no retired WOL presenter. The selected optional
network-mode patch uses the existing null-safe provider query at that one check.
The tag remains conditional on an active WOL-compatible mode; name visibility,
team, stealth, rank and distance behavior are unchanged.

The bandwidth graph method is part of the preserved render group but remains
the no-op provider in port/platform/a31_network_options_boundary.cpp. Its graph
implementation is not restored or claimed by this change.

## Spawning already has an original owner

Native simulation calls cNetwork::Update. Original messages.cpp Server_Think
services cGod::Think when Combat is active. cGod's multiplayer state creates a
body only for active in-game players without an existing soldier. The existing
intermission/core restart consumer preserves loading/in-game flags and waiting
player admission. No additional cGod Think or replacement respawn was inserted.
This is a source path, not evidence that every next-round player spawns.

## Evidence index and boundaries

- port/platform/a31_gameplay_boundary.cpp: native simulation/render hook calls,
  existing active-mode guard and gameplay HUD presentation scopes.
- port/platform/vita/a31_vita_runtime.cpp: original player/team/game-data and
  bandwidth-graph process owner initialization and shutdown around gameplay.
- port/patches/commando-a36-original-overlay-owner.patch: shared original call
  groups/declarations; selected after reload-loading presentation in
  tools/stage_sources.sh. Application and compilation remain unexecuted.
- port/patches/commando-a36-player-list-input-owner.patch: shared original
  list-format action and Vita non-mission Select-release adaptation; selected
  after the overlay owner. Application and compilation remain unexecuted.
- port/patches/commando-a36-multihud-optional-network-mode.patch: null-safe
  optional WOL activity query for the original recruit tag; selected after the
  list-input owner. Application and compilation remain unexecuted.
- staging/commando/combatgmode.{cpp,h}: original caller ordering, initialization
  and core shutdown/restart; existing selected patches supply the shared owners.
- staging/commando/multihud.cpp: initialization, projected player names,
  Think/reset/render and visibility checks.
- staging/commando/playermanager.cpp and teammanager.cpp: original renderer
  creation, Think/render, cached list formatting and early resets.
- staging/commando/gamedata.cpp: time/countdown/limits/pending-text rendering.
- staging/commando/messages.cpp and god.cpp: server update and original spawn
  admission; port/platform/vita/a31_vita_runtime.cpp between-frame restart.
- CMakeLists.txt: native original managers/game data and full-port multihud
  source selection; port/compatibility/include/a31_multihud_stub.h selects the
  original header on full native builds.
- port/platform/a31_network_options_boundary.cpp: disabled bandwidth graph.

All additions are process-local C++ calls, not disk/wire or script-format changes.
Existing ARMv7-A little-endian ILP32/ABI gates remain; no dependency or artifact
was rebuilt. Original source and retail data were not modified in place.

Pending acceptance: process owners initialize/shut down once per session,
update/render calls once per active frame, the active guard
prevents overlays over an inactive or torn-down world, names obey original
distance/occlusion/team/stealth
rules, list formatting and Select edge behavior, team scores/time/countdown, clear during
intermission and rebuild after same-map/changed-map reload. Player/team text
renderers retain the gameplay coordinate range captured during Onetime_Init;
cached geometry and game-data clipping across frontend/reload scope changes
still require runtime evidence. Projected names use original current screen
dimensions and camera projection; pixels remain unverified.

Also verify original save/load and campaign HUD regressions, resource balance,
held controls, pause/menu overlays and performance with the newly active callers.
Host, ARM, emulator and matching physical Vita/PSTV evidence remain separate.
No visual, frame-time, next-round spawn or complete-game success is inferred
from restored source calls.
