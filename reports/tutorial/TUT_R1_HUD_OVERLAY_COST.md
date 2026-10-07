# Tutorial round 1: HUD_OVERLAY_COST (RVHD1)

Agent TUT-R1-08. Branch `tut-r1-08-hud-overlay-cost`, based on
`tutorial-r1/base` (45c6cf5, main + FPS round 4 / dev240). Nothing was
compiled, nothing ran on Vita3K or hardware, and no gain here is measured.

## Question

What does tutorial 2D/HUD presentation still rebuild per frame after FPS
round 4 (help/objective text build-once, HUD glyph prewarm)? Look at the
tutorial help prompts, dialogue subtitles, the message window, objectives,
radar, target box, weapon/health HUD and the Vita presentation scopes.

## Findings

### 1. The steady-state HUD no longer rebuilds text every frame

Every sentence owner left on the single-player path is change-driven:

| Owner | Rebuild trigger | Evidence |
| --- | --- | --- |
| Help text (tutorial prompts) | dirty flag; identical repeats keep the build (R4) | `staging/combat/hud.cpp:721-751` |
| Objective message + range | index or 10 m range change; equal strings keep (R4) | `hud.cpp:2120-2177` |
| Target name | name string change; position change only moves vertices | `hud.cpp:1766-1785` |
| Weapon / vehicle name | weapon or seat change | `hud.cpp:991-1013` |
| Weapon chart key names | weapon count change / forced rebuild | `hud.cpp:1259-1263` |
| Radar compass | one sentence per direction, built once | `staging/combat/radar.cpp:498-523` |
| Powerup labels | built at add (R4, combat-a36-powerup-text-once) | `hud.cpp:405-416` (`:409`) |
| cGameData bottom text | cached and compared | `staging/commando/gamedata.cpp:1832-1856` |
| TextDisplay console | cached and compared | `staging/commando/textdisplay.cpp:249-269` |
| MultiHUD names | multiplayer only (`!IS_MISSION`) | `staging/commando/combatgmode.cpp:407-409` |
| Message / objectives-viewer TextWindow | `IsViewDirty` | `staging/combat/textwindow.cpp:1078` |

The Vita tutorial help strings are converted once, when the script sets the
prompt (`staging/combat/scriptcommands.cpp:3372`), not per frame. Health,
shield and ammo numbers use `Render2DTextClass` on a fixed Font3D texture
with `Generate_WChar_Text_From_Number` (`hud.cpp:83`, `937`, `2729`). There
is no per-frame UTF-16 `Format` on the single-player HUD.

### 2. Biggest remaining text cost: the message window builds twice per message

Dialogue subtitles (`soldier.cpp` Say_Dynamic_Dialogue; the Vita patch
forces `display_text`) and objective messages all go through
`MessageWindowClass::Add_Message`. The tutorial has more of these than any
other mission.

1. `Insert_Item` marks the view dirty (`textwindow.cpp:592`).
2. `Update_Window_Rectangle` (`messagewindow.cpp:364`) calls
   `Get_Total_Display_Height` (`messagewindow.cpp:459`), which is
   `Update_View(&h, info_only=true)` (`textwindow.cpp:889`). That pass is a
   full build: both sentence renderers are Reset, and every row gets
   `Build_Sentence`, `Draw_Sentence` and a new A4R4G4B4 atlas surface with
   glyph blits (`textwindow.cpp:982`). It leaves `IsViewDirty` set.
3. The window grows, so `Set_Backdrop` → `Free_Backdrop` clears `IsDisplayed`
   (`textwindow.cpp:196`), and `Display(true)` sets the view dirty again
   (`messagewindow.cpp:370`, `textwindow.cpp:1014`).
4. In the same frame, `On_Frame_Update` → `Get_Display_Count`
   (`messagewindow.cpp:287`) rebuilds every row a second time. The pending
   surfaces from step 2 are released without ever being uploaded.

So each message costs two full text builds and one atlas upload. The second
build is the same as the first whenever no row before the last crosses the
new text-area bottom. That is the normal case, because the window was just
sized to fit the text. Each expiry (`Delete_Item`, `messagewindow.cpp:313`)
costs one more build and one upload. That one cannot be avoided without
changing the atlas packing and the number of draws.

### 3. Smaller per-frame residuals (report only, not changed)

