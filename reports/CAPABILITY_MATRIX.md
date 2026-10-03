# Capability matrix

2026-10-03 text/prompt continuation adds eleven English control hints in the
existing M13/M01 adapter, uncompiled. Direct HUD/objective IDs and image lookup
candidates resolve; computed dialogue discovery retains additional absent
M13 names and cinematic parameter provenance. 93 Python/source checks pass;
rendered guidance, spoken controls and native progression remain unverified.
See [text and prompt coverage](MISSION_TEXT_AND_PROMPT_COVERAGE.md).

2026-10-03 conversation continuation restores the original global CONV10.CDB
startup load in both bootstraps, uncompiled. Metadata links for authored
Tutorial/M13/M01 conversations resolve, while global voice and source-name
leads remain open. 74 Python/source checks pass; playback, native startup,
save/reload and physical acceptance remain unverified. See
[conversation coverage](MISSION_CONVERSATION_COVERAGE.md).

2026-10-03 authored-binding audit adds parameter pairing, spawner IDs and
cinematic script provenance for Tutorial/M13/M01. 55 Python/source checks pass.
Reference gates and all new native mission/runtime gates remain incomplete;
no build or launch. See [binding audit](AUTHORED_MISSION_BINDINGS.md).

2026-10-03 integration follow-up: all original campaign DSP code units are
source-selected; Scripts trim-symbol isolation and original-owner mission-rank
storage are implemented but uncompiled. 41 static/diagnostic checks pass.
Restart persistence, runtime registration, complete mission routes and physical
acceptance remain open. See [integration report](STATIC_SCRIPT_LINK_AND_MISSION_RANKS.md).

2026-09-27 follow-up: additional startup particle lifetime/LOD defaults,
mission-rank persistence, radio-input and round-transition gaps are confirmed;
projector render targets remain unsupported. Nested W3D scan finds 14 unresolved
texture names as leads, not confirmed asset defects. 81 Python checks pass,
no build/launch or native acceptance. See [follow-up audit](DEEP_AUDIT_FOLLOWUP.md).

2026-10-02 source-only follow-up: five required script owners and three W3D
owners are source-selected; Vita startup restores their original loader
registrations and particle defaults. The original Options template and
supported Tech Options route are selected. Static sweep reports no unselected
script/persistence owners across 17 maps. Changes are uncompiled; missing M01
cinematic data, death/failure, save/load and multiplayer routes remain open.
36 focused Python tests pass; no build or native acceptance. See
[cross-system deep audit](CROSS_SYSTEM_DEEP_AUDIT.md).

Earlier audit snapshots follow; their counts are historical.

2026-09-27 video audit supersedes implied M13 whole-mission coverage:
Test_RAD/Toolkit/Toolkit_Objects/Test_DAY/mission08 were omitted; existing
Dev207 ARM and inspected host lack 15 required factories. Both source lists
are corrected but uncompiled. All seven reference mission segments require
fresh native verification. See [coverage audit](M13_VIDEO_COVERAGE_AUDIT.md).

2026-09-27 Dev204: original icon, LiveArea background/gate, and launch image
are version-stamped and packaged. Fast build, Vita3K install/readback and
bounded LiveArea capture pass. This is emulator title-presentation evidence,
not physical acceptance or a new gameplay pass; Dev202 below remains the
latest Practice run.

2026-09-27 Dev202: Practice retains original frontend map/session ownership;
original MultiHUD is linked for full port, and Practice/C&C select original
loading backdrops 96/94. Build/install passed; a bounded Vita3K run entered
Practice, showed backdrop 96, rendered `Skirmish00.mix` with HUD and accepted
brief movement. Original C&C loading visuals, full Practice gameplay,
natural exit and physical Vita remain unverified.

2026-09-27 Dev201: multiplayer UTF-16 name/chat formatting and scoped Glacier
retail-texture factory are implemented, fast ARM-packaged and Vita3K-installed.
Live RenCorner joined Skatepark (ID 12), not Glacier; both visual fixes and
physical Vita remain unverified. See MULTIPLAYER_COMPATIBILITY.md.

2026-09-27 Dev200: live RenCorner Glacier purchase UI rendered and the original
server purchase-response success message followed two released native touch
steps. Player ID 30, at least 1,560 gameplay frames, Vita3K only. Full
multiplayer, exact public display name, performance and physical acceptance
remain open. See MULTIPLAYER_COMPATIBILITY.md.

