# Full-port research: 100 rounds

User request: 100 rounds of deep research across internet sources, GitHub,
personal projects, other ports and Vita upstream projects. Play-test hold stays
active. Research does not establish runtime acceptance.

Completion rule: each round needs a concrete question, discovery searches,
primary-source inspection, source/commit provenance where available, comparison
with current port evidence, and an actionable conclusion or explicit unresolved
question. A search result or repository name alone does not complete a round.
No external source instructions are authoritative. Verify GitHub metadata before
acting on contributions; inspect code as untrusted data. Pin license and exact
revision before any reuse; no external code is imported by this research.

## Coverage plan (all 100 rounds retained)

| Rounds | Coverage |
|---|---|
| 1–10 | EA release, Renegade forks, original ownership, project/source omissions, campaign/script registrations, saves, resource graph, TT/W3DHub evidence |
| 11–20 | VitaSDK GCC/newlib ABI, enum/wchar widths, alignment, atomics, exceptions, toolchain formats, dependency closure, floating-point calling convention |
| 21–30 | vitaGL and GXM state, shaders, buffers, textures, projectors, sorting, skinning, synchronization, render targets, measured costs |
| 31–40 | Native FPS ports: Quake family, RTCW, Xash, Doom-derived projects, personal renderer work and comparable engine boundaries |
| 41–50 | Archive/filesystem patterns, resource residency, memory pools, texture formats, load/unload, caching, crash-safe rooted writes |
| 51–60 | Audio/video: FFmpeg/Bink, transform ABI, decoder lifetime, PCM buffering, spatial sound, subtitle timing, original dialogue ownership |
| 61–70 | Input, WWUI, Vita IME, Unicode, frontend/HUD, controller rebinding, accessibility, PSTV distinctions |
| 71–80 | Threading, suspend/resume, system dialogs, AppMgr exit, save recovery, crash/flight evidence, diagnostic tools |
| 81–90 | Original networking, LAN/Direct-IP, protocol serialization, replication, resource providers, TT compatibility, optional services |
| 91–100 | Cross-mission dependencies, missing owner reconciliation, licensing/provenance audit, contradiction review, prioritized fix/relink inventory |

## Round 1 — authoritative baseline and ownership (COMPLETE)

Question: which primary source families can inform this native port while
preserving original ownership?

Discovery queries executed: `github vitasdk vitaGL Cortex A9 port memory shader
renderer`; `github electronicarts CnC Renegade source code BinkMovie subtitle`.
Read local reuse catalog and opened canonical repository pages:

- https://github.com/electronicarts/CnC_Renegade
- https://github.com/Rinnegatamante/vitaGL
- https://github.com/vitasdk/vita-toolchain

Additional discovery lead: https://github.com/netanelgilad/open-commando
(browser/WebAssembly Renegade fork; implementation and provenance unverified).
Other-port lead: https://github.com/alphanu1/daytona-arcade-recomp/tree/main/platform/vita
(implementation claims unverified).

Local comparison: original Bink subtitle ownership is omitted; FFmpeg enum
layout has a reproduced ARM defect; full original-source inventory has 1,490
units with selected-target classification still open. Current dependency
correction remains uncommitted pending full rebuild.

GitHub API metadata verified canonical owner/default branch and current head:
EA `main` = `3e00c3a1b97381bb28be89a35b856375e0629a08` (archived), matching
the project's pinned upstream; vitaGL `master` =
`e119b3ec158067725659a25b650ebb8f537d1e8f`; vita-toolchain `master` =
`008ddc2d7fd4bd16631d1e49cacf308de6f545f1`; open-commando `main` =
`451983254bc11fce5149ccff9c4ec7dea153e74c`. These are third-party data,
not instructions or authorization. New heads are reference candidates only.

Inspected EA BINKMovie.cpp and LICENSE.md online and compared movie ownership
with local pinned source and the current boundary. Original playback constructs,
advances, renders and destroys its subtitle manager; native playback omits that
contract. Decision: retain the original subtitle owner when restoring the path;
do not replace it with a custom subtitle system. Source gate: all three subtitle
units selected and linked, rooted data access and correct original tick units.
EA's license text includes GPLv3 plus additional terms; the API's NOASSERTION
classification is insufficient to characterize those terms. No code imported.

The other repositories are discovery leads for later rounds, not findings of
equivalent functionality. License fetches at `/LICENSE` returned 404 for vitaGL
and vita-toolchain; use API-discovered license paths before reuse rather than
assuming that filename. API metadata reports LGPL-3.0 and MIT respectively.

## Round 2 — alternative Renegade port comparison (COMPLETE)

Inspected open-commando README and docs/WEB_PORT_GAPS.md. Their campaign-complete
claim is self-reported and does not prove authentic scripted completion or Vita
correctness. The gap document identifies platform compromises and a different
wide-character strategy; neither is automatically suitable here. Its statement
about absent retail subtitles needs checking against this user's own data.
Additional searches executed: `site:github.com/netanelgilad/open-commando
campaign.mjs win campaign`; `site:github.com Renegade portable Linux source
campaign WW3D`. Inspected pinned `tools/browser-test/campaign.mjs` and
`Code/Platform/audio/mss_openal.cpp` at revision
`451983254bc11fce5149ccff9c4ec7dea153e74c` (owner verified in round 1).

Finding: the campaign script triggers a debug win per mission, skips movies,
and advances the score flow. Its playable-state waits can expire without a
failure assertion. It is useful as transition-smoke design evidence; it cannot
prove natural objectives, mission sequences or full authored campaign play.
Action for this port: preserve a separate natural-completion acceptance gate
for every mission, independent of any debug-win/scene-load checks. Do not reuse
the external campaign-complete claim as evidence of our missing source closure.

The inspected audio implementation stores a sample effects level without an
active reverb send. It also uses OpenAL, unlike our native Miles boundary.
Decision: study interface coverage only; no backend adoption or source copying.
Open question carried into audio rounds: compare every required Miles function
against original callers, including effects and sample offset units.

Primary pinned sources:
- https://github.com/netanelgilad/open-commando/blob/451983254bc11fce5149ccff9c4ec7dea153e74c/tools/browser-test/campaign.mjs
- https://github.com/netanelgilad/open-commando/blob/451983254bc11fce5149ccff9c4ec7dea153e74c/Code/Platform/audio/mss_openal.cpp

## Round 3 — audio effects ownership and Vita output (COMPLETE)

Question: does a linked effects setter establish original 3D audio coverage?
Searches: `site:github.com vitasdk audio reverb sceNgs voice port` and
`site:github.com electronicarts CnC_Renegade AIL_set_3D_sample_effects_level reverb`.
Inspected pinned EA `Code/WWAudio/Sound3D.cpp` and current VitaSDK audioout.h,
then compared staged original callers with `renegade_miles_provider.cpp`.
The first EA fetch used incorrect filename casing and returned 404; corrected
`Sound3D.cpp` resolves. Preserve case-sensitive provenance in the inventory.

