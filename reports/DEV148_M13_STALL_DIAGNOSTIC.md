# Dev148 M13 stall diagnostic

Status: ARM build and asset-free package pass; M13 direct-entry Vita3K/OpenGL
diagnostic runs return `TIMEOUT_UNASSESSED`. This is not a performance or
campaign-completion acceptance build. Physical Vita was not tested.

The full-port boundary routes failed mission completion to the original
`cGod::Mission_Failed()` dialog, and the Vita loop observes restart without
reusing a stale completion latch. Five source-contract tests pass; ordinary
death/restart gameplay remains unverified. The demo profile is unchanged.

Bounded, full-port-only mesh timing shows that indexed draw completion is not
the dominant measured cost. A rejected M13 texture prewarm moved 183 textures
to loading but did not remove the multi-second stall. A rejected repeated-color
submission candidate also retained a 6.91-second worst frame. Both changes
were reverted; the original cinematic/game clock remains intact. Measurements
and exact diagnostic receipts are in `PERFORMANCE_HYPOTHESIS_LEDGER.md`.

Restored diagnostic artifact: `build/vita-dev140-diagnostic/`.
SELF SHA-256: `4d55f724ae94e1eb9eb7d8281945b29d05c3bce1e140bf94a3d6907497ede4eb`.
VPK SHA-256: `4ed26752f168035d192f80758acc04e41c32a96433bc0d966f01f31566675261`.
The VPK contains only `eboot.bin` and `sce_sys/param.sfo`; it contains no game
data. It requires the user's unchanged supported retail files under
`ux0:data/renegade/retail/Data/` and writes state under
`ux0:data/renegade/user/`.

Next: time the remaining scene traversal/material-state/backend boundary in
the same long frame; fix the responsible operation and verify M13 intro actor
sequencing, ambush timing/audio, death/restart, and normal campaign flow.
