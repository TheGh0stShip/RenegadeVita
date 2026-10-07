# Session-chain accumulation audit (M13 → M01…M11 in one process)

Evidence class: host source review of the Vita session loop plus
`arm-vita-eabi-g++ -fsyntax-only` of the changed files. Nothing was built,
installed or run on Vita3K or physical Vita. Every growth figure is a
source-derived estimate, not a measurement.

## Session model (why most state cannot accumulate)

`a30_main.cpp` calls `A31_Vita_Run_Interactive_Runtime()` once per session:
for the menu, for each campaign level, and for each Score/Movie intermission
that hands off to the next level. Each call constructs, and tears down before
it returns:

- the root and Data factories, the `Always2.dat`, `always.dbs`, `Always.dat`
  and `M00_Tutorial.mix` `MixFileFactoryClass` objects, and `FileFactoryListClass`
  (all on the stack)
- the selected mission MIX and the glacier texture supplement (`unique_ptr`)
- `WWAudioClass` (on the stack)
- `WW3DAssetManager` (`new`, then `Delete_This`)
- WW3D, WWPhys, WWSaveLoad, WWMath and PathMgr (Init/Shutdown)
- StyleMgr, TranslateDB, Input, Campaign/Encyclopedia, Combat, the
  GameInitMgr SP transport, cNetwork, the player/team/game-data one-time
  owners, and every registered GameMode

The teardown checks `strong_session_cleanup`: no asset manager, no WW3D, no
scene, star, camera, player or game object, and no Combat mode. So the only
state that can cross a session boundary is (a) process-lifetime statics in
port code, (b) original-code statics that the per-session Shutdown calls do
not clear, and (c) vitaGL itself, which is initialized once and never shut
down (`RenegadeVitaRenderer::Initialize` re-activates a logical session).

## Accumulation table

Growth is per campaign mission (one level session plus its Score and Movie
sessions). "High-water" means the allocation does not grow with each mission
but keeps the largest size seen so far for the rest of the process.

