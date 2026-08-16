# Known gaps

## Reconciled program status (2026-08-16)

The frozen A3.2-dev1 package is a failed physical checkpoint, not a candidate
awaiting acceptance. A3.5-dev1 repairs are host/ARM/package evidence only
until its already-produced candidate completes the physical matrix. v3.6–v4.0 contracts, including
resource/memory, renderer performance, authentic frontend/HUD/audio, campaign,
and Direct-IP/LAN provider work, are tracked in `PROGRAM_CHARTER.md` and must
not be inferred as complete from host-only closure.

- The direct host/Vita Combat route now restores the original `PathMgrClass`
  application lifecycle after a canonical LSan run found one retained
  `PathSolveClass` (80,256 bytes). Its focused two-cycle M00 sanitizer rerun
  is clean, but complete canonical regression and physical exit/restart proof
  remain required. This does not validate device memory behavior.

- A3.2-dev1 restores the original texture route and diagnostic fallback, but
  texture correctness still requires physical Vita observation; A3.1.4 remains
  the accepted untextured visual baseline.
- A3.1.4 right-stick look was unusable because the platform emitted ±32767 to
  an original consumer expecting ±1000. The central conversion is host-tested;
  physical confirmation remains required.
- Font3D/HUD now passes the original Targa/Surface/Texture, RadarManager, and
  Render2D path in optimized and ASan two-cycle M00 runs. Native HUD promotion
  remains pending A3.2 hardware evidence and a separate candidate; audio output
  is still deferred.
- The authentic `FontCharsClass` provider now obtains Regatta and Arial from
  retail archives through the original file factory and passes ASan memory-safety
  cycles. The current HUD-enabled two-cycle M00 route is leak-free under
  LeakSanitizer after restoring original Combat/GameInit shutdown ordering and
  the `cNetwork` factory-file return. This is host evidence only; repeated
  load/exit behavior still needs physical Vita confirmation before resource
  ownership is considered closed.
- The authentic frontend requires the original WWUI StyleMgr/DialogMgr/MenuDialog
  stack plus controller-facing WWUI input. Its 90-source staging pool and retail
  menu models (`IF_BACK01`, `IF_RENLOGO`, `IF_EVAGIZMO`) are available; no
  substitute menu is used. `StyleMgrClass` now compiles, ARM-links, and performs
  two host `stylemgr.ini` font lifecycles through the provider. The expanded
  52-unit frontend/campaign probe compiles the selected full control set,
  Render2D/StyleMgr, Campaign, GameMode, SaveGame, and GameInitMgr under host,
  ASan/UBSan, and Vita ARM. The earlier frozen-ELF audit found 91 references
  beyond the A3.2 package. A separate 495-unit target now link-closes the
  selected owners normally, under ASan, under UBSan, and as a Vita ARMv7 ELF
  against the production renderer/platform libraries. This still does not
  establish a device runtime menu. The later original `MenuGameModeClass2`
  lifecycle now registers before the original `Goto_Location(LOC_MAIN_MENU)`
  route activates it, then receives three manager-driven Think frames before
  safe removal around the real dialog lifecycle under normal,
  ASan/LeakSanitizer, targeted UBSan, and ARM closure; it still requires the
  physical A3.2 gate before any device-menu or campaign-launch claim.
- The bounded frontend probe now compiles original DialogParser, DialogMgr,
  WWUIInput, DialogControl, MenuDialog/MenuBackDrop, mouse, tooltip, transition,
  `RenegadeDialogMgr`, and real `MainMenuDialogClass`. The real map-enumeration
  boundary resolves only beneath the retail root and passes a normal + ASan
  ten-check case-fold/wildcard/traversal contract. Its Vita selection retains
  only original Main Menu/Start SP/options/difficulty/load/quit factories;
  WOL/LAN factories are explicitly unavailable until their original providers
  are ported. The installed `game2.exe` resource table was rejected: its
  purported dialog leaves resolve to executable bytes, not valid templates.
  The replacement boundary deterministically compiles canonical released
  `chat.rc` records, not handcrafted layouts or retail assets. `DialogBase`,
  dialog text, Button/MenuEntry, ListCtrl/ScrollBar/ListIconMgr now compile,
  but the genuine link/runtime closure and Vita observation remain. Original
  `EditCtrl` requires the full
  IME composition/candidate service. Do not replace it with a synthetic edit
  control; complete a real Vita text-composition boundary before enabling IME
  use at runtime.
- The actual `StartSPGameDialogClass` and `DifficultyMenuClass` bodies are now
  selected from original shared `dialogtests.cpp` under a Vita single-player
  compilation boundary. The tutorial button retains the genuine
  `cGod::Reset_Inventory` → `CampaignManager` → `GameInitMgrClass`
  `Initialize_SP`/`Start_Game("M00_Tutorial.mix")` route, while difficulty
  retains original `Start_Campaign`/replay routing. Its unrelated WOL/LAN and
  GameSpy implementations remain conditionally excluded because their first
  declaration dependency is `gamechannel`/`WWOnline`; full menu linking,
  ownership, and runtime activation remain unproven.
- `GameInitMgrClass` now compiles with its original SP initialization, start,
  load, exit, and return-to-dialog ordering intact. Only retired WOL NAT,
  GameSpy QnR, PC server-control, and auto-restart service endpoints are
  isolated below that branch; they are inactive rather than emulated. The
  original `CombatGameModeClass::Load_Level` owner is now selected into the
  495-unit host link, but the direct M00 harness deliberately does not execute
  its full virtual/menu graph. Its remaining multiplayer presentation and
  desktop-service owners must be closed before this becomes a campaign-launch
  claim.
- The authentic `LoadSPGameMenuClass` now compiles at the same host, sanitizer,
  and Vita ARM boundary. Its original saved-game/map enumeration and launch
  routes use Vita `FindFirstFile`/`FindNextFile` and a bounded pointer-token
  compatibility bridge. It has not been linked into a device runtime: actual
  list ownership, save deletion, map launch, and repeated menu transitions
  require the A3.2 physical gate and a subsequent candidate.
- The original `ListCtrlClass`, embedded scrollbar, and list-icon manager now
  compile with Load-SP and their narrow compatibility contracts are tested,
  but rendering, focus, and repeated ownership behavior are not linked or run
  on Vita yet.
- The frozen A3.2-dev1 diagnostics ZIP and collector are validated. The
  collector now resolves output paths before temporary staging and content-
  prefixes returned evidence to avoid basename collisions. Phase-specific
  screenshots and runtime captures still require a physical Vita return; no
  automatic device screenshot claim is made.
- The configured Vita3K data root contains only the historical A3.1
  `RNEGA3101` installation; no A3.5 VPK is installed and no executable/log
  location is configured. `VITA3K_EVIDENCE.md` records the observed title
  identity and the controlled user-mediated replacement/collection loop. This
  is an emulator-automation gap, not a reason to delay physical Vita testing.
- No campaign slice, playable combat claim, AI encounter, mission scripting,
  readable HUD, or essential feedback claim is made before A4.0.
- The returned A3.5-dev4 static-world screenshot observed invisible NPC/player
  bodies, an incorrect first-person weapon, upside-down doors, and an inverted
  static overhead-camera vertical axis. Because its executable identity and
  runtime evidence were contaminated, these are retained as visual/input
  investigation leads, not physical validation of a corrected candidate. Do
  not change original Combat player, NPC, weapon, or door behavior based on
  that capture alone; collect a phase-labelled interactive capture first.
