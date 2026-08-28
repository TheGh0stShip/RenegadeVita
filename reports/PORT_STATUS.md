# Renegade Vita port status

Updated: 2026-08-28. Engineering changes use source-driven review, bounded
ownership, deterministic staging, and independent validation.

Current work: **post-dev68 original material mapper texture-coordinate state,
null texture-stage disable semantics, Vita stream-output submission telemetry,
stream restart handling, per-buffer stream-mix telemetry, active streamed-audio
telemetry, Vita DX8 bound-texture lifetime,
WWAudio stream loop-count return, streamed-dialogue fact runtime telemetry, WAVE fact-duration metadata,
streamed-dialogue duration metadata, dialogue/audio
diagnostics, texture provenance, DX8
texture surface ownership, DX8
surface-copy compatibility, DDS retained surface levels, direct mesh base-pass
replay, native stage-1 multitexture boundary, and DX8 bound-texture lifetime
for the restage-proven shared
original `LoadingScreenClass` loading path, the dev35 stack fix, dev36 camera-Y
boundary correction, dev37 DataSafe guard, dev38 loading capture metadata,
dev39/dev40 TGA loading fixes, original WWAudio/background/material/conversation
corrections, dev43 no-pullout route gate, dev45 replay-complete clean-exit
bridge, dev46 original message-window render plus dialogue/audio diagnostics,
and dev47 original TranslateDB object-factory closure. Dev48 adds a narrow
WWAudio category-volume fix by initializing dialog/cinematic volume defaults in
the Vita constructor path and logging those volumes in runtime audio
breadcrumbs. Dev49 preserves that fix, adds stream/read/decode/start/mix/output
counters for the Logan dialogue path, and changes the Vita DX8 texture boundary
to try original `DDSFileClass` lookup before loose Targa decode so `.tga`
material names can resolve retail `.dds` assets through the FileFactory/MIX
chain; that original DDS alias path is now covered by an executable host
contract. Dev50 fixes DDS descriptor metadata so original `TextureClass::Init()`
receives DX8 `D3DFORMAT` values instead of raw `WW3DFormat` values, avoiding
the DXT1/RGB888 enum collision; it also pins the documented
`/usr/local/vitasdk` default through `RENEGADE_VITASDK`, tightens vitaGL enum
detection, and extends the audio mixer/source contracts. Dev51 keeps those
source fixes and adds stream-only mix isolation counters inside the Vita Miles
provider: opened streams are tracked separately from ordinary samples, mixed
into a diagnostic accumulator, and reported as streamed buffers, frames, nonzero
buffers, peak sample, and currently active streams. Dev52 keeps those counters
and adds read-only original speech-object diagnostics from the active
conversation path: source owner, speaker presence, sound object presence, scene
membership, cull state, playing state, class/type/state, duration, dropoff
radius, and listener distance. Dev53 keeps those dialogue diagnostics and adds
texture provenance telemetry: successful DDS/TGA load counters, first-load
breadcrumbs with dimensions/format/checksum/native texture id, checkerboard
fallback bind counts, runtime `loaded_dds/tga` breadcrumbs, and capture-bundle
comparison coverage for those fields. Dev54 keeps those diagnostics and
restores the Vita DX8 texture surface boundary: texture-owned refcounted surface
levels, original `GetSurfaceLevel`, texture `LockRect`/`UnlockRect` with
writable mip uploads, priority storage, and width/height `_Create_DX8_Texture`.
Dev55 keeps that ownership and replaces the remaining
`IDirect3DDevice8::CopyRects` invalid-call stub with bounded CPU-backed surface
copies plus texture-owner uploads, and exposes fail-closed
`D3DXLoadSurfaceFromSurface` / `D3DXFilterTexture` compatibility for original
surface/mip call sites. This restores original `Render2DSentence` pending
surface-to-texture copy semantics needed by message, loading, and dialogue text
textures. Dev56 preserves dev55 and gives DDS-loaded retail textures decoded
CPU-backed `D3DFMT_A8R8G8B8` surface levels for every mip while keeping the DX8
source-format descriptor metadata from `DDSFileClass`, so original
`GetSurfaceLevel`/D3DX/`SurfaceClass` callers receive actual decoded retail
pixels instead of blank descriptor surfaces after DDS loads. Dev57 preserves
dev56 and makes the direct Vita `MeshClass` submitter replay every original
base material pass, reading pass-specific stage-0 texture, shader, UV, DCG, and
vertex material data instead of drawing only pass 0. This restores the original
multi-pass fallback shape for lightmap/detail/emissive/shiny-mask material data
that survived W3D load under the current direct mesh boundary. Dev58 preserves
dev57 and removes the stage-1 unsupported renderer gap by translating original
DX8 sampler and texture-stage combiner state for both WW3D texture stages,
binding Vita texture units 0/1, and emitting stage-1 UVs for original
post-detail materials. Dev59 preserves dev58 and fixes streamed dialogue timing
metadata by carrying decoded WAVE sample-frame counts through
`AILSOUNDINFO.samples` and computing original `SoundBufferClass` duration from
frames/rate before falling back to byte-length estimates. Dev60 preserves
dev59 and reads exact WAVE `fact` sample-frame metadata, preferring it over
estimated frame counts and trimming decoded ADPCM output to the exact frame
count before playback. Dev61 preserves dev60 and makes the WAVE
fact/estimate/untrimmed/trimmed frame decision visible in runtime audio stats
and the A3.5 audio log beside the post-trim streamed frame count. Dev62
preserves dev61 and fixes staged original `SoundStreamHandleClass` so
`Get_Sample_Loop_Count()` returns the Miles-compatible provider
`AIL_stream_loop_count` value instead of discarding it and always reporting
zero. Dev63 preserves dev62 and fixes the Vita DX8 bound texture-stage cache
so `IDirect3DDevice8::SetTexture` retains bound textures with `AddRef`/
`Release` semantics instead of storing raw potentially stale backend pointers
during retail material and checkerboard-fallback churn. Dev64 preserves dev63
and adds active-stream cursor/length/loop/volume/pan telemetry while forcing
exhausted finite streams to report zero remaining loops before stop, so Logan
dialogue logs can distinguish active but inaudible streams from stalled or
completed streams. Dev65 preserves dev64 and adds per-buffer stream-mix
telemetry (`last_stream_mix=active/frames/nonzero/peak`) so Logan dialogue
logs can prove whether the most recent active stream buffer is contributing
nonzero samples or silence. Dev66 preserves dev65 and records streamed-audio
buffers that are actually submitted successfully to `sceAudioOutOutput`
(`output_stream=buffers/frames/nonzero/peak` and
`last_output_stream=active/frames/nonzero/peak`), while rewinding exhausted
sample/stream cursors before restart so a restarted Logan dialogue stream cannot
report started and then mix silence at end-of-buffer. A full canonical
no-deploy dev66 build now passes retained host-validation reuse, deterministic
restaging, 72 host unittest checks, source integration reporting, ARM
link/package, identity verification, compressed VPK validation, diagnostics
generation, and SHA verification. The canonical VPK SHA-256 is
`99ad437fc05c9a8bde760df346816a33103875f620a605ba0fa7c9ca7a316543`.
Dev67 preserves dev66 and changes `IDirect3DDevice8::SetTexture(NULL)` to use
the Vita renderer stage-disable path for all stages. That keeps `invalid_bind`
from counting intentional stage-0 fixed-function texture disables, so the next
material/texture hardware log better separates real non-null invalid/unuploaded
texture submissions from normal D3D stage-disable traffic. A full canonical
no-deploy dev67 build now passes retained host-validation reuse, deterministic
restaging, 72 host unittest checks, source integration reporting, ARM
link/package, identity verification, compressed VPK validation, diagnostics
generation, and SHA verification. The canonical VPK SHA-256 is
`3c6279ed13db704e2416b41ff073dace7d772da20d7424541a1846017efb9403`.
Dev68 preserves dev67 and replays original `VertexMaterialClass`
texture-coordinate mapper/default UV-source state in the direct Vita
`MeshClass` path. Base-pass submissions now split when the original vertex
material changes, call the original `TextureMapperClass::Apply()` path when a
mapper exists, restore original default `D3DTSS_TEXCOORDINDEX` /
`D3DTSS_TEXTURETRANSFORMFLAGS` state otherwise, carry texture-stage transforms
through the Vita DX8 boundary texture matrix path, and emit UV arrays selected
by the original material UV source rather than assuming texture stage equals UV
array index. A full canonical no-deploy dev68 build now passes retained
host-validation reuse, deterministic restaging, 73 host unittest checks, source
integration reporting, ARM link/package, identity verification, compressed VPK
validation, diagnostics generation, and SHA verification. The canonical VPK SHA-256 is
`bccfb2e4ef99b5246331b3bb4d6c09e46364c314eedfc19b98c9fe0e236b80d8`.
Dev46 physical replay used
the retained dev43 route, returned PASS and LiveArea cleanly, and proved SFX
audio works, but all active M00 tutorial dialogue lookups returned missing
strings and sound ids (`str=0`, `sound=-1`). Dev47 fixed those lookups
(`str=1`, valid sound ids) by linking `wwtranslatedb/translateobj.cpp` and
`wwtranslatedb/stringtwiddler.cpp`, but its physical replay failed: no audible
dialogue was heard and the old route diverged/stuck because dialogue timing/
control changed. Dev68 is built but not deployed; dev46 remains restored on
device. Text-dialogue/audio acceptance, texture/material acceptance, and a
valid post-dialogue route remain pending physical evidence**.
Exact-dev6 pause passed on physical Vita.
Exact-dev7 physically proved grounding, movement, Square delivery, and an
isolated original weapon-fire path, while exposing a nondeterministic external
input-provider sequence and invisible skinned bodies. The v3.6 host
resource/memory work remains subordinate to the current visual-correctness
gate. A3.2-dev1 remains frozen failed evidence, A3.5-dev4 is invalid identity
evidence, and neither is the active candidate. Dev13 completed one matching
physical record but failed sky/material/audio/Logan-progression acceptance;
its route is retained and exact dev7 is restored. Dev15 proved provider/link
closure but left the Vita runtime in lite, uninitialized, unserviced audio mode.
Dev16 corrected that lifecycle. Dev19 physically proved Logan-to-pistol
progression but crashed after six pistol shots. Dev43 supersedes that
progression point for route/runtime only: 5,958 recorded samples, clean
lifecycle, no new PSP2DMP, `Weapon_Pistol_Player`, `fired_total=36`, unchanged
retail M00, and route SHA-256
`5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895` under
`build/device-evidence/a3.5-dev43-route-record-20260825-022835/`. Dev45
replays that route to automatic clean exit under
`build/device-evidence/a3.5-dev45-route-replay-20260825-025927/`. Dev20 through dev24 are failed
or superseded loading/replay attempts; dev24 physically proved the direct
VitaGL loading shortcut still looked wrong despite tile residency. Dev25
removed that shortcut and restored original `MenuBackDropClass` model-animation
ownership. Dev26 completed the original loading text, string, style, and status
lifecycle: `STRINGS.TDB`, `StyleMgrClass`, `Render2DSentence`,
`SaveLoadStatus`, and Campaign backdrop description parsing. Dev27 restored
original `CombatManager::Set_Load_Progress(0)` /
`CombatManager::Get_Load_Progress()` ownership and removed manual terminal
progress fractions. Dev28 supersedes it by restoring original
`loading_screen.Render(true)` behavior: loading presentation passes
`cNetwork::Update` through `WW3D::Begin_Render` instead of rendering as a
network-idle frame. Dev29 supersedes dev28 by scoping `Render2DClass` to the
original 640x480 loading logical resolution for `MenuBackDropClass` and
`Render2DSentenceClass` layout, then restoring Vita 960x544 before gameplay.
Dev30 supersedes dev29 by scoping WW3D/DX8Wrapper/Render2D together during
loading, so original `Render2DClass::Render()` and `CameraClass::Apply()` use
the same 640x480 logical viewport, while the Vita renderer scales that viewport
to the full 960x544 framebuffer. Dev31 supersedes dev30 by removing the
Vita-side loading-presenter clone and linking a shared original
`LoadingScreenClass` owner in `staging/commando/loadingscreen.cpp`; direct Vita
now constructs/renders/destroys that original owner through a narrow bridge,
so the same implementation can be reused for other original loading states.
Dev32 supersedes dev31 by making that extraction deterministic under
`tools/stage_sources.sh` through `commando-a35-shared-loadingscreen-owner.patch`
and proving it with a forced-restage fast package. Dev33 supersedes dev32 by
leaving gameplay/world UV semantics unchanged while flipping V only for original
loading-screen texture basenames beginning with `loadscreen_`, covering the
original loading W3D/DDS orientation mismatch. Dev34 superseded dev33 by
retaining that path and writing a returned loading-screen BMP/state capture at
original `level_ready`; the route runner required that capture before accepting
the user's fresh movement recording. Dev34 was deployed once for an approved
route-record attempt and crashed before the first original-runtime log; VDB
PSP2 analyzer maps the dump to `A31_Vita_Run_Interactive_Runtime()` line 605,
the function prologue, and objdump showed a roughly 276 KB stack subtraction
from stack-local `A31FrameHistory` diagnostics. Dev35 supersedes dev34 by
moving that history storage off the Vita stack, reusing one heap history for
loading/gameplay capture, and reducing the prologue stack subtraction to about
17 KB. Dev36 supersedes dev35 by changing only the Vita right-stick Y
mouse-delta default after the latest physical camera-inversion feedback, while
leaving original Input and CCamera ownership unchanged. Dev37 supersedes dev36
by fail-closing invalid `GenericDataSafeClass` list indexes in release builds:
VDB symbolicated the retained dev19 pistol-shot PSP2 dump to
`GenericDataSafeClass::Get_Entry` at `datasafe.cpp:350`, where compiled-out
`ds_assert` checks allowed `Safe[list]` to be dereferenced. Dev38 supersedes
dev37 by making the returned loading capture auditable with schema-v4 visual
gate metadata. Dev39 supersedes dev38 by proving the original retail loading
W3D uses `.tga` tiles (`loadscreen_beam.tga`, `loadscreen_cnc_1..4.tga`) and
routing those requests through the existing TGA decoder at the Vita DX8
boundary. Dev40 supersedes dev39 by matching original TextureLoader TGA
Y-origin handling and removing the loadscreen-only UV workaround from mesh and
indexed submissions. Dev46 restores the original message-window render pass
and adds audio/dialogue diagnostics; its physical replay is the current
no-dialogue diagnostic evidence. Dev47 links the missing original TranslateDB
object factories and physically proves string/sound-id lookup, but fails
audible dialogue and route fidelity. The next hardware gate requires a new
source fix and either dialogue-aware replay synchronization or a fresh route;
do not claim audible dialogue until physical output and provider counters
support it.

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

