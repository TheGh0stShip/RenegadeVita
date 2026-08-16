# A3.0 Commando continuation after the M00 static-world load

Status: source and retail dependency trace complete; implementation not performed by this report

Canonical upstream: EA/Westwood `CnC_Renegade` at
`3e00c3a1b97381bb28be89a35b856375e0629a08`

Date: 2026-08-07

## Conclusion

The next coherent original subsystem is **not** another static-world renderer
feature and is **not** `Commando/mainloop.cpp` in isolation. It is the genuine
dynamic-level restore path for `m00_tutorial.ldd`, with original Combat and
WWPhys subsystem registration, object factories, pointer remapping, and
post-load callbacks. That load creates the game objects, dynamic physical
objects, `CombatManager` state, Star reference, and camera state which the
original update loop expects.

The minimum architecture-preserving sequence is:

```text
CombatManager::Scene_Init                         owns the one PhysicsScene
CombatManager::Init                              creates the one CCamera
CombatManager::Pre_Load_Level                    resets per-level managers
SaveGameManager::Pre_Load_Game("M00_Tutorial.mix")
SaveGameManager::Load_Game("m00_tutorial.ldd")
  -> level info -> existing original M00_Tutorial.lsd static load
  -> LEVEL_DATA -> SaveLoadSystemClass::Load(..., false)
       -> CombatSaveLoadClass
       -> ConversationMgrClass
       -> PhysDynamicSaveSystemClass
       -> EncyclopediaMgrClass
       -> DynamicAudioSaveLoadClass
       -> MapMgrClass
SaveLoadSystemClass::Post_Load_Processing
CombatManager::Post_Load_Level
TimeManager::Update
Input::Update
CombatManager::Generate_Control
local/offline network service at the existing network boundary
CombatManager::Think
CombatManager::Render -> existing original WW3D/Vita renderer
```

The present static-world harness-owned `PhysicsSceneClass` must be retired for
this route. `CombatManager::Scene_Init` creates the canonical scene used by
`COMBAT_SCENE`; creating a second scene would split ownership and invalidate
the pointer relationships restored from the `.LSD` and `.LDD`
(`Combat/combat.cpp:152,264-293`).

## Exact unchanged M00 dynamic payload

The following inventory was derived read-only from the 148,616-byte retail
`m00_tutorial.ldd` obtained through the already-proven original
`FileFactoryListClass -> MixFileFactoryClass -> FileClass` route. The audit
only bounded existing chunk headers for dependency selection; it is not, and
must never become, a runtime loader.

Top-level `.LDD` structure:

| Chunk | Meaning | Payload bytes |
|---|---|---:|
| `0x3C51C460` | level info | 29 |
| `0x3C51C461` | level data | 148,571 |

`LEVEL_DATA` contains exactly six direct save/load subsystems:

| Chunk | Original subsystem | Payload bytes | Source registration/ID |
|---|---|---:|---|
| `0x00040000` | `CombatSaveLoadClass` | 102,007 | `Combat/combatsaveload.h:61`, global at `combatsaveload.cpp:61` |
| `0x00040700` | `ConversationMgrClass` | 25,396 | `Combat/conversationmgr.cpp:238-242` |
| `0x00020050` | `PhysDynamicSaveSystemClass` | 20,914 | `WWPhys/wwphysids.h:52-80`, global at `physdynamicsavesystem.cpp:52` |
| `0x00040148` | `EncyclopediaMgrClass` | 40 | `Combat/combatchunkid.h:172-174`, `encyclopediamgr.h:121` |
| `0x00030006` | `DynamicAudioSaveLoadClass` | 25 | `WWAudio/SoundChunkIDs.h:56-66`, global at `AudioSaveLoad.cpp:51-52` |
| `0x00040147` | `MapMgrClass` | 141 | `Combat/combatchunkid.h:172-174`, `mapmgr.h:123` |

This is an important registration gate. `SaveLoadSystemClass::Load` looks up a
registered subsystem for each chunk and silently skips an unknown one before
performing pointer remaps and post-load work
(`wwsaveload/saveload.cpp:73-107`). A superficially successful `.LDD` pass
with missing subsystem globals would therefore be false progress. All six
must be present, or an explicitly documented platform boundary must preserve
the original subsystem's serialized semantics.

### Exact CombatSaveLoad payload

