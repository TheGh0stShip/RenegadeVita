# Historical Evidence Inventory

This inventory records where previous Renegade Vita screenshots and logs were found for the GitHub historical gallery. It intentionally excludes retail data, saves, credentials, raw dumps, and VPK payloads.

- Bash workspace scanned: `/home/steve/projects/RenegadeVitaBuilder/workspace/active`
- GitHub gallery PNGs: 176
- VitaShell FTP was checked read-only at `10.0.0.202:1337` for `ux0:/data/renegade/user/logs/`, `captures/`, and `screenshots/`; the latest audit found 24 runtime logs, 89 capture directories, and no files in the top-level screenshots folder.
- All 89 live Vita capture directories are now represented locally between `build/device-evidence/vitashell-gallery-pull-20260828/`, `build/device-evidence/vitashell-gallery-pull-secondpass-*`, and `build/device-evidence/vitashell-gallery-pull-listingpass-*`.
- `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder` was not present; targeted AppData evidence came from the Vita3K user data root instead.
- `/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs/` supplied the older A3.1 captures and logs.

## Gallery By Build

| Build | PNGs in GitHub gallery |
| --- | ---: |
| A3.1 | 4 |
| A3.5-dev12 | 4 |
| A3.5-dev13 | 7 |
| A3.5-dev16 | 10 |
| A3.5-dev17 | 10 |
| A3.5-dev18 | 14 |
| A3.5-dev19 | 7 |
| A3.5-dev20 | 2 |
| A3.5-dev21 | 2 |
| A3.5-dev24 | 2 |
| A3.5-dev42 | 8 |
| A3.5-dev43 | 15 |
| A3.5-dev44 | 4 |
| A3.5-dev45 | 10 |
| A3.5-dev46 | 10 |
| A3.5-dev47 | 4 |
| A3.5-dev5 | 21 |
| A3.5-dev6 | 2 |
| A3.5-dev7 | 23 |
| A3.5-dev78 | 8 |
| A3.5-dev79 | 4 |
| A3.5-dev82 | 4 |
| A3.5-dev86 | 1 |

## Scanned Roots

| Label | Exists | Files | Type counts | Root |
| --- | --- | ---: | --- | --- |
| github_gallery | True | 176 | png:176 | `/home/steve/projects/RenegadeVitaBuilder/workspace/active/docs/history/screenshots` |
| active_device_evidence | True | 4239 | bmp:161, csv:51, json:2821, log:994, png:21, txt:191 | `/home/steve/projects/RenegadeVitaBuilder/workspace/active/build/device-evidence` |
| active_logs | True | 277 | log:277 | `/home/steve/projects/RenegadeVitaBuilder/workspace/active/logs` |
| active_dist | True | 680 | json:116, log:39, txt:525 | `/home/steve/projects/RenegadeVitaBuilder/workspace/active/dist` |
| vita3k_user_appdata | True | 7 | log:6, txt:1 | `/mnt/c/Users/steve/AppData/Roaming/Vita3K/Vita3K/ux0/data/renegade/user` |
| missing_c_local_builder_root | False | 0 | - | `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder` |
| e_vita_logs | True | 39 | bmp:4, csv:9, json:9, log:9, txt:8 | `/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs` |
| e_project_logs | False | 0 | - | `/mnt/e/Projects/RenegadeVitaBuilder/workspace/active/logs` |
| e_project_dist | True | 734 | csv:5, json:102, log:41, txt:586 | `/mnt/e/Projects/RenegadeVitaBuilder/dist` |

## Diagnostic-Only Or Loading-Only Screenshot Groups

These builds have screenshot files but no useful gameplay screenshot in the current local/Vita/AppData/E: evidence set:

`A3.5-dev6`, `A3.5-dev12`, `A3.5-dev20`, `A3.5-dev21`, `A3.5-dev24`, `A3.5-dev42`, `A3.5-dev43`, `A3.5-dev44`, `A3.5-dev45`, `A3.5-dev46`, `A3.5-dev47`, `A3.5-dev78`, `A3.5-dev79`, `A3.5-dev82`, `A3.5-dev86`.

## Builds With Logs But No Screenshot File

`A3.5-dev1`, `A3.5-dev14`, `A3.5-dev22`, `A3.5-dev23`, `A3.5-dev34`, `A3.5-dev36`, `A3.5-dev37`, `A3.5-dev38`, `A3.5-dev40`, `A3.5-dev41`.

The full machine-readable inventory is `reports/generated/historical_evidence_inventory.json`.
