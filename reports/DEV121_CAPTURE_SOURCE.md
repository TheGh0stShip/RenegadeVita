# Dev121 presented-frame capture

## Runtime return and Dev122 follow-up

Dev121 Vulkan Gunner capture at frame 526 still yields an all-black game-owned
BMP; emulator F12 at 19:57:17 UTC is nonblack and visibly matches the scene.
Retained `build/dev121-capture-return/receipt.json`. Front-buffer selection is
necessary for post-present semantics but does not resolve emulator readback.
Native Select acknowledged release and opt-in marker removed. Run r1 remains
bounded to 19:59:23 UTC; check receipt/process for actual termination.

Pinned vitaGL RGBA8888 glReadPixels uses direct CPU memcpy from the display
surface; that bypasses the emulator's GPU surface transfer. Dev122 uses
vglAlloc(size, VGL_MEM_RAM), glFinish, vglReadPixels, CPU copy and vglFree.
The mapped RAM allocation is temporary and bounded to 960*544*4 bytes per
explicit capture, with no gameplay-frame allocation. vglMalloc is unsuitable
because it tries external/newlib memory first. The pinned vglReadPixels waits
for sceGxmTransferFinish before returning. No upstream library changes.
Focused test now covers mapped storage, finish-before-read, failure/free paths
and allocation failure. Pass: build/dev122-frame-capture-focused.log.
Dev122 initial 134 checks/package closure pass, build/dev122-fast-console.log.
Final pre-runtime hardening clears the mapped temporary buffer before the
transfer, preventing an unreported transfer failure from serializing old pool
contents. Pre-hardening artifacts retained in build/dev122-pre-runtime-package/;
final incremental package runner 36985, build/dev122-fast-final.log. Dev121
r1 ended at its watchdog at 19:59:25 UTC. No Dev122 runtime evidence yet;
all rendering defects remain open.

Dev120 r5 finally uses Vulkan, confirmed by `renderer::vulkan::VKState::create`
and its window title. The pinned emulator configuration merge skips an override
equal to its default `Vulkan`, leaving the global OpenGL setting. Uppercase
`VULKAN` survives that merge and is normalized by the backend selector. Only
the run-owned YAML changes; the user's global configuration is unchanged.
Reference: https://github.com/Vita3K/Vita3K/blob/84184a36/vita3k/config/src/config.cpp

Matching emulator F12 framebuffers are nonblack and visually inspected. Nearby
barracks walls and elevator appear intact from these angles; the original user
wall camera is not matched, so the rendering defect is not cleared. Input was
shared with the user, as shown by live analog movement and a pistol shot; this
is not a deterministic replay or performance benchmark. All five native input
commands were acknowledged released, and the opt-in input marker was removed.
The owned run was stopped after capture; CloseMainWindow did not finish within
the helper's deadline, so termination was forced. No clean-exit claim.

Evidence and hashes: `build/dev120-vulkan-return/receipt.json`. Original wall
return remains unchanged at `build/dev120-wall-return/`. The native Select
channel successfully produced a state/CSV/BMP bundle, but its BMP is black.

Production readback always used vitaGL's default GL_BACK. A31 loading/gameplay
captures occur after presentation; vitaGL rotates its back index on swap. Add
an explicit presented-frame parameter and select GL_FRONT for these callers,
then restore GL_BACK. The older A30 pre-presentation capture retains its back
buffer semantics. This corrects buffer selection; emulator CPU readback may
have an additional synchronization limitation. Runtime proof is required.

The focused host test exercises production readback against different front
and back buffer contents, failed readback, buffer restoration and invalid
storage. Pass: `build/dev121-frame-capture-focused.log`. First package attempt
stopped at the old loading-capture call assertion; updated it to require the
presented-frame argument. Retry passes 134 checks and ARM/ELF/SELF/VPK closure:
`build/dev121-fast-retry.log`. Matching ELF/map/SELF/VPK, source hashes and a
telemetry-only diagnostics ZIP are retained in dist/. Dev121 installed with
Dev120 backup, retail coverage checked without modification. Runtime r1 is a
180-second Gunner replay with Vulkan and native Select enabled; revalidate its
live receipt before acting. Capture acceptance remains pending.

Latest user Logan return: r5 frame 4784 starts MTU_LOGAN_PREPARE_INFANTRY,
remark 5404 plays, and conversation ends at frame 4811. Original script then
moves Logan to (-18.648,42.75,1), his barracks staging point. Objective states
remain 1/1/3/3/3/3: WF is hidden, and Gunner's ending callback has not occurred
in this run. That callback activates WF and tells Logan to prepare weapons.
This does not prove a new conversation hang; the older Gunner checkpoint is
not the later Hotwire/WF state. Do not force mission flags to skip the sequence.

Next: finish Dev121 artifact closure, validate presented-frame capture, use
matching scene/camera evidence for remaining wall/sky/elevator and credits
issues, then repeat lifecycle. Final user playthrough and physical tests remain
held; no demo release acceptance gate is complete.
