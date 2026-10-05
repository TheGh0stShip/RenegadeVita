# Practice completion and restart source boundaries

## C&C reference menu transition handoff

The live Practice match continues through `cNetwork::Update` while the
original C&C reference menu is open. That update can complete intermission and
raise `g_b_core_restart`, a pending original game exit, or client quit. The
nested native menu pump previously ignored all three and continued presenting
the old generation until the user closed the menu, stalling automatic map-cycle
restart and risking another frame against transition-owned state.

After each network update, the multiplayer menu pump now leaves immediately
when any of those original transition requests appears. It only releases the
menu/input presentation; the outer between-frame owner still performs the
existing restart, changed-map provider handoff, disconnect, or original
`GameInitMgr` exit. No round rule or map-cycle policy changed. Source only;
completion while the menu is open still requires runtime acceptance.

## Configured map basename preservation

Original server configuration retains arbitrary accessible MIX basenames in
`MapName00..` and `Rotate_Map` selects those entries unchanged. The native
restart resolver previously imposed an extra `C&C_` or `Skirmish` prefix,
so a valid configured later slot could pass original settings validation and
then be rejected after intermission.

The resolver now accepts any bounded `.mix` basename while continuing to
reject control characters, path separators and drive or URI colons. Actual
availability remains owned by the existing rooted file factory and prepared-map
boundary. The initial Practice chooser retains its selection policy; this
change only preserves configured cycle entries during restart.

Source inspection only. No tests, staging, builds, network or device actions.
No completed-round acceptance; all current findings precede runtime proof.

Overlay continuation: original player-name HUD, player/team list update/render
and game-limit/countdown presentation now share original CombatGameMode hooks
with the full native frame. cNetwork Server_Think already owns cGod spawning;
no replacement spawn pass added. Source only, local/uncommitted/unvalidated;
see ORIGINAL_GAMEPLAY_OVERLAY_WIRING.md. Cached layout and list controls remain
separate open presentation boundaries.

Pause/menu continuation: the native menu pump now preserves the released
single-player/multiplayer distinction. Missions suspend Combat and open EVA;
Practice and network matches keep Combat plus `cNetwork::Update` active and
open `LOC_CNC_REFERENCE`. Direct-IP Start no longer unconditionally abandons
the server. This is source wiring only; live-background rendering, menu actions,
disconnect and repeated open/close behavior remain unvalidated.

The concrete `CnCReferenceMenuClass` and its `cSuicideEvent` dependency are now
selected in the full-port link graph. Canonical dialog 245 is included in the
generated WWUI resource set, and generation requires every control dereferenced
by its initializer. Its Main Menu command queues the existing original
`GameInitMgr` exit request for the native between-frame teardown envelope rather
than destroying the active world from inside the dialog callback. Help, suicide,
team change and back retain their released dialog/event owners. This graph is
uncompiled and its controls/actions remain runtime-unvalidated.

The original team, battle and server information dialogs are also selected,
with canonical resources 240, 242 and 249. Resource generation verifies every
direct and array-indexed icon, health-bar and list control used by these owners.
The native frame calls a shared `CombatGameModeClass` input owner for the three
released actions; missions remain excluded and team/battle require an admitted
client plus star. Obsolete, disabled WOL clan-display includes were removed;
the released `#if 0` clan branch and normal player names are unchanged. Native
button bindings, hold-to-display behavior and pixels remain unvalidated.

Loading continuation: the first-load callback/screen now disarms/releases before
full-port gameplay. Original Combat reload's fresh stack screen is borrowed only
within its load scope, and local restart uses the existing logical loading
presentation scope before gameplay rebind. Source only, uncommitted/unvalidated;
see RELOAD_LOADING_PRESENTATION_WIRING.md. Default round looping stays original.

## Default map-cycle behavior