Original Sound3D sends the WWAudio effects level when configuring its sample.
Our provider discards it. Original Sound3D and Listener also call orientation,
and Sound3D sends velocity; both corresponding provider functions are empty.
These are confirmed interface coverage gaps, not proof that every content path
audibly depends on them. Determine selected provider capability and original
defaults before choosing a bounded implementation. Do not claim a full 3D
provider merely because its symbols link.

VitaSDK's output interface accepts mixed PCM and exposes output configuration;
its named output effects are not evidence of a per-source EAX reverb graph.
Decision: preserve WWAudio ownership and investigate mixer/provider semantics
separately from PCM delivery. No speculative replacement backend adopted.

Primary sources:
- https://github.com/electronicarts/CnC_Renegade/blob/3e00c3a1b97381bb28be89a35b856375e0629a08/Code/WWAudio/Sound3D.cpp
- https://github.com/vitasdk/vita-headers/blob/master/include/psp2/audioout.h

Discovery leads (not reused or verified solutions): `maci0/openmiles` API-status
and source, VitaSDK SoLoud sample, `floooh/sokol` Vita audio output backend.
Exact revisions, licensing and implementation checks remain for later rounds.

## Round 4 — listener-space ownership (COMPLETE)

Question: should native stereo apply a second listener orientation transform?
Searches: `site:github.com/Rinnegatamante/vitaQuake listener orientation sound
spatial audio`; `site:github.com/maci0/openmiles AIL_set_3D_velocity_vector doppler`.
Opened pinned EA Listener.cpp and inspected original Sound3D transform/velocity
owners alongside native provider enumeration, position/pan and distance mixing.

Finding: Sound3D takes the inverse listener transform, converts source position
into listener space and then remaps axes before passing it to Miles. Listener
initialization sets position zero and a fixed forward/up basis. Our advertised
provider is `Vita Native Stereo`, and pan is calculated from those transformed
positions. Decision: do not add camera rotation at the provider; that would
duplicate original ownership. An ignored fixed listener basis is not itself
evidence of broken camera-relative panning. Source direction/cones, velocity
and effect semantics remain distinct open coverage questions.

OpenMiles search results suggest another implementation comparison, but no
source or license from it is adopted. Quake search results did not provide
enough implementation evidence to justify an audio change.

Primary source:
https://github.com/electronicarts/CnC_Renegade/blob/3e00c3a1b97381bb28be89a35b856375e0629a08/Code/WWAudio/Listener.cpp
and the pinned Sound3D.cpp from round 3. Local evidence:
`Sound3DClass::Update_Miles_Transform`, `Listener3DClass::Initialize_Miles_Handle`,
`Apply_3D_Position_Locked` and the native provider enumeration.

## Round 5 — native PCM lifetime and shutdown (COMPLETE)

Question: should a small Vita output backend replace our buffer ownership?
Searches: `site:github.com/floooh/sokol sokol_audio.h VITA sceAudioOutOutput`;
`site:github.com/vitasdk/samples audio sceAudioOutOutput buffer`.
GitHub API verifies owner `floooh`, default-head revision
`e7a48ed6251543eae8c5677f1cbe5fa4b2557573`, license metadata Zlib.
Inspected sokol_audio.h's Vita callback/init/shutdown and compared with the
VitaSDK output contract, our Miles output thread and Bink audio thread.

Sokol runs output on a pthread, converts its float stream to PCM16, uses BGM,
and joins its worker before freeing storage. It uses a single PCM output buffer.
Our boundary instead alternates two aligned blocks and explicitly drains the
final output pointer before thread-local storage is destroyed. Both native
Miles and Bink paths use that shared lifetime helper. Decision: retain current
ownership; this external design does not justify weakening it. No code copied.

Action retained: verify shutdown/join order and negative-output handling in
every native audio owner. Source comparison is not evidence of glitch-free
playback, queue timing or physical suspend correctness.

Primary source:
https://github.com/floooh/sokol/blob/e7a48ed6251543eae8c5677f1cbe5fa4b2557573/sokol_audio.h
(Vita backend). Local evidence: `RenegadeAudioOutputBuffers`, Miles
`Output_Thread`, and Bink audio thread. License contents/file notices need
inspection before any future reuse; API metadata alone is not a reuse approval.

## Round 6 — newlib heap versus graphics pools (COMPLETE)

Question: does another port's heap constant establish a safe Renegade budget?
Searches: `site:github.com/vitasdk/samples newlib_heapsize_ctrl _newlib_heap_size_user`;
`site:github.com/Rinnegatamante/vitaRTCW _newlib_heap_size_user`;
`site:github.com/vitasdk/newlib "_newlib_heap_size_user" "heap"`;
`site:github.com/Rinnegatamante/vitaGL "vglInitExtended" "ram"`.
Inspected the primary VitaSDK heap-control sample and compared native main,
SFO configuration and renderer free-pool logging. Sample uses the user heap-size
symbol and explicitly notes the tradeoff with allocations outside malloc.

Our source reserves 192 MiB for newlib and requests ATTRIBUTE2=12; graphics
uses a separate pool. Decision: another project's 128/192/256 MiB constant
does not establish sufficient space for our scene/decoded-audio/texture mix.
Retain separate heap, user RAM, CDRAM and contiguous-memory accounting, plus
failure checks at pool creation. Do not raise the heap from search results.
The current main comment about graphics capacity without extended memory is
an assumption requiring verification, not a closed resource gate.

Primary source inspected:
https://github.com/vitasdk/samples/blob/master/newlib_heapsize_ctrl/src/main.c
(moving branch; pin before reuse). No external code imported. Additional
personal-port packaging and heap claims discovered in search remain leads,
not validated platform requirements. Next pool round must inspect actual
vitaGL allocation code and matching SELF memory settings before recommending
any budget or packaging change.

## Round 7 — vitaGL pool sizing and version drift (COMPLETE)

Question: what does the RAM reserve argument actually reserve?
Searches: `site:github.com/Rinnegatamante/vitaGL "vglInitExtended" "ram_threshold"`;
`site:github.com/Rinnegatamante/vitaGL "VGL_MEM_RAM" "sceKernelGetFreeMemorySize"`.
Inspected upstream vgl.c and mem_utils.c at
`e119b3ec158067725659a25b650ebb8f537d1e8f` and local staged dependency code.
Owner/revision metadata was verified in round 1; file notices state LGPLv3-or-later.

