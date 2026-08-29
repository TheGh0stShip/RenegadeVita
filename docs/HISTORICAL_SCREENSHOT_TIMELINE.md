# Historical Screenshot Timeline

This page collects web-viewable local diagnostic screenshots from the Renegade
Vita evidence tree. It is meant to show visual progression on GitHub without
publishing retail data, raw dumps, saves, credentials, or a new runtime
artifact.

Evidence policy:

- Source evidence came from `build/device-evidence/` in the bash workspace.
- The gallery stores PNG copies under `docs/history/screenshots/`.
- Each build section may include up to 15 representative screenshots. Gameplay
  captures are preferred; when fewer than 15 local screenshots exist, every
  useful local sample is included. When only loading or diagnostic frames are
  available, that limitation is stated.
- These images are historical evidence. They do not make dev82 physically
  accepted; dev82 still requires a returned Vita test with matching logs,
  screenshots/captures, and any crash dumps.

## Five Gameplay-First Samples

These five samples are listed before the loading-screen history so the first
GitHub view shows actual in-game progression where local evidence exists.

<table>
<tr>
<td width="20%"><img src="history/screenshots/a35-dev5-spawn-control.png" width="220" alt="A3.5-dev5 spawn/control gameplay capture"><br><strong>A3.5-dev5</strong><br>Visible M00 world, weapon view, and movement/control evidence.</td>
<td width="20%"><img src="history/screenshots/a35-dev7-effects-131326.png" width="220" alt="A3.5-dev7 effects diagnostic gameplay capture"><br><strong>A3.5-dev7</strong><br>In-game effects/input diagnostic capture from a physical observation run.</td>
<td width="20%"><img src="history/screenshots/a35-dev13-selected-frame.png" width="220" alt="A3.5-dev13 selected gameplay frame"><br><strong>A3.5-dev13</strong><br>Route-record frame with NPC visibility, black sky, and material defects still present.</td>
<td width="20%"><img src="history/screenshots/a35-dev16-selected-frame.png" width="220" alt="A3.5-dev16 selected gameplay frame"><br><strong>A3.5-dev16</strong><br>Later route frame after audio/runtime lifecycle work.</td>
<td width="20%"><img src="history/screenshots/a35-dev17-selected-frame.png" width="220" alt="A3.5-dev17 selected gameplay frame"><br><strong>A3.5-dev17</strong><br>Replay evidence frame from the retained tutorial route path.</td>
</tr>
</table>

## Timeline

### A3.5-dev5 - Visible M00 and Movement Evidence

Local evidence includes three gameplay or near-gameplay samples. These show the
move from mostly dark early display evidence to a visible textured M00 subset
with first-person weapon and control progression.

<table>
<tr>
<td width="33%"><img src="history/screenshots/a35-dev5-first-interactive.png" width="260" alt="A3.5-dev5 first interactive capture"><br>First interactive capture</td>
<td width="33%"><img src="history/screenshots/a35-dev5-walk-manual.png" width="260" alt="A3.5-dev5 manual walk capture"><br>Manual walk capture</td>
<td width="33%"><img src="history/screenshots/a35-dev5-spawn-control.png" width="260" alt="A3.5-dev5 spawn control capture"><br>Spawn/control capture</td>
</tr>
</table>

Source paths:

- `build/device-evidence/a35-dev5-recursive-create-20260824/capture-first-interactive/frame.png`
- `build/device-evidence/a35-dev5-recursive-create-20260824/interactive-walk-run/manual-capture/frame.png`
- `build/device-evidence/a35-dev5-recursive-create-20260824/spawn-control-run/manual-capture/frame.png`

### A3.5-dev7 - Input, Effects, and Skinned-Body Defect Evidence

Local evidence includes four gameplay diagnostic samples from separate
physical observation runs. They are not polished gameplay screenshots, but they
are useful because they show real in-game rendering while the input/effects
path was being isolated.

<table>
<tr>
<td width="25%"><img src="history/screenshots/a35-dev7-effects-130626.png" width="220" alt="A3.5-dev7 effects capture 130626"><br>Effects capture 130626</td>
<td width="25%"><img src="history/screenshots/a35-dev7-effects-131326.png" width="220" alt="A3.5-dev7 effects capture 131326"><br>Effects capture 131326</td>
<td width="25%"><img src="history/screenshots/a35-dev7-effects-131654.png" width="220" alt="A3.5-dev7 effects capture 131654"><br>Effects capture 131654</td>
<td width="25%"><img src="history/screenshots/a35-dev7-effects-132016.png" width="220" alt="A3.5-dev7 effects capture 132016"><br>Effects capture 132016</td>
</tr>
</table>

Source paths:

- `build/device-evidence/a3.5-dev7-effects-20260824-130626/selected-capture-frame.bmp`
- `build/device-evidence/a3.5-dev7-effects-20260824-131326/selected-capture-frame.bmp`
- `build/device-evidence/a3.5-dev7-effects-20260824-131654/selected-capture-frame.bmp`
- `build/device-evidence/a3.5-dev7-effects-20260824-132016/selected-capture-frame.bmp`