Original cGameData initializes DoMapsLoop to true. cGameDataSkirmish does not
override it. Rotate_Map advances MapCycleIndex, wraps at the first empty entry
or MAX_MAPS, and sets IsMapCycleOver only when wrapping with DoMapsLoop false.
A one-entry cycle therefore reloads the same map; a longer cycle advances and
wraps indefinitely under the original default. Skirmish configuration restores
persisted MapName00.. entries. The released Practice command overwrites slot
zero with the selected map and retains configured higher entries despite its
nearby one-map comment. The earlier port cleared those entries and therefore
changed the implemented original rotation behavior. That override has been
removed from both the original menu staging path and native latched launch.
DoMapsLoop remains true: a configured one-entry cycle repeats indefinitely,
while a configured longer cycle rotates and wraps. IsAutoRestart remains a
separate setting.

Game_Over_Processing rotates before opening intermission, so the win dialog's
next-map label describes the selected next round. At countdown completion,
Intermission_Over_Processing requests g_b_core_restart for a continuing cycle.
Practice does not expose a non-looping cycle setting, so its ordinary menu
return is reserved for explicit exit or a native load-failure path. A
non-looping cycle end belongs to LAN/C&C server configuration; it is not the
intended default after each Practice match.
These are source semantics, not verified repeated-round behavior on Vita.

## Exit/restart arbitration and LAN replication, source only

The combined local client/server can observe an invalid rotated map and request
game exit in the same frame that server intermission processing raises
`g_b_core_restart`. The native loop previously consumed the exit first, reported
an ordinary menu return, and left the process-global restart flag armed. It now
validates that superseded next-map request before original teardown, retains a
source/archive failure classification when applicable, clears the restart flag
at the exit boundary, and clears it again during final session teardown. A later
Practice or LAN session therefore cannot inherit another session's restart.

Practice and LAN-host respawn retain their original local `cGod` path. LAN
clients now wait for both replicated `cPlayer` and star ownership during initial
entry and after a round restart, using the released connection-loss loading
allowance rather than applying the local one-frame spawn rule. LAN source,
archive, required-level-data and replication failures request cleanup back to
the LAN list. Practice restores the released automatic team choice (`-1`);
explicit LAN host selection remains data-owned by the host dialog.

Evidence remains source inspection and local edits. No build, emulator, Vita,
PSTV, GitHub or GitHub Actions run has accepted these paths.

Original MainMenuDialogClass's Practice launch installs the chosen map in slot
zero after the skirmish initializer without clearing configured higher slots.
The native first-load route now matches that exact behavior. Practice and LAN
host cycles remain governed by their configured entries and original
`Rotate_Map` rules.

## Rejected next-round preparation, source only

The native between-frame restart route previously requested ordinary session
teardown/menu return when the next source was unsupported or its changed-map
MIX was invalid. It did not retain a load-failure code. Since the previous round
could already have initialized and rendered successfully, the launcher's
ordinary session-success predicates could accept that incomplete transition.

That rejection now uses Queue_Local_Load_Failure_Recovery with existing
SOURCE_REJECTED (10) for failed source resolution, or ARCHIVE_UNAVAILABLE (9)
for an invalid changed-map factory. It still clears the pending core-restart
request and cleans up the existing round through its original owners. It does
not enter Core_Restart or replace the archive after failed preparation.

The existing launcher excludes retained load failure from PASS and requires its
independent full-cleanup gate before original menu reentry. This makes rejection
failure-classified; it does not prove cleanup or a working next round. Valid
preparation, results countdown and automatic looping are unchanged. The shared
campaign restart envelope receives the same classification on source rejection.
No new serialized fields, retry policy or victory rules were introduced.

Evidence: staging/commando/dlgmainmenu.cpp Practice command;
staging/commando/gamedata.cpp constructor/Rotate_Map;
staging/commando/messages.cpp Intermission_Over_Processing;
port/platform/vita/a31_vita_runtime.cpp local restart preparation/helper;
port/platform/vita/a30_main.cpp success/recovery predicates. Source inspection
and local edit only, uncommitted/unvalidated; no staging/tests/build/device work.

Focused acceptance remains pending: unsupported next source, missing/invalid
changed-map MIX, retained failure code/no PASS, cleanup-gated menu recovery,
and valid one-map replay plus multi-map wrap. Physical Vita/PSTV evidence must
remain separate from future host/ARM/emulator checks. The earlier pre-shutdown
archive replacement ordering has been removed by the callback described below;
runtime evidence must still prove the intended boundary and worker quiescence.
MIX member files use the backing root factory, so source ordering alone is not
proof that no outstanding file survives Core_Shutdown.