In the local ordinary-app path, requested graphics RAM is current free user RAM
minus the threshold, or zero when below threshold. The other pools have distinct
thresholds. The wrapper leaves common-dialog memory reserved. Allocation also
has an uncached-RAM cap and alignment requirements. Decision: keep total/free
pool telemetry separate and treat the reserve as outside-pool headroom, not a
guaranteed malloc allocation. Do not adopt constants from search snippets.

Upstream now uses `VGL_MEM_PHYCONT` where our dependency uses `VGL_MEM_SLOW`.
This is concrete API drift: do not upgrade vitaGL or apply current-head examples
without adapting and validating the installed API. A `git rev-parse` inside the
extracted dependency resolves to the enclosing project, not dependency provenance;
use its builder pin and file hashes instead. No external source copied.

Sources:
- https://github.com/Rinnegatamante/vitaGL/blob/e119b3ec158067725659a25b650ebb8f537d1e8f/source/vgl.c
- https://github.com/Rinnegatamante/vitaGL/blob/e119b3ec158067725659a25b650ebb8f537d1e8f/source/utils/mem_utils.c

Next: audit init-result semantics and individual pool-allocation failure paths;
do not infer graphics readiness from a boolean or a requested pool size.

## Round 8 — graphics init boolean semantics (COMPLETE)

Question: can callers treat a false vitaGL init return as initialization failure?
Searches: `site:github.com/Rinnegatamante/vitaGL "vglInitWithCustomSizes" "return"`;
`site:github.com/Rinnegatamante/vitaGL "resolution" "fallback" "GL_TRUE"`.
Search results were mostly unrelated; inspected actual pinned source instead:
https://github.com/Rinnegatamante/vitaGL/blob/6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5/source/vgl.c
and the local dependency's allocation implementation.

Finding: ordinary completion returns `res_fallback`, initially false and set
when display resolution falls back. The already-initialized branch also returns
false. This is not a generic success boolean. Current renderer logging correctly
names it `resolution_fallback`; do not invert it into an error condition based
on another project's report. Individual allocation/map/context failures still
need their own evidence and checks, especially in builds skipping error checks.
Decision: retain current interpretation and track pool failures separately.
No code imported. This closes the research question, not graphics acceptance.

## Round 9 — distinguish host harness omissions from native omissions (COMPLETE)

Question: does the dev246 host link failure prove missing native engine owners?
Searches for EA `PointGroupClass::_Init` and
`Does_Animation_Have_Embedded_Sounds` returned no indexed matches; opened pinned
pointgr.cpp directly and traced staged original callers and both build graphs.

Native manifests already select pointgr.cpp, animatedsoundmgr.cpp and
statistics.cpp. Render-target cleanup is defined in a31_gameplay_boundary.cpp.
The retained A22 host target lacks these owners; its source set is intentionally
smaller and currently stale against shared source dependencies. Decision: label
the failure host harness closure, not a discovered Vita omission. Repair that
graph with explicit ownership/profile boundaries; do not remove original calls
or add native no-ops to make this host target link. The larger host harness
already maintains per-target statistics additions and optional audio closures;
these are comparison evidence, not automatic approval to copy every stub.

Action: reconcile A22 additions, native-owner selection and the headless
render-target seam before resuming canonical validation. Source-list presence
still needs eventual native compile/link evidence. Primary reference:
https://github.com/electronicarts/CnC_Renegade/blob/3e00c3a1b97381bb28be89a35b856375e0629a08/Code/ww3d2/pointgr.cpp

## Round 10 — registration-only source closure (COMPLETE)

Question: why can a linked image still miss mission behaviors?
Searches: EA repository `ScriptRegistrar Mission01` and
`SimplePersistFactoryClass`. Search results mostly repeat this port's own
reports, so they are not independent corroboration. Opened pinned upstream
ScriptFactory.cpp and ScriptRegistrar.cpp and compared staged constructors,
the DSP collector and native campaign list.

Original ScriptFactory construction registers the factory with ScriptRegistrar.
Thus absence of direct calls to a mission unit cannot justify excluding it.
Our DSP collector selects 44 original units while replacing DLLmain at the
platform seam, checks duplicates and inventory count, and verifies all 13
campaign units belong to that selection. Decision: retain direct source
selection and require defined factories plus registration/binding coverage;
ordinary unresolved-symbol success alone does not prove mission closure.
Carry the same owner check into persist-factory inventory. No code imported.

Primary sources:
- https://github.com/electronicarts/CnC_Renegade/blob/3e00c3a1b97381bb28be89a35b856375e0629a08/Code/Scripts/ScriptFactory.cpp
- https://github.com/electronicarts/CnC_Renegade/blob/3e00c3a1b97381bb28be89a35b856375e0629a08/Code/Scripts/ScriptRegistrar.cpp

Local evidence: cmake/RenegadeScriptSources.cmake, campaign subset checks in
CMakeLists.txt. Source closure is distinct from runtime factory registration,
retail attachment resolution and natural mission completion; those stay open.

## Round 11 — enum ABI and dependency boundaries (COMPLETE)

Question: can the transform sentinel be fixed by changing only its caller?
Searches: GCC `-fshort-enums binary compatible`; ARM abi-aa `Tag_ABI_enum_size`.
Inspected GCC code-generation documentation and Arm's 32-bit build-attribute
definitions, then compared actual ARM output from the corrected FFmpeg build.

GCC documents binary incompatibility when enum modes differ. Arm attributes
distinguish small enum containers from 32-bit intent independently of VFP call
attributes. Our new bink.o reports ARMv7 Application, int-sized enums and VFP
register arguments. The retained compile probe still rejects the default mode
and accepts explicit int enums. This proves the new object settings, not all
archives or the full caller boundary. The earlier attempt to inspect new tx.o
found no object yet; do not substitute its previous-build attributes.

Decision: keep matching dependency/caller flags, stale-stamp rejection and
compile assertions; inspect every final archive and Bink object before closing
the ABI gate. Do not globally change original engine enums or suppress linker
ABI diagnostics to bypass this audit. Corrected dependency build remains live
as session 42273; no second builder started.

Primary references:
- https://gcc.gnu.org/onlinedocs/gcc/Code-Gen-Options.html
- https://github.com/ARM-software/abi-aa/blob/main/addenda32/addenda32.rst

## Round 12 — wchar ABI versus libc string interfaces (COMPLETE)

Question: does compiling engine text as UTF-16 make libc wide APIs compatible?
Searches: GCC `-fshort-wchar binary compatible`; newlib `wchar_t wcslen sizeof`.
Read GCC's warning and newlib's documented wide API, then inspected actual
installed libc archive attributes: `Tag_ABI_PCS_wchar_t: 4`. Engine builds use
short wchar. Existing compatibility helpers and exported string wrappers
therefore remain necessary; do not forward engine UTF-16 pointers directly to
the unadapted library. Current short-wchar source checks cover selected string
calls, not all numeric conversion or locale APIs.