`CombatSaveLoadClass::Load` dispatches these chunks directly to the original
managers (`Combat/combatsaveload.cpp:63-82,155-233`):

| Chunk | Original recipient | Bytes |
|---|---|---:|
| `0x36A82EA6` | `GameObjManager` | 93,897 |
| `0x36A82EA7` | `CombatManager` game mode state | 255 |
| `0x36A82EA9` | `SpawnManager` | 1,673 |
| `0x36A82EAB` | `ScriptManager` | 3,665 |
| `0x36A82EAC` | persistent game-object observers | 1,352 |
| `0x36A82EAD` | `CoverManager` | 0 |
| `0x36A82EAE` | `ObjectiveManager` | 14 |
| `0x36A82EAF` | `RadarManager` | 17 |
| `0x36A82EB1` | game-object observers | 14 |
| `0x36A82EB2` | `BulletManager` | 0 |
| `0x36A82EB3` | `WeaponViewClass` | 14 |
| `0x36A82EB4` | dynamic `BackgroundMgrClass` | 494 |
| `0x36A82EB5` | dynamic `WeatherMgrClass` | 311 |
| `0x36A82EB6` | `HUDClass` | 11 |
| `0x36A82EB7` | `ScreenFadeManager` | 170 |

The obsolete transitions, time, and buildings slots from the enum are absent.
The zero-length cover and bullet chunks do not remove their link dependency:
`combatsaveload.cpp` contains direct calls to every manager.

### Exact GameObj factory closure

The original `GameObjManager::Load` iterates persisted object factory chunks,
finds each registered `PersistFactoryClass`, and calls its `Load`
(`Combat/gameobjmanager.cpp:124-177`). M00 contains 74 objects and exactly six
object factory IDs:

| Factory chunk | Original class | Count | Factory/definition TU |
|---|---|---:|---|
| `0x0004010E` | `SoldierGameObj` | 22 | `Combat/soldier.cpp:119-121,293-295` |
| `0x00040122` | `ScriptZoneGameObj` | 31 | `Combat/scriptzone.cpp:83-85,199` |
| `0x00040106` | `PowerUpGameObj` | 8 | `Combat/powerup.cpp:80-82,480` |
| `0x0004010A` | `SimpleGameObj` | 5 | `Combat/simplegameobj.cpp:55-57,166` |
| `0x00040124` | `TransitionGameObj` | 4 | `Combat/transitiongameobj.cpp:53-55,162` |
| `0x00040133` | `BuildingGameObj` | 4 | `Combat/building.cpp:105-107,323` |
|  | **Total** | **74** | |

Each listed leaf TU also registers its corresponding original Definition
factory. Do not substitute a hand-built definition table.

The common inheritance/load closure is:

```text
BaseGameObj -> ScriptableGameObj -> DamageableGameObj -> PhysicalGameObj
                                                -> ArmedGameObj -> SmartGameObj
                                                                 -> SoldierGameObj
PhysicalGameObj -> SimpleGameObj -> PowerUpGameObj
ScriptableGameObj -> ScriptZoneGameObj
BaseGameObj -> TransitionGameObj
DamageableGameObj + CombatPhysObserverClass -> BuildingGameObj
```

`SimplePersistFactoryClass<T>::Load` constructs the real object, calls its
original `Load`, and registers the old-to-new pointer identity
(`wwsaveload/persistfactory.h:109-126`). `BaseGameObj` construction
immediately joins `GameObjManager`; its load resolves the serialized
definition ID and asserts that the original `DefinitionMgrClass` result is
non-null (`Combat/basegameobj.cpp:137-147,200-270`). Thus all 74 objects must
finish with valid original definition pointers.

`BaseGameObj` also derives from `NetworkObjectClass`. The original WWNet
network-object ID, dirty-bit, factory, manager, and list core is required even
when sockets/GameSpy/WOL are absent. External networking is optional; the
engine's object identity machinery is not.

### Exact dynamic PhysicsScene closure

`PhysDynamicSaveSystemClass::Load` restores the scene, physics constants, and
PathMgr and registers its original post-load callback
(`WWPhys/physdynamicsavesystem.cpp:85-112`). The M00 payload is:

| Chunk | Meaning | Bytes |
|---|---|---:|
| `0x00007001` | `PhysicsSceneClass::Load_Level_Dynamic_Data` | 20,832 |
| `0x00007002` | `PhysicsConstants::Load` | 58 |
| `0x00007003` | `PathMgrClass::Load` | 0 |

