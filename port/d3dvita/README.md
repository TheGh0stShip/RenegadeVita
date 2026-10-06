# VitaD3D graphics variant

An opt-in build of Renegade Vita in which the **original WW3D Direct3D 8
renderer** draws through [VitaD3D](https://github.com/TheGh0stShip/VitaD3D),
an independent Direct3D 8 implementation on GXM, instead of the native vitaGL
boundary renderer. vitaGL, vitashark and SceShaccCgExt are not linked.

The default build is unchanged; everything here is selected by
`RENEGADE_GRAPHICS_D3DVITA=ON`.

## What changes

| Layer | Default build | VitaD3D variant |
| --- | --- | --- |
| WW3D mesh/2D rendering | `port/renderer/vita` boundary on vitaGL | original `dx8wrapper`, `dx8renderer`, `dx8polygonrenderer`, `dx8texman`, `dx8caps`, `surfaceclass`, `textureloader`, `missingtexture` |
| Direct3D 8 | WW3D-shaped stand-ins | VitaD3D `vitad3d_core` + `vitad3dx8` |
| Movies | GL textured quad | D3D8 texture + `DrawPrimitiveUP` through `DX8Wrapper` state |
| Presentation services | native renderer | `renegade_d3dvita_presentation.cpp` (statistics, display size, touch mapping) |

Staging: `tools/stage_d3dvita_sources.sh` copies the committed `staging/`
tree to `build/staging-d3dvita/` and applies
`port/patches/d3dvita/`:

- `ww3d2-d3dvita-original-renderer.patch` returns the WW3D branches that route
  into the boundary renderer to the original DX8 path
  (`RENEGADE_VITA_PORT && !RENEGADE_D3DVITA`). Every other staged portability
  and correctness change is kept.
- `ww3d2-d3dvita-dx8wrapper-gcc.patch` hoists three MSVC 6 for-loop variables.

`include/renegade_d3dvita_win32_types.h` gives VitaD3D Renegade's Win32 types
(VitaD3D is compiled with it), and `include/renegade_d3dvita_win32.h` provides
the window and module calls the original `DX8Wrapper` makes: one 960x544
full-screen display and a `D3D8.DLL` whose `Direct3DCreate8` is VitaD3D's.

## Build

```bash
bash tools/stage_d3dvita_sources.sh
cmake -S . -B build/vita-d3dvita-full -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE=$VITASDK/share/vita.toolchain.cmake \
  -DRENEGADE_CANDIDATE_LABEL=A3.5-dev1-d3dvita \
  -DRENEGADE_VITA_TITLE_ID=RVDX00001 \
  -DRENEGADE_VITA_CONTENT_ID=EP9000-RVDX00001_00-RENEGADEVITAD3D0 \
  -DRENEGADE_GRAPHICS_D3DVITA=ON \
  -DRENEGADE_D3DVITA_SOURCE_DIR=/path/to/VitaD3D
ninja -C build/vita-d3dvita-full
```

The variant installs as its own title (`RVDX00001`) next to the default build
and uses the same retail data under `ux0:data/renegade/retail/`. Like
VitaD3D, it requires the user-supplied `ur0:data/libshacccg.suprx`.

## Hardware status (PSTV, RVDX00001, A3.5-dev1-d3dvita)

Verified on the PSTV through VitaD3D, from the runtime log under
`ux0:data/renegade/user-d3dvita/logs/` and front-buffer captures:

- Device creation, the 800x600 frontend and the 640x480 loading screens,
  letterboxed 4:3 into the 960x544 display through VitaD3D's scaled
  back-buffer presentation. Art, textures and fonts render correctly; lines
  in the loading screen's red text block overlap (open).
- Movies play through the D3D8 texture path at the current back-buffer size.
- The M00 tutorial loads and gameplay starts (mission script and conversation
  active). In-game rendering is not yet correct and frames take 0.7-1.9 s
  during the first minutes (runtime shader compilation); both are being
  diagnosed with VitaD3D's `draw.fail` markers and the automatic gameplay
  captures written to `user-d3dvita/captures/d3dvita-gameplay-f*.bmp`.

## Known gaps

- Render-to-texture targets (shadows, projectors) are not available in VitaD3D
  yet; those draws fail as they do in the default build.
- Backend memory queries report unavailable.
- In-game rendering correctness and frame time (see above).
