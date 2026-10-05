# Single-player completion source review

Status: source and deterministic staging inspection only; no builds, test suites,
emulator, device, GitHub or GitHub Actions runner actions.
The complete-game goal remains open. Existing physical M13 missing-finale
evidence occurred during a save stall and does not establish an independent
finale-script defect.

## Current success ownership

### Local replay/load frontend continuation

Selected `port/patches/commando-a36-original-replay-flow.patch` restricts the
early LoadSPGame native bypass to the tutorial-demo profile. Full-port selection
again reaches original map/backdrop lookup, stored mission rank and
DifficultyMenuClass::Set_Replay. Missing filename tokens return before
dereference. Normal save selection still latches Start_Game; native dispatch
skips immediate End_Game/Initialize_SP. Desktop and demo paths remain separate.

## Campaign catalog readiness, source only

Original CampaignManager::Init returns void and historically accepts a missing
or empty `campaign.ini`; Continue then interprets the zero-entry catalog as the
end of the campaign. The native full-port startup previously marked campaign
initialization successful unconditionally, so New Campaign could silently route
back to the end menu without proving that retail campaign data was parsed.

The selected `commando-a36-campaign-catalog-readiness.patch` validates the
structure that the released `Continue` parser actually consumes: a non-empty
flow and backdrop catalog, recognized Message/Score/Level/Movie directives,
required directive tokens, and at least one line in every parsed backdrop.
Full-port startup rejects a missing, empty or structurally malformed catalog
before campaign start or restored campaign handoff. It does not reorder,
synthesize or hard-code mission entries; retail `campaign.ini` remains the sole
sequence owner. Initialization is marked before the gate so common teardown
still calls CampaignManager::Shutdown after failure. The M00 demo route is
unchanged. No staging, compilation or runtime validation was performed.

### Campaign save-state validation, source only

The released loader wrote campaign state and loading-backdrop indices directly
into process globals and returned success for missing or arbitrary values. A
corrupt save could therefore index beyond the parsed `campaign.ini` flow or
backdrop vectors during continuation/loading presentation. The selected A36
validation patch reads both required microchunks into temporary 32-bit values,
accepts only the released sentinel/progression range and an existing backdrop,
and publishes globals only after validation. Backdrop accessors also reject
invalid indices. `CommandoSaveLoadClass` now propagates failures from original
network, cGod and campaign child loaders instead of returning unconditional
success. No state is clamped or synthesized, and campaign order remains retail
data-owned. This is unbuilt source evidence only.

### Required player-save state, source only

The generic save/load framework previously returned success when a registered
subsystem chunk was absent. A partial dynamic save could therefore contain
enough world data to pass the outer level checks while omitting the complete
Commando owner state needed for campaign progression. Player-save loads now
use an opt-in required-subsystem contract. `CommandoSaveLoadClass` is the first
required owner; static level/resource loads retain the released permissive
behavior.

Within the Commando chunk, Network, God and Campaign children must each occur
exactly once. `cGod::Load` requires exactly one variables/state value, validates
the released `GodState` range, and publishes the process-global state only
after validation. Missing, duplicate or invalid state returns through the
existing dynamic-subsystem load failure and unwind path. The chunk IDs and
serialized representation are unchanged, so this adds admission checks rather
than a new save format.

The Network child is also closed recursively: `cNetwork::Load` now requires
exactly one PlayerManager child and propagates its result, while
`cPlayerManager::Load` requires exactly one PlayerList container and skips a
duplicate rather than constructing duplicate players before reporting failure.
An empty released PlayerList remains valid; the admission rule requires the
container and does not invent a player. These failures propagate through
Commando and the generic required-subsystem contract to the existing dynamic
load-failure unwind.

Each present player record now requires one PlayerData parent, one variables
container, and exactly one ID, name, kills, deaths, team and pointer-remap
microchunk. `PlayerDataClass` likewise requires one variables container while
retaining zero or more released weapon-stat chunks. A rejected player is
deleted immediately, which removes the constructor-registered player from the
manager, and its old pointer is never published to `SaveLoadSystemClass`.
Unknown forward-compatible chunks remain ignored under the released format.

The required-subsystem set now matches the fixed sequence written by
`SaveGameManager::Save_Game`: Combat, level conversations, dynamic physics,
encyclopedia, dynamic audio, map state and caller-supplied Commando state.
All seven must occur exactly once in a dynamic player save. This requirement is
enabled only at the player-save load call; static LSD/LDD/resource loading keeps
the generic framework's released permissive behavior. The audio requirement is
attached to `DynamicAudioSaveLoadClass`, not the separate static-audio owner.

Combat now validates the exact 15 child chunks emitted by its writer: game
objects, CombatManager state, spawners, scripts, persistent observers, cover,
objectives, radar, game-object observers, bullets, weapon view, background,
weather, HUD and screen fade. Each occurs exactly once and each child loader's
failure propagates. Dynamic physics similarly requires exactly one scene,
constants and PathMgr child. Neither subsystem registers its post-load callback
after failed admission, preventing post-load work over a knowingly partial
world.

The remaining fixed manager owners now apply the same writer/load symmetry.
Conversation state requires one variables child and either one current category
or the released repeated legacy-conversation representation. Encyclopedia state
requires its variables child and exactly `TYPE_COUNT` ordered type vectors; an
excess vector is rejected before indexing the fixed array. Map state requires
one variables child and one correctly sized shroud. Dynamic audio preserves its
released conditional writer contract: it accepts either the variables and scene
pair or the intentionally empty subsystem written when no sound scene exists,
while rejecting partial or duplicate pairs.

Rejected subsystem loads no longer execute or retain post-load callbacks.
Pointer-token remapping still completes before rejection so partially created
objects do not retain serialized addresses during cleanup, after which the new
discard path clears each registration flag without calling `On_Post_Load`.
Original level loading now checks the retained Vita failure before the global
post-load pass and explicitly discards callbacks for failures detected outside
the subsystem loader, such as a missing required outer chunk.

The player-save envelope now admits one validated level-info chunk before one
level-data chunk. Map name, description and mission-description fields are read
into temporaries exactly once, the required `.LSD` name is validated before any
definition or static-level load, and globals are published only after the
header is complete. Duplicate, reordered or incomplete envelope chunks enter
the existing classified load-failure cleanup.

Campaign and God state now require exact-width, exact-once fields. Vita rejects
terminal God snapshots because the released `SINGLE_DEAD` value does not retain
whether death or mission failure owned the popup/restart state; accepted saves
must restore the running simulation state that the writer itself permits.
Campaign handoff failures are excluded from runtime PASS and reopen the original
main menu only after the same strong network/player/world cleanup predicate used
for failed level loads.