## Existing original owners

## Original win-screen resource closure, source only

The restored `CNCWinScreenMenuClass` constructs canonical dialog
`IDD_CNC_WINSCREEN` (248) and immediately uses its title/list/score controls.
The full-port generated template set omitted 248, so the first completed round
could create a control-less dialog and dereference missing title controls before
reaching intermission restart. Full-port multiplayer template selection now
includes canonical dialog 248 from original `chat.rc`. The M00 demo template
set remains unchanged. Generation now also fails if the canonical template is
missing its title, team list, score, MVP, time or next-map controls. Template
generation, pixels and both team-result branches remain unvalidated under the hold.

Native A31_Interactive_Run_Simulation_Frame calls cNetwork::Update.
In staging/commando/cnetwork.cpp that owner services shared game-data Think;
messages.cpp Server_Think calls End_Game_Test for the server. End_Game_Test
checks original Is_Game_Over, invokes Game_Over_Processing and then waits for
the original intermission countdown. gdskirmish.cpp adds base-destruction
termination to the shared game rules; beacon victory uses base destruction.
These are existing code routes, not evidence of a physically completed round.

The original Combat mode also feeds its measured cNetwork and Combat durations
to cSbboManager on server frames. The native frame already measured those exact
call intervals for diagnostics but bypassed the original consumer. It now feeds
those intervals to the linked original manager and calls its Think method. This
restores the original slow-server bandwidth-budget adaptation; it does not add a
new scheduler or claim improved performance. Runtime budget changes and repeated
round reset behavior remain unverified.

gamedata.cpp Game_Over_Processing owns map rotation, duration, MVP, winner
event, ladder accounting, result logging and Begin_Intermission. Do not replace
it with a platform victory flag or an invented skirmish scoring system.

messages.cpp Intermission_Over_Processing closes the original win dialog,
deletes player objects, clears in-game/loading state, and requests exit or
g_b_core_restart according to original map-cycle/manual-exit rules. It clears
the intermission flag afterward. Preserve the distinction between cycle end,
manual exit and reload.

## Original missing native completion boundary

The CombatGameModeClass::Think restart consumer is guarded out under
RENEGADE_VITA_FRONTEND_SINGLEPLAYER. Native simulation does not invoke that
Think method. This was the missing source consumer for local Practice's
g_b_core_restart. Remote native handling still clears it and leaves the
server world for the menu, conflating restart with disconnect/protocol failure.

Original restart handling toggles the local player's loading state around
Core_Restart, emits loading events, initializes MultiHUD and enables waiting
players. Core_Restart invokes Core_Shutdown, safe mode deactivation, level
loading and mesh-cache invalidation. Core_Shutdown unloads Combat and releases
LevelManager state, audio and Radar. A direct call without reconciling native
loop ownership is insufficient: its cached camera, world, HUD/resource and
cleanup assumptions may now refer to a replaced level.

## Local implementation, unvalidated

The new selected commando-a36-core-restart-owner patch extracts the original
consumer into Process_Core_Restart_Request, retaining loading events, player
flags, Core_Restart, MultiHUD and waiting-player ownership. Original Think
also calls that shared method. The native loop invokes it only for local
Practice, between frames when Combat is active; it does not replace round
rules or recreate the player manually.

