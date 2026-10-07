# Tutorial round 1: per-frame heap allocations (TUT-R1-09, RVAL1)

Source-only static audit. Nothing was compiled, built, launched or measured.
Every gain below is an unmeasured estimate.

## Result in one paragraph

The port's own per-frame and per-draw paths no longer allocate in steady state.
FPS round 4 and earlier work already moved them to grow-only scratch, fixed
rings and stack buffers. On the tutorial route, the one steady-state per-frame
heap allocation I could still find is in original Combat code: the HUD
target-name comparison copy. It takes one malloc and one free per frame while
the target box shows a named object (Logan, Sydney, the range targets, the base
buildings). The largest per-event port allocation is the zero-filled RGBA
vector, 16 to 256 KiB, made for every Render2DSentence text atlas. Both now
reuse storage, behind one flag. A new pure-Python guard test fails if any of 50
audited hot functions brings back an allocation pattern.

## Method

- I read every function on the frame path from the native loop
  (`a31_vita_runtime.cpp:6277` `while (true)`) into simulation, render, audio
  update, telemetry and logging. I followed each one into the port renderer, the
  DX8 boundary, input, Miles and the flight recorder.
- I grepped the port tree and all 578 registered patches for `std::vector`,
  `std::string`, maps, `new`, the malloc family, `push_back`, `resize`,
  `Delete_All()`, `StringClass`/`WideStringClass` locals and `.Format`.
- I ran a heuristic scan of staged original `Render`/`Think`/`Update`/`Process_*`
  bodies, then checked each hit by hand.
- I read `retail-pc/Data/always.dbs` (`objects.ddb`) read-only to settle one
  lead (weapon-chart rebuilds, below).

Call counts come from `A3.0-HARDWARE-M00-WORLD-VALIDATION.md` (654 meshes on
the first physical M00 frame) and the code structure.

## Audit of port-owned hot paths (steady state)

| Path (file:function) | Est. calls/frame (tutorial) | Heap per call | Evidence |
| --- | --- | --- | --- |
| `ww3d_vita_renderer.cpp` `Submit_Mesh_Internal` | ~650+ (meshes + material passes) | 0 | skin scratch grow-only (`:129`), procedural APT retained (`:4899` reference to a global), vertex-array/indexed batches are globals |
| `Submit_Indexed_Triangles`, `Draw_Vertex_Array_Batch`, `Replay_Static_Mesh_Entry` | per HUD/particle/2D draw, per batch, per cached mesh | 0 | fixed or global batch storage |
| `Begin_Material_Color_Pass` | per lit material pass | 0 after warm-up | `new[]` only when `entry_count > g_material_color_capacity` (`:2042`) |
| `Bind_Texture_Stage`, `Apply_*_State`, `Apply_DX8_Render_State` | 1000s | 0 | shadow tables |
| `End_Frame` + 120-frame telemetry | 1 | 0 | stack `vsnprintf` into the async ring |
| `ww3d_dx8_boundary.cpp` `Submit_Bound_Triangles` | per DX8 draw | 0 after warm-up | strip expansion grow-only (`:1903`) |
| `DX8Wrapper::Draw_*`, `Set_*_Buffer`, `Apply_Render_State_Changes` | per draw | 0 | refcounts only; dynamic VB/IB are original grow-only owners (`ww3d2-a35-dynamic-buffer-growth.patch`) |
| Material-pass queue | per extra pass | 0 after warm-up | free list (FPS R4, `:129`) |
| `a31_gameplay_boundary.cpp` `A31_Interactive_Run_Simulation_Frame` / `_Render_Frame` | 1 | 0 | trace strings are fixed `char[]` `snprintf` |
| `A31_Interactive_Get_Mission_Progress_State` | 1 | 0 | static remark copy (`:687`, FPS R4) |
| `a31_vita_runtime.cpp` loop body, `Copy_Flight_Memory`, `Copy_Renderer_Statistics` | 1 | 0 | memory query sampled every 30 frames |
| `A30_Vita_Log`, `Vita_Append_A22_Runtime_Breadcrumb`, `RenegadeAsyncLogRing::Enqueue` | 0–1 (gated/sampled) | 0 | stack buffers + fixed 256 KiB ring |
| Frame profiler (`Find_Slot`, Begin/End, End_Frame) | 100s–1000s scopes | 0 | fixed 256-slot table |
| Flight recorder `A35_Campaign_Flight_Record_Frame`, script lookup telemetry | 1 / per lookup | 0 | fixed rings and sample arrays |
| `DirectInput::Read`, `Record_Sample`, `Sample_Touch_Port` | 1 | 0 | route buffer allocated once at load |
| Miles `Publish_Pending_Position` / `Apply_Pending_Positions_Locked` | per 3D sound update | 0 | fixed pending slots |
| `surface_boundary.cpp` | — | — | `Create_Store` is never called (dead) |