The shared chunk reader now distinguishes exact container exhaustion from
structural failure. It retains a sticky error for truncated headers or payloads,
child sizes outside their parent/file boundary, excessive nesting, invalid
read/seek ranges and failed seeks. Generic save loading and the player-save
envelope propagate that error into the existing rejection path. The typed
vector/quaternion overloads also read the serialized object width rather than
the host pointer width, preserving the format on Vita's ILP32 ABI and host
probes. Map variables now require all six exact-width writer fields before its
post-load callback is registered.

The deterministic staging stack contains 446 ordered patches with inventory
SHA-256 `d54f18d1d5671c8b66cc350b1bd8add904184ad90278e6a7066c810b41a5bd6d`.
Patch inventory validation, reject/original-debris inspection and
`git diff --check` pass. Compilation and runtime validation remain paused.

Conversation loading now admits only objects whose own loader succeeds and
whose category matches the enclosing category. Invalid category indices cannot
reach the manager array, failed active conversations are released rather than
published, and structural chunk-reader errors fail the manager load. This keeps
partially restored dialogue state out of post-load mission execution.

The required dynamic-physics subsystem now accepts physics constants only when
all seven exact-width writer fields occur once, and accepts saved path objects
only after their complete variable envelopes load. Rejected paths are released
before publication and cannot register post-load work. Previously admitted
paths remain alive for outer rejected-load callback discard and teardown.

Script restoration now requires each entry's original header envelope, bounded
NUL-terminated name and parameter strings, exact 32-bit serialized pointer
tokens and observer ID, and no duplicate or misplaced data child. Pointer
registration and owner remapping occur only after entry admission. A script
missing from the linked provider retains the released null-remap compatibility
behavior; a malformed script instance is removed and destroyed.

Script serialization now rejects null active entries and script fields outside
the released micro-chunk capacity before publication. Mendoza, Sakura and
Raveshaw also propagate their original parent, defense, reference, stealth and
effect save results. Raveshaw rejects a missing Tiberium effect safely instead
of dereferencing it or publishing a partial boss record. Original state-machine
bytes and boss ownership remain unchanged.

Save transactions now aggregate every fixed and caller-supplied subsystem's
logical result. A false serializer result calls the narrow native write-abort
boundary before close, causing the rooted provider to delete its `.pending`
sibling rather than atomically replacing the prior valid save. The result
reported to quicksave/manual-save callers requires both logical serialization
and physical close/rename success.

The original load menu, development save resolver and real Vita loader now use
the same level-info parser. It bounds and validates terminated map/description
fields, the exact mission-ID width and `.LSD` suffix. Preflight additionally
requires one ordered `LEVEL_INFO` followed by one `LEVEL_DATA`, preventing a
header-only, duplicated or reordered file from appearing as a usable save.

Radar, objective and spawner managers now propagate child loader failures and
publish manager globals only after required state is present. Failed radar
markers are not added. Pointer-bearing objective and spawner objects stay alive
for outer rejected-load teardown so queued remaps cannot reference freed
memory. Spawners additionally require parent/variables, every writer-owned
singleton field at its exact width, a resolved retail definition, valid repeated
spawn-point transforms, and bounded NUL-terminated script name/parameter pairs
in the released alternating order.
Each objective now also requires every field emitted by its writer exactly
once, with exact scalar widths and bounded NUL-terminated sound/POG names. The
two separately serialized age fields remain distinct required IDs, matching
the released format, and must agree before the age is published. Objective IDs
must be positive and unique, while type and status values must stay within the
released enums.

Active conversations now require one variables root, propagate monitor-reference
failure and reject more than the released ten monitor slots before indexing the
fixed array. Rejected pointer-bearing conversations remain manager-owned until
the outer failure discards callback/remap queues, preventing dangling targets.

The shared pointer-remap pass now distinguishes serialized null and explicitly
registered null replacements from unresolved non-null tokens. Any unresolved
token rejects the outer load before behavioral post-load callbacks execute;
ref-count requests no longer dereference an intentional null replacement.

Observer and custom script-timer readers now require their released variables
root and all three exact fields, reject duplicates and unknown children, and
bound optional custom-timer sender state to one reference. `ScriptableGameObj`
now requires and propagates its parent, referenceable and variables roots,
validates explicit 32-bit identity/observer tokens, retains timer ownership for
teardown, and registers behavioral post-load work only after full admission.

The generic simple persist factory now requires the released ordered pointer
and data wrapper, a nonzero 32-bit object token and a successful concrete
`Load`. It reports semantic failure through a sticky outer transaction flag
while returning the manager-owned partial object so remap, callback discard and
teardown cannot target freed memory. The top-level loader consumes that flag
before remap/callback completion.

Player data now requires all 24 released scalar fields exactly once. Weapon
statistics require one exact ID/count pair, a nonzero unique weapon ID and a
nonnegative count. Safe score and money values publish only after the whole
record succeeds. The enclosing `cPlayer` similarly requires exact ID, kill,
death, team and 32-bit remap fields plus a bounded, even-width, NUL-terminated
UTF-16 name before publishing identity or registering its pointer mapping.

Game-object observer IDs and weapon-view state now publish only from complete
manager envelopes. Weapon-view hands use an explicit 32-bit disk token. Each
bullet requires all eight exact writer fields, a valid ammo definition and a
nonzero projectile token; only admitted bullets register post-load work. The
constructor-created placeholder projectile is released before token install.

Persistent game-object observers now require their single released root,
reject unknown child factories, propagate null factory loads and reject trailing
root chunks. Loaded observer objects remain owned by the original manager for
outer rejected-load teardown; the admission layer does not invent observers.

HUD, screen-fade, dynamic-background and dynamic-weather state now require the
released roots before Combat restoration succeeds. HUD enabled state publishes
only after its exact value arrives. All five fade interpolators are required
once and each requires exact value, target and rate fields. Background and
weather reject duplicate/missing dynamic roots and structural reader failure.

Cover restoration now admits entries only after one complete variables root,
exact transform/crouch/in-use/remap fields, valid repeated attack positions and
a nonzero 32-bit old-pointer token. Pointer remapping is registered only after
admission; rejected entries never enter the live cover collection.

CombatManager now requires the released star and variables children, rejects
duplicate camera/state children, bounds and validates terminated start/respawn
script names, and enforces the writer's conditional field set: first-load
saves omit difficulty/first-person while running saves require them. Combat
globals and cheat-history side effects publish only after full admission.

### Atomic save replacement boundary