The scene data contains 35 dynamic physical objects:

| Factory chunk | Original class | Count | Factory TU |
|---|---|---:|---|
| `0x00020100` | `DecorationPhysClass` | 5 | `WWPhys/decophys.cpp` |
| `0x00020101` | `HumanPhysClass` | 22 | `WWPhys/humanphys.cpp` |
| `0x00020105` | `Phys3Class` | 8 | `WWPhys/phys3.cpp` |
|  | **Total** | **35** | |

Those counts exactly correspond to the five Simple objects, 22 Soldiers, and
eight PowerUps. `PhysicsSceneClass::Load_Dynamic_Objects` uses the original
persist factories, inserts each result into dynamic culling, and calls
`Internal_Add_Dynamic_Object` (`WWPhys/pscene_saveload.cpp:604-637`).
`PhysicalGameObj::Load` separately restores/remaps its `PhysObj` and
multiple-inheritance observer pointer; its post-load callback reconnects that
observer (`Combat/physicalgameobj.cpp:483-573`). This is why GameObj and
dynamic-physics loading must share one `SaveLoadSystemClass` pointer-remap
cycle and one scene.

The current A3 frontier already compiles the complete original 93-TU WWPhys
runtime, including all three dynamic factories and
`physdynamicsavesystem.cpp`. This part should be activated through the genuine
`.LDD` subsystem load, not copied or replaced.

## Original load and post-load order

`SaveGameManager::Pre_Load_Game` converts `M00_Tutorial.mix` to
`m00_tutorial.ldd` and `M00_Tutorial.lsd` and configures the original provider
search (`Combat/savegame.cpp:150-235`). `SaveGameManager::Load_Game` then:

1. opens the `.LDD` through `_TheFileFactory` and `ChunkLoadClass`;
2. consumes level information;
3. tries the optional level DDB and loads the existing `.LSD` static data;
4. on the server, feeds `LEVEL_DATA` to
   `SaveLoadSystemClass::Load(cload, false)`
   (`Combat/savegame.cpp:238-305,493-497`).

For the direct local mission route, the server role must be established
through the original Combat/network state before `Load_Game`; otherwise line
288 skips all dynamic data.

The post-load order is architectural, not incidental. Original
`CombatGameModeClass::Load_Level` calls
`SaveLoadSystemClass::Post_Load_Processing` before
`CombatManager::Post_Load_Level`
(`Commando/combatgmode.cpp:704-717`). This completes references among the 74
GameObjs, 35 dynamic Phys objects, static world, Combat Star, camera host,
scripts/observers, and conversation state. Do not call manager post-loads
manually or reorder them.

`ReferencerClass::Load` requests pointer remapping and relinks its target in
post-load (`Combat/reflist.cpp:53-90`). `CombatManager::Load` restores the
serialized `TheStar` reference and the already-created `CCameraClass`
(`Combat/combat.cpp:852-912`). These are the natural bridge from dynamic load
to an original playable camera, not values to synthesize in Vita main.

## Combat scene, Star, and camera ownership

The source-defined initialization order in `Commando/init.cpp:945-971` is
PhysicsScene first, platform/system settings as available, network handler,
then `CombatManager::Init`.

`CombatManager::Init(render_available)` initializes conversation, scripts,
bones, armor/warhead, camera profiles, surface effects, objectives, sound,
creates the sole `CCameraClass`, and only gates Dazzle/HUD render resources on
`render_available` (`Combat/combat.cpp:157-203`). Its load thread then performs
the original ordered definition reload, animated-sound initialization,
`Pre_Load_Game`, optional asset preload, and `Load_Game`
(`Combat/combat.cpp:355-445`). Running those same ordered calls synchronously
is a valid temporary Win32-thread boundary adaptation; replacing them with a
custom loader is not.

`CombatManager::Pre_Load_Level` resets the original per-level managers and
creates the background scene/sound environment before loading
(`Combat/combat.cpp:301-350`). `Post_Load_Level` flushes input, creates static
network wrappers, enables sound if a Star exists, and builds coordination
zones (`Combat/combat.cpp:464-518`).

