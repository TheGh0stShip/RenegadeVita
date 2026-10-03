# Complete mission overview review — 2026-10-03

Every section of the supplied overview is accounted for below. This closes a
review-accounting gap; it does not certify every numeric claim, asset linkage,
behavior or recommendation. The previous reconciliation checked the mission
manifest deeply but explicitly left aggregate media counts and runtime systems
unverified. Those limits remain. No complete-content or native gate is closed.

The deeper [soldier voice audit](MISSION_VOICE_ROUTE_COVERAGE.md) now traces
global voice findings into preset and serialized dialogue tables. Most affected
options are DIE tables without a direct Combat caller; M01 has a concrete
idle-to-search record requiring branch/runtime verification. 220 focused
source/Python tests pass; this does not certify every linkage in the overview.

The reproducible source-owner review is `tools/audit_mission_research.py`.
It checks all 16 system groups, 13 mission source units, additional script
files, the eight prominent call counts and review scope for the architecture,
10 asset classes, 11 port-checklist items, four profiling priorities and nine
caveat groups. Source references are matched case-insensitively for discovery
and report actual canonical paths; build paths still require their exact case.
Every nominated system owner is located. Presence does not prove target
selection, successful linkage or runtime registration.

The subsequent [event/callback sweep](CINEMATIC_EVENT_ROUTES.md) traces source
callers, actual header constants and parameter contexts for Tutorial/M13/M01.
It retains four slot leads and native/runtime uncertainty; the focused suite
now has 191 passing source/Python tests. It does not certify the remaining
command, media or gameplay requirements listed below.

## Architecture and count claims

The [campaign reconciliation](CAMPAIGN_SOURCE_MAP_RECONCILIATION.md) confirms
13 source units, 101,508 source lines, 1,370 declared scripts, 143 used command
methods from 202 table entries, and the per-mission literal-ID counts. The
original DSP has 45 source entries; 44 original code units plus the existing
static provider replace the DLL entrypoint. Seven previously omitted mission
units were restored in source, still uncompiled. Campaign order and the M13
opener were confirmed against the user's retail campaign.ini, rather than
leaving the opener as an inference. Numeric-ID preservation remains a runtime
and save/load requirement, not a conclusion from that campaign file.

| Quoted call count | Supplied overview | Current source parser | Assessment |
|---|---:|---:|---|
| Find_Object | 3,478 | 3,480 | discrepancy open |
| Send_Custom_Event | 2,991 | 2,994 | discrepancy open |
| Create_Object | 872 | 872 | matches |
| Attach_Script | 732 | 732 | matches |
| Join_Conversation | 712 | 712 | matches |
| Action_Goto | 661 | 661 | matches |
| Start_Timer | 614 | 614 | matches |
| Debug_Message | 150 | 150 | matches; already WWDEBUG-gated |

These counts remove comments but are source expressions, not executed calls.
Different conditional-compilation/parser scopes may explain differences; no
normalization or invented runtime omission is applied. Distinct cinematic and
music literal counts, 365 and 12, match. The approximate 436 conversation keys,
367 string IDs, 101 objective images, 119 presets, 104 sound names and 34
assembly-containing files remain independently uncertified aggregate claims.

## Shared systems and suggestions

