# Level load memory trace (.lsd/.ldd, M02 focus)

Status: static source trace plus read-only chunk-size metadata from the unchanged retail
`M02.mix`/`M13.mix`. These are host estimates, not Vita measurements. No build was run, no code
was changed, and nothing was deployed. Inputs: `reports/campaign/MISSION_MEMORY_ESTIMATES.md`,
`staging/` (the patched upstream copies), `port/`.

## Verdict

- **The port adds no whole-file copy of `.lsd` or `.ldd`.** Both files stream through the
  original `ChunkLoadClass`, which reads through `BufferedFileClass` (16 KiB read-ahead) and then
  `RawFileClass`. `RawFileClass` is biased into the open mission MIX.
- **Level-load file buffers do not leak after the level starts.** Every file object is deleted
  in `RenegadeRootedFileFactoryClass::Return_File`. Read-ahead buffers are freed by
  `Reset_Buffer` on close or destruction.
- **No reduction was applied.** The `.lsd`/`.ldd` path has nothing material to stream. The
  remaining candidates below are either tiny or affect runtime behaviour. Under the no-build
  rule, none of them is clearly safe.
- Peak heap during an M02 load comes from decoded objects: W3D prototypes, pathfind, and static
  scene data. File I/O buffers are a small share.

## Load path on Vita (as executed)

1. `a31_vita_runtime.cpp` (about line 5156) creates
   `new MixFileFactoryClass("Data\\M02.mix", &root_factory)`. This reads the header and the
   12-byte `FileInfo` index (316 entries, about 3.7 KiB). It sorts the index only when the
   archive is unsorted (TT patch) and adds the factory to the `FileFactoryListClass`.
2. Level preparation (`Warm_Level_Cinematic_Preset_Models`, about line 3605) builds a second,
   temporary `MixFileFactoryClass` on the same archive and its filename list (316 `StringClass`).
   It reads each `.txt` cinematic script whole into a `std::string`, capped at 1 MiB. For M02
   that is 54 files and 171.7 KiB in total, read one at a time. Everything here is freed at
   function exit. The models it warms stay as asset-manager prototypes, by design.
3. `AssetDependencyManager::Load_Level_Assets("M02.mix")` runs the original `.dep` list.
   `WW3DAssetManager::Load_3D_Assets(name)` then opens each W3D (`Get_File` → biased
   `RenegadeRootedFileClass`) and decodes it with `ChunkLoadClass`, which is streamed.
4. `CombatManager::Load_Level_Threaded(source, false)` calls `LoadThreadClass::Thread_Function()`
   synchronously on the vitaGL thread (Vita boundary in `staging/combat/combat.cpp`), so there
   is no second loader stack. The sequence is: `Free_Definitions` → `Load_Definitions("Objects.ddb")`
   (streamed) → `Pre_Load_Game` → `SaveGameManager::Load_Game("M02.ldd")`.
5. `Load_Game` opens `M02.ldd` and runs `ChunkLoadClass` on it. `CHUNKID_LEVEL_INFO` triggers
   `Load_Definitions("M02.ddb")`, which is optional and not present in `M02.mix`. It then calls `Load_Level()` →
   `Load_Save_Load_System("M02.lsd")`, which opens a second streamed file while `.ldd` is still
   open. Next, `CHUNKID_LEVEL_DATA` runs `SaveLoadSystemClass::Load(cload)` over the rest of the
   `.ldd`. Both files are closed and returned.
6. MIX member reads: `MixFileFactoryClass::Get_File` does a binary search on CRC, then calls
   `Factory->Get_File(MixFilename)` and `Bias(offset, size)`. There is no member extraction or
   copy.

### Per-open file cost (port boundary)

| Item | Bytes | Lifetime |
|---|---:|---|
| `BufferedFileClass` read-ahead (`_DesiredBufferSize`) | 16,384 | First small read until Close/destructor |
| `RenegadeRootedFileClass` object: `LogicalName[768]`, `RenegadeResolvedPath` (about 1.9 KiB), `AtomicTarget[1024]`, `AtomicTemporary[1024]` | about 4,800 | `Get_File` to `Return_File` |
| `StagedData` | 0 on reads | Write-only staging |

At most 3–4 files are open at once during the level load: `.ldd`, `.lsd`, a W3D opened on
demand by static-object creation, and a DDS or TGA. That is about **85 KiB** of I/O state.

Behaviour to note (upstream, not a leak): `BufferedFileClass::Seek` frees the 16 KiB buffer on
any absolute or backward seek. That makes allocation churn on `ChunkLoadClass::Peek_Next_Chunk`,
which only `conversationmgr.cpp` uses, and on archive index walks. `Tell()` is
`Seek(0, SEEK_CUR)` and keeps the buffer.

## M02 serialized level data (retail chunk metadata)