The current rooted writer already stages write-only ChunkSave streams in RAM,
so header back-patching no longer performs thousands of memory-card seeks. It
previously opened and truncated the visible destination before serialization,
meaning interruption could still destroy a valid slot. Writable rooted files
now open a same-directory `.pending` sibling, retain the exact staged bytes and
cursor semantics, close it, and rename it over the destination only on success.
Failure removes the temporary sibling and leaves the prior destination intact;
the existing `Has_Write_Failed` consumer receives flush, close or rename failure.
This platform boundary applies to writable save/configuration files and never to
retail data. Source only; atomic replacement and recovery remain unvalidated.

The full-port difficulty callback records the mission and original button-derived
difficulty through A4_Frontend_Latch_Replay_Level. It does not unload the world,
initialize transport or invent campaign state during dialog dispatch. The latch
uses the existing supported campaign-map boundary, rejects saves and selects
campaign routing rather than inheriting Practice/client routing. Normal
Start_Game and pause/menu entry clear replay metadata.

`port/platform/vita/a31_vita_runtime.{cpp,h}` and `a30_main.cpp` retain replay
metadata with the existing requested source through pause/death cleanup.
Startup accepts a map as replay only with a recorded valid difficulty; ordinary
reload still requires a save. After frontend initialization, the startup menu
owner invokes original Initialize_SP and CampaignManager::Replay_Level while
the Start_Game latch is active. Original Replay_Level sets REPLAY_LEVEL, resets
inventory, sets difficulty and selects the original player type. Later SP
initialization does not reset CampaignManager or Combat difficulty (source
trace in gameinitmgr.cpp Shutdown/Initialize_SP).

Run_Original_Campaign_Intermission also pumps the original final-score/menu
route. Save/replay selections there now retain a load request rather than
serializing previous campaign/replay state as next-level advancement. Ordinary
campaign advancement still uses original CampaignManager serialization.

Original CombatManager::Load in `staging/combat/combat.cpp` keeps pre-load
difficulty when IsFirstLoad is true; otherwise it restores serialized difficulty.
This is source support for fresh replay using selected difficulty and normal
saves restoring their snapshot. The native loading presenter derives the
original backdrop from the resolved archive. Added fields are process-local
lifecycle requests; no disk/wire format or campaign/map-cycle rule changed.

No staging, patch application, tests, builds, emulator/device or commit/push
ran. All changes are local/uncommitted/unvalidated. No rank was manufactured
and no retail content was inspected/copied. Acceptance remains open for
unlocked-map selection, each supported difficulty, ordinary saves, dialog
cancel/held input, pause/death/final-score replay, score-to-menu return,
repeated cleanup and failure behavior on matching Vita/PSTV candidates.
Initial failed-world recovery has a later source continuation in
INITIAL_LOAD_FAILURE_RECOVERY.md; runtime acceptance remains open.

`port/platform/a31_gameplay_boundary.cpp` installs A31VitaCombatMiscHandler:
Mission_Complete records the original Combat callback; failure invokes original
cGod::Mission_Failed. Star_Killed invokes original cGod::Star_Killed.

`port/platform/vita/a31_vita_runtime.cpp` consumes observed success and calls
Run_Original_Campaign_Intermission. That function calls CampaignManager::Continue,
then runs original GameModeManager, GameInitMgr and DialogMgr for score/movie
presentation. It serializes CampaignManager state when the original frontend
latches a subsequent level. Retention of these calls is source evidence only;
normal M13-to-M01 progression remains physically unverified.

`staging/commando/campaign.cpp` Continue owns replay scores, campaign scores,
movies, subsequent levels and end-of-campaign return. Its Level branch requests
an autosave except for M13. Do not replace this with a hard-coded M01 transition.

## Confirmed missing consumer

Original `staging/commando/combatgmode.cpp` Think consumes
CombatManager::Is_Autosave_Requested, clears the request, sets the translated
autosave description and saves through SaveGameManager with _CommandoSaveLoad.
Neither the native simulation boundary nor native runtime contains an autosave
consumer. Native simulation does not execute CombatGameModeClass::Think.
Consequently the original campaign request has no consumer in that frame route.

Local integration now extracts the existing autosave block into shared
CombatGameModeClass::Process_Autosave_Request and calls it after native
CombatManager::Think. The original Think also calls this shared consumer.
The selected commando-a36-autosave-owner patch preserves the original save
format/path/description and request clearing. It checks the pending close-time
write status before logging completion; a failed save is not retried every
frame. Patch application and compilation remain unexecuted. No background traversal
of live game objects or replacement save format. The existing save hang and
failure paths must be resolved before runtime acceptance; wiring the request
alone cannot establish a reliable checkpoint.

## Remaining completion boundaries

Source trace narrows the finale owner: MissionX0.cpp's MX0_A03_END_ZONE
only notifies the Area 3 controller and advances reinforcements. It does not
report mission success. In Test_DLS.cpp, MX0_Area4_Controller_DLS handles
ION_CANNON_STRIKE by creating the beacon planter, scheduling FLASH_TO_WHITE
after 22 seconds and FINALE after 25 seconds. FINALE attaches Test_Cinematic
with X0Z_Finale.txt. The controller's MX0_MISSION_SUCCESS custom-event handler
then calls Mission_Complete(true). The enum comment identifies event 9 as
hard-coded into the control file; that comment is not verification of the
current user-supplied file or its target object.

MX0_Plant_Ion_Beacon_DLS gives/selects the original AI beacon weapon and
force-fires through Action_Attack. It does not own campaign advancement.
Test_Cinematic::Command_Send_Custom resolves a numeric ID or object slot,
looks up the target and sends only if found. Missing targets are silently
ignored in this source. Therefore the next diagnostic boundaries are timer
delivery, finale attachment, control-file open, target resolution and event
delivery; changing beacon weapon timing would not repair a missing target.

Read-only inspection of the user-owned retail `M13.mix` now confirms the exact
authored completion command in `x0z_finale.txt`: at frame 440 it sends custom
type `445009` with parameter 1 to placed object `1500017`. The enum beginning at
`445000` makes that value `MX0_MISSION_SUCCESS`, and the attached
`MX0_Area4_Controller_DLS` handler on the same placed object calls
`Mission_Complete(true)`. The file also returns camera/HUD/letterbox state at
that frame. This verifies data-to-source linkage without copying retail content
into the repository. It does not prove that the 25-second FINALE timer fires,
that the control file opens on Vita, that object 1500017 remains resolvable, or
that the event reaches the handler during a real session. No forced-success or
alternate timer path is justified by current evidence.

Source-selection provenance is cmake/RenegadeScriptSources.cmake's original
Scripts.dsp inventory. Linked retention and physical execution require
matching later build/runtime evidence, not these source references alone.

