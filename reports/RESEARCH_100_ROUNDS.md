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

Completed rounds: 10/100. Remaining rounds retain the coverage plan above.