| Item | Evidence | Estimate (unmeasured) | Why not changed |
| --- | --- | --- | --- |
| Message window draws an empty head scene every frame: `WW3D::Render(Scene, Camera)`. The head model creation is commented out in the original. | `messagewindow.cpp:212`, `258` | 10-40 µs/frame, every mission | Its `Flush` also draws anything queued since the combat flush (mesh queue, static sort lists, `SortingRendererClass`), before the objective viewer, dialog and text overlays. It also leaves viewport, projection and render state behind. Skipping it can change draw order and state. It needs its own flag and a visual A/B, so it is deferred (candidate RVHD1 bit 1). |
| Objective pog fly-in: for 2 s after every objective add or update, each frame frees and `new`s one Render2DClass per pog plus one per flying star, with a texture lookup by name | `hud.cpp:2238-2307` | 10-40 µs/frame during fly-ins (about 6 tutorial objectives, `Mission00.cpp:2378-2674`) | Small and short-lived. A fix would mean structural renderer reuse. |
| Help prompt quads: per frame `Reset_Polys`, 2× `Draw_Sentence` and `Force_Alpha`, even while the text, position and colour do not change | `hud.cpp:758-782` | 10-40 µs/frame while a prompt is on screen | This is the original per-frame model, and there are no uploads. Caching the quads would need new Render2DSentence state. Deferred. |
| Target name: per frame TranslateDB lookup, WideStringClass copy and compare | `hud.cpp:1766-1773` | 1-3 µs/frame | Negligible |
| Powerup labels: per frame `Get_Text_Extents`, `Reset_Polys` and `Draw_Sentence` | `hud.cpp:576-582` | <5 µs/frame per toast | Negligible |
| Presentation scopes: 3 per frame (HUD Think, MessageWindow, render envelope) | `port/platform/a31_gameplay_boundary.cpp:306-322`; rect early-out at `port/renderer/vita/ww3d_vita_renderer.cpp:3591-3596` | <1 µs | Depth counter and two rect copies |
| Render2D vertex storage | `staging/ww3d2/render2d.cpp:109-115` (`Reset_Active`), 60-entry preallocation | 0 after growth | No per-frame reallocation. The per-draw dynamic VB/IB is covered by R4 RVRC1/RVGS1. |

## Change

`port/patches/combat-tut1-textwindow-measured-build.patch` (combat, applied
last in the combat list of `tools/stage_sources.sh`). The tracked
`staging/combat/textwindow.{h,cpp}` carry the same edit. All new code is under
`#if defined(RENEGADE_VITA_PORT)` and the patch only adds lines.

- After a height-only `Update_View`, record what the renderers now hold and
  every input of that build (`textwindow.cpp:855-866`): first line, row count,
  the largest bottom (`y + row_height`, the exact expression of the stop test)
  of the rows before the last, the text area, the column-header setting, the 2D
  resolution, the screen UV bias and device readiness.
- A later full `Update_View` (`info_only == false`, no height requested) keeps
  that build and skips the rebuild only when `Can_Keep_Measured_Build`
  (`textwindow.cpp:911`) holds:
  - same first line and row count, columns setting, and text-area left, top
    and right;
  - same resolution and UV bias, device ready;
  - no earlier row ends below the current `TextRect.Bottom`.

  The kept path sets exactly what the rebuild would: `CurrentDisplayCount` =
  all rows and `IsViewDirty = false` (`textwindow.cpp:763-768`).
- Every content, column or renderer change forgets the build: Insert, Delete,
  Set_Item_Text/Color, Delete_All_Items, Add/Remove/Delete_All_Columns and
  Free_Renderers (which Build_View and Free_Contents go through). The inline
  `Display_Columns` and `Set_Text_Area` change inputs that the predicate
  compares.
- Why the output is identical: a row build is a pure function of its text,
  colour, wrap width (text-area width and column widths), location (text-area
  left/top, preceding row heights, column height and line spacing, both fixed
  per renderer lifetime), the renderers' fixed fonts, the 2D resolution and UV
  bias read when renderers are created, and deterministic glyph data. All of
  those are either unchanged (every mutator forgets) or compared. The bottom
  edge only decides where a view update stops. The kept renderer state is the
  same state the rebuild ends in (same surfaces, quads, cursor, lock).
- Telemetry, with or without the flag:
  - `A4 hud-cost: version=1 mode=…` once, when the first TextWindow is created
    (level load);
  - `A4 hud-cost: textwindow mode=… full_builds=… measure_builds=…
    kept_measured=…` at power-of-two totals, so the log stays bounded;
  - a `WWPROFILE("TextWindow Build")` scope, which shows under RVFP1.

### Flag

`ux0:data/renegade/user/config/hud-cost-v1.flag` = exactly `RVHD1 X\n`, where
X is one hex digit. Bit 0 enables the measured-build reuse; bits 1-3 are
reserved. The parse is strict, in the same style as RVRC1, and is read once
(`port/compatibility/include/renegade_vita_hud_cost.h`, header-only, no
CMake change). **The default is OFF** (`RENEGADE_VITA_HUD_COST_DEFAULT 0`).
The argument above is construction plus a Python model of the logic. Neither
the real C++ nor a build has been run, so it is not yet proven bit-identical.
With the flag off, the remaining differences are the counters, the profile
scope and a few stores. Rendering is unchanged.