The native route resolves the map chosen by original rotation and validates
a changed-map MIX before committing the handoff. It releases dialogs and the
TextWindow scene reference and clears prepared model references before invoking
original reload. For a changed Practice map, a narrow callback now commits the
prepared archive provider immediately after original Core_Shutdown releases the
old level and before Load_Level begins. This avoids destroying the old MIX
factory while old-level resources can still own files from it, without moving
teardown or level-load ownership out of Combat. Same-map replay invokes no
callback and retains the established configured map cycle. Campaign death/replay is
required to retain its current archive; an unexpected archive change is now a
classified source rejection rather than an unsafe pre-shutdown swap. The later
death-flow patch preserves an active native completion observer at original
Load_Level's seam before object/script creation; newly produced callbacks are
retained. After reload it restores gameplay rendering and TextWindow scene
binding. It reacquires the
local player and resets cached render/progress/capture observations; input is
flushed around reload. Before accepting the new world, the native boundary now
requires the retained local player to remain active/in-game and disembodied;
the following normal cNetwork update remains the original owner that calls
cGod::Think and creates its new commando. A missing, inactive, stale-body or
premature-star binding is classified with the existing player-binding failure
and uses failed-load cleanup instead of leaving an unplayable round active.
Campaign restart is checked separately for cGod's immediately recreated star.
Practice then permits one ordinary simulation frame to run original
cNetwork::Update/cGod::Think and requires the resulting star, player-data and
control-owner links to point back to the retained local player. It observes and
classifies this owner; it does not create a replacement commando itself.
The original active Combat owner retains teardown.

An unsupported or unavailable next archive requests normal session cleanup
and menu return rather than attempting reload. A missing scene or failed
native resolution restoration exits the loop. This does not prove all corrupt
level failure cases: original Load_Level returns void and the Scene check is
not structural load validation. The follow-up below now propagates existing
required-file/subsystem failure evidence through this route. Renderer cache lifetime, held inputs after
reload, loading callback/resolution, script registration and repeated round
stability remain unverified. Multi-map acceptance must prove the old provider
survives through Core_Shutdown and the new provider is visible before Load_Level.

The desktop TextureLoader would require queue quiescence before this provider
swap. The selected Vita build does not link that worker implementation:
`a4_frontend_lifecycle_boundary.cpp` owns a synchronous texture boundary with
empty request queues and a no-op Flush_Pending_Load_Tasks. VitaGL decoding and
upload occur synchronously below DX8Wrapper, so there is no current loader worker
to flush at this seam. If the real threaded TextureLoader is restored later,
quiescence while the old provider remains mounted becomes a prerequisite. This
source distinction does not replace repeated-round resource validation.

No patch application, compilation, tests or physical actions were executed.
Changes remain local and uncommitted. Remote restart still uses the previous
menu-return behavior pending its distinct prepared-map/resource owner work.

## Map-cycle and manual-exit continuation, unvalidated

Original Intermission_Over_Processing uses Set_Needs_Game_Exit at cycle end
and Set_Needs_Game_Exit_All for manual full exit. These requests are owned by
GameInitMgrClass::Think, which invokes original End_Game and either
Display_End_Game_Menu or Stop_Main_Loop. Native gameplay previously serviced
that Think only in frontend/intermission presentation loops, not after local
round completion.

The selected commando-a36-pending-exit-owner patch adds a read-only native
Has_Pending_Game_Exit query over the original two fields. Before any restart
or world access in the native gameplay loop, local sessions now service a
pending request through the original Think. The route releases dialog,
TextWindow and prepared-model references first, enters the frontend context,
and then observes whether Combat became inactive. Only that observation marks
level/radar/session cleanup as consumed; a failed handoff records an error.
It clears stale render/capture observations and retains the distinction between
menu return and the original full application exit latch. The existing outer
session owner recreates the original frontend after normal cleanup.

This is local-session source wiring, not a verified completed map cycle.
Original End_Game owns inventory retention, Combat shutdown, goodbye events,
network/player destruction and mode selection. No replacement exit protocol
or round rules were introduced. Full-exit, cycle-end, failure and repeated
menu/session acceptance remain open. Remote exit/restart is still separate.

## Required reload failure follow-up, unvalidated

The existing native a35_level_load_status provider and selected original
SaveGameManager patch already retain missing/open-failed dynamic/static data,
subsystem failures and required dynamic chunk omissions. Initial native loads
check that status after reference post-processing; original Combat Load_Level
previously did not check it when reached by Core_Restart.