| File / chunk | Owner | M02 MiB | M13 MiB |
|---|---|---:|---:|
| `.lsd` total | | 6.87 | 0.85 |
| 0x00020000 / 0x04433221 `PSDSSC_CHUNKID_PATHFIND` | `PathfindClass::Load` (sectors, portals, `HeightDBClass`) | 3.50 | 0.57 |
| 0x00020000 / 0x04433220 `PSDSSC_CHUNKID_SCENE` | Static culling/VIS/light scene data | 2.19 | 0.17 |
| 0x00020001 / 0x06090609 `PSOSSC_CHUNKID_SCENE` | Static physics objects (create W3D render objects) | 1.07 | 0.10 |
| 0x00030005 / 0x10291220 | Static audio scene | 0.11 | 0.00 |
| `.ldd` total | | 1.65 | 0.27 |
| 0x3C51C461 / 0x00040000 `CHUNKID_COMBAT_BEGIN` | Combat dynamic objects | 1.42 | 0.11 |
| 0x3C51C461 / 0x00020050 | Physics dynamic data | 0.20 | n/a |

M02 pathfind alone is 6.1x M13, and its static scene data is 13x M13. Pathfind decodes into many
small heap objects: one `new` per sector and per portal. Newlib per-allocation overhead therefore
makes the in-memory size likely **at or above** the serialized 3.5 MiB. This is not measured.

## Estimated peak heap during M02 load (newlib 192 MiB heap, relative)

| Term | Estimate | Basis |
|---|---:|---|
| File I/O state (buffers + file objects) | about 0.1 MiB | Above |
| Largest whole-DDS transient (`DDSFileClass::Load`, upstream) | ≤ 0.33 MiB | Largest M02 DDS |
| MIX indexes (always.dat 15,161 entries plus others) | about 0.2 MiB | 12 B/entry |
| Cinematic-warm transient (second index + one `.txt` + lines) | < 0.1 MiB | Above |
| `.lsd` decoded (pathfind + static scene + static objects) | 6.9–14 MiB | 1.0–2.0x serialized; not measured |
| `.ldd` decoded (combat/physics dynamic) | 1.7–3.4 MiB | 1.0–2.0x |
| W3D closure prototypes (local 14.29 + shared 22.97 MiB) | about 37 MiB at 1.0x | `MISSION_MEMORY_ESTIMATES.md` |
| DX8 FVF vertex/index buffers (Vita shim `IDirect3DVertexBuffer8::Storage`, CPU) | Part of the mesh share | Same as a PC managed-pool system copy |
| Retained non-native texture CPU surfaces | 0.55 MiB | Same report |
| **Level-attributable total** | **about 46–55 MiB** | Plus the engine/definition baseline (not estimated) |

Of this, about 0.8 MiB (I/O plus transients) is load-only and freed. Everything else is resident
game state that the original engine owns. vitaGL texture and static-mesh-cache memory (24 MiB
cap, filled on first draw) lives in vitaGL pools and is not counted here.

## Port-introduced copies and retentions (candidates, none applied)

| Candidate | Size | Retained after start? | Why not applied |
|---|---:|---|---|
| `Warm_Level_Cinematic_Preset_Models`: whole `.txt` into `std::string` plus per-line `substr` copies, and a duplicate M02 MIX index | < 0.1 MiB | No | Too small to matter. Line parsing needs the text. |
| `Upload_Texture_Level_From_Surface`: `static thread_local std::vector rgba` scratch | Largest RGBA surface level ever uploaded through it. If the TGA and decode paths route through it, that is M02 256x256 = 256 KiB, M06 512x512 = 1 MiB, M03 800x600 = 1.9 MiB (routing not traced) | **Yes**, high-water for the process lifetime | Deliberate: it avoids a heap round trip on every dynamic-surface (HUD text, video) re-upload. Releasing above a threshold would change per-frame allocation behaviour and needs measurement. |
| `RenegadeRootedFileClass` read objects carry about 2 KiB of write-only atomic path arrays | about 2 KiB per open file | No | Changing the struct layout touches the save/config atomic-write path. The gain is under 10 KiB at peak. |
| `LazyDDSSource` filename copy per fast-path DDS | about 20–40 B per texture (about 20 KiB for 571 textures) | Yes, intentionally | Needed for lazy CPU decode or reload |
| Prepared render-object slots (`g_A35PreparedRenderObjects[128]`) | M13/M01 only | Cleared on unload and session change | Not used for M02 |

No port-introduced temporary duplicate of `.lsd`, `.ldd`, W3D or MIX member data was found. The
only whole-file buffers on the load path are upstream: `DDSFileClass` (whole DDS, freed per
texture) and the TGA surface loader.

## What would actually move M02

These are measurement-first; none applies to the file path.

1. Measure `mallinfo()` around `Load_Level()` and around the `CHUNKID_LEVEL_DATA` load, and log
   the deltas for pathfind, static scene and static objects separately. That replaces the
   1.0–2.0x guesses.
2. Measure the W3D prototype heap delta across `Load_Level_Assets`. At about 37 MiB of file
   bytes, this is the largest term.
3. Fragmentation check: the load makes thousands of 16 KiB + 4.8 KiB allocate/free pairs next to
   long-lived pathfind and mesh objects. Log largest-free-block before and after load before
   treating "free bytes" as usable.