- Trace MX0_A03_END_ZONE and its cinematic/custom-event prerequisites before
  changing the finale. Do not force success or shorten authored timers.
- Verify score statistics are captured before original End_Game destroys objects.
- Verify campaign state survives teardown/reload and the next original Start_Game.
- Verify mission failure, death, retry and load preserve original inventory/state.
- Review Practice round restart separately: original g_b_core_restart consumer
  is excluded by the native frontend guard; remote native handling currently
  returns to the menu. A remote disconnect and local round restart need distinct
  original-owner handling.

Acceptance requires ordinary play into the finale, score/movie input, M01 spawn,
checkpoint reload and repeated transitions on matching Vita/PSTV artifacts.
Source, host, ARM/link and physical evidence must remain separate.

## Campaign level-start provenance

The frontend `Start_Game` latch is shared by campaign levels, Tutorial,
Practice, LAN and load/replay selections. The campaign intermission consumer
previously inferred campaign advancement from a resolvable map name, which
could serialize `CampaignManager` state for an unrelated selection made from
an end-of-campaign menu.

The released `CampaignManager::Continue` Level directive now marks its
immediately following `GameInitMgrClass::Start_Game` request as campaign-owned.
The process-local marker is consumed once and copied into the frontend trace;
replay, load and all other `Start_Game` producers remain unmarked. Intermission
serialization is admitted only for that marked campaign request. Save/replay
continues through its existing load handoff. Unmarked Tutorial and Practice
selections are copied into a bounded process-local deferred-selection record,
then restored into the next frontend generation after the old world completes
its original teardown. The restored route re-enters the same original SP or
Skirmish initializer before the shared `Start_Game` latch; no world or gameplay
object crosses the teardown. LAN and remote-client selections return to their
original menu boundary because their live network ownership cannot be reduced
to a map name. None of these paths can corrupt campaign state or be reported
as a campaign handoff failure.

This is source-only evidence. Deterministic staging passes with 384 ordered
patches and inventory SHA-256
`324290a8d84262418d830a10dae93d9bf8a3646e773fa063ecdbb03b538b68d1`;
patch inventory, debris inspection and `git diff --check` pass. No build,
runtime, device, GitHub or GitHub Actions operation was performed.

The deferred-selection fields are lifecycle-only and never enter a save, wire
packet or retail file. This remains uncompiled source evidence; acceptance
requires selecting Tutorial and Practice from an end-of-campaign frontend,
observing complete old-session teardown, and verifying one automatic launch in
the new generation without duplicate input or stale map-cycle state.

## Original death/failure frontend continuation, source only

The retained native misc-handler callbacks reached cGod::Star_Killed and
cGod::Mission_Failed, but god.cpp included empty popup/menu/GameInit/DialogMgr
boundaries. The real DeathOptionsPopupClass and FailedOptionsPopupClass
implementations in dialogtests.cpp were also inside the excluded desktop block.
Thus calls to those owners did not establish functioning original death UI.
Earlier status that described only the native popup pump was insufficient.

The new selected commando-a36-original-death-flow patch enables only those
original dialog handlers for the full frontend/non-demo profile, leaving
unrelated editor/test dialogs excluded. a31_god_ui_stub selects the real
dialog declarations there, and god.cpp uses the real GameInitMgr/DialogMgr.
Original On_Init_Dialog still flushes the audio playlist, activates the Menu
mode and suspends Combat. Original resource templates, buttons and failure
Cancel behavior remain the owners; no replacement popup is introduced.

### Restart

Native restart buttons queue cGod::Request_Restart rather than invoking
Core_Restart from dialog/input dispatch. The process-local pending bool is
accepted only in original SINGLE_DEAD state, queried without mutation and
cleared by Restart, Reset and Exit. It does not alter the serialized GodState,
disk layout, player tokens or wire format.

Between native frames, the existing local reload envelope now distinguishes a
campaign restart from Practice round restart. Campaign invokes original
cGod::Restart, preserving its Core_Restart, stats reset, commando creation,
start-script attachment and SINGLE_RUNNING handoff. It keeps the current
selected campaign archive mounted. Practice still invokes its original shared
network restart owner and uses the original map cycle. No platform respawn
implementation or fresh campaign replacement was added.

Before reload, native presentation releases dialogs, TextWindow scene and
prepared render references and flushes input. Original Load_Level now preserves
an installed native completion observer before object/script creation and
begins the next level's observation there. After success the native envelope
restores original render resolution/capabilities, TextWindow
background scene, player reference and cached progress/capture state. Failed
required loads return from cGod::Restart before player creation and retain the
existing load-failure code and cleanup-gated menu recovery. Failure tracking
inside original Load_Level remains native; host execution does not establish
that native failure route.

The full host runtime source definition now includes the existing
a35_level_load_status.cpp provider once, alongside the gameplay boundary.
Native already selected it. This is source/link wiring only: no host or ARM
compile/link was run. All affected units require coherent rebuild.

### Load and cancellation

Native cGod::Load_Game opens the original LoadSPGame menu over suspended
Combat instead of calling End_Game during dialog dispatch. Inspection also
found LOC_LOAD_GAME excluded from RenegadeDialogMgr::Goto_Location in the
native frontend. The new patch moves that existing case into the supported
full-frontend scope; its existing include and dialog implementation are used.

Original LoadSPGameMenu::Load_Game already queues Start_Game through the
frontend latch. The death/failure pump now copies that reload request into
A31VitaInteractiveResult, as the ordinary pause route does. Session cleanup
precedes the outer launcher's existing save/level handoff. Previously the
death route broke out without retaining the selected source.

If the load menu is cancelled and the death/failure context has no dialogs or
restart/reload request, it queues original NeedsGameExit. It must not resume
a dead world with no options UI. Quit/main-menu commands likewise queue the
original exit request and rely on the between-frame GameInitMgr consumer.
Mission failure's original IDCANCEL suppression is retained.

The death pump no longer clears terminal callback evidence or reports a
successful restart simply because Combat resumed. Observation/cache reset
now separates next-level observation at original Load_Level's seam from
post-reload cache reset; an unexpected closed death dialog
with no request falls back to the original menu-exit request.

### Reload callback ownership

Further inspection found original Load_Level replaced the native misc handler
with GameMiscHandler during reload. Its success callback only sets
PendingCampaignContinue, which the native simulation route does not consume;
reinstalling/resetting the observer after cGod::Restart also loses callbacks
generated during load or start-script attachment.

A31_Interactive_Restart_Mission_Completion_Observation now resets/reinstalls
only an already-active native observer. The new patch calls it at original
Load_Level's misc-handler seam before threaded load and retains the original
handler when that native owner is absent. End_Observation clears its active
flag. The native reload envelope no longer resets observation after creation,
so new-level callbacks survive through the next normal event-consumption step.
Cache/result flags are reset separately and do not clear the producer latch.

