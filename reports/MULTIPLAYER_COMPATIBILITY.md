# Native multiplayer compatibility

## 2026-09-27: Dev202 Original Mode Loading And Practice HUD Candidate

The full-port loading presenter now selects original campaign backdrops for
campaign, original backdrop 96 for Practice, and the original C&C multiplayer
backdrop 94 for remote C&C. The full-port links original `MultiHUDClass` rather
than its no-op compatibility header. Practice map selection and game/session
initialization remain owned by the original frontend. The user's retail
`campaign.ini` and `Skirmish00.mix` were inspected unchanged.

Dev202 passed 177 focused tests, fast ARM package and Vita3K install/readback.
VPK SHA-256: `d0b0eb1b803ec07d8ee17e1f361a5a10684ecee8b66a86126abdf229c7025f28`.
A bounded Vita3K run reached the original main menu but did not enter Practice;
loading visuals, Practice gameplay and physical Vita remain unverified.
The [Dev202 prerelease](https://github.com/TheGh0stShip/RenegadeVita/releases/tag/A3.5-dev202)
is tied to source commit `30b0d27a492c43ab2807f925230f5d6f0b47b601`;
GitHub's uploaded VPK digest matches the SHA-256 above. This is publication
and package integrity evidence, not additional runtime acceptance.

## 2026-09-27: Dev201 Glacier Texture And Multiplayer Text Candidate

Dev200 Glacier logged a real `l02_ice.tga` source fallback and repeated checkerboard
binds while buildings rendered. The user's unchanged retail `M02.mix` contains
`l02_ice.dds`; the multiplayer factory list did not mount that archive. Dev201
mounts the retail M02 archive only for the remote Glacier U1 map, after the
server map factory, without packaging or modifying retail data. The original
texture loader remains responsible for resolving and decoding the DDS.

Original player-join/leave, scoreboard, and chat formatting passed
`WideStringClass` objects into `%s` varargs on ARM. Dev201 passes explicit
UTF-16 pointers at those call sites through a deterministic staging patch.
This explains the square player-name glyphs despite working StyleMgr fonts.

Dev201 fast ARM/package, candidate identity, Vita3K install/readback, and
focused contracts passed. VPK SHA-256:
`576f974a167efb92ea034c6b05505aba5bce7413a53984c4274b818227f06b87`.
The bounded live Vita3K replay joined RenCorner as `PS Vita` (replicated ID 12),
but the server had rotated to `C&C_SkateparkV2.mix`. Its capture shows readable
server text, not enough player names to prove the glyph fix. No Glacier visual
validation occurred. The 150-second runner ended `TIMEOUT_UNASSESSED`, not a
clean-exit proof. Private evidence: managed `dev201-glacier-texture-font-01`,
runtime log SHA-256
`bf722448cc895a0c297648737b561f04812b61015d8ce58d68c6f88cc4aca8ea`.
Full map textures, player names, physical Vita, and stable performance remain
open.

## 2026-09-27: Dev200 Live Purchase Response

The Vita remote-player wait now uses original WWNet's server loading window
(15-second connection timeout plus 45-second loading allowance) instead of the
port's fixed 30-second cutoff. It still exits on connection failure, protocol
failure, START cancellation, or expiry. This addresses a demonstrated local
early-abort condition; the following run does not isolate this change from the
different negotiated map, so no causal connection-stability claim is made.

Dev200 fast ARM/package and Vita3K install/readback passed. VPK SHA-256:
`1197653f2ac16243f7dbd2cc705117d5fab46eaf5bb99b20bf63019811405ab9`.
On RenCorner Glacier the client requested `PS Vita`, received player ID 30,
and the one-shot diagnostic opened the original purchase screen. An owned-window
Vita3K capture visibly shows the original item grid, credits and Buy control.
Two native touch steps, both with release receipts, selected zero-cost Nod
Soldier and activated Buy. The dialog closed and a subsequent capture displayed
"Purchase request granted." In original source, that exact message is emitted
by `cPurchaseResponseEvent::Act` for `VendorClass::PERR_SUCCESS`; this is
evidence of a successful original server purchase response, not merely a local
button press. The run reached at least 1,560 gameplay frames without a recorded
connection-loss transition. Public RenCorner listing showed `PSVita` with no
space; exact display-name preservation remains unresolved.

Private evidence: managed `dev200-tt-purchase-01` (runtime log SHA-256
`0ae761ccd832dae365bbadb3dec67e1b3ef263cf10c3f25e5b65a18b393b48b2`,
owned-window captures at 03:09:22, 03:09:44 and 03:09:58 UTC). The runner ended
at its three-minute limit with `TIMEOUT_UNASSESSED`, not a clean-exit proof.
Vita3K title-window captures are user-visible visual evidence, not direct
framebuffer readback. A bounded host original-client comparison also joined
the same endpoint after the map changed to Glacier, received its player and
completed 60 simulation frames. No physical Vita, respawn, vehicles, chat,
round transition, sustained 60 FPS or full multiplayer acceptance is claimed.

## 2026-09-27: Dev199 Original Purchase Menu Diagnostic

The full-port runtime now recognizes an opt-in, one-shot local file
`ux0:data/renegade/user/config/dev-tt-purchase-menu-once.flag`. Only after a
remote session has a valid replicated Soldier and matching player data does it
consume the marker and call the original
`PlayerTerminalClass::Display_Default_Terminal_For_Player`. It does not move the
player, alter credits/items, or bypass the original purchase request/response.
Absent the marker, normal gameplay is unchanged; the demo profile is untouched.

Dev199 fast build/package and Vita3K install/readback passed; VPK SHA-256 is
`12d95a0f7007b8fb7954ee59ae1b97304dd6f1ea16cc2005f59383a6728a1987`.
The first live Vita3K run joined RenCorner Mesa as requested `PS Vita`, received
player ID 5, consumed the marker, and instantiated original purchase dialog
template 236. It reached 236 gameplay frames, then left with `ConnectionLost`
(state 5). No visual dialog, selection, purchase request/response, respawn, or
round transition is proven. Private evidence is `dev199-tt-purchase-01` in
managed logs; its runtime-log SHA-256 is
`251130155d4efb3ebcfa1fe8ba2a0dcb91ea693dc222bd332d852c38a0ed8d0e`.
A second same-binary capture attempt failed during remote-player replication;
Vita3K then reported a host access violation during game close. It never
consumed the diagnostic marker, which was removed afterward. This does not
establish an ARM crash or visual result. The opted-in owned-window focus
capture helper was syntax-checked but has not captured an active dialog.

The broader optional Python discovery suite found three failures in unrelated
historical screenshot, diagnostic-hotpath, and wide-character contracts;
Dev199's focused tests and fast package gates passed. Canonical acceptance and
physical Vita multiplayer remain open.

## 2026-09-27: Dev198 Gameplay Dialog Candidate Return

Canonical host, ARM, ELF/SELF/VPK identity and Vita3K install/readback gates
passed. VPK SHA-256: `2336fb7f705cedfa50dbaa5717a5d59f41e526bd23f9536eda88af7b23f7556f`.
The bounded OpenGL Vita3K run requested `PS Vita` at RenCorner, accepted the
server's Mesa map, received the replicated player/Soldier (ID 3), and passed
the 480-frame checkpoint. It did not exercise a purchase terminal. The runtime
log ends during the next checkpoint and the six-minute runner returned
`TIMEOUT_UNASSESSED`; do not infer a crash, a dialog pass, or sustained frame
pacing. Matching private evidence is `dev198-tt-native-01` in managed logs;
runtime log SHA-256 is
`2b88f42958f2408ff1759314db7db0fdc65fe7dfdcf1ea7cc76a7a3c2b14e8e4`.
No physical Vita test or exact public display-name proof follows.

## 2026-09-26: Gameplay Dialog Dispatch Candidate

Original desktop `mainloop.cpp` updates `DialogMgrClass` once per frame and `gamemode.cpp` renders it with the combat overlay. The native gameplay boundary omitted both, although the original purchase dialog and resource providers were linked. It also omitted the existing WWUI key-transition pump during gameplay; Vita D-pad input stayed mapped to weapon/zoom controls even when a dialog opened. The full-port-only Vita boundary now calls the original update/render methods in desktop order, pumps WWUI keys each gameplay frame, and routes D-pad/Cross/Circle to WWUI while a dialog exists. Original `Input::Menu_Enable` suppresses gameplay actions, and `MenuGameModeClass2::Deactivate` flushes frontend dialogs before gameplay. Demo behavior is unchanged. Focused frontend/input contracts pass (21/21); Dev198 packaging and a bounded native join passed as detailed above. Native purchase UI remains unverified. Next proof: exercise a real terminal and verify dialog presentation, selection, purchase result, respawn, and round transitions. The requested display name with a space also remains unverified; Dev195 was listed publicly as `PSVita`.

## 2026-09-26 Status: Dev195 Native Join In Vita3K

The installed ARM executable now downloads all five server packages, mounts
them through original factories, loads City_U1 and receives the server-created
player/Soldier. 9,723 rendered frames, bounded movement and START original session
teardown/main-menu return are verified. Public snapshot lists PSVita without a
space, rather than the requested PS Vita. Exact normalization is unresolved.
The purchase dialog did not appear after Action; ongoing native dialog dispatch
is absent from the gameplay loop and must be connected with original owners.
Early multiplayer text has malformed glyphs. Full multiplayer/round transitions,
physical acceptance and leak closure remain open. The outer runner timed out
at the returned menu; retain TIMEOUT_UNASSESSED separately from session PASS.
Evidence and exact setup/hashes: DEV195_RENCORNER_NATIVE_JOIN.md. This supersedes
all earlier unlaunched/public-list-unverified entries, not full-game acceptance.
The runtime return is from 2026-09-25. Dev195 is now published with matching
source, green GitHub Actions and a redownload-verified VPK. Older work-unit
entries below preserve their original unpublished/unlaunched states as history.

## 2026-09-24: Original Owners And Dev195 Package

The six audited missing Combat owners are now linked unchanged in the shared
full-port manifest: SAMSite, DamageZone, SakuraBoss, MendozaBoss, RaveshawBoss
and CharacterClassSettings. The deterministic combat-a35-original-owner-cpp
patch fixes explicit member-function pointers, dependent type qualifiers and
one MSVC loop-scope assumption. It does not replace boss state transitions.
The original state-machine callback/denial/force/halt/resume/save-load executable
test passes ASan/LSan. Loaded Soldier/vehicle/catalog/C4 probes pass two tutorial
cycles with sanitizers. Eight focused factory/ABI/reference tests pass.

Final downloaded-package factory audit has no missing Combat registrations.
Its exit1 still records editor-only factories and intentionally absent host
audio; registration is not runtime behavior acceptance. Evidence under
build/host-m13-diagnostic: tt-combat-owners-factory-audit-final.json,
tt-state-machine-selftest.log, tt-combat-owners-loaded.log and
tt-combat-owners-focused.log.

The fast package gate passes171 contracts plus the original DDS alias executable
test. One source-contract test originally scanned from the M00 prewarm definition
through unrelated multiplayer startup to its caller. It now restricts the
no-simulation assertion to that prewarm function. No runtime change was needed.
266 staged patches; registry d46a9e4123d23f9f67ca535593eedd234c16478d9daf033c9b96b6adce1bea98.
Dev195 ELF cf0bc71915616a53a14ad8286184eb74429e97e6a4ef5d621e3ac52dfbd3be64;
SELF 28468b0b6fd5ce3e7ee6d804c55d51a3cac1becea46e6da141bbeefb2291cb2e;
VPK 04f4615dc9d9f891c2f36d8782f41b66580de35b6c90346a0cea0e5d417eaf61.
Host 630067efbf3d08cae895087c6d4614324620d362287562f704ab66c00abd374d.
VPK contains only eboot.bin and param.sfo. Fast package and matching Vita3K
installation pass; no native launch or physical acceptance yet. Canonical
acceptance and asset-free GitHub publication remain pending.

At the user's request, live host rejoin now negotiates C&C_Uphill.mix and five
packages. A bounded short run verifies the server-created player/Soldier for60
frames and exits normally. The first long run was manually interrupted before
its outer timeout; the sampled stack was in weather spawning. This does NOT
prove a deadlock: a subsequent weather probe found normal density0.3, emitter
size20 and17ms frame delta, and the short live run passed without a spawn-count
breakpoint firing. No weather fix or lag-free claim follows. Public/player-side
join-message visibility is not yet independently verified. Full private logs
stay outside Git. The subsequent non-debugger soak completed3600 verified player
frames and normal teardown, exit0. Safe milestones: tt-uphill-rejoin-summary.log.
All sessions are terminal. Native TT launch, modern round transitions and the float-VIS leak
remain open; earlier installed-Dev194 statements below are historical.

## 2026-09-24: Live Host Player And Native TT Entry

First verified live original-host player: the post-C4 probe negotiated
C&C_DethRiver_HD.mix, mounted five packages, received its server-created player
and matching controlled Soldier, completed60 simulation frames and exited
normally. `Initialize_Direct_IP` requests the name PS Vita; no local player or
network ID is manufactured. This supersedes the earlier no-host-player state,
not the still-open native PS Vita/full-multiplayer objective.

The longer sanitizer run failed after417 verified frames when RenCorner created
preset82110001. Read-only inspection found it in downloaded rc_custom_01.mix's
Objects.DDB as Spawner Created Special Effect. Its original
SpecialEffectsGameObj definition/persist/runtime owner was absent from the link.
Added the unchanged original compilation unit to the shared full-port source
manifest. Original animation, sound, collision group and timed deletion remain
the owner; no substitute effect or fake creation success was introduced.

After that fix, the bounded live host run completed3600 verified simulation
frames with the server-created player and clean original session teardown.
Inferior exit0; GDB capture did not encounter a rejected update. This run had
LSan disabled because of ptrace, and is NOT leak-clean acceptance. The preceding
LSan run reproduced the known1032-byte float-VIS channel leak. DethRiver and
Glacier share that unresolved asset ownership problem. No native rendering,
input, purchases, death/respawn, round transition or performance claim follows
from this headless participation test. The public player-page URL returned a
server-selection dashboard; no independent player-list confirmation is claimed.

Native one-shot direct-IP launch now accepts explicit
`tt://51.222.10.72:5001` in
`ux0:data/renegade/user/config/direct-ip-launch-v1.txt`. The shared strict parser
also drives host requests. Bare addresses retain legacy behavior, malformed
requests leave outputs unchanged, and the original WWNet client consumes the
one-shot TT greeting. Normal campaign/demo launch is unchanged. This is an
experimental entry route, not a finished multiplayer browser. It still needs
the privately provisioned identity file and trusted `user/config/cacert.pem`;
neither credentials nor server/retail assets belong in a VPK or Git.

Durable inventory: `tools/diagnostics/definition_factory_audit.py` parses DDB
definition-manager chunks from unchanged MIX members, then asks the actual host
executable's SaveLoadSystem for each factory. Three malformed/structured-data
tests pass. Output `tt-definition-factory-audit.json` identifies six remaining
unlinked original Combat definition owners: SAMSite, DamageZone, SakuraBoss,
MendozaBoss, RaveshawBoss and CharacterClassSettings. It also reports editor-only
records and the intentionally absent host audio definition owner; those must
not be misreported as native gameplay linkage failures. The audit establishes
registration coverage only, not correctness of registered implementations.

Evidence in `build/host-m13-diagnostic/`: `tt-effects-live-summary.log` retains
only whitelisted live milestones; private full logs/captures stay outside Git.
`tt-native-entry-parser-final.log` passes explicit-profile and repeated original
UDP accept/refuse cleanup checks. `tt-effects-reference-tests.log` has14 passing
reference/audit/ABI tests. `tt-effects-tutorial.log` passes two ordinary tutorial
ASan/LSan cycles; `tt-effects-udp/result.json` passes original Walls purchase/
replication/disconnect with both exits0. These regressions use the final binary.
Host/ARM links and no-work repeats pass; ELF32 little-endian ARM EABI5 inspection
passes. ARM ELF SHA256
`4aba1418bfa5a1ced8116be8a16ec840b84a4eed3f407e345107d81fb260fdb0`;
host SHA256 `370b7521c5d4ade1610e7768651eb002e3fc1dfd53229eda9297fb7ca1e30fe7`.
Manifest: `tt-effects-artifacts.sha256`. Staging remains265 patches.

All jobs terminal. No new SELF/VPK/install/push: Dev194 remains installed and
does not contain this work. Next: resolve audited runtime-class gaps and
float-VIS ownership, then package/hash/install the native TT candidate and
provision its isolated launch request, identity and trust bundle. Confirm native
download -> negotiated map -> server-created player before claiming PS Vita
has joined. Every packaged dev still requires Vita3K install and authorized
asset-free GitHub publication. Physical auto-deployment remains prohibited.

## 2026-09-24: Catalogs And C4 Checkpoint

HTTP403 remains resolved by the exact retail TTFS User-Agent. All17 downloader/
TLS tests pass again with sanitizers and the original engine cache probe:
`tt-c4-http-engine-regression.log`. No certificate checks were relaxed.

PurchaseSettings2004 and TeamPurchaseSettings2005 now use the original
definition, network, vendor and dialog owners. Network factories attach existing
definitions by page/team; definition lifetime remains authoritative. Deferred
registration preserves legacy local sessions. Hidden/disabled/busy flags drive
original purchase availability, item visibility and enabled state. Catalog costs,
presets and textures still come from loaded definitions, not invented wire fields.
Air/naval definition pages are accepted; a new air/naval purchase UI and hiding
the page-navigation button itself are not implemented.

Retail b9000 references: page export/import 0x12202680/0x12202b40 and factory
prepare/create 0x12203090/0x122030e0; team export/import 0x1225d6f0/0x1225d8c0
and factory 0x1225dad0/0x1225db10. Twelve executable reference vectors,1215
truncated updates, invalid factory selectors and definition-controlled lifetime
pass. Both factions' original purchase UI/availability, paid/free/refill and
vehicle-order tests pass two loaded ASan/LSan cycles. Original UDP purchase/world
and tutorial also passed on the catalog binary. Evidence: `tt-purchase-catalog-*`.

The subsequent bounded live probe passed the former missing-class boundary and
captured a rejected C4GameObj update, not a player acceptance. The capture tool
was exercised successfully; private packet/logs remain outside Git. C4 rare
uses full-width velocity, position and attachment-offset floats on current TT;
reading legacy compressed fields shifted subsequent health data. Reference
export/import 0x12134b10/0x12133ec0 and four executable synthetic vectors confirm
the layout. Modern decoding now retains original C4 physics/owner/attachment
behavior, preflights the subclass suffix and validates ammunition definition
type. Legacy serialization remains unchanged. Parent state is not claimed to
be transactional. Static-attachment bytes are reference-tested, but an actual
loaded static-animated attachment has not been exercised.

Four C4 vectors and1197 truncated suffixes pass; airborne, ground and dynamic
attachment imports/readback pass two loaded ASan/LSan cycles. The initial loaded
test failed because its legacy readback encoders were uninitialized; setting
the original velocity precision and explicit fixture world bounds fixed the
test without a further runtime change. Final20 reference/audit/ABI/staging tests
pass. Evidence: `tt-c4-reference-final.log`, `tt-c4-runtime-final.log`.
Final ordinary tutorial two-cycle ASan/LSan regression and original UDP Walls
purchase/world/disconnect pass on the same host binary (`tt-c4-tutorial.log`,
`tt-c4-udp/result.json`, both process exits0). All jobs are terminal.

Full host and ARM links plus no-work repeats pass; ELF32 little-endian ARM EABI5
inspection passes. ELF SHA256:
`ba4f728dd718e190851968342eb75131259f3905d88e58309401291a327f1bf5`.
Matching host/map/source hashes: `tt-c4-artifacts.sha256`.
265 deterministic patches; registry
`02063df0f9ad47139e3c4833db183f10a9086595ab5cf95d183e15bbc48ff9b8`.
Evidence files are under `build/host-m13-diagnostic/`.

Raw-animation inventory tool now identifies18 type15 float-visibility channels
in six Glacier building animations. Original HRawAnim's supported-type switch
does not retain these allocations;864 channel-object bytes plus168 float bytes
matches the observed1032-byte leak. Four asset-free audit tests pass. Runtime
ownership/visibility support is still unfixed; dropping the channels is not an
accepted visual fix. Public TT headers name type15 ANIM_CHANNEL_VIS.

No live retest after the C4 fix, public-player acceptance, native execution,
new SELF/VPK or installation. Dev194 remains installed. Next: exercise the
fixed C4 boundary in one bounded captured live run; implement the remaining
observed contracts, and resolve float-visibility ownership before leak-clean
Glacier acceptance. Full TT events/transitions and native play remain open.
Earlier entries below are historical checkpoints.

## 2026-09-24: Vehicle, Client Input And Rotating Server Map

Source/build checkpoint complete; public player acceptance remains open.
Modern vehicle rare/frequent/occasional state is
connected through original occupants, physics, controls, turret and weapon-bag
owners. Seat swaps, local driver versus actual gunner aim, permission disable/
reenable, purchase/team/owner locks, enemy stealing and ammunition preservation
pass two loaded-world ASan/LSan cycles. Eight retail vectors and 1008 truncated
vehicle prefixes pass. Original UDP Walls purchase/replication/disconnect and
ordinary tutorial regressions pass. No native/gameplay acceptance is implied.

Confirmed lifetime fixes: WeaponBag removed its selected weapon before
deselecting it, causing an ASan use-after-free on subsequent selection. Removal
and Clear_Weapons now deselect while the object lives; slot zero stays intact.
RigidBody allocated its owned prediction History but never released it; its
destructor now releases it. Loaded vehicle cleanup passes ASan/LSan. These are
not claimed causes of previously reported campaign freezes.

Reference: pinned retail b9000 below. Vehicle rare export/import
0x12275e30/0x12276090; frequent 0x12272040/0x12272b70; occasional
0x12277320/0x12277390; permissions 0x12276950, controls 0x12276520,
targeting 0x122712e0, PostThink 0x12274040, Armed aim 0x1211fc10.
Stock vehicles have no underground effect; its wire color is consumed as retail
does when that owner is absent. This does not implement custom subterranean
vehicle physics. Physical/Smart parent decoding remains separately tested.

Original CClientControl bytes match retail creation, soldier/sniping, armed
vehicle, missing/deleting object and idle exports in two loaded cycles. The
original one-shot pending controls and object update flag clear after sending.
Reference creation/frequent 0x12138550/0x12138c10, Control 0x1215ec50,
Soldier outgoing 0x12245160 and Armed 0x12120310. Durable tools:
`tt_client_control_oracle.py`, `tt_client_control_probe.h`, and
`test_tt_client_control.py`. This covers outgoing input, not all client events.

The bounded live server retry selected C&C_Glacier_Flying_HD.mix. Its 49,869,382
byte MIX has 201 entries, seven ordering breaks, no duplicate CRCs and valid
member ranges. Our preflight rejected unsorted indexes. Retail's constructor
checks ordering at 0x12009a66 and sorts at 0x1200a7c0; five synthetic executable
oracle cases confirm empty/single/sorted/reversed/appended behavior. The original
MIX factory now sorts only its in-memory index when necessary, retaining
binary lookup and unchanged downloaded/retail bytes. TTFS keeps count/range/
CRC/TLS checks. A shuffled-index original-engine test passes; all17 TTFS/TLS
tests pass ASan/UBSan, with the original factory probe under ASan/LSan.

After this fix the live original host mounts five packages and loads Glacier.
It initially stopped at occasional replication, before a verified player.
Code/reference comparison confirmed Soldier occasional incorrectly used the
creation-time ammunition list. Retail 0x12243fa0/0x12244040 uses the shared
ID-only bag (0x1227f990/0x1227f630), WITHOUT vehicle's selected-index suffix.
Two independent retail vectors retain this difference; populated-inventory and
empty-list tests now pass two loaded-object ASan/LSan cycles. The previous
empty-inventory test was insufficient.
The same live teardown reports 1032 bytes in36 raw-animation channel allocations;
root cause/fix remains open, not hidden by a claimed successful run.

The next live failure identified missing ammunition event 2003. Its four-word
clip/reserve/owner/weapon update now uses original cNetEvent lifetime and original
weapon owners. Retail reference: constructor 0x12288050, import 0x12288100,
Act 0x122881d0 and export 0x12164780. Loaded tests cover authoritative counts,
unlimited reserve, absent targets and all128 truncated payload lengths, without
partial ammunition mutation. Two ASan/LSan cycles pass. The latest bounded live
probe advances past2003 but stops at unsupported class2004, PurchaseSettings;
no server-created player is verified. TeamPurchaseSettings class2005 belongs
to the same pending catalog integration. GDB probes disable LSan only because
ptrace is incompatible; they are not leak-clean acceptance evidence.

Final evidence: `tt-ammo-event-runtime.log`, `tt-ammo-event-reference-tests.log`
(seven pass), `tt-ammo-event-purchase-world/result.json` (both exits0), and
`tt-ammo-event-tutorial.log` (two ordinary tutorial sanitizer cycles).
Full ARM link and no-work repeat pass. ELF32 little-endian ARMv7 EABI5 hard-float
inspection passes; existing wchar_t/GNU-stack linker warnings remain.
ELF SHA256 `13fc9725b353c5bdb300d3d26708dd015e6b3885deb2e3b6a19dd7f4e07799ff`.
Matching host/map/source/inventory hashes: `tt-ammo-event-artifacts.sha256`.
261 deterministic patches; registry
`e6e2b42c0c14262953e6a5493fd8c31be565caf926b11b94058aa595921404b1`.
All build/test jobs are terminal. Next: integrate both original purchase catalog
network owners together, verify their lifetime and fields against retail, then
run offline original purchase tests before another public-server retry.

Evidence is under `build/host-m13-diagnostic/tt-vehicle-*`, `tt-client-control-*`,
`tt-mix-order-*` and `tt-soldier-selection-*`. Private live logs and downloaded
assets remain in the existing private reference cache, never Git or packages.
No new SELF/VPK, install or physical gate. Dev194 remains installed. Full
modern replication/events, player acceptance, native downloads/gameplay,
round transitions, scaling/team visibility and animation behavior remain open.
This supersedes the missing-vehicle/client-control and unsorted-index gaps below.

## 2026-09-24: Soldier movement and outgoing aim checkpoint

Modern Soldier frequent import now consumes full-precision position, omitted
legacy ammunition, ladder heading, airborne velocity, animation names, optional
special damage and DoTilt through original Soldier/HumanState/physics owners.
Locked animations keep their state; the modern DIVE branch leaves following
Smart fields unread as retail does. The vehicle fast path resets existing
prediction history, not animation state. Optional full-position tails work in
both the ordinary and vehicle fast paths. Invalid/truncated fields report decode
failure; this is not a claim that the entire inherited update is transactional.

Outgoing Soldier client state now omits the retired checksum flag and emits
sniping followed by full-precision relative aim, through original Armed export.
Legacy client/server formats and campaign branches remain unchanged. Modern
remote ground corrections blend half the displacement at squared distance <=2;
larger/airborne corrections retain the full step, without changing velocity or
terrain snapping. Local prediction remains owned by the existing history path.
Smart Re_Init restores active stealth; client aiming uses the received DoTilt.

Reference: pinned retail b9000 below, Soldier frequent export/import
0x12244120/0x12244800, outgoing 0x12245160, Armed outgoing 0x12120310,
Set_Targeting 0x1224dc60, position routing 0x122456e0, physics interpolation
0x121e9840 and history Init 0x121eeb90. Inspected interpolation constants are
0.5, 2.0 and 1.0. These correct the earlier hypothesis that the in-vehicle call
was an animation update. `tt_soldier_frequent_oracle.py` executes retail export
with synthetic position/velocity/transform/weapon accessors and an x87 atan2
primitive. Nine incoming and two outgoing reference vectors match; no retail
assets or credentials are in the fixtures.

Final evidence prefix: `build/host-m13-diagnostic/tt-soldier-frequent-`.
Six reference tests, nine staging/ABI/HTTPS contracts, original network test,
two loaded-soldier ASan/LSan cycles and Walls UDP purchase/replication/disconnect
pass. Each loaded cycle rejects 1829 truncated frequent packets and checks
state, ladder heading, airborne position/velocity, correction thresholds,
outgoing sniping/aim, serialized HumanState tilt, locked animation and position
tails. RAMFile is linked only into the host fixture to inspect original saved
HumanState in memory; no user save is touched. Ordinary tutorial regression
passes two in-process ASan/LSan cycles on the final host binary. All jobs terminal.

Full ARM ELF links; repeat Ninja is no-work; ARMv7 little-endian ILP32 hard-float
remains the native target. Existing wchar_t/GNU-stack warnings remain. ELF SHA
`e6ffce195e1b1af69f14eef1c88db9fb20b3961d22730b0b205ca43c3b4b09be`;
matching map/host/patch/fixture hashes: `tt-soldier-frequent-artifacts.sha256`.
257 zero-fuzz patches, registry
`4bb71721cedcece26d43c6417df44df8fc3a599dc9da51ff65e894cbfde27ca8`.
Use `RENEGADE_INCREMENTAL_STAGE=1 bash tools/stage_sources.sh`; wait for terminal
staging before compiling. Final repeat-build closure verifies staged inputs.

Still open: vehicle-specific replication/occupant aiming/stealing, full client
control/event and round-transition contracts, non-unit model scale, team
visibility and modern animation behavior. Host state checks do not prove native
rendering or live gameplay. HTTP403 remains fixed. No new live attempt, verified
public player, SELF/VPK or native execution; Dev194 remains installed. Normal
modern gameplay stays diagnostic-only until remaining contracts are ready.

## 2026-09-24: Shared replication source checkpoint

HTTP403 remains fixed by the exact retail TTFS User-Agent (controlled evidence
below). Shared modern Armed/Smart aiming, control ownership and stealth flags,
Defense health/armor, and Soldier occasional sniping/fly transitions now import
through the original owners. Full soldier frequent and vehicle formats remain
incomplete; normal modern gameplay is still disabled.

Reference: pinned b9000 DLL below. Smart export/import 0x122405b0/0x12240660;
Defense export/import 0x1216f560/0x1216ef10; Soldier occasional import 0x12244040.
New synthetic oracles execute retail serializers; the Defense oracle also
executes its importer using synthetic DataSafe storage. Fixtures contain no
retail assets. Modern aim is three floats; local controls must be consumed but
not applied or followed by a packet flush. Defense uses separate 14-bit ranges
through 10000, retaining existing encoder IDs and legacy packet layouts.

Loaded tests exposed a separate Linux LP64 DataSafe conversion overread:
unsigned-long conversion read eight bytes from a four-byte value and combined
armor type 3 with adjacent storage. Explicit signed/unsigned 32-bit copies fix
the conversion while preserving Vita/Windows x86 semantics. Five word-boundary
cases pass in each of two loaded-object cycles. This is a host ABI defect, not
a change to Vita's fixed ARMv7 little-endian ILP32 architecture.

Evidence: `build/host-m13-diagnostic/tt-shared-final-*`. Host/ARM links, five
reference tests, loaded-soldier two-cycle ASan/LSan, original tutorial two-cycle
ASan/LSan and Walls UDP purchase/replication/disconnect pass. Loaded checks cover
local/remote aim/control, exact payload consumption, 270 Smart truncations per
cycle, 67 transactional Defense truncations, health/armor maxima and sniping/
fly state/collision transitions. Twelve staging/ABI/HTTPS/DataSafe contracts
pass. All16 downloader/cache tests also pass ASan/UBSan against the final host
engine probe, including exact retail User-Agent for manifests and payloads.
ARM ELF SHA-256
`0ff5b46bab2fed10920c7ec3a9b534497c9db6a889c2d7f44465dbb078635359`;
matching map/host/patch hashes: `tt-shared-final-artifacts.sha256`.
255 deterministic patches, registry
`23d2888b97f5367f5c8483fbf26cce832c9c0617bc62df4b919bd9efeed3abf1`.
Existing wchar_t/GNU-stack warnings remain. No new SELF/VPK, native execution,
live world retest or verified public player join. Dev194 remains installed.

Research correction: Soldier frequent's revision>7497 boolean is DoTilt
(raw object +0xd68), NOT UpdatedTarget (+0xd67). Verified against the public
Soldier header and retail UpdateLockedFacing 0x12247e60. Ghidra trace tooling
now supports explicit `entry:0xADDRESS` for independently verified undefined
functions; ordinary missing address selectors report that fact.

Next: implement full Soldier frequent/outgoing state and vehicle contracts,
including occupant aiming ownership, before another live world probe. Confirm
Smart Re_Init resets the new active-stealth flag as retail does. Non-unit model
scaling, full vehicle stealing, team visibility and animation semantics remain
open. Headless tests do not prove visual/gameplay correctness on Vita.

## 2026-09-24: Soldier rare-state source checkpoint

The HTTP403 fix remains verified. This checkpoint adds bounded TT b9000
soldier rare-state decoding and applies supported fields through original
Soldier/HumanState/vehicle-entry/HUD owners: speed, freeze/action restrictions,
damage-animation permission, footsteps, muzzle targeting, animation options,
bot name and skeleton interpolation. Legacy/campaign defaults remain unchanged.
Normal modern gameplay remains disabled; this is not a verified public join.

Reference: pinned b9000 DLL below, rare export 0x1224b5a0 and import 0x1224ba40.
`tools/diagnostics/tt_soldier_rare_oracle.py` executes the original serializer
with synthetic state, excluding the separately verified physical prefix.
All three legacy/modern byte vectors match; 5904 truncated suffix cases retain
the previous state and report an error. Eight bit alignments are covered.
HumanState references 0x121c02c0/0x121c09a0 establish that HumanAnimOverride
controls the override animation collection, and MovementLoitersAllowed controls
automatic weapon lowering, not ordinary idle animations. Extra hold styles
10-14 use the reference names without changing original weapon definitions.
Skeleton interpolation uses original HTree ownership; the width axis advances
against its own target (the reference appears to compare the height axis).

`TT_SOLDIER_STATE_SMOKE`, retained in `tools/run_a30_host.sh`, loads original
M00 definitions and tests a real soldier twice under ASan/LeakSanitizer. Speed,
flags/name import, frozen control and skeleton approach/target checks pass.
The initial probe ran before the first Combat simulation update and failed its
gameplay-active assertion. Running the normal first simulation frame fixes
the fixture; no production gameplay-permission override was introduced.
Bot text rendering, footsteps and animation visuals are not verified by this
headless test. CanDriveVehicles gates entry to an empty driver seat; complete
CanStealVehicles behavior still requires the vehicle's TT CanBeStolen state.
Non-unit model scale and unsupported hold styles explicitly reject rather
than pretend to apply unknown model-scaling semantics.

Evidence: `build/host-m13-diagnostic/tt-soldier-*`. Three final reference tests,
16 TTFS sanitizer tests, nine ABI/staging/HTTPS checks, original UDP purchase/
world/disconnect and two-cycle M00 sanitizer regressions pass. Host and ARM
ELF link; native remains ARMv7 little-endian ILP32 hard-float. Existing mixed
wchar_t/GNU-stack linker warnings remain, not new hardware acceptance.
251 zero-fuzz staging patches; registry SHA-256
`ca42ea53c7a840c71916fff98f1d97d7980bc3416f93dbfd1443a2acd6b4adcf`.
ARM ELF SHA-256
`c5d5b776ca14c04b28cdf3b1c08abf2dae867303f6ccd15de1ce36329214d8ff`;
matching map/host/source hashes in `tt-soldier-artifacts.sha256`.

Next: implement/offline-test occasional and frequent replication through their
original owners, then vehicle state. Verified vtable entries are occasional
import/export 0x12244040/0x12243fa0 and frequent import/export
0x12244800/0x12244120. Occasional adds sniping and fly-mode flags after the
weapon list. Frequent modern position/ammunition/ladder/target flags differ;
nested Smart/Armed/Defense contracts need verification before implementation.
Reference analysis stays in the private reference cache, not in Git.
No new live world test, SELF/VPK, native execution or player-join acceptance.
Dev194 remains installed. Earlier sections below are historical checkpoints.

## 2026-09-24: Downloaded-world replication boundary

The new explicit host `TT_WORLD_PROBE` selects the negotiated map after package
activation and enters the original Combat world loader. A bounded live run
loaded Hourglass (`a31.remote_client_world_loaded=true`), then ASan reported a
bitstream overread in PhysicalGameObj::Import_Rare. This is world-load evidence,
not a player join. A subsequent private incoming-packet capture also exposed an
invalid weapon-definition cast. No further live join is warranted until the
remaining modern replication layouts are implemented and checked offline.

Reference pin remains the b9000 DLL identified below. Physical creation import
0x121f0b60 uses full-width position floats in the modern profile; smart creation
0x122404e0 appends an initial weapon list. Weapon import 0x1227fac0 uses a 32-bit
ID plus signed 16-bit clip and reserve counts. The captured packet's original
decoder entered rare state at bit 201; parsing these reference-confirmed
creation fields places it at bit 361. Its physical prefix and strings then
decode coherently. The redacted summary is
`build/host-m13-diagnostic/tt-physical-capture-summary.json`; raw packets and
downloaded assets stay outside Git.

Source now includes bounded bit/string reads with observable decode failure,
weapon definition class/count validation, modern creation/inventory fields,
and modern physical rare prefix/hidden fields. Physical serializer 0x121f1120
and importer 0x121f1460 are the reference; the synthetic, asset-free oracle
`tt_physical_rare_oracle.py` retains both profiles in
`tools/fixtures/tt_physical_rare_b9000.json`. Non-default team visibility is
explicitly rejected pending implementation, not silently ignored. The verified
DisableCameraShake option now gates the original PhysicsScene shake owner only
on an active modern multiplayer client; campaign and legacy behavior remain.

Still missing: TT Soldier rare suffix (reference import 0x1224ba40/export
0x1224b5a0), including interaction/control flags, scale/skeleton, movement and
animation overrides, bot tag and footsteps; remaining frequent/occasional and
vehicle contracts, modern animation-controller behavior, player replication,
round transitions and native acceptance. Do not treat consuming unknown fields
without applying their semantics as integration. Normal modern gameplay remains
disabled. No new VPK; Dev194 remains installed.

Verification for this source checkpoint:
- Host and full ARM ELF link successfully; repeated Ninja reports no work.
  ARM ELF is 32-bit little-endian ARMv7 EABI5 hard-float, SHA-256
  `a4eb4ff31fe06bb7de4f4e317b7619a61a6779c17b14d57fe34d134024de627d`.
- Synthetic physical serializer bytes match both reference profiles; 5728
  truncated physical payloads and 8448 bit-boundary cases pass under ASan.
  Greeting, options, malformed-header/preset and direct-client regressions pass.
- All 16 TTFS download/cache tests pass ASan/UBSan with the original engine
  cache probe. No TLS or validation safeguards were relaxed.
- Original C&C_Walls UDP purchase/replication/disconnect and two in-process
  M00 load/run/cleanup cycles pass ASan/LSan. These are not modern live gameplay.
- Nine ABI, staging and HTTPS-platform contract tests pass. 250 deterministic
  staging patches; registry SHA-256
  `f6d0b9e39efeecb07ca04574f10085b3cb5fd0c81ffc11a793b218755d983425`.

Evidence: `build/host-m13-diagnostic/tt-replication-*`, final build logs
`tt-creation-final-{host,arm}-build.log`, and `tt-replication-artifacts.sha256`.
There has been no live world retest with these fixes, native execution, new
SELF/VPK or physical acceptance. Next: implement and offline-test the remaining
modern object semantics, then perform one bounded world/player experiment.

## 2026-09-24: Repository HTTP compatibility fixed

Focused recheck for the user's 403 report: the current downloader retains the
exact retail header below. All 17 downloader and TLS-platform tests passed with
`TTFS_SANITIZE=1`, ASan leak checking and the original host engine cache probe.
Log: `build/host-m13-diagnostic/tt-http-compat-recheck.log`. This is a local
regression recheck, not a new live request or native test; the controlled HTTP
comparison and live package download evidence below are retained prior results.
No additional source fix or new package was needed for this recheck. Dev194
remains installed and does not represent this source-only downloader fix.

The 403 was request-header dependent, not an established TLS/platform failure.
Pinned retail b9000's WinINet initializer at 0x121c6d40 uses the exact User-Agent
`TT/4.80.9000-20252502`. `tt_http_user_agent_reference.py` extracts its constants
and checks the InternetOpenA call site without starting the DLL or reading keys;
`tools/fixtures/tt_http_b9000.json` retains the result and reference SHA-256.

Controlled GET of `/marathon/packages/de63063e.tpi` on
`https://ttfs.rencorner.net.co`, fixed to Cloudflare IP 172.67.141.157 using
curl `--resolve`, with certificate verification enabled:

| User-Agent | HTTP | Body bytes |
| --- | --- | --- |
| RenegadeVita-TTFS-Compatibility/1 | 403 | 4551 |
| TT/4.80.9000-20252502 (RenegadeVita-TTFS-Compatibility/1) | 403 | 4551 |
| TT/4.80.9000-20252502 | 200 | 87 |

The exact header is now used by the existing curl provider for manifests and
payloads. This is TTFS request compatibility, not a claim of full TT gameplay.
TLS peer/name verification, redirect rejection, CRC checks and download bounds
are unchanged. The isolated official Windows PackageEditor also failed its
request; Windows alone is not the determining factor. Retail's header differs.

Verified after the fix:
- All 16 downloader/cache tests pass ASan/UBSan, including exact-header requests
  for both manifest and payloads, original engine cache reads, corruption,
  redirect and rollback checks (`tt-http-compat-tests.log`).
- Live original host WWNet negotiates C&C_Hourglass.mix, downloads/validates all
  four required packages and mounts the set through the original factory.
  Transport accepted, options ready, state Ready, joined=0. Exit 0 with ASan/LSan
  enabled; no reported sanitizer error. This diagnostic does not load a world.
- Full ARM ELF links; ELF32 little-endian ARMv7 EABI5 hard-float rechecked.
  SHA-256 `216f9ce7ddbce5293532311d70414d80000789f50e901dfc19db6492205c15c8`.
  `build/host-m13-diagnostic/tt-http-compat-artifacts.sha256` pins matching host,
  ARM and inventory; `tt-http-compat-live-summary.log` retains redacted evidence.

Downloaded assets and raw responses remain private and excluded from packages
and Git. No new SELF/VPK or installation; Dev194 remains installed. Native HTTPS
and a public player join are still unverified. Next: apply the retained camera
shake contract, then verify downloaded-world/player and round transitions.

## Earlier checkpoint: Modern admission and options

Supersedes the missing-greeting/zero-resource-offer checkpoint below. Original
`cNetwork::Init_Client` can now send a one-shot **diagnostic** TT b9000 greeting.
Normal campaign/legacy connections remain unchanged; the diagnostic revision
does not claim complete modern replication or native gameplay compatibility.
The private seed stays in the existing writable-root identity provider. The
greeting transmits MD5(seed), not the seed; no fake Windows hardware identity.

Reference: user-installed `bandtest.dll`, SHA-256
`d520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db`,
TT 4.8.4 b9000, commit `6c9dba44ee3fb7114d83549e6277768235d8588d`.
`tt_client_greeting_oracle.py` executes packet construction/serialization at
0x1214b9d2..0x1214babb with synthetic providers. Three retained fixtures match.
`tt_options_tail_oracle.py` executes 0x1213fa30 with synthetic tier providers:
only the event suffix is tested, not the tier serializers. Its two fixtures
verify float/time, hosted-game word and the one-bit modern flag. The importer
at 0x1213fb30 corroborates replacement of the legacy final CRC pair. Original
tier-one CRCs remain authoritative; the bounded incoming capture consumes all
1039 bits and its map CRC matches the separately offered map. No proprietary
implementation or real credentials are copied into fixtures.

The new read-only options preflight checks lengths, every field boundary,
profile suffix, full consumption and legacy CRC agreement before original game
importers run. Connection-owned profile state prevents server TT metadata alone
from changing a legacy client's decoding. The modern flag is retained on that
connection. Reference global 0x12320783 is `Server/DisableCameraShake` (config
reader 0x122b1f60); applying this to the original camera-shake owner is still
required before full TT gameplay. The admission diagnostic does not load a world.

Live RenCorner observations from original host WWNet, not a physical Vita:
- The modern greeting receives three complete reliable resource groups; legacy
  greeting previously received none. Transport accepted, no refusal.
- Real group names omit `.mix`. Normalize that suffix and select by the options
  map CRC, not group order or HostedGameNumber. Keep original group identity for
  cancellation. Basename/archive/preceding-prefetch fixtures pass.
- Initial legacy options decoding produced map CRC 0/mod CRC 0x80000000. The
  modern suffix correction now resolves the real map and starts preparation.
- The pre-fix run negotiated `C&C_Hourglass.mix`. Its first required package request
  to the server-advertised HTTPS repository returned HTTP 403. A separate normal
  curl GET confirmed a Cloudflare block page. No downloaded world or player join.
  Do not substitute another repository, disable TLS or fabricate package success.

Evidence under `build/host-m13-diagnostic`:
- `tt-greeting-tests.log`, `tt-negotiation-runtime-selftest.log`: reference bytes,
  unaligned fields, 384 insufficient greeting tails, 1437 truncated options,
  wrong profiles, oversized string, missing identity and one-shot reset pass.
  Original UDP greeting accept/refuse and modern-options import pass ASan/LSan.
- `tt-greeting-modern-{stem,truncated}-asan/result.json`: complete modern
  synthetic download/mount succeeds; truncated options fail before mounting.
- `tt-greeting-{stem,stem-archive,prefetch-first,wrong-map,removed}-asan`:
  preparation/selection/cancellation fixtures pass; not world gameplay.
- `tt-greeting-legacy-options-final.log`, `tt-options-direct-final.log`:
  original legacy options/transport regressions pass.
- `tt-options-purchase-world-final/result.json`: original separate-process
  Walls purchase/replication/disconnect passes ASan/LSan.
- `tt-options-tutorial-final.log`: final original M00 two-cycle ASan/LSan pass.
- `tt-greeting-contracts.log`: 18 identity/ABI/staging/resource checks pass.
- Full native ELF links. `tt-negotiation-arm-attributes.log` verifies ELF32,
  little-endian ARMv7 EABI5 hard-float. Existing wchar link warnings remain.
  `tt-negotiation-artifacts.sha256` pins ELF, ASan runtime and patch inventory.
  Native ELF SHA-256 `a28a3c7bc91a8f15a64c289d3694e7b26137483e434d0e29d2d80299d97ddb35`.
  243 deterministic patches; repeated staging copies 0 of 1947 managed files.

Reproduce the focused host gate with `python3 tools/test_tt_client_greeting.py`;
the canonical host runner includes it and both modern preparation fixtures.
Bounded live mode is `TT_ADMISSION_PROBE`, using the existing private user root;
never put identity material in command arguments. Synthetic start-latch checks
use the separate `RESOURCE_ADMISSION_FIXTURE` mode.

The later header comparison and successful live download above supersede this
checkpoint's repository blocker. Continue applying verified modern gameplay contracts, starting with the retained
camera-shake flag, then downloaded-world/player and round-transition tests.
No new SELF/VPK, installation or native execution; Dev194 remains installed.
Normal modern gameplay stays disabled until those contracts are verified.

2026-09-24. User target: join **RenCorner** from physical Vita as **PS Vita**,
including the server-required asset download flow. This is a new active work
scope, not a claim that unresolved M13/M01 behavior or performance is accepted.
The last packaged/installed build remains Dev194.

## Resource preparation and archive checkpoint, 2026-09-24

Supersedes the preparation/TLS-link gaps below, not live compatibility acceptance.
The original client now prepares a complete offered package set outside packet
dispatch, pumps original WWNet while downloading/checking CRCs, mounts through
the original temporary file-factory override, and uses the original deferred
Start_Game handoff. Flat LDD/LSD sets need no fabricated MIX. Stock-map override
sets retain the original retail MIX. A changed/removed active group cancels;
an unrelated next-map offer does not interrupt current preparation. Failed or
partial sets never become active; existing corrupt caches are preserved/reported.

Packages containing original MIX1 archives (.mix/.dat/.pkg) now use the existing
MixFileFactoryClass. A bounded little-endian preflight validates index counts,
sorted CRCs and member ranges before engine allocation/read bias. Combined
index cap is 65,536 entries; unsorted/malformed archives are rejected. Direct
payload lookup is separate from member lookup to prevent recursive archive reads.
Downloaded content is read-only and remains outside unchanged retail data.

Priority follows pinned b9000 observations: last package wins duplicate loose
names; archive activation prepends each archive before the loose factory, so
last archive wins. Reference functions 0x12218a80/0x122177e0 select extensions
and mount order, 0x120076e0 owns first-available lookup. The retained isolated
`tt_resource_precedence_oracle.py` executes original index insertion/lookup and
chain lookup with synthetic records; no proprietary code/assets are copied.
DLL SHA-256 remains d520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db.

Evidence under `build/host-m13-diagnostic/`:
- `tt-archive-factory-tests.log`: 15 tests pass ASan/UBSan, including original
  engine read/seek/read-only/remount, archive/loose priorities and malformed index
  rejection. Eight initial UDP preparation scenarios pass ASan/LSan, followed
  by four archive scenarios and retained good/removal/retail-overlay regressions
  (`tt-archive-final-*/result.json`). These fixtures explicitly do NOT load worlds.
- `tt-archive-final-purchase-world-asan/result.json`: separate-process
  original C&C_Walls player replication, purchase and disconnect pass ASan/LSan.
  `tt-archive-tutorial-final.log`: two-cycle tutorial passes ASan/LSan.
  `tt-archive-contracts.log`: 12 ABI/parser/provider/staging tests pass. Repeated
  staging leaves all 1,947 managed files unchanged; final host/ARM Ninja has no work.
- Full native game ELF links project-local curl8.22.0/Mbed TLS3.6.5, including
  Vita entropy/time providers. The provider is an object library so archive
  ordering cannot silently omit it. ELF32 little-endian ARMv7 EABI5 hard-float
  verified; SHA-256 a4b3749d02e960cb47f0f708cc47a2ad59d8ff60b70f96bac1b954367dd1b685.
  Artifact manifest: `tt-archive-artifacts.sha256`. No new SELF/VPK/runtime claim.
- 240 zero-fuzz staging patches; registry
  81f12cebbd2e3967b0048eeb824f80ead16477ab6e5238cf9be6171b08b660cb.

One bounded live host admission after these changes still receives TT9000
metadata but zero resource groups, unresolved map options, no player. It exits
cleanly under ASan/LSan. This does not prove a server failure: outgoing client
greeting remains legacy, not a fully implemented TT client. No TT revision is
advertised merely because resources work. The analytics page independently
reported C&C_City_Flying_U1.mix at observation; it is not a packet identity check.

Remaining executable work: verify modern greeting and version-dependent packet
contracts against the pinned reference, implement required owners, then test
actual server offers and a downloaded world with server-created player replication.
Round transitions, custom preset registration and native multiplayer remain open.
Host direct-world probe still requires the negotiated map to match its CLI map;
independent preparation does not establish downloaded-world gameplay.

Native experiment prerequisites: trusted PEM at
`ux0:data/renegade/user/config/cacert.pem`, private identity under the same config
root, and writable `ux0:data/renegade/cache/ttfs`. No certificate verification
bypass. A public Mozilla CA bundle was verified in external source-cache:
cacert-2026-08-13.pem SHA-256
f66dff1bdf8f96060b8177976f8b7d9254bc89bc4db933d769f7384d28480bc9;
it is not installed/bundled. Preserve its [upstream source and MPL terms](https://curl.se/docs/caextract.html)
when adding distribution support, and update the strict two-file VPK verifier
before changing package contents. Do not copy the host's private trust store.

## Resource transport checkpoint, 2026-09-24

One bounded live retry after purchase integration still stopped before world
load. Existing options-only capture resolves the current server's map CRC to
`15e7099d`, absent from the retail map set. Both CRC copies agree and the original
options decoder consumes all 1182 bits. This establishes a missing map for this
rotation, not the cause of earlier empty-map runs. Private capture:
`/tmp/renegade-vita-tt-reference/purchase-options-01/`; no credentials captured
or published. No new live player join is claimed.

`tt_resource_oracle.py` executes pinned TT b9000 resource serializers with
synthetic groups in isolated x86. Actual bit/string writer and packet constructor
execute; only memset and final transport send are modeled. Generated synthetic
fixtures are retained in `tools/fixtures/tt_resource_b9000.json`, not proprietary
code/assets. Four groups, empty/max-length names, high-bit IDs, package ordering
and removal bytes match independently constructed expected fields.

`RenegadeTTResources` now belongs to each original cConnection. Resource type8
uses original sender validation, ACK, reliable ordering and duplicate removal,
then bounded parsing. Partial groups do not replace completed groups. Limits:
64 groups, 4096 total package IDs, 255 printable ASCII name bytes. Unsupported
subtypes/names/counts/truncations fail the connection observably. Connection
destruction owns cleanup; receipt alone never downloads or marks a world ready.
Invalid outer header lengths/types are rejected before copies/type statistics.

Evidence under `build/host-m13-diagnostic/tt-resource-*`:
- Parser tests use original bitpacker with explicit 32-bit host ABI; all eight
  bit alignments, every field truncation, trailing bits, limits/replacement/reset
  pass UBSan.
- UDP replay passes ASan/LSan with reordered/duplicate messages, foreign sender,
  invalid header/type and group removal. Malformed-resource replay cleanly fails
  the session and tears down. Synthetic identity only; no public server contact.
- Original transport18/options10, metadata415 and codec18/577 checks pass under
  ASan, as does separate-process original purchase/replication/disconnect.
- Full ARM ELF links: `ecf4927665366419225c636fe77ad25874e0d267a356decfd12c281a353c95fc`.
  ELF32 little-endian ARM EABI5 hard-float verified. 239 zero-fuzz patches,
  registry `a363d16d330f7e77dfe67a70160abead5012051400cd4b19838a9d8ee05eff80`.

Next: resource selection -> validated package cache -> original factory mount ->
deferred original world load, then native/runtime join. Client TT capabilities
are not advertised solely because group parsing works. Package activation,
round transitions, native HTTPS and public/native player join remain unverified.

### Native HTTPS dependency preparation

`tools/build_ttfs_https_vita.sh` pins curl8.22.0 and Mbed TLS3.6.5 archives and
builds into project-local `build/deps/ttfs-https-vita`, leaving SDK OpenSSL/curl
untouched. Configuration is informed by [VitaSDK curl-mbedtls recipe](https://github.com/vitasdk/packages/blob/39efc30332ffeadf6db52dab3e096d62a054466b/curl-mbedtls/VITABUILD)
and [Mbed TLS recipe](https://github.com/vitasdk/packages/blob/39efc30332ffeadf6db52dab3e096d62a054466b/mbedtls/VITABUILD).
Archive SHA-256 pins live in the build script. Curl owns socket handling; Mbed
TLS uses its documented hardware-entropy and monotonic-time alternate providers.
The small original Vita provider uses SDK RNG calls of at most64 bytes and
process-time-wide milliseconds, with failure propagation. 1025 buffer lengths,
three failure positions and >32-bit clock values pass ASan/UBSan. No unlicensed
VitaSDK package patch was copied. Libraries retain upstream notices: Mbed TLS
Apache-2.0 option, curl's permissive COPYING. Build/link and explicit CA bundle
validation are separate from native HTTPS runtime acceptance, which is pending.

## Original purchases and resource research, 2026-09-24

Ten additional original purchase/catalog/UI units are linked through the shared
full-port source manifest (24 AOW units total). This includes VendorClass,
request/response events, the original player terminal, purchase dialogs and
chat. The demo profile remains separate. Original retail definitions now total
3785. Purchase indices and alternatives are checked before catalog access;
missing player/base owners fail explicitly. Legacy WOL commands remain optional.

Original character purchases, insufficient funds, credit deductions, request
refill and invalid-index rejection pass twice under ASan/LSan. A separate
loopback client requests a character, the original server applies it, and the
changed player replicates back before disconnect/clean teardown:
`build/host-m13-diagnostic/tt-purchase-udp-asan/result.json` passes. This is not
a RenCorner or native gameplay test. The full ARM ELF link passes after the
UTF-16 fix; ELF32 little-endian ARM EABI5 hard-float is verified. Artifact hash:
`b34255a155ab6a3640db12ff16be813d5511b2247feb8042808f810c16c3c4de`.
No new VPK or installed candidate.

The original purchase UI needs resource templates 220/221/229/230/236, now
opt-in for multiplayer; demo generation is unchanged. Six resource tests pass,
including an independent LLVM RC comparison (30 dialogs, 382 controls). The
expanded original-terminal/vehicle-order host test initially exposed
EditCtrlClass::Set_Text calling host libc wcslen on engine UTF-16 strings.
The deterministic patch uses established rv_utf16 helpers in edit/chat controls.
This is a host libc ABI mismatch, not a change in Vita's 32-bit architecture.
`tt-purchase-asan-runtime/runtime-07.log` now passes two complete cycles for
both factions: original menus, characters, funds/refill and vehicle orders,
with clean ASan/LSan teardown. Factories initially build startup harvesters;
the test waits through original simulation before ordering, without forcing
factory state. This verifies order acceptance, not completed vehicle delivery.
238 zero-fuzz patches reproduce the source; only two files changed on restage.

Read-only research against authorized TT 4.8.4 r9000 bandtest.dll (SHA-256
`d520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db`,
reference commit `6c9dba44ee3fb7114d83549e6277768235d8588d`) narrows resource
negotiation. These are implementation observations, not accepted wire fixtures:

- 0x12160470 constructs resource packet type 8; 0x1213a930 receives type 8
  through accepted-sender validation, ACK and the original reliable queue.
- 0x12217ae0 serializes subtype 0, group ID, terminated name and package count,
  followed by per-package subtype 0/ID packets, sent in reverse vector order.
  Revisions below 4957 use a package-name CRC; r9000 uses the package ID.
- 0x12217a10 reconstructs a pending group, then its package IDs; 0x12217e20
  dispatches this parser and transfers completed groups to 0x12216220.
- 0x12217d40 sends subtype 1/group ID. Its transition semantics and ordering
  must be verified before implementation; do not infer success from parsing.
- 0x12219dc0 formats repository/packages/%08x.tpi. 0x12214070 schedules missing
  manifests. 0x12215f20/0x12217020 coordinate resource/load states, still open.

Local evidence: `/tmp/renegade-vita-tt-reference/4.8.4-r9000/ghidra/` resource
and downloader analysis logs. No proprietary implementation was copied. Next:
build a bounded resource offer oracle/fixture before connecting type-8 handling
to original transport, and test full vehicle delivery/round transitions.
Native TLS/download, package activation, round transitions and live join remain
unverified. No TT capabilities are advertised solely on these observations.

## Client identity continuation, 2026-09-24

### AOW original-runtime integration

The controlled retry identifies unavailable preset **491590001**, corresponding
to the original WarFactory definition range. Inspection of actual target inputs
and ELF symbols proved all specialized building owner units were absent, despite
being present on disk. Linking them increases loaded retail definitions from
3758 to 3770. No preset substitution or asset changes were made.

`cmake/A35MultiplayerBuildingSources.cmake` is shared by host interactive and
native full-port targets, not the M00 demo profile. It directly links refinery,
power plant, soldier/vehicle factory, airstrip, war factory, communications and
repair bay owners plus original harvester AI. Subsequent live import reaches
missing class 1016 (SCAnnouncement), so original announcements/flood protection,
client chat, loading event and Obelisk event are also linked. Original
SCAnnouncement::Import_Creation incorrectly called Add(mRadioCmdID); corrected
to Get, with a field-value/read-cursor/write-cursor regression under ASan/LSan.
Win32 flood timing uses the existing TIMEGETTIME boundary; no gameplay rewrite.

Missing/truncated preset references now propagate a failed creation through the
original factory/packet handler, mark the active session ProtocolMismatch, and
discard further queued application packets until owner-controlled cleanup. The
test proves no replacement object or successful session is fabricated.

The richer separate-process C&C_Walls fixture exposed two original teardown
leaks: unfinished Test_Cinematic control lists and detached HarvesterClass
observers. Cinematic destruction drains its remaining lines; harvester detach
uses the existing deferred observer-delete owner, and refinery destruction
detaches a surviving vehicle observer before releasing the refinery.
`tt-aow-walls-world-asan-final/result.json` passes server-created player/star
replication, 60 client frames, disconnect and ASan/LeakSanitizer-clean teardown.
Two-cycle M00, synthetic TT UDP identity replay and 19 ARM object builds pass.

Last live event-integrated attempt receives an unresolved map and exits before
world start. Rotation/custom content is plausible, but no matching CRC capture
proves the cause. Neither the new announcement handling on RenCorner nor a
playable public player join is accepted yet. TT resource-manager/package
negotiation, native TLS/download, purchases, UI and round transitions remain.
`audit_multiplayer_linkage.py` uses the configured target's Ninja compilation
database to inventory original macro-registered factory owners: 13 are still
omitted. This inventory is source membership, not runtime/protocol acceptance.

Build-loop correction: incremental staging used to sync an intermediate tree
then reapply the later patches to the active tree, invalidating roughly 180
compile actions on no-op restages and allowing partial staging on late failure.
Sync now follows every patch. Two full restages preserve all 1946 managed files
(zero copies/removals/metadata updates); seven staging tests pass. 234 ordered
zero-fuzz patches, registry SHA-256
`0ae379c5ef9381f02281786a3785921cf6832797e59119bfb5fc99ec2e54ca79`.
No new VPK, native execution or physical performance claim; Dev194 stays installed.

### Subsequent options and world evidence

The previous suspicion of an unsupported legacy options layout is superseded.
`tt_options_capture.gdb.py` captures only the incoming public options event,
normalized from its actual unaligned read cursor. It excludes outgoing packets,
identity material and arbitrary process memory. `tt_options_inspect.py` checks
field consumption; `--options-wire-probe` replays through the original importer
and rooted map lookup. The live fixture consumes all 1198 bits, resolves
CRC f4a8020d to installed C&C_Walls.mix and passes original validity checks.
The previous empty map was not captured, so its cause remains unconfirmed.

The observed TT acceptance extension is now owned by each cConnection: marker
0x21545421, version bits 0x4099999a, bounded length-prefixed repository, revision.
Unknown/truncated metadata fails before acceptance; original retail acceptance
without the extension remains valid. No client TT feature claim or automatic
download is added. Synthetic truncation (415), unaligned-reader and reset cases,
captured greeting UDP replay, original transport/options and separate local
world replication/disconnect pass. Two ARM objects compile.

The bounded live world probe loads negotiated C&C_Walls.mix through original
Combat and submits original BioEvent. Both the initial run and stack-only GDB
replay crash in NetworkGameObjectFactoryClass::Create at definition->Create().
The preset lookup is null. This is not player replication or a successful join.
The next fix propagates missing-preset creation failure through original packet
dispatch, stops the incompatible session, and records the numeric identifier.
Distinguish unavailable server content from wrong decoding before adding assets.
Private runtime roots and options payloads stay outside the checkout.

### Compatibility-key correction (subsequent work)

The installed b9000 TT binary hooks original Get_Data_Files_CRC at client VA
0x00457040 to 0x1214f1c0 (implementation 0x1214f1f0). It retains the same 67
filename entries, including the duplicate, but opens first and reads 16 KiB
chunks to EOF instead of reading a size obtained before opening. The original
key combiner at game2.exe 0x00457450 remains the owner. Its real build getter
returns 838. This is the retail base wire stamp, not TT revision 9000.

`tools/diagnostics/tt_data_crc_oracle.py` executes the pinned TT function with
synthetic file providers: twelve vectors, filename order, short/empty reads,
unavailable files and factory returns pass. `tt_network_key_oracle.py` executes
the original PC combiner/build getter/CRCEngine with synthetic translation
versions/data CRCs: sixteen vectors match. Both tools are isolated x86 function
tests, not a Windows client run. No assets, OS services or credentials execute
inside the emulated references. game2.exe SHA-256:
`1325ed64b91c023caf6a96f35654156e0ef277069f6d1da580c258bb459a809e`.

Confirmed host defect: CRCEngine used sizeof(long) for 32-bit checksum words;
WSL LP64 made its result unlike Windows x86/Vita ILP32. Fixed the accumulator,
stream staging and bulk words to 32 bits, using explicit little-endian loads
instead of potentially unaligned long pointers. Of 832 streaming/alignment/
initial-value vectors, 512 failed before and all pass afterward under UBSan.
This was a host evidence defect; it does not mean Vita is a 64-bit target.
Build-stamp reads now consume exactly four little-endian bytes on both ABIs.

cNetwork now uses verified retail wire stamp 838 separately from artifact
identity and computes the actual translation-version/data checksum, not a
copied final key. No TT feature version is advertised. Data checksum reads
follow the verified EOF contract; failed opens/negative or impossible reads
retain invalid status, return files, and prevent the client sending a join.
Successful empty files and missing entries preserve reference semantics.
ASan/UBSan tests compile the actual staged method against synthetic providers;
failed reads never cache a partial key, and retries/cached success pass.

Four changed ARM objects compile; ELF attributes verify ARMv7/ELF32/little
endian and VFP arguments. Full host runtime links. Eighteen original transport
cases, ten server-options cases, separate-world replication/disconnect,
synthetic TT response replay and M00 two-cycle regressions pass. Build-stamp
getter vectors also pass ASan/UBSan. 227 zero-fuzz patches reproduce the changes.

The subsequent single bounded live host attempt returned server options instead
of the earlier version-refusal text. Computed inputs: retail build 838,
translation version 145, data CRC fa53ecf4, resulting key 4f453ba3. Original
challenge response was prepared; no final key was copied from the server.
The legacy options decoder produces an empty map and marks MissingMap, which is
NOT evidence of a missing retail asset. The options layout/TT accept metadata
must be implemented and validated before downloading or adopting a world.
The diagnostic exits cleanly with transport accepted/options received/joined=0;
exit zero here denotes options receipt only, not a successful player join.
Private run logs stay outside the checkout; never distribute their roots.
Identity acceptance and native execution remain unverified. No new package;
Dev194 remains installed.

Architecture policy is durable in the user's global instructions and this
project's native-porting skill. The force-included target ABI gate rejects a
non-ARMv7/non-little-endian/non-ILP32 native compiler while permitting explicit
host probes. Three compiler-gate tests are in the normal host workflow.

### Earlier identity checkpoint

Original challenge/response events now link in the full-port target. The
response boundary uses the user's privately provisioned serial-derived seed;
it does not revive GameSpy services, fabricate a key, or advertise TT support.
The original event/factory/packet serializer remains owner. Admission precedes
CombatGameMode's replication tick, so response creation now explicitly queues
the original Send_Object_Update before transport Service_Send. Missing/invalid
identity fails visibly and cleans up without emitting an empty response.

The user's installed TT b9000 client is the interoperability reference:
`ttversion.txt` names commit `6c9dba44ee3fb7114d83549e6277768235d8588d`.
`bandtest.dll` SHA-256 is
`d520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db`.
Ghidra 12.1.3 identified the response function at 0x12138040 and its serial
wrapper at 0x12138160. `tools/diagnostics/tt_identity_oracle.py` executes the
pinned x86 routine with synthetic inputs only: no DLL initialization, registry,
filesystem, sockets or real credentials. Twelve vectors match the independent
formula. The tool uses Unicorn 2.1.4 and pefile 2024.8.26 in an external research
venv. Reference binaries/decompilation are not distributed or copied into code.

For numeric retail serials, seed = lowercase hex MD5(normalized digits).
Response = MD5(seed) + eight hex nonce digits + MD5(seed + decimal(nonce modulo
65535) + challenge). This is legacy protocol compatibility, not a modern secure
password protocol. The existing RSA Data Security, Inc. MD5 Message-Digest
Algorithm is reused with UINT4 corrected to uint32_t, fixing host LP64 math
while retaining Vita's original 32-bit representation and required attribution.

Provisioning: `tools/configure_client_identity.py --output PRIVATE_PATH` reads
hidden terminal input, refuses nonnumeric/incorrect-length serials and existing
files, requires a private directory and creates mode 0600. Only the seed is
stored; it is still credential material. Runtime reads exactly 32 lowercase hex
characters plus newline from `user/config/tt-identity-v1.txt`, exclusively through
the writable rooted factory. Never put identity files in VPKs, diagnostics,
Git, command-line arguments or logs. No identity is automatically deployed.

Evidence under `build/host-m13-diagnostic/`:
- `tt-identity-oracle.json`: twelve real-function synthetic comparisons pass.
- `tt-identity-synthetic-{01,asan-01}/result.json`: original replay receives
  class 1017 and sends a complete independently checked response over UDP.
- `tt-identity-missing-{01,asan-01}/result.json`: missing credentials fail cleanly.
- Six focused identity/provisioning/redaction tests, 18 transport and 10 server
  options cases, 18 valid/577 malformed codec cases pass; separate-world
  replication/disconnect passes ASan/LSan (`tt-identity-world-asan-final`).
- Final M00 two-cycle ASan/LSan regression passes (`tt-identity-tutorial-final`).
- Seven identity/event/MD5/message ARM objects compile. This is not native execution.

One bounded live attempt with the legitimate derived identity prepared its
response and exited cleanly, but received no options within the ten-second
probe. Transport acceptance is NOT identity acceptance or a player join.
It also received a host text event, motivating bounded pre-join message capture
(four messages, controls and serial/hash-shaped strings redacted; no gameplay
chat capture). The subsequent bounded attempt captured the exact server reply:
**Connection to server has been refused: Version mismatch.**
Public TT 4.8.4 `DefaultConnectionAcceptanceFilter.cpp` uses that exact reason
for `clientExeKey != gameData->Get_Version_Number()`, separately from the newer
scripts.dll requirement. Thus the next boundary is the original executable/data
compatibility key, not a reason to advertise a fabricated TT revision. Identity
acceptance is still not proven, because that filter checks the version first.

Source investigation: original `Compute_Exe_Key()` combines the build stamp,
translation database version and data CRC. The port still compiles the upstream
unstamped `Insert1Build2Number3Here4` placeholder; its getter also assumes a
32-bit unsigned long. The user's `game2.exe` stamp at file offset 0x3f7cdc has
build 838 at +28 (little-endian uint32). Do not simply override ExeKey or copy
the PC's value: verify the complete compatibility-key calculation, data inputs
and TT patches against an isolated reference before adopting a wire contract.
Native TLS, package negotiation and runtime verification remain open. Dev194
stays installed; no new VPK or multiplayer acceptance.

Final closure: 224 zero-fuzz patches reproduce all three edited staged files.
`tt-identity-artifacts.sha256` pins host executables, seven ARM objects and the
patch inventory. Credential-derived token scan of changed/untracked source and
reports passes. All work-unit processes have exited; no native package produced.

## Earlier native adoption and live TT reply, 2026-09-24

The missing challenge implementation described in this earlier checkpoint is
superseded by the identity continuation above; live admission remains incomplete.

The user supplied the current **RenCorner AOW** gameplay endpoint
`51.222.10.72:5001`, with
[server analytics](https://booyahh.com/log_players.php?srv=RenCorner%20AOW).
This supersedes the older website address below. The user confirms TT owns
the modern connection path despite legacy GameSpy naming. Legacy info-query
timeouts are not TT connectivity tests; do not repeat them as an admission gate.

Native full-port frontend now accepts an explicit one-shot IPv4:port request
in `ux0:data/renegade/user/config/direct-ip-launch-v1.txt`. It retains the
original client connection through world loading, sends original BioEvent and
waits for the server-created player instead of starting a local SP server.
No request is installed automatically. Campaign/demo defaults are unchanged.
START disconnects; remote round changes disconnect until original round flow
is connected. Native execution and TT admission remain unverified.

Fixed a native platform defect: newlib socket descriptors were passed directly
to SceNet handle APIs for close/nonblocking/receive-size lookup. Use libc close,
libc SO_NONBLOCK and original PacketManager with MSG_DONTWAIT recvfrom instead.
The descriptor model passes; three affected ARM objects compile. Interface
reference: VitaSDK newlib
[`socket.c` at 6cba98129f0a286949391de00519ef39762eff18](https://github.com/vitasdk/newlib/blob/6cba98129f0a286949391de00519ef39762eff18/newlib/libc/sys/vita/socket.c),
cross-checked against installed libc symbols and headers. No external code copied.
Host model tests are not native socket execution evidence.

One bounded host original-client attempt received a 99-byte reply from the
specified game endpoint. It contains `!TT!` and the advertised repository
`https://ttfs.rencorner.net.co/marathon`. Receipt:
`build/host-m13-diagnostic/rencorner-aow-admission-01/socket.trace`.
The process crashed while dispatching network class **1017**, original
`GameSpyScChallengeEvent`: `Create_Network_Object` dereferenced a null factory.
This confirms the importance of the retained GameSpy-named event in TT's
modern protocol; it does not call for the defunct discovery/auth service.

The same reply now replays locally through original WWNet with transport
acceptance, explicit `ProtocolMismatch`, no world/player creation, and clean
teardown. Full-port unknown-factory handling reports failure outside packet
dispatch instead of dereferencing null or pretending the event succeeded.
Normal and ASan/LeakSanitizer replay pass; the source-side failure is fixed,
but the required challenge/response is **not implemented**. Original response
code depends on `CCDKeyAuth::AuthSerial`/`gcd_compute_response` and Windows
serial storage. Do not merely link that legacy provider or fabricate a serial,
TT revision or successful validation. Compare with an authorized working TT
client to establish the current identity/response contract.

Immutable reply SHA-256:
`aed8a82b5b6e9c9d018715f38eec2523e34f8e0eba2a4cec5cf1dd538308acaf`.
`tools/replay_tt_admission.py` sends that one reply on loopback only, bounds the
child, and uses isolated writable roots. It explicitly distinguishes expected
controlled admission failure from a passed join. Registered in normal and
sanitizer canonical host gates. Example:

```sh
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 python3 tools/replay_tt_admission.py --binary build/host-a35-asan/a31_m00_interactive_runtime --retail build/host-m13-diagnostic/retail --output build/host-m13-diagnostic/tt-admission-replay-new
```

Evidence: `tt-admission-replay-before/runtime.log` is the GDB diagnosis;
`tt-admission-replay-{after,asan}/result.json` records controlled failure.
The server analytics JSON endpoint (`&ajax=1`) supplies timestamp, map, current
players and history. Before/after observations showed no `PS Vita` player;
these sampled third-party listings cannot prove absence between samples or
replace native gameplay evidence. No other players' records are published.

Host 18 transport/10 options/18 valid + 577 malformed codec cases, 35
socket/frontend/conversation contracts and independent server/client world
replication/disconnection tests pass, including ASan/LSan transport/world
checks. Edited ARM objects compile; all 221 zero-fuzz patches apply and both
new staged file hashes match the tested sources. No new VPK or RenCorner
player join is claimed. Next: current TT identity/challenge implementation,
then actual server options/map negotiation, repository download and native
execution. Remote round flow remains explicitly incomplete.

## Separate client/server worlds, 2026-09-24 continuation

Two independent original-engine processes now load retail Skirmish00 and join
over loopback UDP. New full-port `GameInitMgr::Initialize_Direct_IP` owns the
original C&C game-data/provider lifetime, rejecting an existing session. The
client retains its accepted connection through original CombatGameMode level
preparation/finalization. `A31ClientConnect` then sends the original initial
`cBioEvent`, waits for server-created player/soldier replication and checks
negotiated control ownership. It does not spawn a local substitute player.
The fixture uses the original one-player server setting, which permits play
without an opposing player. Each process has isolated writable directories.

The normal and ASan/LeakSanitizer world tests pass, including 60 client
simulation frames and teardown. These are headless host tests, not rendered
gameplay, PC interoperability, TT admission or native networking evidence.
Final normal and sanitizer runs explicitly pass server-observed disconnection.

Reproduced fixes retained as deterministic staging patches:

- Map-cycle validation used a raw relative `data\\` filename instead of the
  rooted original file factory. Full-port validation now uses the same rooted
  lookup as original map discovery; no validation requirement is disabled.
- MOTD emptiness called Linux's four-byte `wcslen` on two-byte engine strings
  in host validation. Test the first UTF-16 element directly on all targets.
- Reliable-send timeout destroyed a remote host, then wrote its resend count
  through the freed pointer. Invalidate the local pointer before the original
  callback and skip that write. A real silent-peer timeout passes ASan/LSan.
- Client replication hints retained every acquired visibility table. Release
  the table after gathering visible objects, before either return path.
- Conversation Think's reentrancy guard was leaked when releasing list
  ownership also nulled the local pointer. Release the list reference without
  clearing the guarded pointer; the existing final release drops the guard.
  This shared correction also applies to campaign dialogue.

```sh
python3 tools/test_remote_world.py --binary build/host-a30-definitions/a31_m00_interactive_runtime --retail build/host-m13-diagnostic/retail --output build/host-m13-diagnostic/remote-world-new
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 python3 tools/test_remote_world.py --binary build/host-a35-asan/a31_m00_interactive_runtime --retail build/host-m13-diagnostic/retail --output build/host-m13-diagnostic/remote-world-asan-new
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 timeout 90s build/host-a35-asan/a31_m00_interactive_runtime --connection-timeout-selftest
```

Use a fresh output directory per run. Runner bounds both processes and cleans
up only its own children. Tests are retained in `tools/run_a30_host.sh`.
Evidence lives under `build/host-m13-diagnostic/remote-world*` and
`remote-timeout-asan.log`. Final process results are `remote-world-04/result.json`
and `remote-world-asan-04/result.json`; matching binaries, ARM objects, patches
and harness sources are pinned by `remote-world-artifacts.sha256`.
Earlier `remote-world-01` preserves the map-validation failure;
`remote-world-asan-01` preserves the buffer read/timeout failure and
`remote-world-asan-02` preserves the leaks. Tutorial and skirmish each pass two ASan/LSan cycles;
18 transport, ten options, 18 valid/577 malformed codec cases and config
regressions pass. Seven ARM objects compile. Eighteen conversation contracts
pass. All 219 zero-fuzz staging patches reproduce the seven tested files;
registry SHA-256 is
`c13347e81832483f40a3bb3284f4cb4cca2b9e79e8cd6781140146f05ae13857`.

**Next:** adopt this shared state machine in `a31_vita_runtime.cpp` across
frontend, existing-connection world load, server-owned spawn and teardown.
The native frontend's client-only guard remains intentionally closed until
that complete ownership path is wired. Initial joining is tested; subsequent
remote round/map transitions, HUD, purchases, death/respawn, native TLS and TT
repository/admission remain open. No new VPK, install, publication or physical
acceptance is claimed. Dev194 remains installed.

## Server options and deferred launch, earlier 2026-09-24 checkpoint

Original `cGameOptionsEvent` now has a full-port connecting-notification
boundary (`A31ClientConnect`) instead of depending exclusively on an absent
desktop popup. It records readiness/failure without loading inside the UDP
callback. Outside packet dispatch, `Request_Start` repeats the original
settings validation, selects the original multiplayer backdrop, sets client
required/server not required, and calls original `GameInitMgr::Start_Game`.
The existing frontend latches that request; a distinct client-only flag prevents
it from being mistaken for a campaign selection. Connection cleanup invalidates
pending readiness before deleting the connection, including pointer reuse.
The demo profile does not activate this route.

Two additional defects addressed:

- `ModPackageMgr` discovers map basenames in `Data/`, but the rooted existence
  check previously looked only at the retail root. The first UDP options test
  reproduced rejection of a present map. Full-port `cMiscUtil::File_Exists`
  now tries `Data/` for bare `.mix`/`.pkg` names after original lookup fails.
  It preserves factory ownership, namespace restrictions and read-only access.
- Missing-map rejection in `cGameOptionsEvent` previously set `act = false`
  only when a desktop dialog existed. Full-port rejection is now unconditional,
  including without a connecting observer; hosted-game state cannot advance.

`--client-options-selftest` sends the original server-serialized event over
localhost UDP, then exercises the original client packet handler, registered
network-object factory, import and deferred launch request. Ten cases pass
normally and under ASan/LeakSanitizer: two repetitions each of valid map,
missing map, invalid settings, cancellation after options, and missing map
without an observer. It checks no reentrant start, no duplicate start, exclusive
observer registration, the imported time/map/game number, client-only selection,
and restoration of baseline object counts. The original 18 transport cases
also pass normally and under ASan/LSan; 14 frontend contracts pass. Six affected
Vita ARM objects compile, including the runtime frontend guard.
Tutorial and Skirmish00 each pass two host load/run/cleanup cycles. Eleven
TTFS tests, the 18-valid/577-malformed packet codec test and rooted config test
pass. All 215 staging patches apply with zero fuzz; both affected staged
source hashes match the tested files. Final patch-registry SHA-256:
`36c563ce773ad17934e5d33e9aa01523e0dfe1995ac0bbc90c91dda0bfc95c46`.

The generated empty fixture archive tests name discovery/existence only. It
is never loaded as a world, and this test is not PC/TT interoperability proof.
For deterministic serialization the fixture temporarily selects its server
game/connection, restores client ownership, then dispatches received UDP data.
It does not import player/gameplay replication on the fixture server.

```sh
timeout 45s build/host-a30-definitions/a31_m00_interactive_runtime --client-options-selftest
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 timeout 45s build/host-a35-asan/a31_m00_interactive_runtime --client-options-selftest
```

Evidence is `build/host-m13-diagnostic/client-options-{runtime,asan}.log`,
`client-options-transport-{regression,asan}.log`, `client-options-arm-build.log`,
`client-options-frontend-contract.log` and `client-options-artifacts.sha256`.
Both normal and sanitizer options tests are retained in `run_a30_host.sh`.
Remaining evidence: `client-options-{tutorial,skirmish,ttfs,codec,config}-regression.log`,
`client-options-restage.log`, and `client-options-stage.sha256`.

**Remaining integration:** this is the notification-to-original-load-request
boundary, not remote world loading. The Vita frontend intentionally refuses a
client-only request until world adoption retains its existing connection and
server-created objects. Do not enable the public join UI or replace it with
local SP initialization. Next change must cover map adoption, loading/ready
events, server-created player/control ownership, and teardown together. TT
repository/admission and modern native TLS gates remain open. No new VPK,
installation, GitHub publication or hardware acceptance in this work unit.

## Original client transport, 2026-09-24 continuation

Added `--direct-client-selftest`, an asset-free localhost fixture using original
`cNetwork::Init_Client`, `cConnection`, packet encoding, acceptance/refusal
callbacks and `CombatNetworkReceiverInstanceClass`. No local-list single-player
transport, replacement game loop, public server or fabricated TT credentials.
The fixture checks the original request's `PS Vita` nickname, password and
current executable key; its shared-host key does not prove PC/TT compatibility.

Two reproduced failures are fixed by
`commando-a35-optional-network-modes.patch`:

- `cGameDataCnc` construction crashed in `Set_Ip_And_Port` because WOL was
  absent. A shared optional-mode query now covers game-data validation,
  client/server startup and acceptance/refusal. Registered active providers
  retain their original behavior. It does not pretend LAN/WOL is implemented.
- Disconnect immediately after acceptance crashed in
  `Client_Update_Dynamic_Objects`, before replication created `cServerFps`.
  Until that object arrives, preserve the configured client update rate;
  retain original server-FPS throttling afterward. The original goodbye
  export/delete-pending lifecycle now completes without leaking.

Three repetitions of acceptance plus all five refusal codes pass (18 sessions)
normally and under AddressSanitizer/LeakSanitizer. Original client control/FPS
objects are created on acceptance; network-object counts return to the initial
baseline after every cleanup. Both tests are retained in `run_a30_host.sh`.
Tutorial and Skirmish00 each pass two host cycles. Packet codec and rooted
config regression tests also pass. Four affected Vita ARM objects compile.
Restaging passes 214 ordered zero-fuzz patches and matches the tested sources.

Evidence: `build/host-m13-diagnostic/direct-client-before.gdb.log`,
`direct-client-after.log`, `direct-client-asan.log`,
`direct-client-{tutorial,skirmish}-regression.log`,
`direct-client-arm-{build,receiver-build}.log`, `direct-client-restage.log`,
`direct-client-stage.sha256`, `direct-client-artifacts.sha256`.

```sh
timeout 45s build/host-a30-definitions/a31_m00_interactive_runtime --direct-client-selftest
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 timeout 45s build/host-a35-asan/a31_m00_interactive_runtime --direct-client-selftest
```

Not covered: server gameplay/replication import, remote map negotiation,
TT admission, refusal UI, native UDP execution or public Internet joining.
The fixture drains server-received application packets without importing them.
Next: connect original server-info/map events and client-only load lifecycle
against a controlled server, then TT package/admission negotiation. Review
server-controlled decoding before permitting public joins. The native TLS
gate below remains open. No new VPK, installation or publication this unit;
Dev194 remains installed and physical acceptance is unchanged.

## TTFS implementation, 2026-09-24 continuation

`port/filesystem/renegade_ttfs*` now implements manifest parsing, HTTP(S)
downloads, verified isolated caches and a read-only original `FileFactoryClass`
adapter. Original file-factory ownership, case-insensitive lookup, buffered
reads, seeks and teardown are preserved. Packages do not auto-mount into
campaigns or overwrite retail data. The remote join flow is not wired yet.

Evidence comes from executing checksum-pinned official b9000 PackageEditor
against two self-created, asset-free MIX1 files, not speculative packet or
format definitions. Repeated generation yields identical manifests:

| Fixture | Manifest SHA-256 | Coverage |
|---|---|---|
| `2b1cb7bd.tpi` | `76f706f3c9585c5666756fd54b424852e60ee1c67bc06454784706116b66eba9` | text, binary, two records |
| `fb41cad5.tpi` | `eab067734444cc1911080043edd62ad93643ccef6c9d41f89ff66a5e0c51c307` | empty file, case folding, space in name, uncompressed repetitive payload, three records |

Observed layout: little-endian chunk headers (four-byte tag, uint32 size).
`DAEH` contains package ID then file count. `ATAD` contains three uint16-length
strings (name/version/author), then a metadata word observed as 2. The meaning
of that word is not established: other values fail closed. Each `ELIF` contains
CRC32, byte length, uint16-length basename. Blobs are raw bytes at
`files/%08X.basename`; manifests use `packages/%08x.tpi`. Header word two is
**not a version**: differing file counts exposed and corrected that inference.
Unknown layouts are rejected; two fixtures do not prove every TT release.

The independent native reader/downloader rejects wrong IDs, every truncated
prefix (266 cases), duplicate/unsafe names, native executable extensions,
oversized counts/files, trailing chunks, HTTP redirects and bad payload
length/CRC. Failed transfers remove only their newly created cache. Existing
caches are never overwritten. Cache validation repeats all payload checks
before mounting. CRC checks are not cryptographic authentication. Transfers
have manifest/file/aggregate caps and a package-wide deadline; HTTPS keeps
hostname/chain verification, a TLS 1.2 minimum and an explicit CA-file option.

Host HTTP fixture download -> committed cache -> original engine factory
read/seek/read-only/remount passes normally and under ASan/UBSan/LeakSanitizer.
All eleven tests pass, including HTTPS rejection of an untrusted certificate
and success with an explicitly trusted fixture CA. Normal host engine and ASan engine
builds pass. Parser/cache/factory compile in the native target; the downloader
compiles as `renegade_ttfs_download_probe`. A standalone native diagnostic
ELF also links with SDK curl/TLS/zlib (ELF32 ARM EABI5 hard-float), but is not
a runnable game or hardware acceptance.

**Native transport gate:** installed curl 8.17.0 links OpenSSL 1.0.2i-dev,
confirmed in headers, pkg-config and library strings. Do not publish this
diagnostic linkage as the production HTTPS solution. The downloader is an
explicit compile-only target, not linked into the game. Resolve a current,
license-compatible TLS backend and trust bundle, then native HTTPS tests.
No alternate TLS implementation was imported without verified reuse permission.
Original native parser/cache/factory use existing zlib, without new TLS linkage.

Reproduce the retained automated checks:

```sh
TTFS_ENGINE_PROBE=build/host-a30-definitions/a31_m00_interactive_runtime python3 -m unittest tools.test_ttfs -v
TTFS_SANITIZE=1 TTFS_ENGINE_PROBE=build/host-a35-asan/a31_m00_interactive_runtime ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 python3 -m unittest tools.test_ttfs -v
cmake --build build/vita-fast-candidate --target renegade_ttfs_download_probe -j4
```

`tools/make_ttfs_fixture.py` generates each MIX; `--edge-cases` selects the
second. `tools/run_ttfs_reference_fixture.ps1 -WorkDir <fresh-directory>`
verifies exact tool/input hashes, isolates APPDATA/LOCALAPPDATA/USERPROFILE,
runs bounded official conversions and checks output hashes. Supply only the
official PackageEditor/MemoryManager and generated MIX files to that directory.
It refuses to overwrite existing evidence. Golden manifests in `test_ttfs.py`
contain no retail assets or proprietary implementation. Reference evidence is
under managed `evidence/ttfs-484-fixture` and `evidence/ttfs-484-reproduce`.
No new VPK, installation or GitHub dev-build publication in this work unit.
Final logs under `build/host-m13-diagnostic`: `ttfs-final-sanitizer-contract.log`,
`ttfs-engine-contract.log`, `ttfs-native-download-probe.log`,
`ttfs-native-link.log`, `ttfs-arm-build.log`. M00 and Skirmish00 both pass two
fresh host cycles (`ttfs-m00-regression.log`, `ttfs-skirmish-regression.log`).
The canonical host runner now runs the complete download-to-original-factory
test, and the package test suite includes the standalone TTFS contracts.

## Implemented source candidate

- Full-port frontend retains original Skirmish selection across the native
  launch boundary, accepts original `Skirmish*.mix`/`C&C_*.mix` names without
  path traversal, links `gdskirmish.cpp`, and calls original
  `GameInitMgrClass::Initialize_Skirmish`. Demo remains excluded.
- Combat stays suspended during local handshake/loading so uninitialized
  bases cannot trigger victory. Original post-load reset, building init and
  On_Game_Begin own activation; original skirmish owns both base controllers.
- Server configs load user overrides before retail defaults and write only
  to `user/`. Missing optional INIs retain original class defaults. Failed
  writes are observable. This fixes the reproduced null-INI crash caused by
  the original raw `fopen("data\\...")` bypassing the rooted factory.
- Optional WOL rank formatting checks for the mode's existence. This fixes a
  reproduced null dereference in player-list results logging.
- Original WWNet packet CRC/IPv4/delta word reads use explicit 32-bit values
  and memcpy-safe unaligned reads. LP64 no longer writes an 8-byte CRC or
  reads beyond 4-byte IPv4 fields. Short CRC wrappers are rejected before
  hashing. Packet framing, delta compression and ownership remain original.

## Evidence and gaps

| Surface | State | Evidence / required next check |
|---|---|---|
| Original offline skirmish init/run/cleanup | passed on host | `build/host-m13-diagnostic/skirmish-final-runtime.log` and `skirmish-asan-runtime.log`: normal and ASan/LeakSanitizer, two cycles, 120 frames each, original player/base lifecycle |
| Original UDP packet codec | passed on host | `--network-selftest`: 18 loopback round trips, 577 malformed cases, delta/combo paths, independent 4-byte CRC and 2-byte header wire check; normal and ASan/LeakSanitizer |
| Config creation/persistence and map validation | passed on host | `--local-session-selftest`, isolated temporary root, retail absence checked; canonical host runner |
| Tutorial regression | passed on host | `skirmish-m00-regression.log`, two original M00 cycles |
| Changed ARM objects | passed | `skirmish-arm-objects.log`, `wwnet-bounds-arm.log`; not an ELF/VPK or runtime acceptance |
| Vita skirmish UI/gameplay | unverified | ARM objects/build plus device input, purchases, HUD, death/respawn and round-end tests required |
| Multiplayer HUD | incomplete | `a31_multihud_stub.h` still replaces original HUD; do not call skirmish feature-complete |
| Remote original cNetwork session | separate-world host join/replication passed; native adoption incomplete | Original UDP options, connection-preserving Skirmish00 load, server-owned player/soldier replication and 60 client frames pass ASan/LSan; native frontend/lifecycle still gated |
| TT 4.x negotiation / integrity checks | unimplemented | Public scripts headers expose requests, not complete wire/client implementation |
| TTFS packages | host fixture pipeline passed; native partial | reader, bounded HTTP(S) downloader, verified cache, original file-factory mount; live repository negotiation, modern native TLS and in-game joining remain unimplemented |
| RenCorner join / downloaded map / replication | unverified | No game join or server asset download attempted |
| Physical performance / gameplay | unverified | Host and Vita3K cannot establish physical acceptance |

Reproduce from active checkout:

```sh
cmake --build build/host-a30-definitions --target a31_interactive_runtime -j4
build/host-a30-definitions/a31_m00_interactive_runtime --network-selftest
build/host-a30-definitions/a31_m00_interactive_runtime --local-session-selftest
timeout 300s build/host-a30-definitions/a31_m00_interactive_runtime build/host-m13-diagnostic/retail build/host-m13-diagnostic/user build/host-m13-diagnostic/cache build/host-m13-diagnostic/mods Skirmish00.mix SKIRMISH_SMOKE
python3 -m unittest discover -s tools -p test_query_renegade_server.py -v
```

Diagnostic retail root is read-only through the original MIX/rooted factory;
all writable diagnostic state is isolated under `build/host-m13-diagnostic`.
Canonical package command remains `bash tools/build.sh`; no new package has
been produced by this source-only work. Every successful dev package still
requires Vita3K installation and authorized asset-free GitHub publication.

## Verified upstream scope

- [OpenW3D](https://github.com/w3dhub/OpenW3D/tree/89cfaaffe7d9245eb22f41882cfc0167c4d9f6d9),
  revision `89cfaaffe7d9245eb22f41882cfc0167c4d9f6d9`, GPL-3.0-or-later
  with EA terms. Inspected `Code/wwnet/socket_wrapper_posix.cpp` and
  `packetmgr.cpp`. Its long-to-int packet-word correction corroborates the
  local fixed-width patch; local memcpy reads also avoid alignment/aliasing
  assumptions. No external source tree is imported.
- [W3DHub's source announcement](https://w3dhub.com/forum/topic/449238-w3d-hub-commanding-the-future-with-the-renegade-source-code/)
  separates closed 4.x/5.x engine branches from GPL OpenW3D. OpenW3D does not
  establish current TT server compatibility; 5.x is not a Renegade replacement.
- TT 4.8.4 r9000 official archive and diff hashes are retained in
  `TT_PATCH_INTEGRATION.md`; fetch/audit repeated successfully this session.
  `DefaultConnectionAcceptanceFilter.cpp` and `ConnectionRequest.h` expose
  name/password/executable key/serial hash/version/revision admission fields.
  Some implementations call fixed Windows binary addresses. They cannot be
  linked into native ARM unchanged. `PS Vita` meets the public lexical name
  rule, but acceptance/availability on RenCorner is not proved.
- [TTFS documentation](https://www.tiberiantechnologies.org/Docs/?page=Resource+Manager+(TTFS))
  describes HTTP package repositories and `.tpi` identifiers, not a complete
  binary format or portable client. The inspected scripts archive contains
  no TTFS package/downloader implementation. Do not substitute a generic MIX
  download and call it TTFS, spoof version/integrity success, or run downloaded
  Windows DLLs. Packages must be bounded, validated and staged outside retail.

## Earlier RenCorner discovery (superseded)

[Official server list](https://rencorner.co/servers/) retrieved 2026-09-24
lists Marathon at `54.39.131.45:5001` and Snipe at `:7003`. Marathon is the
earlier target, superseded by the user's AOW endpoint above.
One `\\info\\` UDP query to `:5001` timed out after 3 seconds, with no join.
Receipt: `build/host-m13-diagnostic/rencorner-info.json`. This does not prove
the server is offline. `tools/query_renegade_server.py` limits response size,
time and count, filters the sender, and retains no player records. Three
parser tests pass. This legacy query does not establish modern TT discovery
or admission. Use the current user-supplied join endpoint; do not guess ports.

[RenCorner setup advice](https://rencorner.co/topic/13309-i-am-having-issues-getting-cc-renegade-running-on-windows-10/)
recommends TT scripts and RenList; it does not establish the currently required
revision. Follow [server rules](https://rencorner.co/renegade-rules/); no
cheats, integrity bypasses or diagnostic event injection on a live server.

Next: carry the host-tested original direct-IP provider and remote-world
lifecycle into the native frontend. Optional LAN/WOL dereferences are fixed
and controlled original-protocol joining now passes. Restore authentic
multiplayer HUD/round flow. Connect real
server repository/package negotiation to the tested cache pipeline, resolve
the native TLS gate, and verify RenCorner's endpoint/admission before the
final physical demonstration. Do not advertise a fabricated TT revision.

Additional receive audit: `Break_Packet` read declared base payloads without
checking the available datagram length; delta reconstruction lacked an input
length. A separate `wwnet-a35-receive-bounds.patch` now bounds both, including
chained headers and receive capacity. All 577 malformed-packet cases pass
normally and under ASan/LeakSanitizer. This is not a complete WWNet/bitstream
security audit. Final canonical staging passes 213 zero-fuzz patches; the
seven changed staged sources match the tested hashes. 26 focused Python
contracts and 15 lifecycle contracts pass; the added supplemental-archive
test also passes. No new native package was built.

The user's Server and Tools ZIPs were also fetched and verified against both
published MD5 and observed SHA-256, outside the repository. See
`TT_PATCH_INTEGRATION.md` for pins and reproduction. Server includes
`PackageEditor.exe`, `tt.cfg`, Windows binaries and bundled game data; Tools
includes Windows tools and `perfdocs.rtf`. Neither contains C/C++ sources.
PackageEditor has a download command and `.tpi` path strings, useful as a
bounded package compatibility reference but not proof of the binary format.
The initial inventory did not execute binaries. The continuation above runs
only pinned PackageEditor on self-created fixtures; no retail asset imported.
Its example repository is not a verified RenCorner repository.