| Resource | Owner | Reset point | Growth per mission | Risk |
|---|---|---|---|---|
| Retail MIX factories (always.dat index 15,161 × 12 B, Always2, dbs, M00) | a31 runtime (stack) | Function exit, each session | 0. Rebuilt every session | None (memory). Time: each handoff re-indexes always.dat and rewrites the M00 index cache (startup precache phase) |
| Mission MIX + glacier supplement factory | a31 runtime `unique_ptr` | Function exit; `factory_list` is destroyed first | 0 | None |
| Original temporary MIX factory (`SaveGameManager::Peek_Description`) | savegame.cpp | Removed and deleted in the same call | 0 | None |
| Directory-listing case cache | renegade_paths.cpp | Process lifetime | 0 after first use. Capped at 128 listings | Low (KiB) |
| Known-available retail path cache | renegade_file_factory.cpp | Process lifetime | 0 after first use. Capped at 256 paths | Low (KiB) |
| Registry / options / ranks / movie unlocks | port filesystem | Fixed arrays; `Configure` sets count = 0 | 0 | None |
| W3D prototypes, HTrees, HAnims, font chars, texture hash | `WW3DAssetManager` | `Delete_This` + `WW3D::Shutdown → Free_Assets`, each session | 0 | None |
| vitaGL texture objects + retained CPU surfaces + lazy DDS/TGA names | `IDirect3DBaseTexture8::Release` | Last TextureClass ref (asset-manager teardown) | 0 | None found. `texture_bytes_resident` is reset mid-session (`Reset_Statistics`), so it cannot prove this. Use the new residual line |
| Static mesh cache (24 MiB cap, GL buffers) | ww3d_vita_renderer.cpp | `Invalidate_Static_Mesh_Cache` + `Release_Static_Mesh_Builder` at renderer Shutdown | 0 | None |
| Material-colour, deformed-skin and static-mesh-builder scratch | ww3d_vita_renderer.cpp | Renderer Shutdown | 0 | None |
| **DX8 surface→RGBA upload scratch** (`thread_local` vector) | ww3d_dx8_boundary.cpp | **Was never reset.** Now `RenegadeVita_Release_DX8_Scratch` at renderer Shutdown | Was high-water: the largest surface level uploaded through `Upload_Texture_Level_From_Surface` (HUD/text/TGA surfaces). That is 256 KiB for a 256² level and 1.83 MiB for M03's 800×600 TGA32 at native size; more if the level was resized to a power of two. M03's size carried into M04–M11, including M08 | **Fixed.** Medium for M08/M09 heap headroom |
| **Triangle-strip expansion index scratch** | ww3d_dx8_boundary.cpp | Was never reset. Now released by the same call | High-water: largest strip × 6 B (tens to hundreds of KiB) | **Fixed.** Low |
| Native material-pass queues (hold mesh/pass refs) | ww3d_dx8_boundary.cpp | Drained every frame | 0 | None |
| CPU surface stores (64 slots) | surface_boundary.cpp | `~SurfaceClass` | 0 | None |
| FreeType library, faces and retail TTF bytes | renegade_freetype_font_provider.cpp | `RenegadeVita_Font_Shutdown` from `WW3D::Shutdown` | 0. TTFs are re-read each session | None |
| **Movie decoder buffers** (320×240 RGBA 300 KiB, 2 s stereo ring 375 KiB, resample buffer, packet deque) | a4_binkmovie_boundary.cpp | `Release_Decoder_State` at movie end, skip or Stop. It used `clear()`, which kept capacity | Was about 0.66 MiB, kept from the first movie through every later mission (high-water, not cumulative). FFmpeg contexts, the GL texture and the audio thread/port were already freed | **Fixed** (capacity released) |
| Miles PCM cache (4 MiB budget, 128 slots) + sample objects | renegade_miles_provider.cpp | `AIL_shutdown` from `~WWAudioClass`, each session | 0. The sample pointer-array capacity stays (bytes) | None |
| Miles output thread / audio port, WWAudio delayed-release thread | Miles provider / WWAudio Threads.cpp | Joined and released each session | 0 | None |
| WWAudio sound cache, 2D/3D handles, sound scene | `WWAudioClass` (stack) | Destructor each session (plus `Flush_Cache` at `Unload_Level`) | 0 | None |
| Startup status repaint thread | a31 runtime | Created and deleted each session | 0 | None |
| Power callback + callback thread | a31 runtime | Once per process (guarded) | 0 | None |
| Flight-recorder flush worker + snapshot | a35_campaign_flight_recorder.cpp | Once per process (`gFlushWorkerAttempted`); state reset each session | 0 | None |
| Async log writer thread + 256 KiB ring | renegade_async_log.h | Process lifetime, fixed size | 0 | None (memory) |
| Runtime log file byte cap (4 MiB + 256 KiB priority reserve) | renegade_async_log.h | **Per process.** `session_bytes_` is never reset | Not memory. After about 4 MiB of log, only priority lines are written | **Diagnostic risk.** Later missions in a long campaign lose non-priority evidence. The new residual line uses `[LIFECYCLE]`, so it survives the cap |
| Prepared render objects (128 slots) | a31 runtime | `A35_Vita_Clear_Prepared_Render_Objs` at unload and session end | 0 | None |
| Cinematic-warm second MIX index and `.txt` buffers | `Warm_Level_Cinematic_Preset_Models` | Function exit (the warmed models belong to the asset manager) | 0 | None |
| Frame history and capture pixels | a31 runtime | `delete` / `free` each session | 0 | None |
| Definitions (`Objects.ddb`, level `.ddb`) | DefinitionMgrClass | `Free_Definitions` at each load, and in `WWSaveLoad::Shutdown` | 0 | None |
| Strings DB | TranslateDBClass | `Shutdown` each session; `Load` frees before reloading | 0 | None |
| Global and level conversations | ConversationMgrClass | `CombatManager::Shutdown` | 0 | None |
| Physics scene, pathfind sectors/portals, HeightDB | `CombatManager::GameScene` | `Release_Ref` in `CombatManager::Shutdown` → `~PathfindClass` → `HeightDBClass::Shutdown` | 0 | None |
| Armor/Bones/SurfaceEffects/Dazzle/Script re-init in `Start_Game` (`_reload_game_configuration_files`) | Combat / ww3d2 | Each Init shuts down or replaces in place; Combat/WW3D shutdowns at session end | 0 | None |
| `cNicEnum` (`Init` every session) | nicenum.cpp | Fixed static arrays; `WSAStartup` is a no-op on Vita | 0 | None |
| GameModeManager entries (stack modes) | a31 runtime | Removed at teardown (`Find("Combat") == NULL` is checked) | 0 | None |
| `SaveLoadSystemClass` PointerRemapper tables (pair 8 B, request 4 B) | wwsaveload (original static) | `Reset()` uses `Delete_All`, which keeps capacity (growth step 4096) | High-water of the largest `.lsd`/`.ldd` load's pointer count. Estimated 0.3–2 MiB after M02/M01, kept through M08. Not measured | Low–medium. Not fixed: needs an upstream patch (free the tables in `WWSaveLoad::Shutdown`) |
| `AssetStatusClass` report hashes (missing + load-on-demand names) | ww3d2 original singleton | Never reset. Reporting is enabled by `Vita_Finalize_Loaded_Level` and disabled by `Unload_Level`. Missing-asset entries are always added | Only new distinct names (deduplicated). Bounded by the asset-name universe (≤ about 0.5 MiB estimated). Read only under `WWDEBUG`, which the Vita build does not define, so this is dead data | Low. Not fixed (needs an upstream patch) |
| Pool allocators (`AutoPoolClass`: multilist nodes, packets) | wwlib original | Never returned to heap | High-water of the most concurrent nodes (largest level) | Low. Not quantified |
| vitaGL FFP shader/program caches, GXM pools | vitaGL (process lifetime) | No shutdown API | Only new state combinations | Low. Fixed pools |

