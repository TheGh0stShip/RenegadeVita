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

Vita3K trial `campaign-dev141-m13-trial-1/` in managed AppData used the matching
SELF SHA-256 `6610192696cffad86adb02255671ced9b2cba40775e9bd2241df0d464a265d34`.
The original campaign menu selected `M13.mix`; the retained Movie mode breadcrumb
appeared. M13 loaded, registered the original MX0 scripts, and rendered a first
gameplay frame with 108 meshes, 10,560 vertices, and 7,116 triangles. A bounded
W press was released and player position changed in the runtime log. The
240-second watchdog ended the trial and terminated its owned emulator process.
No M13 objectives, completion, transition, or physical Vita result is claimed.
