# Dev113 build and bounded Vita3K return

Stopped at the user's request after finishing this build and testing it.
Both owned Vita3K processes were closed; a final Windows process query returned
an empty list. All build/debug/runtime sessions from this work are terminal.
No further build, source fix or test is scheduled for this session.

## Build: PASS

Canonical retry session 5497 completed successfully. Fresh host gates, sanitizer
cycles, 157 contracts, ARM build, ELF/SELF/VPK checks and identity verification
passed. Original failed dev113 host evidence remains retained separately.

- VPK: `dist/RenegadeVita-A3.5-dev113.vpk`.
- VPK SHA-256: `7a8c31956b78ceb87d66ba973846954c20242349a711728f65e3e16cb93a94e4`.
- ELF SHA-256: `c32bc9e3b49261bb3434b58543f09e4e08fd9384c4333f70b802c53dd10f7a92`.
- SELF SHA-256: `494c6e30453a110a2b4f002f34c4ada7c479bee53c017cc0231829d7fb385949`.
- VPK members: only eboot.bin and sce_sys/param.sfo; development checkpoint on.
- Retail Data verification: all 51 source files matched; 2 extras preserved.
- Retail files and archived checkpoint saves were not modified.

## Checkpoint run: controlled failure, not successful restoration

Evidence: `D:/Vita3K/RenegadeEvidence/Dev113-20260909T051945Z/`.
Original save `save/dev112-post-sydney.sav` passed the previous conversation
access-violation location, returned from original Load_Game, and reached level
finalization. It then logged:

`A3.5 checkpoint: FAIL restored local player/star identity; no respawn or rejoin attempted`

The application completed controlled-failure teardown with zero gameplay frames.
The request was consumed; the save remains unchanged. Do not claim reload works
or bypass this guard by spawning a replacement player. Runtime evidence:
`build/dev113-host-evidence/checkpoint-runtime.log`.

## Fresh M00 run: startup and pause/resume observed

Evidence: `D:/Vita3K/RenegadeEvidence/Dev113-Fresh-20260909T052123Z/`.

- Viewed EA intro frame (window-010.png) and orange second intro (window-031.png).
- Main and Single Player menu labels are visible in step captures 052247057 and
  052303417. Disabled-option behavior was not exhaustively exercised.
- Selected original Tutorial through native input. Loading capture 052346107
  shows readable Preparing M00 textures 91% over the loading backdrop. Smooth
  progress-bar animation and the complete warmup transition are not proven.
- Fresh original Commando/Logan scene is visible in capture 052419002.
- Start suspended Combat without an observed access violation. However capture
  052431977 shows only the menu backdrop with gray side margins: EVA controls,
  tabs and text are missing. This is not a functional pause-menu acceptance.
- Circle resumed the same gameplay scene. Runtime reports resumed=1 exit=0;
  capture 052458684 confirms the restored scene. Thus pause/resume control works
  in this bounded test, but pause presentation remains broken.
- HUD digits, sky and stippled NPC rendering remain visibly defective. Sampled
  starting-scene captures show approximately 13-14 FPS; this is not a fixed
  benchmark, a hardware result, or a 60 FPS acceptance.

Native commands were accepted and released without OS keyboard injection.
The final neutral release receipt is
`build/dev113-host-evidence/final-input-release.json`. The Windows runner does
not count this separate native-input channel in its synthetic_input_steps field;
the native receipts and matching runtime acknowledgments are the evidence.

## Shutdown and next-session blockers

The checkpoint application closed itself after controlled failure. Its emulator
was then closed explicitly. After fresh-start testing, inputs were released and
that owned emulator was also closed explicitly. Runner PROCESS_FAILED statuses
reflect operator process termination and are not evidence of guest crashes or
successful original mission teardown. Final runtime and hashes are retained in
`build/dev113-host-evidence/final-runtime.log` and `runtime.sha256`.

Next work, only when resumed: original saved-player identity restoration and
missing EVA presentation, then HUD/render correctness and full original M00
completion/ending evidence. The complete port and demo goals remain unfinished.
