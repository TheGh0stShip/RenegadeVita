# Live engineering progress

## 2026-08-16 — v3.5 active

`[█████████░] 9/10 current evidence gates complete`

- Now: A3.5-dev2 physical Vita acceptance.
- Last focused step: A3.5-dev3 observer-loader chunk-open breadcrumb routing: deterministic WWLib `Open_Chunk` null-parent/required-root/short-read breadcrumbs and bounded contract coverage.
- Completed: A3.2 artifact identities verified; button state contract 10/10;
  axis/camera contract 22/22; weapon-style table deterministic repair; shader
  state contract 4/4; renderer lifecycle contract 11/11; bounded PSP2 note
  inventory; rate-limited deferred audio diagnostics.
- Completed: host observer-loader contract now directly exercises
  `PersistentGameObjObserverManager::Load` plus `ChunkLoadClass::Open_Chunk` null-file,
  truncated-root, parent-exhaustion, and repeated-open balance paths with `46` checks.
- Evidence: focused host tests pass and the changed ARM sources link locally.
- Retained host/sanitizer closure: PASS. The first canonical package attempt
  found and corrected a stale 14-versus-15 capture-test fingerprint; fresh ARM/VPK/hash/ZIP is next.
- ARM/VPK/hash/ZIP: PASS. Candidate VPK SHA-256 is
  `26445efb9ece7f64a86b38e6b49767233a7c3321f19c90e96ead6ef7c6073244`;
  it contains only `eboot.bin` and `sce_sys/param.sfo`.
- Remaining gate: authoritative physical Vita controls/visuals/lifecycle/soak
  evidence.
- Blocker: user-performed physical test required; no automatic deployment was attempted.

The current package is `RenegadeVita-A3.5-dev2.vpk` SHA-256
`8ac77116c19d9eaf5093634ad9b5ff888ce9d42dcd42f34727ea52b9603a8b53` with
matching `A3.5-dev2-BUILD-DIAGNOSTICS-20260816-124825.zip`. Its packaging
reused the completed canonical host gate after only provenance/build-script
changes, then deterministically restaged and rebuilt the ARM candidate. ELF,
VPK and every SHA-manifest entry verified PASS. Physical evidence remains the
only open A3.5 gate.

Focused diagnostics, provenance, performance, asset/cache auditing, warning
trend, parser-fixture, and network-inventory work remains subject to narrow
file ownership and deterministic validation. The post-run diagnostic tool
recognizes this project's `*-SHA256SUMS.txt` manifests; its frozen VPK/ELF
manifest checks and two-run output comparison pass. A missing runtime log is
reported explicitly as `unknown`.

## 2026-08-16 — v3.6 host infrastructure

`[██░░░░░░░░] 2/10 current evidence gates complete`

- Added `tools/renegade_asset_manifest.py`: deterministic, read-only,
  content-hash inventory with required-archive validation and case-conflict
  detection. It does not extract, convert, or package retail assets.
- Unit tests: PASS (3 tests). Real local retail `Data` inventory: 51 files,
  required files present, no case conflicts, `always3.dat` present, digest
  `a3cc696b1d938c2780f1514875234a2ea9a9aac7b57bd5ac6f0d1599f01f4264`.
- This is host-only evidence; Vita cache/residency/memory/load behavior and
  second-scene validation remain open.

- Resource-boundary telemetry now accounts fixed-size `Read`/`Write` calls and
  bytes (13/13 focused host contract; ARM link PASS). No paths or file content
  are recorded, and original MIX routing remains unchanged.

The original-engine M01 archive preflight now passes: `MixFileFactoryClass`
enumerated 231 entries and found LDD/LSD/DEP content. It is integrated into the
canonical host runner but is not yet a full M01 PhysicsScene load.

M01 now has a separate original `CombatManager::Load_Level_Threaded` host proof:
two lifecycle cycles and 120 render/update frames each pass with zero rejected
or unsupported submissions. This remains host-only.

Cache-key v1 tests pass: source digest, cache/tool schema, and canonical
conversion options deterministically select a cache identity; invalid source
manifests are refused. No converted retail data is generated.

The expanded canonical host gate now passes M01 preflight and two original
Combat load/render/teardown cycles in addition to the retained M00 sanitizer
cycles. Evidence remains host-only.

Capture telemetry schema v2 is host- and ARM-link-validated. It records a
bounded periodic low-water free-memory sample for Vita system/VitaGL pools;
the capture self-test passes 17/17 and the capture comparison tests pass 2/2
with backward-compatible schema-v1 input. No device memory conclusion is made
without a returned physical capture bundle.

`C&C_City.mix` now passes a host-only original Combat load/render/teardown
smoke twice (120 frames each, first frame 43 meshes / 4,115 vertices / 2,963
triangles, zero rejected/unsupported). It is explicitly not a multiplayer
gameplay or network claim.

