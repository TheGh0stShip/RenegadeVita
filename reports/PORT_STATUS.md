# Renegade Vita port status

Updated: 2026-08-16. Engineering changes use source-driven review, bounded
ownership, deterministic staging, and independent validation.

Current work: **A3.5-dev5 identity/evidence physical validation**, while the
v3.6 host resource/memory work remains subordinate to that gate. A3.2-dev1
remains frozen failed evidence, A3.5-dev4 is invalid identity evidence, and
neither is the active candidate.

Recent host diagnostics cover post-run evidence, resource-manifest deltas,
cache consistency, warning trends, and PSP2 parser fixtures. Their focused
tests and repeatability checks pass; they remain host tooling and do not read,
convert, package, or publish retail payloads. The PSP2 parser does not infer
private Sony register fields.

A3.1.4 is frozen as the first physically accepted visible original interactive
M00 baseline: geometry, original player/session/camera path, 1,226 stable
frames, and clean START exit physically passed. It remains untextured and its
right-stick input was delivered at approximately 32 times the original logical
range. See `A3.1.4-HARDWARE-CANDIDATE.md` and `../../baselines/A3.1.4/`.

`RenegadeVita-A3.2-dev1.vpk` is frozen as a failed physical-hardware checkpoint
(SHA-256 `d5b1df3a06139bc4522a4b5faba3893bd29cd4a985e98919e210d2bf507e4627`).
The returned dump and exact matching symbols establish a release-blocking
`HumanStateClass::Update_Animation` fault; physical observation also reported
stuck fire/crouch, reversed axes, perspective warp, muzzle transparency error,
and non-clean exit. Its evidence remains immutable and must not be overwritten.

### A3.5-dev5 — coherent host/ARM/VPK candidate; physical acceptance pending

The fresh canonical build passed the complete host gate, deterministic
restaging, focused observer contract (46/46), input normalization (22/22),
capture/evidence contract (24/24), renderer state (4/4), renderer lifecycle
(11/11), ASan, LeakSanitizer, and targeted UBSan routes. The final ARM closure
contains 424 original and 21 port translation units and completed 456 Ninja
build actions. A mandatory post-link verifier passed all 15 identity and
lineage checks against the exact final ELF, SELF, and VPK: the intended dev5
display/capture/log identities are present, all prohibited dev1/A3.1 strings
are absent, and packaged `eboot.bin` is byte-identical to the verified SELF.
The physical candidate is `RenegadeVita-A3.5-dev5.vpk`, SHA-256
`e69919b557b8b2a807ac6437310d4c62072635ce1a493e63eee604a0c935287c`.
This is not an A3.5 milestone acceptance claim; the player/NPC body, weapon,
door orientation, and static overhead-camera observations remain physically
unresolved.

### v3.6 — bounded host foundation in progress

The new deterministic read-only asset manifest validates the local user-owned
Data tree (51 files, required archives present, no case conflicts), and cache
key v1 deterministically binds content identity, tool/schema version, and
conversion options without converting or packaging retail data. The original
`M01.mix` path is preflighted by `MixFileFactoryClass` and then exercised by
two 120-frame original `CombatManager::Load_Level_Threaded` load/render/
teardown cycles on host. Capture schema v2 adds bounded periodic free-memory
low-water telemetry; host self-test 17/17, comparison tests 2/2, and ARM link
pass. The host-only v1 archive-index precursor also uses the original factory:
M01's 231 names are byte-identical across two writes and City has 83 names.
These are host/ARM facts only; device scene, cache, memory, storage, and
performance acceptance remain open. The complete canonical revalidation log
is `../../logs/a30-20260816-114055-host-runtime.log`: retained M00
normal/ASan/LeakSanitizer/targeted-UBSan cycles, M01 two-cycle original Combat
load/render/teardown, and City two-cycle original Combat smoke all passed. The
runner explicitly calls the cache scripts through `python3`; real M01 cache
metadata verifies valid against its manifest/options key. This adds no native
cache consumer or physical claim.