`CombatManager::Set_The_Star` stores the original `GameObjReference`, aligns
camera heading, and updates original audio/HUD state
(`Combat/combat.cpp:996-1019`). `Update_Star` selects the original combat mode
and `Update_Combat_Mode` anchors the camera to the Soldier/vehicle
(`Combat/combat.cpp:1024-1055,1235-1283`). `CCameraClass::Set_Anchor_Position`
makes the camera valid, while `CCameraClass::Load` restores saved camera and
host-model references (`Combat/ccamera.cpp:463-542,673-682`).

## First original update and render

The first semantic gate should execute one exact original frame sequence; it
must then become the continuous original GameMode/main-loop path rather than a
new Vita game loop.

The canonical outer ordering is in `Commando/mainloop.cpp:83-193`:

1. `TimeManager::Update()`;
2. `Input::Update()`;
3. `PathMgrClass::Resolve_Paths` around the current Combat camera;
4. `GameModeManager::Think()` and game-init service;
5. network/object/optional services;
6. `GameModeManager::Render()`.

`GameModeManager::Think` walks each active original mode and then reaches the
Bink boundary (`Commando/gamemode.cpp:169-189`). Active Combat ordering is
explicit (`Commando/combatgmode.cpp:1231-1402`):

```text
Combat_Keyboard
CombatManager::Generate_Control
cNetwork::Update                 deliberately between input and Think
CombatManager::Think
optional multiplayer/UI/campaign services
```

`CombatManager::Think` performs SyncTime, gameplay permission/input, bullets,
objectives/conversations, all GameObj `Think`, PhysicsScene update, Star,
camera, all GameObj `Post_Think`, targeting, spawn/background/weather, and HUD
(`Combat/combat.cpp:664-750`). `GameObjManager`'s exact loops are in
`Combat/gameobjmanager.cpp:251-343`. Rendering remains the original background
and `COMBAT_SCENE` `WW3D::Render` traversal
(`Combat/combat.cpp:755-796`); no special dynamic-object renderer is needed.

One mandatory precondition is easy to miss:
`CombatManager::Think` unconditionally dereferences `NetworkHandler` for
`Is_Gameplay_Permitted` at `Combat/combat.cpp:670`. The project must either:

- integrate original `cNetwork::Onetime_Init` and
  `GameCombatNetworkHandlerClass` (`Commando/cnetwork.cpp:558-570`,
  `nethandler.cpp:44-152`), or
- temporarily install a valid local/offline implementation through the
  existing `CombatNetworkHandlerClass` boundary (`Combat/combat.h:101-108,179`).

A null pointer is invalid, and deleting the
Generate-Control -> network-service -> Think ordering is invalid. The full
original single-player path ultimately starts both its local server and client
(`Commando/gameinitmgr.cpp:651-690,540-610`); socket transport/GameSpy/WOL may
be adapted or disabled below that boundary while the network-object core and
local gameplay semantics remain original.

## Player and control path

The loaded Star should emerge from original serialized/remapped state.
Additionally, original network creation assigns the local Star when a
`SmartGameObj` control owner equals `CombatManager::Get_My_Id`, installs the
FollowInput action, and calls `CombatManager::Set_The_Star`
(`Combat/smartgameobj.cpp:978-996`). `SoldierGameObj::Set_Control_Owner`
maintains the original Star list (`Combat/soldier.cpp:570-578`).

The input-to-player chain is already defined:

```text
Input action map
 -> FollowInputActionCodeClass::Act
 -> ControlClass values
 -> SoldierGameObj::Generate_Control / SmartGameObj::Generate_Control
 -> SoldierGameObj::Apply_Control
 -> original PhysController/HumanPhys
```

`FollowInputActionCodeClass::Act` maps original input functions to movement,
jump, action, weapon, and fire control fields
(`Combat/action.cpp:237-308`). `SmartGameObj::Generate_Control` runs original
server AI or locally owned actions (`Combat/smartgameobj.cpp:518-548`), and
Soldier applies those controls only when gameplay is permitted
(`Combat/soldier.cpp:1595-1618`). `CCameraClass::Update` calls its original
input handler and physics sweep/transform path
(`Combat/ccamera.cpp:714 onward,1319-1543`).

## Smallest coherent original source cluster

This is a **source-backed seed/closure**, not a promise of the final TU count.
Old C++ translation units contain direct references beyond the exact M00 data,
so the linker must expose the remaining genuine closure. Do not resolve those
symbols by replacing engine behavior.