### A3.5-dev5 — visible physical M00 and movement pass; acceptance incomplete

The fresh canonical build passed the complete host gate, deterministic
restaging, focused observer contract (46/46), input normalization (22/22),
capture/evidence contract (24/24), renderer state (4/4), renderer lifecycle
(11/11), ASan, LeakSanitizer, and targeted UBSan routes. The final ARM closure
contains 424 original and 21 port translation units and completed 456 Ninja
build actions. A mandatory post-link verifier passed all 15 identity and
lineage checks against the exact final ELF, SELF, and VPK: the intended dev5
display/capture/log identities are present, all prohibited dev1/A3.1 strings
are absent, and packaged `eboot.bin` is byte-identical to the verified SELF.
The current recursive-trace build is `20260824-004956`: ELF SHA-256
`b8f0c6c6be2b9aba79000050ea2301e3700eafd7afc4e5cb174976c516e6d4c3`,
SELF SHA-256
`ec08e891087243a6a44da8db29ef80bf9c485d31a6ef1b0f27423ea9626b59b1`,
and VPK SHA-256
`0316009326b5c043edbb80f87f70792f02e9f597382f2cf0370fcc7bc675a5e6`.
Its Vita-only trace is paired with the byte-identical retained completed host
validation log; it does not claim a fresh host execution for the trace-only
change.