The runtime now has a bounded optional cache-index health check in the existing
`cache/` namespace. It verifies the generated M01 index schema, archive,
count, ordering, and absence of trailing data, while missing/corrupt/unsafe
indexes remain diagnostic-only and always fall back to the unchanged original
MIX factory route. The 9/9 host contract and an ARM EABI5 link passed; the
complete follow-up host gate is
`../../logs/a30-20260816-115428-host-runtime.log`. This is neither device
cache consumption nor a hardware result.

Post-freeze revalidation (2026-08-16): the complete 17-file A3.2-dev1
SHA-256 manifest and VPK archive test remain exact. The current 495-source
host closure again completed its two retail M00 cycles under AddressSanitizer,
LeakSanitizer, and targeted UBSan: each retained original campaign catalog,
Main Menu lifecycle, `GameInitMgrClass::Initialize_SP`, session/player/camera
ownership, 205/12,426/8,661 first-frame mesh/vertex/triangle telemetry, zero
rejected/unsupported submissions, and clean teardown. This is regression
evidence only; the frozen A3.2-dev1 package, its hash, and its physical gate
are unchanged.

After freezing A3.2-dev1, the direct original M00 route was brought into the
same level/session teardown order used by `CombatGameModeClass` and
`GameInitMgrClass`: `cGod::Exit`, `CombatManager::Unload_Level`, session
flush, client/server cleanup, player/team removal, and pending-network-object
drain. A missing `Return_File` in original `cNetwork::Get_Data_Files_CRC` is
now an explicit staged patch, and the no-output WWAudio boundary implements
the original cache-clear state transition required by level unload. The
HUD-enabled normal, ASan/LeakSanitizer, and UBSan two-cycle M00 runs all pass;
LeakSanitizer now reports no leaks. The un-packaged ARM A4 closure now links
after 495 build actions with SHA-256
`19925dc85bde73f645100ca61883e84442bf1f86094f18c84b143b928cd6ed9a`.
`tools/run_a30_host.sh` now repeats this path with LeakSanitizer enabled as a
canonical regression gate; its freshly rebuilt 495-action ASan target passed
the two-cycle M00 run without a sanitizer report.
The candidate's complete 17-file SHA-256 manifest and VPK integrity were
rechecked afterward and remain exact. The known VitaSDK 2-byte/4-byte
`wchar_t` linker warning remains identical to accepted A3.2-dev1; no new ABI
claim is made from this host/ARM closure.

The final canonical host gate is recorded in
`<managed-log-root>/a30-20260816-073250-host-runtime.log`.
It passes the retained A2.2 checks (19/19 bitpack, 10/10 filesystem/MIX, and
14/14 W3D), A3.0 45/45 world runtime, capture 15/15, Vita input 20/20, and
texture upload 4/4 contracts, followed by normal, ASan, LeakSanitizer, and
targeted UBSan two-cycle M00 runs. Fresh staging had exposed stale host target
link closures for original AssetManager/WW3D Font3D/Render2D symbols; those
targets now explicitly link the existing original Font3D/Render2D/Targa owners
and existing Vita surface/FreeType boundary. This changes host validation only,
not the frozen candidate.

A4 host closure restored the original Font3D/Targa/Surface/Texture path,
CombatGameMode-owned RadarManager ordering, renderer preset initialization,
and the 44-byte original Render2D dynamic vertex layout. A HUD-enabled ASan
two-cycle M00 run passed 120 frames per cycle with zero rejected/unsupported
submissions. GDB then isolated an LP64 host-only retail observer-token read:
`ScriptableGameObj::Load` read eight bytes from a four-byte serialized pointer.
The host reader now uses the existing token-width helper while the Vita ILP32
branch retains the original four-byte read. Optimized and ASan host two-cycle
runs pass. The font-provider boundary now reads the original `54251___.TTF`
(Regatta) and `ARI_____.TTF` (Arial) through the original file factory, caches
FreeType faces, and returns original `FontCharsClass` alpha-4444 glyph data.
Two optimized and two ASan memory-safety cycles rasterized both families;
Regatta produced 7x19/67-covered-pixel and Arial 12x18/60-covered-pixel
glyphs. The original `StyleMgrClass::Initialize_From_INI` now
passes twice against retail `stylemgr.ini`: the original menu and in-game font
slots are populated through the provider, not Win32 font registration. Its
UTF-16 wrapped-text byte calculation is pointer-safe on LP64 hosts. The staged
ARM closure compiled and linked 448/448 units; its un-packaged ARM executable
is SHA-256 `08204a96a72e5ecbf71147c851738ae6bbc5560f390424cf7af5d8a879a93455`.
The original 90-file WWUI pool is deterministic staging input. The original
`DialogParserClass` now compiles with DialogMgr, controller input, controls,
MenuDialog/MenuBackDrop, mouse, tooltip, and transitions. A deterministic
build-time resource boundary compiles five canonical `chat.rc` records
(main/start-SP/difficulty/splash1/splash2) into native `RT_DIALOG` bytes; its
contract passed main menu 128 (nine controls) and splash 255. The generator
sets the original `DS_SETFONT` bit before appending font data, and an
ASan-validated parser-equivalent walk verifies font skipping, DWORD alignment,
all serialized main-menu controls, and the exact canonical `FONT 8, "MS Sans
Serif"` declaration. The generator aligns the first `DLGITEMTEMPLATE` after
each variable-length font field; all five selected canonical frontend records
now pass normal and ASan parser-equivalent walks. The normal
440-unit interactive M00 host build and its two 120-frame cycles still pass.
This is not a hardware HUD or menu claim, and the frozen A3.2 VPK is unchanged.

