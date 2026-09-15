# Dev111 M00 obstacle-course return

Evidence class: Vita3K only. Recorded 2026-09-09 approximately 03:31 UTC.
Candidate identity remains the closed Dev111 r7 package. Run:
`D:/Vita3K/RenegadeEvidence/Dev111-20260909T030903Z/`.

## Original progression

- Native input sequences 13-41 used bounded normal controller input and
  acknowledged release. No objective, script event or position was injected.
- Initial failed movement pressed against the wall. A corrected approach
  reached `MTU_LOGAN_JUMP_TEST`; this conversation temporarily disabled control.
- Use followed by forward movement climbed the original ladder. The gap-jump
  attempt landed below box-top height; that isolated jump is not accepted as
  visually successful. Subsequent normal movement reached `MTU_LOGAN_EVA`.
- EVA completion changed objective 1 from hidden (3) to pending (0), followed
  by `MTU_LOGAN_POKE`. Original script selected `Weapon_Pistol_Player`.
- Close-range Use on the GDI soldier triggered `MTU_GDI_POKE` at frame 42723.
  Capture `step-20260909T033043575Z.png` shows the opened gate. Earlier presses
  from farther away had no confirmed effect and are not counted as successes.
- Crossing the gate reached Logan outside with "Follow Me" visible in
  `step-20260909T033103584Z.png`. Full M00 completion is still unproven.

## Original checkpoint retained locally

`build/dev111-host-evidence/quicksave-post-obstacle/quicksave-result.json`
records a stable new `quicksaveB.sav`, 94807 bytes, SHA-256
`8774dbe47c9ae17a244d4e73ff0426e2064b48d9e7aef314a46fdec4760a0696`.
The initial quicksaveA remained unchanged. The new save is archived at
`build/tutorial-checkpoints/m00-post-obstacle-dev111/`, with the unchanged
retail-content identity and original EVA-phase capture as provenance.
This save precedes the later GDI interaction and course-exit trigger.
Creation/archive are proven; successful original reload is not.

## Presentation findings

- `step-20260909T032835934Z.png` shows the objective image, pistol, hand,
  weapon name and readable Logan label. It also shows malformed bitmap HUD
  counters and polygonal sky shading. It is not full visual acceptance.
- The counter path uses original `Font3DInstanceClass` with `FONT12x16.TGA`
  and `FONT6x8.TGA`; menu/sentence font rendering is a different path.
- Host inspection of installed `always.dat` found `FONT12x16.TGA` intact:
  192x256, 32-bit RGBA, 196652 bytes, payload SHA-256
  `2616bd665c044539cb8951e9f1c03dad149238fee9a62b8ed2149df029f5da59`.
  Metadata receipt: `build/dev111-host-evidence/font12x16-retail-metadata.json`.
  Pillow decoded it with 5000 opaque and 44152 transparent pixels; no retail
  payload was written. This does not validate native atlas construction/upload.
- Both the native surface loader and original TextureLoader toggle TGA Y origin
  before loading. Original Targa::Open retains the header when already open.
  No speculative texture flip has been applied.

## Next

Follow original Logan/guard-tower training; preserve further checkpoints.
Resolve native bitmap counters, original pause ownership and checkpoint reload
as a coherent source batch. The successful gate interaction is not a save-load,
full tutorial, ending/credits, performance-target or release-acceptance claim.