Physical Vita now proves that all 495 static objects load, the original loader
returns, the original player/session/camera reaches visible textured M00, and
movement/look input changes the player position. An untouched late capture at
frame 355 is visually coherent; a separate interaction run reached frame 1,321
with zero rejected submissions and zero renderer backend errors. This is not an
A3.5 milestone acceptance claim: jump/action effects, collision/grounding, and
pause remain unaccepted. Clean exit and restart/repeat now pass. Door/NPC
interaction, HUD, audio, device-memory work, and repeated-session soak remain
later milestone gates.

### A3.5-dev6 — original Combat pause physical pass

Triangle now enters the existing `INPUT_FUNCTION_MENU_TOGGLE` path and toggles
original `GameModeClass::Suspend/Resume`; START remains the proven clean-exit
control. While suspended, the direct M00 boundary continues time, input, and
local-network service, skips original Combat simulation, and preserves the last
original frame because the desktop pause-menu presenter is not linked.

Focused normal and ASan compilation passed for the changed sources, as did the
6/6 static pause contract. Canonical build `20260824-013626` completed all 456
ARM actions and passed 15/15 identity checks. ELF, SELF, and VPK SHA-256 are
`2b820d533815a135db020804b287affe6521ecc68ff8dc0602e9c7e74c4473a2`,
`293768e9d79769b9872e1ad9d472c66305310032c74727d6e08a1a444ad52360`,
and `929bdbcfbf10292f250c799faf74b254384482ddc1e8cb43d6d2b21e7f573bae`.
The VPK contains only eboot and SFO. The build reused the exact completed dev5
host log because no local retail tree was available; retail was not copied.
Matching physical evidence proves one original Combat suspend/resume pair,
stable player position across 316 paused input frames, resumed movement, zero
renderer errors, clean teardown, and stopped app state. This raises the
physical evidence gate count to 8/10 without claiming visual correctness.