| Supplied group | Review and port treatment | Verification still required |
|---|---|---|
| Script runtime | Original manager/commands/zones, registrar/factory and static provider retained | All commands, timer/custom/zone delivery, state restoration and registrations |
| Shared scripts | Exact DSP inventory governs toolkit/designer source selection | Retail attachments, parameters and every helper callback |
| Innate behavior | Original soldier observer, soldier and smart-object owners located | Senses, cover, home/aggressiveness switches and per-frame cost |
| Scripted actions | Original action/path-action/vehicle-driver owners located | Goto/attack/animation/enter-exit/dock/facing/input and action-complete chains |
| Pathfinding | Original Pathfind/Path/PathObject/Portal owners located | Actual map navigation; time slicing is deferred pending measured evidence |
| Conversations/voice | Original conversation/active-conversation/viseme owners; omitted CONV10.CDB load restored in source | Playback, remarks, speaker lifetime, lip sync, global unresolved voice IDs |
| Cinematics | Original Test_Cinematic/scene-object/camera retained; 166 reached candidates traced | External slot fills, primary-death state, callbacks, timing and visual/audio fidelity |
| Bosses | Mendoza/Sakura/Raveshaw owners exist and full-port manifest names them | Every boss fight on hardware; Petrova remains script-owned |
| Objectives/HUD/radar | Original objectives/HUD/radar/encyclopedia owners; direct text/image candidates investigated | Rendered help, map/radar progress, objectives, unlocks and touch behavior |
| Buildings/defenses | Original building/airstrip/factory/harvester/beacon ownership retained | Power, MCT damage, delivery, docking and single-player beacon completion |
| Weapons/damage | Original weapon/bullet/explosion/damage/C4 owners located | Weapon and collision/damage behavior; aim changes require separate approval/evidence |
| Rendering | Existing Vita boundary beneath WW3D; DX8 wrapper/renderer/texture/buffer source links located | Fog, stealth, beams, effects, bones, blend/depth and physical visual correctness |
| Audio | Existing Miles-compatible provider remains beneath original audio ownership | Positional/2D/music/twiddler behavior and non-audible AI stimuli |
| Movies | Existing FFmpeg boundary decodes unchanged retail BINK | Campaign movie playback, timing and A/V; mandatory retail MP4 conversion rejected |
| Weather | Original command/weather/background owners located | Rain/fog/wind/ash/lightning/blitz and fill-rate; emitter reductions deferred |
| Platform | Existing native input/filesystem/timing/thread boundaries retained | ARM ABI, all input locks, lifecycle and storage; thread publication corrected in source below |

The supplied action and innate-command lists are requirements, not evidence
that those commands work. Linking a source file unchanged is insufficient
where Win32, assembly, thread state or serialized widths cross the boundary.
No performance suggestion automatically authorizes removing mission content.

## Every mission section and its remaining linkages

The complete play-order/beat descriptions were reviewed as investigation
targets. Their narrative ordering, all listed asset counts and exact runtime
conditions are not independently certified by the source-owner inventory.
The following retains the supplied content scope instead of dropping later
missions or treating a few representative areas as the full game.