### A3.5-dev12 - Deformed Skin Geometry Pass, Sky Failure

Local evidence includes one available first-frame gameplay capture from the
route-record attempt. It is kept because dev12 physically proved ordinary NPC
body skin geometry while the sky/material path remained wrong.

<table>
<tr>
<td width="33%"><img src="history/screenshots/a35-dev12-first-frame.png" width="260" alt="A3.5-dev12 failed safe first frame"><br>Failed-safe first frame</td>
</tr>
</table>

Source path:

- `build/device-evidence/a3.5-dev12-route-record-20260824-135219/failed-safe-first-frame.png`

### A3.5-dev13 - Route Record With NPC/Material Defects

Local evidence includes two gameplay samples: the full selected frame and a
crop centered on the NPC/material defect. This is useful for before/after
comparison with later dev82 texture/material work.

<table>
<tr>
<td width="50%"><img src="history/screenshots/a35-dev13-selected-frame.png" width="320" alt="A3.5-dev13 selected gameplay frame"><br>Selected gameplay frame</td>
<td width="50%"><img src="history/screenshots/a35-dev13-npc-crop.png" width="220" alt="A3.5-dev13 NPC material crop"><br>NPC material crop</td>
</tr>
</table>

Source paths:

- `build/device-evidence/a3.5-dev13-route-record-20260824-144843/selected-frame.png`
- `build/device-evidence/a3.5-dev13-route-record-20260824-144843/selected-frame-npc-crop.png`

### A3.5-dev16 - Audio Lifecycle Route Evidence

Local evidence includes one selected gameplay frame from the route-record run.
It belongs in the timeline because dev16 changed the original WWAudio lifecycle
under the same M00 progression path.

<table>
<tr>
<td width="33%"><img src="history/screenshots/a35-dev16-selected-frame.png" width="260" alt="A3.5-dev16 selected gameplay frame"><br>Selected route frame</td>
</tr>
</table>

Source path:

- `build/device-evidence/a3.5-dev16-route-record-20260824-190103/selected-frame.png`

### A3.5-dev17 - Route Replay Evidence

Local evidence includes one selected gameplay frame from the replay run.

<table>
<tr>
<td width="33%"><img src="history/screenshots/a35-dev17-selected-frame.png" width="260" alt="A3.5-dev17 selected gameplay frame"><br>Selected replay frame</td>
</tr>
</table>

Source path:

- `build/device-evidence/a3.5-dev17-route-replay-20260824-192336/selected-frame.png`

### A3.5-dev43 - Loading Screen Route Record/Replay Evidence

Local screenshot evidence for dev43 is loading-screen focused. The build is
still included because dev43 is an important route-record milestone, but no
separate gameplay PNG/BMP was found locally for this build.

<table>
<tr>
<td width="50%"><img src="history/screenshots/a35-dev43-loading-record.png" width="320" alt="A3.5-dev43 loading screen record frame"><br>Route-record loading frame</td>
<td width="50%"><img src="history/screenshots/a35-dev43-loading-replay-annotated.png" width="320" alt="A3.5-dev43 annotated loading screen replay frame"><br>Annotated replay loading frame</td>
</tr>
</table>

Source paths:

- `build/device-evidence/a3.5-dev43-route-record-20260825-022835/loading-screen-frame.bmp`
- `build/device-evidence/a3.5-dev43-route-replay-20260825-023903/loading-screen-frame-annotated.bmp`

### A3.5-dev45 - Replay Auto-Exit Evidence

Local screenshot evidence for dev45 is loading-screen focused. Dev45 remains
important because it proved route replay could return cleanly to LiveArea.

<table>
<tr>
<td width="33%"><img src="history/screenshots/a35-dev45-loading-replay-annotated.png" width="260" alt="A3.5-dev45 annotated loading screen replay frame"><br>Annotated replay loading frame</td>
</tr>
</table>

Source path:

- `build/device-evidence/a3.5-dev45-route-replay-20260825-025927/loading-screen-frame-annotated.bmp`

### A3.5-dev46 - Message Window and No-Dialogue Diagnostic Evidence

Local screenshot evidence for dev46 is loading-screen focused. Dev46 is still
listed because its runtime evidence proved SFX while dialogue text/audio was
still missing.

<table>
<tr>
<td width="33%"><img src="history/screenshots/a35-dev46-loading-replay-annotated.png" width="260" alt="A3.5-dev46 annotated loading screen replay frame"><br>Annotated replay loading frame</td>
</tr>
</table>

Source path:

- `build/device-evidence/a3.5-dev46-route-replay-20260825-034048/loading-screen-frame-annotated.bmp`

### A3.5-dev78 - Physical Loading Screen Regression Evidence