### A3.5-dev7 — physical effects observation and provider isolation

The separate observation-only candidate samples the original player identity,
state, transform, velocity, health, physical-object registration and
`HumanPhysClass::Is_In_Contact`, plus original `WeaponClass` rounds/fire state
and `ActionClass` activity. It does not mutate player, physics, weapon, action,
mission, renderer, or asset state. The existing schema-3 capture comparator now
reports these gameplay fields independently.

Focused comparator, runtime-contract, hygiene, normal capture, ASan capture,
and ARM syntax checks pass. Canonical build `20260824-020540` completed all 456
ARM actions and passed 15/15 identity checks. ELF, SELF, and VPK SHA-256 are
`6063c5eb2c5136ee4376fe6dc0b3944c54ce728ff7b59af76b90ffdaf6e62e21`,
`7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5`,
and `234139c2411fed7be8f2003a15ba015bc2270608ef8e3ec5406308e5c3c1443e`.
The VPK contains only eboot and SFO. Four matching physical sessions proved
original physics registration, ground contact, movement, Square delivery,
clean teardown, and stopped app state, but the external combined route did not
deliver R in those same sessions. A separate exact-dev7 probe delivered raw R
and fired 17 original weapon rounds, isolating the remaining failure to the
external injection sequence rather than the VitaSDK/DirectInput/WeaponClass
path. User observation also found missing Havoc forearm/hand geometry and NPC
bodies while rigid attachments remained visible. Those visual defects are not
a retail-data absence signal; they share the Vita skinned-mesh submission seam.

