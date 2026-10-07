# TUT-R1 TEXTURE_BUDGET: tutorial texture residency and upload cost

Agent TUT-R1-01, branch `tut-r1/texture-budget`, base `45c6cf5`
(tutorial-r1/base). **Nothing was compiled or run on Vita3K or hardware.** All
byte and time figures are static estimates from unchanged retail headers
(`retail-pc/Data`, read-only) and from source reading. No gain is measured.

## Verdict

The tutorial's texture path is already in good shape. In the static M00
closure, every DDS stays compressed on the GPU. Nothing is decoded, nothing is
oversize, no file is uploaded twice under two names, and nothing is evicted
and uploaded again.

The only expanded uploads are 14 archive TGAs: 5.7 % of the textures but
19.6 % of the GPU bytes. The 7 A1R5G5B5 TGAs among them are expanded to 32 bits
for no reason. One change is implemented behind a switch that is off by
default: keep those 7 TGAs at 16 bits (RVTX1 bit 0). In the tutorial this
saves about 0.8 MB. The same code path matters far more for M08, where 214
such TGAs make up about 28 MB of avoidable residency.

## Tutorial texture receipt (static closure)

Run `python3 tools/tutorial_texture_budget.py --data <retail Data> --output build/tutorial-texture-budget.json`.

- The receipt is not committed. It holds only retail-derived names and sizes,
  no asset bytes, and is written under the git-ignored `build/` directory.
- Closure inputs:
  - 31 W3D members of `M00_Tutorial.mix`;
  - 194 W3D names from `m00_tutorial.dep`;
  - render objects reached through HLOD or aggregate references.
- Models: 246 resolved and 12 unresolved. The unresolved ones are HLOD
  container prefixes such as `mgagd_int`, which have no file of their own.
  They are leads, not missing assets.
- Search order follows `a31_vita_runtime.cpp:5120-5125`: loose `Data/`, then
  `Always2.dat`, `always.dbs`, `always.dat` and `M00_Tutorial.mix`.
- Prelit wrapper: multi-pass (`ww3d.cpp:210`), using the
  `meshmdlio.cpp:335-367` fall-through.

| Path at the DX8 boundary | Keys | Formats | Est. GPU bytes |
| --- | ---: | --- | ---: |
| Native compressed DXT (archive blocks, authored mips) | 231 | 198 DXT1, 33 DXT5 | 7,856,712 |
| TGA → RGBA8888, level 0 only, CPU per-texel convert | 14 | 7 A1R5G5B5, 4 R8G8B8, 3 L8 | 1,918,528 |
| CPU-decoded DDS (DXT3, NPOT, sub-4×4 tails) | 0 | — | 0 |
| Missing / fallback | 0 | — | 0 |
| **Total** | **245** | | **9,775,240 (9.32 MiB)** |
| Total with `RVTX1 1` | | | 8,980,616 (−794,624, −8.1 %) |

Other facts from the receipt:

- **Size:** the largest dimension is 512, for 9 textures: `e_master01` (DXT5)
  and 8 character and vehicle skins (DXT1). No texture exceeds 1024. Of the
  245, 126 top out at 256. Nothing is oversize for 960×544.
- **Lightmaps:** 44 are 256² DXT1 from `M00_Tutorial.mix`, requested as
  `MIP_LEVELS_2`, for 1.80 MB in total.
- **Mip requests:** none are mixed. The static estimate does not depend on
  which request loads first.
- **CPU conversion at load:** 478,540 TGA texels, all on the loading screen.
  Today they cost an estimated 25–40 cycles per texel, about 27–43 ms in total
  (estimate only).
- **Prewarm budget:** the total fits the 32 MiB soft extra budget of
  `Warm_Original_M00_Referenced_Textures` (`a31_vita_runtime.cpp:1897-1921`)
  about 3.4 times over. The 24 MiB free-memory floor is never approached:
  dev230 logs show about 150 MB of vitaGL pool free after init.
- **Cross-check against hardware:** the dev229/dev230 tutorial logs report
  249 referenced textures prepared during the M00 prewarm, none deferred. The
  closure finds 245 keys; the difference is textures loaded by code (HUD and
  UI).

## Findings (file:line, current tree)

1. **DXT stays compressed in the tutorial.**
   - `Native_DXT_Level_Count` (`ww3d_dx8_boundary.cpp:1488`) and the
     whole-chain check at `:1679` accept DXT1/DXT5 textures that are
     power-of-two, at most 2048, and have every requested level at least 4×4.
   - `DDSFileClass` drops the two smallest file levels (`ddsfile.cpp:85`), so
     square full chains end at 4×4.
   - All 231 tutorial DDS, including the 6 non-square ones, qualify. Upload is
     only the block swizzle copy: no CPU decode, no retained 32-bit copies.
