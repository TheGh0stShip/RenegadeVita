# Campaign mission memory estimates

Status: static, read-only estimate from MIX/DDS/TGA/WAV/W3D headers of an unchanged retail
Data directory (`retail Data tree`). Numbers only: no retail bytes, names beyond file names, or
thumbnails are stored. Host/static analysis; **not a hardware measurement**. M13 is the
only campaign level known to load on physical Vita and is the 1.00x baseline. M00 is shown
as a second reference. Regenerate with
`python3 tools/campaign_mission_memory_estimates.py --data-dir <Data> --output reports/campaign/MISSION_MEMORY_ESTIMATES.md`.

## Method and assumptions

- Texture residency follows `port/renderer/vita/ww3d_dx8_boundary.cpp`: power-of-two DXT1/DXT5
  DDS (4 <= side <= 2048) uploads DXT blocks unchanged (`native-dxt`; GPU bytes = block chain over
  the stored mips, no retained CPU copy). Uncompressed/DXT3/non-power-of-two DDS takes the RGBA8888
  decode path (`decode-rgba`): GPU bytes = `sum(w*h*4)` over the mip chain plus an equal retained
  CPU surface chain. TGA (`tga-rgba`, `Create_Texture_From_Surface`) uploads **level 0 only** as
  RGBA8888 (GPU bytes = `w*h*4`, no mips) and retains one source-format surface copy in the C heap
  (`w*h*{1,2,3,4}` for 8/16/24/32-bit TGA). Retained-surface sizes are from source reading, not measured.
- Closure set: the original per-level `.dep` W3D list, plus HLOD sub-object W3Ds found in
  the mission MIX or the shared archives, plus every texture name (`W3D_CHUNK_TEXTURE_NAME`,
  emitter texture) those W3Ds carry. `.tga` names resolve through the `.dds` alias first, then
  `.tga`, searching mission MIX, `Always2.dat`, `always3.dat`, `always.dat`. This approximates
  the texture hash the Vita loader walks in `Warm_Original_Campaign_Referenced_Textures`
  (48 MiB extra-prepare budget, 24 MiB vitaGL free floor). It excludes HUD/UI, characters spawned
  from definitions only in `always.dbs`, effects spawned by scripts, and cinematic-only assets.
- Heap proxy (main 192 MiB newlib heap): `.lsd + .ldd` bytes + W3D closure file bytes +
  retained CPU texture copies + decoded PCM of mission-local WAVs. W3D/LSD in-memory expansion
  factors are unknown and treated as 1.0x; this is a relative ranking input, not an absolute
  total. It omits the engine/physics baseline, vitaGL meshes, and streamed dialogue.
- Risk score = max(GPU texture ratio, heap-proxy ratio), each relative to M13.
- Audio: WAV PCM16 size derived from the fmt/fact fields (IMA/MS ADPCM about 4x). MP3 is
  streamed through the MPEG path and is not counted as resident PCM. Shared dialogue is referenced
  by name from level data (`.ldd/.lsd/.txt/.dep` strings); this is a lower bound because
  most sound/conversation definitions live in `always.dbs`.

Vita budgets for context: newlib heap 192 MiB (`a30_main.cpp`), vitaGL extended init with 4 MiB
legacy pool and a 16 MiB RAM threshold (`ww3d_vita_renderer.cpp`), texture prepare 48 MiB,
static mesh cache 24 MiB.

## Ranking against M13