### A3.5-dev12 — deformed skins physically pass; sky fails

The Vita backend now follows the original DX8 skin container semantics:
`MeshClass::Get_Deformed_Vertices` obtains HTree-owned animated positions and
normals, and skinned vertices submit with identity world transform. Rigid mesh
submission remains unchanged. Bounded runtime counters distinguish skin
submissions, deformed vertices, and allocation/deformation failures.

The existing DirectInput platform boundary can record or replay one version-1
raw-controller route selected by exact one-shot marker files. The route is
capped at 18,000 eight-byte samples, FNV-1a checksummed, committed through a
temporary file and rename, and replay retains live physical START as an
emergency abort. Original Input/Combat bindings and update ownership remain
unchanged. VDB input control remains available for lifecycle/input release;
recorded replay removes dependence on nondeterministic external sequencing.

Canonical build `20260824-083354` completed all 465 ARM actions and passed
identity, ELF/SELF/VPK, retail-exclusion, archive, and diagnostics-manifest
checks. ELF/SELF/VPK SHA-256 are
`cbf956dbd001ef13dd94da465ef756d69f882bcfb8b25d621045065f905dd1d0`,
`805b853e737c884acc9f590a3c5793f9ba6f32f5ff80542454919bf1d2750b99`,
and `86f08c02dab2829e9ef7e25c12983313c1eb3664d2d9a3aeebaf962ff037e284`.
The VPK contains only eboot and SFO. Post-build tool discovery passes 74/74;
the ARM symbols contain both `MeshClass::Get_Deformed_Vertices` and the Vita
skin submission/scratch path. Physical observation confirms ordinary NPC body
skins now render with zero deformation failures. The same run begins in the
authentic unarmed tutorial state and reports a black sky, so dev12 is not a
fully accepted candidate and exact dev7 was restored afterward.