2026-09-24 native Dev195: original ARM client in Vita3K downloads five packages,
loads City_U1, receives server player/Soldier, renders world/HUD and responds to
bounded movement.9723 frames, START clean session teardown/menu return. Public
listing confirms PSVita without a space. Purchase UI did not appear; full
multiplayer/round transitions and physical acceptance remain open. Details:
DEV195_RENCORNER_NATIVE_JOIN.md. Earlier unlaunched notes below are history.

2026-09-24 Dev195: six audited Combat factory gaps closed in full-port links;
original state-machine callbacks and save/load pass focused sanitizer checks.
Loaded replication probes and 171 fast contracts pass. Package and Vita3K
install/hash verification pass; native execution and full multiplayer remain
unverified. Live host Uphill player test passes 60 frames; public join-message
confirmation pending. See MULTIPLAYER_COMPATIBILITY.md for exact evidence.

2026-09-24 live-player checkpoint: original host negotiates/downloads DethRiver,
receives server-created PS Vita player and controlled Soldier, completes 3,600
simulation frames and disconnects normally. Original special-effects owner is
now linked. Native explicit tt:// direct-IP entry compiles, but native execution,
rendering/input/audio, purchases/respawn/round transitions remain unverified.
Six Combat factory gaps and float-VIS leak remain. No new VPK; Dev194 installed.
Details: MULTIPLAYER_COMPATIBILITY.md; supersedes no-host-player statements below.

2026-09-24 catalog/C4 checkpoint: original catalog network factories, lifetime,
availability and item UI states pass reference and loaded-owner tests. Modern
C4 float layout now passes reference/truncation and loaded attachment/ownership
checks after a live captured decode failure. Host/ARM link;20 focused tests and
17 downloader/TLS tests pass. Static-animated C4 attachment runtime, full TT
events/transitions, float-visibility ownership and live/native player acceptance
remain open. No new VPK; Dev194 installed. MULTIPLAYER_COMPATIBILITY.md is current.

2026-09-24 current checkpoint: live TTFS downloads/mounts and Glacier world load
pass on host; HTTP403 fixed. Modern vehicle state/occupants/control, outgoing
client-control conformance, Soldier occasional inventory and ammo event2003 have
reference/loaded-object evidence. Final ARM link, tutorial and UDP purchase/world
sanitizer tests pass. Purchase catalogs2004/2005, full events/transitions and
native/public-player acceptance remain open. No new VPK; Dev194 installed.
MULTIPLAYER_COMPATIBILITY.md supersedes older missing-vehicle/input statements.

2026-09-24 movement checkpoint: modern Soldier frequent and outgoing aim/state
now pass retail-vector and original loaded-object checks, including ladder,
airborne, locked animation and physics corrections. ARM links; original UDP
purchase/world sanitizer regression passes. Vehicle/full client and native/
public-player acceptance remain open. No VPK; Dev194 installed. Current details
and limitations: MULTIPLAYER_COMPATIBILITY.md.

2026-09-24 shared-state checkpoint: Armed/Smart aim/control/stealth, Defense
health/armor and Soldier occasional sniping/fly imports pass reference and
loaded-object sanitizer checks. Host/ARM link; original tutorial and UDP
purchase/world regressions pass. Full Soldier frequent/vehicle contracts and
native/public-player acceptance remain open. HTTP403 fixed; no new VPK.
Current details: MULTIPLAYER_COMPATIBILITY.md; prior entries are history.

2026-09-24 soldier checkpoint: reference-matching rare decoder and supported
original-owner state integration pass 5904 malformed updates and two loaded
soldier sanitizer cycles; host/ARM link. Full vehicle permissions, non-unit
model scale, frequent/occasional contracts and modern gameplay remain open.
No native/public-player acceptance or new VPK; Dev194 remains installed.
MULTIPLAYER_COMPATIBILITY.md supersedes wholly missing soldier-suffix notes.

2026-09-24 replication continuation: downloaded Hourglass world loading is now
observed on the host, followed by replication failure. Modern creation/inventory,
physical rare fields, bounded decoders and camera-shake policy pass focused host
checks and ARM linkage; legacy purchase/world/tutorial sanitizer checks pass.
Soldier/vehicle and other TT contracts remain incomplete;
no playable public player or native acceptance. No new VPK. Current details in
MULTIPLAYER_COMPATIBILITY.md supersede no-world/unapplied-shake statements below.

