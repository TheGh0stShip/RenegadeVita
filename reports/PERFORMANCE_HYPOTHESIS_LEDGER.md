# Performance hypothesis ledger

## Dev200 RenCorner Glacier bounded Vita3K run (2026-09-27)

The live purchase-response run reached 1,560 frames. At that checkpoint the
flight recorder's rolling 120-frame distribution was p50 149.788 ms and p95
284.171 ms, with 1,560/1,560 frames over 33.3 ms. Original gameplay pacing
reported 139.178 s real versus 116.756 s simulation, a 22.422 s drift.
These are emulator measurements; render-stage CPU time is not GPU time. No
optimization was adopted from this run. Native Vita frame pacing remains
unmeasured and the 60 FPS goal is unmet on this heavier emulator route.

## Dev197 M01 short-save freeze boundary (2026-09-26)

- Hypothesis: the freeze a few steps before the M01 ladder is render/presentation-bound in the current Vita3K OpenGL run, not a long simulation command. Do not generalize this to the separate physical PSTV frame-six stop.
- Evidence: debugger-attached replay of the original M13 pre-Ion save completed M13 and passed M01's first aircraft entry. The user saved in M01, moved a few feet, and reported a freeze. Flight recorder last completed frame 387; frame 386 simulation/render 3.3/568.8 ms, frame 387 7.7/552.5 ms. Two host CDB samples found Vita3K's OpenGL presentation thread inside Intel `DrvSwapBuffers` -> `wglSwapBuffers` -> DWM wait. This is a Windows host thread stack, not an ARM guest stack or GPU timing. Installed Vita3K guest GDB did not respond to interrupt.
- Decision: no renderer or gameplay change from these observations alone. Preserve the user-created save for the short replay; compare OpenGL presentation behavior and capture a physical PSTV frame boundary before adopting a fix. No before/after win claimed.

## M13 authored intro and shared effects preparation (2026-09-23)

- Retail `M13.mix` `X00_Intro.txt` requires `X00_Havoc_Traj`,
  `S_A_Human.H_A_X00_Havoc`, and `X00_Rope` at frame 1773; the two engineers
  use their own trajectories and animations later. These were absent from
  loading-time preparation. The full-port candidate now loads and releases
  13 original intro render models and 24 animations during M13 loading. No script command,
  attachment, animation, or actor lifetime is replaced.
- Two original M13 host cycles resolve all 13 selected intro render models
  and 24 animations.
  Havoc trajectory and body animation each have 228 frames; rope has 333.
  The three attachment bones exist, and original W3D animation moves
  `BN_Havoc` 13.75 units over frames 0-200 (Z 11.975 to -1.505).
  This validates source assets and trajectory motion, not Vita visual output.
- Original M13 world object definitions expose seven distinct killed-explosion
  IDs for SAMs, buggy, mobile artillery, light tank, harvester, obelisk,
  and gun emplacements. Loading-time preparation now follows those IDs and
  original Twiddler choices. Two host cycles prepare all seven and still kill
  both retail SAMs through original damage/scripts in 0.22-0.33 ms each.
  Later scripted vehicle spawns and all explosion visuals still need a
  candidate-matched run.
- Original tracked-vehicle texture mapper writes scroll translation to the
  D3D `_31/_32` fields. The Vita DX8 COUNT2 pass-through UV path previously
  supplied a zero third coordinate, cancelling the translation. It now
  supplies the implicit homogeneous one; generated coordinates remain
  unchanged. The 13-check renderer lifecycle test covers both scroll
  directions and passes. A visual run is required for medium, light, and
  mammoth tank treads and the reported medium-tank barrel material.
- Decision: retain this source-only candidate pending M13 fixed-route
  p50/p95/p99/worst frame time, audio drift, full explosion visuals, NPC
  behavior, rope/body pose, memory, and normal transition. No VPK or Vita3K
  install was produced. M00 tutorial host regression passes twice.

## M13 randomized explosion preparation: cover every retail choice (2026-09-23)

- Primary upstream finding: EA revision
  `3e00c3a1b97381bb28be89a35b856375e0629a08`,
  `Code/wwsaveload/definitionmgr.cpp` resolves a named Twiddler by calling
  `Twiddle`; `Code/wwsaveload/twiddler.cpp` chooses one referenced definition
  from a time-seeded random index. The existing M13 loading preparation used
  `Find_Typed_Definition` once, so it warmed only one random explosion variant.
  The script's later lookup could select another and pay its first-use cost.
- Actual retail M13 data through the script-linked host runtime: `Air Explosions
  Twiddler` references exactly `Air Explosion 01` and `Air Explosion 02`.
  The port now inspects the original un-twiddled definition list, walks nested
  selectors to depth four, and prepares each referenced original timed
  decoration model. No effect is spawned, retained, or selected for gameplay;
  the original script lookup and explosion creation remain unchanged. The
  accessor is full-port-only; the demo is unchanged.
- After the two WW3D duplicate-load fixes, warming only one random choice left
  first-SAM host pauses of 0.14-0.35 s in the sampled runs. Warming both real
  choices and `Explosion_SAM_Site` reduced the two-cycle non-sanitized host
  `Apply_Damage` timings to 0.64/0.49 ms and 0.38/0.27 ms for the two SAMs.
  The same two cycles pass ASan/LeakSanitizer at 1.21/1.49 ms and
  1.17/1.09 ms. Each SAM still goes from 100 to 0 health; the M00 tutorial
  regression is being rerun. All changed ARM objects compile, and deterministic
  staging passes 206 zero-fuzz patches.
- Decision: retain as a first-use asset preparation candidate, not a proven
  Vita frame-time win. All explosion variants must render correctly, and the
  normal M13 scripts, damage/decal visuals, A10/Ion sequence, audio sync,
  mission transition, memory, and physical-Vita 60 FPS target require a
  matching runtime replay. No VPK or Vita3K install was produced.

## M13 SAM death: repeated unresolved W3D prototype loads (2026-09-23)

- Reproduction: the original `Test_DLS.cpp` script attached to both retail M13
  SAMs creates `Air Explosions Twiddler` on death. The script-linked host smoke
  measures `Apply_Damage` directly: before the change, two non-sanitized cycles
  took 1.43/1.21 s and 2.26/1.78 s for SAMs 1500015/1500016. These are host
  wall times, not Vita frame times or a complete mission progression test.
- Attribution: Callgrind placed about 78% of the second-SAM sampled instruction
  cost below original `TimedDecorationPhysDefClass::Create`. A GDB loader trace
  saw repeated `Load_3D_Assets` calls for unresolved explosion child names;
  `e_19_Asmk1.w3d`, `e_19_Aflame1.w3d`, and `e_19_ARock1.w3d` were each parsed
  12 times in one SAM death. `strace` confirmed repeated `always.dat` opens and
  directory scans, with no single long blocking syscall. Original
  `WW3DAssetManager::Create_Render_Obj` retries the W3D load every time a
  successfully parsed file did not register the requested child prototype.
- Change: a source-hash-guarded, zero-fuzz full-port patch retains up to 256
  names whose W3D file parsed successfully but whose prototype stayed absent.
  `Find_Prototype` still runs first on every request, failed file loads still
  retry, and `Free_Assets` clears the names. The demo path is unchanged.
  Existing original render-object and explosion creation remain authoritative.