| Section | Content and special links retained for verification | Current evidence |
|---|---|---|
| Tutorial | Logan movement/checkpoints/camera; Sydney health/armor/radar; Gunner moving targets and all weapons/beacon; Hotwire Humvee/tank/squish; Mobius refinery; Petrova power; stealth win/lose; final Apache/flyover/MCT; MSK multiplayer-primer zones | Deep authored bindings, direct text/image candidates and source selection checked; all stations, touch locks and native progression unverified. MSK primer is outside inspected Tutorial attachments. |
| M13 opener | Intro flyover; two engineers and wrong-way/sniper branches; troop drop; Tiberium harvester/Orca; reinforcement infantry/Humvee/tank; section 4 buggy/turrets/tank; completion; damage-modifier and send-ID helpers | Authored IDs, computed dialogue and cinematics traced. Four normal slot leads across M13/M01 and the HIT6 damage/voice lifetime remain open. |
| M01 | Beach/base/spawners/artillery and five controls lines; church/nuns/priest disc/evac; barn/prisoners/truck/ropes; cave/visceroids; bridge/harvester/turret beach/gunboat; tunnel/tank/Billy; tailguns; detention/towers; every Hand of Nod room; Comm Center/SAM/Kane; propaganda; flyovers; finale | Largest source is selected; deep bindings, direct HUD/objective text, conversations and cinematic candidates checked. ConYard filename, callback/ID lifetimes, finale audio layouts, voiced PC controls and complete native route remain open. |
| M02 | Area A00–A24 wakeup; buggy/tank/Sakura; dam/MCT; plant/Obelisk power; convoy/helipad/jet; Mendoza; data disk/Mobius transition/evac; respawn/reinforcements; objectives/logical sounds | Source/registration counts and literal-ID inventory checked. Area ordering, all 187 lookup lifetimes, vehicles, logical stimuli and retail media not fully verified. |
| M03 | Beach/inlet/gunboat; Chinook/paradrops; SAMs/turrets; tailgun/cave/lift; volcano/lava/earthquake; big guns; Nod base/harvester/keys/repair; Comm Center/Kane/radar; Sakura dogfight/outro; ambient flyovers | Source and cross-mission links recorded; lift/paradrop reuse, boss behavior and particle/weather visuals require data/runtime verification. |
| M04 | Boarding/patrols; cargo/missiles; engine targets and ambience swap; prison/lift/warden; medlab; aft deck/first mate/repopulation; Apache hangar floors; mutant Tiberium hold; fore deck/mess/torpedoes; giant SAM/captain; prisoner firefight/rescue/sub escape; hunter reuse | Source selected. Parameter-driven zone sounds, layered ambience, doors, room conditions and rescue route remain unverified. |
| M05 | All Dead-6 rescues and resistance team switches; repeated Mendoza; Inn/Hotwire midtros; collapse; square/triangle/bridge; overlook/dump captives; cache/escapee/windows/Babushka; park; sniper alley/roadblock/execution; cathedral; APC/artillery/Tiberium spill and drops | Source selected; reused M07 Apache effect, armed-civilian weapon/preset links and exact Aggessiveness parameter retained. Town-square profiling deferred. |
| M06 | Gate/tank/towers; courtyard/maze/allies; barracks; alarm switch/terminal/engineer/objective and heard stimuli; room spawning; secret door/cache; war room/Kane; greenhouse/lab/prisoners; scientists/midtro; Mendoza; burning collapse/escape; Thunder squad | Source selected. Alarm convergence, Sydney protection, boss behavior, every model/debris swap and escape route require verification; no emitter budget change adopted. |
| M07 | Dead-6/Sydney deaths; SAM trucks; Inn and rope evac; mobile radar/square; napalm/barrels; SSMs/Obelisk/stealth tank; hostages/resistance; triangle/bridge/vehicle zones; Hotwire; present/vehicles/rocket emplacement; evac/nuke inside/outside zones; air/paradrops | Source selected. Countdown/zone/death logic and squad survival, shield/team changes, rope rigs and nuke visuals unverified. |
| M08 | Pistol-only prison/free prisoners/yard; Petra A/B/C; convoy/stealth trap/player tank; archaeological dig; facility/helipad/observatory/cultivation MCT; cavern; stations/scientists/elevators; mutant pens/lock 10; Sakura/Kane; midtro/Raveshaw | Exact lowercase filename and Archaelogical spelling retained. Source selected; canyon/draw-distance, cloak, pens, cutscene protection and boss behavior unverified. |
| M09 | Mobius and power suit/follow; lab scientists; keys/containment; mutant encounters/team/damage switches; explosions/elevators/security cameras/Shuman; excavation spawners; checkpoint paradrop reuse; SAMs/stealth tank; surface weather/evac/Gunner | Source selected. Frame-rate-sensitive escort, lock 10, reused M03 rig/camera scripts, dynamic dialogue IDs, weather transition and escort completion unverified. |
| M10 | Reinforcements/cargo; gates/keys/fences; turrets/SAMs; every base building/power/repair/spawns; Obelisk; helipads/Apaches; Mammoth/MRLS; stealth tanks; paradrops; Kane; ion-beacon Temple finale | Source selected. Building-wide reactions, vehicle access, beacon completion and large-base performance require data/runtime checks. |
| M11 | Heard exterior battle; floor 1/security/stealth; volt rifle; museum/Net Runner/wet bar/green room; war room; barracks/uprising; laboratory/cryo crypt; Sydney torture/escort; ceiling rappels; Petrova/stealth troops; power core; nuke/elevators; Obelisk; Kane/Seth/Temple; end switch | Source selected. Reused M01 hunter/M04 chamber links, bone attachments, floor conditions, scripted Petrova fight, difficulty pickups and final route unverified. |

## Other scripts, assets and caveats