2026-09-24 modern admission: real resource offers now arrive, modern options
decode through original owners, and required-package preparation starts.
Exact retail TTFS User-Agent fixes the repository403; original host downloads,
validates and mounts all four required Hourglass packages. All16 downloader
sanitizer tests pass; native HTTPS still unverified. Modern synthetic
download/mount and malformed-options rejection pass; original legacy purchase/
world and tutorial sanitizer regressions pass. ARM ELF links, not native runtime.
No public player join or new VPK. DisableCameraShake semantics remain to apply;
normal modern gameplay is not enabled. See MULTIPLAYER_COMPATIBILITY.md.

2026-09-24 resource preparation: implemented original reliable offer -> bounded
HTTP(S)/cache -> original temporary factory -> deferred start. Flat level pairs,
stock-map overlays and nested MIX1 archives pass host sanitizer fixtures. Native
TLS links in the full ARM executable, but has not executed on Vita. Downloaded
world gameplay, modern TT greeting/replication, normal round transitions and a
RenCorner player join remain unverified. No new VPK; Dev194 stays installed.
See MULTIPLAYER_COMPATIBILITY.md for authoritative current evidence.

2026-09-24 purchase continuation: 24 original AOW units now link, including
catalogs, purchase events, terminal and dialogs/chat. Both factions' original
menus, character/funds/refill and vehicle orders pass two ASan/LSan cycles.
Separate UDP character purchase replicates and disconnects cleanly under ASan.
Full ARM executable links and verifies ELF32 ARM hard-float; this is not native
execution. Full vehicle delivery, TT resource negotiation/TLS and live RenCorner
join remain unverified. No VPK; Dev194 remains installed.

2026-09-24 AOW continuation supersedes the options-layout suspicion below.
Original captured options replay resolves C&C_Walls.mix. Eight specialized
building factories, original harvesting, announcement/chat/loading and Obelisk
event owners now link in full-port targets (14 added original units). Separate
C&C_Walls server/client replication, disconnect and cleanup pass ASan/LSan.
Missing preset 491590001 exposed absent original WarFactory linkage; after that
fix the live host reached missing announcement class 1016, now linked with a
tested original decoder correction. The subsequent live attempt stopped at an
unresolved map, before verifying this latest event integration. Nineteen ARM
objects compile; no new VPK, native execution or RenCorner player join.

2026-09-24 key continuation: original checksum matches PC/TT reference vectors;
host LP64 semantics now preserve Vita/Windows x86 32-bit words. Host runtime,
four ARM objects, original network regressions and two-cycle M00 pass. A live
host RenCorner attempt receives options but decodes an empty map: TT options,
downloads and a playable/native join remain unverified. No new package.

2026-09-15 current candidate: Dev134 canonical/package/matching Vita3K visual
milestone PASS, physical deployment/readback verified. No current physical FPS
or full-demo acceptance. See DEV134_PHYSICAL_MILESTONE.md for current evidence
and remaining gates; older candidate numbers below are historical capabilities.