### A3.5-dev13 — physical route recorded; visual/progression failure

Original Haze, Starfield, CloudLayer, sun, and moon retain their existing
dynamic indexed geometry ownership. The Vita DX8 boundary now consumes the
deferred original `ShaderClass` and stage-0 `TextureClass` immediately before
indexed submission and records bounded indexed-state applications. It does not
add a custom sky, scene graph, shader, or asset format.

Clean staging also closes the official Scripts parameter-array `new[]`/`delete`
lifetime, drains scripts queued by original object detach when teardown's
`Post_Think` is disabled, and prevents headless validation from allocating HUD
presentation icons without HUD resources. Fresh strict LeakSanitizer and
targeted UBSan complete two authentic M00 cycles, plus retained M01 and City
smokes. Canonical build `20260824-093614` completed all 465 ARM actions and all
identity, ELF/SELF/VPK, retail-exclusion, archive, and diagnostics checks.
ELF/SELF/VPK SHA-256 are
`d3b7d69e40f1968a9beda0b46312c0609d73522b8ce30799cecb169a352d8b1b`,
`5c254b8a914a603baca2c9b343bb075df58c7d05ed05448db267f2d599a14555`,
and `7f7e31b37afff79ea1ab662cd9afc5d0e366f9252be6dd236b2ac8fabdf5d63d`.
Post-build tool discovery passes 81/81. The VPK contains only eboot and SFO.
Physical record evidence under
`build/device-evidence/a3.5-dev13-route-record-20260824-144843` contains a
committed 4,537-sample route (SHA-256
`39d915e02611079b29fb43cb2ea11ede583b063745e9675efe15010c606b7cf8`),
4,507 frames, clean START exit, 37,606 skin submissions, 7,207,630 deformed
vertices, and zero skin/backend errors. The user observed wrong NPC materials,
no audio, a black sky, and a Logan cutscene after the ladder that remained
active with control disabled and did not reach the pistol grant. Indexed
submissions and state applications were exactly zero. Capture frame 4,209
corroborates the black sky and wrong material appearance. Retail M00 remained
unchanged; exact dev7 was restored and verified.

### A3.5-dev14 — original background/material correction; hardware candidate

Source tracing found two concrete platform-boundary defects. The Vita runtime
passed `false` to original `CombatManager::Pre_Load_Level`, so
`BackgroundMgrClass::Init` never constructed its original Sky/Dazzle objects;
the indexed bridge therefore could not execute. The runtime now declares world
rendering available while retaining the separate HUD-resource gate. The absent
Vita DazzleLayer is a bounded no-op, not a rejected world draw.

The Vita mesh bridge also invented RGB from vertex normals. It now consumes the
original pass-0 DCG color, or the original `VertexMaterialClass` diffuse and
opacity when DCG is absent. Original TextureClass, HTree, mesh, shader, scene,
and animation owners remain intact. Bounded first-skin telemetry records mesh,
texture, UV/DCG, and pass presence without asset payloads.

Read-only diagnostics expose the first active original conversation's name,
ID, state, action, current/total remark, and remaining remark duration. They do
not call `Stop_Conversation`, grant a weapon, or advance Mission00. The route
runner now prints the user play instruction before launch; the later status is
explicitly telemetry-ready because the former human prompt arrived after the
game was already interactive.