The host-only v1 archive-index precursor now enumerates through original
`MixFileFactoryClass` rather than a replacement parser. M01's 231-entry index
is byte-identical across two writes; City indexes 83 names. No retail content
is extracted, converted, or packaged.

The frozen A3.2 frame-2400 performance record has been re-extracted directly:
39.418 average FPS, p50/p95 21.874/24.446 ms, simulation/render 6.427/18.938
ms, and zero indexed submissions. It is now a hypothesis baseline only;
no optimization has been adopted without corrected-candidate A/B evidence.

Vita3K inspection is now recorded: the configured data root contains a
historical A3.1 `RNEGA3101` app only, with no configured emulator executable or
session logs. No emulator state changed; the documented loop remains a future
rapid-regression aid and never physical acceptance evidence.

The asset manifest now has explicit M01 and City profiles. Unit contracts pass
9/9 across capture/manifest/cache-key tools, and both real profiles are valid
against the same local 51-file content digest. The canonical host runner
regenerates them without extracting retail content.

The host cache-format precursor now writes versioned M01 index metadata and
verifies it against manifest/options identity and artifact hashes. The focused
contract suite passes 14/14; unsafe, stale, missing, and corrupt cache states
are explicit. Native device consumption is still unimplemented.

Final canonical revalidation now passes after correcting the runner to invoke
cache tools via `python3` rather than relying on their executable bits. The
retained M00 normal/ASan/LeakSanitizer/targeted-UBSan cycles, M01 two-cycle
original Combat route, and City two-cycle original Combat smoke all completed;
the complete host log is
`<managed-log-root>/a30-20260816-114055-host-runtime.log`.
The real M01 cache sidecar verifies `valid` for key
`55d93acb1240e2b7ddb4416660d0a3b0e7330eb7499eed10099fcd177c762538` and the
two generated index writes share SHA-256
`7a277d47fd50388ccec9c7841d3127cb452903b502f67b8dfa2df82605531b34`.

`[█████████░] 9/10 current evidence gates complete`

- Now: persist host v3.6 evidence and prepare the next native cache-consumer
  boundary without bypassing original MIX loading.
- Next: optional device cache validation, resource/memory/storage capture, and
  the pending A3.5-dev1 physical correctness test.
- Blocker: no engineering blocker; all device conclusions remain untested.

The next native v3.6 boundary is now implemented and host/ARM-closed. The
startup-only `Renegade_Inspect_Mix_Index_Cache` probe is constrained to the
existing `cache/` namespace and validates a bounded v1 M01 filename-index
structure. Its 9/9 contract covers absent, valid, malformed, retail-path, and
traversal cases. Invalid or absent indexes only produce a diagnostic state;
the original retail `MixFileFactoryClass` path remains authoritative.

The canonical gate including this contract passed at
`<managed-log-root>/a30-20260816-115428-host-runtime.log`:
M00 normal/ASan/LeakSanitizer/targeted-UBSan, M01, and City cycles all pass.
The current production executable ARM-links and exports the cache-health
symbols. No VPK was repackaged and no physical cache behavior is claimed.

## 2026-08-16 — v3.6 resource telemetry and lifecycle correction

`[█████████░] 9/10 current evidence gates complete`

- Completed: rooted original-file-factory telemetry contract 12/12; counters
  record Get/Return, read/write resolution, prepared-resolution hits, and
  open/availability/create/delete attempts/failures without names, payloads,
  allocations, or a replacement loader. The Vita runtime emits one teardown
  summary; original `MixFileFactoryClass` ownership is unchanged.
- Corrected: the next canonical host run exposed an 80,256-byte
  `PathSolveClass` retention after the direct harness omitted the original
  `PathMgrClass` process lifecycle. Both host and Vita paths now initialize it
  after `WWMath` and shut it down after `WW3DAssetManager`, precisely matching
  original Commando application order.
- Evidence: focused two-cycle M00 ASan/LeakSanitizer rerun is PASS at
  `build/host-a31-asan/a36-pathmgr-lsan.log` with no sanitizer finding; the
  ARM EABI5 closure links and exports `PathMgrClass::{Initialize,Shutdown}`
  and `Renegade_File_Factory_{Reset,Get}_Statistics`.
- Next: rerun the full canonical host gate once, then obtain physical A3.5
  evidence before any candidate promotion. The in-tree rebuilt VPK is not a
  candidate: it lacks a matching diagnostics package and physical validation.

Canonical revalidation is now PASS at
`<managed-log-root>/a30-20260816-122251-host-runtime.log`:
the retained M00 normal/ASan/LeakSanitizer/targeted-UBSan cycles and the M01
and City two-cycle original Combat paths all completed. The focused PathMgr
LSan proof remains at `build/host-a31-asan/a36-pathmgr-lsan.log`.

