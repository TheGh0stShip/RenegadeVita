# Dev117 rifle animation and EVA margins

User resumed on 2026-09-14, then prioritized rifle hand pose, grey EVA bars,
and measured 60 FPS polish over further uncorrected tutorial playthroughs.

Dev116 run `D:/Vita3K/RenegadeEvidence/Dev116-gunner-20260914-r1` reloaded
unchanged Gunner save 4526385983138b19c24eeae9e3eccf36ccc6710133d918cefe71b1c72a381d97.
Capture 173336005Z shows gameplay; 173343571Z shows readable EVA; 173354088Z
shows resumed gameplay. Input receipts 01–06 acknowledge release. The process
later ended with runner status PROCESS_FAILED and null exit code; cause is
unassessed. A later pause request received no acknowledgment after termination.
The native input enable flag was removed after the process stopped.

The matching run's runtime log contains malformed weapon/hand animation names
for both PIST and RIFL and explicit fallback to F_SKELETON.F_HA_PIST_IDLE.
Two original StringClass::Format calls passed non-trivial objects to varargs.
Dev117 converts those arguments to const char pointers at the original calls.
Original models, skeletons, animation selection and retail files remain owners.
Synthetic reload bob/restart patches are retired; their historical files remain.
The original animation controller and accepted-reload latch remain active.

EVA's aspect-preserved original artwork leaves native screen margins. The
original GameModeManager began that frame with the suspended world's clear
color; Dev117 selects black when Menu is active and Combat is absent or
suspended. Active gameplay retains BackgroundMgr's clear color.

Validation: 22 focused checks pass, including 80 actual production formatting
expressions executed with original StringClass. A negative control rejects the
old calls. Zero-fuzz staging passes with 164 ordered patches. Canonical Dev117
stopped at a host Targa layout mismatch; no ARM package was produced.

The constructor dependency selected pristine upstream TARGA.H while its caller
used the patched header. The centralized targa.h shim now explicitly forwards
to staging. Only eight affected host objects and the existing executable were
rebuilt. Both original M00 cycles then passed ASan/LeakSanitizer. The full
pipeline was not restarted. Retained logs: dev117-incremental-asan.log and
dev117-focused-m00-asan.log under build/.

Renderer diagnostic guards now test the once-only latch before inspecting
texture names or generated-coordinate state. Focused executable tests use the
production conditions and verify identical admission decisions and zero name
scans for one million post-latch vertices on each submission path. This is a
demonstrated redundant-work correction, not a measured native FPS improvement.
The Targa include-order regression also passes. Fast tooling now explicitly
honors the development checkpoint option with a default-off setting.

User correction: full canonical builds only at milestone/release gates. During
development, use existing object trees and focused tests; accumulate coherent
fixes before one fast runtime package. No repeated new canonical build trees.

The stationary baseline initially failed before guest launch: Vita3K changed
from executable c5976240... to b31cc4c6... (4095). Its bundled bicubic OpenGL
shader used four obsolete texture2D calls. A candidate-scoped backup and exact
four-call texture replacement are retained under
build/dev117-stationary-benchmark/emulator-shader-backup/. Original shader hash
9fa3658ded5ef92617a8fb9f1e4f4818ade997a44c0061bdff77619f95b76b50;
corrected hash 5d91004fc7d7e88626b687fd360c2bcdc90132927b32945d9ca0f26d3ef17c4b.
No emulator executable or global configuration was changed by this repair.
The failed owned process was stopped after normal window close failed.

The successful baseline replay is Dev116-stationary-20260914-r2, using the
same executable/config/shader planned for the comparison. At the unchanged
Gunner position its 240 samples are median 16594.5 us, p95 17873 us, p99
29274 us, worst 33039 us. Render median 15654 us; update median 943.5 us.
Presentation is not separately instrumented. Native BMP capture is black and
cannot prove visual correctness. The original replay exits and tears down;
the Windows runner reports PROCESS_FAILED/null after the emulator window was
closed normally. Preserve that receipt without interpreting it as a crash.