2. **Latent cost outside the tutorial: the decode path.** Triggers are DXT3,
   NPOT, over 2048, or a requested chain with levels under 4 texels.
   - Every level is decoded to RGBA8888 on the CPU (DXT3 per pixel through
     `DDSFileClass::Get_Pixel`, since `:1803` limits the block decoder to
     DXT1/DXT5), and every decoded level is kept as a CPU surface.
   - Each level is then sent with `glTexImage2D(level)` (`:1846`). In vitaGL
     `6e7fe40`, `textures.c:923-924` handles any level above 0 by calling
     `gpu_alloc_mipmaps`, which ignores the supplied pixels and regenerates
     the chain by downscaling (`gpu_utils.c:808-899`). The authored mips and
     their CPU decode are therefore wasted, and generated mips replace
     authored ones.
   - Zero tutorial textures take this path, and none in M01, M08 or M13 by
     the same tool, so nothing was changed.
   - The generator still ranks this case (`dxt_sub_block_tail_keep_compressed`,
     `dxt3_native_ubc2`) so a future level that uses it shows up.
3. **TGA uploads are expanded and have no mips.**
   - `Create_Texture_From_Surface` (`:1325`) converts every texel to RGBA8888
     and uploads level 0 only, with `GL_LINEAR` and `MipLevels` 1 (`:1377`,
     `:1404`).
   - The original PC loader kept A1R5G5B5 at 16 bits
     (`textureloader.cpp:1359`; `ww3dformat.cpp:265`) and generated a full mip
     chain (`textureloader.cpp:1466-1560`).
   - 16-bit storage is implemented below. The missing mips are a fidelity gap
     and stay report-only, because vitaGL generates mips for a GL 5551 texture
     using the `U1U5U5U5_ABGR` transfer layout, whose bit fields do not match.
4. **No duplicate uploads.**
   - Each lower-case spelling is its own `TextureClass` key
     (`assetmgr.cpp:1045`). No tutorial texture is requested under two
     spellings that resolve to the same file.
   - Four pairs of different archive members have identical bytes (muzzle
     flash, muzzle smoke, Nod logo / Scorpion, busted glass), 87,368 GPU bytes
     duplicated in total. This is in the data and owned by the original asset
     manager, so it is report-only.
5. **No eviction churn.**
   - File textures default to a 30 s `InactivationTime` (`texture.cpp:187`).
     The original evicts them from `TextureLoader::Update` →
     `Invalidate_Old_Unused_Textures(0)` (`textureloader.cpp:822`).
   - The Vita replaces `TextureLoader::Update` with a network-callback stub
     (`a4_frontend_lifecycle_boundary.cpp:149`), so prewarmed tutorial
     textures are never evicted and uploaded again.
   - Guard: restoring the original update would bring this churn back in the
     middle of a level.
6. **The texture-resolution option has no effect.**
   - `Apply_Performance` sets `WW3D::Set_Texture_Reduction`
     (`renegade_vita_options.h:67`), and `TextureClass::Get_Reduction` exists
     (`texture.cpp:632`).
   - But the Vita DDS path always builds `DDSFileClass(filename, 0U)` (`:1629`).
   - Default reduction is 0, so there is no default impact. This is a possible
     future memory option, not an optimisation here.

## Change: RVTX1 bit 0, archive A1R5G5B5 TGAs uploaded at 16 bits

The switch is `ux0:data/renegade/user/config/tutorial-texture-v1.flag`,
containing exactly `RVTX1 1\n`. **Default off:** if the file is absent,
`RVTX1 0\n` or malformed, every path is unchanged.

- **New header `port/renderer/vita/texture_upload_packing.h`** (pure and
  host-testable):
  - the strict flag grammar;
  - the A1R5G5B5 → RGBA5551 field move `((p & 0x7fff) << 1) | (p >> 15)`,
    applied row by row;
  - the vitaGL linear-storage estimate.
- **`ww3d_dx8_boundary.cpp`:**
  - `Texture_Packing_Mode()` reads the flag once and logs
    `tutorial-texture version=1 mode=… pack_a1r5g5b5=…`.
  - `Create_Packed_A1R5G5B5_Texture()` uploads with
    `glTexImage2D(GL_RGBA, GL_RGBA, GL_UNSIGNED_SHORT_5_5_5_1)`. This is
    vitaGL's fast-store memcpy into `SCE_GXM_TEXTURE_FORMAT_U5U5U5U1_RGBA`.
    Filtering and wrap are the same as the RGBA8888 path; no mips are added.
  - The gate is in `Create_Texture_From_Surface` (`:1340`) and applies only
    to `!retain_surface_copy` (archive TGAs that can be decoded again) with
    `D3DFMT_A1R5G5B5`. Any failure, including a GL error, returns NULL and
    leaves no GL object, so the unchanged RGBA8888 path runs instead.
  - CPU access to the texture still rebuilds the source surface lazily. A
    later unlock re-uploads RGBA8888 into the same object, as today.
  - `Load_Targa_Texture` now logs totals for archive TGAs in both modes:
    `tutorial-texture archive-tga loads= packed16= texels= resident_bytes= decode_us= convert_upload_us= mode=`.
    It logs every load up to 16 and then at powers of two.