The current 248-original-source M00 static-world runtime already provides the
complete WWPhys runtime, WWSaveLoad/DefinitionMgr, `savegame.cpp`,
`reflist.cpp`, the static Combat factory slice, and required WWMath/WW3D
support. Add the following coherent dynamic/Combat seed.

### 1. Dynamic load and ownership kernel

- `Combat/combat.cpp`
- `Combat/combatsaveload.cpp`
- `Combat/gameobjmanager.cpp`
- existing `Combat/savegame.cpp`

### 2. Exact M00 GameObj hierarchy and leaf factories

- `Combat/basegameobj.cpp`
- `Combat/scriptablegameobj.cpp`
- `Combat/damageablegameobj.cpp`
- `Combat/physicalgameobj.cpp`
- `Combat/armedgameobj.cpp`
- `Combat/smartgameobj.cpp`
- `Combat/soldier.cpp`
- `Combat/scriptzone.cpp`
- `Combat/powerup.cpp`
- `Combat/simplegameobj.cpp`
- `Combat/transitiongameobj.cpp`
- `Combat/building.cpp`

### 3. Serialized embedded game-object behavior

- `Combat/control.cpp`
- `Combat/action.cpp` (registers the original ActionCode factories in one TU)
- `Combat/pathaction.cpp`
- `Combat/animcontrol.cpp`
- `Combat/humanstate.cpp`
- `Combat/weapons.cpp`
- `Combat/weaponbag.cpp`
- `Combat/weaponmanager.cpp`
- `Combat/explosion.cpp`
- damage/defense support reached from `DamageableGameObj`
- `Combat/playerdata.cpp` and `Combat/clientcontrol.cpp` as local player/network
  ownership becomes active

`SmartGameObj::Load` restores `Control`, `PhysController`, `Action`, PlayerData
and stealth state and registers pointer/post-load work
(`Combat/smartgameobj.cpp:264-421`). Its constructor also assumes
`WWAudioClass::Create_Logical_Listener` returns a valid object and immediately
registers a callback (`smartgameobj.cpp:166-183`); the silent audio boundary
must therefore preserve a valid logical listener, not return null.

### 4. Every direct CombatSaveLoad recipient

- `Combat/spawn.cpp`
- `Combat/scripts.cpp`
- `Combat/persistentgameobjobserver.cpp`
- `Combat/cover.cpp`
- `Combat/objectives.cpp`
- `Combat/radar.cpp`
- `Combat/gameobjobserver.cpp`
- `Combat/bullet.cpp`
- `Combat/weaponview.cpp`
- `Combat/backgroundmgr.cpp`
- `Combat/WeatherMgr.cpp`
- `Combat/hud.cpp`
- `Combat/screenfademanager.cpp`

### 5. The other five exact top-level `.LDD` subsystems

- conversations: `Combat/conversationmgr.cpp`, `conversation.cpp`,
  `conversationremark.cpp`, `activeconversation.cpp`, `orator.cpp`, and
  `oratortypes.cpp`
- `Combat/encyclopediamgr.cpp`
- `Combat/mapmgr.cpp`
- existing `WWPhys/physdynamicsavesystem.cpp` and complete WWPhys closure
- `WWAudio/AudioSaveLoad.cpp` plus the original logical-listener/sound-scene
  core needed to load dynamic state under a silent platform backend

### 6. Original object/network identity core

- `WWNet/networkobject.cpp`
- `WWNet/networkobjectmgr.cpp`
- `WWNet/networkobjectfactory.cpp`
- `WWNet/networkobjectfactorymgr.cpp`

This is distinct from socket, GameSpy, and WOL integration.

### 7. Camera, timing, and input bridge

- `Combat/ccamera.cpp`
- `Combat/timemgr.cpp`
- `Combat/input.cpp`
- a Vita implementation beneath the existing `DirectInput` class contract
  rather than the Windows `directinput.cpp`

### 8. Replace static-world-only scalar/global closures with their owners

The current static-world targets deliberately provide a few exact or
fail-fast definitions in
`port/platform/vita/a30_static_world_boundary.cpp` and
`tools/host_a30_definitions/world_load_optional_boundary.cpp`. They were valid
only while gameplay objects and updates were unreachable. They must remain
scoped to that regression target and must not enter the dynamic/Commando
target. The original owning TUs are mandatory:

| Existing temporary symbol | Original owner | Source evidence/action |
|---|---|---|
| `CombatManager::IAmServer` | `Combat/combat.cpp` | defined with all related client/server/MyId state at `combat.cpp:108-123`; link this TU and exclude the temporary definition |
| `CombatManager::TheStar` | `Combat/combat.cpp` | original `GameObjReference` definition at `combat.cpp:112`, serialized by `CombatManager::Load`; never manufacture a parallel Star pointer |
| `GameObjManager::StarGameObjList` | `Combat/gameobjmanager.cpp` | original list storage at `gameobjmanager.cpp:61-65`, maintained by `SoldierGameObj::Set_Control_Owner` |
| `SmartGameObj::Is_Human_Controlled` | `Combat/smartgameobj.cpp` | original predicate at `smartgameobj.cpp:567-572`; link the full gameplay TU already required by the object hierarchy |
| `VehicleGameObj::Get_Driver` | `Combat/vehicle.cpp` | original seat lookup at `vehicle.cpp:2363-2369`; required by `SmartGameObj::Is_Controlled_By_Me` even though this particular M00 payload has no persisted Vehicle factory |
| `DiagLogClass::Log_Timed` | `Combat/diaglog.cpp` | original timed FileClass logger at `diaglog.cpp:91-106`; port `SYSTEMTIME/GetSystemTime` and writable-root behavior beneath it rather than retaining the scalar logger substitute |

Consequently `Combat/vehicle.cpp` and `Combat/diaglog.cpp` are part of the
minimum gameplay-core link closure. `vehicle.cpp` may expose more genuine
vehicle/gameplay dependencies at link time; those are source-authentic closure,
not a reason to keep the isolated `Get_Driver` copy. `diaglog.cpp` has a clear
Win32 platform seam (`SYSTEMTIME`/`GetSystemTime` at lines 42,69-72,79-82), but
its formatting, `TimeManager` timestamp, `FileClass` ownership, and write path
remain original.

After the load kernel passes its semantic gates, add the original continuous
runtime layer in the same A3.0 progression:

- `Commando/gamemode.cpp`
- `Commando/combatgmode.cpp`
- `Commando/mainloop.cpp`
- `Commando/gameinitmgr.cpp`, single-player GameData, and the local network
  service closure demanded by those calls

Do not begin by blindly linking `combatgmode.cpp`: it directly references
loading screen, UI, campaign, multiplayer, and network services. First make
the exact dynamic load kernel semantically correct, then advance into
GameMode/mainloop while keeping their original order and isolating only the
legitimate boundaries below.

## Legitimate optional and platform boundaries

| Boundary | Allowed first-world treatment | Must remain original above it |
|---|---|---|
| DirectInput/Win32 devices | Implement `DirectInput` state arrays/read/flush/acquire over SceCtrl | `Input`, action mappings, `ControlClass`, Soldier and camera behavior |
| Win32 timing | Replace only `TimeManager::SystemTicks`/`TIMEGETTIME` with monotonic Vita milliseconds | frame clamping/scaling, timers, WW3D sync and update order (`timemgr.cpp:142-318`) |
| ThreadClass/Win32 loader thread | pthread/Vita thread, or temporary synchronous execution of the same ordered original load calls | definition reload, pre-load, asset/load, post-load sequence |
| WWAudio/Miles | silent Vita backend is acceptable; dynamic audio data must still parse; return valid logical listener/sound-scene objects | WWAudio ownership, logical listeners, callbacks, save/load architecture |
| scripts DLL loader | replace `LoadLibrary/GetProcAddress` boundary later; missing scripts are explicitly nonfatal for the first visual world | `ScriptManager::Load` and serialized observer/pointer semantics |
| sockets/GameSpy/WOL | disable external services for local mission | WWNet object identity and dirty/list machinery, valid Combat network handler, local control ordering |
| Bink | no-op/skip only at Bink movie boundary | `GameModeManager` ordering |
| GDI/fonts/menu/loading screen | limited/no presentation at platform/UI edge | Combat/game/scene ownership; do not replace UI framework |
| registry/system settings | Vita config/default provider | original setting consumers and initialization ordering |
| Umbra | existing conservative `UMBRASUPPORT=0` fallback | PhysicsScene/WW3D scene traversal |