## Remaining allocation sites, ranked

| # | Site | Frequency on the tutorial route | Status |
| --- | --- | --- | --- |
| 1 | `staging/combat/hud.cpp:1776` (pre-patch `:1766`) `WideStringClass translate_string = ...Get_String()` in `Target_Update` | every frame while the target box shows a named object: 1 malloc + 1 free | **changed** (RVAL1 bit 1) |
| 2 | `ww3d_dx8_boundary.cpp:1213` (pre-change) `std::vector<unsigned char> rgba(W*H*4)` in `Create_Texture_From_Surface` | each Render2DSentence atlas build (subtitle remark, target-name change, objective-range step every 10 m, help text), and each archive TGA load | **changed** (RVAL1 bit 0) |
| 3 | Same path: original `SurfaceClass` (`render2dsentence.cpp:919`), `IDirect3DTexture8`, `Allocate_Texture_Surface_Levels` (3 small arrays, `:942`), retained CPU copy (`Attach_Texture_Surface_Copy`, `:1175`) | per atlas build | unchanged. The copy backs the DX8 Lock contract; dropping it for text atlases needs a proof that no lock path is reached. Follow-up candidate. |
| 4 | Static mesh cache upload `malloc` batches/materials (`ww3d_vita_renderer.cpp:3120`) | per cache entry (re)build | unchanged; GL buffer creation dominates |
| 5 | `new LogicalSoundClass` (`a31_gameplay_boundary.cpp:1586`) | per AI-audible event | unchanged (original ownership) |
| 6 | Whole-file stream image (`renegade_miles_provider.cpp:1137`) | per streamed dialogue/music open | unchanged; it is the decode source (see `ADPCM_STREAMING_DESIGN.md`) |
| 7 | Loading-only vectors/strings and file images (`a31_vita_runtime.cpp:4067`, `:4198`) | loading screen | out of scope |

Leads checked and rejected:

- **`HumanAnimControlClass::Update` "allocates one `HAnimComboDataClass` per anim
  per frame with the malloc lock"** (`FPS_R4_SIM_HOTPATHS.md`,
  `FPS_R4_ANIMATION_HTREE.md`). This is not heap churn. `HAnimComboDataClass`
  derives from `AutoPoolClass<HAnimComboDataClass,256>` (`hanim.h:176`), so `new`
  and `delete` use the object pool's free list (a `FastCriticalSection`, not
  malloc). `HAnimComboClass::Reset` ends with `Reset_Active()`, which keeps the
  vector's storage. No change needed. Both reports should be corrected.
- **Weapon chart rebuilt every frame.** `Weapon_Chart_Update` (`hud.cpp`)
  rebuilds while `Get_Count()-1 != WeaponChartIcons.Count()`. Icons are made only
  for `(int)KeyNumber` in 0..9, so a weapon outside that range would force a
  rebuild every frame for 3 s after each pickup. The retail `objects.ddb` has 145
  weapon definitions, all with KeyNumber in [0, 9.3]. The counts always match, so
  the chart rebuilds only on real changes.
- `HUD` ammo/health/score use `char` buffers and `Render2DTextClass`. Other HUD
  strings use the temporary hint `(0,true)`. Name, chart and objective text are
  rebuilt only on change (FPS R4 build-once).
- `MultiHUD`/player/team overlays return early or only render retained
  renderers in single player.

## Changes

### RVAL1 flag (new header)

