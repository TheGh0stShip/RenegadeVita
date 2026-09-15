# Renegade Vita project contract

## Read first and treat disk as authoritative

At the start of every task, read these files in order before changing code:

1. `reports/PROGRAM_CHARTER.md`
2. `reports/PORT_STATUS.md`
3. `reports/BUILD_STATE.json`
4. `reports/CODEX_HANDOFF.md`
5. `reports/MILESTONE_ROADMAP.md`
6. `reports/CAPABILITY_MATRIX.md`
7. `reports/KNOWN_GAPS.md`
8. `reports/LIVE_PROGRESS.md`

Resolve contradictions using immutable physical-Vita evidence and matching
artifact hashes first, then current source/build/test evidence, then the
current state reports. Never alter frozen evidence to make reports agree.

## Mission and boundaries

Port the official EA/Westwood C&C Renegade source to a **native ARM PlayStation
Vita application**. Preserve original engine/game architecture above platform
boundaries: original filesystem/MIX/W3D/WW3D/Combat/Commando/network behavior
must remain the owner. Replace only platform boundaries such as Win32,
DirectInput, DX8, audio/video providers, timing, and threading.

Do not create a replacement game loop, scene graph, physics engine, runtime
asset format, PSP/Adrenaline app, or custom W3D-world renderer. Do not package
or redistribute retail assets. Retail data stays unchanged at
`ux0:data/renegade/retail/Data/`; writable state belongs under
`ux0:data/renegade/user/`.

The active source candidate is normally
`/home/steve/projects/RenegadeVitaBuilder/workspace/active`; historical A2.0
is under `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder/workspace/A2.0`.
Confirm authority from evidence, not directory names. Keep upstream pristine;
use centralized compatibility headers and deterministic, zero-fuzz staging
patches. No `.orig`/`.rej` debris.

## Standing user authorizations

For dev82 physical-test work, the user has explicitly authorized bounded PS Vita
mutation needed to make and test a hardware candidate: replacing only
`ux0:/app/RNEGA3101/eboot.bin`, uploading the matching VPK to the user tree,
installing the title-scoped taiHEN demo-recorder plugins, updating tai config
with backups and hash receipts, launching/killing `RNEGA3101`, driving bounded
input, and pulling logs, captures, recordings, and PSP2 dumps through VDB or
VitaCompanion/FTP. Do not mutate unrelated apps, firmware, plugins, or user
files, and always release synthetic inputs.

The user also authorizes inspection, pulling, interaction with, and controlled
modification of the user's own retail Renegade data when it materially helps
diagnostics, WW3DHub/Tiberian Technologies comparison, or dev82 correctness.
Before changing any retail file, make a candidate-scoped backup and record
hashes. Do not commit, upload to GitHub, package, or redistribute retail data,
saves, credentials, or unrelated user files.

When resuming, treat the bash workspace above as source authority. The E: mirror
can lag and is a copy target only after active-tree validation. If historical
screenshots/logs are requested, inventory all local evidence roots, the physical
Vita via VDB/VitaCompanion FTP, `/mnt/c/Users/steve/AppData`, and E: evidence
trees before declaring anything missing.

## Current program

The accepted physical baseline is A3.1.4. A3.2-dev1 is frozen failed physical
evidence, never overwrite it. A3.5-dev1 is the current correctness and flight
recorder candidate work; it is not physically accepted until a new Vita test
returns matching evidence.

The roadmap is v3.5 correctness/diagnostics, v3.6 resource-memory and
multi-scene infrastructure, v3.7 measured renderer/frame pacing, v3.8
authentic frontend/HUD/audio, v3.9 representative campaign RC plus controlled
networking foundation, and v4.0 a genuinely playable representative campaign
release. Exact gates live in `PROGRAM_CHARTER.md` and the roadmap.

## Engineering routine

Continue through inspect → minimal coherent fix → focused test → retained host
validation/sanitizer as appropriate → ARM build → ELF/SELF/VPK inspection →
hashes/reports → hardware candidate. A build, host test, or report is progress,
not completion. Continue until a fully evidenced hardware candidate or a real
external/user blocker. Do not auto-deploy or touch the Vita filesystem.

Canonical build: `bash ./tools/build.sh`. Artifacts/logs go to the managed
`/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder/{dist,logs}` when
available. Preserve matching ELF, map, symbol list/header, source/patch
identity, compiler/host logs, VPK inventory, SHA-256 manifest, expected
runtime breadcrumbs, and telemetry-only diagnostic bundle for every candidate.
The VPK and diagnostics must exclude retail assets, saves, credentials,
arbitrary user files, and raw memory dumps except explicitly returned crash
dumps.

Treat host, Vita3K, and physical Vita as separate evidence classes. Host and
Vita3K never prove physical acceptance. Physical Vita is authoritative for
controls, rendering, frame pacing, memory/storage behavior, suspend/resume,
LiveArea exit, and soak stability. Never claim visual correctness from logs.

## Progress and reporting

On starting a work unit, before a long build, after material evidence, and at
least every 10–15 minutes during sustained work, publish a compact update:

```
Renegade Vita — v3.5 active
[████░░░░░░] 4/10 current evidence gates complete

Now: concise active action
Completed: evidence-backed work
Evidence: tests/builds
Next: exact action
Blocker: none or concrete blocker
```

The bar counts completed evidence gates only. Mirror material gate changes in
`reports/LIVE_PROGRESS.md`. Keep reports concise and non-contradictory.

Keep the active plan/goals current. At each resume, user scope change, physical
or emulator evidence return, blocker discovery, completed build/test gate, or
handoff, update the visible plan before continuing. If the persistent goal tool
cannot be rewritten because an unfinished dev82 goal already exists, preserve
that goal and record the expanded dev82 breakdown in the visible plan and the
durable reports instead of silently relying on memory.

## Performance, diagnostics, and safety

Adopt performance changes only for a measured cost or demonstrated algorithmic
defect, behind correctness checks and a fixed replay/camera/content benchmark.
Record hypothesis, risk, before/after median/p95/p99/worst, subsystem timing,
memory high-water, visual result, and adopted/rejected/deferred decision. Do
not use `-Ofast`, global fast-math, or speculative broad rewrites. Never trade
away original physics, collision, animation, networking, serialization, or
asset semantics for a benchmark.

Maintain bounded, versioned diagnostics: build identity, lifecycle/crash flight
recorder, sampled performance/resource/memory/input/render events, and
candidate-scoped ZIP/dashboard. Expensive instrumentation is sampled or trace
only. PSP2 symbolication must distinguish verified fields/frames from
heuristics and use only matching artifacts.

## Networking and future compatibility

Preserve original WWNet/cNetwork/session/packet/replication ownership. Do not
build a bespoke gameplay-facing multiplayer loop or revive obsolete GameSpy as
a hard dependency. Maintain a narrow provider seam below original game/UI
code: Disabled, Direct-IP, LAN, optional GameSpy-compatible replacement, and
future W3DHub/TT provider. Public services are optional; no credentials,
unlicensed TT code, Windows launcher port, or public-service claim without
authorized protocol evidence and controlled compatibility tests. Networking
must not block the first stable campaign path.

## Collaboration and source-control

Do not reset, force-push, overwrite unrelated work, or create arbitrary new
workspaces. Use `apply_patch` for edits. Do not run two writers in the shared
tree concurrently. Exact `gpt-5.3-codex-spark` may be used only for one small,
isolated, verifiable task when selectable; otherwise record unavailability and
continue coordinator-owned. Never silently substitute another model; validate
all delegated output independently before integration.
