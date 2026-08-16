# A3.1 interactive execution-equivalence gate

Status: required before A3.1.3 packaging. The old host-only `HUDClass::Enable(false)` operation was removed. `a31_interactive_runtime` and the Vita runtime now call the shared A3.1 HUD policy plus shared simulation and render functions; adapters may provide only clock, controller sampling, logging, and presentation.

| Stage | Host action / state transition | Vita action / state transition | Same decision, argument, and coverage |
|---|---|---|---|
| Application audio | Construct `WWAudioClass(true)` before retained M00 validation; destroy after interactive teardown | Application owns the same singleton before retained M00 validation | Yes; A3.1 audio/world two-cycle regression |
| Filesystem factories | Rooted retail factory plus Always2, DBS, Always, M00 MIX factories | Same names and factory order rooted at `ux0:data/renegade/retail` | Yes; A2.1/A3.0 checks |
| WWMath | `WWMath::Init()` before engine objects | Same | Yes |
| Asset manager | `new WW3DAssetManager`, load-on-demand and fog-on-load true | Same | Yes |
| WW3D | `WW3D::Init(NULL,NULL,true)` | Same | Yes; Vita adapter owns actual presentation |
| WWPhys/WWSaveLoad | Init in that order before Combat | Same | Yes |
| Input | `Input::Init(true)` | Same, then Vita controller adapter supplies state | Same game input decision; platform sampling differs |
| Single-player data | `cServerFps`, `cSinglePlayerData`, nickname, `cGameDataSinglePlayer`, Combat mode, M00 map, mission type | Same | Yes |
| Network one-time/server/client | Original `cNetwork::Onetime_Init`, server then client | Same | Yes; client pointer and establishment asserted |
| Scene | `CombatManager::Scene_Init()` after network creation | Same | Yes |
| Font3D capability | Assert original `FONT12x16.TGA` and `FONT6x8.TGA` requests return null at the Vita renderer boundary | Same boundary compiled into target | Yes; capability is explicitly unavailable, not a missing-file inference |
| Combat initialization | `CombatManager::Init(A31_Interactive_Render_HUD_Available())`, currently false | Same shared function and false result | Yes; adapters cannot choose this argument |
| Transport handshake | Up to 120 original `cNetwork::Update` calls until established | Same | Yes |
| Pre-load/load | `CombatManager::Pre_Load_Level(false)`, level-loading flag, `Load_Level_Threaded("M00_Tutorial.mix",false)` | Same | Yes |
| Post-load | Original `SaveLoadSystemClass::Post_Load_Processing`, clear level-loading flag, `CombatManager::Post_Load_Level` | Same | Yes; no host-only HUD correction remains |
| HUD post-load state | Record serialized enabled, resources available, and effective displayability | Same physical breadcrumb | Yes; serialized enabled may be true while resources are false |
| Player/cGod | `cGod::Create_Player`, then `cGod::Think`; assert player manager and original Commando | Same | Yes |
| First input/control | Shared `TimeManager::Update`, `Input::Update`, `CombatManager::Generate_Control` | Same | Yes; Vita only supplies controller state |
| First network/Combat update | Shared `cNetwork::Update`, `CombatManager::Think` | Same | Yes; host runs 120 complete frames |
| Render | Shared `CombatManager::Render` inside `WW3D::Begin_Render/End_Render` | Same | Yes; host executes renderer boundary but cannot prove Vita GPU pixels |
| Frame count | 120 complete simulation/render frames per cycle | Physical log emits a 120-frame checkpoint | Same required sequence; physical duration remains hardware gate |
| Exit | START-equivalent after 120 frames | Physical START sample ends loop | Same post-loop teardown decision |
| Combat teardown | `CombatManager::Shutdown` | Same | Yes |
| Session teardown | `cGod::Reset`, client/server/onetime network cleanup, player cleanup, game data deletion | Same | Yes; required for cycle two |
| Input/engine teardown | Input, asset manager, WWMath, WWSaveLoad, WW3D, WWPhys shutdown | Same | Yes |
| Repeat lifetime | Run entire scenario twice in one process | Host-only stress amplification | Intentional difference; it proves no stale singleton/state from cycle one |

Both targets define `RENEGADE_VITA_PORT`, `RENEGADE_VITA_A31`, `RENEGADE_SHORT_WCHAR_ABI`, and `RENEGADE_A30_FULL_WWPHYS`. The host additionally defines `RENEGADE_HOST_ABI_TEST` only for pointer-token instrumentation; it does not select a different gameplay/HUD path.

## HUD resource invariant

`_HUDEnabled` is serialized/user state. `_HUDRenderResourcesAvailable` means the complete original render-dependent HUD closure was constructed. `HUDClass::Think`, `Render`, `Reset`, and `Is_HUD_Displayed` require the latter before reaching Sniper HUD, Font3D-backed widgets, `InfoRenderer`, or any other HUD owner. Shutdown always frees base render images and only tears down the full closure when it was initialized.

Therefore M00 post-load may restore `enabled=true` in temporary no-HUD mode without making original `CombatManager::Think` or `CombatManager::Render` reach an uninitialized resource. The regression deliberately reproduces that state: Font3D unavailable, `CombatManager::Init(false)`, post-load enabled state, original player/Commando, 120 full input/network/Combat/render frames, teardown, then a second in-process cycle under ASan/UBSan.