New integration lead: original subtitleparser.cpp calls wcstoul for time fields.
No wcstoul adapter was found in a31_miscutil_boundary.cpp or win32_compat.h.
Restoring that parser must close its numeric conversion boundary as well as
linking the missing units. Treat it as a source-integration dependency, not a
currently executing Vita failure. No global wchar or disk-layout change adopted.

Primary references:
- https://gcc.gnu.org/onlinedocs/gcc/Code-Gen-Options.html
- https://sourceware.org/newlib/libc.html

## Round 13 — floating-point calls versus hardware support (COMPLETE)

Question: does Cortex-A9/NEON alone establish dependency call compatibility?
Searches: GCC ARM Options `mfloat-abi hard softfp link-compatible`; Arm AAPCS32
`VFP registers parameter alignment`. Read GCC's ARM options and Arm's procedure
call descriptions. Hardware instructions and argument-passing convention are
separate contracts; variadic calls also require their own ABI treatment.

Local compiler macros report ARM architecture 7, 4-byte pointers and
`__ARM_PCS_VFP=1`. Built vitaGL vgl.o reports ARMv7 Application, VFP register
arguments and 8-byte stack alignment requirements/preservation. The corrected
FFmpeg bink.o has the same VFP calling attribute (round 11). These observations
support those objects only, not a blanket claim about every archive member.
Decision: retain hard-float consistency checks across dependencies and audit
assembly/variadic seams separately; do not infer them from `-mfpu=neon`.

The skill artifact inspector currently prints ELF headers but not attributes;
ELF machine/class alone is insufficient. Candidate review must retain `readelf
-A` output in addition to `-h`. No dependency settings changed in this round.

Primary references:
- https://gcc.gnu.org/onlinedocs/gcc/ARM-Options.html
- https://github.com/ARM-software/abi-aa/blob/main/aapcs32/aapcs32.rst

## Round 14 — alignment and serialized layout (COMPLETE)

Question: can ARM unaligned-access support replace explicit wire-layout checks?
Searches: GCC ARM Options `munaligned-access packed structures`; Arm AAPCS32
`composite alignment packed`. Read compiler and ABI descriptions, then inspected
the native beacon decoder and original chunk read boundary. Compiler-generated
unaligned accesses do not excuse arbitrary typed-pointer casts or establish
portable struct layouts. Aggregate alignment and ABI passing remain separate.

Local LanBeacon asserts its 76-byte size and four field offsets, receives into
a byte buffer and copies into its record after an exact-length check. Chunk
headers are read into owned header storage. These are specific examples of
bounded layout handling, not proof of every packet/save record. Decision:
preserve explicit widths, layout assertions and byte-safe admission; do not
globally pack engine structs to match disk or wire data. Continue per-record
review and ARM compilation in the complete inventory.

Primary references:
- https://gcc.gnu.org/onlinedocs/gcc/ARM-Options.html
- https://github.com/ARM-software/abi-aa/blob/main/aapcs32/aapcs32.rst
Local evidence: renegade_network_provider.cpp and staged wwlib/chunkio.cpp.
No new alignment defect was established in these inspected records.

## Round 15 — allocation containment and ARM unwinding (COMPLETE)

Question: is a catch block sufficient when surrounding frames lack unwind support?
Searches: GCC `-fexceptions unwind`; Arm EHABI32 exception handling unwind tables.
Read GCC exception guidance and EHABI descriptions, then inspected the native
target's default exception flags, scoped audio overrides and decoder code.

Native target defaults to no exceptions, with scoped exceptions enabled for
the retained audio failure boundary. The wave decoder catches bad_alloc and
length_error; other provider objects use nothrow. These choices must retain a
valid same-thread unwind path. A handler alone cannot recover across arbitrary
frames lacking required unwind support. No global exception-policy change is
justified by this research.

New lead: Bink boundary uses vector growth while remaining under the default
exception policy. Audit bounded sizes, allocation-failure admission and cleanup
for those decode/ring/prefetch paths rather than assuming audio containment
covers movies. Verify matching ARM unwind sections and actual source options
when the native candidate compiles. This is a coverage lead, not a reproduced
Bink allocation crash.

Primary references:
- https://gcc.gnu.org/onlinedocs/gcc-7.2.0/libstdc++/manual/manual/using_exceptions.html
- https://github.com/ARM-software/abi-aa/blob/main/ehabi32/ehabi32.rst

## Round 16 — loader completion publication (COMPLETE)

Question: does volatile or a zero handle alone safely publish loaded state?
Searches: GCC `__atomic acquire release memory model`; POSIX `pthread_join
memory synchronization`. Read GCC builtin documentation; the Open Group join
page returned 403, so no claim is based on reading that page.

Staged ThreadClass publishes `running=false` with release, clears ThreadID,
then publishes handle zero with release as its last object access. Stop polls
that handle with acquire. Running queries use acquire too. This preserves
publication and object-lifetime ordering rather than relying on volatile.
Decision: retain that existing correction; do not remove atomic operations as
a host-only optimization. Audit cancellation/cooperative stop and retained
worker resources separately; this source check does not prove bounded stop
latency or full thread join semantics.

Primary reference:
https://gcc.gnu.org/onlinedocs/gcc/_005f_005fatomic-Builtins.html
Local sources: staged wwlib/thread.cpp and thread.h, selected thread-completion
patch and the focused publication contract. No new synchronization change.

## Round 17 — clock units and original timer width (COMPLETE)

Question: can the original millisecond timer be replaced with an arbitrary
64-bit microsecond counter? Searches: Microsoft timeGetTime wraparound;
VitaSDK sceKernelGetProcessTimeWide microseconds. Microsoft's API contract uses
DWORD milliseconds and wraps at 2^32. Vita's process-time API exposes a distinct
wide source. Original timer interfaces must preserve their units and widths;
diagnostics may retain wider timestamps separately.

Local QueryPerformanceCounter explicitly scales the Vita clock to nanoseconds,
matching its declared frequency rather than leaking raw microseconds into that
interface. Decision: review timers by API contract; do not globally widen engine
time fields or reinterpret saved/network timestamps. Existing file-time checks
are not evidence of tick-wrap handling. `unittest` found zero cases in the
standalone file-time script; pytest is unavailable. Those attempts close no
timer gate. Further wraparound counterexamples remain an implementation audit
item, not a demonstrated new runtime defect.

Primary references:
- https://learn.microsoft.com/en-us/windows/win32/api/timeapi/nf-timeapi-timegettime
- https://github.com/vitasdk/vita-headers/blob/master/include/psp2/kernel/processmgr.h

## Round 18 — archive extraction versus section retention (COMPLETE)

