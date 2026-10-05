# Initial mission/save failure recovery source wiring

Status: local/uncommitted/unvalidated. Source inspection only; no staging,
patch execution, tests, builds, emulator/device or commit/push actions.
This does not establish safe handling of arbitrary corrupt saves or hardware
recovery. The complete native-game goal remains active and unachieved.

## Missing ownership found

Native `port/platform/vita/a31_vita_runtime.cpp` marked level_unload_pending
only after successful post-load finalization. Original CombatManager::Pre_Load_Level
already initialized GameObjManager, cover/bullets, background scene, sound
environment, weather and weapon view. A failure before finalization therefore
left the fallback unload flag unset. Original active/suspended Combat mode
cleanup already invokes Core_Shutdown, which performs Unload_Level and releases
the level; the flag omission does not prove a leak on that normal route.
The corrected flag protects direct fallback cleanup if mode teardown did not
consume the pending level. CombatManager::Shutdown alone does not call
GameObjManager::Shutdown or release level background/sound environment.

Missing selected archives also failed before session_initialized. At that point
the original SP/Practice initializer and server-FPS singleton could already be
owned, but their cleanup was conditioned on an established network session.
Original frontend difficulty callbacks can initialize SP before a source is
rejected. These are source defects, not newly observed hardware failures.

## Local correction

Pre-load now records pending level unload as soon as original pre-load returns.
Cleanup retains original cGod exit, CombatManager::Unload_Level and then
LevelManager::Release_Level ordering before Combat shutdown. The direct release
matches the original Core_Shutdown owner: object/conversation/audio/scene and
asset cleanup remains in original engine code. No custom object destruction or
replacement save format was introduced.

Selected `port/patches/commando-a36-load-failure-unwind.patch` adds original
CombatGameModeClass::Vita_Abort_Level_Load at the existing platform load seam.
When no loader remains active and queued post-load references are resolved, it
clears the original loading flag and restores server packet processing. Initial
known load failure clears NetworkObjectMgr loading state and follows the existing
texture continuation/post-load processing before abort. The demo source-rejection
branch also clears the gates it acquired, retaining its separate fatal policy.

Queue_Local_Load_Failure_Recovery records a failed local load, requests cleanup
and original-menu return. It is called for these known boundaries:

| Boundary | Recorded failure | World state |
|---|---|---|
| Original frontend latched a source but rejected its selection | SOURCE_REJECTED (10) | No loaded world; frontend may own SP initialization |
| Selected local mission/Practice MIX factory is invalid | ARCHIVE_UNAVAILABLE (9) | SP/game data and server-FPS may exist, before level pre-load |
| Original loader reports required dynamic/static failure | Existing codes 1–8 | Pre-load and partial objects may exist; skip gameplay finalization |
| Existing saved-player identity/reuse/relink checks reject restore | PLAYER_BINDING_FAILED (11) | Loaded world is retained for original cleanup; no replacement player admitted |

Codes 9/10/11 are appended process-local diagnostic values. Existing loader values
remain unchanged; none is written to original game saves or network packets.
The local between-frame restart preparation now also retains codes 10/9 for
unsupported next sources or invalid changed-map archives before Core_Restart.
See PRACTICE_COMPLETION_WIRING.md and MANUAL_SAVE_FAILURE_WIRING.md.
Missing startup prerequisites, renderer/font/audio/network setup failure,
unreported parser defects and remote-map failures are not converted into
accepted local recovery.

Frontend SP ownership is retained even on rejection. Native network ownership
is recorded immediately after Onetime_Init, so null/partial connection cleanup
uses original Cleanup_Client/Server. Their source guards use null connection
checks. GameInitMgr shutdown also runs when SP initialized before networking.
The runtime records ownership of its own server-FPS instance independently.

## Recovery evidence gate

The existing a30 launcher still excludes a retained load failure from PASS.
It requires clean cleanup, menu-return intent, no full frontend exit and no
renderer error before re-entering the original menu with no failed load request.
Its recovery count survives into the final lifecycle record. There is no
automatic retry of the failed mission or save.

The native cleanup gate checks renderer/assets/audio release, null connections,
empty player/game-object lists, null Combat scene/star/camera and removed Combat
mode. It now additionally requires null PTheGameData, inactive SP transport and
no server-FPS singleton. Held-input priming remains in the existing menu reentry.
These are source predicates, not executed proof of cleanup.

## Evidence and pending acceptance

The original Core_Shutdown/LevelManager cleanup assumes an existing scene.
The native route previously activated Combat before connection creation and
Scene_Init, so failed connection setup could enter mode shutdown without that
scene. Native activation now follows original Scene_Init and CombatManager::Init,
before the first handshake Update. Failed connection creation therefore leaves
the original mode inactive. Practice/client suspension still follows activation
and precedes simulation. This source ordering needs runtime evidence; network
setup failure remains fatal rather than automatically reclassified as recovery.
Known required-level failures occur after scene/Combat initialization;
missing-archive/source failures occur before activation.

Inspected original owners: `staging/combat/combat.cpp` Pre_Load_Level,
Unload_Level and Shutdown; `staging/commando/level.cpp` Release_Level;
`staging/commando/combatgmode.cpp` Vita_Begin/Finalize_Level_Load and
Core_Shutdown; `staging/commando/gameinitmgr.cpp` Initialize_SP/Skirmish and
Shutdown; `staging/commando/cnetwork.{cpp,h}` cleanup/null-peer guards;
`staging/wwnet/singlepl.cpp` transport cleanup; serverfps.{cpp,h} singleton
ownership. Staging was read only and has not received the new patches.

Modified platform sources: a31_vita_runtime.cpp and a35_level_load_status.h.
The unwind patch is selected after the replay patch and before the manual-save
patch in tools/stage_sources.sh. The existing
`port/platform/vita/a30_main.cpp` failed-load menu recovery consumes the result.
All touched fields are process-local; target remains ARMv7-A, little-endian,
ILP32 with the existing ABI gates. No dependency or artifact was rebuilt.

Pending acceptance includes rejected/missing saves, recognized damaged dynamic
and static chunks, missing selected archives, first-load and between-round
failures, another successful selection after recovery, held controls, repeated
recovery/exit cycles and memory/resource growth. Required loader failure must
not run post-load gameplay finalization, create a star or report PASS. Physical
Vita and PSTV evidence must be candidate-matched and kept separate from future
host/ARM/emulator checks. User-visible error presentation remains unverified.