## 2026-08-16 — A3.5-dev3 hardware candidate

`[████████░░] 8/10 current candidate evidence gates complete`

- Completed: canonical host execution/sanitizer validation, ARM EABI5 link,
  VPK packaging, compressed-VPK validation, and generated-artifact hash
  verification for A3.5-dev3.
- Evidence: build log
  `<managed-log-root>/a35-dev3-20260816-135706-build.log`
  exited 0; diagnostics bundle
  `A3.5-dev3-BUILD-DIAGNOSTICS-20260816-135706.zip` is present; VPK SHA-256 is
  `286eaf0bd0bef9bd62802228df0e947c1d0310085f750320deed7bd49d837ded`.
- Next: manual physical Vita validation of controls, perspective, muzzle alpha,
  release behavior, pause/resume, and clean LiveArea exit. No physical result
  is claimed.

## 2026-08-16 — A3.5-dev3 physical-crash correction

`[████░░░░░░] 40% — exact dev3 crash reconstruction`

- Verified: the returned dump and dev3 ELF/map/symbol/VPK identities match the
  supplied SHA-256 values. VitaSDK ARM Thumb disassembly proves PC
  `0x810EAFBE` is the `bl ChunkLoadClass::Open_Chunk()` instruction in
  `PersistentGameObjObserverManager::Load`, not the historical HumanState
  crash.
- Corrected: the Vita controller boundary no longer reverses left Y and no
  longer defaults camera invert-Y on. The revised 22-check input contract
  passes on host.
- Corrected: future candidate packaging writes an explicit no-matching-dump
  status instead of copying the old A3.2 symbolication report.
- Pending: establish why the observer loader reaches an invalid FileClass or
  chunk state; no new VPK is promoted while that root cause is unresolved.
- Added: combat observer loader diagnostics patch (`combat-a35-observer-load-diagnostics.patch`)
  applied via staging (`tools/stage_sources.sh`), plus new deterministic host contract
  target `a35_persistent_observer_loader_contract_selftest` in
  `tools/host_a30_definitions/CMakeLists.txt`.
- Added: `port/validation/persistent_observer_loader_contract.cpp` directly covers
  `PersistentGameObjObserverManager::Load` with deterministic fixtures and a narrow
  registered factory hook: required-root open/ID failures, truncated headers, known
  vs. unknown children, repeated invocation, and chunk depth/close balance.
- Validation: `a35_persistent_observer_loader_contract_selftest` and `a36_file_factory_telemetry_contract_selftest`
  both pass (including ASan and UBSan build routes) with exit status `0`.
- Still pending: physical Vita breadcrumb evidence for the `0x810EAFBE` session remains
  unverified; this step intentionally validates only deterministic host fixtures.

## 2026-08-16 — A3.5-dev4 candidate identity correction

`[██░░░░░░░░] 20% — candidate integrity gate, no physical acceptance`

- Invalidated: `A3.5-dev4` physical evidence is not a valid candidate result.
  Its VPK/report filename was dev4, but the returned ELF retained dev1/A3.1
  runtime labels and the dev1 runtime-log path. The return does not prove the
  observer, axis, player, NPC, weapon, or camera paths ran.
- Returned static capture: framebuffer readback is valid, but the capture state
  records static-world rather than interactive-player conditions. The empty
  orderly-exit bundle is a failed evidence result, not a clean exit claim.
- In progress: generated-at-configure build identity, final ELF/SELF/VPK
  lineage verification, unified runtime log identity, phase-labelled capture
  metadata, post-write artifact checks, and a fixed-width overlay formatter.
- Gate: no successor VPK is called hardware-ready until a fresh ARM build and
  retained diagnostics prove candidate identity, nonempty evidence artifacts,
  and the candidate-specific runtime-log path.
- Added: the live ARM interactive path now emits a first
  `interactive-player-owned` capture only after original Combat reports both
  its player object and camera. Static-world, simulated-host-interactive, and
  device-interactive evidence remain explicitly distinct.
- Built: fresh canonical `A3.5-dev5` host/ARM/VPK candidate. The complete host
  gate and focused contracts pass; the ARM target selected 424 original plus
  21 port translation units and completed 456 build actions.
- Verified: final VPK SHA-256
  `e69919b557b8b2a807ac6437310d4c62072635ce1a493e63eee604a0c935287c`;
  final ELF SHA-256
  `bf1a250554f0666fbc3814f0a47b784cd399a410bd823bf12885c8a92ebd2e05`.
  All 15 identity/lineage checks pass and the VPK contains only `eboot.bin`
  and `sce_sys/param.sfo`.
- Physical gate: pending. The tester must stop immediately unless startup says
  `A3.5-dev5` and `a35-dev5-runtime.log` is created. No visual defect or
  milestone acceptance is claimed from host/ARM evidence.
