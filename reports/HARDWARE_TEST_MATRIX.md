# Hardware test matrix

| Gate | Required observation | Status |
|---|---|---|
| A3.1.4 | visible M00, original session/camera, 1,226 stable frames, START exit | passed; frozen |
| A3.2-dev1 | failed physical evidence: warped first-person textures, black muzzle rectangle, held fire/crouch, inverted axes, crash | frozen; do not retest as acceptance |
| A3.5-dev1 | M00: axes, granular look, held/release actions, near/far wall perspective, muzzle alpha, pause/resume, 120-frame checkpoint, START LiveArea exit, returned ZIP/log/dump | packaged; physical test pending |
| v3.6 candidate | tutorial, second campaign scene, multiplayer-map render smoke, cache/memory/reload evidence | M01 and City host smokes pass; physical promotion pending A3.5 |
| v3.8 candidate | original menu/HUD/audio path, campaign launch, pause/resume/exit | pending v3.5–v3.7 |
| v3.9/v4.0 | representative campaign progression, repeat sessions, soak, balanced pacing, diagnostics | pending |

Each returned dump must be symbolicated only with the matching candidate ELF,
map, symbols, source revision, and patch identity.