The new selected commando-a36-required-reload-failure patch resets that provider
at original Load_Level entry and checks it after reference post-processing and
after clearing NetworkObjectMgr's loading state. On failure it clears the
global loading flag, restores server packet processing and returns before
Post_Load_Level, Radar/building initialization or On_Game_Begin. The shared
restart consumer does not mark the player in-game or enable waiting players
when that failure is present. Its bool means request consumed, not successful
reload. Native handling checks the retained failure explicitly and exits to
session cleanup, with stale captures cleared. The initial follow-up used the
existing fatal runtime path. The recovery continuation below now separates
known load failure from renderer failure and gates original menu re-entry.

Radar shutdown is null-safe in original radar.cpp; the partial-world cleanup
still uses original Combat/LevelManager. This source inspection is not crash
or leak evidence. The status records known required-load failures and does not
certify complete level validity, asset availability or mission behavior. No new
load parser or replacement initialization was introduced. Patch application,
compile/link and runtime failure behavior remain unexecuted.

## Failed-reload menu recovery continuation, source only

A31VitaInteractiveResult now retains the uint32_t required-load failure code
separately from render_error. This is a native in-process result, not an
original save or wire-format change. Known Practice reload failure requests
controlled exit and menu return, while original owners clean up the partial
world. A retained failure excludes the session from the launcher's PASS path.

Before allowing recovery, the native result checks released renderer/assets
and audio, null client/server connections, empty original player/object lists,
null Combat scene/star/camera and removal of the Combat game mode. The launcher
also requires clean exit, menu-return intent and no frontend/full-exit request
or renderer error. It then re-enters the existing original frontend loop with
no previous reload/campaign request. Failure of this gate retains controlled
process exit; it does not start another engine over live state.

Diagnostics classify this result as LOAD_FAILURE_RECOVERY, retain the code and
count recoveries for the final lifecycle record. A subsequent clean user exit
does not erase the earlier failure count. Main-menu re-entry samples input and
primes the existing WWUI edge tracker before creating the dialog, so a held
control from gameplay is not introduced as a fresh menu edge. This follows
the existing pause-menu priming method and preserves original UI ownership.

No automatic retry of the rejected map, replacement menu or custom gameplay
loop was added. User-visible failure presentation, partial-world cleanup,
held/released controls, choosing another game and repeated recovery remain
unverified. Initial-world failures now have local source recovery wiring in
INITIAL_LOAD_FAILURE_RECOVERY.md; remote-map failures remain separate routes.
New result fields require coherent recompilation of callers and
callee before any candidate use. No staging/tests/builds/device actions ran.

## Remaining acceptance requirements

1. Validate the extracted shared owner and local frame handoff described above.
2. Verify world, HUD/resource and cleanup ownership through unload/load.
3. Separate remote disconnect/protocol mismatch from restart handling.
4. Verify restored original win-dialog, map-cycle exit and menu-return ownership.
5. Verify repeated rounds, both team wins, beacon victory, timed victory,
   cycle end, failed next-map load and exit during intermission.

Acceptance needs matching physical Vita/PSTV evidence, stable resources across
repeated rounds and working original win UI. No physical result from earlier
Practice loading/spawn closes these completion gates.

## Original victory dialog continuation, source only

The previous selected source removed START_DIALOG from Begin_Intermission,
omitted dlgcncwinscreen.cpp from the full-port manifest, and replaced its
network close callbacks with empty classes. The new selected
commando-a36-original-win-screen patch restores the original creation call
and real DialogMgr include for the full original frontend, outside the M00
demo. The shared full-port manifest now selects dlgcncwinscreen.cpp. Both the
intermission and server-goodbye close boundaries use the same real class in
that profile; other profiles retain their previous no-dialog boundary.

The dialog retains original translated winner/condition/time/team scores,
player lists, MVP, banner model and next-map label. Original WWUI handles
activation, update and rendering through the existing native frame hooks.
Explicit soldier/player-manager/time-manager includes replace transitive
desktop dependencies. An absent optional WOL mode no longer asserts or
dereferences null while checking ladder presentation. GameSpy queries use the
existing disabled-by-default provider seam. A missing backdrop is guarded
consistently with the existing MenuDialog render boundary.

