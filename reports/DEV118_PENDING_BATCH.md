# Pending engineering batch — user controls gameplay

Current: Dev118 consolidated objective varargs, tutorial hints, reload
diagnostics and original per-frame NPC path service package is built. 130 fast
contracts and matching artifact identity pass; see DEV118_NPC_PATH_SERVICE.md.
Dev117 recovery-r2 is stalled in the finale with advancing frames and scripted
control lock; Power Plant checkpoint preserved. No session replacement yet.
The PID 10604 references below are historical and superseded by ALPHA_STATE.md.

Latest addition: objective-message varargs correction passes original string
formatting and ARM-object tests; Hotwire/WF original checkpoint archived.
Sky rectangles and moving elevator black artifacts remain unresolved.
See DEV118_VISUAL_DEFECTS.md. No new package or runtime acceptance.

## Crash recovery — 2026-09-14

Recovered the tutorial-help work completed after the previous handoff. Thirteen
English PC-key HUD hints now use Vita controls at the original ScriptCommands
presentation boundary. Unknown IDs and other languages retain TranslateDB;
HUDInfo copies the temporary wide string, and original sound dispatch remains.
Retail assets and original script/objective ownership are unchanged.

Retained evidence: `build/dev118-help-focused.log` passes 19 tests;
`build/dev118-help-staging.log` passes zero-fuzz staging with 165 ordered
patches. Recovery compiled both affected ARM objects, scriptcommands and
weaponview, in the existing fast tree: `build/dev118-recovery-arm.log`, exit 0.
`git diff --check` passes. This is object compilation, not linked/package or
runtime proof; the installed Dev117 package does not contain these changes.

Read-only recovery verified Vita3K PID 10604 at the expected executable and
matching session start. No input, launch, shutdown or installation was sent.
The Mobius master remains 96576 bytes with the SHA-256 below unchanged.
No agent was delegated; exact gpt-5.3-codex-spark is unavailable.

Next: accumulate further demonstrated corrections and assess user-controlled
M00 progression before another runtime package. Tutorial hint visibility,
Mobius reload, complete M00/ending and measured moving/firing performance
remain pending. Physical Vita/PSTV access remains held.

Previous work unit made progress: Dev117 package/visual/replay evidence and
the original Mobius checkpoint are retained. The demo goal remains active;
full M00/ending, sustained 60 FPS and physical acceptance are incomplete.

User explicitly owns movement/camera/gameplay inputs. Agent owns checkpoint
creation and engineering. Do not resume automated navigation or repeated
screenshot-driven movement. Current user session is Dev117-progression-20260914-r1,
owned Vita3K PID 10604 (revalidate receipt/process before acting), runner
session 40046, originally bounded to 1800 seconds. Do not interrupt the user's
session for checkpoint reload tests. Native automated input is disabled.

At the user's reported Mobius location, only the original Select+Square save
shortcut was sent through the admitted emulator keyboard mapping. Its receipt
confirms both keys released and no navigation input. Existing quicksave A/B
bytes were backed up with hashes to build/dev117-mobius-checkpoint/previous-slots/
before clearing the live quicksave filenames, avoiding the known emulator
shorter-overwrite defect. Fresh quicksave A structurally validates as original
M00_Tutorial.lsd, 96576 bytes, SHA256
72d0eb6f7f239f2cd985f8d541f8c861e82d038a3a12eb2c84ee6add1ebac521.
Immutable master: build/tutorial-checkpoints/m00-mobius-dev117/.
Location is user reported; reload and segment completion are unassessed.
Retail files and checkpoint contents were not edited or packaged.

Pending source corrections, not in the installed Dev117:

- Reload diagnostics now log only state transitions, removing the demonstrated
  per-frame reload log write. Retains reload entry/exit and original animation.
- Checkpoint archival accepts ordinary --evidence without falsely recording
  OPERATOR_ATTESTED_PASSED. Existing --passed-evidence remains explicit.
- Owned-window quicksave helper supports checkpoint creation while automated
  gameplay input stays disabled; only the original save shortcut is admitted.

Validation: 23 focused checkpoint/development/conversation tests pass in 0.708s.
Original-byte archive/restore and immutable master guards are exercised with a
synthetic save structure; actual Mobius save passes strict structure validation.
No new ARM build or package. Accumulate the next coherent batch before packaging.