No Mission12.cpp or Mission13.cpp exists; Mission12.h is a stub. No fabricated
replacement source is needed. Original DSP membership, including designer
tests, DrMobius and MissionDemo, governs shipped selection. MissionS04, PRDemo,
Common, Group, GroupControl, GroupScript, unitcombat, Test_DEL and Test_DLS_M03
remain excluded as the original project did. A claim that designer-test files
are never used in retail is rejected: inspected bindings reach such helpers.

All ten inventory classes remain tracked: level geometry/IDs/pathfind/vis;
presets; models/animations; textures/objective images; cinematic controls;
conversations/voice; sound/twiddler/logical stimuli; music; text/subtitles;
and campaign movies. Retail data stays unchanged and user-supplied. Missing
source SDKs remain boundary work; source does not substitute for retail content.
Dynamic names, level parameters and authored attachments make literal counts
lower bounds. The twelve named music files are discovery evidence; absence of
script music in M04/M09/M10/M11 does not mean those maps have no music.

Installed GXM headers define BC1/BC2/BC3 corresponding to DXT1/3/5, but the
current compressed upload branch admits DXT1/DXT5 only. Hardware capability
does not prove DXT3 uses that path or that any format renders correctly.
Original DDS/TGA resolution and fallback remain separate from that capability.

The damage parameter typo is retained: Killable_by_NotStar differs from
Killable_ByNotStar even under case-insensitive lookup. Exact Aggessiveness,
Archaelogical and Contoller names remain unchanged. stricmp compatibility,
the 512-byte parameter limit and filename case require explicit checks.
ARM floating-point differences cannot be dismissed categorically as harmless
to single-player behavior or saves. Assembly replacement requires per-owner
verification. The 150 Debug_Message calls already have an original WWDEBUG
guard; deleting them is not necessary to disable retail debug output. Existing
diagnostics retain their own bounded policy. Code and retail-data licensing
remain separate; complete reviewed licenses stay in the repository.

## Every checklist and profiling recommendation

| Item | Decision |
|---|---|
| Static Scripts.dsp / mission08 case | Implemented in source; compile/register gate open |
| All used ScriptCommands without behavior changes | Required; 143 names counted, every implementation not yet verified |
| Numeric IDs and original chunked script saves | Required; inspected bindings are partial proof; complete save/load compatibility open |
| Innate/actions/pathfind/hibernation | Original ownership retained; behavior and proposed scheduling changes require evidence |
| Conversations and cinematic parser | Startup restoration and deeper tracing implemented; playback/slot/callback proof open |
| Vita audio and logical stimuli | Existing provider retained; logical stimuli must remain independent of audible playback |
| WW3D/Vita rendering, fog/stealth/beams | Existing boundary retained; feature-specific visual correctness open |
| HUD/button/voiced instructions and touch | Eleven English hints restored; spoken PC instructions, touch and input locks open |
| Three boss classes and profiling | Source owners located; all boss fights unverified |
| Movie conversion and unchanged campaign sequence | Keep existing unchanged-BINK provider; campaign data confirmed; A/V remains open |
| Difficulty playthroughs | All difficulties remain required, including spawners and M11 pickup scaling; not run |

M05 town square, M10 open base, M06 collapse and M08 canyon remain useful
profiling priorities. Caps on flyovers/particles, simpler nuke visuals, trimmed
vis, new aim assistance and pathfinding scheduling are deferred until matching
correctness, physical visual and measured performance evidence exists. They
cannot authorize dropping the very segments this review is intended to retain.

## Concrete loader correction and validation

The review exposed an original-port boundary defect: POSIX completion stores
were release operations, but Is_Running polled the marker non-atomically.
ThreadID was cleared after publishing completion, allowing teardown or reuse
before the worker's final object access. Worker-side running=true could also
undo Stop after Execute returned but before the worker started.

Two new zero-fuzz patches correct acquire polling, publish completion last,
initialize ThreadID, establish the run request in the parent, clear both flags
on creation failure, and add atomic cooperative cancellation for the selected
texture worker. Original ThreadClass, Combat loading and texture queues remain
owners. Class fields and disk/wire formats are unchanged. Execute/Stop lifecycle
operations must remain serialized by their owner; this is not a new concurrent
start/stop API. Finite non-cooperative loader work still runs to completion.
Creation failure still needs original caller-level handling; this patch does
not turn an idle marker into proof that a level loaded successfully.