Native cancellation closes the dialog and queues original NeedsGameExit,
instead of unloading the world from inside input/dialog dispatch. The existing
between-frame pending-exit consumer retains original GameInitMgr teardown and
menu-return ownership. Automatic Close_Dialog at countdown completion does not
issue that exit request; the original continuing-cycle restart stays intact.
No new scoring, countdown, victory condition or application loop was added.

Follow-up inspection also found messages.cpp still included the empty
a31_gameinit_stub, so its original cycle-end/manual-full-exit requests would
not reach the real pending-exit consumer. This patch restores the real
GameInitMgr header for that full-frontend translation unit. Earlier descriptions
of the pending-exit consumer alone did not establish that request path.
Other legacy GameInit/dialog stubs in cnetwork.cpp and god.cpp remain separate
review boundaries; this change does not certify all exit/failure routes.

Original RenegadeUIInput Enter_Menu_Mode only enables menu input; it does not
suspend Combat. Native cNetwork::Update still owns the intermission countdown
and End_Game_Test while the dialog is open. The existing input-edge pump runs
before that update and the existing HUD render envelope services DialogMgr.
This establishes a source route, not correct pixels, controls or timing.

No staging, tests, builds, emulator or physical actions ran. These changes are
local, uncommitted and unvalidated. Remaining focused acceptance includes GDI
and Nod wins, timeout/beacon/base conditions, a one-map replay, a two-map wrap,
cancel during intermission, held controls on dialog entry/close, missing next
map, and repeated resource cleanup. Remote restart is still incomplete and
must not be described as fixed by restoring the shared win screen.

The reload presentation envelope is now also used by a deferred original
cGod campaign restart, selected separately from Practice's network request.
Practice still resolves the map chosen by its original cycle and invokes
Process_Core_Restart_Request. See SINGLE_PLAYER_COMPLETION_WIRING.md for the
unvalidated death/failure route; this reuse does not establish round acceptance.

## Original Bio-event player ownership and failure recovery

The native frontend intercepts `GameInitMgrClass::Start_Game` before its
desktop body reaches `Transmit_Player_Data`. Initial Practice and LAN sessions
previously compensated with a direct `cGod::Create_Player`, while LAN clients
only waited for a replicated player that they had never asked the server to
create. The direct call also skipped the released LAN server's Bio-event join
side effects.

The post-load native boundary now submits the original `cBioEvent` with the
latched team and clan values. Combined campaign, Practice and LAN-host sessions
therefore execute the original synchronous server owner; a LAN client sends the
same event and performs the bounded replication wait. The initial acceptance
gate verifies the complete reciprocal player/star binding and local control
owner. Missing or partial identities now carry
`A35_LOAD_PLAYER_BINDING_FAILED` through clean teardown, returning LAN sessions
to the LAN list. Rejected frontend sources and next-round preparation failures
also preserve that LAN destination.

This is source inspection and local editing evidence. Repeated Practice rounds,
LAN joins and LAN map rotation remain unverified on runtime or hardware.

## Per-world-generation admission

The session result previously retained `first_frame_completed` and geometry
success from the first map for its entire lifetime. A later Practice/LAN round
could therefore return without ever proving that its replacement world spawned
and rendered. The native boundary now counts each original world generation
after successful initial binding or `Process_Core_Restart_Request`, and requires
each generation to achieve its own reciprocal local-player binding and first
scene/star/camera/geometry render. Application-level success requires the
started, bound and rendered counts to match. The binding counter advances only
after campaign restart returns its required star or a Practice/LAN simulation
frame observes the original respawn/replication result; a session-old commando
flag cannot satisfy a later generation.

LAN clients waiting for their next replicated star now remain in the bounded
loading presentation and service audio instead of falling through into a
gameplay render with no player. Timeout still produces the classified LAN-menu
recovery. These are evidence gates around original ownership; they do not add
a replacement round loop or establish hardware correctness.

## Direct-IP terminal exit ownership

The native gameplay frame now consumes original pending game-exit requests for
Direct-IP clients as well as Practice and LAN. A broken remote connection's
`g_client_quit` edge is converted to the same `GameInitMgr` pending-exit
request before world state is reused. This closes the source path where an
invalid next map, a completed non-looping cycle, or a broken direct connection
could leave the client trapped in intermission.