The next original bridge, `RenegadeDialogMgrClass`, now compiles with that WWUI
frontier on host and under the Vita ARM compiler. Its Vita single-player
selection retains the original Main Menu, Start SP, options, difficulty, load,
and quit factories; unsupported WOL/LAN factories remain null rather than
being replaced. The manager's `Goto_Location` and command routes retain only
the providers available to this initial single-player path. Canonical dialog
resources are present; the separate original string-table resource boundary
and full DialogBase/control link closure remain next. This is compilation
evidence only, not a menu-runtime or hardware claim.
The isolated canonical dialog-resource contract also passed AddressSanitizer
with leak detection enabled.
`bash tools/validate_a4_dialog_resources.sh` now deterministically regenerates
those templates, runs the host contract, and ARM-compiles the provider as a
32-bit Vita EABI object without repackaging the frozen candidate.

The next authentic frontend translation unit, `MainMenuDialogClass`, now joins
that same bounded host/ARM probe. Its real single-player handlers still
enumerate practice maps and transition through original Start SP/difficulty
logic; only unavailable WOL/LAN routes are conditional. The Vita filesystem
boundary now supplies that original `FindFirstFile`/`FindNextFile` contract
from the read-only retail root with case-insensitive DOS `*`/`?` matching and
traversal rejection. Its 10-check normal and ASan contracts passed, and the
Dialog Manager, MainMenu, and enumeration source passed Vita ARM syntax
validation. This remains compile/logic evidence only: no menu code is linked
into the frozen A3.2-dev1 VPK.

The original Start-SP implementation was also traced, not recreated: its
tutorial command calls `cGod::Reset_Inventory`, `CampaignManager`, then
`GameInitMgrClass::Initialize_SP` and `Start_Game("M00_Tutorial.mix")`.
Its shared `dialogtests.cpp` now has an explicit Vita single-player
compilation boundary: the released Start-SP, Difficulty, and Quit bodies are
selected while unrelated WOL/LAN/GameSpy implementations (whose first missing
declaration is `gamechannel` → `WWOnline\RefPtr.h`) remain excluded. The
resulting 13-unit DialogMgr/MainMenu/Start-SP/Difficulty/Quit probe compiles
normally, under ASan/UBSan flags, and under the Vita ARM compiler; the
retail-root enumeration contract remains 10/10 normal + ASan. This is still
compile-path evidence, not a linked/menu-runtime or hardware claim. The A3.2
candidate hashes still match every entry in its 17-file manifest.

The original `LoadSPGameMenuClass` now joins the same bounded frontend probe.
It retains its released saved-game and map-list construction, ranking, delete,
and genuine `Start_Game` routes. The Vita file-enumeration boundary records
directory attributes and last-write `FILETIME` values while resolving only
within the approved retail/user roots. A small pointer-token bridge keeps the
original 32-bit list-control payload contract safe on LP64 host validation
without changing Vita's ILP32 representation. The expanded 16-object probe
compiled normally, under ASan/UBSan flags, and under the Vita ARM compiler;
file enumeration passed 11/11 and pointer tokens 5/5 in both normal and
sanitizer runs. This remains a compile/logic boundary: Load-SP is not linked
into, nor does it modify, the frozen A3.2-dev1 VPK.