Question: can KEEP or a successful link compensate for unselected registrar units?
Searches: binutils ld `gc-sections KEEP init_array archive extraction`; CMake
`TARGET_OBJECTS object library static registration`. Read ld's KEEP and garbage
collection documentation and compared direct executable source selection.
Our original script list is supplied directly to the executable rather than
hidden behind ordinary archive extraction. Retain that design. Section retention
and archive-member selection are separate checks; neither proves the factories
actually registered. Inspect final constructor references/map/symbol inventory
when native linking resumes. No linker flag change adopted.

Primary reference:
https://sourceware.org/binutils/docs/ld/Input-Section-Keep.html
and https://sourceware.org/binutils/docs/ld/Options.html

Dependency follow-through: corrected FFmpeg build session 42273 completed.
readelf over all five archives found only int enum and VFP-register-call values
among emitted attributes. Some members omit enum attributes, so this is not
a claim every member declares them. Caller integration found the target's
small-enum assertion would reject the scoped Bink ABI. Added an explicit
source-local macro and alternate int-enum assertion; ARM syntax probe and
three existing target checks pass. Full Bink compilation remains pending.

## Round 19 — source-specific build options (COMPLETE)

Question: are the intended boundary options present in the actual compiler command?
Searches: CMake `COMPILE_OPTIONS source file full path directory scope` and
`COMPILE_DEFINITIONS source property`. Read official source-property documentation.
Configured the existing dev246 native build directory with compile-command
export, inspected Bink's generated command and compiled its exact Ninja object.
Configure and ARM compilation both pass. The command includes the isolated
FFmpeg enum definition and `-fno-short-enums`; compile-time assertions pass.

Decision: use generated commands and object evidence rather than source-text
checks alone for scoped ABI options. Corrected dependency archives and actual
Bink caller now compile consistently. Full native linking/package gates and
canonical host harness repair remain open. No gameplay launch or acceptance.

Primary reference:
https://cmake.org/cmake/help/latest/prop_sf/COMPILE_OPTIONS.html
Native evidence: build/vita-a35-dev246-candidate-20261104-143651/compile_commands.json
and its a4_binkmovie_boundary.cpp.obj, successful Ninja session 71004.

## Round 20 — dependency cache identity (COMPLETE)

Question: does an ABI version stamp also prove the dependency matches the compiler?
Searches: ccache `compiler_check content header hashing`; CMake `imported library
full path dependency rebuild`. Read official ccache identity documentation and
compared the FFmpeg script's early return, optional cache key and configure gate.

The version bump and CMake gate reject the old enum build. Optional dependency
cache keys include script, archive, compiler-driver identity and SDK information.
However, the earlier installed-prefix shortcut checks only configuration ID and
archive existence. A compiler/SDK change with an unchanged ID can bypass that
richer key. Decision: record this as an open provenance-hardening item; do not
claim the version stamp verifies every input. Future correction should compare
a retained complete recipe/toolchain identity even on installed-prefix reuse.
No global cache disabling or unmeasured rebuild-policy change adopted.

Current rebuilt library hashes retained here:
- avcodec: a51045a1666d3d72d419eafffb43e7a4ee9a036a404d6f381b913f3db3c79cfc
- avformat: 8e714cedbfd23eda2cfed74f7dadcf0cda23a69bedb105484259cb0aeb3f637d
- avutil: 90ceb1588aa3f56542d76da2d1e5812b6731c11d0502e8a0f113242201d8fc39
- swresample: f7fa536e48c93fb6b14386ac5bec43e7ba99c9461c8269473505bd248e28560e
- swscale: 1b4753b26b9af73882951edd2b4cd3590a666b3da3549001af5f2b31338b6a1b

Primary reference: https://ccache.dev/manual/latest.html
Local evidence: tools/build_ffmpeg_bink_vita.sh and dependency_cache.sh.

## Round 21 — texture replacement and cached binding ownership (COMPLETE)

Question: is in-place texture updating automatically safe or cheaper on Vita?
Searches: vitaGL `glTexSubImage2D sceGxmFinish texture`; vitaGL `glBindTexture
texture state`. Inspected pinned textures.c and local DX8 upload boundary.
For recently used textures, the normal subimage path allocates replacement
storage, copies old contents, updates the requested region and defers old
texture-data release; a separate
speedhack conditional changes this behavior. Do not treat the API name alone
as proof of an in-place update or free bandwidth.

Our direct upload sites invalidate the renderer texture-state cache around GL
binding mutation. Decision: preserve that invalidation contract and deferred
GPU ownership. Do not enable noncompliant texture speedhacks or replace storage
with direct writes without measured evidence and synchronization correctness.
Local dependency already omits the old-pixel copy for a narrowly checked full
aligned RGBA replacement while retaining replacement allocation and retirement;
account for that selected patch before claiming a new copy-removal opportunity.
Follow-up: compare dynamic font/movie usage with this allocation cost; distinguish
texture contents from sampler/binding state in the renderer inventory.
Search leads about other ports' direct writes remain unverified examples.

Primary source:
https://github.com/Rinnegatamante/vitaGL/blob/6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5/source/textures.c
Local sources: ww3d_dx8_boundary.cpp, pinned textures.c, build_vitagl_demo.sh.
No code copied or renderer optimization adopted.

## Round 22 — projector framebuffer ownership (COMPLETE)

Question: does FBO support alone restore original dynamic projectors?
Searches: vitaGL `glFramebufferTexture2D glDeleteTextures framebuffer`; EA
`Set_Render_Target TexProjectClass`. Inspected pinned vitaGL framebuffers.c,
original staged texproject.cpp and native DX8 target construction/binding/free.

Original TexProject retains its target and renders through DX8Wrapper, then
returns to the default target. Native boundary validates level-zero render
surfaces, retains surface/texture owners, and provides shutdown restoration.
Texture objects own FBO/depth cleanup; allocation checks framebuffer completeness.
Decision: preserve original projector orchestration and target ownership rather
than draw projectors in an independent renderer. Source wiring is present;
this does not establish correct projection, depth, orientation or shadows.

Open failure-path lead: default-target restoration is fallible, but the caller
continues releasing retained target references and clearing IsRenderToTexture.
Inspect Restore_Default_Render_Target's actual failure conditions before deciding
whether that path needs state-preserving recovery. Do not claim a reproduced
GPU lifetime error from source suspicion alone.

Primary reference:
https://github.com/Rinnegatamante/vitaGL/blob/6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5/source/framebuffers.c
Local evidence: texproject.cpp, a31_gameplay_boundary.cpp and ww3d_dx8_boundary.cpp.
No external code copied or render ordering changed.

## Round 23 — default-target restore failure transaction (COMPLETE)

Question: does the round-22 failure lead have a concrete state inconsistency?
Searches: Khronos `glDeleteFramebuffers currently bound framebuffer zero` and
`glBindFramebuffer errors framebuffer zero`. Compared ES specification behavior,
pinned vitaGL framebuffer deletion and native restore/caller implementation.