`port/compatibility/include/renegade_vita_frame_alloc.h`: the file
`ux0:data/renegade/user/config/frame-alloc-v1.flag` holds exactly
`RVAL1 <hex digit>\n`. It is parsed like `RVRC1`, read once (inline function
static), and primed in `RenegadeVitaRenderer::Initialize` with a breadcrumb:

```
[... frame-alloc NNN] version=1 mode=3 texture_rgba_scratch=1 hud_target_name_temp=1 default=3 acceptance=unassessed
```

| Bit | Name | Default | Off switch |
| --- | --- | --- | --- |
| 1 | `TEXTURE_RGBA_SCRATCH` | on | `RVAL1 2` |
| 2 | `HUD_TARGET_NAME_TEMP` | on | `RVAL1 1` |
| — | everything original | — | `RVAL1 0` |

### Bit 0: texture-creation RGBA scratch (`ww3d_dx8_boundary.cpp` `Create_Texture_From_Surface`)

The function now converts into the existing `thread_local
g_surface_upload_rgba` with `resize()` instead of building a fresh zero-filled
vector. That scratch is already used by `Upload_Texture_Level_From_Surface` and
released by `RenegadeVita_Release_DX8_Scratch`.

- It may grow only for creations of at most 256 KiB, which covers every
  Render2DSentence atlas (`CurrTextureSize` is at most 256). A larger creation
  uses the scratch only if it already has the capacity; otherwise it uses a
  local vector as before.
- Retained memory therefore never exceeds max(existing high-water, 256 KiB).
- With the flag off, `transient_rgba.resize(n)` is exactly the old
  `std::vector<unsigned char> rgba(n)`.

Why the output is identical:

- Every success case of `Convert_Surface_Pixel_To_RGBA` writes all four bytes.
  The only other case is `default: return false`, which returns the
  checkerboard fallback.
- The loop covers every pixel before the checksum and `glTexImage2D` read the
  buffer.
- `ResidentBytes = rgba.size()` is still `W*H*4`.
- Nothing between the `resize` and the upload touches the scratch.
- vitaGL copies `glTexImage2D` data synchronously, which the existing upload
  path already relies on.

The guard test asserts each of these. There is also a small loading-time
benefit: every archive TGA of 256×256 or less now reuses the scratch.

### Bit 1: HUD target-name temporary hint (`port/patches/combat-tut1-hud-target-name-temp.patch`)

Under `RENEGADE_VITA_PORT`, the original construction becomes
`WideStringClass translate_string(<same source>, RenegadeVitaFrameAlloc::Enabled(HUD_TARGET_NAME_TEMP))`.
The `#else` branch is the original code, unchanged.

- With the flag on, it uses WWLib's own temporary-buffer pool (4 × 256 WCHAR,
  `widestring.cpp:84-130`, mutex-guarded).
- A name of 256 or more characters, or an exhausted pool, falls back to the
  heap exactly as before.
- With the flag off, it is the same copy constructor with `hint_temporary=false`.
- Comparison, MCT reassignment and `TargetNameString` assignment are unchanged.
  Values are identical; only the storage differs.

The patch was generated with `diff -u` against the current tracked staged
`hud.cpp`. It is appended after the last combat patch in
`tools/stage_sources.sh`, so no SHA anchor moves. It dry-runs at `--fuzz=0`, and
the edited staged file is byte-identical to applying it.
`renegade_patch_inventory.py --root .` passes (578 patches). As required,
`staging/PATCH_INVENTORY.json` was not regenerated. The coordinator must rerun
staging to refresh the receipt.

### Guard test (`tools/test_frame_allocation_guard.py`, pure Python)

- Extracts 50 hot functions by exact signature (a missing or renamed signature
  fails the test). It strips comments and strings, then rejects:
  - by-value STL containers;
  - `new` and the malloc family;
  - `push_back`, `emplace`, `insert`, `resize`, `reserve` and `assign`;
  - `std::to_string` and `make_*`;
  - shrinking `Delete_All()`;
  - non-temporary `StringClass`/`WideStringClass` locals;
  - by-value `ConversationRemarkClass` or `DynamicVectorClass`-family locals.
- Three grow-only sites are allowlisted, and only when their capacity guard
  precedes the allocation.