Deterministic 111-patch staging, focused contracts, complete 87-test discovery,
and the affected 504-action host link pass. The fresh Vita build completed all
465 ARM actions and passed ELF/SELF/VPK identity, compressed-package, manifest,
symbol, and retail-exclusion gates. Exact ELF/SELF/VPK SHA-256 values are
`0cc4b9f68967cfaef29d3927ebfd1c6791924b5c442e03f0a7c7fd5c738de8e0`,
`eda78f4f3dd57a064cb915af9cab677e3e64fc340c16ad09f0c74e6839ca6860`,
and `6528991ca58877cb159a5c57b396c84e0a29c55ffa74487e5bb22f9af3e7e0e4`.
The VPK contains only `eboot.bin` and `sce_sys/param.sfo`; no Vita filesystem
was accessed. Because the local retail link was unavailable, the package
explicitly reused dev13's matching complete sanitizer/runtime log while
freshly rebuilding the affected host and ARM targets; it does not claim a
fresh retail sanitizer execution.

The TT 4.8.4 revision-9000 reference audit is integrated; portable TT
correctness semantics were already/equivalently present in EA source, while
campaign/audio/controller/lighting engine changes remain study-only because
their public implementations are absent or platform-specific. The historical
dev14 route runner admitted the exact dev14 SELF and exact installed dev7
fallback. Dev14 was not physically replayed and is superseded below.

### A3.5-dev15 — original WWAudio/Vita-native provider linkage; superseded

The source/link closure expanded without moving game ownership into platform
code. Fifteen additional original WWAudio TUs retain definitions,
buffers, sound/scene/listener objects, callbacks, playlists, priorities,
looping, transforms, and timing. Together with the previously selected logical
audio units and AudioSaveLoad, the source report records all 20 WWAudio TUs.

The local Miles-compatible boundary provides bounded RIFF PCM8/16, Microsoft
IMA ADPCM, and Microsoft ADPCM decode; 48 kHz stereo rate conversion/mixing;
pan, volume, loop, playback rate, encoded-byte 3D seek/timing, and linear
distance attenuation; original file callbacks; and blocking Vita
`sceAudioOutOutput`. This is independently implemented platform code, not a
TT or Windows Miles import. Whole-track stream decode is capped at 64 MiB and
remains subject to v3.6 incremental-streaming and physical memory measurement.

Fresh focused tests cover PCM8/16, mono/stereo IMA, mono/stereo Microsoft
ADPCM, bounded/truncated inspection, encoded-byte timing, manual mixing, pan,
and distance. ASan/UBSan and standalone Vita ARM `-Werror` checks pass. Full
post-restage discovery passes 89/89.

The canonical run completed deterministic 113-patch staging and all 482
ARM/packaging actions. Identity 15/15, required original-WWAudio/provider
symbols, ELF/SELF/VPK, compressed-package, manifest, diagnostics, and retail-
exclusion gates pass. Source integration records 447 unique original and 26
native boundary TUs. Exact ELF/SELF/VPK SHA-256 values are
`db96d327219e77d4df99d0a2942a635eda1872b311aa0c6dceb2b2a42d2eb0c9`,
`c4d5aaa1c04d93329617a086a7f57a423ff50ad40ee510f92a37ae9f8f9bfc1f`,
and `e2036901c8edceaaee73a0bfb6d94f620476c794ab8dc94207feeb00b8ca17d3`.
The VPK contains only eboot and SFO; no Vita filesystem was accessed.

Because the local retail link is unavailable, the unchanged full M00 sanitizer
route explicitly reuses the matching retained log SHA-256
`97fc49202c76a04710964cf3939dd128329df88acc6b3005241632b69df5ec1e`.
That is not a fresh retail sanitizer claim. The changed provider has the fresh
focused/sanitizer/ARM evidence above. Source review after packaging found that
the Vita entry point still constructed `WWAudioClass(true)`, did not call
`Initialize()`, and never called `On_Frame_Update`; dev15 was never deployed and
cannot support an audible-runtime claim. Its former route admission is retired.

### A3.5-dev16 — original WWAudio lifecycle activation; hardware candidate