On first observed mission failure or star death, the native consumer also
offers the event to the original cGod handler after initialization. This covers
callbacks that arrive before cGod resumes SINGLE_RUNNING during original
restart; its existing state guard suppresses duplicate popups for normal
in-frame callbacks. Star handling requires an existing original star and is
limited to local campaign sessions. No terminal event is invented or forced.

### Open evidence and risks

No staging, test, build, emulator or physical operation ran. All changes are
local/uncommitted/unvalidated. The callback-ownership window has source wiring,
but callbacks during load/player/start-script creation need runtime evidence
before acceptance. Save loading
of dead-state snapshots, repeated retry inventory/statistics, replay runtime
acceptance and initial failed-load recovery acceptance remain open boundaries.
The original audio pre-service waits in Continue_Game are retained, not a
measured performance improvement.

Focused acceptance still requires ordinary player death and script-driven
mission failure; readable original popups; restart with correct level-start
inventory, stats, start script and camera; load selection/cancel with held
controls; empty/missing saves; quit; corrupt reload recovery; and repeated
cycles without memory/resource growth on matching Vita and PSTV candidates.
Successful source wiring or a later compile will not prove these behaviors.

### M13 finale delivery trace

The Vita script build now has a bounded, M13-only trace across the existing
retail-authored finale route. `MX0_Area4_Controller_DLS` records the ion-strike
timer, the later finale timer and its cinematic owner, and receipt of the
`MX0_MISSION_SUCCESS` custom event. `Test_Cinematic` records only the
`Send_Custom` command issued by `X0Z_Finale.txt`, including target ID, lookup
result, event type and parameter. These one-shot breadcrumbs distinguish timer
loss, cinematic creation failure, missing object 1500017 and failed custom
delivery without changing any authored timing or forcing completion.
If the beacon actor or invisible cinematic controller cannot be allocated, the
script records an owner ID of zero and leaves the original route unresolved
without passing the missing object to `Attach_Script` or `Set_Facing`. It does
not substitute another actor/controller or complete the mission on the
platform's behalf.
The beacon breadcrumb separately records whether authored object ID 1500087
resolved. Its position is no longer dereferenced when that required placed
object is absent, so the diagnostic distinguishes level-ID loss from actor
allocation failure.

This is source instrumentation only. It has not been staged, compiled or run
under the active validation hold, and it does not establish that the finale
works on Vita or PSTV.

### Level-owned cinematic camera teardown

Source review found a campaign transition lifetime defect in the released
ownership order. `CCameraClass::Set_Host_Model` retains the cinematic render
object and activates the global cinematic freeze, while `CombatManager` keeps
its main camera alive across individual level unloads. A mission can report
success before its finale sends the authored `Control_Camera, -1`; Mission 01
does so on an independent 20-second completion event. The previous unload path
then destroyed game objects and freed W3D assets while the persistent camera
still retained the level-owned host.

`CombatManager::Unload_Level` now clears the main camera host before
`GameObjManager::Shutdown` and `WW3DAssetManager::Free_Assets`, and defensively
clears the cinematic-freeze flag at that same per-level boundary. This uses the
original camera setter, including its profile restoration and reference release;
it does not change authored cinematic timing or mission-completion ownership.
The deterministic staging patch is
`port/patches/combat-a36-level-cinematic-camera-release.patch`. This correction
has source-inspection evidence only under the active validation hold.

### Classified campaign handoff recovery

The original intermission boundary previously treated only a successful
bounded `CampaignManager::Save` as a next-level handoff. Source rejection,
RAM-state open/write/size failure, or `CampaignManager::Continue` failing to
consume the old game silently left the result without a clean transition and
caused the application wrapper to terminate.

Those branches now record a distinct `A31CampaignHandoffFailure`, request
owned session teardown, and reopen the original main menu after cleanup. They
do not fabricate a next level or advance campaign state. An overlong consumed
`Start_Game` request now publishes a rejected-start edge so both frontend and
intermission pumps terminate instead of waiting forever. Campaign `Level`
directives are also required to contain exactly one map token, preventing a
truncated prefix from passing catalog admission.

The released 1.5-second pre-service and 250-millisecond post-service audio
windows are preserved, but Vita iterations now yield for one millisecond after
each audio update instead of busy-spinning a Cortex-A9 core throughout mission
start/end transitions. These changes remain uncompiled and untested under the
active validation hold.

### Teardown-safe score progression, autosave, and movie input

Normal score acceptance still advances through
`ScoreScreenDialogClass::On_Destroy`. Native forced dialog cleanup now marks a
narrow teardown scope so destroying a still-open score dialog cannot call
`CampaignManager::Continue` after the session result has already been decided.
The flag is cleared immediately after `DialogMgrClass::Flush_Dialogs`; ordinary
IDOK/IDCANCEL progression is unchanged.

An autosave requested by a campaign `Level` directive is retained across a
successful handoff and consumed by the original gameplay owner after the new
world starts. If source admission, archive loading, player binding, or campaign
state handoff fails, the recovery boundary now clears that abandoned request so
it cannot write into a later tutorial, replay, or new campaign session.

Movie skip-edge state now belongs to each `MovieGameModeClass` instance rather
than a function-static process lifetime. `Init` and every `Start_Movie` sample
the current Menu Toggle state, so a control held through score/menu transition
requires release and repress before it can skip the new movie. Consecutive
campaign movies retain original `Movie_Done` progression and Bink ownership.
These changes have source-inspection evidence only.

### Mission-complete input handoff

The native intermission owner now disables the gameplay input route before its
first menu-state sample, then primes the established WWUI transition tracker
before dispatching success to `CampaignManager::Continue`. This prevents a
recorded gameplay input frame from being replayed into the score/movie UI. A
control held on the final gameplay frame is baseline state rather than a new
score-screen action. Original score, movie and campaign progression code
remains responsible for subsequent input and transitions. This source
correction is uncompiled and has no runtime or physical acceptance evidence.

The campaign-state writer now returns the sticky `ChunkSaveClass` result rather
than reporting success unconditionally. The native session handoff already
classified a false `CampaignManager::Save` result and retained the old campaign
session for clean recovery; this closes the writer side of that contract so a
failed chunk header, field, or close cannot be published as a valid next-level
state merely because the RAM file contains some bytes. The original two-field
campaign format and `CampaignManager` progression ownership are unchanged.

