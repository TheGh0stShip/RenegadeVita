# Vita3K evidence loop

Checked read-only on 2026-08-16. The configured data root is
the local Vita3K application-data directory and contains installed title
`ux0/app/RNEGA3101/`:

| Item | Observed value |
| --- | --- |
| Installed title | `RNEGA3101` |
| `param.sfo` title | `Renegade Vita A3.1` |
| App version | `03.10` |
| Installed `eboot.bin` SHA-256 | `2d03d5f501f8772863ac58180f4896d70ff2ea2460ba248e0f068a474889d9e4` |
| A3.5 app installed | no |
| Configured Vita3K executable | not found under the configured Roaming tree or the available user-file search |
| Emulator logs/session markers | not found in the configured tree |

No Vita3K files were installed, replaced, deleted, or launched. The existing
app is not evidence for A3.5 or later.

## Controlled future loop

When a user supplies the Vita3K executable location, retain this sequence:

1. Record emulator version and existing `RNEGA3101` EBOOT/SFO hashes.
2. Manually install or replace the candidate VPK through the user-controlled
   Vita3K workflow; record the resulting EBOOT/SFO hashes and title path.
3. Launch only the title ID `RNEGA3101` with a fixed configuration and the
   user-owned retail tree beneath `ux0:data/renegade/retail/Data/`.
4. Collect the emulator log, a session-completion marker, screenshots, and any
   crash evidence into a candidate-specific directory.
5. Compare capture bundles only with matching candidate artifacts, using
   `tools/compare_capture_bundles.py`.

Vita3K remains a rapid regression aid only. It cannot accept controls,
perspective, VitaGL/GXM behavior, memory, storage, suspend/resume, LiveArea
exit, or soak milestones that require physical Vita evidence.