Dev16 makes the smallest original-lifecycle correction at the Vita boundary.
After the direct runtime installs the rooted retail/MIX chain, it creates the
original basename-stripping audio adapter, constructs `WWAudioClass(false)`,
calls `Initialize()` before engine/world setup, and refuses entry unless the
original sound scene and Vita-backed 2D/3D drivers exist. The frame loop services
`WWAudioClass::On_Frame_Update(0)` after each active render, matching original
Commando ordering, and during the intentionally suspended Combat branch. Audio
is destroyed after Combat/session/input teardown and before asset, WW3D, WWPhys,
and factory teardown. This does not move conversation timing or mission
progression into platform code.

The pinned TT 4.8.4 r9000 audit passes 5/5 portable-pattern checks, but its
607-file public scripts archive and nine-file update delta contain no WWAudio
constructor, frame-update, main-loop, or conversation implementation. No TT
implementation is interpolated; the correction restores semantics from the
authoritative EA sources. `ActiveConversationClass` still owns remark timing,
so the missing audio lifecycle is not represented as the proven cause of the
Logan hang.

The final canonical build used the retail tree at
`/mnt/d/SteamLibrary/steamapps/common/Command & Conquer Renegade` and freshly
passed M00/M01/City two-cycle host routes, ASan, LeakSanitizer, targeted UBSan,
the canonical 42-test selection, deterministic 113-patch staging, all 482
ARM/package actions, and identity 15/15. Post-build full discovery passes
90/90. The host log SHA-256 is
`d5503bf47ea37f184b268e18a3ec89101177fbbf8705538240ba033cabeda3fd`.
Source integration records 447 unique original TUs, all 20 WWAudio TUs, and 26
native boundary TUs. Exact ELF/SELF/VPK SHA-256 values are
`684f15da87bb8e2d3fcdc45d7646132cb8f0ac65ec2612c0010d0365d10b8dea`,
`4dd1f7fd4a10ee26605986c58c1aad9e63986fbbf5c91e48326c9d4a0c81169f`,
and `fa7903ba94442c7f18b554dd986d868bd90fe4dedfbcbcfc732b9f506e741a63`.
The VPK contains only `eboot.bin` and `sce_sys/param.sfo`; no Vita filesystem
was accessed.

The route runner now admits only exact dev16 SELF or exact installed dev7
fallback and retains the 4,537-sample route plus live START abort. Physical
audio, sky/material appearance, Havoc first-person meshes, original Logan
progression, clean lifecycle, and matching visual evidence remain required.

### A3.5-dev8 — native Mission00 script provider; physical pending

The original Combat `ScriptManager` now uses a native static provider composed
of the official `ScriptCommands`, `ScriptFactory`, `ScriptRegistrar`,
`ScriptImp`, and `Mission00` sources. This preserves original script
registration and attachment ownership without a Windows DLL loader or a
replacement mission system. The selected closure is 430 unique original plus
22 port translation units; only the script ABI translation units receive the
scoped compatibility compilation mode. Provenance remains the existing
pristine EA repository at revision
`3e00c3a1b97381bb28be89a35b856375e0629a08`, licensed under GPL v3 with the
repository's additional terms; no external source tree or retail asset was
imported.

The provider contract passes 4/4, the current core-tool suite passes 52/52,
diagnostics pass 29/29, deterministic zero-fuzz staging is clean, and upstream
is pristine. Canonical build `20260824-031918` completed all 463 ARM actions
and passed 15/15 identity checks. ELF, SELF, and VPK SHA-256 are
`3d4b1f56e82782d1958c9a82dd5f9f773ebd3f8046652caae4c8ecd01d9b4b21`,
`7d944a8f0fe0425007cbb22b3ea039f8c173b64c4f8f6c4dce71a5670ee02c20`,
and `86b00a0d4a07a2fde9bd1734934e9bb31bdae848a2d84da551545281ad8219ac`.
Required original create/registrar/M00 controller symbols are present. The VPK
contains only eboot and SFO; no retail data or device write occurred.

This is host/ARM/package evidence only. On hardware, dev8 must report its
provider active, a nonzero registered-script count, a nonzero attached-script
count, and `scripts_active=true`, then complete the bounded walk/look/jump/
fire/Square-action and clean-exit route. It may run only after exact dev6 and
dev7 PASS receipts. The approximately 30-second normal load is covered by a
45-second readiness timeout.

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