- It also checks the RVAL1 contract and prefix uniqueness, the output-identity
  invariants above, the HUD patch registration, and that `patch -R --dry-run`
  of the HUD patch succeeds on the tracked staging file.
- It has a self-test of the scanner (9 known positives, 8 known negatives).
- A mutation check against `HEAD` flags the old `rgba(` vector and the old
  `translate_string =` copy.

## Hypothesis ledger entry

- **Hypothesis:** removing the last steady-state per-frame heap round-trip on
  the tutorial HUD path, and the 16–256 KiB zero-filled transient per text-atlas
  build, reduces newlib malloc-lock traffic (shared with the mixer, vitaGL GC
  and log threads) and large-block churn during dialogue-heavy tutorial
  sections.
- **Risk:** very low. The bytes are identical by construction. Bit 0 keeps up
  to 256 KiB of extra heap retained for the WW3D session, which is a deliberate
  trade against repeated large alloc/free. Bit 1 holds one WWLib temp slot
  during `Target_Update`.
- **Estimated gain (unmeasured):**
  - Bit 1: about 1–2 µs per frame while targeting, below frame-time noise.
  - Bit 0: per atlas build, one 16–256 KiB malloc, memset and free avoided,
    about 5–80 µs per build at roughly 0.5–2 builds per second. Per-frame
    averages are negligible.
  - The main value is fewer large-block heap events (fragmentation and
    heap-pressure risk) and a regression guard. **No FPS gain is expected or
    claimed.**
- **How to measure:** on the fixed tutorial route (see below), compare `A3.5
  heap` `in_use`/`free`/`top_free` drift and the largest free block between
  `RVAL1 0` and the default. Use frame-profile `Vita Render Overlays and HUD`
  and `Vita Render End_Render` median/p95/p99, plus any malloc-lock contention
  visible as audio `output_lock_starvation_buffers`.

## Verified vs unverified

- Verified (host, static):
  - `python3 -m unittest tools.test_frame_allocation_guard` passes (6 tests).
  - The related pure-Python contract tests (texture surface/provenance, indexed
    state, skin submission, hanim combo guard, particle keyframe guard, mission
    teardown, required level load, DataSafe, M08 readiness, explosion recycler)
    pass: 66 tests.
  - The patch registry passes.
  - The HUD patch dry-runs cleanly at fuzz 0.
- Unverified:
  - **Nothing is compiled.** The ARM build, host builds that compile `hud.cpp`
    or the DX8 boundary, and the g++-based tests were not run, by rule.
  - No Vita3K or hardware run.
  - The temp-pool behaviour and the bounded scratch are argued from source.

## Hardware A/B steps

1. Install the candidate. Delete `frame-alloc-v1.flag` (default mode 3). Check
   that the log shows `frame-alloc ... mode=3`.
2. Fixed tutorial route: Logan dialogue → Sydney → gunner range, picking up
   every weapon, and aim at the targets and Logan for at least 10 s → Mobius →
   HMVV drive to the base → stand in front of each building.
3. Record frame p50/p95/p99/worst, the `A3.6 frame-profile` windows, the `A3.5
   heap` checkpoint lines and the `texture-state`/`render-work-cache` lines.
4. Repeat with `RVAL1 0\n`, then with `RVAL1 1\n` and `RVAL1 2\n` to isolate each
   bit.
5. Visual check: subtitles, target names (including MCT names in buildings),
   objective range text and help text are identical. Each bit changes storage
   only.

## Files touched (conflict risk)

- `port/renderer/vita/ww3d_dx8_boundary.cpp`: one include, `Create_Texture_From_Surface` body, scratch comment.
- `port/renderer/vita/ww3d_vita_renderer.cpp`: one include and a 7-line
  breadcrumb after `Read_Vertex_Array_Mode()` in `Initialize`. Other agents'
  flag reads at the same spot will cause a trivial merge conflict.
- `staging/combat/hud.cpp` and the new patch. Another hud.cpp patch from this
  round must be ordered relative to it.
- `tools/stage_sources.sh`: 4 lines appended after the last combat patch.
- New: `port/compatibility/include/renegade_vita_frame_alloc.h`, `tools/test_frame_allocation_guard.py`, this report.