| Capability | Status | Evidence / boundary |
|---|---|---|
| Native bootstrap, retail root, clean exit | physically validated | A2.0 |
| Original MIX/file-factory chain | physically validated | A2.1 |
| Original WW3D visible asset pipeline | physically validated | A2.2 |
| Original M00 static world | physically validated | A3.0 |
| Original interactive M00 session/player/camera/lifecycle | physically validated | A3.1.4 |
| Original M00 mission-script provider | physically active; progression incomplete | Dev13 physically observed original conversation/control/objective transitions through the post-ladder Logan interaction. Dev82 adds original CombatGameMode finalization plus transition/action diagnostics and restores Triangle as the action/use input for the next physical gate, but it is not accepted until Logan/gate/pistol progression is observed. |
| Vita DirectInput logical +/-1000 axis contract | physically observed + host-tested | A3.5 contract 22/22; physical frame checkpoints record bounded forward/strafe/look values and player displacement. Dev82 keeps the current camera-Y correction, maps D-pad Left/Right to weapon-only switching, maps D-pad Up/Down to sniper zoom, and leaves shoulder buttons unchanged. |
| Original DDS lookup/decode/native upload/bind | physically validated for current M00 subset | A3.5-dev5 late spawn capture visibly shows textured world and weapon; physical telemetry records source requests, decode/upload/bind, with bounded checker fallbacks still reported |
| Original skinned-mesh deformation on Vita | geometry physically validated; material correctness under test | Dev13 physically records 37,606 skinned submissions / 7,207,630 HTree-deformed vertices with zero failures and visible NPC bodies, but material/color correctness failed later physical checks. Dev82 preserves original texture ownership and changes gameplay DDS upload orientation to top-down retail rows; physical validation is pending. |
| Original background/sky path | dev13 physically failed; dev14 host/ARM/package corrected | Dev13 recorded zero indexed draws because Vita passed `render_available=false` to original BackgroundMgr initialization. Dev14 constructs the original sky path, retains original indexed ShaderClass/TextureClass state, and treats the unavailable lens-flare layer as a bounded no-op. Exact physical replay/visual acceptance is pending. |
| Original loading-screen presentation | Dev134 source/build/Vita3K checkpoint; physical runtime pending | Dev40 restored the shared original `LoadingScreenClass` route. Dev99 established the startup/loading repaint path; Dev120 corrected the original animated loading model; later Dev127-Dev134 work preserved the original loading presenter through pause/save/load/refinery checks. Physical validation must still prove coverage, placement, text, audio pacing, and progressing bar behavior on hardware. |
| Startup pre-cache/pre-warm/pre-compute | Dev134 canonical checkpoint; physical runtime pending | Dev99 preserved visible startup pre-cache, persistent MIX filename indexes, source-owned frontend/menu/HUD/subtitle/pickup/shadow/objective/M00 touches, debug/status screen through original engine setup, and startup-status repainting during root/MIX factory construction. Dev134 preserves that line and adds matching package/Vita3K milestone evidence plus verified physical deployment/readback. Physical runtime evidence is pending manual launch. |
| Original HUD/TextDisplay path | Dev134 source/build/Vita3K checkpoint; physical visual acceptance pending | Original message/text surfaces are selected and ARM-linked. Dev99 preserved Render2D text/HUD state, UTF-16 boundary work, dialog-template copying, and HUD presentation scoping; Dev116-Dev134 added numeric HUD, EVA, pause, save/load, Help, and refinery visual checks in Vita3K. Physical validation must still prove Logan/Sydney/Gunner text, health/ammo/pickup legibility, target-box alignment, and pause/HUD stability on hardware. |
| Bounded native input record/replay | physical record passed; dev40 replay pending explicit approval | Dev13 committed 4,537 raw-controller samples with SHA-256 `39d915e02611079b29fb43cb2ea11ede583b063745e9675efe15010c606b7cf8`; replay retains live START abort. The route runner is hash-guarded to exact dev40 SELF plus known prior dev39..dev7 hashes and requires validated loading-screen capture metadata/BMP plus unchanged retail before accepting a route recording. Do not deploy or run another Vita iteration without explicit approval and a first-gate loading-screen visual check. |
| Original texture/material alpha/multistage coverage | mapped | pending coverage matrix and validation |
| Automatic evidence ZIP/capture return | host/ARM validated + physical capture returned | dev5 schema 3 BMP/state/CSV/summary groups are candidate- and phase-matched; physical spawn and post-interaction bundles plus clean-exit logs are retained under the candidate-scoped device-evidence directory |
| HUD Font3D / original Render2D | host-validated | original factory-backed Regatta/Arial FontChars FreeType provider plus Targa/Surface/Texture/RadarManager; optimized + ASan memory-safety two-cycle M00 runs; pending Vita |
| Original WWUI StyleMgr font/layout initialization | host-validated + ARM-linked | retail `stylemgr.ini` initializes menu and in-game original FontChars slots twice; DialogMgr and controls remain unselected |
| Original WWUI parser/resource/manager/MainMenu/Start-SP/Load-SP control frontier | host + ASan/UBSan + canonical ARM package + Vita3K checkpoints; physical frontend proof pending | 52 units now compile: the full selected control stack plus original Render2D/StyleMgr, `RenegadeDialogMgr`, MainMenu, GameMode, Campaign, SaveGame, and GameInitMgr. Focused contracts cover enumeration, pointer tokens, ListCtrl UTF-16/tag/modifier semantics, dialog resources, menu input, font glyph readiness, text-atlas diagnostics, and loading/runtime log breadcrumbs. Dev87 physically failed readable original menu text. Dev88-Dev99 repaired indexed glyph state, frontend scope, font/glyph handling, BINK sizing, text atlas/UVs, deferred Render2D state, short-wchar/UTF-16 formatted text, dialog-template copying, and startup repainting. Dev102 restored visible menu labels in Vita3K; Dev129-Dev133 validated pause pages, Save/Load/Delete/Options/Help, controller focus, native save text entry, repeated Load lifecycle, and Cycle Objectives in native emulator runs. Dev134 retains matching refinery visual evidence. WOL/GameSpy/server-control endpoints are inactive beneath the original single-player branch. Physical Vita must still prove paced intro A/V and a visibly labelled, navigable original menu. |
| A4 original lifecycle/frontend source closure | host + Vita ARM linked; ASan/LSan/UBSan runtime | The 495-action target selects original GameMode, `MenuGameModeClass2`, CombatGameMode, campaign, dialog, WWUI, GameInitMgr and supporting owners; normal, ASan/LeakSanitizer, and UBSan host builds complete two 120-frame M00 cycles. The direct route uses original `Initialize_SP` and matching `Shutdown`, executes the authentic level/session unload order, and is leak-free in the current LSan run. The same selection links as an ARMv7 Vita ELF against the production renderer/platform library closure. `RenegadeDialogMgr` instantiates, updates/renders three frames, and tears down real `MainMenuDialog` (nine controls); when Menu is registered first, the original `Goto_Location(LOC_MAIN_MENU)` route activates `MenuGameModeClass2`, after which `GameModeManager` dispatches three Think frames and safely deactivates/removes it. Generated `chat.rc` aliases are contract-checked against the six IDs used by `MainMenuTransitionClass`. The full menu/CombatGameMode virtual graph is intentionally not activated yet. |
| Original WWUI frontend source pool | staged | 90 source/header files staged deterministically; StyleMgr and the single-player parser/manager/control-construction frontier are selected separately |
| Essential audio | provider/sanitizer + Vita lifecycle contract + ARM linked; physical pending | All 20 selected original WWAudio TUs retain sound/scene/callback ownership over a local Miles-compatible provider. PCM8/16, IMA ADPCM, Microsoft ADPCM, encoded-byte timing, pan, distance, loop/rate mixing, and `SceAudio` linkage pass focused checks. Dev16 statically enforces retail/MIX-chain installation before the original basename-stripping adapter, non-lite construction and initialization before engine/world setup, 2D/3D driver admission, active/suspended frame updates, and audio destruction before renderer/factory teardown; fresh retail host routes pass but intentionally do not claim audible execution. No physical-audio or retail-format claim yet. |
| TT patch/reference integration | toolkit validated; declarations/provenance corroborated | Official TT 4.8.4 revision 9000 archive/diff are checksum-pinned and audited outside the tree. Five portable semantics are already/equivalently present. TT declares the relevant WWAudio interface but publishes no constructor, frame-update, main-loop, or conversation implementation; dev16 restores authoritative EA semantics and imports no TT source or binary. |
| Campaign catalog / launch path | catalog host-validated + ARM-linked; launch source-traced | original `CampaignManager::Init` loads 36 retail `campaign.ini` flow records and matching Shutdown clears them across two normal and ASan/LeakSanitizer M00 cycles. `CampaignManager::Start_Campaign` calls `GameInitMgrClass::Start_Game`, whose original branch calls `CombatGameModeClass::Load_Level`; device activation awaits the A3.2 gate and full ownership closure |
| Multiplayer | native adoption and identity implemented; live admission refused | Original Skirmish00 and separate-process UDP world/player replication pass host/ASan/LSan. Native client ownership/socket fixes compile for ARM. Original challenge response matches 12 TT-reference vectors and transmits over original UDP in normal/ASan replay. RenCorner explicitly refuses the executable/data version key; original unstamped build identity is under investigation. No RenCorner player join, native runtime or automatic TTFS negotiation verified; multiplayer HUD/round flow remain incomplete. See MULTIPLAYER_COMPATIBILITY.md |