| Rank | Mission | Score vs M13 | GPU tex ratio | Heap ratio | Closure GPU tex MiB | Heap proxy MiB | Main driver |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | M08 | 8.88x | 8.88x | 3.79x | 62.88 | 54.81 | GPU textures; 217 non-native tex = 53.33 MiB GPU + 26.67 MiB CPU-retained |
| 2 | M09 | 5.66x | 5.66x | 2.20x | 40.06 | 31.77 | GPU textures; 134 non-native tex = 33.05 MiB GPU + 16.54 MiB CPU-retained |
| 3 | M02 | 3.20x | 2.89x | 3.20x | 20.48 | 46.33 | heap proxy; 11 non-native tex = 1.10 MiB GPU + 0.55 MiB CPU-retained |
| 4 | M10 | 2.85x | 2.85x | 2.63x | 20.21 | 38.04 | GPU textures; 10 non-native tex = 1.55 MiB GPU + 0.78 MiB CPU-retained |
| 5 | M01 | 2.83x | 2.73x | 2.83x | 19.33 | 40.88 | heap proxy; 10 non-native tex = 0.82 MiB GPU + 0.53 MiB CPU-retained |
| 6 | M03 | 2.72x | 2.04x | 2.72x | 14.44 | 39.33 | heap proxy; 10 non-native tex = 0.82 MiB GPU + 0.47 MiB CPU-retained |
| 7 | M07 | 2.47x | 2.05x | 2.47x | 14.51 | 35.77 | heap proxy; 8 non-native tex = 0.59 MiB GPU + 0.31 MiB CPU-retained |
| 8 | M04 | 2.37x | 2.37x | 1.82x | 16.75 | 26.27 | GPU textures; 33 non-native tex = 7.03 MiB GPU + 3.57 MiB CPU-retained |
| 9 | M05 | 1.92x | 1.65x | 1.92x | 11.65 | 27.77 | heap proxy; 5 non-native tex = 0.57 MiB GPU + 0.30 MiB CPU-retained |
| 10 | M06 | 1.35x | 1.31x | 1.35x | 9.29 | 19.53 | heap proxy; 5 non-native tex = 1.54 MiB GPU + 0.53 MiB CPU-retained |
| 11 | M11 | 1.35x | 1.35x | 1.20x | 9.53 | 17.38 | GPU textures; 1 non-native tex = 0.02 MiB GPU + 0.01 MiB CPU-retained |
| 12 | M00_Tutorial | 1.33x | 1.33x | 0.94x | 9.43 | 13.54 | GPU textures; 14 non-native tex = 1.83 MiB GPU + 0.98 MiB CPU-retained |
| 13 | M13 | 1.00x | 1.00x | 1.00x | 7.08 | 14.47 | GPU textures; 2 non-native tex = 0.04 MiB GPU + 0.02 MiB CPU-retained |

## Findings (computed from the tables below)

- M13 baseline: closure GPU textures 7.08 MiB (178 resolved names), heap proxy 14.47 MiB. M00 sits at 1.33x.
- Risk bands (score >= 5.0x high, >= 2.0x medium, else low): high M08, M09; medium M02, M10, M01, M03, M07, M04; low M05, M06, M11, M00_Tutorial.
- M08: 217 non-native (TGA) closure textures = 53.33 MiB GPU RGBA8888 (level 0 only) + 26.67 MiB retained CPU copies; closure GPU total 62.88 MiB vs the 48 MiB prepare budget. The DXT share is only 9.55 MiB.
- M09: 134 non-native (TGA) closure textures = 33.05 MiB GPU RGBA8888 (level 0 only) + 16.54 MiB retained CPU copies; closure GPU total 40.06 MiB vs the 48 MiB prepare budget. The DXT share is only 7.01 MiB.
- The M08/M09 TGAs are 256x256 16-bit images expanded to 4 bytes per pixel on upload; a 16-bit
  GL upload format or skipping the retained surface copy would roughly halve GPU or heap cost
  (candidate mitigations only; not evaluated and not applied).
- Medium-band missions are driven by `.lsd/.ldd` bytes and W3D closure size (largest: M02 and M01),
  not textures; their closure textures are DXT-native and only 14.44-20.48 MiB.
- Context pool sizes: a Vita3K dev148 log (128 MiB heap, not physical) reported vitaGL RAM 112 MiB,
  VRAM 110 MiB, phycont 26 MiB. Physical pool sizes with the current 192 MiB heap have not been
  measured here; the closure GPU numbers above should be compared to a physical
  `texture_bytes_resident` for M13 before treating any absolute threshold as safe.

## Per-mission archive inventory