The same status contract now reaches the gameplay state that determines whether
a resumed mission can continue faithfully. Script timers and their sender
references, observer references, action parameters and their move/attack/look
targets, weapon ownership/targets, and every non-default weapon-bag entry report
failed nested writes through `ChunkSaveClass`. Null timer or weapon entries are
rejected instead of dereferenced or silently omitted. `ScriptableGameObj` also
aggregates its base, referenceable, observer-timer, and custom-timer writers.
This preserves the released chunk layout while preventing a quick, manual, or
autosave from being committed after losing mission timers, AI action targets,
or the player's inventory state.

Failure propagation now continues through the persistent gameplay-object
inheritance chain. Base, scriptable/damageable, physical, armed, smart, soldier,
and vehicle writers report the shared transaction status; physical animation
and host references, defense state, control/action state, stealth state, human
state, transition completion, damage attribution, and weapon bags all feed that
result. Vehicle transition destruction/recreation still occurs in the released
order even when writing fails. This lets the persist factory reject an
incomplete Havoc, NPC, or vehicle record instead of accepting it because an
intermediate class returned unconditional success.

The sibling persistent branches now follow the same rule. Simple objects,
powerups and their optional weapon bags, planted C4 ownership/stuck-object
references, and cinematic actors all propagate their parent and nested write
status. These records are used throughout campaign objectives and scripted
sequences, so losing one while still publishing the enclosing world would make
later mission behavior diverge silently.

Campaign and C&C building state now reaches the same transaction boundary.
`BuildingGameObj` propagates damageable state, while power plants, communications
centers, refineries, soldier factories, vehicle factories, airstrips, war
factories, repair bays, and animated building aggregates propagate their parent
and physical-animation writers. This covers power/destruction state, refinery
docking and unload progress, production queues and aggregate animation state
without adding fields or changing original building/base-controller ownership.

### Save-state admission and corrupt-list filtering

Source inspection found that original `cGod` serializes only its numeric state,
while both player death and script-driven mission failure use
`GOD_STATE_SINGLE_DEAD`. A save made under either terminal popup therefore
cannot restore which original popup and continuation rules owned the session.
The selected Vita patch now exposes a read-only `cGod` admission query and
allows autosave, quicksave and manual save only in
`GOD_STATE_SINGLE_RUNNING`. Startup autosaves remain requested until original
`cGod::Think` enters that state; quick/manual terminal attempts are rejected
without changing the original save format.

The invariant now also lives inside `cGod::Save`: a direct caller cannot bypass
the UI admission checks and serialize ambiguous `SINGLE_DEAD` state. Vita load
admission continues to reject legacy terminal snapshots. Script-data loading
marks the shared chunk transaction failed for null destinations, negative
capacities or saved fields larger than their destination, so ScriptManager can
reject the complete save before mission callbacks run.

The load menu now checks `Smart_Peek_Description` for `.sav` entries and omits
files whose chunk metadata cannot be read. Ranked `.mix` replay entries retain
their original handling. This prevents a partial or corrupt save from being
presented as a selectable campaign continuation, while the atomic rooted-file
writer preserves the previous completed save until replacement succeeds.

Writer-side semantic failure now crosses the generic persistence boundary.
`ChunkSaveClass` owns a sticky error bit, `SimplePersistFactoryClass` reports a
failed concrete-object `Save`, and `SaveLoadSystemClass::Save` combines the
subsystem result with chunk open/close status and that sticky bit. The existing
atomic file owner can therefore abort publication when a nested persist object
rejects serialization. This preserves the released void persist-factory ABI.
The adjacent structural patch also initializes the load-reader error bit in the
reader constructor rather than the writer constructor. Both case-distinct
persist-factory headers now implement the same contract, including the uppercase
header used by `CNCModeSettings.cpp`. The two custom render-object factories
reject null inputs, and chunk writes retain short-write failure in the same
sticky status.

The original top-level save owners now preserve their child results as well.
Combat aggregates every required manager, Commando aggregates network, cGod
and campaign state, physics retains structural errors across its
scene/constants/path records, and
network/player and conversation lists reject failed child records. A false
result at these layers now reaches the existing pending-file abort instead of
publishing an incomplete save as successful.

These changes are local source wiring only. Patch staging, compilation, save
round trips and Vita storage-failure behavior have not been exercised under the
active test hold.

### Mission combat, trigger and observer writer status

The campaign save transaction now retains child failures from another set of
objects that can remain live across a mission checkpoint. Bullet persistence
rejects missing ammo definitions and null manager entries, and propagates owner
and target reference failures. Beacon, special-effects and SAM-site objects
propagate their inherited state, including beacon owner and cinematic-object
references. Damage, script and transition zones now propagate inherited and
vehicle-reference writes; script zones also reject null reference-list entries.
Persistent soldier observers propagate both their base record and enemy-object
reference. These changes preserve the existing record layout and original
gameplay ownership while preventing a failed nested write from being published
as a valid campaign save.

This is source and deterministic-staging evidence only. Compilation, save
round trips, mission completion and physical Vita behavior remain unverified
under the active test hold.

Player and interactive-world persistence now participates in the same failure
transaction. `cPlayer` propagates its `PlayerDataClass` result. Accessible
animated physics propagates its static-animation parent and variable writer;
doors and elevators propagate that result, and elevators also retain a failed
current-rider reference write. Damageable static objects propagate both their
animated-physics and defense-object writers. This protects mission doors,
elevators, destructible scenery and the player record without adding fields or
altering their released chunk layout.

The underlying WWPhys inheritance chain still needs the same audit: these
callers now detect a false parent result, but any deeper parent that continues
to return unconditional success can still conceal a semantic failure.

The first underlying WWPhys chain is now closed. `PhysClass` rejects a missing
render model instead of dereferencing it, and returns the shared writer status
after its model factory runs. `DynamicPhysClass`, `StaticPhysClass` and
`StaticAnimPhysClass` propagate their parent results; static animated physics
also propagates its animation-manager writer. This makes the checked door,
elevator and destructible-world callers meaningful through the base physical
object and model record. Other specialized moving-physics subclasses remain in
the continuing audit.

The moving-physics branches now carry that result through the original class
hierarchy as well: moveable physics, rigid bodies, generic vehicles, motor and
wheeled vehicles, tracked vehicles, VTOLs, motorcycles, Phys3 and human
movement, projectiles, decorations, render-object physics, timed decorations
and dynamic animated physics. Dynamic animation also propagates its animation
manager result. This covers the principal physical records behind soldiers,
campaign vehicles, ordnance and scripted animated scenery while retaining the
released fields and inheritance structure.