- **Why it is correct:** the D3D A1R5G5B5 fields are moved without rounding
  and match vitaGL's GL 5551 layout. This is proven in Python for all 65,536
  inputs, using the expression taken from the header text. The PC also kept
  this format at 16 bits.
- **Why it is off by default:** it is not bit-identical. The GPU expands 5-bit
  channels in hardware, while the old path used `floor(v*255/31)`. Both stay
  within one 8-bit step, but they can differ. The U5U5U5U1 channel order on
  real GXM has also not been seen on hardware.
- **Shared file touched:** only `port/renderer/vita/ww3d_dx8_boundary.cpp`,
  with additions confined to the texture-creation functions. There are no
  staging or upstream patches, and no changes to `a31_vita_runtime.cpp`,
  `ww3d_vita_renderer.cpp` or `tools/build.sh`.

### Hypothesis-ledger entry (RVTX1-1)

| Field | Value |
| --- | --- |
| Hypothesis | Uploading archive A1R5G5B5 TGAs as RGBA5551 halves their GPU residency. It also replaces the per-texel RGBA8888 expansion and FNV pass with a field move. |
| Est. tutorial gain | −794,624 GPU bytes (7 textures; the 6 MCT/PCT terminal skins plus `atr_scrnstat_c`). 397,312 texels no longer expanded, about 15–35 ms less CPU at load. Any frame-time effect is possible texture-bandwidth relief while terminals are on screen; it is unmeasured and **not claimed**. |
| Est. campaign gain | M08: 214 textures, −27.9 MB (TGA residency about 55.9 → 28.0 MB), about 0.5–1 s less load time. M01: −139 KB. M13: none. |
| Risk | Visual: wrong channel order on GXM would show as a colour swap on the terminal screens. Possible ±1 LSB channel rounding. Vita3K format support is not assessed. On any GL error the old path runs. |
| Switch | `RVTX1 1` on, `RVTX1 0` or absent off (default) |
| Decision | Deferred pending hardware A/B; not adopted. |

## Verification status

Verified on the host, pure Python, no compiler:

- `python3 -m unittest tools.test_tutorial_texture_budget` passes 13 tests on
  synthetic MIX, DDS, TGA and W3D fixtures. They cover:
  - closure and search-order precedence;
  - prelit wrapper selection;
  - the drop-two-levels rule;
  - native vs decode decisions, including sub-block tails and DXT3;
  - vitaGL byte models;
  - fallbacks and duplicates;
  - ranking, and confirming no asset bytes are emitted.
- `python3 -m unittest tools.test_vita_texture_packing_contract` passes 10
  tests: exhaustive 16-bit proofs of the re-pack expression read from the
  header, the strict flag grammar, and the boundary gate, transaction and
  logging contract.
- The existing pure contract tests still pass: `test_vita_texture_surface_contract`,
  `test_vita_texture_provenance_contract`, `test_vita_loading_screen_contract`,
  `test_vita_indexed_state_contract` and `test_cinematic_presentation_contract`.
- `test_original_decal_submission.test_anchored_connected_replay` errors only
  because `upstream/CnC_Renegade/Code` is not populated in this worktree. That
  is a worktree environment issue, unrelated to this change.
- Tests that compile were not run, per the round rules: `test_vitagl_dds_chain`,
  `test_vita_render_state_shadow`, `test_vita_static_mesh_cache` and others.

Not verified:

- The ARM compile of the boundary edit.
- vitaGL/GXM U5U5U5U1 channel order and sampling on hardware.
- Every load-time and bandwidth estimate.
- Runtime-only textures (HUD, scripts, definitions) outside the static closure.

## Hardware A/B (tutorial route)

1. **Baseline:** no flag file. Play from boot through Logan, Sydney, the
   gunner range, Mobius and the vehicles, then enter the base buildings
   (barracks, refinery, power plant, weapons factory). Look at the PCT and MCT
   terminals and keep the runtime log.
2. **On:** write `RVTX1 1` plus LF (exactly 8 bytes) to
   `ux0:data/renegade/user/config/tutorial-texture-v1.flag`. Relaunch and take
   the same route.
3. **Compare the logs:**
   - expect `tutorial-texture version=1 mode=1 pack_a1r5g5b5=1`;
   - the last `archive-tga` line should show `packed16=7`;
   - `resident_bytes` should fall by about 794,624;
   - compare `convert_upload_us`;
   - check the M00 prewarm duration;
   - compare frame p50/p95/p99 while terminals fill the view (`RVFP1`
     profile on).
4. **Visual check:** compare screenshots of the terminal screens (textures
   `agd_pct_master`, `bar_pct_master`, `ref_pct_master`, `mct_con-ref-hnd`,
   `mct_pwr-com-obl`, `mct_wep-atr`, `atr_scrnstat_c`). Any colour or alpha
   change rejects the switch.
5. **Optional confirmation:** on M08, compare `A4 M08 referenced textures:
   resident_after` (expect about −28 MB) and the load time.