Confirmed: restore returns before resetting dimensions/winding/cache on GL error,
but its caller previously released target refs and cleared IsRenderToTexture
anyway. Restore also read the GL error flag without separating earlier errors.
Worktree correction records a prior error before binding and makes the caller
retain target ownership/state when restoration fails. This is a narrow boundary
transaction fix; full ARM compilation and focused failure injection are pending.
No visual/GPU acceptance inferred. Do not rely on deletion implicitly restoring
all engine-side state even though GL defines default-binding behavior.

Primary reference:
https://registry.khronos.org/OpenGL/specs/es/2.0/es_full_spec_2.0.pdf
and pinned vitaGL framebuffers.c from round 22. No external code copied.

## Round 24 — GL error attribution and failure injection (COMPLETE)

Question: does one pre-bind read clear the selected backend's prior error?
Searches: Khronos `glGetError error flags reset multiple errors`; vitaGL
`glGetError GL_NO_ERROR`. Compared specification error-state behavior with
pinned local get_info.c: vitaGL returns one vgl_error value and resets it to
GL_NO_ERROR. The round-23 prior-error read therefore clears that backend's
stored error; do not generalize it to arbitrary multi-flag GL implementations.

Added isolated execution of the actual production restore body with injected
prior error and bind failure. It verifies error counting, successful winding/
dimension/cache reset and failure preservation. This is CPU boundary evidence,
not hardware FBO proof. Targeted ARM compilation of both changed owners is
being observed separately; caller-reference release still needs dedicated
failure-path coverage. No additional GL abstraction or renderer rewrite.

Primary reference:
https://registry.khronos.org/OpenGL/specs/es/3.1/es_spec_3.1.withchanges.pdf
Local pinned implementation: vitaGL get_info.c, glGetError.

## Round 25 — transparent sorting ownership (COMPLETE)

Question: can backend batching replace original transparent depth ordering?
Searches: EA `SortingRendererClass Flush`; vitaGL `glBlendFunc depth sorting`.
Inspected pinned original sortingrenderer.cpp and native Draw_Sorting_IB_VB.
Original sorting and flush remain engine-owned; the boundary copies sorting
vertices and rebases indices into original dynamic DX8-shaped buffers. It
rejects unsupported primitive types, excessive 16-bit counts and indices outside
the declared vertex window. Blend support alone is not correct depth ordering.

Decision: retain original transparent ordering and keep opaque reordering out
of this path. New audit lead: vertex memcpy and source-index traversal use
combined offsets without an explicit source-buffer-capacity check in this
function. Inspect original buffer counts and offset domains before deciding
whether to add admission checks. No out-of-bounds runtime failure claimed.
Depth-sort checks are focused CPU evidence, not visual transparency acceptance.

Primary source:
https://github.com/electronicarts/CnC_Renegade/blob/3e00c3a1b97381bb28be89a35b856375e0629a08/Code/ww3d2/sortingrenderer.cpp
Local evidence: ww3d_dx8_boundary.cpp, Draw_Sorting_IB_VB.

## Round 26 — sorting source-window admission (COMPLETE)

Question: can the native sorting converter read past its retained source buffers?
Searches: EA `Draw_Sorting_IB_VB`; Microsoft indexed draw vertex-window bounds.
Compared original DX8 converter offsets with native code and original buffer
capacity accessors. Combined offsets are sums of 16-bit fields and remain
representable in unsigned 32 bits; both buffers expose actual element counts.

Confirmed omission: native converter validated rebased index values but did not
admit source vertex/index windows against capacities before reading them.
Added subtraction-based window checks before vertex memcpy and source-index
traversal. Valid ordering/rebasing remains unchanged. Focused malformed-window
counterexamples remain to be retained; ARM object compilation is live as session
19884. No claim of a reproduced retail crash or visual transparency correction.

Primary reference:
https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-drawindexedprimitive
(supporting window semantics; exact legacy offsets verified from pinned EA
dx8wrapper.cpp, not inferred from D3D9 alone).

Completed rounds: 26/100. Remaining rounds retain the coverage plan above.

## Round 27 — topology admission versus actual submission (COMPLETE)

Question: do equal index counts make triangle strips and fans interchangeable?
Searches: Microsoft D3DPT_TRIANGLEFAN/TRIANGLESTRIP primitive types; vitaGL
GL_TRIANGLE_FAN/GL_TRIANGLE_STRIP. Read Microsoft primitive definitions and
compared native sorting dispatch and indexed submission.

Confirmed latent mismatch: Draw_Sorting_IB_VB accepts a fan count but forwards
all non-list modes as a boolean strip. A fan shares its anchor; a strip does
not, so the count alone cannot preserve topology. Current native call sites
pass list or strip only. Record fan support as incomplete/dormant rather than
claim a current retail fan defect or silently enable a new call route. Future
fan integration must convert anchor triangles or pass an explicit topology
through the established renderer, with winding/degenerate cases checked.
Original engine owns submission intent; do not reinterpret topology for speed.

Primary references:
- https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dprimitivetype
- https://learn.microsoft.com/en-us/windows/win32/direct3d9/triangle-fans
Local evidence: ww3d_dx8_boundary.cpp sorting dispatch and Submit_Bound_Triangles.

Completed rounds: 27/100. Remaining rounds retain the coverage plan above.

## Round 28 — homogeneous coordinates and projected texture divisors (COMPLETE)

Question: can native submission divide clip/texture coordinates on the CPU
without changing interpolation? Searches: Khronos perspective interpolation
clip w; Microsoft transformed vertices RHW perspective. Read transformation,
clipping and texture-coordinate API descriptions and inspected native matrix
conversion, indexed submission and projected texture-coordinate generation.

Current renderer preserves homogeneous clip W through the GPU path and remaps
D3D clip depth to the GL interval. Generated projected texture coordinates
retain q separately instead of interpolating already-divided ratios. Decision:
retain these correctness paths; do not reintroduce affine interpolation as an
optimization. Source evidence is distinct from FOV, near-plane, projector and
hardware visual acceptance. Fixed-camera unequal-depth/near-plane checks remain
required after the play-test hold; CPU tests cannot prove actual shader output.

Primary references:
- https://learn.microsoft.com/en-us/windows/win32/dxtecharts/the-direct3d-transformation-pipeline
- https://learn.microsoft.com/en-us/windows/win32/direct3d9/viewports-and-clipping
- https://learn.microsoft.com/en-us/windows/win32/direct3d9/texture-coordinate-transformations
Local evidence: Build_Indexed_Transform_Matrices, native indexed submission and
original texture-coordinate adapter in ww3d_vita_renderer.cpp. No renderer change.

Completed rounds: 28/100. Remaining rounds retain the coverage plan above.

## Round 29 — normal transforms and skin-cache identity (COMPLETE)