Audio-scene persistence now follows the same transaction. Base sound-scene
objects, audible sounds, positional 3D sounds, logical sounds and logical
listeners propagate parent failures and the shared chunk-writer status. Logical
sounds are mission AI stimuli as well as audio-adjacent state, so silently
publishing an incomplete record could alter enemy-hearing and scripted-event
behavior after a load. No playback-provider behavior or save fields changed.

Mission manager state now participates in the transaction end to end. Blendable,
simple and human animation controllers propagate parent/channel failures;
conversation definitions, orators and active conversation participants retain
reference failures; and game-object, objective, cover, persistent-observer and
spawner managers reject null list entries before serialization. Objective
targets and last-spawn references are also checked. This protects mission
dialogue position, scripted animation continuity, objective completion, AI
cover data and reinforcement scheduling without altering the original manager
ownership or chunk schema.

World-state writers now retain failures from combat camera and player-star
references, screen-fade interpolators, radar markers, static pathfinding,
action/waypath portals and sectors, shakeable/light physics, and terrain
material layers. Required terrain material owners and material-pass list
entries are checked before dereference. This covers cinematic overlays,
navigation, radar guidance and persistent terrain rendering state while
preserving original records and runtime ownership.

The corresponding load-side audit is now active. Saved action parameters
propagate failed move, attack and look-object references. Action restoration
rejects missing persist factories, null action-code products, duplicate or
failed parameter records, and missing required parameters. Weapon bags reject
duplicate/missing structural chunks, failed weapon entries and invalid selected
indices; weapon restoration rejects missing weapon/ammo definitions and failed
owner/target references. Invalid records therefore stop before AI or weapon
state is published into a resumed mission. Original formats and runtime owners
remain unchanged.

Game-object restoration now carries those failures through the principal
inheritance chain. Damageable, physical, armed, smart, soldier and vehicle
objects propagate parent, defense, animation, weapon-bag, control, controller,
action, human-state, transition and reference results. Required physical
objects, physics observers, animation controls, stealth effects, render-object
factories and render products are checked before dereference. Excess soldier
dialog records are rejected. This prevents a partially restored actor or
vehicle from reaching post-load callbacks as an apparently valid mission
object; chunk layouts and original ownership remain unchanged.

Building restoration now propagates failures through `BuildingGameObj`, power
plants, communications centers, refineries, vehicle/soldier factories,
airstrips, war factories and repair bays. The special mission-object branches
do the same for simple objects, powerups, C4, beacons, cinematic and special
effects, SAM sites, damage/script zones and transition objects. Weapon-bag,
owner, stuck-object, cinematic-object and zone-inside references are retained
as transaction failures instead of being silently accepted. This covers base
state, production, beacon/C4 objectives and trigger occupancy without changing
their original records.

Boss restoration now participates in the same admission boundary. Mendoza
propagates soldier, state-machine and camera-spline failures. Sakura propagates
vehicle, rocket-defense, target/damager/pilot reference and path failures while
replacing the constructor-created path without leaking it. Raveshaw propagates
soldier, stealth-soldier, all combat state-machine and Tiberium-effect failures,
and rejects a missing required effect before dereference. A rejected boss
record therefore cannot proceed into its post-load initialization as valid.

Foundational WWPhys restoration now carries failure through `PhysClass`,
dynamic/static/animated-static physics, moveable physics and rigid bodies. The
base physical loader rejects a missing nested model chunk, missing render-object
factory or null render product before model installation, while derived classes
propagate parent and animation-manager failures. This makes the earlier
game-object admission meaningful through its underlying physics record instead
of allowing a broken model/physics object to reach post-load callbacks.

The derived runtime WWPhys load chain now carries the same result through
generic, motor, wheeled, tracked and VTOL vehicles; Phys3 and human movement;
projectiles; decoration and render-object physics; timed and dynamic animated
decorations; accessible objects; lights; and shakeable static objects. Dynamic
animated physics also propagates its animation-manager load result. These
classes continue to parse the released chunks and register the same post-load
callbacks, but a failed parent or child load can no longer be converted into an
unconditional success before Combat admits the enclosing actor or world object.

The corresponding definition hierarchy now preserves failure as well. Physical,
dynamic, static, animated-static, moveable and rigid-body definitions carry
their original base-definition status through the vehicle, motorcycle, Phys3,
human, projectile, decoration, timed-decoration, accessible and shakeable
branches. Static and dynamic animated definitions also retain projector and
animation-manager failures. Retail `objects.ddb` remains the definition owner;
this change only prevents a failed nested definition parse from being reported
as a valid preset.

Definition loading now returns the generic save/load result to its callers.
The required base `objects.ddb` load stops the Combat loader before animated
sound or level data can consume a rejected catalog. An absent optional
level-specific `.ddb` retains released behavior, while a present but malformed
override records a required-load failure and skips the static-level load for
that envelope. This connects nested preset rejection to the existing original
level-load failure and cleanup owner instead of leaving a partial catalog live.

Definition child records now participate in the same admission boundary.
Dialogue and dialogue-option loaders return status, reject over-capacity
dialogue arrays, and publish options only after a complete load. Transition
records are added to vehicle and transition-game-object definitions only after
their nested load succeeds. Building aggregate state-animation records return
their stream status. The mixed-case `PersistFactory.h` include alias is also
refreshed from the hardened lowercase implementation after every staged patch,
so case-sensitive Vita builds cannot select the stale factory template.

The translated-string database now participates in the same admission boundary.
Its top-level variables, object table and category table must each occur once;
factory and chunk failures propagate; required object/category fields and
UTF-16 byte alignment are checked; and a rejected load discards partially
published lookup tables. This keeps the original `strings.tdb` format and
translation owners while preventing partial menu, objective, subtitle and
conversation text from being treated as a valid database.

WWAudio now carries the same failure contract through its original sound
definition and save/load owners. Audible-sound definitions require one base and
one variables envelope and return stream status. Static and dynamic scene
writers propagate nested scene failures. Their readers reject duplicate scene
records and missing runtime scene ownership; dynamic logical-listener scale and
background-music changes are staged until the complete variables/scene envelope
has been admitted, preventing a rejected save from partially changing global
audio state.

The shared defense-definition component now admits its released variables
envelope transactionally. All eight health, shield, armor and score fields must
occur exactly once at their original 32-bit widths; duplicate or truncated
fields fail; armor save IDs must resolve back to the same retail armor entry;
and live definition fields are assigned only after complete validation. This
applies beneath soldiers, vehicles, buildings and destructible world objects
without changing damage or armor ownership.

Definition catalog publication is now transactional at the original manager.
Factory results are staged outside the searchable catalog, sorted and checked
for zero or duplicate IDs against both the incoming batch and the live catalog,
and published only when the complete objects envelope and all nested loaders
succeed. Rejected definitions remain quarantined through pointer-token remap
and the failed-load return so other partially loaded objects can unwind safely;
they are retired at the next load boundary after recovery rather than becoming
searchable presets or being freed underneath remapped pointers.

