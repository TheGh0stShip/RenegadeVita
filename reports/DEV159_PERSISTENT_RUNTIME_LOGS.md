# Dev159 persistent runtime log handles

Dev159 makes both runtime-log writers retain their file handles after first
open while still syncing each completed record.  The change applies to
`A30_Vita_Log` and the older `Vita_Append_A22_Runtime_Breadcrumb`
renderer/input breadcrumb path.

This is a diagnostic-overhead reduction, not campaign or 60 FPS acceptance.
It does not change original gameplay ownership, M13 scripts, assets, or
mission progression.

## Build

- Candidate: `A3.5-dev159`
- Profile: full-port campaign, `RENEGADE_VITA_M00_DEMO=OFF`
- Title built: `RNEGC3101`
- SELF SHA-256:
  `b55dfad403dc05dfbdf830268355f6cc087a130981cdb623a5374328e5e01136`
- VPK SHA-256:
  `39e1ab980f36b41e72473346a4e8430b734f490eef8ff336034a7555e4c60ff9`
- Focused tests: `python3 -m tools.test_development_checkpoint` PASS
- Whitespace: `git diff --check` PASS

## Runtime Evidence

The earlier Dev158 custom-VFS package/autoboot run was invalid: Vita3K
installed the package but did not start the title.  A valid route was obtained
by placing the candidate eboot into the emulator's existing registered
`RNEGA3101` installed-title slot, setting the M13 direct-entry marker,
launching with `--installed-path RNEGA3101`, and restoring the prior Dev134
eboot afterward.  This was emulator-only evidence; no physical acceptance is
claimed.

Evidence directory:

- Managed AppData:
  `campaign-dev159-persistent-all-logs-m13-installedtitle-1/`

Temporary default-VFS mutation was restored:

- Restored `ux0/app/RNEGA3101/eboot.bin` SHA-256:
  `55ec5e560eed2ca94a4ab06d8b10e6f7039c19b8d6c79353f5a63f3ea1e7e385`

## Measured Results

Compared with the valid Dev158 installed-title run:

| Metric | Dev158 | Dev159 |
| --- | ---: | ---: |
| Vita3K stdout bytes | 117383 | 101520 |
| `export_sceIoOpen` console records | 1061 | 888 |
| Runtime-log open records | 52 | 2 |
| `always.dat` open records | 240 | 208 |
| `Always2.dat` open records | 15 | 15 |
| `M13.mix` open records | 25 | 21 |
| Shader-cache open records | 8 | 8 |

M13 frame checkpoints in Dev159:

| Frame | Avg FPS | p50 / p95 / p99 / max frame us | Avg sim / render us |
| ---: | ---: | --- | --- |
| 120 | 15.488 | 20717 / 183179 / 472759 / 2028056 | 30563 / 33997 |
| 240 | 17.282 | 44128 / 73743 / 112818 / 2028056 | 22006 / 35852 |
| 360 | 18.315 | 42596 / 73526 / 100651 / 2028056 | 17861 / 36735 |
| 480 | 17.380 | 53818 / 101965 / 254968 / 2028056 | 15687 / 41846 |
| 600 | 16.709 | 61752 / 130004 / 137739 / 2028056 | 15776 / 44066 |
| 720 | 15.266 | 68666 / 178292 / 397428 / 2028056 | 21950 / 43551 |

Event-local M13 retained-template behavior is preserved:

- `X00_AG_Explode` loading preparation: 6122005 us.
- Slot 19 live model setup: object 585 us, template clone 4600 us,
  `Set_Model` 5091 us.
- `ag_RocketL` live clones: 63-65 us.

## Remaining Problem

Dev159 removes most runtime-log open spam and improves the early M13 emulator
measurements, but the route is still nowhere near the 60 FPS goal and remains
unaccepted.  Frame 703 still spikes to 564717 us
(`simulation_us=410882`, `render_us=153833`), and frame 720 still has p95
178292 us.  Audio remains real-time while simulation/render fall behind, so
cinematic A/V sync remains unresolved.

Next highest-value work is the measured render/scene path: visibility/object
submission/material-state cost around the M13 intro and post-rocket sequence,
plus the remaining large simulation spike at frame 703.