The original `ListCtrlClass` and its embedded `ScrollBarCtrlClass`, required by
that released Load-SP dialog, now also join the probe. Its verified
compatibility surface is deliberately narrow:
the original `LVS_NOCOLUMNHEADER` style bit, page/home/end key values, and
UTF-16 `CompareStringW` three-way sort result. Three VC6 loop-scope uses are
an explicit staged portability patch, not a behavior rewrite. The 19-source
frontend probe compiles normally, under ASan/UBSan, and under the Vita ARM
compiler; its focused sort contract passes 5/5 alongside enumeration 11/11
and pointer-token 5/5. The frozen candidate VPK/ELF hashes remain exactly
`d5b1df3a…e4627` / `69a75b50…5a00` after this host-only work.

The frontier now reaches actual menu construction rather than only parsing:
the original `DialogBaseClass`, `DialogTextClass`, `ButtonCtrlClass`, and
flat-menu `MenuEntryCtrlClass` compile with the canonical Main Menu and
Load-SP dialog records. Their serialized style semantics remain original
(`WS_*`, `BS_*`, `SS_*`, and `ES_*` values); six DialogBase and one ButtonCtrl
VC6 loop-scope uses are staged mechanical portability fixes. The 23-source
probe passes normal, ASan/UBSan, and Vita ARM compilation. Its focused
contracts now total 23 checks: UTF-16 sort/integer conversion 7/7, file
enumeration 11/11, and pointer tokens 5/5. This establishes the next genuine
boundary precisely: full original control/link closure and device lifecycle,
not a replacement menu. The A3.2-dev1 VPK remains unchanged.

Preflight provenance (2026-08-15): upstream is pristine at
`3e00c3a1b97381bb28be89a35b856375e0629a08`; deterministic source inventory is
423 original translation units and 97 applied patches. The historical un-applied
WOL NAT experiment is retained but excluded from that inventory. The baseline
host harness passed A2.1 10/10, A2.2 14/14, A3.0 45/45, A3.1 two-cycle ASan,
targeted UBSan, capture 14/14, and the new controller-axis 9/9 check. Persistent
native-ext4 ccache is present (1.5 GiB; 4,361 / 5,648 cacheable-call hits at the
time of this record).

The durable program objective is **A4.0 — First Playable Campaign Slice**. It
remains active after the A3.2 hardware gate; no A4.0 gameplay implementation
will merge onto an unvalidated A3.2 foundation.

The control frontier now compiles 52/52 selected original/frontend and
single-player lifecycle units in normal host, ASan/UBSan, and Vita ARM builds. It covers the original edit,
combo/dropdown, slider, tab, tree, map, viewer, input, shortcut, merchandise,
progress, health-bar, child, menu-entry, tooltip, and transition controls in
addition to DialogMgr, MainMenu, and Load-SP. Four focused contracts pass:
ListCtrl 10/10, retail-root enumeration 11/11, pointer tokens 5/5, and canonical
dialog resources. A deliberate Vita unresolved-symbol audit found 418 unique
frontend references, with 302 absent from the frozen A3.2 ELF. Adding the
original Render2D, StyleMgr, campaign, GameMode, GameInitMgr, savegame, and
offline Bink boundary owners reduces the remaining frozen-ELF link gap to 91.
The next closure is real renderer/audio/network/resource ownership, not a
substitute menu.
This precisely defines the next authentic link boundary; it is not a
menu-runtime claim. The frozen A3.2-dev1 VPK remains unchanged. A small staged
WWMath patch also removes the VitaSDK `__fastcall` macro-redefinition warning
while retaining the original non-MSVC default-calling-convention intent.

The unchanged 440-unit original interactive runtime was rebuilt after these
boundaries and passed two in-process retail M00 cycles: each completed 120
frames, retained original session/player/camera ownership, submitted its first
frame with 205 meshes / 12,426 vertices / 8,661 triangles and zero
rejected/unsupported submissions, then tore down cleanly. This proves the
frontend boundary did not regress the existing M00 runtime; it does not enable
or claim a device menu yet.