No per-mission linear growth was found in port code or in the original code
driven by the Vita loop. The defects were high-water retentions that let one
mission's peak buffer survive into every later mission. Three are fixed below.

## Changes in this unit

1. `port/platform/a4_binkmovie_boundary.cpp`: `Release_Decoder_State` now swaps
   the video upload buffer, audio ring, resample buffer and prefetch deque with
   empty containers instead of `clear()`. The audio thread is joined first,
   and `Reset_Audio_Ring` and the conversion path reallocate on the next movie,
   so playback is unchanged. Freed: about 0.66 MiB per gameplay mission.
2. `port/renderer/vita/ww3d_dx8_boundary.cpp`, `d3d8.h`,
   `ww3d_vita_renderer.cpp`: the RGBA upload scratch and the strip-expansion
   index scratch move from function-local statics to namespace scope. The new
   `RenegadeVita_Release_DX8_Scratch()` releases them, and renderer `Shutdown()`
   calls it next to the existing bound-texture release (weak under the host
   lifecycle self-test, as before). Per-frame reuse inside a session is
   unchanged; only the next session's first upload re-grows the buffer.
3. `port/platform/vita/a31_vita_runtime.cpp`: after the full teardown, each
   session logs one line:
   `[LIFECYCLE] SESSION residual index=N frames=F heap arena/in_use/free/free_chunks=… vitagl=1 ram/vram/all_free=… user_free=…`.
   This is the measurement this audit could not take. Across a campaign run,
   `in_use` and `all_free` should be flat between consecutive sessions. A
   steady rise is retained state, and a rising `free_chunks` with flat
   `in_use` is fragmentation.

Validation: `-fsyntax-only` with the Vita toolchain passes for all four
changed translation units. The stale compdb needed
`-DRENEGADE_VITA_CAMPAIGN_MSAA_SAMPLES=2`, a newer CMake define. The related
Python contract tests pass except 14 that fail identically at HEAD without
these changes: missing `build/deps` archives, stale source-anchor
assertions, and the input-binding/async-log/requested-owner/script-lookup
tests.

## Open (needs Vita3K or physical evidence)

- Run M13 → M01 → M02 (at least three handoffs) and compare the
  `SESSION residual` lines. M08 is the decisive point for heap and GPU
  headroom.
- If the residual shows growth of 1 MiB or more per handoff, the next
  candidates in order are: PointerRemapper capacity (upstream patch to
  `WWSaveLoad::Shutdown`), `AssetStatusClass` tables, then AutoPool high-water.
- The log byte cap is per process. A full 12-mission run will truncate
  non-priority evidence after about 4 MiB. Raise the cap or reset it per
  session (a policy decision) before relying on late-mission logs.
- Each handoff re-indexes always.dat and rewrites the M00 index cache. This
  costs time and ux0 writes, not memory. It is not measured.