| Mission | MIX MiB | Entries | .dds n / MiB | .tga n / MiB | .w3d n / MiB | .wav n / MiB | .lsd MiB | .ldd MiB | .txt n / KiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M00_Tutorial | 5.53 | 84 | 44 / 1.84 | 0 / 0.00 | 31 / 2.99 | 0 / 0.00 | 0.50 | 0.14 | 0 / 0.0 |
| M01 | 18.74 | 231 | 95 / 3.74 | 0 / 0.00 | 103 / 9.32 | 0 / 0.00 | 4.64 | 0.93 | 18 / 48.9 |
| M02 | 31.27 | 316 | 184 / 7.57 | 0 / 0.00 | 70 / 14.29 | 0 / 0.00 | 6.87 | 1.65 | 54 / 171.7 |
| M03 | 23.68 | 318 | 116 / 4.70 | 3 / 0.15 | 129 / 8.63 | 53 / 6.33 | 3.05 | 0.76 | 12 / 14.0 |
| M04 | 18.96 | 192 | 73 / 2.13 | 26 / 3.13 | 68 / 11.02 | 0 / 0.00 | 1.73 | 0.79 | 1 / 4.5 |
| M05 | 18.56 | 143 | 92 / 3.74 | 0 / 0.00 | 41 / 11.22 | 0 / 0.00 | 2.62 | 0.91 | 5 / 14.5 |
| M06 | 14.24 | 322 | 90 / 2.53 | 1 / 0.25 | 215 / 9.25 | 9 / 0.06 | 0.91 | 1.18 | 2 / 14.1 |
| M07 | 23.24 | 188 | 119 / 5.12 | 0 / 0.00 | 8 / 9.94 | 56 / 4.52 | 2.67 | 0.93 | 0 / 0.0 |
| M08 | 45.10 | 286 | 16 / 0.49 | 209 / 26.13 | 41 / 12.72 | 0 / 0.00 | 4.17 | 1.38 | 10 / 23.4 |
| M09 | 28.95 | 185 | 4 / 0.17 | 130 / 16.26 | 32 / 6.85 | 0 / 0.00 | 1.87 | 0.69 | 9 / 16.2 |
| M10 | 16.35 | 149 | 118 / 4.90 | 1 / 0.13 | 24 / 6.00 | 0 / 0.00 | 4.13 | 1.10 | 0 / 0.0 |
| M11 | 13.64 | 138 | 85 / 3.29 | 0 / 0.00 | 41 / 7.68 | 0 / 0.00 | 1.72 | 0.83 | 8 / 19.2 |
| M13 | 12.58 | 137 | 48 / 1.87 | 0 / 0.00 | 62 / 5.01 | 0 / 0.00 | 0.85 | 0.27 | 22 / 78.6 |

Shared archives (always present, mounted for every level):

| Archive | MiB | Entries | .dds n / MiB | .tga n / MiB | .w3d n / MiB | .wav n / MiB | .mp3 n / MiB |
|---|---:|---:|---:|---:|---:|---:|---:|
| always.dat | 551.74 | 15161 | 1563 / 56.64 | 49 / 3.93 | 3069 / 73.60 | 10100 / 318.62 | 47 / 91.97 |
| Always2.dat | 13.65 | 181 | 146 / 5.93 | 6 / 0.08 | 21 / 7.41 | 0 / 0.00 | 0 / 0.00 |
| always3.dat | 12.75 | 38 | 4 / 0.04 | 0 / 0.00 | 7 / 0.09 | 23 / 12.60 | 0 / 0.00 |

## Mission-local textures (everything stored in the mission MIX)