Local screenshot evidence for dev78 is loading-screen focused. These samples
show the late physical loading-screen state that dev82 explicitly targets with
the original loading text/progress path, viewport synchronization, prewarm, and
Render2D viewport restoration.

<table>
<tr>
<td width="50%"><img src="history/screenshots/a35-dev78-loading-physical.png" width="320" alt="A3.5-dev78 physical loading screen frame"><br>Physical loading frame</td>
<td width="50%"><img src="history/screenshots/a35-dev78-loading-annotated.png" width="320" alt="A3.5-dev78 annotated physical loading screen frame"><br>Annotated loading frame</td>
</tr>
</table>

Source paths:

- `build/device-evidence/a3.5-dev78-physical-20260828-logan-gate/original-loading-screen-level-ready-t28916211-frame.png`
- `build/device-evidence/a3.5-dev78-physical-20260828-logan-gate/original-loading-screen-level-ready-t28916211-frame-annotated.png`

## Builds With No Local Screenshot File

The current bash workspace has device-evidence directories but no matching
PNG/BMP screenshot file for these build groups:

`A3.5-dev6`, `A3.5-dev14`, `A3.5-dev18`, `A3.5-dev19`, `A3.5-dev20`,
`A3.5-dev21`, `A3.5-dev22`, `A3.5-dev23`, `A3.5-dev24`, `A3.5-dev34`,
`A3.5-dev36`, `A3.5-dev37`, `A3.5-dev38`, `A3.5-dev40`, `A3.5-dev41`,
`A3.5-dev42`, `A3.5-dev44`, and `A3.5-dev47`.

Those builds should be added later only if matching diagnostic captures are
returned or discovered with their evidence directories. Do not fabricate images
from logs.

## Gallery Manifest

| Gallery file | Dimensions | SHA-256 |
| --- | --- | --- |
| `a35-dev5-first-interactive.png` | 960x544 | `bc4731cd9b219d151442d0bec3dd8b58ffe3a93f02d26a710b73569a83a3bd70` |
| `a35-dev5-walk-manual.png` | 960x544 | `8cc47f87c213d8d602063d5955c056ef916d48c6e5408a95143aaee7c6f1389b` |
| `a35-dev5-spawn-control.png` | 960x544 | `c76234cacaa7fb8656a47688e9ba193aa49165c81126a398d9bf18f4a997dd89` |
| `a35-dev7-effects-130626.png` | 960x544 | `dfabfc377599f75da9281ecc1abd3d4cbe726fa11e576d09773cffcc1aee46e7` |
| `a35-dev7-effects-131326.png` | 960x544 | `78ebbfa5ead95477521d0790f32f32ddec6298c592ac612efeb2ffb7a83e911f` |
| `a35-dev7-effects-131654.png` | 960x544 | `dadd65c3644e36ba338aa36d24e0f9a01707cb561c8ca9ddbe58ac6d2a93125a` |
| `a35-dev7-effects-132016.png` | 960x544 | `9b2268a37f1df4b69fca2255af29b965eaf670fe01c743e17307909e03bd5ef3` |
| `a35-dev12-first-frame.png` | 960x544 | `f558a38b2e67ae19ca8d58513af53375466984efee3f034b2e18151ba81a933b` |
| `a35-dev13-selected-frame.png` | 960x544 | `c5ef700d03647e686a094be4506281a678300daeea80277ac7b9d28034667b97` |
| `a35-dev13-npc-crop.png` | 1000x1200 | `1fe44b496884acf19fed96550c7ccc133c9713b6319306ab1065e16fdc1a2c3a` |
| `a35-dev16-selected-frame.png` | 960x544 | `75200229c5e252ee84b3483f1c74734abab751a3fbfc46e58e7475dc69128d19` |
| `a35-dev17-selected-frame.png` | 960x544 | `4d96fec09a002efa18508b7985d313bab28115bf18306c4250c38d2c060dbb52` |
| `a35-dev43-loading-record.png` | 960x544 | `a7802519ccef02e9557e1da6ff6f5bba598250c6706b9449edcc41610de49117` |
| `a35-dev43-loading-replay-annotated.png` | 960x544 | `be3801d48c79e48264eae9fe96d0b4757967bd229dda6b8d97a8214edb2dc118` |
| `a35-dev45-loading-replay-annotated.png` | 960x544 | `4a1e3b5059f72e2a6967e0656674b0474eb1452c27ff2eb48e82337db1d32f4e` |
| `a35-dev46-loading-replay-annotated.png` | 960x544 | `6c691d71b741e09f5365c27784afc24e18c37474a7e9eda0c7d90d27bcfdbfaa` |
| `a35-dev78-loading-physical.png` | 960x544 | `872ecb6930b0703421c5599c2b52b16acf7c58e7600a9644c41859ef39e44690` |
| `a35-dev78-loading-annotated.png` | 960x544 | `88ac1dc9dc716e6c2438ae5bee0c2902443950b0f10b33daba48f26b371cc17a` |