Original Combat teardown cleared result.level_loaded, incorrectly destroying
historical load evidence and making final runtime status FAIL. Dev117 uses a
separate pending-unload flag, preserving original teardown ownership and the
observed load result. Original EVA entry/resume now records its observed flags.
These fixes join the same incremental package, with no full-build retry.

The initial fast batch passed 128 contracts, then exposed that the checkpoint
option was directory-wide and invalidated every engine object. Its Ninja was
interrupted before packaging. CMake now scopes that option to its sole consumer,
a31_vita_runtime.cpp. Generated Ninja commands confirm exactly one consumer;
receipt: build/dev117-checkpoint-build-scope.json. Removing the old global
definition changes compile keys once; future checkpoint toggles affect only
that translation unit. The existing fast tree/cache is reused, and the already
passing contract suite is not rerun by the resumed packaging invocation.

Fast artifact closure now PASS. The fast script's obsolete Decode_Wave symbol
gate was updated to the actual Decode_Wave_With_Info owner, matching canonical
validation. Closure retry compiled zero objects and only repeated six packaging
actions. Logs: build/dev117-fast-scoped-batch.log and dev117-fast-closure.log.
Artifacts and explicit source-hash/diagnostic bundle are under workspace dist/;
the managed Windows builder directory is unavailable in this session.
SELF 5d2ecfa964d72ab0a2902307dcb4c9c55f9158549af6e54a3c8b1c64eb45cd50;
VPK 3e7cdfc8d0a0df44622d89bcb8dda46b5ff25ce5f5c4b76b529a363ccaf5d9e5;
ELF 551bc1203b4cfa0e6e36b322a05cb9afc4debe9d6d8483d2455dcecd55535ebb.
Vita3K setup passed full retail hash coverage without modifying retail files.

Dev117-stationary-20260914-r1 returned matching player position/orientation,
health and grounded state. Its 240 samples: median 16.5605 ms, p95 17.638 ms,
p99 18.001 ms, worst 38.960 ms. Mean 59.999 FPS; 39.58% of samples still exceed
16.667 ms. One paired sample is insufficient to attribute a gain to the guard
change; worst frame regressed. Decision: retain the correctness-preserving
redundant-work fix, defer any sustained-60-FPS claim. Present timing is not
separate and zero emulator memory fields are unavailable, not memory proof.
Comparison: build/dev117-stationary-benchmark/comparison.json.
Original replay exit now retains level=1 and returns runtime teardown PASS,
with mission_complete/success/star=0/0/0. This is not mission completion.

Dev117-visual-20260914-r1 used the same package. Captures show rifle idle
(visible-20260914T180010885Z.png), EVA with black margins (180022254Z), original
rifle reload/left-hand motion (180051537Z), and returned idle with 100/98 ammo
(180105386Z). Original fire consumed two rounds; reload restored the magazine
from 98 to 100. Original RIFL fire/reload animation pointers are non-null with
no missing-animation fallback. EVA resumed gameplay. All six controller inputs
acknowledged release. The input enable flag and owned replay route were removed.
Normal emulator window close did not terminate this visual run within five
seconds; it subsequently exited. The runner records PROCESS_FAILED/null exit
code. Do not treat it as clean native teardown or an established native crash.

Next batch: bound the demonstrated every-reload-frame diagnostic in
combat-a35-weaponview-reload-latch.patch; profile a fixed moving/firing replay
with developer file input disabled; continue original M00 range/vehicle/final
tasks. Do not build again for the diagnostic alone. Retain the tested package.
Full M00, ending, sustained 60 FPS and physical PS Vita/PSTV acceptance remain
open; physical access remains held. Black margins preserve the original 4:3
EVA artwork; they are not widescreen artwork conversion.