| Mission | Textures | Native DXT n | Native GPU MiB | Non-native n | Non-native GPU MiB | Non-native CPU-retained MiB | Largest dims (w x h, fmt) |
|---|---:|---:|---:|---:|---:|---:|---|
| M00_Tutorial | 44 | 44 | 1.83 | 0 | 0.00 | 0.00 | 256x256 DXT1 |
| M01 | 95 | 95 | 3.72 | 0 | 0.00 | 0.00 | 512x512 DXT1 |
| M02 | 184 | 184 | 7.55 | 0 | 0.00 | 0.00 | 256x256 DXT1 |
| M03 | 119 | 116 | 4.68 | 3 | 1.85 | 1.84 | 800x600 TGA32rle |
| M04 | 99 | 73 | 2.12 | 26 | 6.25 | 3.13 | 512x512 DXT5 |
| M05 | 92 | 92 | 3.72 | 0 | 0.00 | 0.00 | 256x256 DXT1 |
| M06 | 91 | 90 | 2.52 | 1 | 1.00 | 0.25 | 512x512 TGA8 |
| M07 | 119 | 119 | 5.10 | 0 | 0.00 | 0.00 | 512x512 DXT1 |
| M08 | 225 | 16 | 0.49 | 209 | 52.25 | 26.12 | 256x256 TGA16 |
| M09 | 134 | 4 | 0.17 | 130 | 32.50 | 16.25 | 256x256 TGA16 |
| M10 | 119 | 118 | 4.88 | 1 | 0.25 | 0.12 | 512x512 DXT1 |
| M11 | 85 | 85 | 3.28 | 0 | 0.00 | 0.00 | 512x512 DXT1 |
| M13 | 48 | 48 | 1.86 | 0 | 0.00 | 0.00 | 256x256 DXT1 |

## Dependency-closure texture residency (resident-set estimate)

| Mission | .dep names | W3D closure n | W3D local MiB | W3D shared MiB | Unresolved W3D | Textures resolved | Unresolved tex names | Native DXT GPU MiB | Non-native GPU MiB | Non-native CPU MiB | Total GPU MiB | Of which local-MIX MiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M00_Tutorial | 280 | 249 | 2.99 | 8.93 | 7 | 245 | 0 | 7.61 | 1.83 | 0.98 | 9.43 | 1.83 |
| M01 | 1016 | 915 | 9.32 | 25.46 | 14 | 547 | 1 | 18.51 | 0.82 | 0.53 | 19.33 | 3.72 |
| M02 | 640 | 592 | 14.29 | 22.97 | 10 | 571 | 0 | 19.38 | 1.10 | 0.55 | 20.48 | 7.53 |
| M03 | 639 | 573 | 8.63 | 16.63 | 7 | 411 | 1 | 13.62 | 0.82 | 0.47 | 14.44 | 4.58 |
| M04 | 657 | 554 | 11.02 | 9.16 | 22 | 354 | 1 | 9.73 | 7.03 | 3.57 | 16.75 | 8.37 |
| M05 | 480 | 424 | 11.22 | 12.71 | 4 | 288 | 0 | 11.08 | 0.57 | 0.30 | 11.65 | 3.72 |
| M06 | 507 | 495 | 9.25 | 7.56 | 7 | 269 | 0 | 7.75 | 1.54 | 0.53 | 9.29 | 3.51 |
| M07 | 394 | 357 | 9.94 | 12.89 | 5 | 386 | 0 | 13.92 | 0.59 | 0.31 | 14.51 | 5.10 |
| M08 | 394 | 373 | 12.72 | 9.87 | 9 | 523 | 0 | 9.55 | 53.33 | 26.67 | 62.88 | 52.74 |
| M09 | 207 | 205 | 6.69 | 5.98 | 6 | 359 | 0 | 7.01 | 33.05 | 16.54 | 40.06 | 32.67 |
| M10 | 619 | 558 | 6.00 | 26.03 | 11 | 577 | 0 | 18.66 | 1.55 | 0.78 | 20.21 | 5.13 |
| M11 | 350 | 320 | 7.68 | 7.14 | 2 | 276 | 0 | 9.52 | 0.02 | 0.01 | 9.53 | 3.28 |
| M13 | 315 | 285 | 5.01 | 8.32 | 3 | 178 | 0 | 7.04 | 0.04 | 0.02 | 7.08 | 1.85 |

Total GPU above the 48 MiB prepare budget means the loader defers textures (lazy upload on
first draw); deferred textures still allocate GPU memory when first drawn, so the budget
only moves the cost into gameplay frames.