- Host comparison after the change: two non-sanitized cycles measured
  1.02/0.96 s and 0.77/0.71 s for the two SAMs. Two ASan/LeakSanitizer cycles
  passed with both SAMs reduced from 100 to 0 health and no reported memory
  error; the corresponding pauses were 1.06/0.87 s and 0.81/0.92 s.
  Prewarming original timed-decoration models improved the first SAM but left
  the second at roughly 0.7-1.1 s. The edited asset-manager object compiles
  for Vita ARM. This is a measured host reduction, **not** a lag-free or native
  FPS result, and does not establish the A10/mission transition behavior.
- Decision: retain the targeted redundant-load fix pending matching M13
  Vita3K and physical replay with explosion visuals and resource high-water.
  The 0.7-1.1 s host pause described above was subsequently narrowed to a
  second load path in the aggregate definition; see the next entry. Do not
  present either source fix as resolution of the last-SAM freeze, ambush lag,
  or 60 FPS goal without matching runtime evidence.

## M13 SAM death: aggregate fallback repeated the on-demand load (2026-09-23)

- Primary upstream check: EA source revision
  `3e00c3a1b97381bb28be89a35b856375e0629a08`, `Code/ww3d2/assetmgr.cpp`
  `Create_Render_Obj` loads the local and parent W3D when on-demand is enabled.
  `Code/ww3d2/agg_def.cpp` `Create_Render_Object` then calls `Load_Assets`
  again when that lookup returns null. The Vita full-port runtime and host
  route both explicitly enable on-demand loading. After the first targeted
  cache, Callgrind still attributed 38.8% of second-SAM instructions to W3D
  loading, reached through aggregate subobject attachment.
- Change: in full-port mode, skip `AggregateDefClass`'s direct fallback only
  while asset-manager on-demand loading is enabled; preserve it when disabled.
  The asset manager still attempts local/parent W3D and prototype lookup.
  No explosion, decal, damage, or script callback is skipped. The demo is
  unchanged. Source staging passes 205 ordered zero-fuzz patches and the
  edited aggregate object compiles for Vita ARM.
- Identical non-sanitized two-cycle host SAM smoke after both fixes: first
  SAM 0.441/0.461 s, second SAM 0.00055/0.00032 s. With the two original
  explosion definitions warmed and released before damage: first SAM
  0.354/0.143 s, second SAM 0.00052/0.00033 s. ASan/LeakSanitizer prewarmed
  route passed two cycles; first SAM 0.138/0.100 s, second 0.0011/0.0018 s.
  These are host wall times for isolated `Apply_Damage`, not complete frame
  times or a Vita performance claim. Both retail SAMs still fall from 100 to
  0 health in each cycle.
- Residual first-SAM Callgrind sample after warming: roughly 689k instructions,
  with original decal creation and explosion damage/collision prominent; W3D
  model creation is smaller than before. These original effects and damage
  cannot be dropped to satisfy a benchmark. This sample warmed only one
  random Twiddler choice; the full-choice preparation above removed its
  measured first-SAM host pause. Native frame-time acceptance still needs a
  candidate-matched replay.
- Decision: retain as a host-measured algorithmic fix, with acceptance pending
  original explosion/decal visuals, area-4/A10 completion, frame distribution,
  memory, and physical Vita comparison. No package/install was produced.

## M13 steady mesh submission: original WW3D and pinned vitaGL review (2026-09-23)

- Measurement: Dev194 M13 frames 5521-5640 submitted 17,002 meshes and
  47,194 draw ends. The 1-in-16 sampled mesh-boundary estimate is 2,128,032
  us over 120 frames (~17.7 ms/frame); draw ends account for an estimated
  225,728 us (~1.9 ms/frame). These are **CPU submission estimates**, not GPU
  timing. The sampled slowest mesh is `L00.WALL_BUSTED2` (3,569 us).
- Counter caveat from the original texture boundary: `texture_requests` counts
  filename-based `_Create_DX8_Texture`, while `texture_decodes/uploads` also
  count surface-backed texture creation. In Dev192 M13 frames 6000-6120,
  requests rose by only 3 but uploads rose by 131; this does **not** prove 131
  repeated DDS decodes or a retail archive cache failure. The existing
  aggregate counters cannot attribute those dynamic uploads to an owner.
