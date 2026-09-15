# Dev111 retained runtime return

Vita3K evidence, 2026-09-09 03:39 UTC. Supersedes running-state wording in
earlier Dev111 entries. The M00-only community demo is not release-ready.

## Run termination

Owned runner session 76938 exited 124 at its configured 1800-second limit.
The final receipt records `owned_process_terminated=true`, synthetic inputs
released, and finish time `2026-09-09T03:39:06.1271929Z`.
This is a runner timeout/termination, not evidence of a guest crash or clean
original-game teardown. No replacement run has been started.
Final runtime SHA-256 recorded by the runner:
`2834c7de44c2cf1f5ec5fb5f05a0bb60db5cf34e79fbe2698a1e05751bb8f35e`.
Retained copies:
`build/dev111-host-evidence/dev111-runtime-final.log` and
`build/dev111-host-evidence/dev111-runtime-final-receipt.json`.

## Further original progression

- Original keycard briefing ran; capture `step-20260909T033406666Z.png`
  shows the security-card pickup icon/text. The door opened and the original
  elevator carried the player into Sydney's lower room.
- Sydney's health, armor and radar conversations progressed. Objective 1 was
  completed and objective 2 became pending. Captures show pickup prompts and
  Sydney; bitmap HUD digits remain incorrect.
- The requested turn/board/turn/exit sequence was attempted through ordinary
  input, but its final capture still showed Sydney's room. Do not count that
  sequence as a verified elevator return.
- Later runtime state reached `MTU_PETROVA_POWER`; the final viewed capture
  `step-20260909T033854821Z.png` shows Petrova. Sampled objective states were
  `1/0/3/3/1/3`. This does not establish ordered completion of every intervening
  tutorial segment or attribute every movement to automation.

## Four local original checkpoints

All are under `build/tutorial-checkpoints/`, excluded from distribution.
Original quicksave alternation overwrote active slots only after earlier
versions had been archived. Archive receipts preserve unchanged save bytes.

| Checkpoint | Bytes | Save SHA-256 |
| --- | ---: | --- |
| m00-initial-spawn-dev111 | 95326 | c32b434a7da20a0f4d6eac1145589ac7d6efb67cd0704275a5326f5fb3ff2eee |
| m00-post-obstacle-dev111 | 94807 | 8774dbe47c9ae17a244d4e73ff0426e2064b48d9e7aef314a46fdec4760a0696 |
| m00-post-sydney-dev111 | 96458 | f651d389877c6df19dc2fa95b1c636627a331e2f451d46f286599c56f8981ec7 |
| m00-petrova-dev111 | 96491 | 0c59ef8fb2336db81ce7efe3b6c67fcbe01bbe68e11b59a13033342bb73f1d6d |

Creation and archival are proven, successful original reload is not. Checkpoint
names describe the observed phase, not exhaustive prior-segment acceptance.

## Bitmap-font lead

Both installed font entries decode under host Pillow. `FONT12x16.TGA` is
192x256; `FONT6x8.TGA` is 96x128. Direct host inspection of ASCII cells
0, 1, 2 and 5 in the large font shows recognizable original digits. The TGA
descriptor is 0x08. Neither a missing retail file nor malformed original digit
artwork explains the visible counter defect. Native decoding, atlas packing,
UVs and draw state remain to be isolated; no speculative flip was applied.

## Next source/runtime batch

Close the original checkpoint-launch/reload route, bitmap HUD counters and
original pause ownership before another integrated candidate. Preserve the
current saves so the next run can prove reload and continue from retained
progress rather than starting over. Full M00, safe ending/credits, original
pause, smooth hidden loading and 60 FPS remain unproven.