## Largest closure textures per mission (top 5 by GPU bytes)

- **M00_Tutorial**: e_master01.dds 512x512 DXT5 0.33 MiB; agd_pct_master.tga 256x256 TGA16 0.25 MiB (+CPU); bar_pct_master.tga 256x256 TGA16 0.25 MiB (+CPU); mct_con-ref-hnd.tga 256x256 TGA16 0.25 MiB (+CPU); mct_pwr-com-obl.tga 256x256 TGA16 0.25 MiB (+CPU)
- **M01**: c_nod_chemt.dds 512x512 DXT5 0.33 MiB; e_master01.dds 512x512 DXT5 0.33 MiB; bump_water.tga 256x256 TGA24 0.25 MiB (+CPU); mct_con-ref-hnd.tga 256x256 TGA16 0.25 MiB (+CPU); gdflor-gdi.tga 223x256 TGA24 0.22 MiB (+CPU)
- **M02**: c_nod_chemt.dds 512x512 DXT5 0.33 MiB; e_master01.dds 512x512 DXT5 0.33 MiB; atr_pct_master.tga 256x256 TGA16 0.25 MiB (+CPU); mct_con-ref-hnd.tga 256x256 TGA16 0.25 MiB (+CPU); mct_pwr-com-obl.tga 256x256 TGA16 0.25 MiB (+CPU)
- **M03**: c_nod_chemt.dds 512x512 DXT5 0.33 MiB; e_master01.dds 512x512 DXT5 0.33 MiB; bump_water.tga 256x256 TGA24 0.25 MiB (+CPU); mct_con-ref-hnd.tga 256x256 TGA16 0.25 MiB (+CPU); ref_pct_master.tga 256x256 TGA16 0.25 MiB (+CPU)
- **M04**: e_master01.dds 512x512 DXT5 0.33 MiB; water_caustic_grid1.dds 512x512 DXT5 0.33 MiB; bump_water.tga 256x256 TGA24 0.25 MiB (+CPU); l4_sr_b_lm04+\0.tga 256x256 TGA16 0.25 MiB (+CPU); l4_sr_b_lm04+\1.tga 256x256 TGA16 0.25 MiB (+CPU)
- **M05**: e_master01.dds 512x512 DXT5 0.33 MiB; mct_con-ref-hnd.tga 256x256 TGA16 0.25 MiB (+CPU); mct_wep-atr.tga 256x256 TGA16 0.25 MiB (+CPU); 01_gdi a-10.dds 512x512 DXT1 0.17 MiB; 01_orca.dds 512x512 DXT1 0.17 MiB
- **M06**: rshaw_statue.tga 512x512 TGA8 1.00 MiB (+CPU); c_nod_chemt.dds 512x512 DXT5 0.33 MiB; e_master01.dds 512x512 DXT5 0.33 MiB; mct_con-ref-hnd.tga 256x256 TGA16 0.25 MiB (+CPU); mct_wep-atr.tga 256x256 TGA16 0.25 MiB (+CPU)
- **M07**: c_nod_chemt.dds 512x512 DXT5 0.33 MiB; e_master01.dds 512x512 DXT5 0.33 MiB; mct_con-ref-hnd.tga 256x256 TGA16 0.25 MiB (+CPU); mct_pwr-com-obl.tga 256x256 TGA16 0.25 MiB (+CPU); c_flametroop.dds 512x512 DXT1 0.17 MiB
- **M08**: c_nod_chemt.dds 512x512 DXT5 0.33 MiB; e_master01.dds 512x512 DXT5 0.33 MiB; l08_cave_lm+\0.tga 256x256 TGA16 0.25 MiB (+CPU); l08_cave_lm+\1.tga 256x256 TGA16 0.25 MiB (+CPU); l08_cave_lm+\10.tga 256x256 TGA16 0.25 MiB (+CPU)
- **M09**: e_master01.dds 512x512 DXT5 0.33 MiB; l09_cave_lm01+\0.tga 256x256 TGA16 0.25 MiB (+CPU); l09_cave_lm01+\1.tga 256x256 TGA16 0.25 MiB (+CPU); l09_cave_lm01+\10.tga 256x256 TGA16 0.25 MiB (+CPU); l09_cave_lm01+\11.tga 256x256 TGA16 0.25 MiB (+CPU)
- **M10**: c_nod_chemt.dds 512x512 DXT5 0.33 MiB; e_master01.dds 512x512 DXT5 0.33 MiB; atr_pct_master.tga 256x256 TGA16 0.25 MiB (+CPU); con_pct_master.tga 256x256 TGA16 0.25 MiB (+CPU); mct_con-ref-hnd.tga 256x256 TGA16 0.25 MiB (+CPU)
- **M11**: c_nod_chemt.dds 512x512 DXT5 0.33 MiB; e_master01.dds 512x512 DXT5 0.33 MiB; 19_ravebod.dds 512x512 DXT1 0.17 MiB; c_flametroop.dds 512x512 DXT1 0.17 MiB; c_nod_mg.dds 512x512 DXT1 0.17 MiB
- **M13**: e_master01.dds 512x512 DXT5 0.33 MiB; c_havoc.dds 512x512 DXT1 0.17 MiB; c_nod_mg.dds 512x512 DXT1 0.17 MiB; havoc_desert.dds 512x512 DXT1 0.17 MiB; havoc_nightops.dds 512x512 DXT1 0.17 MiB