## Hypothesis ledger entry

- **Hypothesis**: The message window rebuilds all visible text twice for each
  dialogue subtitle or objective message: once for the height measurement and
  once for the view update. The second build is redundant. Keeping the
  measured build removes one full text build per message: a new atlas surface
  (new + memset, 8-128 KiB), glyph blits for every visible row and Render2D
  renderer allocations.
- **Risk**: low. Rendered output should be the same, gated by the predicate
  above, and the flag is off by default. Failure mode if the predicate missed
  an input: stale message-window text for one view update. The model test
  shows that dropping any compared term produces such mismatches, and the
  predicate includes all of them.
- **Estimated gain (unmeasured)**: about 0.2-0.8 ms of game-thread CPU on
  every frame that adds a message, and less surface-allocator churn. This is a
  hitch trim on message frames, not an average-FPS change: averaged over the
  tutorial it is well under 0.05 ms/frame. Atlas uploads are unchanged (one
  per message).
- **How to measure (tutorial route)**: Logan intro → Sydney → gunner range,
  where conversation density is highest.
  - From the `A4 hud-cost: textwindow` line: `kept_measured` should be about
    equal to `measure_builds`, and `full_builds` should fall by the same
    amount.
  - Under RVFP1 1: the `TextWindow Build` scope count and time, and the
    worst-frame breakdown on message frames.
  - p95, p99 and worst frame time over the conversation windows.
- **Decision**: adopt behind the flag. Make it default-on only after the A/B
  below shows identical subtitles.

## Verified vs unverified

Verified (pure Python and `patch`, no compiler):

- The patch applies at `--fuzz=0` to the pre-change staged files and
  reproduces tracked staging byte for byte. No later registered patch touches
  `textwindow.*`.
- Removing the port blocks yields the pre-image (non-blank lines identical),
  so non-port builds are unchanged.
- `python3 tools/renegade_patch_inventory.py --root .` passes (578 ordered
  patches; registry and hunk validation only, the staging receipt was not
  rewritten).
- `python3 -m unittest tools.test_hud_cost_textwindow`: 12 tests OK.
  - Static: mutator coverage, predicate terms, the stop-test expression, flag
    strictness.
  - Model: a Python transcription of TextWindow/MessageWindow over 40 seeds ×
    1500 frames, with random messages, decay, overflow/clamp, resolution and
    UV-bias changes, device loss, colour edits, paging, column toggles and
    text-area moves. Renderer contents are identical after every step and
    builds are saved. A subtitle flow goes from 2 builds/message to 1.
  - Mutation: removing any single predicate term (or first line + row count
    together) is detected.

Unverified:

- No ARM or host compilation. There may be compile errors, and the host
  target `a31_gameplay_seed_runtime` also compiles textwindow.cpp, with
  RENEGADE_HOST_ABI_TEST.
- No execution of the real C++, no Vita3K, no hardware.
- All costs and gains are estimates.

## Hardware A/B

1. Install the candidate and remove any `hud-cost-v1.flag`. Run the tutorial
   from the start through the gunner range, about 5 min. Pull
   `a35-*-runtime.log`. Expect `A4 hud-cost: version=1 mode=0` and textwindow
   lines with `kept_measured=0`.
2. Write `ux0:data/renegade/user/config/hud-cost-v1.flag` with exactly the 8
   bytes `RVHD1 1` + LF and repeat the same route. Expect `mode=1`,
   `kept_measured` close to `measure_builds`, and lower `full_builds`.
3. Optionally add `frame-profile-v1.flag` = `RVFP1 1` to both runs and compare
   the `TextWindow Build` scope and the p95/p99/worst frame times in the
   conversation windows.
4. Visual check with the flag on:
   - subtitle wrapping, colours and positions;
   - window growth for 1-4 lines;
   - top-line trimming when many lines arrive quickly;
   - expiry;
   - objective messages;
   - the EVA objectives viewer (unaffected path).
5. `RVHD1 0` + LF or no file returns to baseline.

## Files

- new `port/compatibility/include/renegade_vita_hud_cost.h`
- new `port/patches/combat-tut1-textwindow-measured-build.patch`
- `staging/combat/textwindow.h`, `staging/combat/textwindow.cpp`, the same
  edit as the patch
- `tools/stage_sources.sh`: one patch line plus a comment, appended after the
  last combat patch
- new `tools/test_hud_cost_textwindow.py`
- this report

`staging/PATCH_INVENTORY.json` was not edited. The coordinator's staging run
rewrites the receipt.
