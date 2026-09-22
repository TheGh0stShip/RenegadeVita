# Dev141 campaign Movie mode lifetime

The full-port frontend now retains the original `MovieGameModeClass` after a
single-player mission is selected. `CampaignManager::Continue` looks up that
mode for Score and Movie states, but the frontend previously removed it before
gameplay. The selected session removes it during owned teardown. The M00 demo
profile retains its previous remove-after-menu behavior.

Verification: 18 focused host contract/parser tests passed. The full-port ARM
ELF, SELF, and VPK built with development checkpoint disabled. Package
inventory contains only `eboot.bin` and `sce_sys/param.sfo`. VPK SHA-256:
`a59090105b74fb7c1d4c7e5bf16f2af558dcbbd547144f5e25c0b9565bb9bb8f`.

This fixes one necessary registration dependency only. It does not yet route
the observed Combat mission-complete event through original Score/Movie/M01
session ownership. No Dev141 runtime or physical-Vita result is claimed.
Next: retest M13 startup in Vita3K, then connect the original pending
continuation without double teardown and test normal transition.