## Audio

| Mission | Local WAV n | Local WAV MiB (file) | Local WAV decoded PCM16 MiB | Local MP3 MiB | Level-referenced shared WAV n | Shared WAV file MiB | Shared WAV PCM16 MiB | Largest referenced WAV PCM MiB | Referenced MP3 n / MiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| M00_Tutorial | 0 | 0.00 | 0.00 | 0.00 | 2 | 0.51 | 0.54 | 0.48 | 0 / 0.00 |
| M01 | 0 | 0.00 | 0.00 | 0.00 | 50 | 4.98 | 8.28 | 0.56 | 0 / 0.00 |
| M02 | 0 | 0.00 | 0.00 | 0.00 | 32 | 2.71 | 4.25 | 0.34 | 0 / 0.00 |
| M03 | 53 | 6.33 | 9.79 | 0.00 | 64 | 5.22 | 9.86 | 0.56 | 1 / 2.95 |
| M04 | 0 | 0.00 | 0.00 | 0.00 | 22 | 1.32 | 3.26 | 0.45 | 1 / 3.63 |
| M05 | 0 | 0.00 | 0.00 | 0.00 | 23 | 2.39 | 5.50 | 0.50 | 1 / 3.63 |
| M06 | 9 | 0.06 | 0.12 | 0.00 | 18 | 2.53 | 3.08 | 0.50 | 1 / 3.56 |
| M07 | 56 | 4.52 | 9.03 | 0.00 | 15 | 1.42 | 3.92 | 0.50 | 1 / 2.16 |
| M08 | 0 | 0.00 | 0.00 | 0.00 | 13 | 1.37 | 2.03 | 0.38 | 1 / 2.16 |
| M09 | 0 | 0.00 | 0.00 | 0.00 | 25 | 2.00 | 3.49 | 0.41 | 1 / 3.47 |
| M10 | 0 | 0.00 | 0.00 | 0.00 | 41 | 3.24 | 5.91 | 0.35 | 1 / 2.65 |
| M11 | 0 | 0.00 | 0.00 | 0.00 | 38 | 4.23 | 6.86 | 0.51 | 1 / 2.73 |
| M13 | 0 | 0.00 | 0.00 | 0.00 | 4 | 0.53 | 0.93 | 0.27 | 1 / 2.73 |

Per `reports/AUDIO_STREAM_MEMORY.md`, WAV streams currently decode fully to PCM16 on open
(sources over 1 MiB bypass the 4 MiB PCM cache), so concurrent-stream peak is the practical
audio risk, not the per-level file totals above.