Question: can a cached deformation or simplified normal transform preserve
original animation/material behavior? Searches: Microsoft inverse-transpose
NORMALIZENORMALS; OpenLara skinning joints normals. Read Microsoft normal
transform requirements and inspected native prepared-normal use and skin-cache
key/lifetime contract. OpenLara is a design lead only; no different skeleton or
runtime format is adopted into the original HTree/MeshModel path.

Normal transformation must account for inverse transpose and original normalize
state, including nonuniform transforms. Cache reuse requires matching actual
deformation inputs, not only mesh identity. The selected cache checks per-frame
identity and retained deformation inputs and has bounded capacity/release.
Decision: keep original deformation ownership and correctness fingerprints;
do not trade animation updates or normal semantics for benchmark results.
Review stale comments against configured defaults separately: declaration says
off until configuration while the reader enables it by default before overrides.

Primary reference:
https://learn.microsoft.com/en-us/windows/win32/direct3d9/camera-space-transformations
Local evidence: ww3d_vita_renderer.cpp and ww3d_vita_skin_deform_cache.h.
No performance/visual acceptance follows from isolated cache checks.

Completed rounds: 29/100. Remaining rounds retain the coverage plan above.

## Round 30 — fixed-function shader cache provenance (COMPLETE)

Question: does upstream shader caching cover our generated fixed-function states?
Searches: vitaGL `HAVE_SHADER_CACHE FFP`; vitaGL shader cache version hash.
Read pinned ffp.c and compared the selected local FFP cache patch, builder digest
and program-key/prewarm owners. Upstream's application-shader cache option does
not by itself establish the local generated-FFP cache contract.

Local builder derives cache identity from selected FFP implementation/shader
inputs; key records carry a version/tag and bounded entries. Decision: retain
that provenance and rejection/fallback path. Do not trust an old GXP merely
because its key name exists, or conflate program-key prewarm with GPU-validated
visual output. Further audit should include malformed binary payloads, shader
compiler identity and actual state-mask completeness. Personal-port cache
reports discovered in search are leads only, not evidence to replace our owner.

Primary reference:
https://github.com/Rinnegatamante/vitaGL/blob/6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5/source/ffp.c
Local evidence: build_vitagl_demo.sh, vitagl-ffp-program-cache.patch and
ww3d_vita_ffp_program_keys/warm. No shader/batching optimization adopted.

Completed rounds: 30/100. Next block: native Vita port comparisons (31–40).

## Round 31 — vitaQuake input boundary (COMPLETE)

Question: which controller patterns transfer without replacing Renegade input?
Searches: vitaQuake sceCtrlPeekBufferPositive deadzone; vitaQuake in_psp2.
GitHub API verified owner Rinnegatamante and head
`fbe7c5e7fe77aa35c69421b721ddf5dbb58adc27`. Inspected source/in_psp2.c:
polling feeds engine movement, look uses a scaled radial dead zone, and
movement uses per-axis thresholds. Touch and motion are separate inputs.
File notice is GPLv2-or-later while repository metadata reports GPL-3.0;
review applicable file/project terms before copying. No code copied.

Local comparison: DirectInput retains original input ownership, gates uncaptured
or failed controller reads and blocks input around the native keyboard. Decision:
retain release/neutral transitions and menu/gameplay ownership rather than copy
Quake's view-angle update or its sensitivity constants. Quake's input curve is
a comparison design, not evidence that our current controls are physically
correct. Audit analog scaling and low-frame-rate look behavior through original
Renegade input semantics; optional motion/rumble must not displace required paths.

Primary source:
https://github.com/Rinnegatamante/vitaQuake/blob/fbe7c5e7fe77aa35c69421b721ddf5dbb58adc27/source/in_psp2.c
Local evidence: renegade_directinput.cpp capture, sampling and keyboard gates.

Completed rounds: 31/100.

## Round 32 — vitaRTCW renderer ownership and memory choices (COMPLETE)

Question: does a working FPS port justify copying its renderer thread or heap?
Searches: vitaRTCW `_newlib memory` and `vglInit`; indexed search was noisy,
so used canonical API metadata/tree to locate platform sources. Owner verified
as Rinnegatamante; revision `21fe39f2018ce55757cb3ac7cfd4b40a30adc0dd`.
Inspected psp2_glimp.c and sys_main.c. Metadata says GPL-3.0; inspected files
carry GPLv2-or-later notices. Additional project/file terms still require review.

RTCW starts its renderer through a dedicated thread and semaphores, retains a
single initialization generation, and restarts the executable for a resolution
change. End-frame allocates scratch attribute storage after swap. Its main
source selects a 260 MiB newlib heap. These are engine-specific choices.
Decision: study producer/consumer lifetime and restart ordering; do not move
Renegade GL calls to another thread or copy the heap constant without measured
ownership/resource evidence. Our process-owned graphics generation and original
logical session teardown must remain distinct. No source copied or thread change.

Primary sources at the pinned revision:
- https://github.com/Rinnegatamante/vitaRTCW/blob/21fe39f2018ce55757cb3ac7cfd4b40a30adc0dd/code/psp2/psp2_glimp.c
- https://github.com/Rinnegatamante/vitaRTCW/blob/21fe39f2018ce55757cb3ac7cfd4b40a30adc0dd/code/psp2/sys_main.c
Local comparison: renderer one-time initialization guard and logical shutdown,
plus newlib heap setting from round 6. Threaded-render performance unproven here.

Completed rounds: 32/100.

## Round 33 — vitaXash3D module-provider comparison (COMPLETE)

Question: does Renegade need a dynamic loader to retain original script ownership?
Searches: vitaXash3D heap/module and sceKernelLoadStartModule. API verified owner
fgsfdsfgs, revision `37ec148715d8aa9b9e116bc71175106853d02390`, GPL-3.0 metadata.
Inspected pinned dll_vita.c; file notice is GPLv3-or-later. Its module boundary
passes allocator/I/O imports, receives exports, validates handles and reference
counts module loads/unloads. Post-start admission failure paths need their own
resource audit; a familiar loader pattern is not automatically robust.

The old port README explicitly redirects current Vita support to FWGS mainline.
Mainline documentation uses a different loader/dependency stack; its build flags
are engine-specific and not instructions to alter our SDK or device.
Decision: retain Renegade's original ScriptRegistrar through the existing static
provider. Dynamic-mod/plugin support would require a separate original-interface
contract and lifetime audit; do not introduce it merely to resemble another
port. No loaders, kernel plugins or foreign source imported.

Primary sources:
- https://github.com/fgsfdsfgs/vitaXash3D/blob/37ec148715d8aa9b9e116bc71175106853d02390/engine/platform/vita/dll_vita.c
- https://github.com/fgsfdsfgs/vitaXash3D/blob/37ec148715d8aa9b9e116bc71175106853d02390/README.md
- https://github.com/FWGS/xash3d-fwgs/blob/master/Documentation/psvita.md
Local comparison: static script provider and direct DSP-derived source closure.

