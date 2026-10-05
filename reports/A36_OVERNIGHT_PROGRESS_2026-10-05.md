# A3.6 overnight development report — 2026-10-05

## Review window and evidence boundary

This report covers the eight-hour local window from **2026-10-05 00:16:40
through 08:16:40 CDT**. It is based on the active WSL worktree, file timestamps,
the deterministic patch inventory, current diffs, and the contemporaneous
entries in `LIVE_PROGRESS.md` and the focused subsystem reports.

The window contains **248 relevant touched files**:

- 194 deterministic staging patches;
- 27 native platform, renderer, audio, filesystem, or compatibility files;
- 13 engineering reports;
- 12 local tools and contract probes;
- `CMakeLists.txt` and one CMake source manifest.

At the pre-report snapshot, 177 of those files were untracked and 69 were
tracked modifications. Two tracked compatibility headers had overnight mtimes
but content identical to `HEAD`, accounting for the remainder. These figures
describe the overnight worktree, not accepted runtime functionality; this
report itself adds one further untracked file after that snapshot.

No commit was created inside the measured eight-hour window; `main` and
`origin/main` remained at `9f05633` during that period. After this omission was
identified during review, the complete validated source set was committed on
`main` as **`17d6d5f`** (`Wire campaign saves frontend and repeated sessions`):
509 files, 35,187 insertions and 2,341 deletions. Publication to `origin/main`
is reported separately below because a local commit and a successful push are
distinct evidence.

## Executive result

The overnight work concentrated on wiring original game owners together and
making failures explicit instead of allowing partial worlds, saves, dialogs,
or resources to continue. The largest completed source work was:

1. campaign and Practice completion/restart ownership;
2. transactional save/load admission and failure propagation across the full
   dynamic world graph;
3. original frontend, pause, Controls, Movies, Credits, Technical Options,
   multiplayer-information, LAN, and Direct-IP routing;
4. renderer resource ownership for repeated worlds, render targets, Dazzle,
   prototypes, animated primitives, and material passes;
5. audio deadline, stream lifetime, and movie teardown fixes;
6. strict canonical WWUI resource contracts and stronger artifact identity
   gates;
7. complete campaign-script source selection and explicit source-closure
   reconciliation.

All results in this report remain **source inspection and deterministic local
integrity evidence**. No compiler, test suite, Vita3K instance, Vita, or PSTV
accepted the overnight changes.

## Campaign, mission completion, and frontend lifecycle

The campaign path gained source closure for the original success, failure,
score, movie, next-level, save, and restore owners:

- Campaign catalog loading now rejects missing, empty, or structurally invalid
  `campaign.ini` data instead of treating it as a completed campaign.
- Campaign catalog reinitialization, backdrop selection, level-start
  provenance, restored campaign/source binding, and inventory publication were
  connected to the native lifecycle.
- Original score-screen continuation, mission-complete input handoff,
  autosave ownership, replay flow, death/failure routing, and classified load
  failure recovery were retained.
- The level-owned cinematic camera is released at the correct lifecycle edge.
- M13 finale delivery gained bounded trace points, while beacon save/load now
  retains warning state, weapon identity, and armed-audio continuity without
  replaying the transition.
- The 13 campaign mission translation units are explicitly asserted as a
  subset of the released `Scripts.dsp` inventory.

Primary evidence:

- `reports/SINGLE_PLAYER_COMPLETION_WIRING.md`
- `reports/M13_QUICKSAVE_HANG.md`
- `port/patches/commando-a36-campaign-*.patch`
- `port/patches/commando-a36-original-{death,replay,win-screen}.patch`
- `port/patches/scripts-a36-m13-finale-delivery-trace.patch`
- `port/patches/combat-a36-beacon-save-state.patch`

## Save/load transaction and corruption rejection

The overnight pass closed the source-level result chain from the outer save
transaction through the nested original subsystems. This was the broadest work
unit of the window.

- Manual, quick, autosave, and cGod paths now propagate logical serialization,
  file-close, and atomic-replacement failures.
- Failed saves abort the pending write and retain the prior valid save.
- The player-save envelope validates the ordered level-info and level-data
  chunks before world publication.
- Required dynamic save owners are enforced exactly once: Combat,
  conversations, dynamic physics, encyclopedia, dynamic audio, map, and
  Commando state.
- Combat validates its fixed manager children, including game objects,
  spawners, scripts, objectives, radar, weapon view, weather, HUD, bullets,
  observers, background, cover, and screen fade.
- Commando state validates Network, cGod, Campaign, player lists, per-player
  fields, and campaign indices before publishing process globals.
- Physics, audio, W3D objects, buildings, bosses, definitions, scripts,
  observers, timers, objectives, spawners, and game-object hierarchies now
  propagate their child load/save results.
- Rejected loads quarantine and discard post-load callbacks instead of running
  them over a partial world.
- Pointer remapping distinguishes serialized null from unresolved non-null
  tokens and rejects unresolved references before behavioral post-load work.