Follow-up loader failure classification: the registered Vita load boundary calls
the original loader routine synchronously; thread-creation failure is therefore
not the active native path. Original Load_Game and Load_Level return void. Their
file Open results and nested SaveLoadSystem Load results are ignored. RawFile
Open can return false on an invalid handle despite older success-only comments.
SaveLoadSystem's false argument disables automatic post-load callbacks; it does
not establish optional parsing or best-effort success. Its bool aggregates
recognized subsystem Load results and does not certify required chunks exist.

A fresh read-only check confirms Tutorial/M13/M01 dynamic members each contain
one retail level-info and one level-data chunk, and their authored static LSD
target exists in the same archive. Archive/member/source hashes remain in private
`build/level-load-required-members-20261003.json`. This rules out a missing static
member in that inspected scope, not native file-open, parsing, subsystem load or
mission success. Optional definition lookups must be distinguished from required
dynamic/static level files before adding failure gates. Failure propagation is
now implemented in source for the confirmed outcomes below, uncompiled.

The299th registered staging patch adds native-only required dynamic/static file
open and subsystem-load outcome propagation. Load_Level explicitly marks its
static input required; the helper's existing definition calls default to optional.
The dynamic loader also records missing level-info or missing server level-data
chunks, matching original Save_Game's output and the inspected retail members.
Failed opens close/return the file before returning. No serialized fields,
factory ownership, mission scripts or valid-file parsing order were replaced.

A fixed uint32 atomic latch retains the first failure without heap allocation,
file names or coverage opt-in. Startup resets it before the original level load.
After original pointer remapping and post-load reference relinking, a recorded
failure clears the level-loading flag and exits through initialized-component
teardown before Post_Load_Level, world finalization or player creation. The
existing runtime error result carries this failure; its generic render_error
field does not mean a renderer defect. The log's numeric load code distinguishes
the actual cause. Reference relinking remains necessary before partial-world
destruction; skipping all post-load callbacks was not adopted.

Thirty focused Python/source checks pass, including zero-fuzz/no-offset
patch replay, required/optional call separation, file-return branches and native
reference-closure/finalization ordering. Stage/build entrypoints were checked for
shell syntax only. A C++ latch counterexample test is prepared but uncompiled and
unrun. The staging receipt remains unchanged under the hold;299 is the registered
patch count, not evidence of a newly staged or built candidate.

No recorded failure is not a success certificate. Malformed required members
with superficially present chunks, unknown/missing subsystem data, truncated
parsing and post-load callback failures remain incompletely classified. Actual
required-failure cleanup, valid Tutorial/M13/M01 loading, optional-definition
absence and checkpoint restoration need matching native runtime evidence.
No build, launch, deployment or retail mutation occurred; native gates remain0/10.

The compiler target reports arm-vita-eabi; inspected libpthread attributes
report ARMv7-A/Thumb-2 and VFP-register arguments. Native remains little-endian
ARMv7-A/Cortex-A9 ILP32; host probes remain LP64 and separate evidence. Read-only
attribute inspection is not a new compiled artifact or physical acceptance.

The C++ original-ThreadClass probe covers gated late startup, cancellation,
ordinary payload visibility, terminal state, serialized reuse and create
failure. It is prepared but uncompiled/unrun. The 13 new Python/source checks
and broader 170-check focused suite pass. Source replays are isolated temporary
copies; canonical staging and upstream remain unchanged. The patch inventory
is 293. No C++ build, package, game launch, device action or retail edit occurred.
Native mission/runtime gates remain 0/10 under the existing build/launch hold.

```sh
python3 -m tools.audit_mission_research \
  --output build/dev208-research-review-20261003/source-review.json
python3 -m unittest tools.test_mission_research tools.test_thread_publication_contract
```

The next work is to reconcile the two count differences, remaining conditional
event/slot lifetimes and global voice references. Full authored-data and native
mission verification remains required; reviewing all sections must never be
reported as implementing or proving all of their content.
