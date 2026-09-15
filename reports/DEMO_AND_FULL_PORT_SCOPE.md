# Full port destination, interim demo delivery

User clarification: 2026-09-08.

The durable objective is a complete native Renegade port for PlayStation Vita.
M00-only development gates, the public tutorial demo, and the roadmap's first
representative campaign release are intermediate deliveries. None is the
full-port completion criterion.

## Shared work

Original engine, campaign, WW3D, Combat, WWAudio, WWUI, filesystem, resource,
and WWNet ownership remain shared. Movie scheduling, glyph rendering, target
projection, loading presentation, memory correctness, caching and measured
performance fixes must benefit the full port rather than a replacement demo.
The 60 FPS+ target remains active; source and synthetic tests do not prove it.

## Demo-specific policy

The public demo permits the entire original M00 tutorial, not a shortened or
fabricated route. Original success triggers a slow fade, the user's exact
thank-you text, project and dependency credits, then safe teardown. Later-map
launches are blocked only for the demo profile. The VitaGL spinning splash is
unnecessary; project/dependency acknowledgement remains in text credits.

The showcase must identify the native port as work of the Renegade Vita
project while clearly distinguishing EA/Westwood's original game and credited
third-party components. No assistant credit is requested. Do not imply EA
endorsement or permission to redistribute retail data.

## Full-port progression

Retain the current correctness, resource/multi-scene, measured renderer,
original frontend/audio, representative campaign, and controlled networking
milestones. Expand from them to all campaign missions and original systems.
Later-map infrastructure must not be removed merely because the demo stops at
M00. Removing an unused hardcoded M01 startup pre-cache does not constitute
removing later-map support, nor does a profile switch create support that has
not yet been implemented.

A selectable demo profile is implemented in Dev101 source after Dev100
canonical closure. `RENEGADE_M00_DEMO=1` selects the showcase; `0` selects
full-port development through either build script. CMake exposes the matching
`RENEGADE_VITA_M00_DEMO` option. The non-demo configuration retains current
full-port development behavior and explicitly reports its profile; it must not
claim that all campaign missions already work. Preserve distinct candidate
artifacts and hashes across source/profile changes.

## Evidence boundary

Host, Vita3K, PS Vita, and PSTV results remain separate. Both physical devices
are required for final acceptance, and the user's current physical-test hold
remains in force. The demo must not be called flawless or released as complete
without an authentic end-to-end M00 run and visual/lifecycle evidence. The full
port has a broader completion obligation beyond that demo gate.