The subsequent A4 source/link closure now selects 495 original and boundary
translation units into one host runtime. Normal, AddressSanitizer, and
UndefinedBehaviorSanitizer builds each linked, then completed two retail M00
cycles of 120 frames with the same 205 meshes / 12,426 vertices / 8,661
triangles first-frame checkpoint and zero rejected/unsupported submissions.
The same 495-unit selection now compiles and links to a Vita ARMv7 ELF against
the production VitaGL, vitaShaRK, FreeType, and platform-stub library closure
(`19925dc85bde73f645100ca61883e84442bf1f86094f18c84b143b928cd6ed9a`).
`CombatGameModeClass`, original `GameMode`, campaign, dialog, and lifecycle
owners are therefore source- and ARM-link-closed. The host still registers a
deliberately narrow M00 harness rather than executing the full
`CombatGameModeClass` virtual/menu graph: its remaining multiplayer
presentation and desktop service owners are not yet portable. This is source
closure and regression evidence only, not a campaign/menu or hardware claim.
It does not modify the frozen A3.2-dev1 candidate.

The direct route now uses original `GameInitMgrClass::Initialize_SP` to create
the single-player data/session owner and `GameInitMgrClass::Shutdown` for its
matching cleanup, rather than manually duplicating that ownership. It does not
call original `Start_Game`/`End_Game`: those functions require the complete
registered Menu/Combat mode graph, which this direct harness intentionally
does not fabricate. Normal, ASan/LeakSanitizer, and UBSan runs each reached
both `original_gameinit_sp_initialized=true` checkpoints and completed two
120-frame M00 cycles; the new ARM ELF above contains the same source boundary.

The bounded lifecycle now executes the authentic `RenegadeDialogMgrClass` and
`MainMenuDialogClass` before the existing direct M00 route: original
`MainMenuTransitionClass` ran three update/render frames with nine original
controls, then shut down cleanly. GDB exposed that the first six transition
controls had been serialized as ID 0 because `chat.rc` aliases from
`dialogresource.h` were not resolved. The deterministic generator now resolves
those source-header expressions; its contract checks the exact IDs
`11000, 11029, 11030, 1563, 11003, 11018`. Normal, ASan, and UBSan two-cycle
M00 validation and the 495-action VitaSDK closure pass. The original
`MenuGameModeClass2` now registers before the original
`Goto_Location(LOC_MAIN_MENU)` call, which itself activates the mode; the
original `GameModeManager` then dispatches three `Think` frames before safe
deactivation and removal around that real dialog lifecycle. Its
single-player staging patch excludes only the unused WOL include, retains
original `gamemenu.cpp` ownership of `g_is_loading`, and uses the existing
silent WWAudio boundary only where original menu code already accepts a null
sound effect. This is original menu lifecycle evidence only; it neither
enables nor replaces the frozen A3.2 device route.

The original campaign catalog is now exercised through the same retail
FileFactory/MIX chain before frontend construction. `CampaignManager::Init`
loads 36 `campaign.ini` flow entries in each of two in-process M00 cycles, and
its matching `Shutdown` clears the flow table before the next cycle. The
catalog contract passed normal and ASan/LeakSanitizer runs, and the current
unpackaged 495-action ARM closure is ELF32 ARM hard-float with SHA-256
`bb58ea315062b70593ade55425fe8fdc00fe72b52d11c2aa7e251ca16582d5e6`.
This proves original campaign content discovery and lifecycle only;
`CampaignManager::Start_Campaign` remains correctly withheld until the real
Combat mode graph can own its `GameInitMgr::Start_Game` transition.

The direct original M00 lifecycle now also retains `PathMgrClass` in the exact
original application position: initialize after `WWMath`, release after
`WW3DAssetManager`. A new canonical host run found that this ownership was
previously omitted, leaving one `PathSolveClass` (80,256 bytes including its
heap) after a two-cycle run. The focused M00 ASan/LeakSanitizer rerun is now
clean and ends PASS; the matching ARM runtime links the same calls. This is a
lifecycle correction, not physical-Vita evidence. Full canonical revalidation
passes at `logs/a30-20260816-122251-host-runtime.log` before the next hardware
package.