The original Windows script module boundary is visible at
`Combat/scripts.cpp:149-258`. Crucially, `ScriptManager::Load` already treats a
missing script as nonfatal while preserving observer pointer registration
(`scripts.cpp:367-459`). This permits a first world frame without inventing a
script runtime, although real campaign progression later requires a native or
in-process implementation at that same boundary.

`DynamicAudioSaveLoadClass::Load` restores listener scale, background music,
and sound-scene state (`WWAudio/AudioSaveLoad.cpp:230-290`). Skipping its
top-level chunk would not be equivalent to a silent backend.

`MapMgrClass::Load` registers post-load work that resolves the original map
texture (`Combat/mapmgr.cpp:191-272`). Texture presentation may be deferred at
the existing texture/backend edge, but the manager and its serialized state
should not be silently discarded. Encyclopedia and conversation data are
ordinary original game logic, not platform dependencies.

### Vita input mapping boundary

`Input::Init` delegates to `DirectInput::Init`, and `Input::Update` delegates
to `DirectInput::Read` before applying original mappings and deadzones
(`Combat/input.cpp:651-668,782-981`). `Combat/directinput.h:57-173` supplies a
stable device-state contract. A Vita backend can map:

- left analog to original joystick axes;
- right analog to original mouse-look deltas;
- face/shoulder/START controls to the existing DIK/mouse/joystick button
  state table.

Do not set camera transforms or Soldier velocity from Vita main.

## Integration gates and required semantic fingerprints

### Gate A: factory and subsystem registration before load

- all six exact `.LDD` subsystem IDs resolve to original subsystem objects;
- all six exact GameObj factory IDs resolve;
- the three exact dynamic Phys factory IDs resolve;
- `CombatManager::Scene_Init` owns the only PhysicsScene;
- original definitions are loaded before GameObj construction;
- local mission server state permits `LEVEL_DATA` to load.

### Gate B: exact original dynamic load

- 74 GameObjs: Soldier 22, ScriptZone 31, PowerUp 8, Simple 5,
  Transition 4, Building 4;
- 35 dynamic Phys objects: Decoration 5, Human 22, Phys3 8;
- all 74 `BaseGameObj` definition pointers are non-null;
- original pointer remap and post-load processing complete without unresolved
  required references;
- all 35 dynamic objects enter the same live PhysicsScene as the existing
  static M00 world;
- existing 495 static objects / 192 lights and their accepted render graph
  remain intact;
- serialized `TheStar` remaps to a loaded Soldier when present;
- the original camera is loaded/anchored and reports valid.

### Gate C: one exact original frame

- `TimeManager::Update` produces a finite nonnegative frame interval;
- `Input::Update` feeds the original function table;
- `GameObjManager::Generate_Control`, `Think`, and `Post_Think` run over the
  original lists;
- a valid local network handler permits gameplay;
- `PhysicsSceneClass::Update` runs once;
- Star/camera update runs in the source-defined order;
- `CombatManager::Render` traverses the populated original scene through the
  existing WW3D/Vita backend;
- teardown follows the original subsystem ownership order and is ASan-clean on
  host.

### Gate D: continuous original runtime

Move that validated frame into active `CombatGameModeClass` and
`GameModeManager`, then the original `_Game_Main_Loop_Loop`. A temporary
platform bootstrap may invoke the same original methods to establish Gate C,
but it must not become a separate custom gameplay loop.

## Non-regression constraints

- Do not change the validated `.LSD` static-world loader or its fingerprints.
- Do not create a custom `.LDD`, GameObj, PhysicsScene, or definition parser.
- Do not create a second PhysicsScene, camera ownership graph, or game loop.
- Do not bypass WWSaveLoad pointer remapping/post-load callbacks.
- Do not null out `CombatNetworkHandlerClass` or WWAudio logical listeners.
- Do not drive Soldier/camera movement directly from SceCtrl.
- Do not carry the static-world target's temporary definitions of IAmServer,
  TheStar, StarGameObjList, Is_Human_Controlled, Get_Driver, or Log_Timed into
  the dynamic target; use `combat.cpp`, `gameobjmanager.cpp`,
  `smartgameobj.cpp`, `vehicle.cpp`, and `diaglog.cpp` respectively.
- Keep original retail files unchanged and outside the VPK.
- Keep the canonical EA checkout pristine and represent source fixes as exact
  zero-fuzz staged patches.

This continuation is the shortest source-authentic route from the accepted
M00 static-world proof to a real populated, updated, camera-owned Commando
world on Vita.