- Source comparison: original EA `MeshMatDescClass::Peek_Texture` and
  `Get_Shader` retain per-polygon material ownership; no geometry or material
  shortcut is justified from these samples. The pinned vitaGL revision
  `6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5`, `source/ffp.c`
  (https://github.com/Rinnegatamante/vitaGL/tree/6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5), still
  performs FFP shader/state resolution and `sceGxmDraw` at `glEnd`; our indexed
  extension copies transient indices, so caller pointers are not retained.
  The dependency already uses `SKIP_ERROR_HANDLING`, shader cache, and compact
  unlit vertices. Upstream's documented optional draw/indices/texture speedhacks
  (https://github.com/Rinnegatamante/vitaGL/blob/6e7fe40292e8f1d10f9a94ff2cd2f4fb1ba452a5/README.md) explicitly
  carry crash, compliance, or visual-risk caveats and are deferred pending a
  fixed route A/B, rather than globally enabled for M13.
- Focused source change: untransformed `D3DTSS_TCI_PASSTHRU` UVs now submit
  the original S/T pair directly, avoiding the 4-component temporary and
  texture-transform path for every emitted vertex. Generated coordinates,
  projected transforms, missing UVs, and first-use diagnostics retain their
  existing paths. This is a candidate CPU-work reduction, not an accepted FPS
  gain. Renderer ARM object compilation passed; script-linked M13 SAM smoke
  still passes two ASan/LeakSanitizer cycles. No matching runtime A/B or visual
  comparison exists, so adoption for performance remains pending.
- Next evidence: same M13 route and camera/content window, before/after
  p50/p95/p99/worst, simulation/render/present split, mesh-boundary and draw-end
  estimates, texture upload spikes, memory high-water, A/V drift, visible
  original effects/NPCs, and SAM-to-A10-to-transition continuity. Physical Vita
  remains the acceptance target.

## M13 script-linked host sanitizer and WWMath layout (2026-09-23)

- Gap found: the prior M13 host harness did not link `Test_DLS.cpp`, so its
  120-frame pass could not validate the Area 4 controller that owns SAM
  destruction, A10 strike, dialogue, and mission completion timers.
- Change: link the original script unit and assert the retail M13 controller
  carries `MX0_Area4_Controller_DLS`. The first ASan run then reproduced an
  8-byte read from a 4-byte float in `WWMath::Is_Valid_Float`, reached from
  original vehicle physics. `Is_Valid_Double` had the same LP64/word-order
  assumption. A hash-guarded staged patch uses `memcpy` into `uint32_t` and
  `uint64_t` and the same exponent tests, without changing physics formulas.
- Verification: source staging passes 203 zero-fuzz patches; finite, signed
  zero, subnormal, infinity, and NaN host value tests pass; ARM syntax check
  passes. With `Test_DLS.cpp` linked, isolated retail M13 and tutorial M00 each
  complete two 120-frame host cycles under ASan/LeakSanitizer. The pre-fix
  M13 sanitizer stack and the fixed pass are retained locally under
  `build/host-m13-diagnostic/` and `build/host-a31-asan/`.
- Host-only SAM isolation: `M13_SAM_DAMAGE_SMOKE` applies the original
  `STEEL` warhead through `DamageableGameObj::Apply_Damage` after M13 load.
  Both retail SAM IDs, 1500015 and 1500016, drop from 100 to 0 health in two
  ASan/LeakSanitizer cycles with clean teardown and are now a canonical host
  regression. This tests object death and
  explosion boundaries, not the later `SAMS_DESTRUCTION`/A10 script state.
  Dev192's matched route had 1.84 s and 0.77 s simulation stalls near the two
  SAM losses but continued to A10 dialogue; its result does not prove a
  permanent SAM-death hang in the later Dev194 report.
- Decision: retain as a shared portability/correctness fix and stronger host
  gate. Do not attribute the Vita3K last-SAM freeze or any FPS improvement to
  it: the host route does not reach either SAM death or the A10 transition,
  and no matching Vita3K/physical frame-time comparison exists.

## Internal Dev195 M13 first-use preparation and recorder gate (2026-09-23)

- Measured lead: matching Dev194 frames 2040/5032 took 621/780 ms in render
  submission while 15/14 textures were decoded/uploaded. Frame 5678 took
  631 ms total, 613 ms simulation; `X0E_Obelisk.txt` created two objects in
  258/304 ms. The frame timer excludes later recorder flush I/O. Dev194's
  captured frames end at 5726 with both SAMs alive, so the reported last-SAM
  freeze is not localized by that trace.
- Change: prepare one fresh `X0E_Obelisk` and `X0E_AG_OrcaPart` instance at M13
  loading, consumed by the original `PhysClass::Set_Model_By_Name` path; prepare
  referenced original texture objects under a 32 MiB soft extra-residency cap.
  This shifts observed categories of first-use work toward loading but does not
  alter original script events, texture content, or effect spawn semantics.
- Diagnostic fix: checkpoint sidecars append deltas, replace on candidate reset
  and ring rollover, and avoid repeated directory creation. Cross-thread
  runtime-log writes are serialized; the owner thread alone writes the flight
  ring. A canonical host self-test now covers append, replacement, rollover,
  and owner-only log capture.
- Guardrail: an attempted SAM explosion recycler preload violated the existing
  fresh-effect source contract, which protects against previously missing
  explosions/trails. It was removed before the successful ARM compilation.
- Verification: recorder host test and ASan/UBSan pass; focused contracts pass;
  internal Dev195 ARM ELF compile/link and identity pass. No package, Vita3K
  installation/launch, same-route before/after, visual check, memory result,
  or physical test. The older isolated host M13 runtime completed two 120-frame
  load/teardown cycles but does not include `Test_DLS` SAM mission scripting.
- Decision: pending. Do not present a candidate as fixing lag or the freeze.
  Compare matching M13 frame-time median/p95/p99/worst, texture upload counts,
  X0E create time, resident memory high-water, complete SAM-to-transition
  behavior, and visible original effects before retaining these preloads.

## Dev194 runtime: synchronous flight-recorder amplification (superseded by internal Dev195 compile)

- Evidence: candidate-matched `A3.5-dev194` M13 telemetry covers frames 1-5726.
  It reports 40.1 average FPS; p50/p95/p99 26.5/96.5/160.6 ms; worst 2.43 s
  at startup. The last recorded frame is 5726 (41 ms; 24.8 ms simulation,
  16.2 ms render); no SAM destruction event or post-freeze callback was captured.
  Matching Vita3K logs show the flight recorder reopening events, frames, log
  tail and summary plus attempting `mkdir` every 2-3 seconds. The runtime calls
  full flush on each mission-progress change, each 120-frame checkpoint, and
  every frame above 250 ms. Full flush rewrote up to 4096 frame samples, 768
  events and 768 log lines synchronously on the campaign thread. This is a
  confirmed diagnostic cost and plausible self-amplifying stall source, not
  proof of the reported SAM freeze or the remaining ~25 ms steady workload.
- Evidence integrity: `campaign-flight-events.jsonl` ends its Dev194 records
  with a partial Dev192 JSON object and stale Dev192/Dev185 records. The
  available frame/runtime tail stops at frame 5726 with both SAMs present;
  it is not evidence for the subsequently reported last-SAM failure and must
  not be used to infer that callback's cause.
- Change: local recorder appends only newly recorded frame/event/log deltas;
  the bounded sidecars are replaced only at ring rollover or when recovering
  from a write failure. Full ring snapshots remain on fatal, clean exit, final
  and shutdown. Capture directory creation is no longer repeated per flush.
- Verification: four focused source contracts, strict host `-fsyntax-only`
  compilation with warnings-as-errors, and `git diff --check` pass. Pytest is
  not installed; the focused Python contract functions were invoked directly.
  No game build, Vita3K install/launch, runtime performance comparison, or
  physical test occurred. This change is not yet an accepted FPS improvement.
- Decision: retain as a diagnostic-overhead correction. Do not present a new
  build or claim 60 FPS/SAM-freeze resolution. Next integrate deeper measured
  render/simulation work and SAM-callback analysis before one candidate is
  prepared; compare matching M13 frame distributions and SAM progression.

## Dev194: prevent retained-instance reuse in the M01 opening sequence

- Evidence: candidate-matched Dev192 log records M13 original completion
  success at frame 8222 and normal selection of `M01.mix`. M01 initializes;
  first visible frame is 5.93 s (5.03 s simulation, 0.90 s rendering), while
  its intrusive per-object PostThink profiler accounts for 1.89 s over 443
  objects. At M01 frame 2, `X1H_Hover_Troop.txt` begins; the final complete
  records show cached instances consumed for `vxag_nod_heli`,
  `X1c_AG_xplosion`, `VxAG_X1Borca`, and `X1C_AG_Missile`. These names and
  event ordering match the first authored M01 beach-aircraft sequence in
  retail `M01.mix`'s `x1c_intro.txt`. The log terminates here; it does not
  identify the blocking function or prove these consumes caused the hang.
- Change: these four mutable animated models are now warm-only during M01
  preparation. Their prototypes are touched during loading, then the temporary
  instances are released; original cinematic commands still create fresh
  instances, attach them, and play authored animations. All other M01 retained
  preparation is unchanged. Dev193's deterministic sampled PostThink fix is
  also included.
- Verification: canonical host/sanitizer, 174 existing Python tests, original
  M00/M01 host runtime cycles, ARM, SELF/VPK identity, diagnostic bundle, and
  Vita3K install passed. Two focused instrumentation/M01 source tests passed
  directly after the build; they are now wired into the canonical suite for the
  next run. Dev194 VPK SHA-256
  `8b7ba2c0bcb8a57eaee978041ca47765807492b09d14329e6c0652e4da61c15c`.
- Runtime: Dev194 is installed but not launched. The user's Vita3K process was
  left untouched. This is a targeted lifetime hypothesis, not a verified M01
  freeze fix or performance improvement. Havoc rope-animation and finale
  double-image behavior were not changed.
- Decision: keep pending a matching Dev194 opening-scene capture, including
  whether `x1c_intro.txt` completes, the first NOD aircraft appears, and
  persistent progress reaches a stable M01 frame.

## Dev193: sampled PostThink object timing restored after preservation patch

- Evidence: Dev192's first M01 frame took 5.93 s (5.03 s simulation,
  0.90 s rendering). The PostThink recorder attributed 1.89 s to its 443-object
  pass, but made two process-time calls and object identity/name lookups for
  every eligible object. This instrumentation materially contaminated its own
  measurements; it is not evidence that the uninstrumented game spends 1.89 s
  there.
- Change: after the deterministic Dev190 preservation patch, verify the exact
  preserved `gameobjmanager.cpp` SHA-256 and reapply the exact guarded 1-in-16
  sample transform. Keep exact object counts; time and resolve identity/name
  only for sampled entries. Added a source regression preventing preservation
  from silently restoring per-object timing.
- Verification: focused test, all 174 Python tests, canonical host/sanitizer,
  original M00/M01 host-runtime checks, ARM/SELF/VPK identity, package hashes,
  diagnostics, and Vita3K installation pass. The installed receipt is
  `build/vita3k-backups/A3.5-dev193-setup-20260924T021712937253Z/`. VPK SHA-256
  `d373428f36dbbeb533e074464f6a72a0eea910cd522a851565b91284b4c0a8c9`.
- Runtime: Dev193 has not been launched because the user's Dev192 Vita3K
  session remains active. It does not directly alter M01 aircraft preparation,
  cinematic actor rendering, rope animation, or mission scripts. No freeze,
  animation, or frame-time fix is accepted yet.
- Decision: retain the sampling correction to produce less intrusive hotspot
  data. Compare same-route M13/M01 timing and inspect first-plane progress in a
  matching Dev193 run before drawing performance or correctness conclusions.

## Dev192: campaign log sync overhead and truncated records (2026-09-23)

- Hypothesis: synchronizing the persistent runtime log after every emitted
  line adds avoidable storage stalls on the campaign thread and may amplify
  frame-time spikes; the Dev190 log also ends inside a 768-byte-truncated
  performance line shortly after frame 7200.
- Change: campaign appends now defer storage synchronization until explicit
  startup/reset, each 120-frame flight checkpoint, fatal capture, and final
  flush. Campaign line capacity is 2048 bytes. The M00 demo retains its
  existing per-line sync and 768-byte capacity.
- Limits: the available log termination and freeze are correlated only by
  proximity in the reported mission; they do not prove storage sync caused the
  freeze. A larger line buffer does not eliminate all I/O cost. User saves and
  game data are untouched.
- Verification: five focused contracts, canonical host/sanitizer, 174 tests,
  repeated original M00/M01 host-runtime cycles, ARM, SELF/VPK identity,
  diagnostics, and Vita3K installation pass. The candidate is installed but not
  launched because the user's Dev190 emulator process was active. VPK SHA-256:
  `776f7fd028b666a489323be375524f2c87abd9595d4147cb603c7a2ee12e30a2`.
- Decision: retain as a candidate pending a matching M13 route. Compare complete
  checkpoint records, log tails, frame percentiles, and GPS-lock progression;
  accept performance only from same-route runtime measurements.

## Dev191 tracked-vehicle UV time-unit correction (2026-09-23)

- Evidence: `LinearOffsetTextureMapperClass::Set_UV_Offset_Delta` converts the
  supplied rate from seconds to a per-millisecond increment, and `Apply`
  integrates it using elapsed milliseconds. `TrackedVehicleClass::Render`
  supplied distance accumulated between render calls as if it were a
  per-second rate, multiplying the result by frame duration a second time.
- Change: convert the measured world displacement to distance per second using
  elapsed engine milliseconds; skip a fabricated first-render displacement and
  reset sample history when a different model is installed. This preserves the
  original mapper and render ownership.
- Verification: 2 source contract tests pass; canonical host/sanitizer, 173
  tests, M00/M01 host runtime, ARM/SELF/VPK identity, diagnostics package, and
  Vita3K install passed. VPK SHA-256
  `4d1c39b3fa9da16fb9a352cb1fab28445e46c4e10944c3abbb10dff0b11ed4eb`.
- Runtime: Dev191 is installed but not launched. Tread animation, frame-time
  improvement, and campaign behavior are unverified; this fix cannot explain or
  claim resolution of the Ion Cannon freeze, NPC reload cadence, or mission lag.
- Freeze lead from the Dev190 log: the 1596 ms maximum belongs to startup frame
  1 (1037 ms simulation, 559 ms render), not CON012. Frame 6467 later took 1322
  ms, dominated by simulation (1309 ms); frames 6760-6762 each took about 520 ms
  across simulation and render. `MX0_A04_CON012` begins at frame 7168 with
  `MX0_A04_CON011` still active near completion; the log ends mid-record shortly
  after frame 7200. This does not establish a conversation-manager fault or
  report the freeze's last executed function. The mixed flight bundle is invalid.
- Decision: retain the unit correction for candidate testing; require matching
  runtime observation of moving tank tracks before accepting the tread issue as
  fixed.

## Dev190 measured regressions and corrective candidate (2026-09-23)

- Runtime identity: the installed Dev189 candidate's own persistent log
  identifies `A3.5-dev189`; its package hash matches the recorded installation.
  The run completed M13, transitioned into M01, and logged M01 through frame 5.
- M13 evidence: at frame 6000 the recorder reported 35.747 average FPS,
  p50/p95/p99/max frame times of 32.4/206.4/384.7/2486.1 ms. A 2.49 s
  simulation stall occurred at frame 5810. One authored cinematic `Create_Object`
  command took 324.6 ms; other logged object-create commands took 177-275 ms.
  This points to command/object creation bursts, not mesh submission alone.
- M01 evidence: frame 1 took 5.66 s (4.82 s simulation, 0.84 s rendering).
  Its `Post_Think` pass logged 1.72 s over 443 objects. The diagnostic called
  the process timer twice for every object, so this measurement was heavily
  intrusive and cannot be accepted as uninstrumented game cost.
- Behavior evidence: the two M13 engineers were registered and alive in actor
  snapshots at frames 2880-3600, and their positions changed after the intro.
  This does not prove they rendered correctly. `GDI_RocketSoldier_0` id
  1500000039 remained at one position with zero velocity and
  `human_state=ANIMATION` across the intro and subsequent frames; its action
  became inactive at frame 2280 while that state persisted. This isolates a
  scripted-animation lifecycle defect but does not yet identify its authored
  stop/movement command.
- Change under test: remove the campaign-only explosion-recycler spawn route
  and prepared volatile projectile/particle-emitter reuse, preserving original
  fresh-create/reset/lifetime semantics. Reduce per-object process-time calls
  to a rotating 1-in-16 sample. Register the previously staging-only direct
  track-name matcher and NaN target-box guard as source-anchored patches.
- Decision gate: canonical host/sanitizer/ARM/VPK and Vita3K installation must
  pass first. Performance, A/V sync, visible explosions/trails, engineer
  presentation, rocket-soldier behavior, treads, and the M01 aircraft freeze
  remain runtime-unverified until a matching Dev190 run. The M13/M01 run facts
  above are user runtime evidence, not a Dev190 before/after result.
- Candidate result: canonical build, 173 host tests, retained M00 runtime,
  package identity/closure, and Vita3K installation all passed. VPK SHA-256 is
  `e7ece5f02d71709a0d681777c6d74e9dfac8f4011267bf66358018e0146a8219`;
  installation receipt is
  `build/vita3k-backups/A3.5-dev190-setup-20260923T234508866640Z/setup-receipt.json`.
  Vita3K was already open; this candidate was not launched. Dev190 route metrics,
  visible effects, engineers, rocket-soldier behavior, tread animation, and the
  M01 plane-arrival stall therefore remain unverified.
- Decision: keep sampled `Post_Think` timing and original fresh effect-spawn
  semantics because they remove per-object timer pressure and avoid custom
  reuse paths implicated by missing visuals. Keep direct track-name matching
  and invalid HUD projection rejection as candidate fixes, not accepted runtime
  fixes. Do not claim an overall frame-time win without a matching fixed-route
  before/after capture.

## Dev189 source/build closure (2026-09-23)

- Hypothesis: two remaining avoidable sources of burst cost are timed
  explosion visuals that were not connected to the reproducible build patch
  registry, and unconditional Vita process-time queries on every mesh and draw
  end. The Dev186 recorder attributed about 13.9 ms/frame to the mesh boundary,
  but its sidecars are corrupt, so the value is a lead rather than an accepted
  baseline.
- Change: register the original `EffectRecyclerClass` preparation/spawn/reset
  integration as a zero-fuzz source patch; sample process-time calls at a
  deterministic 1/16 stride while retaining exact event counts; validate
  candidate identity and monotonic timing before profiling flight bundles.
- Guardrails: no cinematic/AI/objective skips, no gameplay behavior forced,
  and no GPU-time inference from CPU boundary timing. Estimated total sampled
  microseconds scale each observed sample by 16 and are an estimate; sample
  count and raw sampled total are emitted too.
- Verification: patch reconstruction and source contracts, canonical host and
  sanitizer suite, M00/M01 original host harnesses, ARM/SELF/VPK identity,
  and diagnostics packaging pass. Candidate was not installed or launched.
- Decision: retain as a candidate implementation; do not call the recycler an
  in-game win or the timer sampling an FPS gain until a valid same-route runtime
  A/B confirms frame percentiles, effect correctness, and actor behavior.

## Dev188 build closure (2026-09-23)

Canonical host/sanitizer, 171-test, ARM, SELF/VPK, identity, and diagnostics
packaging gates pass. VPK SHA-256 is
`7dd9b959529e050f3d8b1b62930447867e874dcfa3252ce2f2caad64efc1978a`; ELF
SHA-256 is `dc8a26aa6c933c20d44f38bd8ec386b2106e35a537bb4c20d9755bd8d4663e5b`.
The candidate was not installed or run, so the explosion-recycler restoration
and timing-sample reduction have no runtime A/B result yet.

## Dev187 invalid HUD geometry and prefixed tread names (2026-09-23)

- Hypothesis: the new early M13 freeze is being triggered or amplified by NaN
  target-box coordinates submitted after a target enters a destroyed or
  transition state; static treads may use prefixed mesh names outside the
  original dotted-name assumptions.
- Evidence: Dev186 runtime ends at frame 3720 after 64 HUD diagnostics include
  repeated `clip_top=(-nan,-nan)` and `box=(-nan,-nan,-nan,-nan)`. The same
  frames still list `GDI_Engineer_0_B` in the actor registry, so disappearance
  is not object deletion at that point. The existing matcher only recognized
  exact `V_TRACK-*`/`V_TREAD-*` prefixes.
- Change: reject invalid projected target boxes before adding Vita 2D geometry;
  scan full mesh names for prefixed `TRACKL/TRACKR`, `TREADL/TREADR`, and
  separator variants.
- Guardrails: no mission/objective/AI shortcut, no actor deletion, no renderer
  replacement, and valid target geometry remains unchanged.
- Decision: adopt for Dev187; retain only if the next run shows no NaN target
  submissions and a reduction in the reported freeze/tread failures.

## Dev186 track animation and Vita mapper-state cache (2026-09-23)

- Hypothesis: part of the remaining vehicle/effect cost is avoidable repeated
  Vita GL texture-matrix submission, while static treads are a separate naming
  mismatch rather than a missing original animation path. A tighter cinematic
  command budget should prevent authored bursts from monopolizing simulation
  long enough to let audio drift.
- Evidence: Dev185 recorder showed M13 render spikes of 0.53 s and simulation
  spikes up to 1.90 s; M01 frame 1 was 6.336 s (5.356 s simulation). The
  tracked-vehicle code only searched after `.` and therefore rejected direct
  retail names such as `V_TRACK-L`/`V_TREAD-L`. The Vita texture-stage boundary
  performed GL matrix setup for every identical mapper state.
- Change: accept direct track mesh names; cache per-stage transform/flags and
  skip identical Vita GL matrix work; reduce full-port campaign cinematic
  batches from 12 ms/4 commands to 4 ms/2 commands before yielding.
- Guardrails: original mapper, render ownership, track UV updates, cinematic
  command order, AI, collision, objectives, audio callbacks, and progression
  remain intact. Cache is only at the platform boundary and does not reuse
  volatile render objects.
- Evidence retained: focused source contracts, ARM/SELF/VPK identity, and
  Vita3K install PASS. Runtime A/B and visual/audio acceptance remain pending.
- Decision: adopt for Dev186 as a bounded, measurable candidate; keep or revert
  after the same M13 ambush/tiberium/Ion and M01 beach/ladder route is captured.

## Dev185 retained cinematic/effect physics models (2026-09-23)

- Hypothesis: Dev184's remaining M13 ambush/Ion and M01 beach stalls are not
  solved by warm-only create/release because the expensive render-object
  construction still happens when scripted physics models are first attached
  during live cinematics.
- Evidence: Dev184 runtime logs show `PhysClass::Set_Model_By_Name` taking
  about 2.57 s for `X0F_AG_EFFECTS` from `X0F_Harvester.txt` and about 2.85 s
  for `X0D_AG_Explode` from `X0D_A10_Crash.txt`. The flight recorder shows
  M01 frame 1 at 6.16 s, including 5.21 s simulation and 0.94 s render, right
  after warm-only preparation and at the user-reported beach plane/vehicle
  freeze.
- Change: Allow duplicate retained preparation slots, retain only selected
  scripted M13/M01 cinematic/effect aggregate render objects during loading,
  and consume them only in `PhysClass::Set_Model_By_Name` before falling back
  to original `WW3DAssetManager::Create_Render_Obj`.
- Guardrails: The earlier Dev181 broad cache remains rejected. Dev185 does not
  consume prepared render objects in bullets or surface effects, does not skip
  cinematic commands, does not force objectives, and does not alter AI,
  collision, animation semantics, or mission progression.
- Evidence retained: direct M13/M01 preparation assertions PASS, Dev184
  animation action completion contract PASS, development checkpoint PASS,
  campaign profile defaults PASS, 158 focused fast contracts PASS, ARM/SELF/VPK
  identity PASS, Vita3K install PASS.
- Decision: Adopt as the next runtime candidate because it targets measured
  multi-second live creation stalls while preserving Dev182's volatile-object
  safety boundary. Runtime acceptance is pending M13 ambush/tiberium/Ion and
  M01 beach evidence; no physical performance or A/V-sync acceptance is claimed.

## Dev182 volatile render-object warm-only correction (2026-09-23)

- Hypothesis: Dev181's retained live render-object cache moved first-use work
  into loading, but reusing those live objects for original cinematic real
  objects, missiles, explosions, trails, and particle emitters can age
  one-shot animation/particle state and corrupt actor/effect presentation.
- Evidence: The Dev181 user run and flight recorder reached M13 completion and
  M01, but user-observed regressions included disappearing helicopter
  engineers, the ambush rocket soldier walking in place, severe M13 ambush
  audio/video drift, and an M01 ladder freeze. Runtime logs show the live
  prepared cache being consumed during scripted creation, including
  `vxag_nod_heli`, `X1c_AG_xplosion`, `VxAG_X1Borca`,
  `X0Z_Orca01_Traj`, `X0Z_Orca02_Traj`, and `X0Z_Effects`.
- Change: Keep M13/M01 load-time model preparation, but immediately release
  created render objects after warming the WW3D asset/prototype path. Remove
  Vita-only prepared-object consumption from physics model assignment, bullets,
  and surface emitters so runtime objects are fresh original instances.
- Risk: This may reintroduce some runtime first-use cost compared with Dev181
  for objects whose prototypes were not fully warmed by create/release. It
  intentionally rejects reusing live volatile objects as unsafe.
- Evidence retained: focused source contracts PASS, 156 fast contracts PASS,
  ARM/SELF/VPK identity PASS, Vita3K title install PASS. No runtime A/B has
  been performed yet.
- Decision: Adopt as a correctness correction for Dev181's unsafe optimization.
  M13 ambush/Ion performance and M01 ladder/plane behavior remain pending
  runtime verification; no physical performance acceptance is claimed.

## Dev159 persistent runtime-log handles (2026-09-22)

- Hypothesis: Vita3K console/file-open flood from per-record runtime-log
  open/sync/close contributes measurable overhead in the M13 intro run.
- Change: retain file handles for both `A30_Vita_Log` and the legacy
  `Vita_Append_A22_Runtime_Breadcrumb` path while preserving per-record sync.
- Evidence: `campaign-dev159-persistent-all-logs-m13-installedtitle-1`
  compared against the valid Dev158 installed-title evidence.
- Result: runtime-log open records fell from 52 to 2 and total
  `export_sceIoOpen` console records fell from 1061 to 888. Dev159 reached
  frame 720 with 15.266 FPS, but frame 720 p95 remained 178292 us and frame
  703 still spiked 564717 us.
- Decision: keep as a diagnostics-overhead reduction, not a campaign
  performance acceptance. Continue with measured render/scene traversal and
  residual simulation spikes.

## Dev147 campaign preparation and MSAA (2026-09-21)

Source request: `/mnt/e/Renegade_Vita_Performance_Prompt.md`, "Execution prompt".
Dev148 M13 cinematic-stall continuation (2026-09-22): duplicate WW3D sync
and a separate camera-wall-clock experiment did not fix the render stall; the
latter disrupted authored actor sequencing. Both are reverted. The original
`TimeManager` clamps simulation time after a long render frame while audio
continues in real time, so eliminating the render stall is still necessary.
No audio-sync or performance fix is accepted.

An M13 loading-only referenced-texture prewarm prepared 183 textures in a
diagnostic ARM build. Its Vita3K/OpenGL run had zero texture requests through
frame 240 versus 39 in the prior object-timing probe, but by frame 480 it
reached p50/p95/p99/worst 100.5/275.9/389.2/13769.6 ms and 1 new texture
request. The earlier probe at frame 480 had 64.4/107.8/142.7/2482.1 ms.
These are not fixed-input repeats, but the severe stall persisted despite
eliminating early uploads. The prewarm was rejected and reverted. Evidence:
managed AppData `campaign-dev148-textureprep-m13-1` receipt, status
`TIMEOUT_UNASSESSED`; no physical-Vita measurement.

Follow-up source/evidence check: the production mesh boundary still feeds
vitaGL immediate-mode attributes for each original mesh/material batch, then
calls the project-specific indexed end path. At frame 480 the diagnostic
counter had about 29,539 mesh submissions and 2.53 million triangles
cumulatively; texture prewarm did not change this work. The isolated
texture-prewarm emulator stdout contained 13 `getstat`, 5 `open`, and 4
`mkdir` warning records, not a contemporaneous high-volume error flood.
These facts do not yet distinguish CPU attribute submission, shader first-use,
GPU queue backpressure, or Vita3K host-driver stalls. Next experiment must
separate those costs within the same frame without per-object disk logging;
do not apply another clock or texture-cache change as a stall fix.

Dev148 bounded mesh-boundary probe: a full-port-only ARM diagnostic build
measured each original mesh submission and indexed draw completion in memory,
logging one aggregate per 120 frames. In the isolated M13 Vita3K/OpenGL run,
frames 361-480 accumulated 6.46 s across 10,382 mesh submissions, but only
0.19 s across 25,450 indexed draw completions. The slowest individual mesh
was 371 ms; its draw completion was not the long operation. The run's frame
480 p50/p95/p99 was 58.7/93.5/282.5 ms, with 2.19 s worst from startup.
Evidence: managed AppData `campaign-dev148-meshboundary-m13-1`; candidate
SELF SHA-256 `4d55f724ae94e1eb9eb7d8281945b29d05c3bce1e140bf94a3d6907497ede4eb`.

A following full-port-only repeated-color suppression candidate compiled and
ran once against the same direct-entry route. By frame 720 it still had a
6.91 s worst frame (p50/p95/p99 82.5/377.8/471.6 ms); the indexed draw-end
maximum was 0.13 ms in frames 601-720. Differences in scene timing/object
counts prevent claiming an aggregate CPU win. The color change was rejected
and reverted; no audio-sync or 60 FPS improvement is accepted. Evidence:
`campaign-dev148-colorcache-m13-1`; candidate SELF SHA-256
`ab691c1d6f7f64a2b01073aecbaff0f7f28d42116b81f9d60da36d871900269c`.
Both runs timed out unassessed and do not prove physical behavior. The 6.91 s
frame exceeds the maximum individual mesh time by orders of magnitude, so
the next bounded probe must distinguish scene traversal, material/state
setup, and other backend calls rather than assuming indexed draw completion.
After reverting the color experiment, the ARM/package rebuild reproduced the
mesh-timer candidate SELF SHA-256 exactly; five mission-completion contract
tests passed. This is only diagnostic build consistency, not gameplay or
performance acceptance.

Separate isolated Vita3K/OpenGL Dev148 M13 probes measured foreground
`CombatManager::Render` as the slow phase. A timed frame at ambush frame 667
spent 1.290 s in `WW3D::Render(COMBAT_SCENE)`, including 1.287 s in
`scene->Render`; its world-space list took 0.977 s and dynamic list 0.305 s.
Another run observed 1.107 s in `scene->Render` at frame 726. `Flush`,
background, dazzle, and HUD were not the dominant phases. Per-object threshold
logs identify distinct original models (for example `MX0_BASEWALL` at 0.336 s
and `X0E_OBELISK_GD` at 0.307 s), but do not prove shader compilation,
texture upload, geometry cost, or driver synchronization as the cause. No
render policy change is adopted. Evidence: managed AppData isolated
`campaign-dev148-*` receipts; runtime status `TIMEOUT_UNASSESSED`, not hardware
acceptance. Development-only object probes were removed after diagnosis.

These are isolated Vita3K/OpenGL M13 diagnostic direct-entry observations, not
physical-Vita acceptance or a fixed-input three-repeat benchmark. The route
includes the authored intro with no synthetic movement. The same retail data
tree was used; shader/cache warmth and scene timing may differ between runs.

| Experiment | Preparation | Frame 600 FPS; p50/p95/p99/worst (ms) | Frame 600 simulation/render CPU (ms); clock drift (s) | Decision |
| --- | --- | --- | --- | --- |
| No dependency preload, 4x MSAA | none | 14.51; 66.5/142.2/145.9/3649.8 | 21.82/47.09; 5.69 | Comparison baseline only |
| Original global + mission `.dep`, 4x | original loading phase | 7.33; 23.3/282.1/513.9/15804.3 | 69.89/66.61; 28.05 | Rejected: severe late hitch and clock loss |
| Mission `.dep` only, 4x | 9.52 s before threaded map load | 16.96; 79.8/212.9/279.1/2212.7 | 15.12/43.84; 3.60 | Provisional: better early drift, late hitch remains; repeat and physical test required |
| Mission `.dep` only, MSAA off | 8.36 s before threaded map load | 12.09; 87.4/203.0/239.3/7039.2 | 34.32/48.42; 10.62 | Rejected for public default; 4x retained |

The original simulation stage timer places nearly all measured simulation CPU
time inside `CombatManager::Think`, which includes scene/render work; it does
not establish GPU time. Later mission-only runs reach a roughly 6.86-7.04 s
single-frame hitch and 14+ s clock drift. Audio uses real time while the
original simulation clock is capped after long frames, a plausible mechanism
for the observed desync, not yet a proven root cause. Do not solve this by
changing mission-script timers or forcing audio clock changes. Next experiment:
bounded frame-event capture around the late hitch, then fixed-route repeated
M00/M13 A/B on physical Vita before native acceptance. Diagnostic receipts:
managed AppData `campaign-dev147-{profile,preload,missiononly,msaa-off}-m13-1`.


Current continuation: Dev127 implemented measured CPU-work reductions and
Dev128 integrated native DDS chains; their reports supersede older pending
implementation entries below. Physical performance adoption remains open.
Dev134 is in canonical validation, with no physical test requested or performed.

| Current route | Evidence and candidate action | Remaining acceptance |
| --- | --- | --- |
| Discarded textured-character RGB | Production path calculated lighting then submitted white RGB. Dev134 retains diffuse alpha and first diagnostics while skipping the discarded calculation. 192000 full-color, 96000 submitted-skin and 15360 alpha cases pass; production draw ordering/state and sanitizers pass. Fixed host median/p95/p99/worst 164.5/221.1/317.0/317.0 -> 19.6/21.8/29.9/29.9 us; same scratch high-water. | Candidate implementation; ARM/canonical closure active. Matching native visual and physical fixed-route frame-time/memory results pending. See DEV134_SKIN_RGB_WORK.md. |
| Native YUV movie sampling | Actual Bink inputs are 800x600 limited-range YUV420; pinned VitaGL/GXM supports planar CSC textures. At unchanged 320x240, packed payload is 115200 rather than 307200 bytes. | Prototype pending transactional GPU replacement, plane/stride tests, color comparison and native timing. See DEV134_NEXT_RENDER_ROUTES.md. |
| Persistent geometry and render handoff | Original mesh/UV/color/user-lighting arrays expose mutable pointers without generations; direct mesh submissions bypass DX8 buffers. | Requires original mutation/lifetime tracking or a validated immutable snapshot and GPU retirement. Pointer-only caching is not safe; route remains open. |

Earlier ledger entries follow as historical hypotheses, not current implementation
status. Host gains never establish hardware FPS.

This ledger accepts changes only with a fixed content hash, camera/input replay,
settings, build mode, p50/p95/p99/worst frame timing, CPU-stage timing, memory
high-water, and visual/correctness comparison. The frozen A3.2-dev1 data is a
diagnostic baseline, not an A/B result for the corrected source.

| Hypothesis | Evidence | Proposed change | Correctness risk | Benchmark / decision |
| --- | --- | --- | --- | --- |
| The project needs explicit 60/50/30/20 FPS gates before optimizing larger M00/M01 scenes | User target is 60 FPS top-end, less than 50 FPS undesirable, and 30/20 FPS unacceptable for gameplay; prior tooling only exposed 16.7 and 33.3 ms slow-frame counts | Capture comparison now reports pacing tier plus 16.7/20.0/33.3/50.0 ms slow-frame counts and percentages; runtime logs now emit p99 and all four slow-frame bands | None to runtime behavior; reporting-only until built | **Adopted as evidence contract**; no performance gain claimed until matching physical A/B captures exist. |
| Existing renderer state cache cannot be tuned responsibly without knowing skip/applied ratios | Dev84 and A3.2 data show high cumulative state/bind counts, but do not distinguish unavoidable material transitions from redundant platform calls | Add counters for texture bind, sampler, stage-enable, combiner, and render-state skips in renderer logs, state.json, and frames.csv | Low; counters are diagnostic and preserve current state ordering | **Prepared, unbuilt**; use next fixed-route capture to decide whether cache expansion, call removal, or a different renderer path is justified. |
| CPU-side projected normal meshes lose homogeneous W and expand indexed triangles | A3.2-dev1 frame 2400 has render 18.938 ms, 0 indexed submissions; source inspection found CPU perspective division in the normal path | Preserve GPU model/view/projection W (implemented for correctness); evaluate indexed/buffered submission separately | Projection, clipping, UV interpolation, ordering | Correctness repair is ARM-built; performance decision **deferred** until corrected physical capture and visual checkpoints exist. |
| Immediate-mode expanded triangles cause avoidable vertex/submission work | Existing renderer still expands normal mesh indices; no post-fix measured cost split | Prototype a bounded indexed/buffered backend only behind a renderer switch | Mesh offsets, FVF translation, transparency ordering, VitaGL behavior | **Deferred**; require M00/M01/City replay A/B and screenshot fingerprints. |
| Texture/state churn dominates render CPU time | Failed log has 216,621 cumulative binds and 16,800 changes by frame 2400; values are cumulative, not per-material root cause | Add first-use state/resource evidence, then reduce redundant binds only where ordering permits | Alpha/depth/material semantics | **Deferred**; no batching or sort change without material-state capture and A/B. |
| 4x MSAA / fill rate harms pacing | A3.2 startup configuration used native 960x544 triple buffering and 4x MSAA; no controlled device comparison exists | Benchmark MSAA, resolution scale, and frame cap as independent profiles | Visual quality and image correctness | **Deferred**; needs physical fixed-route captures. |
| Deferred no-output audio boundary performs repeated work | Frozen log has 282 repeated messages | A3.5 rate-limits diagnostics and retains a stateful boundary without synthetic sounds | Original audio lifecycle | **Deferred** for performance; no post-fix timing evidence. |
| vitaGL's default 16 MiB system-RAM reserve leaves too little non-pool memory during M00 static-object creation | Physical A3.5-dev5 diagnostic samples at objects 0, 25, 50, 75, 100, and 108-116 were identical: system user free 16,777,216 bytes; CDRAM/phycont free 0; vitaGL RAM/VRAM/slow/all free 54,998,160 / 80,124,896 / 27,262,336 / 162,385,392 bytes | Consider a larger reserve only after direct internal-heap/high-water evidence identifies pressure | Reduces renderer pools; may move rather than fix exhaustion and can regress textures/geometry | **Rejected as the immediate object-116 fix**: no measured pool consumption across the stall window. Internal heap pressure remains unmeasured, so pool tuning is deferred. |
| M00 scene pre-warm repeats full original scene rendering and loading-overlay viewport transitions after assets are already resident | Guarded Dev84 physical log: 60 M00 pre-warm frames took 11,489 ms, with 22 resident textures, 23 binds, 0 uploads, 1,515 cumulative backend errors at its completion; the run then reached original M00 control | First add phase-separated timing for original scene render, original loading overlay, resolution/presentation changes, texture work, and forced delay; only then benchmark a reduced warm-frame budget or convergence-based stop against the same fixed M00 camera/content route | Reducing warm coverage can reintroduce shader/texture compilation hitches or change original loading presentation ownership | **Deferred**: the returned run includes later un-attributed physical input, has no fixed replay/camera identifier or p99, and has no A/B capture comparison. No scope, frame budget, or render behavior has changed. |
| Steady M00 pacing is limited by renderer state/bind churn | Guarded Dev84 physical frame-480 summary: p50/p95 ordinary frame time 33.344/48.957 ms, 431/480 frames over 33.3 ms, 975,308 cumulative state changes, 139,350 texture binds, 75,956 meshes, 3,291,682 triangles, and zero current backend errors | Record state-change categories and redundant-call skips in a fixed M00 camera replay; reduce only proven duplicate platform calls while preserving original material/depth/alpha/fog ordering | DX8 material, alpha, depth, fog, texture-stage, and viewport semantics; sorting or batching would exceed this investigation | **Deferred**: current evidence establishes a cost signal but not a causal category or controlled A/B result. No cache, batching, renderer-profile, or quality setting has been adopted. |
## Dev149 M13 ambush freeze attribution (2026-09-22)

The earlier scene-render hypothesis did not explain the repeated multi-second
ambush frame. In isolated Vita3K/OpenGL M13 direct-entry runs, Dev149 bounded
timers placed a 6.997 s frame in simulation (6.964 s) rather than render
(33.6 ms); Combat Think then attributed a matching 6.285 s frame to its post
phase (6.248 s). The final matching candidate captured frame 633 at 6.778 s,
with 6.740 s simulation and 37.6 ms render. `GameObjManager::Post_Think`
took 6.701 s; a single original object callback, ID `1500000007`, took
6.700 s. Observer deletion and pending script destruction each took about
1 us. This is CPU process-clock timing, not GPU timing. The object definition
and inner operation remain unverified, so no performance fix is adopted.

Evidence: managed AppData `campaign-dev149-postsplit-m13-3` and
`campaign-dev149-postowner-m13-2` Vita3K receipts/logs; final diagnostic
SELF SHA-256 `d4035771f2820779c6e33604fcd83d016287213ec433a43d6fcb8f59644ad482`.
The final run timed out unassessed, not physical acceptance. Next experiment:
record the object's definition and split its original post-think callback
around animation completion/observer dispatch and resource requests; then
apply a load-time or boundary fix only to the confirmed operation. Fixed-route
before/after frame p50/p95/p99/worst, clock drift, visual/script sequence,
and M00 regression are still required before accepting any optimization.
Dev150 narrowed the same M13 event to original `Test_Cinematic` slot 19,
`X00_AG_Explode` in unchanged M13 retail control text. Within the timer's
6.169 s, object allocation was 0.377 ms and `Commands->Set_Model` was
6.166 s. The original latter path creates a WW3D render object by name and
installs it into the physics object/scene. A loading-time creation/release
of this exact model is now a testable preparation hypothesis, not an accepted
fix; it may merely move cost or fail to remove scene-notification cost.
Evidence: managed AppData `campaign-dev150-slot19-m13-1` matching
SELF `1ba9212ececdb4406e4e6dccb59da0740c12444e1392b6deb6296dbf0136493a`.
Dev151 tested the exact loading-time WW3D object pre-create/release hypothesis.
In the isolated M13 Vita3K/OpenGL route, it added 5.885 s to loading and the
live `Set_Model("X00_AG_Explode")` still took 6.005 s (Dev150: 6.166 s).
This is **rejected**: no demonstrated live improvement and greater total
cost. It suggests a per-instance or scene-installation cost rather than only
first prototype load, but that is an inference, not a proved root cause.
Evidence: managed AppData `campaign-dev151-modelprep-m13-1`, matching
SELF `c7c65ef3001f21ace248b68d3963dc7b0e6b61df262f69eabbb1c8721cae025d`.
Dev152 removed the rejected pre-create and split the original physics setter.
In the same M13 route, `WW3DAssetManager::Create_Render_Obj` consumed
6.084 s, while `PhysClass::Set_Model` scene installation consumed 39 us and
reference release 1 us. Thus the repeated per-instance asset-manager create,
not physics scene notification, owns the stall. Whether prototype creation,
nested child requests, or on-demand file I/O dominates is still unmeasured.
Evidence: managed AppData `campaign-dev152-physmodel-m13-1`, matching SELF
`ce01e50e2cf93e273cacfdb91ab3005a9b29f2c94405c47d56964dbabf1307f3`.
Dev153 split the asset manager: `X00_AG_Explode` had an existing prototype
whose resulting object has HLOD class ID 25; lookup 4 us, load phase 1 us, `proto->Create()`
6.123 s. No nested child call exceeded 100 ms in the bounded trace.
Repeated on-demand file loading is not the immediate 6 s cause. The original
prototype's inner work remained to be timed; no optimization is accepted.
Evidence: managed AppData `campaign-dev153-assetdepth-m13-1`, matching
SELF `d73dfcfcd3f25df0c3d889b5472382e49188631dba7f6ac21f363bb96d24e225`.
Dev154 identified the actual prototype as an aggregate, not an HLOD or HModel
prototype. `X00_AG_Explode` has 91 child render objects; in the matching M13
run their creation consumed 6.634 s while attachment consumed 0.207 ms.
The base model took 0.184 ms. Repeated bounds updates during attachment are
therefore not the freeze cause; no performance change is accepted. Next test
is an assembled retained template with fresh clones, compared against this
same route and M00. Evidence: managed AppData `campaign-dev154-children-m13-1`,
matching SELF `e89f3402e43ac431400cea0a6cdfcc6127114f74b0d161316227e07ef830e77d`.
Dev155 retains one fully assembled original `X00_AG_Explode` aggregate
template at M13 loading and returns fresh `Clone()` instances thereafter.
In final-hash M13 Vita3K/OpenGL evidence, preparation cost 8.268 s and the
first live rocket's original script `Set_Model` cost 9.016 ms versus Dev154's
6.638 s. This is an adopted event-local win, not an overall 60 FPS result.
Final-hash M13 frame-480 cumulative p50/p95/p99/worst remained
101.4/328.5/378.4/2559.1 ms; route frame distributions are not directly
comparable because the bounded runs reached different content. Template
memory high-water and physical visual/audio result are unmeasured. Full-port
M00 direct entry reached frame360. Evidence: managed AppData
`campaign-dev155-final-m13-1` and `campaign-dev155-final-m00-1`, SELF
`980640b313ccca8a9dde948497296ee0681b6e3122f226a903aa7d721f8fc96f`.
Dev156 extends retained aggregate templates to measured M13 `ag_rocketl`.
Final-hash live clones took 162 and 81 us versus Dev155's roughly 101-151 ms
per create. Loading preparation added 134 ms. An `ag_fiery_ex06` attempt did
not enter the aggregate path and was removed before the final build. This is
an adopted event-local win only: final frame-480 p50/p95/p99/worst were
90.3/412.9/449.4/2846.0 ms, so overall performance did not improve cleanly.
Evidence: managed AppData `campaign-dev156-final-m13-1`, matching SELF
`f738f786a2dabe07cb701e77b14a436494f1bb32de981c297a722766a2192001`.

Dev157 adds a separate full-port-only retained HLOD template for
`ag_fiery_ex06`, the non-aggregate fiery effect observed after Dev156. In
managed AppData `campaign-dev157-fiery-hlod-m13-1`, loading preparation took
92.263 ms and no later `ag_fiery_ex06` slow-create record appeared. This is
only a narrow event-local improvement. The same route still measured frame-720
average 18.744 FPS with p50/p95/p99/worst 44.3/138.0/148.6/1928.0 ms, and a
later frame 784 cost 642.050 ms. Audio stats still reported
`11-ambient beach.mp3` as the active stream through the intro; that filename is
present in `M13.mix`, so this is not proven cross-map leakage. The remaining
accepted blocker is route-level renderer/scene traversal and audio timing under
frame starvation, not this individual HLOD create. Evidence: matching SELF
`de39b87f8e55c616891835db8f6f35013e93891ff18e3cbf80d4b89f48a4f714`, runtime
SHA-256 `f1ed16493bb4c8a885949091ccdd003272f16eea5ea5f1fad7d7ce5600909986`.
# Dev201 Glacier texture and text replay (2026-09-27)

Dev200 Glacier showed `l02_ice.tga` source fallback and checkerboard binds;
Dev201 scopes user-retail M02.mix to that remote map. No measured performance
claim: the Dev201 live server had rotated to Skatepark, and its 150-second
runner timed out. The UTF-16 player-name formatting change is correctness work,
not an optimization. Re-run fixed Glacier camera/content before comparing
frame-time median/p95/p99/worst or adopting performance conclusions.