Direct-IP round restart now has a two-generation provider transaction. The
client freezes the server's next-round identity and resource offer, prepares a
separate pending TT factory while the old world retains the current factory,
and promotes it only through the post-`Core_Shutdown` callback. Stock-only,
retained-current and replacement generations remain distinct. The runtime then
requires the client state to advance from `LoadingRound` to
`WaitingRoundPlayer`; a failed or skipped promotion is classified as a resource
provider failure before player rebinding. This is source wiring, not Direct-IP
round acceptance on Vita hardware.

The shared original core-restart seam now uses a fallible post-shutdown
resource callback. If provider publication fails after `Core_Shutdown`, it
records `A35_LOAD_RESOURCE_PROVIDER_FAILED` and returns before `Load_Level`,
player re-admission, the loading-finished event, MultiHUD initialization or
waiting-player enablement. The existing Practice map-factory callback returns
success only after its validated ownership arguments are committed. This is a
prerequisite for the Direct-IP current/pending provider transaction; it does
not itself add remote round rotation.

Core teardown now has explicit one-shot ownership. `Load_Level` marks the core
as owning partial or complete resources before initialization begins, and
`Core_Shutdown` claims that ownership before releasing HUD, music, level,
radar and sound-page state. A failed post-shutdown provider callback therefore
leaves the core already released; later Combat deactivation cannot repeat the
same teardown. A successful callback enters `Load_Level`, which establishes
fresh ownership for the next map generation.

## Vita access to original multiplayer information presenters

The selected team, battle and server information dialogs now have held physical
routes through the original input functions. Multiplayer maps SELECT+Square,
SELECT+Cross and SELECT+D-pad Up to unused logical F7, F8 and F9 slots,
respectively. The logical keys remain held for the full physical chord because
the released dialogs close by observing their configured key release. Chat,
radio and information chords suppress the corresponding ordinary gameplay
button while active, preventing a message or presenter chord from also firing,
crouching, jumping, reloading or changing zoom. Campaign SELECT+Square remains
the original quicksave route and campaign SELECT+Circle remains the camera
toggle route.

This is source-inspection evidence only. The dialogs have not been compiled or
observed on hardware, and their resource layout, hold/release behavior and
return to active multiplayer still require runtime validation.

## Per-generation render admission

Renderer statistics are session-cumulative. The replacement-world gate
previously treated their absolute values as evidence for the new Practice/LAN
generation: geometry from round one could admit a blank round two, while one
old rejected submission could poison every later clean round. The restart
boundary now snapshots the cumulative mesh, vertex, triangle, rejected and
unsupported counters after loading and immediately before the candidate world
frame. Admission requires positive new geometry, no new rejection or unsupported
submission, and monotonic counters. Cumulative telemetry remains intact.

This is source wiring only. Same-map replay, changed-map rotation and counter
wrap/error behavior still require runtime evidence.

## Current deterministic source state

The original Practice map-cycle contract is retained: the menu overwrites
`MapName00`, preserves configured later entries and leaves `DoMapsLoop` enabled.
A one-map configuration therefore repeats that map; a longer configured cycle
rotates and wraps under original `cGameData` ownership. The native loop now
returns to its transition owner immediately after a pending exit, client quit,
core restart or campaign restart is raised, so it cannot run a stale gameplay
tail frame after original intermission teardown.

The source-level repeated-round route has no round-count limit. Ordinary match
completion rotates the original map cycle, presents the original win screen,
raises core restart after intermission, and recreates the world/player binding.
Practice menu return is reserved for explicit exit or classified load/rebind
failure. LAN/C&C can additionally return after its configured nonlooping cycle
ends. Current-source same-map replay, changed-map rotation and
long-running repetition still have no executable evidence.

Deterministic reconstruction passes for 434 ordered patches with inventory
SHA-256 `8e110226f929c8ee5a15c2d11f7b21d37a01fffd5dc888cead63081092cbd90c`.
This is source and staging evidence only. Compilation and runtime validation
remain paused, and no GitHub Actions runner was used.