Completed rounds: 33/100.

## Round 34 — OpenLara native GXM resource retirement (COMPLETE)

Question: which GPU teardown guarantees survive comparison with a direct-GXM
port? Search: OpenLara Vita GXM platform memory. Verified API owner XProger,
revision `3b268ca4bf986c380f44a26ffd9218bf6d376249`; inspected src/gapi/gxm.h
and BSD-2-Clause LICENSE. Current tree has no Vita-named platform directory;
the direct GXM backend is the relevant source, not a guessed platform path.

Its backend deinit calls sceGxmFinish then sceGxmDisplayQueueFinish before
releasing swapchain/context resources. Texture and mesh destruction enqueue
memory-block IDs with a frame number. However checkPendings removes expired
entries without an explicit freeGPU call at that site; that path requires a
separate container/lifetime audit before reuse. Allocation also returns NULL
after mapping failure without visible local rollback. Do not assume a popular
port's resource helpers are complete or copy frame-count retirement as proof of
GPU completion.

Local comparison: Renegade Release_Texture uses glDeleteTextures; logical
Shutdown preserves process-owned vitaGL state. Their lifetime guarantees must
be established in the pinned vitaGL implementation, not by injecting direct
GXM teardown beneath it. Decision: preserve one backend owner and audit texture,
buffer and render-target retirement across session changes. No code imported;
no claim that the observed upstream paths caused a measured leak here.

Primary source:
https://github.com/XProger/OpenLara/blob/3b268ca4bf986c380f44a26ffd9218bf6d376249/src/gapi/gxm.h
License at the same revision: LICENSE. Local evidence:
port/renderer/vita/ww3d_vita_renderer.cpp Shutdown and Release_Texture.

Completed rounds: 34/100.

## Round 35 — vitaQuakeIII hunk versus graphics memory (COMPLETE)

Question: can another large Vita FPS provide a safe Renegade memory budget?
Searches: vitaQuakeII hunk allocation and vitaQuakeIII low-memory cache.
Verified Rinnegatamante/vitaQuakeIII API ownership and revision
`7da5c6fbd8d80364ef46aeb936c5ad49ec8126ec`. Inspected sys_main.c,
psp2_glimp.c and qcommon/common.c; metadata GPL-2.0 and common.c GPLv2-or-later.
No external code executed or copied.

The port selects a 256 MiB newlib heap, or 305 MiB for Urban Terror. That latter
renderer disables extra memory and MSAA, and uses a different fourth argument
to vglInitExtended. Original hunk allocation separately calloc's its configured
budget plus alignment slack, checks failure, and aligns with intptr_t.
These allocations compete; a heap declaration is not remaining graphics RAM,
and a number passed to vitaGL must be interpreted against that version's API.
Do not copy any of these constants or introduce a hunk allocator into Renegade.

Local comparison: a30_main.cpp declares 192 MiB; renderer logs before/after
initialization and actual vitaGL pool sizes, and treats the fourth argument as
RAM reserve under its pinned implementation. Decision: retain original engine
resource ownership and measure phase-specific high-water and failed allocation
size/pool before adjusting splits. Source inspection does not establish that
the current campaign fits, nor does a different engine's release establish it.

Primary sources at the pinned revision:
- https://github.com/Rinnegatamante/vitaQuakeIII/blob/7da5c6fbd8d80364ef46aeb936c5ad49ec8126ec/code/psp2/sys_main.c
- https://github.com/Rinnegatamante/vitaQuakeIII/blob/7da5c6fbd8d80364ef46aeb936c5ad49ec8126ec/code/psp2/psp2_glimp.c
- https://github.com/Rinnegatamante/vitaQuakeIII/blob/7da5c6fbd8d80364ef46aeb936c5ad49ec8126ec/code/qcommon/common.c

Completed rounds: 35/100.

## Round 36 — compiler-selected inputs and FFmpeg dependency identity (COMPLETE)

Question: does hashing the GCC driver identify the library configuration it
actually builds? Searches targeted GCC print-file-name/print-libgcc-file-name
documentation and FFmpeg cross-prefix nm/strip configuration. Read primary GCC
Developer Options: library/program queries identify selected toolchain paths,
and multilib selection depends on command-line switches. Local installed GCC
queries with Cortex-A9/NEON/hard-float flags resolved absolute cc1, include and
libgcc paths. Failure, relative and missing-path responses are now rejected by
the production query block and its controlled-driver test.

Read configure directly from the verified FFmpeg 9.0.1 release archive, SHA-256
`cf38e0e28c7e5605942c4a77755349b0145804a397af37eb1fb4c77cb237f635`.
It prefixes nm/strip with cross_prefix and runs nm to determine external-symbol
prefix. Thus compiler internals, startup/runtime libraries, headers and binutils
are material inputs beyond a driver version string. Existing source-cache
extraction also needed replacement with a fresh verified extraction per build.

Decision implemented: mandatory installed identity and installed-byte receipt;
optional shared cache uses the same ordered inputs. Hashes include GCC runtime
tree, SDK headers/libraries and selected tools. Claude review corroborated gaps;
its conditional cache-helper concerns were checked against actual helper code,
not accepted as observations. 27 focused tests and real SDK identity probe PASS.
New recipe rebuild/reuse remains pending until the live native consumer ends;
no receipt is retroactively assigned to old output. No playback or physical claim.

Primary sources:
- https://gcc.gnu.org/onlinedocs/gcc/Developer-Options.html
- https://ffmpeg.org/releases/ffmpeg-9.0.1.tar.xz (verified configure member)
Local evidence: build_ffmpeg_bink_vita.sh, ffmpeg_install_receipt.py,
local-builder/logs/ffmpeg-install-identity-probe.log and ffmpeg-reuse-tests.log.

Completed rounds: 36/100.

Round-36 follow-through: revised recipe build PASS; receipt covers 173 files.
Unchanged second invocation verified reuse in 2.86 s without changing archive
or receipt hashes/mtimes. All five archives reproduce the hashes used by the
successful direct dev246 ARM link. Actual input identity document matches
`fa616f92cc3191eb7cdf9c2e293b3d3b9d8f0b141229ac8ec51567cbe5f593cf`.
Installed-header target probe retains INT32_MAX under explicit int enums and
rejects default short enums. No runtime or complete ABI acceptance inferred.

Round-26 implementation follow-through: exact production vertex/index admission
blocks pass 13,122 generated window cases against independent 64-bit arithmetic
under ASan/UBSan. Native DX8 boundary object compiled successfully in session
19884. This verifies admission arithmetic, not the full GPU sorting pipeline.