- Chunk parsing retains structural errors for truncation, invalid nesting,
  out-of-parent sizes, failed seeks, and wrong-width values.
- Terminal `SINGLE_DEAD` snapshots are rejected because the released integer
  cannot identify whether player death or mission failure owns continuation.

This preserves the released chunk representation and original subsystem
ownership; it adds admission and result checks rather than a new save format.

Primary evidence:

- `reports/SINGLE_PLAYER_COMPLETION_WIRING.md`
- `reports/MANUAL_SAVE_FAILURE_WIRING.md`
- `port/patches/wwsaveload-a36-*.patch`
- `port/patches/combat-a36-*-admission.patch`
- `port/patches/combat-a36-*-save-status.patch`
- `port/patches/commando-a36-*-save-*.patch`
- `port/patches/wwphys-a36-*.patch`
- `port/patches/wwaudio-a36-*.patch`

## Practice, map cycling, LAN, and Direct-IP

Original multiplayer/practice ownership was connected without substituting a
new gameplay loop:

- Local Practice completion reaches original game-over processing, win screen,
  intermission, map rotation, and between-frame core restart.
- One-entry Practice cycles replay the same map; configured multi-map cycles
  advance and wrap under original `Rotate_Map` behavior. Launch replaces only
  slot zero and preserves higher configured slots.
- Changed-map restart prepares and publishes the next archive at the original
  teardown/restart boundary. Invalid sources and archives remain classified
  failures and cannot be counted as a successful session.
- Direct-IP repeated-round state gained generation, identity, provider, and
  replicated-player admission checks.
- The original C&C reference pause menu is reachable for Practice, LAN, and
  Direct-IP while gameplay/network simulation retains multiplayer ownership.
- Original battle, team, server, player-list, public/team chat, radio, Help,
  team-selection, LAN browser, LAN host, and LAN server-preset presenters were
  connected where their released owners are available.
- LAN connection refusal no longer compiles or falls through to an excluded WOL
  owner.
- The Internet control enters the narrow Direct-IP provider dialog; retired
  WOL/GameSpy service UI remains excluded.

Primary evidence:

- `reports/PRACTICE_COMPLETION_WIRING.md`
- `reports/MULTIPLAYER_COMPATIBILITY.md`
- `reports/LAN_SERVER_PRESET_WIRING.md`
- `reports/ORIGINAL_CHAT_ROUTE_WIRING.md`
- `reports/ORIGINAL_RADIO_ROUTE_WIRING.md`
- `port/patches/commando-a36-{core-restart-owner,multiplayer-pause-route,lan-connect-refusal}.patch`

## Original menus, Controls, Options, and resources

The combined frontend now retains original dialog ownership for its supported
surfaces:

- Controls links the released `InputConfigClass` record implementation and all
  five original child tabs.
- The Vita control profile preserves the original logical secondary-fire/use
  binding used by sniper scope, while runtime scope behavior remains unverified.
- Movies and Credits use their original factory routes.
- Technical Options uses the original direct `OptionsMenuClass::On_Command`
  route into linked Audio, Video, and Performance tabs; its null factory slot is
  intentional.
- Canonical resource generation now rejects missing required controls for the
  Options tabs, Controls tabs, multiplayer Help, chat, win screen, and restored
  multiplayer presenters.
- Unsupported desktop audio-device, display-mode, and WOL multiplayer-option
  controls remain unavailable at the platform boundary.

Primary evidence:

- `tools/generate_wwui_dialog_templates.py`
- `port/patches/commando-a36-original-{controls,movies,credits}-route.patch`
- `port/patches/commando-a36-input-config-*.patch`
- `reports/LIVE_PROGRESS.md`

## Renderer, W3D, repeated worlds, and effects

Renderer work focused on preserving original WW3D ownership across resource
replacement and repeated map loads:

- Native generated render targets gained texture/FBO/depth ownership, clear,
  binding, viewport restoration, readback, and shutdown paths.
- Original projector enablement is no longer unconditionally disabled by the
  full-port boundary.
- Repeated-world cleanup releases physics grid textures and invalidates native
  user-lighting/static-mesh caches.
- The native material-pass queue retains original procedural/projector pass
  ownership.
- Dazzle definitions, fixed prototypes, animated primitives, aggregate W3D
  loads, and asset dependency loads now reject partial child state.
- Animated sound restoration and primitive animation admission were connected.
- Build artifact checks now require the active original
  `MeshLoaderClass::Load_W3D` and `MeshModelClass::Load_W3D` owners.
- `meshbuild.cpp`, `polyinfo.cpp`, and `stripoptimizer.cpp` remain deliberately
  excluded after caller-level review showed only obsolete-disabled or desktop
  DX8 consumers. No replacement mesh builder was invented.

Primary evidence:

- `reports/NATIVE_RENDER_TARGET_BOUNDARY.md`
- `reports/PROCEDURAL_MATERIAL_OWNER_REVIEW.md`
- `port/renderer/vita/ww3d_vita_renderer.cpp`
- `port/renderer/vita/ww3d_dx8_boundary.cpp`
- `port/patches/ww3d2-a36-*.patch`
- `tools/build.sh`
- `tools/build_fast_candidate.sh`

## Audio, movie, animation, and frame-time ownership

- Stream preparation and file I/O were moved outside the audio deadline mutex.
- Deadline starvation produces bounded silence, and detailed timing is opt-in
  rather than paid every frame.
- Pooled stream storage is released across stop/restart/destruction.
- Movie audio teardown and skip-edge lifetime were tightened for repeated
  playback and frontend return.
- The game thread now yields to audio service during bounded long work.
- Action completion uses logical time for stall detection, and weapon/action
  load status is propagated.
- Pathfinding time slicing avoids unsigned budget underflow.

Primary evidence:

- `port/audio/vita/renegade_miles_provider.cpp`
- `port/audio/vita/renegade_miles_runtime_stats.h`
- `port/patches/commando-a36-{audio-service-yield,movie-audio-teardown,movie-skip-edge-lifetime}.patch`
- `port/patches/combat-a36-action-*.patch`
- `port/patches/wwphys-a36-path-timeslice-underflow.patch`

## Definitions, translated data, and asset transactions

The source now treats definition and asset publication as a transaction:

- definition catalogs publish only after child definitions load successfully;
- rejected definitions roll back registered factories and singleton globals;
- defense, EVA, global, purchase, translated-string, audio, W3D, Dazzle,
  prototype, and dependency owners propagate failure;
- campaign catalog and load inventories publish only after their complete source
  generation is admitted.

This work prevents a partial retail-data graph from authorizing gameplay. It
does not change retail formats or redistribute data.

## Deterministic build and source closure

The deterministic staging stack ended the review window at:

- **497 ordered patches**;
- inventory SHA-256
  `b5bdbe7ff8fcd544749e29a0e92f6e3eda3198a5ddc068fc64bc2c900e98c751`;
- zero-fuzz staging consistency PASS;
- canonical combined campaign/multiplayer dialog generation PASS;
- `git diff --check` PASS;
- no `.orig` or `.rej` debris found.

The inventory grew through several retained intermediate states during the
window; the focused save report records an earlier 446-patch checkpoint. The
497-patch hash above is the final authoritative state for this report.

No canonical or fast build was run. Newly added symbol gates and all ARM/ELF,
SELF, VPK, Vita3K, Vita, and PSTV gates remain unexecuted.

## Explicit exclusions and unresolved work

The overnight work did **not** establish any of the following:

- successful ARM compilation or linkage;
- correct generated ELF/SELF/VPK identity;
- Vita3K behavior;
- physical Vita or PSTV correctness;
- acceptable campaign frame time, memory high-water, or soak stability;
- successful quicksave/reload after the previously observed freeze;
- complete M13 finale and M01 transition on hardware;
- physical sniper-scope input;
- completed Practice round, automatic restart, LAN session, or Direct-IP
  repeated round;
- correct pixels for projectors, Dazzle, render targets, menus, or overlays;
- complete campaign playthrough.

The validation hold remained active throughout the window. These are open
evidence gates, not implied failures of the source work.

## Publication and automation status

- No commit was created during the eight-hour measurement window.
- The reviewed implementation was subsequently committed on `main` as
  `17d6d5f`; this report is a separate follow-up commit.
- Push status must be recorded from the actual remote operation and is not
  inferred from the local branch.
- No pull request was created.
- No GitHub Actions runner was used.
- No GitHub-hosted build, test, analysis, or automation was used.
- No physical device filesystem was modified.

Before publication, the local work still requires the authorized validation
sequence: focused local checks, ARM build/link, artifact inspection, package
identity, Vita3K installation/hash verification, then separately authorized
physical Vita/PSTV acceptance.

## Review index

Start with these records for detail:

1. `reports/LIVE_PROGRESS.md` — chronological work units and evidence limits.
2. `reports/SINGLE_PLAYER_COMPLETION_WIRING.md` — campaign/save/load closure.
3. `reports/PRACTICE_COMPLETION_WIRING.md` — Practice/restart/map-cycle closure.
4. `reports/MULTIPLAYER_COMPATIBILITY.md` — LAN and Direct-IP boundaries.
5. `reports/MANUAL_SAVE_FAILURE_WIRING.md` — save failure propagation.
6. `reports/NATIVE_RENDER_TARGET_BOUNDARY.md` — projector/render-target work.
7. `reports/LAN_SERVER_PRESET_WIRING.md` — original LAN preset persistence.
8. `reports/KNOWN_GAPS.md` — remaining evidence and implementation gaps.
9. `reports/PORT_STATUS.md` — consolidated current state.
10. `staging/PATCH_INVENTORY.json` — exact ordered source-patch identity.