The transaction now has a definition rejection hook for title-owned singleton
state. EVA settings preserve and restore the previous original settings owner
when their definition batch is rejected. Objective-viewer reload and message
window clearing no longer occur inside parsing; they are registered with the
original post-load phase and run only after pointer remapping and complete
save/load admission. The mixed-case `Definition.h` alias is refreshed after
late hardening patches so Vita's case-sensitive build sees the same hook.

The same rejection contract now covers the general gameplay settings, HUD
settings, character-class table and C&C mode settings. Each definition records
the previous original singleton owner before construction, restores it when a
batch is rejected, and only clears or restores ownership from its destructor
when it is still the active instance. Reverse-order rejection preserves the
ownership chain when more than one singleton definition was constructed in a
single rejected batch.

Purchase and team-purchase definitions now publish their original indexed
team/type slots only after their parent and variables envelopes succeed and
their decoded indices are in range. Each slot retains its previous owner and
restores it on rejection or destruction, so a malformed retail override cannot
replace the purchase-terminal or Practice lookup table. Their writers and
nested variable readers now return stream status instead of unconditional
success.

Campaign catalog initialization is now generation-safe. The released owner
stored campaign flow and backdrop records in process-global vectors but only
cleared them from `Shutdown`; a second `Init` after frontend recovery could
append a duplicate copy of the retail sequence and advance through repeated
score, movie and level directives. `CampaignManager::Init` now clears both
catalogs before parsing `campaign.ini`. It still resets campaign state and
loads every directive from the original data; no order or fallback campaign is
synthesized.

The original WW3D asset manager now retains hierarchy, animation and prototype
loader failures while scanning a W3D file and returns the final chunk-reader
status. Previously it returned success after failed child loads and could let a
partially populated model set cross the required level-load boundary. Existing
asset owners and cleanup remain unchanged; no alternate model format or
renderer path was introduced.

Dazzle prototypes now require one nonempty object name and one nonempty,
registered dazzle type. Duplicate, truncated, missing or unknown type data
returns the existing W3D load failure instead of silently selecting type zero,
and the prototype loader no longer publishes an object after its child load
failed. This keeps the original Dazzle renderer and retail type registry as the
owners of mission lights and lens effects.

Fixed-layout box and null-object W3D prototypes now require an exact structure
size, a complete read and a nonempty terminated object name before publication.
This prevents truncated fixed records from entering the original asset catalog
and lets the aggregate WW3D failure above reach level-load recovery.

Sphere and ring prototype loaders now require one exact released definition
record and reject duplicate animation-channel records. Child stream failures,
missing definitions and unterminated names prevent prototype publication while
the original primitive render objects and animation channels remain unchanged.

Restored campaign handoffs now bind serialized progression state to the
original catalog's current `Level` directive and require that directive to
match the separately resolved next archive. A stale but individually valid
state/source pair is rejected before world creation instead of loading one
mission while advancing another mission's score, movie and backdrop sequence.
Missing catalog, rejected source, state read/load and state/source mismatch
restore failures now receive distinct campaign handoff classifications and use
the existing cleanup-gated return to the original main menu.

Mission dependency preloading now distinguishes an absent optional `.dep`
from malformed metadata or a listed W3D rejected by its original loader. It
checks file open, root and micro-chunk closure, complete filename reads, nested
WW3D results and final reader status. The native load-failure latch is reset
before this preload and retains dependency rejection through the existing
required-level cleanup path instead of erasing it immediately before threaded
loading.

The Vita load menu now clears carried level-start inventory only after an
ordinary save request has been accepted by the frontend latch. Opening and
cancelling replay difficulty, or invoking Load with no selection, leaves the
suspended campaign inventory intact. Replay continues through the original
`CampaignManager::Replay_Level` reset after difficulty acceptance.

Campaign backdrop selection now tracks a separate match flag and stops at the
first matching retail backdrop. Index zero remains a valid selected record
instead of emitting a false missing-backdrop diagnostic; a real miss still
retains the released index-zero fallback.

The original campaign intermission pump now detects only a sustained loss of
every presentation owner: no dialog and no active Movie mode for 120 frames.
That state is classified for cleanup-gated recovery instead of spinning
forever. An existing score or end-menu dialog can remain open indefinitely,
and active movie playback has no artificial duration limit.

The campaign movie-unlock write now crosses a checked registry boundary. A
locked or invalid registry, rejected movie key, allocation failure, or durable
provider write failure is reported to `CampaignManager::Continue`; progression
continues because the movie directive follows an already completed gameplay
state and a persistence failure must not replay or roll back that mission.

Ordinary save restoration now binds the restored campaign state to the map in
the original save header before post-load callbacks publish the world. Normal
campaign saves must match their current `Level` directive. Tutorial's
non-campaign state is accepted only for `M00_Tutorial.mix`; Replay remains a
header-owned, non-advancing route; the replay-score intermission state cannot
own a gameplay save. Rejection uses the existing cleanup-gated local recovery.

The deterministic staging stack contains 492 ordered patches with inventory
SHA-256 `8f44da574ac3e926a5061edb80927e3aedfb0461cb6fd09316b77173c7f468cd`.
A complete reconstruction from the pristine EA source, staging consistency,
mixed-case factory identity, reject/original-debris inspection and
`git diff --check` pass. Compilation and runtime validation remain paused.
## Development campaign-save launcher

The opt-in one-shot `RVCP1` launcher now admits any valid original campaign
save in the full-port profile instead of requiring a tutorial save. The request
parser still accepts only a sanitized save basename and constructs the rooted
`save/<name>.sav` source. Before consuming the request, the launcher uses the
existing frontend single-player resolver, which reads the original save header
through `SaveGameManager`, classifies its `M##.lsd` map, and derives the
matching retail MIX name. The normal load path later checks that archive through
the original file-factory boundary. The launch uses team choice `-1`, matching the
original Load Game menu, and leaves all deserialization to the original runtime.

Source inspection also found and corrected a guaranteed death-restart rejection:
the campaign branch passed a null save-classification output to a resolver that
requires a valid pointer. It now supplies `restart_source_is_save` and accepts
only a resolved map archive, allowing the original `cGod` restart route to reach
the reload envelope while still rejecting save sources there.

The M00 demo profile retains its tutorial-only restriction. The standalone
mission launcher remains map-only. This gives development builds a bounded path
to return directly to saved M13/M01 and later campaign states without changing
normal campaign progression or save files. Source only; no save has been loaded
or accepted on hardware through this expanded route.
