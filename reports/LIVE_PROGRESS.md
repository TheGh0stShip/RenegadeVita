# Live engineering progress

## 2026-08-28 — dev62 WWAudio stream loop-count return

`[██████████] 12/12 canonical source/build gates complete`

- Audio boundary: staged original `SoundStreamHandleClass` now returns the
  provider value from `AIL_stream_loop_count(StreamHandle)` instead of
  discarding it and always reporting zero. The deterministic WWAudio runtime
  correctness patch carries the same fix so clean restaging preserves it.
- Runtime purpose: any original WWAudio or conversation-side caller that polls
  stream loop completion now sees the Miles-compatible provider state. This is
  a source-side correctness fix under original WWAudio ownership, not a custom
  conversation scheduler.
- Validation: focused dialogue/audio diagnostics passed 12/12, the Vita audio
  provider loop-count contract passed, the combined local provider/dialogue/
  staging contract set passed 16/16, and the fast no-deploy candidate passed
  55 focused tests, the original `DDSFileClass` `.tga`-to-`.dds` executable
  contract 11/11, ARM package identity/hash checks, and VPK packaging. The
  full canonical no-deploy build passed retained host-validation reuse, 72
  host unittest checks, deterministic restaging, source integration reporting,
  ARM link/package, compressed VPK validation, identity verification,
  diagnostics bundle generation, SHA manifest verification, and retail
  exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev62.vpk` SHA-256 is
  `f501288b7bb302923502fcf89e0b74c3f35a5aaa824f0eb68531b05cf05acddd`;
  ELF SHA-256 is
  `9d16c948e3212c705333fddb50fd42cc6eed7816d8af350cdd8312e062d03ef7`;
  diagnostics bundle SHA-256 is
  `f0eda4ec27dc3c292fed92d3fc415738c069548a94951f600e4c472eaff15f9b`.
- Boundary: dev62 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev62, verify
  Logan audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev62-runtime.log`, especially stream
  loop-count behavior, speech duration/dropoff/distance, stream bytes/frames/
  mix/last_stream fields, fact/estimate/untrimmed/trimmed values,
  conversation state, and texture/material provenance if dialogue remains
  silent or materials remain incorrect.

## 2026-08-28 — dev61 streamed-dialogue fact runtime telemetry

`[██████████] 12/12 canonical source/build gates complete`

- Audio boundary: dev61 preserves exact RIFF `fact` frame handling and now
  carries fact, estimated, untrimmed, and trimmed streamed-dialogue frame
  metadata into Miles runtime stats. The A3.5 audio log line now includes
  `frames/fact/estimate/untrimmed/trimmed/rate/vol/pan`.
- Runtime purpose: the next Logan hardware run can prove whether streamed
  dialogue used exact `fact` frames or estimated frames, and whether padded
  decode output was trimmed, while original `ActiveConversationClass`,
  `SoldierGameObj`, and WWAudio ownership remain unchanged.
- Validation: focused dialogue/audio diagnostics passed 12/12, and the broader
  local texture/audio/loading/indexed/skin contract set passed 39/39. The fast
  no-deploy candidate passed 54 focused tests, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, ARM package identity/hash
  checks, and the full canonical no-deploy build passed retained
  host-validation reuse, 71 host unittest checks, deterministic restaging,
  source integration reporting, ARM link/package, compressed VPK validation,
  identity verification, diagnostics bundle generation, SHA manifest
  verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev61.vpk` SHA-256 is
  `37c0bcf7d1ffdfff45787437fd2128915bc18d83a8b7c3ac23144704b9108d23`;
  ELF SHA-256 is
  `cfae7e566d9eccbee058f5b82df5ff03fbc8d13d2d386bf32fdfc90165a0442a`;
  diagnostics bundle SHA-256 is
  `cde3d3817cfb19cd5c99d655bccd9e2d577a97cdba9e71141f806d6fc0e1b017`.
- Boundary: dev61 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev61, verify
  Logan audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev61-runtime.log`, especially speech
  duration/dropoff/distance, stream bytes/frames/mix/last_stream fields, the
  new fact/estimate/untrimmed/trimmed values, conversation state, and
  texture/material provenance if dialogue remains silent or materials remain
  incorrect.

## 2026-08-28 — dev60 WAVE fact-duration metadata

`[██████████] 12/12 canonical source/build gates complete`

- Audio boundary: the Vita WAVE inspector now reads RIFF `fact` chunks and
  preserves the exact decoded sample-frame count as `fact_sample_frames`.
  Streamed-dialogue `sample_frames` prefers that exact metadata before falling
  back to bounded estimates, and decoded ADPCM output is trimmed to the exact
  frame count before playback. `AILSOUNDINFO.samples` still feeds the original
  WWAudio `SoundBufferClass::Determine_Stats` duration path.
- Runtime purpose: this tightens Logan conversation timing and trims padded
  ADPCM tails without moving ownership out of original
  `ActiveConversationClass`, `SoldierGameObj`, or WWAudio scheduling.
- Validation: focused dialogue/audio diagnostics passed 12/12, and the broader
  local texture/audio/loading/indexed/skin contract set passed 39/39. The fast
  no-deploy candidate passed 54 focused tests, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, ARM package identity/hash
  checks, and the full canonical no-deploy build passed retained
  host-validation reuse, 71 host unittest checks, deterministic restaging,
  source integration reporting, ARM link/package, compressed VPK validation,
  identity verification, diagnostics bundle generation, SHA manifest
  verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev60.vpk` SHA-256 is
  `98c32184861058c3168f511c8bef9fe9bb9db77055626d3a506ef217f556ad51`;
  ELF SHA-256 is
  `dd7b7b02c073dc3ba75583b3178a3d0ebc79f55f214e1d0170291689444c99be`;
  diagnostics bundle SHA-256 is
  `e57bb82db926688e87b88a65e58401b4696a8c4cf4a6727424b192096a8422fb`.
- Boundary: dev60 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev60, verify
  Logan audible dialogue and timing, dialog/message text, material/texture
  appearance, and route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev60-runtime.log`, especially speech
  duration/dropoff/distance, stream bytes/frames/mix/last_stream fields,
  conversation state, WAVE duration behavior, and texture/material provenance
  if dialogue remains silent or materials remain incorrect.

## 2026-08-28 — dev59 streamed-dialogue duration metadata

`[██████████] 12/12 canonical source/build gates complete`

- Audio boundary: the Vita Miles-compatible WAVE inspection path now reports
  decoded sample-frame counts through `AILSOUNDINFO.samples`. The staged
  original `SoundBufferClass::Determine_Stats` path computes streamed-dialogue
  duration from `samples / rate`, falling back to the old byte-length estimate
  only when frame metadata is unavailable.
- Runtime purpose: original `ActiveConversationClass` and `SoldierGameObj`
  conversation scheduling use `speech->Get_Duration()`. For streamed ADPCM
  dialogue, using compressed RIFF byte length could skew Logan conversation
  timing and route fidelity even when the sound object and stream provider
  were present.
- Validation: focused dialogue/audio diagnostics passed 12/12, and the broader
  local texture/audio/loading/indexed/skin contract set passed 39/39. The fast
  no-deploy candidate passed 54 focused tests, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, ARM package identity/hash checks,
  and the full canonical no-deploy build passed retained host-validation reuse,
  71 host unittest checks, deterministic restaging, source integration
  reporting, ARM link/package, compressed VPK validation, identity
  verification, diagnostics bundle generation, SHA manifest verification, and
  retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev59.vpk` SHA-256 is
  `f183d356ae60692f88d7676e06f8077af1537bb0398c6c5766e7f1225d7e5ab4`;
  ELF SHA-256 is
  `13d823d8f2d3641e4af4e34e9ddfdfc5acb08de658750d8ce720d2c3242b227e`.
- Boundary: dev59 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev59, verify
  Logan audible dialogue, dialog/message text, material/texture appearance, and
  route fidelity, then inspect
  `ux0:data/renegade/user/logs/a35-dev59-runtime.log`, especially speech
  duration/dropoff/distance, stream bytes/frames/mix/last-stream fields,
  conversation state, and texture/material provenance if dialogue remains
  silent or materials remain incorrect.

## 2026-08-28 — dev58 stage-1 multitexture boundary

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: the Vita DX8/WW3D boundary now treats the original two
  texture stages as real backend state instead of declaring stage 1
  unsupported. `IDirect3DDevice8::SetTexture`, sampler state, and texture-stage
  combiner state now track both original stages, and the direct Vita
  `MeshClass` submitter binds texture units 0/1 while emitting stage-1 UVs for
  original post-detail materials.
- Runtime purpose: retail materials that depend on original detail,
  scale/invscale, add/subtract, blend, and detail-blend stage-1 texture
  semantics now reach vitaGL through a bounded fixed-function combiner mapping.
  This preserves original `ShaderClass`, `TextureClass`, `MaterialPassClass`,
  and `MeshModelClass` ownership while removing the dev57 stage-1 unsupported
  renderer gap.
- Validation: focused texture surface/provenance/loading/indexed-state and
  skin/material contracts passed 27/27. The fast no-deploy candidate passed
  the expanded 53-test focused gate, the original `DDSFileClass`
  `.tga`-to-`.dds` executable contract 11/11, and package identity/hash checks.
  The full no-deploy canonical build passed retained host-validation reuse,
  70 host unittest checks, deterministic restaging, source integration
  reporting, ARM link/package, identity verification, compressed VPK
  validation, diagnostics bundle generation, SHA manifest verification, and
  retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev58.vpk` SHA-256 is
  `d9555d54aa3a577a8bb5a3b5ef6f32bf67aa96de4cc128e8726137a1798d0bb3`;
  ELF SHA-256 is
  `82be35efe2d243d04f29844aa0bc196573a33573f57353ab198166a4d4153ae6`.
- Boundary: dev58 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev58, verify
  audible Logan dialogue, message/dialog text, and material/texture appearance,
  then inspect `ux0:data/renegade/user/logs/a35-dev58-runtime.log`, especially
  `first original MeshClass stage1 texture`, `unsupported_stages`, `texture
  loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`, `speech=`, and
  `stream_mix` if dialogue is still inaudible or materials remain incorrect.

## 2026-08-28 — dev57 direct mesh base-pass replay

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: the direct Vita `MeshClass` submitter now replays every
  original base material pass instead of drawing only pass 0. Each pass reads
  its own stage-0 texture, shader, UV array, DCG colors, and vertex material
  from `MeshModelClass`, while the existing geometry fingerprint counters
  remain stable for host regression checks.
- Runtime purpose: retail lightmap/detail/emissive/shiny-mask material data
  that survived W3D load under original ownership now reaches the Vita draw
  boundary as pass-specific work instead of being silently skipped. Stage-1
  multitexture remains a bounded renderer gap.
- Validation: focused texture surface/provenance/loading/indexed-state
  contracts passed 24/24. The fast no-deploy candidate passed the expanded
  52-test focused gate, the original `DDSFileClass` `.tga`-to-`.dds`
  executable contract 11/11, and package identity/hash checks. The full
  no-deploy canonical build passed retained host-validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, SHA manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev57.vpk` SHA-256 is
  `b318946facbd3a732ae8bc314965985d7aebb918d09f15ea38df38a222165d90`;
  ELF SHA-256 is
  `176fc44a0139e59492c25ab1f54710290f3676b27bbb503efab51ec6b0bdb597`.
- Boundary: dev57 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev57, verify
  audible Logan dialogue, message/dialog text, and material/texture appearance,
  then inspect `ux0:data/renegade/user/logs/a35-dev57-runtime.log`, especially
  `texture loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`,
  `unsupported_stages`, `speech=`, and `stream_mix` if dialogue is still
  inaudible or materials remain incorrect.

## 2026-08-28 — dev56 DDS retained surface levels

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: DDS retail texture loads now retain decoded CPU-backed
  `D3DFMT_A8R8G8B8` surface levels for every mip while preserving DX8
  `SourceFormat` descriptor metadata from
  `WW3DFormat_To_D3DFormat(dds.Get_Format())`.
- Runtime purpose: original `GetSurfaceLevel()` callers no longer receive
  blank descriptor-only surfaces after DDS loads. The retained decoded retail
  pixels are available under original WW3D ownership for
  `SurfaceClass`, texture-loader, D3DX, missing-texture, and message/dialog
  text surface-copy paths.
- Validation: focused texture surface/provenance/loading/indexed-state
  contracts passed 23/23. The fast no-deploy candidate passed the expanded
  51-test focused gate, the original `DDSFileClass` `.tga`-to-`.dds`
  executable contract 11/11, and package identity/hash checks. The full
  no-deploy canonical build passed retained host-validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, SHA manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev56.vpk` SHA-256 is
  `ecea466be07e7648429c2f0daa653530a37aeb60c60940fe6befa444caebca17`;
  ELF SHA-256 is
  `fe25fdfa6b2dcc4e36be8c02b1defacd0e12207c4501d4d0f9ee5b086482a2ab`.
- Boundary: dev56 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev56, verify
  audible Logan dialogue, message/dialog text, and material/texture appearance,
  then inspect `ux0:data/renegade/user/logs/a35-dev56-runtime.log`, especially
  `texture loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`,
  `speech=`, and `stream_mix` if dialogue is still inaudible or materials
  remain incorrect.

## 2026-08-28 — dev55 DX8 surface-copy boundary

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: the Vita `IDirect3DDevice8::CopyRects` compatibility
  path now performs bounded CPU-backed surface copies instead of returning an
  invalid-call stub. Copies validate source/destination rectangles, preserve
  same-surface overlap with row-safe `memmove`, reject block-compressed
  formats, and upload a changed destination texture owner once after the copy.
- D3DX compatibility: `D3DXLoadSurfaceFromSurface` and `D3DXFilterTexture`
  are now declared and implemented for the original surface/mip frontier. The
  direct same-format path uses byte copies; scaled or format-converting paths
  use bounded RGBA sampling. Palette and color-key paths fail closed until an
  original caller proves they are needed.
- Runtime purpose: this restores the original `Render2DSentenceClass`
  pending-surface to texture-surface copy behavior used by message, loading,
  and dialogue text rendering, while also giving the staged original
  texture-loader frontier real surface/mip generation semantics.
- Validation: focused texture surface/provenance/loading/indexed-state
  contracts passed 22/22. The fast no-deploy candidate passed the expanded
  50-test focused gate, the original `DDSFileClass` `.tga`-to-`.dds`
  executable contract 11/11, and package identity/hash checks. The full
  no-deploy canonical build passed retained host-validation reuse, 68 host
  unittest checks, deterministic restaging, source integration reporting, ARM
  link/package, identity verification, compressed VPK validation, diagnostics
  bundle generation, SHA manifest verification, and retail exclusion.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev55.vpk` SHA-256 is
  `559b91c07e871a9171f704b59433c33dee14602edeba742ff51278925a24ca4d`;
  ELF SHA-256 is
  `3fa450de230e964b6da6794d607453ec0a157c7bf2226985473e4b322f528e11`.
- Boundary: dev55 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev55, verify
  audible Logan dialogue, message/dialog text, and material/texture appearance,
  then inspect `ux0:data/renegade/user/logs/a35-dev55-runtime.log`, especially
  `texture loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`,
  `speech=`, and `stream_mix` if dialogue is still inaudible or materials
  remain incorrect.

## 2026-08-28 — dev54 DX8 texture surface ownership

`[██████████] 12/12 canonical source/build gates complete`

- Renderer boundary: the Vita `IDirect3DTexture8` boundary now owns
  refcounted CPU-backed surface levels for lockable textures and implements
  `GetSurfaceLevel`, `LockRect`, `UnlockRect`, `GetPriority`/`SetPriority`,
  and width/height `_Create_DX8_Texture`. `SurfaceClass(IDirect3DSurface8*)`
  now mirrors desktop COM ownership by adding a reference and reading the
  surface description, so original `TextureClass::Get_Surface_Level()` can wrap
  and release the raw D3D surface safely.
- Runtime purpose: this removes the descriptor-only texture-surface stub that
  blocked original texture surface semantics in current `texture.cpp` and the
  staged `missingtexture.cpp`/`textureloader.cpp`/`dx8texman.cpp` frontier.
  Writable texture unlocks now upload the changed mip level through the Vita
  backend instead of losing the CPU-side update.
- Validation: focused texture surface/provenance/loading/indexed-state
  contracts passed 19/19. The fast no-deploy candidate passed the expanded
  47-test focused gate plus package identity/hash checks. The full no-deploy
  canonical build passed retained host-validation reuse, 68 host unittest
  checks, deterministic restaging, source integration reporting, the original
  `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev54.vpk` SHA-256 is
  `11d78031946e7e5b8becd710d7dfe3bce04d52ad5f88e347f5850feeef55a4b2`;
  packaged eboot/SELF SHA-256 is
  `82a66e1d06e244ef6a1bc1a82a3f06dd73d296f079f7f501645abfe7df0fb657`;
  ELF SHA-256 is
  `3b2afcd0337b316fff4b9a1c24a0877d94156c24b67b0596fc6d9517cd236b08`.
- Boundary: dev54 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev54, verify
  audible Logan dialogue and material/texture appearance, then inspect
  `ux0:data/renegade/user/logs/a35-dev54-runtime.log`, especially `texture
  loaded`, `loaded_dds/tga`, `checker_bind`, `invalid_bind`, `speech=`, and
  `stream_mix` if dialogue is still inaudible or materials remain incorrect.

## 2026-08-28 — dev53 texture provenance telemetry

`[██████████] 12/12 canonical source/build gates complete`

- Texture diagnostics: the Vita DX8 boundary now records successful retail
  texture loads by source path (`dds` or `tga`) and logs the first 24 loaded
  textures with size, mip count, DX8 format, resident bytes, checksum, alpha,
  fallback state, and native texture id. Checkerboard fallback binds are counted
  separately from invalid/null texture binds so pink/black visibility can be
  tied to missing/decode/upload fallback rather than generic bind failure.
- Runtime breadcrumbs: the `A3.5 perf` line now includes
  `loaded_dds/tga=%llu/%llu` and
  `source/invalid/unsupported/decode/upload_fail/checker/checker_bind/invalid_bind`.
  Capture JSON and capture-bundle comparisons now carry `texture_dds_loads`,
  `texture_tga_loads`, and `texture_checkerboard_binds`.
- Validation: focused texture provenance, loading-screen, indexed-state, and
  capture-compare contracts passed 17/17. The fast no-deploy candidate passed
  the expanded 42-test focused gate plus package identity/hash checks. The full
  no-deploy canonical build passed retained host validation reuse,
  deterministic restaging, source integration reporting, the original
  `DDSFileClass` `.tga`-to-`.dds` executable contract 11/11, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev53.vpk` SHA-256 is
  `bf3116fb0e122edd359b3a0ce2dffaa90df0b58599e77cfd803d825fa8d85699`;
  packaged eboot/SELF SHA-256 is
  `c384aba19d06450fc8cd1f6071083028001f12d1a3252ccffa7bbf1362030b49`;
  ELF SHA-256 is
  `ea279c8848c6f9df15f20b9c582855fb5c4a252662a495ec9e320db66ca6badb`.
- Historical boundary: dev53 was not physically tested before dev54 superseded
  it. Its diagnostics remain retained for comparing texture provenance,
  checkerboard fallback binds, active speech state, and stream-mix evidence if
  a later physical log needs source-level comparison.

## 2026-08-28 — dev52 active-conversation speech object diagnostics

`[██████████] 12/12 canonical source/build gates complete`

- Dialogue diagnostics: the active conversation state now reports the original
  speech object that actually owns playback. Soldier/orator remarks are read
  from `SoldierGameObj::CurrentSpeech`; non-orator conversation sounds still
  use `ActiveConversationClass::CurrentSound`. The probe is read-only and does
  not start, stop, advance, or create sounds.
- Runtime breadcrumbs: the `A3.5 mission progress` line now includes
  `speech=speaker:%d src:%d present/scene/culled/playing=%d/%d/%d/%d`,
  `class/type/state=%d/%d/%d`, and `dur/dropoff/dist=%u/%.3f/%.3f`. Combined
  with dev51 `stream_mix`, this separates "no original speech object",
  "speech exists but is culled", "speech is in the scene but not playing", and
  "speech is playing while decoded stream samples are zero or nonzero."
- Validation: focused mission-conversation diagnostics passed 10/10, the Vita
  audio provider contract passed 1/1, the route-session runner passed 11/11,
  the fast no-deploy build passed package identity/hash checks, the executable
  original `DDSFileClass` `.tga`-to-`.dds` alias contract passed 11/11, and
  the full no-deploy canonical build passed retained host validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream. The
  conversation diagnostics patch now explicitly covers `soldier.h`.
- Artifact: `dist/RenegadeVita-A3.5-dev52.vpk` SHA-256 is
  `d411723bb38a34afb68e4e324799c0f6bccab2e61f08d02fbdf47ea8afc6d8c8`;
  packaged eboot/SELF SHA-256 is
  `536bb10b276ac2b1ead72869d8331692f419fcc2c5b8161fcb88ac29211fa666`;
  ELF SHA-256 is
  `602b35d8d9832937610e729a603d2ff871f14a1943e0d3e530ce2016364f0f9f`.
- Boundary: dev52 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev52, verify
  audible Logan dialogue and material/texture appearance, then inspect
  `ux0:data/renegade/user/logs/a35-dev52-runtime.log`, especially the
  `speech=` and `stream_mix` fields if dialogue is still inaudible.

## 2026-08-28 — dev51 streamed-dialogue mix isolation candidate

`[██████████] 12/12 canonical source/build gates complete`

- Audio diagnostics: the Vita Miles provider now marks opened streams,
  isolates their contribution into a stream-only mix accumulator, and reports
  stream buffers, frames, nonzero buffers, peak sample, and active streamed
  sample count. This preserves original WWAudio/conversation ownership while
  separating "stream decoded but silent in the output mix" from "stream mixed
  nonzero samples but still not audible on hardware."
- Runtime breadcrumbs: the `A3.5 audio` line now includes
  `stream_mix=buffers:%llu frames:%llu nonzero:%llu peak:%u` and
  `allocated/active/streams=%u/%u/%u`, alongside the existing dialogue,
  cinematic, stream-read/decode/start, and Vita output counters.
- Validation: the host Vita Miles provider test now asserts stream-only mixed
  buffer/frame/nonzero/peak behavior and post-close active-stream accounting.
  Focused audio/build-script/diagnostic contracts passed 14/14, the fast
  no-deploy candidate passed 37/37 focused contracts, the executable original
  `DDSFileClass` `.tga`-to-`.dds` alias contract passed 11/11, and the full
  no-deploy canonical build passed retained host validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev51.vpk` SHA-256 is
  `5e4d371ac6f1c509a31f0b6c3fb47580dcb7dc4fef15a20aa6da01532f4f2e74`;
  packaged eboot/SELF SHA-256 is
  `10ff2488c2ea19d003c4ec328c74a683b0654b4f8a4f2917a7c3e97794293e24`;
  ELF SHA-256 is
  `e43764f3a6eacec16544c59340fa7bcadfc8f17ca3bcdf0035ad6b1fe7452e6d`.
- Boundary: dev51 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev51, verify
  audible Logan dialogue and material/texture appearance, then inspect
  `ux0:data/renegade/user/logs/a35-dev51-runtime.log`, especially the
  `stream_mix` fields if dialogue is still inaudible.

## 2026-08-28 — dev50 texture descriptor and SDK-root canonical candidate

`[██████████] 12/12 canonical source/build gates complete`

- Source correction: the Vita DX8 texture boundary now reports DDS texture
  descriptors in original DX8 `D3DFORMAT` terms instead of raw `WW3DFormat`
  enum values. This preserves the original `TextureClass::Init()` round trip
  through `D3DFormat_To_WW3DFormat()` and prevents the shipped
  `WW3D_FORMAT_DXT1` value from being misread as `D3DFMT_R8G8B8`.
- Audio contract: the Vita Miles provider mixer test now validates the whole
  four-frame mixed buffer for mono/pan-left and stream/pan-center cases, locking
  the single-rate cursor behavior needed for streamed dialogue.
- Build-system fix: the canonical and fast build scripts now default to the
  documented `/usr/local/vitasdk` via `RENEGADE_VITASDK`, and CMake detects
  vitaGL physical-contiguous memory names with declaration-aware enum matching.
  The dev50 canonical configure selected `VGL_MEM_SLOW` from `/usr/local/vitasdk`.
- Validation: focused audio/loading/build-script contracts passed 10/10, the
  fast no-deploy candidate passed 37/37 focused contracts, the executable
  original `DDSFileClass` `.tga`-to-`.dds` alias contract passed 11/11, and the
  full no-deploy canonical build passed retained host validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report records 451 upstream original
  Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev50.vpk` SHA-256 is
  `2c9fe46c04596171ba1bc5fa7f47b13d7b95ba565b751b9e528147d982d722b1`;
  packaged eboot/SELF SHA-256 is
  `f9df6d460599154a061a1240465ca1fcfa5ec4fd29d717384c1ff42ba1e673ff`;
  ELF SHA-256 is
  `3b5ed7597bfc36f14240cff75fbe2d4437e2ae8298eba57a4aa3ce22d0238725`.
- Boundary: dev50 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev50, verify
  audible Logan dialogue and material/texture appearance, then inspect
  `ux0:data/renegade/user/logs/a35-dev50-runtime.log`.

## 2026-08-28 — dev49 canonical dialogue telemetry and DDS-first texture candidate

`[██████████] 12/12 canonical source/build gates complete`

- Source correction: the Vita DX8 texture boundary now tries the original
  `DDSFileClass` route before the loose Targa route, so retail material names
  ending in `.tga` can resolve to the shipped `.dds` payloads through the
  original MIX/FileFactory chain. Targa remains as the fallback for real
  uncompressed `.tga` assets, and the first 16 texture fallbacks now log
  bounded reason/name breadcrumbs.
- Audio diagnostics: the Vita Miles-compatible provider now records stream
  bytes read, decoded frames, stream start success/silent/zero-volume counts,
  last stream name/rate/volume/pan, mix buffer/frame/nonzero/peak counters, and
  Vita output write counts. Runtime `A3.5 audio` breadcrumbs include those
  fields alongside dialog/cinematic category volumes.
- Build-system fix: canonical CMake now detects whether the installed vitaGL
  headers expose physical-contiguous memory as `VGL_MEM_PHYCONT` or
  `VGL_MEM_SLOW`, keeping the renderer memory telemetry portable across the
  two VitaSDK layouts present on this machine. The canonical build script also
  records the no-retail retained-host-validation fallback instead of failing
  when the local Steam retail tree is unavailable in WSL.
- Validation: focused fast contracts passed 37/37, including a new WWAudio
  stream-callback provider test and the updated DDS-first texture boundary
  contract. A new executable host contract also links original `DDSFileClass`
  and verifies `.tga` material names map to `.dds` factory lookups: 9/9. The
  full no-deploy canonical build passed retained host validation reuse,
  deterministic restaging, source integration reporting, ARM link/package,
  identity verification, compressed VPK validation, diagnostics bundle
  generation, and SHA manifest verification.
- Source report: the canonical integration report now records 451 upstream
  original Westwood translation units plus one staged original-owner extraction
  (`staging/commando/loadingscreen.cpp`), 26 Vita platform/renderer/validation
  files, 118 deterministic staging patches, and pristine upstream.
- Artifact: `dist/RenegadeVita-A3.5-dev49.vpk` SHA-256 is
  `abb0d3f8a6f895504ee78808ec834de3446d903ea912a8855d2f8e157fc75207`;
  SELF SHA-256 is
  `d6212ac5abd77f825c7d19eca3b9d549b3087d0919be7e7296d066476d0b38e0`;
  ELF SHA-256 is
  `78c76b5da8af4692a3ea20327d80b95fdc85ffd37547932e65eebe66ccd5c270`.
- Boundary: dev49 has not been physically tested and no Vita deployment was
  attempted. The next hardware run should manually install dev49, verify
  audible Logan dialogue and texture appearance, then inspect
  `ux0:data/renegade/user/logs/a35-dev49-runtime.log`.

## 2026-08-25 — broad Vita open-source reference toolkit

`[██████████] 10/10 current tooling gates complete`

- Scope: implemented the non-audio open-source reuse pass as isolated tooling
  and provenance. No gameplay/runtime source was changed, no external source
  tree was imported into the port, no retail data was packaged, and the Vita
  filesystem was not touched.
- Reference pull: `tools/vita_open_source_references.yml` pins 14 repositories
  for the current broad blockers: VitaSDK build/toolchain/samples, vitaGL,
  Vita3K, vita-crashdump, vita-parse-core, libvcp, Sokol audio,
  DaedalusX64-vitaGL, SRB2Kart Vita, Alisa-Vita, Vita Recorder, and psp2spvc.
  `python3 tools/fetch_vita_open_source_references.py` fetched 14/14 into
  `/tmp/renegade-vita-reference-cache`; the provenance report is
  `reports/generated/vita_open_source_reference_fetch.json`.
- License boundary: GPL-2.0-only and NOASSERTION projects are explicitly
  study-only. The compatible references are still fetched outside the source
  tree until a future blocker justifies a minimal copied implementation and
  reuse-ledger entry.
- Tooling added: `tools/fetch_vita_open_source_references.py` validates the
  manifest, uses the skill fetch helper with anchored sparse paths, verifies
  exact commits, counts materialized files, and writes the fetch report.
  `tools/run_vita3k_candidate.py` provides an optional Vita3K emulator-only
  runner and writes receipts with `physical_acceptance=false`.
- Source review: `reports/VITA_OPEN_SOURCE_REFERENCE_INSIGHTS.md` records the
  validated reference findings: Vita3K CLI flags, vitaGL renderer diagnostic
  flags and texture-cache conflict, Sokol's current Vita SceAudio backend,
  crash-dump parser feature targets, and license-based study-only boundaries.
- Validation: `python3 -m py_compile` passed for the new scripts; `bash -n`
  passed for the fetch helper; 62 focused Python tool tests passed, including
  `tools.test_vita_open_source_references`; the full reference fetch passed;
  the dev48 Vita3K dry-run generated
  `build/vita3k-evidence-dry-run/A3.5-dev48-20260825T174200Z/` against VPK
  SHA-256 `7830e41ef8ea98f1ce914091a292a7cceacb2b4bb5b5f20381047af446e2e067`.
- Boundary: no Vita3K executable was found; actual emulator execution remains
  unavailable until `VITA3K_EXE` or `--vita3k-exe` points to one. Emulator
  evidence will remain separate from physical Vita acceptance.

## 2026-08-24 — physical handoff read-only check

The Vita endpoint is online and exposes the admitted input/file capabilities, but
the installed executable is still the restored A3.5-dev46 SELF
`bb42fa9fbbf80e6eb90add5d3ae1bed708f1a9847f61ddc3d3fa441b4a10b244`. The device
still contains only the stale pre-dialogue route
`5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`. No app was
launched, no files were changed, and no dev48 deployment was performed. The
next approved hardware action is dev48 installation followed by a fresh
user-controlled record; the stale route remains inadmissible.

## 2026-08-25 — stale pre-dialogue replay closed

The retained route `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`
is now explicitly rejected by the dev48 route runner. Device evidence showed
that it was recorded before the TranslateDB object-factory fix: Logan's initial
conversation ended near frame 545 in the recording but remained active to about
frame 1345 in the corrected runtime, after which the replay reached no pistol
and settled in a corner. The route checksum was valid; its mission timing was
not. A new user-controlled record on the corrected candidate is required before
another replay can be admitted. Runner syntax and the 11-case route-runner
contract pass.

## 2026-08-25 — dev48 dialog-volume source/build candidate

`[██████████] 10/10 current evidence gates complete`

- Source correction: the Vita WWAudio path now initializes
  `m_DialogVolume` and `m_CinematicVolume` to original defaults in the
  constructor path used by `application_audio.Initialize()` without the desktop
  registry/default-volume route. This is a narrow audio-category fix below the
  dev47 string/sound-id lookup repair; it does not replace WWAudio,
  ConversationMgr, or retail data ownership.
- Diagnostics: `A3.5 audio` runtime breadcrumbs now include
  `volumes_dialog/cinematic`, so the next hardware run can distinguish
  category-volume failure from stream decode/mix/routing failure if dialogue is
  still inaudible.
- Build evidence: deterministic restage applied the WWAudio constructor patch,
  focused fast contracts passed 37/37, the dev48 package completed 15
  incremental ARM/package steps, identity verification passed, compressed VPK
  validation passed, and `SHA256SUMS` verified. VPK SHA-256 is
  `7830e41ef8ea98f1ce914091a292a7cceacb2b4bb5b5f20381047af446e2e067`;
  SELF SHA-256 is
  `0e61044df081b36b1a74da88c6157149cc27e818fca26f7bde537d00f710ec23`;
  ELF SHA-256 is
  `a4416e16a4678c645e492c91f55c4fc0decae095fb4589d947d9559ee1dc63bd`.
- Automation: the route runner is updated to exact dev48 hashes and runtime
  log path. It keeps dev46 and earlier exact hashes as rollback predecessors
  and intentionally does not admit failed dev47 as a predecessor.
- Boundary: dev48 is not deployed and has no physical audio acceptance. The
  retained dev43 no-dialogue route remains invalid for acceptance after dev47/
  dev48 dialogue timing changes. Next hardware should first verify audible
  dialogue and then record a fresh route; replay should come after that.

## 2026-08-25 — dev47 physical replay failed: lookup fixed, route/audio failed

`[██████████] 10/10 current evidence gates complete`

- Physical result: the approved dev47 replay failed. User observation reported
  the retained route was not followed, the player got stuck in a corner, and
  there was still no audible dialogue.
- Evidence is under
  `build/device-evidence/a3.5-dev47-route-replay-20260825-035432/`. The run
  reached `REPLAY_ACTIVE` with route SHA-256
  `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`, but was
  manually aborted after route divergence. The app was stopped and no new crash
  dump was recorded (`new_count=0`).
- Diagnostic split: dev47 did fix the concrete `STRINGS.TDB` object-row
  problem. Early `MTU_LOGAN_START` lines changed from dev46's `str=0` and
  `sound=-1` to `str=1` with valid sound ids such as `163849115`,
  `163849120`, `163849130`, `163849447`, and `163849137`. Audio counters also
  showed stream opens and starts with `last_error=no error`.
- Failure interpretation: because dialogue rows and durations now participate
  in runtime state, the old route recorded under no-dialogue timing is no
  longer timing-equivalent. That explains route divergence. It does not accept
  dialogue audio, because the user still heard no dialogue despite valid sound
  ids and stream counters.
- Device end state: the runner's VitaCompanion FTP rollback failed with
  `550 Could not allocate memory`, so dev46 was restored manually through a
  VDB1 staged replace. Final installed SELF is dev46
  `bb42fa9fbbf80e6eb90add5d3ae1bed708f1a9847f61ddc3d3fa441b4a10b244`; app
  status is stopped. A best-effort removal of the temporary rollback stage file
  reported file-remove failure, likely because the staged replace had already
  moved it.
- Boundary: dev47 is failed physical evidence. Next source work must diagnose
  inaudible streamed dialogue separately from SFX and must use a route strategy
  that waits for the new dialogue/control timing or records a fresh route after
  dialogue behavior is accepted.

## 2026-08-25 — dev47 TranslateDB object-factory source/build candidate

`[██████████] 10/10 current evidence gates complete`

- Diagnosis from dev46 physical replay: dialogue reached active M00
  conversations, the message-window render pass ran, and audio SFX output
  worked, but every active tutorial text lookup returned no string object and
  no sound id. Representative `MTU_LOGAN_*` entries logged
  `text/sound/str/def=<id>/-1/0/0`, while provider counters showed successful
  output start, sample-file loads, and sample starts for footsteps, weapons,
  reload, and impacts. This separates the current no-dialogue failure from the
  audio device/provider path.
- Source correction: the A31 original-source closure now links
  `wwtranslatedb/translateobj.cpp` and `wwtranslatedb/stringtwiddler.cpp`, the
  original translation database object factories required for
  `SaveLoadSystemClass::Load()` to instantiate `STRINGS.TDB` rows. No
  replacement dialogue system, asset conversion, or runtime data mutation was
  added.
- Build evidence: focused dialogue/audio/route/physical-gate contracts passed
  before packaging, then A3.5-dev47 fast package passed 35 focused contracts,
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and retail
  exclusion. VPK SHA-256 is
  `4845d1f5124ecab4b3c2657f3c9910bc697a65d4f3afa7e9064ba6b348a1facf`;
  SELF SHA-256 is
  `525b3d8af2f8cb44d5f1a9f05be3e0e79c1c0fc7846a11dd627e1141b197112e`;
  ELF SHA-256 is
  `cf2ed4da5107e63a026bb343bb7d8795d2f2ffa8db18b7ddf9d9aa24840e9089`.
- Automation: the route runner is locally updated to exact dev47, admits exact
  dev47 plus known exact prior dev46-through-dev7 executables, uses dev47
  runtime/evidence paths, and supplies the dev47 ELF/SHA to VDB crash reports.
- Boundary: dev47 is a source/build/package candidate only. Do not deploy or
  touch the Vita filesystem without explicit approval. The next physical gate
  is the same retained route replay, with user-observed dialogue plus returned
  text/sound/string/definition and provider counters.

## 2026-08-25 — dev46 dialogue presentation and audio-diagnostic candidate

`[██████████] 10/10 current evidence gates complete`

- Source correction: the direct Vita render envelope now restores the original
  interactive message-window pass after `CombatManager::Render()` and before
  the objective viewer/end-render path. This addresses the concrete text
  dialogue presentation gap without replacing ConversationMgr, DialogMgr, HUD,
  or Combat ownership.
- Diagnostics: mission-progress logging now records the active conversation
  remark text id, sound id, `STRINGS.TDB` object availability, and sound
  definition availability. The Vita Miles-compatible provider exposes bounded
  runtime counters for output start, sample-file load, stream open, sample
  start, active/allocated sounds, and the last provider error. The direct
  runtime logs these after audio init, periodically, and at final teardown.
- Build evidence: focused dialogue/render/audio-provider/physical-gate
  contracts passed, then A3.5-dev46 fast package passed 34 focused contracts,
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and retail
  exclusion. VPK SHA-256 is
  `bbf57d346ca373042cc4e2d4be0600617c6f9b4031466a4c08324e221f5aece9`;
  SELF SHA-256 is
  `bb42fa9fbbf80e6eb90add5d3ae1bed708f1a9847f61ddc3d3fa441b4a10b244`;
  ELF SHA-256 is
  `06d602aa57884f1a9d3f3e47cec0370849f6d4c87751417fc843fb28084eb680`.
- Physical replay evidence is under
  `build/device-evidence/a3.5-dev46-route-replay-20260825-034048/`. It used
  the retained dev43 route SHA-256
  `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`,
  returned PASS, verified `SHA256SUMS`, and returned to LiveArea cleanly.
  User observation: no dialogue, only SFX such as footsteps, walking, shooting,
  reloading, bullet puffs, ricochet, and impacts.
- Runtime diagnosis: message-window render closure was active, but every
  logged tutorial conversation lookup had `sound=-1`, `str=0`, and `def=0`.
  Audio provider counters remained healthy for SFX. Dev46 therefore proves the
  no-dialogue defect is upstream of sound creation/decode/output: the
  `STRINGS.TDB` object rows were not being instantiated into TranslateDB.

## 2026-08-25 — dev45 replay auto-exit pass

`[██████████] 10/10 current evidence gates complete`

- Source fix: route replay now requests clean exit only after all recorded
  samples are consumed, and the direct Vita runtime's START-exit poll also
  accepts that bounded route-complete signal. Physical START remains a live
  abort; original Input/Combat action ownership is unchanged.
- Build evidence: A3.5-dev45 fast package passed 33 focused contracts, ELF/
  SELF/VPK identity, compressed VPK validation, SHA manifest, and retail
  exclusion. VPK SHA-256 is
  `760995ea23896216349d75fc4c20caba7caa54c3fd73311d331051a31d5e939f`;
  SELF SHA-256 is
  `950950e04e6ae541ef076a9ae017f47af846ebaab169879621c2b7ea54d741b5`;
  ELF SHA-256 is
  `fe67954914c13d66af07b45786897c22f887acbc662931c0e5f3a4140900743b`.
- Replay evidence is under
  `build/device-evidence/a3.5-dev45-route-replay-20260825-025927/`. The runner
  admitted the dev43 route SHA-256
  `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`,
  returned PASS, and verified `SHA256SUMS`.
- Runtime evidence: `latest-session.log` records
  `replay complete: injecting clean exit sample=5958/5958`,
  `START exit request detected`, and
  `[LIFECYCLE] END status=clean candidate=A3.5-dev45`. Route validation remains
  version 2, 5,958 samples, complete, untruncated, exact-size, checksum
  matched; retail M00 remains unchanged at
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`.
- Device end state: user observed automatic LiveArea return; VDB app status is
  stopped, crash delta reports `new_count=0`, and installed SELF is exact
  dev45 `950950e04e6ae541ef076a9ae017f47af846ebaab169879621c2b7ea54d741b5`.
- Boundary: this accepts the current route/replay clean-exit automation gate.
  It does not by itself accept loading-screen visual correctness, NPC material
  correctness, sky/material appearance, Havoc arm/weapon visibility, audio, or
  longer mission stability.

## 2026-08-25 — dev43 replay fidelity pass with manual-exit caveat

`[█████████░] 9/10 current evidence gates complete`

- Replay evidence is under
  `build/device-evidence/a3.5-dev43-route-replay-20260825-023903/`. The runner
  admitted explicit route source
  `build/device-evidence/a3.5-dev43-route-record-20260825-022835/input-route-v1.bin`
  with SHA-256
  `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`.
- User-observed replay fidelity: gate, ladder, pistol obtain, and pistol
  firing were 1:1 with the recording.
- Runtime evidence: replay receipt PASS, clean lifecycle, no new PSP2DMP,
  unchanged retail M00 SHA-256
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`,
  `Weapon_Pistol_Player`, `fired_total=36`, skin deformation failures `0`,
  indexed submissions rejected `0`, and loading capture validation PASS.
- Caveat: the replay froze at the end and did not return to LiveArea until the
  user pressed START manually. The log then records `START exit request
  detected` and clean teardown. Do not count this as an automatic clean-exit
  replay pass.
- End state: exact dev43 SELF remains installed on the Vita:
  `c81cf891597d97720190b997d79cb67b56fe12911349f31b7ae9e3dfffaba935`.

## 2026-08-25 — dev43 clean route recording recovered after harness false-reject

`[█████████░] 9/10 current evidence gates complete`

- Now: A3.5-dev43 is the current physical route/runtime evidence point. It
  retains the dev40 loading path and later crash/runner fixes, then corrects
  the route activation gate so the runner does not pull an active player out
  when objective states are already hidden.
- Physical run: the user pressed START after the range gate opened. Runtime
  evidence under
  `build/device-evidence/a3.5-dev43-route-record-20260825-022835/` shows
  `route_activation_observed=1`, clean lifecycle end, no new PSP2DMP, 5,958
  recorded route samples, original Combat teardown, and unchanged retail M00
  SHA-256 `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`.
- Progression: the route reached `Weapon_Pistol_Player`, fired the pistol
  (`fired_total=36`), observed the Logan/range transition, and exited cleanly.
  The retained route SHA-256 is
  `5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895`.
- Harness correction: the original dev43 runner falsely rejected the recording
  because its pistol regex required positive `rounds=N/M`; the original runtime
  logs pistol state as `rounds=-1/N`. The runner now requires
  `Weapon_Pistol_Player` plus `fired_total > 0`, and focused route/mission/input
  tests pass 21/21.
- Capture evidence: loading-screen frame/state and pre-clean-exit state were
  pulled after the false-reject. `tools/validate_vita_loading_capture.py` passes
  for the returned loading BMP/state. This remains capture/metadata evidence;
  it does not by itself accept loading-screen visual correctness.
- Device end state: the failed-run cleanup restored exact prior dev18 SELF
  `058a10a594a8038833d8cced9a4b7a5207a4100079da44beef5c645a7ca69278`.

## 2026-08-24 — dev40 original TGA orientation candidate

`[█████████░] 9/10 current evidence gates complete`

- Historical: A3.5-dev40 was the active source/build/package candidate at this
  point. No dev40 Vita deployment or runtime iteration was attempted.
- Source correction: original `TextureLoader` keeps a Targa open, toggles
  `TGAIDF_YORIGIN`, then calls `Targa::Load()`. Dev39 admitted `.tga`
  textures but closed/reopened before load and still retained a
  loadscreen-only UV flip. Dev40 restores the original TGA Y-origin ordering,
  removes `Should_Flip_Loading_Texture_V` / `flip_texture_v` from mesh and
  indexed submissions, and records `loading_texture_v_flip_enabled=false` in
  returned loading visual-gate metadata.
- Retained fixes: dev40 keeps the shared original LoadingScreenClass owner,
  CombatManager progress ownership, original `loading_screen.Render(true)`
  callback semantics, scoped 640x480 loading resolution mapped to Vita 960x544,
  the required returned loading BMP/state capture gate, dev35's heap
  `A31FrameHistory` stack-frame fix, dev36's camera-Y boundary correction,
  dev37's DataSafe invalid-handle guard, dev38's schema-v4 visual gate, dev39's
  `.tga` texture admission, and the indexed shader/texture state fix for
  original sky/star/cloud dynamic indexed submissions.
- Evidence: focused loading/capture/comparator contracts pass 13/13. Broader
  route/loading/crash no-device contracts pass 28/28. Fast package focused
  contracts now pass 27/27 including camera/input route checks. The host
  loading-backdrop probe still passes against
  local retail data at
  `/mnt/d/SteamLibrary/steamapps/common/Command & Conquer Renegade`.
- Package evidence: ARM ELF compile/link, SELF/VPK identity, packaged eboot
  match, compressed VPK validation, SHA manifest, and retail-payload exclusion
  pass; the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Exact hashes: VPK
  `7dcd50a14b95c5ba899ae5cc557221eff7b449ed664bf58471dccf82e4f756d7`;
  packaged SELF `f59209cdecd00dcc398e8c8a13b7af96e2a2c75ad6d737c2ec33b80069ae9461`;
  ELF `15ecc59aecc8736c1dbeffddc81d42f58e53f3715be3925ae6424a5f55fbe77d`;
  map `ddad433bdb5c03f289c4f1e3c07442c60164732a1728d8f1d20768851ade0b15`;
  symbols `a7fe14f19acc20c07140a62d31e0fe7411f17cd3ed05dbc4ba633e03d0c43123`.
- Constraint: do not claim loading-screen correctness, camera correctness,
  pistol-shot stability, or visual/audio correctness until physical Vita
  evidence returns. The first approved physical gate remains loading-screen
  visual acceptance using user observation plus the returned BMP/state metadata.
  Only after that gate passes should user manual input establish a fresh route
  recording.

## 2026-08-24 — dev39 original loading TGA route candidate

`[█████████░] 9/10 current evidence gates complete`

- Historical: A3.5-dev39 is superseded by A3.5-dev40. No dev39 Vita deployment
  or runtime iteration was attempted.
- Source correction: the original-retail host probe proves the Renegade
  multiplayer loading model `if_lvl94load.w3d` resolves
  `loadscreen_beam.tga` and `loadscreen_cnc_1..4.tga` through the original
  FileFactory/MIX/WW3DAssetManager owner with full-tile UVs. The Vita DX8
  boundary now routes `.tga` texture filenames through `_Create_DX8_Surface()`
  before creating the texture instead of sending them through the DDS-only
  archive loader. This addresses the concrete black/missing loading-texture
  cause without replacing the original loading-screen owner.
- Retained fixes: dev39 keeps the shared original LoadingScreenClass owner,
  CombatManager progress ownership, original `loading_screen.Render(true)`
  callback semantics, scoped 640x480 loading resolution mapped to Vita 960x544,
  the bounded `loadscreen_*` V correction, the required returned loading
  BMP/state capture gate, dev35's heap `A31FrameHistory` stack-frame fix,
  dev36's camera-Y boundary correction, dev37's DataSafe invalid-handle guard,
  and dev38's schema-v4 returned loading visual-gate metadata. It also retains
  the indexed shader/texture state fix for original sky/star/cloud dynamic
  indexed submissions.
- Evidence: fast package focused contracts pass 18/18. Independent
  route-runner/loading/capture contracts pass 20/20 after moving the hardware
  runner to exact dev39. A broader no-device crash/loading/route suite passed
  25/25 before the runner relabel. The host loading-backdrop probe passes
  against local retail data at
  `/mnt/d/SteamLibrary/steamapps/common/Command & Conquer Renegade`.
- Package evidence: ARM ELF compile/link, SELF/VPK identity, packaged eboot
  match, compressed VPK validation, SHA manifest, and retail-payload exclusion
  pass; the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Exact hashes: VPK
  `bce09a36607770bdfb4f78f22573b04637dc48bbf5f9b2ba214ee8e770bb71b1`;
  packaged SELF `ccd306883de8d18f6dd72c2d247e905727c970f31ad095aa52c8b19dde435d0f`;
  ELF `aaf5340ccc4c1b4c84414bdfa4a6af77781e85afed6b288df6f0148e08fd29a0`;
  map `ad45ee98bc2d24112ff3c4c2cd87b479c053157aa1f917c1ccb5705b0fe46c70`;
  symbols `03d712510862ac7ab6132f040c8da2b3845d39ff698b930cf465202b1048e868`.
- Constraint: do not claim loading-screen correctness, camera correctness,
  pistol-shot stability, or visual/audio correctness until physical Vita
  evidence returns. The first approved physical gate remains loading-screen
  visual acceptance using user observation plus the returned BMP/state metadata.
  Only after that gate passes should user manual input establish a fresh route
  recording.

## 2026-08-24 — dev38 loading visual-gate schema candidate

`[█████████░] 9/10 current evidence gates complete`

- Now: A3.5-dev38 is the active source/build/package candidate. No dev38 Vita
  deployment or runtime iteration has been attempted.
- Source correction: returned loading-screen capture evidence now uses schema
  v4 and writes `loading_visual_gate` metadata into `loading-screen-state.json`
  and the summary. The metadata records the expected 640x480 original loading
  logical size, 960x544 native display/framebuffer size, fullscreen mapping,
  original `LoadingScreenClass` ownership, direct VitaGL loading overlay
  disabled, `loadscreen_*` V flip enabled, and gameplay UVs unchanged.
- Retained fixes: dev38 keeps the shared original LoadingScreenClass owner,
  CombatManager progress ownership, original `loading_screen.Render(true)`
  callback semantics, scoped 640x480 loading resolution mapped to Vita 960x544,
  the bounded `loadscreen_*` V correction, the required returned loading
  BMP/state capture gate, dev35's heap `A31FrameHistory` stack-frame fix,
  dev36's camera-Y boundary correction, and dev37's DataSafe invalid-handle
  guard.
- Evidence: loading-screen capture/comparator contracts pass 7/7. Focused
  data-safe, conversation, route-runner, and VDB crash snapshot-delta contracts
  pass 19/19. Fast package focused contracts pass 17/17. ARM ELF compile/link,
  SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Evidence-gate hardening: the returned loading capture validator now rejects
  bar-only or tiny/misplaced nonblack evidence by measuring full-frame content
  width/height extent and preserving bounding-box, edge-band, and quadrant
  diagnostics. Focused loading/comparison tests pass 12/12; the broader
  no-device crash/loading/route tooling suite passes 30/30 plus shell syntax
  and `BUILD_STATE.json` parsing. This strengthens the next physical loading
  gate but does not claim visual correctness.
- Automation prep: `tools/run_a35_vita_route_session.sh` now targets dev38,
  admits only the exact dev38 SELF plus known exact prior dev37 through dev7
  predecessors, uses dev38 runtime/evidence paths, prints a
  `LOADING_SCREEN_VISUAL_GATE` before launch, requires the loading-screen PASS
  log, pulls `loading-screen-frame.bmp` and `loading-screen-state.json`, then
  validates schema-v4/candidate/runtime-log identity, exact visual-gate
  metadata, native 960x544 24-bit BMP dimensions, nonblank/color evidence,
  broad full-frame content extent, and unchanged retail M00 hash before
  setting `new_route_retained=1`. It
  records the loading capture path and validation report in the receipt,
  snapshots VDB1 crash state before launch, takes a post-run snapshot on
  non-clean/failure paths, compares snapshots locally with
  `tools/vdb_crash_snapshot_delta.py`, directly pulls only new `ux0:/data`
  dumps through VDB1, verifies dump hashes, and supplies the dev38 ELF/SHA to
  VDB crash reports.
- Manual crash retrieval: `tools/collect_latest_vita_crash_dump.sh` now exposes
  the same read-only VDB crash snapshot/delta/pull/hash-check/report path for a
  user-driven crash that happens outside the route runner. The first dev38
  manual-crash collection under
  `build/device-evidence/A3.5-dev38-manual-crash-20260825T005958Z/` found no
  new dump beyond the 16-entry dev37 baseline and reports
  `device_mutation=false`.
- Exact hashes: VPK
  `61627ffbd4ce78d73b6d91fe6c59ab7c50ee3f2cacc77cf6e5fca1648362b34e`;
  packaged SELF `d8293dc331ee4460f5ee4527f08d05085aed263fbfb9846550cf35b575b1184b`;
  ELF `0b7b5f5d442c7e7ffae0e5e4292fc0a266dba42446290cbbdaf89d475a6aa066`;
  map `1ee5f2e1acfea715f72e4ac1f6e04a28c4d902f6b7de495664fcd470b4f54536`;
  symbols `d5ba4c8d5b869134841f7c1164d81c48ac6549ac8dcc88f22a05cc424b048401`.
- Constraint: do not claim loading-screen correctness, camera correctness,
  pistol-shot stability, or visual/audio correctness until physical Vita
  evidence returns. The first approved physical gate remains loading-screen
  visual acceptance using user observation plus the returned BMP/state metadata.
  Only after that gate passes should user manual input establish a fresh route
  recording.

## 2026-08-24 — dev37 VDB-symbolicated DataSafe pistol-crash guard candidate

`[█████████░] 9/10 current evidence gates complete`

- Historical: A3.5-dev37 is superseded by A3.5-dev38. No dev37 Vita deployment
  or runtime iteration was attempted.
- Crash evidence: the VDB PSP2 DMP analyzer was used on the retained dev19
  pistol-shot dump
  `build/device-evidence/a3.5-dev19-route-record-20260824-203126/crash-dumps/psp2core-1787603646-0x0000a634eb-eboot.bin.psp2dmp`
  with dump SHA-256
  `43490e2ed2c52a70fbb6821b3234cc30af83f5735cb373ca46146718d9c3eb90`.
  With descriptor-pinned dev19 ELF SHA-256
  `4eb15480cb7cadb926487a277b157af15326a0f200e75fe7d95b53337c69788e`
  and source-derived module base `0x81012000`, VDB maps the data-abort PC
  `0x810a2d8e` to `GenericDataSafeClass::Get_Entry` at `datasafe.cpp:350`.
- Source correction: dev37 adds deterministic staging patch
  `port/patches/commando-a35-datasafe-invalid-handle-guard.patch`. Release
  builds now fail closed before dereferencing `Safe[list]` in
  `GenericDataSafeClass::Get_Entry`, `Get_Entry_Type`, and
  `Get_Entry_By_Index`; debug `ds_assert` ownership remains intact.
- Retained fixes: dev37 keeps the shared original LoadingScreenClass owner,
  CombatManager progress ownership, original `loading_screen.Render(true)`
  callback semantics, scoped 640x480 loading resolution mapped to Vita 960x544,
  the bounded `loadscreen_*` V correction, the required returned loading
  BMP/state capture gate, dev35's heap `A31FrameHistory` stack-frame fix, and
  dev36's camera-Y boundary correction.
- Evidence: DataSafe crash contract passes 3/3. Focused data-safe,
  conversation, route-runner, and VDB crash snapshot-delta contracts pass
  19/19. Fast compile/package focused contracts pass. ARM ELF compile/link,
  SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Automation prep at the time: `tools/run_a35_vita_route_session.sh` targeted
  dev37, admitted only the exact dev37 SELF plus known exact prior dev36
  through dev7 predecessors, used dev37 runtime/evidence paths, printed a
  `LOADING_SCREEN_VISUAL_GATE` before launch, requires the loading-screen PASS
  log, pulled `loading-screen-frame.bmp` and `loading-screen-state.json`,
  recorded the loading capture path in the receipt, snapshotted VDB1 crash
  state before launch, took a post-run snapshot on non-clean/failure paths,
  compared snapshots locally with `tools/vdb_crash_snapshot_delta.py`, directly
  pulled only new `ux0:/data` dumps through VDB1, verified dump hashes, and
  supplied the dev37 ELF/SHA to VDB crash reports. It passed shell syntax plus
  10/10 route-session runner tests and the 1/1 crash snapshot-delta comparator
  test.
- Exact hashes: VPK
  `ab2842fb52c8d8349346232d6d2c8d7e58c020aba70a441a635db7d1568d75f4`;
  packaged SELF `f4d05d0c79d0a63ec9c24a94e875f9a46555d8e813aa6272ec3eb50f20e23bce`;
  ELF `f99795324fa3dea5660d9abc750b85ae00167ea705057dbaabd4573ff56887fc`;
  map `66b1f533ebd2c85cf24dea6b1e78674110cb44737ad2ee77b0c9be43b4c7fd54`;
  symbols `a75863d852f446b27448a715b8e148bdf6d381e059816602ddb3e090afd67790`.
- Constraint: do not claim pistol-shot stability, loading-screen correctness,
  camera correctness, or visual/audio correctness until physical Vita evidence
  returns. Latest read-only VDB1 crash retry under
  `build/device-evidence/a3.5-dev37-readonly-crash-retry-20260825T003102Z`
  found 16 existing `ux0:/data` crash entries, matching the older dev34
  snapshot count, with `new_count=0`; the latest user-reported crash is not
  present in that crash root. VDB `debug crash collect --since-bundle` rejects
  both old and fresh snapshots with `crash baseline snapshot schema is invalid`,
  so the route runner intentionally avoids that VDB path and uses local
  snapshot comparison plus direct VDB1 pull/report for future approved cycles.

## 2026-08-24 — dev36 camera-Y/loading-capture source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev36 is superseded by A3.5-dev37. No dev36 Vita
  deployment or runtime iteration was attempted.
- Source correction: after the latest physical feedback still reported inverted
  camera up/down, dev36 changes only the Vita right-stick Y mouse-delta default
  from inverted to non-inverted. Original `Input::Update_Sliders()` and
  `CCamera` remain unchanged and continue to own action/camera integration.
- Retained fixes: dev36 keeps the shared original LoadingScreenClass owner,
  CombatManager progress ownership, original `loading_screen.Render(true)`
  callback semantics, scoped 640x480 loading resolution mapped to Vita 960x544,
  the bounded `loadscreen_*` V correction, the required returned loading
  BMP/state capture gate, and dev35's heap `A31FrameHistory` stack-frame fix.
- Evidence: compiled Vita controller axis contract passes 22/22. Focused
  input/route/loading/conversation contracts pass 25/25. Fast compile/package
  focused contracts pass 17/17. ARM ELF compile/link, SELF/VPK identity,
  compressed VPK validation, SHA manifest, and retail-payload exclusion pass;
  the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Automation prep at the time: `tools/run_a35_vita_route_session.sh` targeted dev36,
  admits only the exact dev36 SELF plus known exact prior dev35 through dev7
  predecessors, uses dev36 runtime/evidence paths, prints a
  `LOADING_SCREEN_VISUAL_GATE` before launch, requires the loading-screen PASS
  log, pulls `loading-screen-frame.bmp` and `loading-screen-state.json`, records
  the loading capture path in the receipt, and passes shell syntax plus
  route-session runner tests.
- Exact hashes: VPK
  `5fcfcce9c32cb5b09881b79c07f98720d42763659f3c7612665db19b1878ce00`;
  packaged SELF `4451964aeefd1c0e5f690852e7111986f28006dc45900aff292b06d8cdb9e636`;
  ELF `e1ff05515cff40ba224aec1782b204e3a166479b92f1e2de84aefc2aea5d36e2`;
  map `508343cecb2794079d7dda0d259eca5e2e01a6a3f1117fd4ec4b9a0e1a8dfdb1`;
  symbols `dc82fd98fa0b7b852e1bfea443b747189ae2e1d609158957c48ab118ac8e8520`.
- Constraint: do not claim visual or camera correctness until physical Vita
  evidence returns. If explicitly approved for a device run, the first gate is
  still loading-screen layout, orientation, scaling, text placement, and
  progress acceptance using both user observation and the returned loading BMP;
  stop immediately if it is still wrong.

## 2026-08-24 — dev35 stack-frame crash fix source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev35 is superseded by A3.5-dev36. No dev35 Vita deployment
  or runtime iteration was attempted.
- Crash evidence: the approved dev34 route-record attempt produced
  `psp2core-1787615083-0x0004072f45-eboot.bin.psp2dmp` under
  `build/device-evidence/a3.5-dev34-route-record-20260824-234411/`; SHA-256
  is `fd27001824bccc038c28788ec25be7f4cb51ba8183af2319f652ff05d6eab05c`.
  VDB PSP2 analyzer with module `RenegadeVitaA31` base `0x81047000` maps the
  data-abort PC to `A31_Vita_Run_Interactive_Runtime()` line 605, the function
  prologue. The runtime log stopped after retail preflight.
- Source correction: dev35 moves `A31FrameHistory` off the Vita stack, reuses
  one heap history for loading and gameplay capture, resets it between the
  loading-screen capture and interactive capture stream, and deletes it during
  teardown. The original LoadingScreenClass path and capture gate are retained.
- Evidence: focused loading/route/conversation contracts pass 18/18. Fast
  compile/package focused contracts pass 17/17. ARM ELF compile/link, SELF/VPK
  identity, compressed VPK validation, SHA manifest, and retail-payload
  exclusion pass; the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
  Objdump shows the `A31_Vita_Run_Interactive_Runtime()` prologue stack
  subtraction reduced from about 276 KB in dev34 to about 17 KB in dev35.
- Automation prep at the time: `tools/run_a35_vita_route_session.sh` targeted
  dev35, admitted only the exact dev35 SELF plus known exact prior dev34
  through dev7 predecessors, used dev35 runtime/evidence paths, printed a
  `LOADING_SCREEN_VISUAL_GATE` before launch, requires the loading-screen PASS
  log, pulls `loading-screen-frame.bmp` and `loading-screen-state.json`, records
  the loading capture path in the receipt, and passes shell syntax plus 9/9
  route-session runner tests.
- Exact hashes: VPK
  `1c6b0926e420962a6eb04518863fd0c949f63b361a403d7ed0f50a968017a709`;
  packaged SELF `1dbb00a3191b1cb11272ee1faf0ca083e480284b9e6d78d7c1c94a287ea3ec56`;
  ELF `b3f63883571dd59ed9831f6935430d02e3e8d3a0a98bd7ad94ed27665b502727`;
  map `85ce85a442890eda324bb7d82f56254d966a9581cb152378b46972006d12ee87`;
  symbols `56e6a804918c91805e6eccd24bb0b35cb7f995d8d9ebdfdf53f7c4d3972f70fa`.
- Constraint: do not claim visual correctness until physical Vita evidence
  returns. If explicitly approved for a device run, the first gate is still
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance using both user observation and the returned loading BMP; stop
  immediately if it is still wrong.

## 2026-08-24 — dev34 loading-screen capture-gated route source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev34 is superseded by A3.5-dev35. The approved route-record
  attempt crashed before first original-runtime log and before loading-screen
  capture; rollback restored the prior executable.
- Source correction: dev34 retains dev33's `loadscreen_*` V-orientation bridge
  and adds a required loading-screen capture bundle at original
  `level_ready`. The capture is labelled
  `phase=original-loading-screen reason=level-ready` and is written before
  interactive gameplay capabilities are applied.
- Reuse boundary: the loading path remains the reusable original owner:
  Campaign backdrop parsing, `MenuBackDropClass`, `Render2DSentenceClass`,
  `SaveLoadStatus`, CombatManager progress, and
  `loading_screen.Render(true)` callback behavior; Vita adds only scoped
  resolution mapping, the loading-texture orientation bridge, and the
  evidence-only capture.
- Evidence: focused loading/route/indexed/staging contracts pass 21/21. Fast
  compile/package focused contracts pass 17/17. ARM ELF compile/link, SELF/VPK
  identity, compressed VPK validation, SHA manifest, and retail-payload
  exclusion pass; the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Automation prep: `tools/run_a35_vita_route_session.sh` now targets dev34,
  admits only the exact dev34 SELF plus known exact prior dev33 through dev7
  predecessors, uses dev34 runtime/evidence paths, prints a
  `LOADING_SCREEN_VISUAL_GATE` before launch, requires the loading-screen PASS
  log, pulls `loading-screen-frame.bmp` and `loading-screen-state.json`, records
  the loading capture path in the receipt, and passed shell syntax plus 9/9
  route-session runner tests. It was executed once for an approved route
  recording and crashed before the capture gate; rollback completed.
- Exact hashes: VPK
  `da0a3124b280d700f331a057533b1d71b7013764ef7f889ebef36257c6be3691`;
  packaged SELF `72aa828d090d3e74180b03582378c73c25a737b0ea7ffdc728c80564c35260ef`;
  ELF `0e5a9a4dcd59165ff541f4bcf40e03d37384cffe9f88463f8f10dd14d0997cdb`;
  map `1d9cf27b682bfd9fb0c168709af86b20fcbf40ca4ac09256df38796f7b132e25`;
  symbols `dce75f31cd39b3f62d914eae04a53505a1f4dfb58f86cdebe781b8e0a3d8a188`.
- Constraint: do not claim visual correctness until physical Vita evidence
  returns. If explicitly approved for a device run, the first gate is still
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance using both user observation and the returned loading BMP; stop
  immediately if it is still wrong.

## 2026-08-24 — dev33 loading-screen texture-orientation source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev33 is superseded by A3.5-dev34. It was a source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev32 kept the original `LoadingScreenClass` owner but
  still inherited a concrete Vita renderer orientation mismatch for
  `loadscreen_*` textures used by the original C&C multiplayer loading W3D.
  Dev33 keeps global gameplay/world UV semantics unchanged and flips V only
  when the bound original texture basename starts with `loadscreen_`.
- Reuse boundary: this remains the reusable loading-screen path. The original
  owner still performs Campaign backdrop parsing, `MenuBackDropClass`,
  `Render2DSentenceClass`, `SaveLoadStatus`, CombatManager progress, and
  `loading_screen.Render(true)` callback behavior; Vita adds only scoped
  resolution mapping and the loading-texture orientation bridge.
- Evidence: focused loading/indexed/staging contracts pass 12/12. Fast package
  focused contracts pass 17/17. ARM ELF compile/link, SELF/VPK identity,
  compressed VPK validation, SHA manifest, and retail-payload exclusion pass;
  the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Automation prep: `tools/run_a35_vita_route_session.sh` now targets dev33,
  admits only the exact dev33 SELF plus known exact prior dev32 through dev7
  predecessors, uses dev33 runtime/evidence paths, prints a
  `LOADING_SCREEN_VISUAL_GATE` before launch, records that logs cannot prove
  visual acceptance, and passes shell syntax plus 9/9 route-session runner
  tests. It has not been executed against the Vita.
- Exact hashes: VPK
  `d7a7386922ab8e8daa887890e7b3bfe71daa8e1ee9e4c03798f44dd3086c1dad`;
  packaged SELF `3f3f0519c16280137ab656d2761f7c659e54170cebeed00a09d316db0d515465`;
  ELF `b36afa9a0841f8d2b41fa808e3dc0aff4069bcd99b086c66465ca3389e4f0171`;
  map `cad0bdadfe9d0ceb0c5cb64ab9e6188fc47dec65e1b0eb895e550311d01d4de1`;
  symbols `7a84eb83de43e8b6046269e5f6433b6f04ab3a1590c98df0c2f1191068b9bb01`.
- Constraint: do not claim visual correctness until physical Vita evidence
  returns. If explicitly approved for a device run, the first gate is still
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev32 restage-proven shared LoadingScreenClass source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev32 is superseded by A3.5-dev33. It was a source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev31's shared original `LoadingScreenClass` extraction is
  now durable under deterministic staging. `tools/stage_sources.sh` applies
  `commando-a35-shared-loadingscreen-owner.patch`, which creates
  `loadingscreen.cpp/.h` and disables the duplicate in `combatgmode.cpp`.
  A forced-restage build no longer depends on reused staged files.
- Retained loading correction: direct Vita still creates/renders/destroys the
  shared original owner through the bridge, with original Campaign backdrop
  parsing, `MenuBackDropClass`, `Render2DSentenceClass`, `SaveLoadStatus`,
  CombatManager progress, original `loading_screen.Render(true)` callback, and
  scoped 640x480 WW3D/DX8Wrapper/Render2D loading layout mapped to Vita 960x544.
- Evidence: forced-restage A3.5-dev32 fast package passes 17/17 focused
  contracts. Staging/loading contracts pass 7/7. ELF/SELF/VPK identity,
  compressed VPK validation, SHA manifest, and retail-payload exclusion pass;
  the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Exact hashes: VPK
  `075682f499fd41f7783d79bcde25d1bc523224330bc58d2d3374d34288d9cb2d`; packaged
  SELF `a45d2a8b54c48e89327eab498bf9a439f497093e85719ffbce76de664a3eef12`;
  ELF `a9b3831cd6f7d296c61de26b2387e38cc3248e6623b2e787e699595c9c69dc82`;
  map `a6b4a7afcc5a221b2de1d85c752d0cf56814c45885e956391f3940e08ab7962d`;
  symbols `6b897415564fc0858d542332c57b7101f629c325e3bc72b6112581b7d1e941c1`.
- Constraint: the route runner is not updated to dev32 yet. Do not run another
  Vita iteration without explicit approval. If approved, the first gate is
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev31 shared original LoadingScreenClass source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev31 is superseded by A3.5-dev32. It was a source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev30 still used a Vita-side loading presenter clone.
  Dev31 links a shared original `LoadingScreenClass` implementation from
  `staging/commando/loadingscreen.cpp` and has direct Vita create/render/destroy
  that original owner through a narrow bridge. The scoped original 640x480
  WW3D/DX8Wrapper/Render2D loading layout and Vita 960x544 presentation mapping
  are retained.
- Reuse boundary: because the original owner now handles Campaign backdrop
  parsing, `MenuBackDropClass`, `Render2DSentenceClass`, `SaveLoadStatus`,
  CombatManager progress, and the original `loading_screen.Render(true)`
  callback, the same path can be bootstrapped to other original loading states
  instead of being a one-screen Vita overlay.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9.
  The final targeted loading/conversation/input-route/route-validator suite
  passes 16/16. A3.5-dev31 fast package passes 17/17 focused contracts.
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Exact hashes: VPK
  `0a1fd7c2bb5b06f448970529d247c25b30f0acd0265458e2e680a2e7a26a5b83`; packaged
  SELF `8375f3f30fe57e309bcf2b68b25a1e5f4a3a99f24953bbd36bd940cc2005c424`;
  ELF `058ed16d0ed5e3e87dcf5abaaf38edafb5e3943c57a48cbd160359385e5d049d`;
  map `94e3b6154242e6b17263963da8195a671c8090c9215634e9bdf13b3d4a6413e6`;
  symbols `f66dbd7f6798deb74acb62293a6d989f6f550022cde653b6ed3961382f1046ea`.
- Constraint at the time: the route runner was not updated to dev31. The
  current route-runner constraint is governed by the dev32 section above.

## 2026-08-24 — dev30 original WW3D/DX8 loading logical-resolution source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev30 is superseded by A3.5-dev31. It was a source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev29 scoped `Render2DClass` to 640x480, but original
  `Render2DClass::Render()` and `CameraClass::Apply()` still get viewport
  dimensions from WW3D/DX8 resolution queries. Dev30 scopes
  WW3D/DX8Wrapper/Render2D together to the original 640x480 loading logical
  resolution, then maps that logical viewport to the full 960x544 Vita
  framebuffer at the native boundary. Native resolution is restored before
  gameplay/HUD rendering.
- Retained loading correction: the failed direct VitaGL tile overlay remains
  absent. The path uses `STRINGS.TDB`, `StyleMgrClass`, original in-game fonts,
  `SaveLoadStatus`, original Campaign backdrop description 94,
  `MenuBackDropClass`, both `Render2DSentenceClass` text layers,
  `CombatManager::Set_Load_Progress(0)`,
  `CombatManager::Get_Load_Progress()`, and the original
  `cNetwork::Update` render callback semantics.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9.
  The final targeted loading/conversation/input-route/route-validator suite
  passes 16/16. A3.5-dev30 fast package passes 17/17 focused contracts.
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Exact hashes: VPK
  `6984647ae9e8503f1ca3c2aaea7f0dbbec5191839456046f85a82809505d2741`; packaged
  SELF `c3810e776f21ce7937c6a261893aed92ed3e5e0cafadf99e15020cb91094c52b`;
  ELF `93ef8f52749375b9f815ee475f1ab66b787569ad6afa85fbe86c7c4ca7389ca8`;
  map `87021178e4f20c57b522b7f06a1780d1f3008430edc938415b0b24a42fcfc487`;
  symbols `bef4bde4c6ed0d08c90e3b243b61d006b5a33b52064e44081a4ef63fe13740c6`.
- Constraint at the time: the route runner was not updated to dev30. The
  current route-runner constraint is governed by the dev31 section above.

## 2026-08-24 — dev29 original loading logical-resolution source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev29 is a superseded source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev28 restored original `loading_screen.Render(true)`
  callback behavior but still built `MenuBackDropClass` camera/view-plane math
  and `Render2DSentenceClass` text/wrap coordinates while
  `Render2DClass::ScreenResolution` was Vita native 960x544. Dev29 scopes
  `Render2DClass` to the original 640x480 loading logical resolution for
  loading-screen construction/rendering, then restores the Vita resolution
  before gameplay/HUD rendering.
- Retained loading correction: the failed direct VitaGL tile overlay remains
  absent. The path uses `STRINGS.TDB`, `StyleMgrClass`, original in-game fonts,
  `SaveLoadStatus`, original Campaign backdrop description 94,
  `MenuBackDropClass`, both `Render2DSentenceClass` text layers,
  `CombatManager::Set_Load_Progress(0)`,
  `CombatManager::Get_Load_Progress()`, and the original
  `cNetwork::Update` render callback semantics.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9.
  The final targeted loading/conversation/input-route/route-validator suite
  passes 16/16. A3.5-dev29 fast package passes 17/17 focused contracts.
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Exact hashes: VPK
  `3e6b5211fb0e82214bd4ea93a6641b560559c2e232b1fc48896d84b4f8d35470`; packaged
  SELF `899df03c98153d8888d00192cf7ef40875901f77aaca96b7c7a2434883cd53f0`;
  ELF `d284b8f92861e3b8da643552bfbc0bf74999215f73ea9004b9feb77112b01d97`;
  map `1404cae05c451799e6e9e4e337f7e84874e45c12172b10cf4d55efc04327475b`;
  symbols `2f0cab60b085f4c81ca43953a954de1a6cb28261c0bbd8e983670cf3485e528f`.
- Constraint: the route runner is not updated to dev29 yet. Do not run another
  Vita iteration without explicit approval. If approved, the first gate is
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev28 original loading render-callback source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev28 is a superseded source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev27 restored original `CombatManager` load-progress
  ownership but still missed the callback behavior used by original
  `loading_screen.Render(true)`. Dev28 now forwards `cNetwork::Update` through
  `WW3D::Begin_Render` during loading presentation, while retaining
  `CombatManager::Set_Load_Progress(0)`, `CombatManager::Get_Load_Progress()`,
  and the original `LoadPercentage / LoadTime` progress calculation.
- Retained loading correction: the failed direct VitaGL tile overlay remains
  absent. The path uses `STRINGS.TDB`, `StyleMgrClass`, original in-game fonts,
  `SaveLoadStatus`, original Campaign backdrop description 94,
  `MenuBackDropClass`, and both `Render2DSentenceClass` text layers.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9.
  A3.5-dev28 fast package passes 17/17 focused contracts. ELF/SELF/VPK
  identity, compressed VPK validation, SHA manifest, and retail-payload
  exclusion pass; the VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Exact hashes: VPK
  `f05e59cd0d8ad57308a819c20729859ff12dfc1be763938d758f6dc0bb036178`; packaged
  SELF `5d1226557ac8b2ce5d66c0f9ae8b59977af3fa3bc16fbb2b18ffbc39802b5aed`;
  ELF `7e6e47453987e8c18f251d2df36d4d0ce0e45e1874130c2b59ec239dec0bd7ea`;
  map `4b1515431f7d5d76b96f35fbb740fc67d18321f14db6fcb196bcd4c17cc62846`;
  symbols `0a4b2848ec685193125d98d851a1b969d574ddb6df8070f4dca03b75a7aa4808`.
- Constraint: the route runner is not updated to dev28 yet. Do not run another
  Vita iteration without explicit approval. If approved, the first gate is
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev27 original loading-progress source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical: A3.5-dev27 is a superseded source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev26 completed the original loading model/text/string/style
  path but still used manual terminal progress fractions. Dev27 now matches the
  original `LoadingScreenClass::Render` progress owner: it calls
  `CombatManager::Set_Load_Progress(0)` before loading-screen construction,
  samples `CombatManager::Get_Load_Progress()` inside each render after
  `TimeManager::Update_Frame_Time()`, calculates `LoadPercentageRate` from
  `LoadPercentage / LoadTime`, and removes the manual `0.985f`, `0.995f`, and
  forced-`1.0f` terminal updates.
- Retained loading correction: the failed direct VitaGL tile overlay remains
  absent. The path uses `STRINGS.TDB`, `StyleMgrClass`, original in-game fonts,
  `SaveLoadStatus`, original Campaign backdrop description 94,
  `MenuBackDropClass`, and both `Render2DSentenceClass` text layers.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9.
  A3.5-dev27 fast compile and fast package each pass 17 focused contracts.
  ELF/SELF/VPK identity, compressed VPK validation, SHA manifest, and
  retail-payload exclusion pass; the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Exact hashes: VPK
  `11a801347791528fd4ee6487e90e536dc14019474dd4c94a0b9c2e9ffe05eaa8`; packaged
  SELF `aa37b69ed826d4fbf5ad93506727a5aba4426bbddb16741afe48dfdc5bf9806d`;
  ELF `25fa4ecb6696eec1d09b786fbee8031394e08b905ecebe469ace53aa59ae81f7`;
  map `2a459ec0272c095c5da2aa20294cc0e6ef5dc217af35223ed93e21e15ecf88d6`;
  symbols `23389cf0fb397e1bd1c29b91cbfc5eb4815c0c1942d4ce922c3635bbabc6494e`.
- Constraint: the route runner was not updated to dev27. Do not run another
  Vita iteration without explicit approval. Dev28 is now the active source
  candidate; if approved, the first gate is
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev26 full original loading-screen source/build/package candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev26 is the active source/build/package candidate only. No Vita
  filesystem was accessed and no deployment or runtime iteration was attempted.
- Source correction: dev25 restored only the original `MenuBackDropClass` model
  animation. Dev26 completes the original `LoadingScreenClass` path by loading
  `STRINGS.TDB` through the current retail MIX file factory, initializing
  `StyleMgrClass` from `stylemgr.ini`, verifying the in-game normal and big
  fonts, resetting `SaveLoadStatus`, parsing original backdrop description 94
  records (`Model`, `Text`, `Text2`, `Wrap`, `Wrap2`, `Color`, `Test`), and
  rendering the `MenuBackDropClass` plus both `Render2DSentenceClass` text
  layers. The failed direct VitaGL tile overlay remains out of the active path.
- Evidence: focused loading-screen and mission-conversation contracts pass 9/9;
  the final targeted loading/conversation/input-route/route-validator check
  passes 13/13. A3.5-dev26 fast compile links `RenegadeVitaA31`. A3.5-dev26
  fast package passes 17 focused contracts, produces ELF/SELF/VPK artifacts,
  verifies compressed VPK data, passes identity verification, and confirms the
  VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Exact hashes: VPK
  `8b5131f97f8e80242303629fd6e2316c05faf26066da2485083de40f69899df1`; packaged
  SELF `8b2ff768f64d2f6d1ac0e79061eb734bb6c9cfa77246bdaebb82924a44de5b6f`;
  ELF `cd89110df49061af29094356bee1ba0a1b7ac7890f910c18a0f9d15f30bd31f9`;
  map `6b66e6f288031c4be7ef5676821c48b526a19ebbfca9ad83c467ef8391d61e16`;
  symbols `e1105f9d026684650492aa9e2b53483777c63f95214da71058d6180fdc888918`.
- Constraint: the route runner is not updated to dev26 yet. Do not run another
  Vita iteration without explicit approval. If approved, the first gate is
  loading-screen layout, orientation, scaling, text placement, and progress
  acceptance; stop immediately if it is still wrong.

## 2026-08-24 — dev25 original MenuBackDrop loading-screen source/build candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev25 is a source/build/package candidate only. No Vita filesystem
  was accessed and no deployment or runtime iteration was attempted.
- Source correction: the failed direct VitaGL four-tile loading overlay is no
  longer the active path. The direct Vita runtime initializes
  `CampaignManager`, selects original backdrop description 94 for the Renegade
  multiplayer loading screen, parses the original `Model` field, and drives
  `MenuBackDropClass::Set_Model`, `Set_Animation`, `Render`, and
  `Set_Animation_Percentage`. Runtime diagnostics identify this as
  `direct_vitagl_tiles=0` and `progress_owner=model_animation`.
- Evidence: focused loading-screen, input-route ABI, and route-validator
  contracts pass 11/11. The fast package run passes 17 focused contracts,
  produces ELF/SELF/VPK artifacts, verifies compressed VPK data, passes
  identity verification, and confirms the VPK contains only `eboot.bin` and
  `sce_sys/param.sfo`.
- Exact hashes: VPK
  `c34cabb08d56104a95032dcdda4e713ff5245140e38208963fb90bca098496fa`; packaged
  SELF `08cdf12864c0eb67d0675983f61bc7543085f4713d89975015847189f5684d4c`;
  ELF `ba882419108eb8898d8916b1c69775465a555c92d60acd1e0b1b52313e465c97`;
  map `4a2285abc89c1e7cfa511d211133ef37fcd31b188cfa9a5728225ba94f436ba3`;
  symbols `0ee73ee472682e5e52a725670b60e94a6600d05a076be3a8320a7b219db0fe72`.
- Constraint: the route runner is not updated to dev25 yet. Do not run another
  Vita iteration without explicit approval. If approved, the first gate is
  loading-screen layout/orientation/scaling/progress acceptance; stop
  immediately if it is still wrong.

## 2026-08-24 — dev24 physical loading failure; source repair only

`[████████░░] 8/10 current evidence gates complete`

- Now: dev24 is failed/unaccepted physical evidence. Do not run another Vita
  iteration until loading-screen correctness is fixed in source against the
  original Renegade loading-screen owner.
- Physical/user result: dev24 launched with matching SELF
  `1738526a3d556d56a02a077fc92ba115021d44144f4bdf1cbb0e673a0f251e30`, and logs
  under `build/device-evidence/a3.5-dev24-route-replay-20260824-220839/` show
  the four loading tiles resident (`tiles_ready=4/4`). The user-visible loading
  screen still remained wrong, invalidating the direct VitaGL four-tile
  shortcut.
- Secondary route result: the legacy replay did not arm. Runtime input telemetry
  stayed `route_mode/active/index/count/truncated=2/0/0/4880/0`; Mission00
  objective state was already `3/3/3/3/3/3`, so the activation predicate was
  too strict for this build.
- Safety/evidence: the interrupted session was killed and the runner completed
  rollback. Retail data was not mutated.
- Supersession: dev25 replaces this source action by selecting the original
  `CampaignManager`/`MenuBackDropClass` loading path. This section remains only
  as the dev24 failure record.

## 2026-08-24 — dev24 loading orientation/scale package candidate

`[████████░░] 8/10 current evidence gates complete`

- Historical package state before the failed physical replay above: A3.5-dev24
  was built as an unaccepted fast hardware candidate.
- Source review after dev23: transient local retail inspection confirmed the
  coherent original loading screen is `loadscreen_cnc_1..4.dds` in 1,2/3,4
  order with no per-tile vertical flip. Dev23 had the right four textures and
  route activation gate, but its loading draw still inverted each tile and
  cover-cropped the square 1024x1024 composition.
- Source correction: the loading presenter still initializes all four original
  CNC loading tiles and requires native non-fallback upload, but now maps them
  top-left/top-right/bottom-left/bottom-right with unflipped UVs and stretches
  the composed backdrop across the full 960x544 display behind the existing
  progress bar. The world mesh texture path is unchanged.
- Route status: original-control synchronized record/replay from dev23 is
  retained. Replay remains neutral before the gameplay activation gate except
  START abort. The runner is pinned to dev24 while admitting exact dev23/dev22/
  dev21/dev20/dev19/dev18/dev17/dev16/dev7 rollback predecessors.
- Evidence: focused loading, route ABI, validator, and route-runner contracts
  pass 19/19. A3.5-dev24 fast package passed 16 focused build contracts,
  compressed VPK validation, identity checks, SHA manifest verification, and
  retail-payload exclusion.
- Exact hashes: VPK
  `37a96dba2f19b2c3d534ff1ef60246220f9bb612e90f80226afffcd200778445`; packaged
  SELF `1738526a3d556d56a02a077fc92ba115021d44144f4bdf1cbb0e673a0f251e30`;
  ELF `39567a08fc260930fccc5574bebd1bd1eea7c8b94b0fdc71ba7f5d5774dba1d8`;
  map `5186f073a511dbac4173f925265f7efa83aff02b657c4b73d8054a2a5db6b7e1`;
  symbols `0c708ccbfec1d3f67486e71c462508a2720982b7954fad8fd4c252302bee6669`.
- Superseded result: the following physical replay invalidated dev24's loading
  screen. Do not retry dev24; repair the original loading path first.

## 2026-08-24 — dev23 four-tile loading and control-synced route candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev23 is the current unaccepted fast hardware candidate. A
  read-only device status check stopped because the Vita at `10.0.0.202` was
  unreachable (`No route to host`); no install, launch, route write, or
  retail-data operation occurred.
- Physical/user dev22 result: the loading screen remained wrong and the
  recording did not follow the prior path. Source review found dev22 drew only
  `loadscreen_cnc_1.dds`; retail `always.dat` contains the four 512x512 DXT1
  CNC loading tiles `loadscreen_cnc_1..4.dds`. Dev22 also admitted route
  record/replay before the same original player-control phase, so timed samples
  could still start from a different game epoch.
- Source corrections: the loading presenter now initializes all four original
  CNC loading tiles, requires native non-fallback upload for all four, logs
  tile/composed/display dimensions, and draws a centered cover-fit tiled
  backdrop behind the existing full-screen progress bar. The world mesh texture
  path is unchanged.
- Route corrections: record/replay still uses v2 `delta_us` samples, but the
  route stays inactive until Mission00 reports objective 1 pending with
  original player control enabled. Replay stays neutral before activation
  except START abort. The runner now requires the gameplay-activation log gate
  and is pinned to dev23 while admitting exact dev22/dev21/dev20/dev19/dev18/
  dev17/dev16/dev7 rollback predecessors.
- Evidence: focused loading, route ABI, validator, and route-runner contracts
  pass 19/19. A3.5-dev23 fast package passed 16 focused build contracts,
  compressed VPK validation, identity checks, SHA manifest verification, and
  retail-payload exclusion.
- Exact hashes: VPK
  `38be588b9709f628243509a8b3bc11e7e3ed2a6aeaed2ffe82145844393e3f7d`; packaged
  SELF `9dbfbce006634472aec5ce13b300d3924f14e6d24fde6e6cd3730acbe22a12cd`;
  ELF `6a0bbcd2c594ede7f7ba979862f08d8eeec93fd5cf31c1537e061684c4f7ccc8`;
  map `a6a51b29de9ac797c9f9bd503dd015469935cff00d73f904aeb02a8e257a235e`;
  symbols `3f97629638e913d04095c2ec410632488aaa1d19578639181442be6e7049608f`.
- Blocker: physical Vita network reachability is currently unavailable. Retry
  the dev23 `record` cycle when the device is awake/on-network and explicit
  install/run authorization is present.

## 2026-08-24 — dev22 loading residency and timed-route candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev22 is the current unaccepted fast hardware candidate. The first
  hardware record attempt stopped at the initial read-only status check because
  the Vita at `10.0.0.202` was unreachable (`No route to host`); no install,
  launch, route write, or retail-data operation occurred.
- Physical dev21 result: the retained 4,880-sample legacy v1 replay route ran
  but timed out without reaching pistol/conversation progression. Device logs
  showed the loading presenter reached the native full-screen path while the
  retail `loadscreen_cnc_1.dds` texture was not native-resident
  (`ready=0`), so dev21 is failed/unaccepted evidence.
- Source corrections: the loading presenter now calls original
  `TextureClass::Init()` before latching readiness, rejects native fallback,
  logs source and full-screen dimensions, and inverts V only for the direct
  hand-authored loading quad because the DDS upload stores source rows
  bottom-up. The world mesh texture path is unchanged.
- Route corrections: new recordings write v2 route samples with per-sample
  `delta_us`; old v1 routes remain readable only as legacy 60 Hz fallback.
  The runner pulls candidate logs before and after killing a failed session.
- Evidence: focused loading, route ABI, validator, and route-runner contracts
  pass 19/19. A3.5-dev22 fast package passed 16 focused build contracts,
  compressed VPK validation, identity checks, SHA manifest verification, and
  retail-payload exclusion.
- Exact hashes: VPK
  `530a3b22d8f6df5eb69554e842209ee1f66f21a8b8cf94254bacd128226945ae`; packaged
  SELF `528e1e87b97a88047c0b5ab65f1d7bba6d0f03a9edb37a1bca16b04bc3900bcf`;
  ELF `d9d32d84eeb28a7298369d9b6be1f235816ac0f9637e4dcf7af95ddb00185828`;
  map `8dbbf27d4104ef2e0507555eb4adf1244aa39d7f9244a3aecd77ff94d57fd863`;
  symbols `37c9acd07e046a6ce1b0a5b42e8fcb4e22c845818ef10f35ca377ee5559f5be4`.
- Blocker: physical Vita network reachability is currently unavailable. Retry
  the dev22 `record` cycle when the device is awake/on-network.

## 2026-08-24 — dev21 loading/replay correction candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev21 is the current unaccepted fast hardware candidate. No dev21
  Vita filesystem write has occurred.
- Physical dev20 result: the old 2,214-sample replay route was too short and
  frame-dependent; the user observed route drift and a still-wrong loading
  screen. The dev20 session was terminated and the previous executable was
  restored, so dev20 is failed/unaccepted evidence.
- Source corrections: the loading backdrop now draws the retail multiplayer
  `loadscreen_cnc_1.dds` as one native full-screen quad through the same
  top-left orthographic VitaGL path as the working progress bar, using normal
  D3D top-left UVs because DDS rows are already flipped at upload. Legacy v1
  route replay now advances by elapsed time at a 60 Hz sample timebase instead
  of one sample per current frame.
- Automation: replay can now upload a selected local route with
  `RENEGADE_ROUTE_FILE`, rejects replay routes under 4,000 samples by default,
  and restores the prior route if selected-route replay fails. The runner is
  pinned to exact dev21 SELF and admits exact dev20/dev19/dev18/dev17/dev16/dev7
  predecessor hashes for rollback-safe replacement.
- Evidence: focused loading, route, validator, and route-runner contracts pass
  17/17. A3.5-dev21 fast compile linked 14 affected actions and verified
  ELF/header/map/symbols. A3.5-dev21 fast package passed 16 focused contracts,
  compressed VPK data, identity, manifest, and two-file VPK inventory.
- Exact hashes: VPK
  `526ea4b10dc42ffae29b6010bad14e4d8fc4497249e1bcb7967a018a2dbd03eb`; packaged
  SELF `93ad509992d1f2e286dbcb56648da1bf8fe966911d6fe0707a9ca7f07b9b66ec`;
  ELF `07829f31cadef4f652c9fc25be62a01698c2a0e756a535b3cfb2b923c5f0d9a2`;
  map `784096b71f7753392ffc2356d4ee666591d302739b70df054ac808e49f0a1cb3`;
  symbols `e118d784bfe6e70846150710eea2bf1c5b66b2fbf46bb279ea6fa4fb66d69fc7`.
- Blocker: explicit authorization is required before installing/running dev21
  on the Vita. The next device cycle should be a fresh record, not the drifted
  short replay.

## 2026-08-24 — dev20 camera/loading/particle-crash candidate

`[████████░░] 8/10 current evidence gates complete`

- Now: A3.5-dev20 is the current unaccepted fast hardware candidate; no Vita
  filesystem write occurred during this work unit.
- Physical dev19 result: Logan progression and pistol acquisition were proven
  on hardware. The route reached `MTU_LOGAN_POKE` at frame 2648, restored
  control, granted `Weapon_Pistol_Player`, fired six rounds at the dummy, and
  captured the manual SELECT point. The app then crashed after the pistol-shot
  segment, so dev19 is not accepted.
- Crash evidence: PSP2 dump
  `build/device-evidence/a3.5-dev19-route-record-20260824-203126/crash-dumps/psp2core-1787603646-0x0000a634eb-eboot.bin.psp2dmp`
  has SHA-256
  `43490e2ed2c52a70fbb6821b3234cc30af83f5735cb373ca46146718d9c3eb90`.
  GDB did not recover registers; schema-inferred private thread notes point at
  `ParticleBufferClass::Reset_Size` dereferencing a suspect particle size
  keyframe pointer. The older filename-PC heuristic points elsewhere and is
  recorded only as heuristic.
- Source corrections: camera up/down is flipped back at the Vita
  device-to-mouse-delta boundary; loading now draws the retail multiplayer
  `loadscreen_cnc_1.dds` directly through original `Render2DClass` as a
  full-screen upright panel with the existing VitaGL progress bar over it; the
  particle size-keyframe path now refuses null, unaligned, out-of-range, or
  implausibly large keyframe arrays before dereference.
- Evidence: focused contracts pass 20/20 before build and 15/15 after runner
  update. A3.5-dev20 fast compile linked the ELF and validated compile
  artifacts. A3.5-dev20 fast package passed focused contracts 16/16, VPK
  compressed-data validation, identity checks, and SHA manifest verification.
- Exact hashes: VPK
  `8650d6f5cf65bef9c033551f2e14704db3411ca50867cf4ad5bf85bf36a7af26`; packaged
  SELF `5e4cc4a4ac44173158b5b897a733de6d46fb33390d7233641b760f83a86ce24f`;
  ELF `d7f6e8826cb2d6d26e4b9db70ae9776331656ff0a9052169e9b880c18e468fa0`;
  map `3202979b290677ffbec04c969dd93efb7e421f8e0e3aec1aef5c0877963f7981`;
  symbols `65c0a32a8f194fb76099b2dfd988db02948eda72e20888c7527ff15607a0e355`.
- Automation: `tools/run_a35_vita_route_session.sh` is now pinned to exact
  dev20 SELF and admits only exact dev19/dev18/dev17/dev16/dev7 predecessor
  hashes for rollback-safe replacement. It writes/reads
  `a35-dev20-runtime.log`.
- Blocker: explicit authorization is required before installing/running dev20
  on the Vita. Physical acceptance still requires camera direction, loading
  orientation/scale, pistol-shot stability, sky/materials, audio, and clean
  route exit.

## 2026-08-24 — dev19 Logan progression and camera-Y candidate

`[██████░░░░] 6/10 current evidence gates complete`

- Now: A3.5-dev19 is the current unaccepted fast hardware candidate; no Vita
  filesystem write occurred during this work unit.
- Physical diagnosis from the latest dev18 recording: the app did not crash or
  hard-freeze. Rendering and input telemetry continued to frame 3003, START
  exited cleanly, Logan jump control returned at frame 1640, and
  `MTU_LOGAN_EVA` completed at frame 2520. The first missing checkpoint is that
  `MTU_LOGAN_POKE` never became active, so the original pistol grant and
  `MTU_PARAM_CONTROL_ENABLE` never fired.
- Source correction: `MTU_LOGAN_POKE` is present in retail `M00_Tutorial.mix`.
  `ConversationMgrClass::Think()` now protects the active conversation during
  script callbacks and removes only that same pointer from
  `ActiveConversationList`, preventing a chained conversation from being
  deleted by a stale index after EVA completion.
- Input correction: Vita right-stick camera Y is flipped at the
  device-to-mouse-delta boundary based on the latest physical report; original
  `Input` and `CCamera` remain unchanged.
- Evidence: deterministic staging patch dry-run passes; focused contracts pass
  18/18; A3.5-dev19 package focused contracts pass 16/16; route-runner
  contracts pass 8/8; SHA manifest and VPK zip verification pass. Fast compile
  took 7.9 seconds; fast package took 16.9 seconds.
- Exact hashes: A3.5-dev19 VPK
  `9aa587203223d5bae22581491d67e97a8a822341f8723a5f3872d739946ad4d2`; packaged
  SELF `901fd5a0d7cb137a782ee42c666a91e9d9ca56a7f95397703468b3044f92e125`;
  ELF `4eb15480cb7cadb926487a277b157af15326a0f200e75fe7d95b53337c69788e`.
  The VPK contains only `sce_sys/param.sfo` and `eboot.bin`.
- Remaining visual blockers: loading-screen backdrop is still reported
  mis-scaled/upside-down, and NPC skin/material textures are still wrong though
  bodies are visible. These require phase-labelled physical capture after the
  progression candidate runs; no visual correctness claim is made.
- Blocker: explicit authorization is required before installing/running dev19
  on the Vita.

## 2026-08-24 — dev18 fast-candidate build path added

`[██████░░░░] 6/10 current evidence gates complete`

- Now: use `tools/build_fast_candidate.sh` for hardware-testable iteration
  builds when full canonical acceptance is not required. The canonical
  `tools/build.sh` remains the acceptance path.
- Build-overhead correction: the fast path uses a stable incremental CMake
  tree (`build/vita-fast-candidate` by default), keeps ccache stats, skips the
  full retained host/sanitizer route by default, and restages sources only when
  `RENEGADE_FAST_RESTAGE=1` or staging is missing.
- Compile-loop correction: `RENEGADE_FAST_SCOPE=compile` now builds only the
  linked `RenegadeVitaA31` ELF and intentionally skips the always-dirty VitaSDK
  SELF/VPK packaging steps. `RENEGADE_FAST_SCOPE=package` keeps the existing
  hardware-testable package path. `RENEGADE_FAST_TESTS=none` is available for a
  pure compile/link check; `focused` remains the default.
- Incremental-staging correction: `RENEGADE_INCREMENTAL_STAGE=1` now stages
  into a temporary tree and syncs only changed files into the managed staging
  subdirectories. Fast restage uses that mode by default; canonical staging
  remains destructive unless explicitly opted into incremental mode.
- Dev18 link correction: the direct Vita runtime uses the original
  `MenuBackDropClass` with retail-backed `IF_LVL94LOAD`/`IF_LVL94LOAD.IF_LVL94LOAD`
  and a VitaGL progress bar, without pulling `CampaignManager` into the direct
  runtime loading path.
- Evidence: focused contracts pass 13/13; the fast builder's internal focused
  tests pass 15/15; the existing dev18 build tree completed the final package
  path in 6 Ninja steps after the initial link; identity verification, ELF
  header, symbol, VPK zip, two-file VPK inventory, and retail-exclusion checks
  pass. ccache reported 82.16% hits.
- Incremental-staging evidence: shell syntax plus
  `tools.test_sync_staged_tree`,
  `tools.test_stage_sources_incremental_contract`, and
  `tools.test_fast_candidate_build_contract` pass 7/7. A no-op full stage
  reported `copied=0`, `removed=0`, `unchanged=1943`; the fast builder with
  `RENEGADE_FAST_RESTAGE=1` passed focused contracts 15/15 and identity/VPK
  checks. After the one-time recovery rebuild, Ninja dry-run reports only the
  six Vita SELF/VPK packaging steps and no C++ recompiles.
- Compile-scope evidence: `bash -n tools/build_fast_candidate.sh` and focused
  fast-build/staging contracts pass 8/8. A no-op run with
  `RENEGADE_FAST_SCOPE=compile RENEGADE_FAST_TESTS=none` completed in 2.1s,
  reported `ninja: no work to do`, validated ELF identity, and wrote
  `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder/dist/A3.5-dev18-FAST-COMPILE-SHA256SUMS.txt`.
- Route-runner update: `tools/run_a35_vita_route_session.sh` now admits exact
  dev18 SELF `058a10a594a8038833d8cced9a4b7a5207a4100079da44beef5c645a7ca69278`
  and exact predecessor hashes for dev17/dev16/dev7 only. Shell syntax and
  `tools.test_vita_route_session_runner` pass 7/7. No Vita filesystem was
  accessed by this metadata update.
- Fast candidate hash: VPK SHA-256
  `1d4daca0cca2972dcaf76714d558bb21a34fa18dd03a39a02262180e4c82d092`
  after the incremental-staging validation rebuild.
  Dist manifest:
  `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder/dist/A3.5-dev18-FAST-SHA256SUMS.txt`.
- Boundary: no Vita filesystem was accessed and no deployment was attempted.
  This is not physical acceptance and not a substitute for the full canonical
  build gate before milestone acceptance.
- Blocker: none for fast-build iteration; physical visual/audio/progression
  acceptance remains pending.

## 2026-08-24 — dev16 original WWAudio lifecycle candidate ready

`[████████░░] 8/10 current evidence gates complete`

- Now: await explicit authorization for the exact-hash dev16 physical replay;
  the Vita was not modified by this work unit. Read-only admission at
  `build/device-evidence/a3.5-dev16-admission-20260824-185719/` confirms the
  device is reachable, app stopped, exact dev7 is installed, retail M00 and the
  retained route match expected hashes, and no dev16 runtime log exists.
- Root cause correction: dev15 linked the complete original WWAudio/provider
  source graph but still constructed lite audio, omitted `Initialize()`, and
  never serviced it per frame. Dev16 first installs the rooted retail/MIX
  chain, creates the original basename-stripping audio adapter, then constructs
  and initializes non-lite original WWAudio before engine/world setup. It
  admits the session only with a sound scene and Vita-backed 2D/3D drivers,
  updates once after active render or during the suspended branch, and destroys
  audio before renderer/factory teardown.
- Ownership boundary: original WWAudio continues to own sounds, scene/listener
  state, callbacks, playback and events; only decode/mixing and SceAudio output
  remain platform-owned. Original ActiveConversation/TimeManager still owns
  remark progression, so Logan causality is not claimed.
- TT audit: the pinned official 4.8.4 r9000 archive/diff audit passes 5/5. It
  corroborates the constructor/frame-update interface but contains no audio,
  main-loop, or conversation implementation to import; no TT source or binary
  is included.
- Fresh retail evidence: D:-retail M00/M01/City two-cycle routes, ASan,
  LeakSanitizer, targeted UBSan, and the canonical 42-test selection pass;
  post-build full tool discovery passes 90/90. Host log SHA-256 is
  `d5503bf47ea37f184b268e18a3ec89101177fbbf8705538240ba033cabeda3fd`.
  Provider codec/mixer code has focused sanitizer coverage; the full host M00
  harness does not claim audible execution.
- Canonical evidence: deterministic 113-patch staging, all 482 ARM/package
  actions, identity 15/15, required symbols, compressed-package, manifest,
  diagnostics, and retail-exclusion checks pass. Source counts are 447
  original and 26 native boundary TUs.
- Exact hashes: ELF
  `684f15da87bb8e2d3fcdc45d7646132cb8f0ac65ec2612c0010d0365d10b8dea`;
  SELF `4dd1f7fd4a10ee26605986c58c1aad9e63986fbbf5c91e48326c9d4a0c81169f`;
  VPK `fa7903ba94442c7f18b554dd986d868bd90fe4dedfbcbcfc732b9f506e741a63`;
  diagnostics `9d7de514cb7a597ad59c037ef921770994102cd6aae57b06cc15580f6c49fabd`.
  The VPK contains only `eboot.bin` and `sce_sys/param.sfo`.
- Automation: the route runner admits exact dev16 SELF or exact installed dev7
  fallback only, retains the 4,537-sample route plus live START abort, and
  rolls back every failed deployed session.
- Blocker: physical observation must still accept audio, original sky/material
  appearance, Havoc arm/weapon geometry, Logan progression, and clean exit.

## 2026-08-24 — dev15 original WWAudio/Vita provider linkage superseded

`[████████░░] 8/10 current evidence gates complete`

- Historical state: no dev15 device write occurred. Post-build review found its
  Vita audio lifecycle inactive; dev16 above supersedes it.
- Original ownership: 15 additional EA/Westwood WWAudio translation units now
  own definitions, buffers, playlists, scene objects, callbacks, 2D/3D sound,
  priorities, looping, and timing above a narrow Miles-compatible Vita device
  boundary. The source report records all 20 WWAudio TUs selected.
- Native boundary: bounded RIFF PCM8/16, Microsoft IMA ADPCM, and Microsoft
  ADPCM decode; 48 kHz stereo rate conversion/mixing; pan, volume, loop, rate,
  encoded-byte seek/timing, and linear 3D distance attenuation; a blocking
  `sceAudioOutOutput` worker; original file callbacks for streams.
- TT integration: the official TT 4.8.4 revision-9000 reference remains pinned
  and audited out of tree. Its callback/schema/timing contracts informed the
  compatibility audit, but no TT source, binary, or Windows Miles runtime was
  imported. Five portable semantics are retained or equivalent.
- Focused evidence: PCM8/16, mono/stereo IMA, mono/stereo Microsoft ADPCM,
  bounded/truncated parsing, encoded-byte 3D seek, mixer, pan, and distance
  tests pass; ASan/UBSan and Vita ARM `-Werror` pass.
- Canonical evidence: deterministic 113-patch staging, 41 build-time contracts,
  482 ARM/packaging actions, identity 15/15, required audio symbols,
  ELF/SELF/VPK, compressed-package, manifest, diagnostics, and the post-restage
  89/89 suite pass. Unique source counts are 447 original plus 26 native TUs.
- Exact hashes: ELF
  `db96d327219e77d4df99d0a2942a635eda1872b311aa0c6dceb2b2a42d2eb0c9`;
  SELF `c4d5aaa1c04d93329617a086a7f57a423ff50ad40ee510f92a37ae9f8f9bfc1f`;
  VPK `e2036901c8edceaaee73a0bfb6d94f620476c794ab8dc94207feeb00b8ca17d3`;
  diagnostics `1cf8c7f118bb151c3308edfc11886c264bf1e95e1f303ea8399927cbb1906a6a`.
  The VPK contains only eboot and SFO.
- Validation boundary: the local retail link remains unavailable, so only the
  unchanged full retail M00 sanitizer route reused the matching retained log
  SHA-256 `97fc49202c76a04710964cf3939dd128329df88acc6b3005241632b69df5ec1e`.
  Changed audio code was tested freshly; no fresh retail sanitizer claim is
  made.
- Resource boundary: whole-track streaming is limited to 64 MiB but is not yet
  incremental or physically memory-measured; that remains v3.6 work.
- Historical automation: dev15 was formerly admitted with exact dev7 fallback,
  but is no longer in the current runner because it was never deployed and its
  activation gap is corrected by dev16.

## 2026-08-24 — dev14 host/ARM/package candidate superseded

`[████████░░] 8/10 current evidence gates complete`

- Historical state: dev14 was not physically replayed; the retained route and
  accepted dev7 fallback remained on the Vita while later candidates advanced.
- Physical dev13: exact SELF ran 4,507 frames and cleanly exited. The committed
  4,537-sample route SHA-256 is
  `39d915e02611079b29fb43cb2ea11ede583b063745e9675efe15010c606b7cf8`.
  Skin deformation recorded 37,606 submissions / 7,207,630 vertices / zero
  deformation or backend failures. The user nevertheless observed wrong NPC
  materials, no audio, black sky, and a post-ladder Logan interaction that did
  not progress; indexed draws/state applications remained zero.
- Rollback: exact dev7 SELF
  `7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5`
  is installed and stopped. Retail M00 remains SHA-256
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`.
- Source diagnosis: Vita passed rendering unavailable to original BackgroundMgr,
  preventing Sky/Dazzle construction; the mesh bridge also invented RGB from
  normals instead of using original DCG/VertexMaterial ownership.
- Dev14 correction: original background construction is enabled, unavailable
  DazzleLayer rendering is a bounded no-op, original material color/opacity is
  restored, and read-only conversation identity/state/remark timing is logged.
  No conversation is stopped or advanced and no weapon is granted by the port.
- Timing correction: `run_a35_vita_route_session.sh` now emits the play notice
  before launch; the later message is explicitly telemetry-ready.
- TT integration: official 4.8.4 revision 9000 source/diff are checksum-pinned
  and audited out of tree. Three portable semantics are already/equivalently
  in EA source; unavailable/PC-specific fixes are tracked without guessed code.
- Build evidence: deterministic 111-patch staging, 87/87 full contracts, the
  affected 504-action host target, all 465 ARM actions, ELF/SELF/VPK identity,
  compressed-package, manifest, symbol, and retail-exclusion gates pass. VPK
  SHA-256 is
  `6528991ca58877cb159a5c57b396c84e0a29c55ffa74487e5bb22f9af3e7e0e4`;
  SELF SHA-256 is
  `eda78f4f3dd57a064cb915af9cab677e3e64fc340c16ad09f0c74e6839ca6860`.
  The VPK contains only eboot and SFO; no Vita filesystem was accessed.
- Validation boundary: the local retail link was unavailable, so the package
  explicitly reused dev13's matching complete runtime/sanitizer log while
  freshly rebuilding the affected host and ARM targets. This is not a fresh
  retail sanitizer execution.
- Historical replay tooling: dev14 admitted only exact dev14 or exact dev7,
  kept the prelaunch play notice, and retained the live START abort plus
  unchanged-retail gate. The current runner is superseded by dev16 above.
- Historical blocker: dev14 had no native WWAudio output. Dev15 added provider
  source/link evidence; dev16 activates the original lifecycle. Physical
  visual, audio, and progression acceptance remains pending. The next replay
  must identify the exact original Logan conversation state; do not force
  completion.

## 2026-08-16 — v3.5 active

`[█████████░] 9/10 current evidence gates complete`

- Now: A3.5-dev2 physical Vita acceptance.
- Last focused step: A3.5-dev3 observer-loader chunk-open breadcrumb routing: deterministic WWLib `Open_Chunk` null-parent/required-root/short-read breadcrumbs and bounded contract coverage.
- Completed: A3.2 artifact identities verified; button state contract 10/10;
  axis/camera contract 22/22; weapon-style table deterministic repair; shader
  state contract 4/4; renderer lifecycle contract 11/11; bounded PSP2 note
  inventory; rate-limited deferred audio diagnostics.
- Completed: host observer-loader contract now directly exercises
  `PersistentGameObjObserverManager::Load` plus `ChunkLoadClass::Open_Chunk` null-file,
  truncated-root, parent-exhaustion, and repeated-open balance paths with `46` checks.
- Evidence: focused host tests pass and the changed ARM sources link locally.
- Retained host/sanitizer closure: PASS. The first canonical package attempt
  found and corrected a stale 14-versus-15 capture-test fingerprint; fresh ARM/VPK/hash/ZIP is next.
- ARM/VPK/hash/ZIP: PASS. Candidate VPK SHA-256 is
  `26445efb9ece7f64a86b38e6b49767233a7c3321f19c90e96ead6ef7c6073244`;
  it contains only `eboot.bin` and `sce_sys/param.sfo`.
- Remaining gate: authoritative physical Vita controls/visuals/lifecycle
  evidence.
- Blocker: user-performed physical test required; no automatic deployment was attempted.

The current package is `RenegadeVita-A3.5-dev2.vpk` SHA-256
`8ac77116c19d9eaf5093634ad9b5ff888ce9d42dcd42f34727ea52b9603a8b53` with
matching `A3.5-dev2-BUILD-DIAGNOSTICS-20260816-124825.zip`. Its packaging
reused the completed canonical host gate after only provenance/build-script
changes, then deterministically restaged and rebuilt the ARM candidate. ELF,
VPK and every SHA-manifest entry verified PASS. Physical evidence remains the
only open A3.5 gate.

Focused diagnostics, provenance, performance, asset/cache auditing, warning
trend, parser-fixture, and network-inventory work remains subject to narrow
file ownership and deterministic validation. The post-run diagnostic tool
recognizes this project's `*-SHA256SUMS.txt` manifests; its frozen VPK/ELF
manifest checks and two-run output comparison pass. A missing runtime log is
reported explicitly as `unknown`.

## 2026-08-16 — v3.6 host infrastructure

`[██░░░░░░░░] 2/10 current evidence gates complete`

- Added `tools/renegade_asset_manifest.py`: deterministic, read-only,
  content-hash inventory with required-archive validation and case-conflict
  detection. It does not extract, convert, or package retail assets.
- Unit tests: PASS (3 tests). Real local retail `Data` inventory: 51 files,
  required files present, no case conflicts, `always3.dat` present, digest
  `a3cc696b1d938c2780f1514875234a2ea9a9aac7b57bd5ac6f0d1599f01f4264`.
- This is host-only evidence; Vita cache/residency/memory/load behavior and
  second-scene validation remain open.

- Resource-boundary telemetry now accounts fixed-size `Read`/`Write` calls and
  bytes (13/13 focused host contract; ARM link PASS). No paths or file content
  are recorded, and original MIX routing remains unchanged.

The original-engine M01 archive preflight now passes: `MixFileFactoryClass`
enumerated 231 entries and found LDD/LSD/DEP content. It is integrated into the
canonical host runner but is not yet a full M01 PhysicsScene load.

M01 now has a separate original `CombatManager::Load_Level_Threaded` host proof:
two lifecycle cycles and 120 render/update frames each pass with zero rejected
or unsupported submissions. This remains host-only.

Cache-key v1 tests pass: source digest, cache/tool schema, and canonical
conversion options deterministically select a cache identity; invalid source
manifests are refused. No converted retail data is generated.

The expanded canonical host gate now passes M01 preflight and two original
Combat load/render/teardown cycles in addition to the retained M00 sanitizer
cycles. Evidence remains host-only.

Capture telemetry schema v2 is host- and ARM-link-validated. It records a
bounded periodic low-water free-memory sample for Vita system/VitaGL pools;
the capture self-test passes 17/17 and the capture comparison tests pass 2/2
with backward-compatible schema-v1 input. No device memory conclusion is made
without a returned physical capture bundle.

`C&C_City.mix` now passes a host-only original Combat load/render/teardown
smoke twice (120 frames each, first frame 43 meshes / 4,115 vertices / 2,963
triangles, zero rejected/unsupported). It is explicitly not a multiplayer
gameplay or network claim.

The host-only v1 archive-index precursor now enumerates through original
`MixFileFactoryClass` rather than a replacement parser. M01's 231-entry index
is byte-identical across two writes; City indexes 83 names. No retail content
is extracted, converted, or packaged.

The frozen A3.2 frame-2400 performance record has been re-extracted directly:
39.418 average FPS, p50/p95 21.874/24.446 ms, simulation/render 6.427/18.938
ms, and zero indexed submissions. It is now a hypothesis baseline only;
no optimization has been adopted without corrected-candidate A/B evidence.

Vita3K inspection is now recorded: the configured data root contains a
historical A3.1 `RNEGA3101` app only, with no configured emulator executable or
session logs. No emulator state changed; the documented loop remains a future
rapid-regression aid and never physical acceptance evidence.

The asset manifest now has explicit M01 and City profiles. Unit contracts pass
9/9 across capture/manifest/cache-key tools, and both real profiles are valid
against the same local 51-file content digest. The canonical host runner
regenerates them without extracting retail content.

The host cache-format precursor now writes versioned M01 index metadata and
verifies it against manifest/options identity and artifact hashes. The focused
contract suite passes 14/14; unsafe, stale, missing, and corrupt cache states
are explicit. Native device consumption is still unimplemented.

Final canonical revalidation now passes after correcting the runner to invoke
cache tools via `python3` rather than relying on their executable bits. The
retained M00 normal/ASan/LeakSanitizer/targeted-UBSan cycles, M01 two-cycle
original Combat route, and City two-cycle original Combat smoke all completed;
the complete host log is
`<managed-log-root>/a30-20260816-114055-host-runtime.log`.
The real M01 cache sidecar verifies `valid` for key
`55d93acb1240e2b7ddb4416660d0a3b0e7330eb7499eed10099fcd177c762538` and the
two generated index writes share SHA-256
`7a277d47fd50388ccec9c7841d3127cb452903b502f67b8dfa2df82605531b34`.

`[█████████░] 9/10 current evidence gates complete`

- Now: persist host v3.6 evidence and prepare the next native cache-consumer
  boundary without bypassing original MIX loading.
- Next: optional device cache validation, resource/memory/storage capture, and
  the pending A3.5-dev1 physical correctness test.
- Blocker: no engineering blocker; all device conclusions remain untested.

The next native v3.6 boundary is now implemented and host/ARM-closed. The
startup-only `Renegade_Inspect_Mix_Index_Cache` probe is constrained to the
existing `cache/` namespace and validates a bounded v1 M01 filename-index
structure. Its 9/9 contract covers absent, valid, malformed, retail-path, and
traversal cases. Invalid or absent indexes only produce a diagnostic state;
the original retail `MixFileFactoryClass` path remains authoritative.

The canonical gate including this contract passed at
`<managed-log-root>/a30-20260816-115428-host-runtime.log`:
M00 normal/ASan/LeakSanitizer/targeted-UBSan, M01, and City cycles all pass.
The current production executable ARM-links and exports the cache-health
symbols. No VPK was repackaged and no physical cache behavior is claimed.

## 2026-08-16 — v3.6 resource telemetry and lifecycle correction

`[█████████░] 9/10 current evidence gates complete`

- Completed: rooted original-file-factory telemetry contract 12/12; counters
  record Get/Return, read/write resolution, prepared-resolution hits, and
  open/availability/create/delete attempts/failures without names, payloads,
  allocations, or a replacement loader. The Vita runtime emits one teardown
  summary; original `MixFileFactoryClass` ownership is unchanged.
- Corrected: the next canonical host run exposed an 80,256-byte
  `PathSolveClass` retention after the direct harness omitted the original
  `PathMgrClass` process lifecycle. Both host and Vita paths now initialize it
  after `WWMath` and shut it down after `WW3DAssetManager`, precisely matching
  original Commando application order.
- Evidence: focused two-cycle M00 ASan/LeakSanitizer rerun is PASS at
  `build/host-a31-asan/a36-pathmgr-lsan.log` with no sanitizer finding; the
  ARM EABI5 closure links and exports `PathMgrClass::{Initialize,Shutdown}`
  and `Renegade_File_Factory_{Reset,Get}_Statistics`.
- Next: rerun the full canonical host gate once, then obtain physical A3.5
  evidence before any candidate promotion. The in-tree rebuilt VPK is not a
  candidate: it lacks a matching diagnostics package and physical validation.

Canonical revalidation is now PASS at
`<managed-log-root>/a30-20260816-122251-host-runtime.log`:
the retained M00 normal/ASan/LeakSanitizer/targeted-UBSan cycles and the M01
and City two-cycle original Combat paths all completed. The focused PathMgr
LSan proof remains at `build/host-a31-asan/a36-pathmgr-lsan.log`.

## 2026-08-16 — A3.5-dev3 hardware candidate

`[████████░░] 8/10 current candidate evidence gates complete`

- Completed: canonical host execution/sanitizer validation, ARM EABI5 link,
  VPK packaging, compressed-VPK validation, and generated-artifact hash
  verification for A3.5-dev3.
- Evidence: build log
  `<managed-log-root>/a35-dev3-20260816-135706-build.log`
  exited 0; diagnostics bundle
  `A3.5-dev3-BUILD-DIAGNOSTICS-20260816-135706.zip` is present; VPK SHA-256 is
  `286eaf0bd0bef9bd62802228df0e947c1d0310085f750320deed7bd49d837ded`.
- Next: manual physical Vita validation of controls, perspective, muzzle alpha,
  release behavior, pause/resume, and clean LiveArea exit. No physical result
  is claimed.

## 2026-08-16 — A3.5-dev3 physical-crash correction

`[████░░░░░░] 40% — exact dev3 crash reconstruction`

- Verified: the returned dump and dev3 ELF/map/symbol/VPK identities match the
  supplied SHA-256 values. VitaSDK ARM Thumb disassembly proves PC
  `0x810EAFBE` is the `bl ChunkLoadClass::Open_Chunk()` instruction in
  `PersistentGameObjObserverManager::Load`, not the historical HumanState
  crash.
- Corrected: the Vita controller boundary no longer reverses left Y and no
  longer defaults camera invert-Y on. The revised 22-check input contract
  passes on host.
- Corrected: future candidate packaging writes an explicit no-matching-dump
  status instead of copying the old A3.2 symbolication report.
- Pending: establish why the observer loader reaches an invalid FileClass or
  chunk state; no new VPK is promoted while that root cause is unresolved.
- Added: combat observer loader diagnostics patch (`combat-a35-observer-load-diagnostics.patch`)
  applied via staging (`tools/stage_sources.sh`), plus new deterministic host contract
  target `a35_persistent_observer_loader_contract_selftest` in
  `tools/host_a30_definitions/CMakeLists.txt`.
- Added: `port/validation/persistent_observer_loader_contract.cpp` directly covers
  `PersistentGameObjObserverManager::Load` with deterministic fixtures and a narrow
  registered factory hook: required-root open/ID failures, truncated headers, known
  vs. unknown children, repeated invocation, and chunk depth/close balance.
- Validation: `a35_persistent_observer_loader_contract_selftest` and `a36_file_factory_telemetry_contract_selftest`
  both pass (including ASan and UBSan build routes) with exit status `0`.
- Still pending: physical Vita breadcrumb evidence for the `0x810EAFBE` session remains
  unverified; this step intentionally validates only deterministic host fixtures.

## 2026-08-16 — A3.5-dev4 candidate identity correction

`[██░░░░░░░░] 20% — candidate integrity gate, no physical acceptance`

- Invalidated: `A3.5-dev4` physical evidence is not a valid candidate result.
  Its VPK/report filename was dev4, but the returned ELF retained dev1/A3.1
  runtime labels and the dev1 runtime-log path. The return does not prove the
  observer, axis, player, NPC, weapon, or camera paths ran.
- Returned static capture: framebuffer readback is valid, but the capture state
  records static-world rather than interactive-player conditions. The empty
  orderly-exit bundle is a failed evidence result, not a clean exit claim.
- In progress: generated-at-configure build identity, final ELF/SELF/VPK
  lineage verification, unified runtime log identity, phase-labelled capture
  metadata, post-write artifact checks, and a fixed-width overlay formatter.
- Gate: no successor VPK is called hardware-ready until a fresh ARM build and
  retained diagnostics prove candidate identity, nonempty evidence artifacts,
  and the candidate-specific runtime-log path.
- Added: the live ARM interactive path now emits a first
  `interactive-player-owned` capture only after original Combat reports both
  its player object and camera. Static-world, simulated-host-interactive, and
  device-interactive evidence remain explicitly distinct.
- Built: fresh canonical `A3.5-dev5` host/ARM/VPK candidate. The complete host
  gate and focused contracts pass; the ARM target selected 424 original plus
  21 port translation units and completed 456 build actions.
- Verified: final VPK SHA-256
  `e69919b557b8b2a807ac6437310d4c62072635ce1a493e63eee604a0c935287c`;
  final ELF SHA-256
  `bf1a250554f0666fbc3814f0a47b784cd399a410bd823bf12885c8a92ebd2e05`.
  All 15 identity/lineage checks pass and the VPK contains only `eboot.bin`
  and `sce_sys/param.sfo`.
- Physical gate: pending. The tester must stop immediately unless startup says
  `A3.5-dev5` and `a35-dev5-runtime.log` is created. No visual defect or
  milestone acceptance is claimed from host/ARM evidence.

## 2026-08-24 — A3.5-dev5 physical M00 loader isolation and recovery

`[████░░░░░░] 4/10 current evidence gates complete`

- Initial physical evidence in this work unit entered the original Combat/M00
  static-object loader but did not reach a first rendered frame. Those durable
  breadcrumbs repeatedly stopped
  inside object 116 after nested on-demand W3D loading; the last completed
  breadcrumb is the return from loading `E_FLAME01.w3d`, before the outer
  `Create_Render_Obj` returns. This is a loader blocker, not visual acceptance.
- The Vita-only original `LoadLevelThreadClass::Thread_Function` now runs
  synchronously on the vitaGL-owning main thread. Exact-source comparisons with
  vitaGL, OpenLara, vitaXash3D, and vitaRTCW support that ownership boundary.
  A physical rerun reached the same object-116 endpoint, so the correction is
  retained but is not claimed as the root fix.
- Sampled memory at objects 0, 25, 50, 75, 100, and 108-116 remained byte-for-byte
  flat across all exposed system and vitaGL free pools. A speculative vitaGL
  pool-size change is rejected as the immediate fix; internal heap pressure is
  still a separate unmeasured possibility.
- The remote-test wake blocker is resolved by the device-specific GPL
  `renegade_nolockscreen` SceShell user plugin. It fingerprinted the exact retail
  3.65 SceShell module, applied and post-validated both bounded injections, and
  the user physically confirmed that the main screen appears with the wipe
  bypassed. The active config/plugin and exact pre-change config backup are
  hash-retained; temporary probe files were removed. This closes an automation
  prerequisite and does not increment a game gate.
- Diagnostic plan at that point: trace bounded recursive
  `WW3DAssetManager::Create_Render_Obj` entry,
  prototype lookup, and `PrototypeClass::Create` return depth around object 116,
  then run one time-bounded physical diagnostic with Renegade killed afterward.

### Follow-up physical result

`[█████░░░░░] 5/10 current evidence gates complete`

- The fresh recursive trace proves object 116 is not hung. `MGWEP_AG_3`
  completes its nested depth-2 prototype work, returns through render and
  physics persistence, and the loader continues through all 495 static objects.
  `Load_Game` and the original loader-thread function return, M00 completes in
  the current direct route, and the original player/session/camera path reaches
  its first Combat frame.
- Canonical A3.5-dev5 ARM build `20260824-004956` passed all 456 actions, ELF,
  SELF, VPK, identity, inventory, and diagnostic-manifest checks. The physically
  installed SELF SHA-256 is
  `ec08e891087243a6a44da8db29ef80bf9c485d31a6ef1b0f27423ea9626b59b1`;
  the prior installed SELF was pulled and retained before replacement.
- Retail recopy was not required. On-device `M00_Tutorial.mix` is 5,802,816
  bytes with SHA-256
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`;
  `always.dat` remains present at 578,539,390 bytes. The current run loads and
  renders from that unchanged retail tree.
- The first automatic interactive readback sampled a stale post-swap vitaGL
  splash buffer. A readiness-gated manual Select capture at frame 355, after
  three untouched interactive seconds, returned a clear textured original M00
  yard with the player-owned camera and first-person weapon. Raw BMP SHA-256 is
  `13f4f1173f452d039c1d14f3cc15e89bb1a9a8ef6c38ef981ec5b57f85f6607e`.
- A separate readiness-gated run exercised forward movement, camera look,
  strafe, jump-button, action-button, a second forward/look segment, and a late
  manual capture. Device telemetry records the stick states and the player moved
  from `(-58.328,-41.527,0.588)` to `(-46.290,-43.339,0.607)`. Jump and action
  input delivery are observed; their world effects are not yet accepted.
- Both physical runs reported zero rejected submissions and zero renderer
  backend errors. The spawn control ran 355 frames and the interaction run
  reached frame 1,321. Each run ended with release-all, app kill, sleep restore,
  and verified `running=false`.
- Evidence is retained under
  `build/device-evidence/a35-dev5-recursive-create-20260824/`. Remaining v3.5
  gates are collision/grounding and action-effect observation, pause/clean exit,
  and restart/repeat stability; bounded repeated-session soak remains v3.9,
  while HUD/audio and mission progression remain later capability gates.

### Clean exit and restart follow-up

`[██████░░░░] 6/10 current evidence gates complete`

- A readiness-gated clean-exit run reached 417 frames, passed the 120/240/360
  checkpoints, then responded to START by completing original Combat level
  unload, session teardown, GameInit SP shutdown, network shutdown, logical
  renderer shutdown, and application audio teardown. It self-exited within one
  second with `exit=1 render_error=0 teardown=1` and lifecycle `END status=clean`.
- A second launch proved restart/repeat: it again reached interactive M00,
  recorded forward/look/Cross/Square at frame checkpoints, completed 894 frames,
  and self-exited through the same clean teardown within one second. Neither run
  required its safety-kill fallback; both ended `running=false`, no-sleep off,
  and all synthetic input released.
- Clean-session SHA-256 values are
  `7e688b37f3103f7009fee1f2abd07418adc38dcb17b1148647881fa2878c74b4`
  and `3145a860d94cc92d370e567d799ec7cf9c5f3eb404dfce5cb7f02f3dd4230b48`.
  Remaining v3.5 physical gates are pause behavior, collision/grounding,
  and observable action effects. Repeated-session soak remains a v3.9 gate.

### Original Combat pause candidate work unit

`[██████░░░░] 6/10 current evidence gates complete`

- Source trace identified the authentic owner: desktop
  `CombatGameModeClass::Combat_Keyboard` consumes
  `INPUT_FUNCTION_MENU_TOGGLE`, then suspends the original Combat game mode;
  the base `GameModeClass` already owns the state transition.
- The minimal Vita seam maps the currently unused Triangle button to the
  original menu-toggle key, keeps START as clean exit, and makes the direct M00
  loop obey `GameModeClass::Suspend/Resume`. During suspension it continues
  input, time, and local-network servicing while preserving the last original
  Combat frame because the desktop menu presenter is not yet linked.
- Focused dev6 validation passes: the exact changed boundary/direct-input
  sources compile normally and with ASan, the runtime-log/identity tests pass
  4/4, and the static pause contract passes 6/6. A fresh full host retail run
  was unavailable without copying retail data, so the canonical package
  honestly reuses the byte-identical completed dev5 host log SHA-256
  `9f9f544a0463e6b786a003957a3c117284d5c3498339efcd92af0a495964db53`.
- Canonical A3.5-dev6 build `20260824-013626` completed all 456 ARM actions and
  passed ELF/SELF/VPK inspection, the 15-check candidate-identity gate, VPK
  integrity, retail exclusion, and the diagnostics manifest. ELF SHA-256 is
  `2b820d533815a135db020804b287affe6521ecc68ff8dc0602e9c7e74c4473a2`,
  SELF SHA-256 is
  `293768e9d79769b9872e1ad9d472c66305310032c74727d6e08a1a444ad52360`,
  VPK SHA-256 is
  `929bdbcfbf10292f250c799faf74b254384482ddc1e8cb43d6d2b21e7f573bae`,
  and diagnostics ZIP SHA-256 is
  `6c597157e5462297dd1174830059710be348d9f78c17c6035fa227d2e03d4b43`.
  The VPK contains only `eboot.bin` and `sce_sys/param.sfo`, and its eboot is
  byte-identical to the verified SELF.
- Matching physical pause/resume evidence is pending; no dev5 physical result
  is transferred to the new executable. Nothing was deployed during build.
- Device preflight failed closed before staging: the paired physical Vita at
  its last address `.202` is offline. The only VitaCompanion endpoint currently
  visible at `.186` authenticates as the separate PS TV (`model=pstv`) and has
  no Renegade data tree, so it was not modified. The dev6 eboot swap and run
  wait for the target Vita to reconnect.

### Original collision and action-effects telemetry work unit

`[██████░░░░] 6/10 current evidence gates complete`

- The physical wait remains 30 seconds after the VitaGL logo, with a bounded
  45-second readiness timeout. The paired PS Vita was retried and remains
  disconnected; no fallback device or retail-data mutation was attempted.
- The existing capture schema had fields for player identity, transform,
  velocity, health, physics registration, and ground contact, but the
  interactive route populated only position and type. The boundary now samples
  those fields from the original `SoldierGameObj` and `HumanPhysClass` owners.
- A bounded first-frame/120-frame flight-recorder record also samples the
  original weapon definition, clip/total rounds, total rounds fired, trigger
  and fire state, plus original `ActionClass` count/active/busy state. This is
  observation-only and does not modify game, physics, weapon, or mission state.
- The capture comparator now accepts the already-current schema version 3 and
  reports player position/orientation/velocity/health/physics/grounding as a
  separate gameplay category. Its three unit tests pass; normal and ASan
  capture-writer self-tests pass; both changed translation units pass the ARM
  Vita ABI syntax compile; the first-mission skill validates; `git diff --check`
  passes.
- A3.5-dev6 remains frozen byte-for-byte for the pending pause run. The new
  telemetry source will be packaged as a separate candidate so physical
  evidence cannot be transferred between executables.
- Canonical A3.5-dev7 build `20260824-020540` completed all 456 ARM actions and
  passed the 15/15 identity gate, VPK inventory, retail exclusion, and
  diagnostic manifest. ELF/SELF/VPK SHA-256 are
  `6063c5eb2c5136ee4376fe6dc0b3944c54ce728ff7b59af76b90ffdaf6e62e21`,
  `7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5`,
  and `234139c2411fed7be8f2003a15ba015bc2270608ef8e3ec5406308e5c3c1443e`;
  diagnostics ZIP SHA-256 is
  `45d77a0378b0f06050263fda4ec602e2906e8b691cc9db3677a33c5d1b23bce2`.
  The VPK contains only eboot and SFO. No Vita deployment occurred.
- Input ownership was rechecked before automation: Cross -> `DIK_SPACE` ->
  original jump; Square -> `DIK_R` -> original action; Triangle -> original
  menu toggle; START -> clean exit. The stale build handoff text saying
  Square was reload is corrected for future packages without mutating the
  already retained dev6/dev7 artifacts.
- Added a candidate-scoped physical runner and independent log/state validator.
  The runner rejects non-PS-Vita identity, unknown installed executable hashes,
  stale readiness lines, and dev7 without an exact dev6 PASS receipt. It backs
  up the installed executable before replacement, restores it automatically on
  launch/readiness failure, uses a bounded 45-second readiness timeout, walks,
  looks, jumps, fires, attempts Square action at multiple positions, captures,
  exits with START, and unconditionally releases synthetic input. Focused pause
  and effects validator fixtures pass 2/2; the effects result explicitly does
  not infer visual correctness or environmental action success.
- The first live dev6-runner invocation at `20260824-072911` failed at the
  initial read-only status request with `DISCONNECTED` / no route to the exact
  PS Vita `.202`. It did not reach identity, application state, hash, backup,
  staging, replacement, launch, or retail data. The separate PS TV was not
  queried or modified. Offline receipt:
  `build/device-evidence/a3.5-dev6-pause-20260824-072911/status.json`.

### Original Mission00 native static provider work unit

`[██████░░░░] 6/10 current evidence gates complete`

- Replaced only the unavailable Windows script-DLL platform boundary with a
  native static provider. Original Combat `ScriptManager` remains the owner and
  now receives official `ScriptCommands`, `ScriptFactory`, `ScriptRegistrar`,
  `ScriptImp`, and `Mission00` implementations; no replacement mission system
  or asset format was introduced.
- Fixed the provider create-function binding to target the global official
  `Create_Script` implementation rather than recurse into `ScriptManager`.
  Focused provider tests pass 4/4, the current core-tool suite passes 52/52,
  diagnostics pass 29/29, zero-fuzz restaging is clean, and upstream is
  pristine.
- Canonical A3.5-dev8 build `20260824-031918` selected 430 unique original plus
  22 port translation units, completed all 463 ARM actions, passed 15/15
  identity checks, and contains the required create/registrar/M00 controller
  symbols. ELF/SELF/VPK SHA-256 are
  `3d4b1f56e82782d1958c9a82dd5f9f773ebd3f8046652caae4c8ecd01d9b4b21`,
  `7d944a8f0fe0425007cbb22b3ea039f8c173b64c4f8f6c4dce71a5670ee02c20`,
  and `86b00a0d4a07a2fde9bd1734934e9bb31bdae848a2d84da551545281ad8219ac`.
  The VPK contains only `eboot.bin` and SFO; no retail or device data changed.
- The candidate-scoped validator requires `provider_active=1`, registered and
  attached counts above zero, and capture `scripts_active=true`. The runner
  waits up to 45 seconds for the normal approximately 30-second readiness,
  then walks, looks, jumps, fires, attempts Square action, captures, exits with
  START, and releases every synthetic input.
- Physical evidence remains pending and the bar remains 6/10. The exact `.202`
  PS Vita is offline; dev8 may run only after exact dev6 pause and dev7 effects
  PASS receipts. No deployment was attempted.

### Direct Mission00 script-attachment closure candidate

`[███████░░░] 7/10 current evidence gates complete`

- Audited every literal original `Mission00.cpp` `Attach_Script` target. Fourteen
  are registered in Mission00 itself; the two missing provider dependencies are
  original `Test_Cinematic.cpp` and `Toolkit_Powerup.cpp`. Those two pinned
  EA/Westwood translation units are now linked unchanged beneath the existing
  Combat `ScriptManager`; the provider source contract proves all 16 literal
  attachment targets resolve and exactly 37 factories are compiled.
- GCC required one additional call-site-only bridge for the original MSVC
  function-pointer default in `Create_Explosion_At_Bone`. It supplies the
  omitted creator as `NULL`; the official source and ScriptCommands ABI layout
  remain unchanged. Focused ARM compile/link/package completed, then canonical
  A3.5-dev9 build `20260824-035114` completed all 465 actions.
- Dev9 selects 432 unique original plus 22 port translation units and passes
  15/15 identity, 54/54 core-tool, 29/29 diagnostics, SHA-256 manifest, archive,
  and independent candidate-provenance checks. ELF/SELF/VPK SHA-256 are
  `e5a7e0e379fba388945e02147feffa4bbbcec700e828bae7a41384b85285fa10`,
  `231fa510a9d39219df93aa2e4b442fe1cd0c9489c1f09f3596df63eea0bf0d88`,
  and `812baacb6bb482d8407fb0fc3ab33588af9a9f877cb5e4c305d790925529f8a5`.
  VPK inventory remains only `eboot.bin` and SFO; upstream is pristine.
- The offline physical gate now supports `dev9-m00-closure`. It retains the
  45-second readiness ceiling around the observed approximately 30-second load,
  performs the bounded requested walk/look/jump/fire/Square route only after
  original first-render readiness, and requires exactly 37 registered factories
  plus active attached scripts. Validator fixtures prove 37 passes and 36 fails.
- A fresh read-only `.202` status request at `20260824-090149` again returned
  `DISCONNECTED` / no route. No device identity, filesystem, app, or input
  operation followed; no deployment was attempted and physical acceptance is
  not claimed.

### Original mission-completion observer candidate

`[███████░░░] 7/10 current evidence gates complete`

- The authentic original path is `Commands->Mission_Complete(true)` into
  `CombatManager::Mission_Complete`. The direct Vita route previously had no
  `CombatMiscHandler`, so that terminal event had no lifecycle consumer.
- A3.5-dev10 installs a bounded Vita `CombatMiscHandler` immediately before
  original level pre-load, observes only original mission-complete and
  star-killed events after each original simulation frame, latches the first
  terminal result, and uninstalls before teardown. It does not call mission
  completion, mutate objectives, advance campaign state, or introduce a game
  loop.
- Canonical build `20260824-042339` passed 465 ARM actions, focused completion
  contracts, 15/15 identity, manifest and VPK checks, provenance, and retail
  exclusion. ELF/SELF/VPK SHA-256 are
  `01159d2cd4ed9dd9ac2999cb8a9d75085aada49e328c8ba587a5fddf17e76cb6`,
  `32eac8d6471d4a60689678dae854b1850682a700161a2e36c61301cfdff0d339`,
  and `7fb2d6f8df0ec1707303a2ce8a168e9dae86c799c91c01a802dee59e12e15090`.
- The new `dev10-completion-smoke` physical route requires an exact dev9 PASS
  receipt, waits up to 45 seconds around the corrected approximately 30-second
  VitaGL-to-playable load, then walks, looks, strafes, jumps, fires, attempts
  Square interaction, captures, and exits with START. Its validator requires
  exactly 37 factories, active scripts, `start_exit=1`, and no terminal mission
  event; the claim boundary explicitly excludes mission completion and visual
  correctness. All 60 tool unit tests and shell syntax pass.
- Read-only `.202` status at `20260824-093330` returned `DISCONNECTED` / no
  route. No deployment, filesystem, application, or input operation occurred;
  the evidence-gate count remains unchanged.

### Original M00 tutorial-control progress candidate

`[███████░░░] 7/10 current evidence gates complete`

- Static tracing confirmed that M00 intentionally disables player control
  during its opening tutorial conversation. The first original render frame is
  therefore a render-readiness marker, not proof that movement input is yet
  accepted by the original player owner.
- A3.5-dev11 adds a change-only, read-only flight-recorder sample of the
  original Star/control state, official ObjectiveManager IDs 1 through 6, and
  active ConversationMgr count after original simulation/render. It emits a
  dedicated automation handoff only when objective 1 is pending and the
  original player has control. It calls no objective, conversation, input, or
  mission mutator.
- Canonical build `20260824-043938` completed all 465 ARM actions and passed
  candidate identity 15/15, VPK/manifest integrity, linked-symbol inspection,
  provenance, retail exclusion, and the diagnostics bundle manifest. ELF/SELF/
  VPK SHA-256 are
  `706d94302bcde7df36a8506f1ead5928d766aa5e70371a5d4a62d284da65ff4f`,
  `ceb491c609c92657f63cf3cd978d4f7674f41d360cda86b657929210441681ad`,
  and `8cdbe4e289ffcf66e8ed5418255ccd8848484f485a4eb744d83c9638ee657c2e`.
  The VPK contains only `eboot.bin` and SFO; no retail data was copied or
  packaged.
- `dev11-progress-smoke` requires an exact dev9 PASS receipt, permits only the
  exact dev9 or dev10 installed predecessor hash, waits up to 45 seconds for
  first render and then up to 60 seconds for the original tutorial-control
  handoff, and only then performs the bounded walk/look/strafe/jump/fire/Square
  route. Its validator requires the same-session progress record and handoff,
  37 original factories, active scripts, a clean START-owned exit, and terminal
  completion/success/star `0/0/0`. Its claim boundary explicitly excludes
  mission completion, visual correctness, and environmental action success.
- The focused validator and completion contracts pass 11/11; full tool
  discovery passes 62/62 and shell syntax/diff hygiene pass. A fresh read-only
  `.202` request at `20260824-0949` again returned `DISCONNECTED` / no route.
  Nothing was deployed or written to the Vita, and the physical-evidence bar
  remains 7/10.

## 2026-08-24 — A3.5-dev6 physical original-Combat pause PASS

`[████████░░] 8/10 current evidence gates complete`

- The exact `.202` physical PS Vita returned online. Authenticated readback
  proved the installed dev5 SELF SHA-256 before replacement, retained a local
  hash-matched backup, and proved the installed dev6 SELF SHA-256
  `293768e9d79769b9872e1ad9d472c66305310032c74727d6e08a1a444ad52360`.
  Only `ux0:/app/RNEGA3101/eboot.bin` changed; the retail M00 archive remained
  byte-identical and no retail path was written.
- The physical dev6 session reached original first-render readiness, then
  original Combat suspended and resumed at frame 206 with identical player
  position `(-58.328,-41.527,0.588)` while 316 paused input frames were
  serviced. The bounded post-resume walk/look/strafe/jump/fire/Square route
  moved the player to `(-54.177,-19.666,0.810)` before the clean START exit.
- Completion recorded 1,334 frames, `render_error=0`, teardown complete,
  pause/resume `1/1`, clean lifecycle END, app stopped, all synthetic inputs
  released, and sleep restored. The independent validator PASS is
  `build/device-evidence/a3.5-dev6-pause-20260824-130016/gate-validation.json`;
  its runtime log, final state, and receipt SHA-256 values are respectively
  `a6087cb07ee259e46786ec0a3e78d2ef3ad1ade249e22ad9f2aa977bea0a7416`,
  `303ff04a57670b69974714f07518e8f452c0dc3a457fba99c4cf64fc3839733b`, and
  `3d173c3fd77be1fd9dfe14cb4d8d6d26899617c88e30d3311203e490840487af`.
- This is telemetry-backed original pause stability and post-resume movement,
  not a visual-correctness or environmental-action claim. Dev7 remains the
  next physical collision/action-effects gate and is admitted only by this
  exact PASS receipt.

## 2026-08-24 — A3.5-dev7 input-provider isolation and physical visual report

`[████████░░] 8/10 current evidence gates complete`

- Four bounded full-route runs of the exact dev7 SELF rendered and exited
  cleanly, proved original physics registration, grounding, movement, and the
  Square raw bit, but did not receive the external synthetic R-trigger bit in
  the same sessions. The final retained run is
  `build/device-evidence/a3.5-dev7-effects-20260824-132016/`; its runtime log,
  state, and receipt SHA-256 values are respectively
  `7d32500eb97a0084e28a5fd6ecd74a26d80b4397388800cad6727904f7955569`,
  `ffb0f46ac3c202675cfbb7189290ffb9e6fbb4c4f7fa413c500552d288dc1103`, and
  `88cf796f6408414a747e06f131d7193a7757907de48eb6b40eed2b0aea746abf`.
- A separate exact-dev7 isolated probe retained under
  `build/device-evidence/a3.5-dev7-input-probe-20260824-131124/` delivered raw
  `0x00000200` for R and advanced the original weapon fired count from 0 to 17.
  This proves the VitaSDK mapping, DirectInput button B binding, and original
  weapon path; it does not combine with another session to pass dev7. Further
  repeats of the nondeterministic external route are stopped.
- Physical user observation after the approximately 30-second load: Havoc's
  first-person forearm/hand is absent or misplaced while the wristband and
  pistol remain visible, and NPC bodies are invisible while rigid weapons,
  headgear, belts, and boots remain visible. This is recorded as a physical
  visual defect, not inferred from telemetry. The shared boundary under
  investigation is original skinned-mesh deformation at Vita submission;
  retail repopulation is not indicated by the attachment evidence.
- The next candidate will keep original Input/Combat ownership while adding a
  bounded, versioned raw-controller route recorder/replayer at the existing
  DirectInput platform boundary. It will also restore original deformed skin
  vertices and identity-world submission beneath WW3D. VDB remains the
  preferred external injector when its negotiated server capability permits;
  the native recording is intentionally provider-independent.

## 2026-08-24 — A3.5-dev12 skin and deterministic-route hardware candidate

`[████████░░] 8/10 current evidence gates complete`

- Source comparison found one shared platform-boundary defect matching both
  physical observations: the Vita mesh path submitted undeformed model-space
  vertices and the mesh world transform for `SKIN`, while the original DX8
  skin container obtains HTree-deformed positions/normals and submits them
  under identity world. A3.5-dev12 restores exactly those original semantics;
  rigid meshes and original scene/animation ownership are unchanged.
- Added bounded counters and first-use breadcrumbs for skinned submissions,
  deformed vertices, allocation/deformation failures, and identity-world use.
  This can prove the corrected path executed but cannot prove visual
  correctness without a returned physical capture and user observation.
- Added a version-1 controller route below the original DirectInput API: eight
  bytes per sample, maximum 18,000 samples, FNV-1a payload checksum, exact file
  length/header validation, temporary-file sync/rename commit, invalid-route
  rejection, and live physical START emergency abort during replay. Exact
  one-shot marker files select record or replay; conflicts fall back safely to
  passthrough and are logged. Original Input/Combat owns all bindings/actions.
- Focused route/skin/runner tests pass, complete tool discovery passes 74/74,
  renderer lifecycle remains 11/11, shell/Python syntax passes, affected host
  units compile, and upstream is pristine. VDB capability negotiation remains
  first choice; VitaCompanion is admitted only for hash-guarded writes when VDB
  advertises no write capability.
- Canonical build `20260824-083354` completed all 465 ARM actions and passed
  ELF/SELF/VPK identity, exact VPK inventory, retail exclusion, archive test,
  SHA-256 manifest, and diagnostics bundle validation. ELF/SELF/VPK SHA-256 are
  `cbf956dbd001ef13dd94da465ef756d69f882bcfb8b25d621045065f905dd1d0`,
  `805b853e737c884acc9f590a3c5793f9ba6f32f5ff80542454919bf1d2750b99`,
  and `86f08c02dab2829e9ef7e25c12983313c1eb3664d2d9a3aeebaf962ff037e284`.
  The VPK contains only `eboot.bin` and SFO. No device was accessed by the
  build.
- The one-shot physical runner is bound to the exact dev7 predecessor and
  dev12 candidate hashes. It backs up before replacement, verifies the retail
  M00 hash before/after, waits for original first-render and tutorial-control
  handoff, records the user's requested 30-second walk/interact route, returns
  log/route/capture, and then replays only the checksum-verified route. Physical
  record/replay and visual acceptance are pending; the evidence bar remains
  8/10.
- The first record attempt failed closed before launch because the current VDB
  debugger is read-only and VitaCompanion supports upload but the CLI's native
  `touch` requires VDB write capability. No marker or route was created. Retail
  M00 readback SHA-256 was
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`.
  Receipts prove dev12 was staged and then exact dev7 SELF SHA-256
  `7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5`
  was restored before exit. The runner now uploads a zero-byte marker through
  the negotiated, hash-verifying VitaCompanion file-write path; generic exact
  file removal remains available for failed-start cleanup.

## 2026-08-24 — A3.5-dev12 physical skin pass and indexed-sky diagnosis

`[████████░░] 8/10 current evidence gates complete`

- Physical dev12 observation confirms ordinary NPC body skins now render. The
  retained runtime reached frame 4,800 with 67,209 original skinned-mesh
  submissions, 13,343,536 HTree-deformed vertices, zero deformation failures,
  and zero renderer backend errors. This physically accepts the shared NPC
  deformation correction, but not the whole candidate.
- The same physical session reports Havoc's arm/pistol absent and the sky
  entirely black. Matching logs show dev12 has no selected weapon from frame 0
  onward, while dev7 had `Weapon_Pistol_Player` and exactly four additional
  meshes (250 vertices / 279 triangles). Original `MTU_Commando::Created`
  deliberately deselects the weapon and original Mission00 selects the pistol
  only after Logan's poke instruction. This is authentic tutorial state, not a
  skin regression; no platform-owned weapon grant is admitted.
- Source tracing found the independent sky defect at the existing DX8 boundary:
  original Haze, Starfield, CloudLayer, sun and moon use dynamic indexed draws,
  but the Vita draw bridge submitted their geometry without consuming the
  deferred original `ShaderClass` and stage-0 `TextureClass`. The narrow repair
  applies those original owners immediately before indexed submission and
  records indexed state-application telemetry. No custom sky or asset format is
  introduced.
- The route runner now recognizes the observed original `star/control=1/1`
  handoff instead of waiting for objective 1 to be pending. The six objectives
  are correctly hidden (`OBJECTIVE_STATUS_HIDDEN == 3`) at the opening state.
  Exact dev7 was restored after the failed visual candidate; no route or marker
  remains on the device.

## 2026-08-24 — A3.5-dev13 pre-build lifecycle closure

`[████████░░] 8/10 current evidence gates complete`

- The indexed sky-state correction passes its focused contract and the native
  renderer lifecycle remains 11/11. Physical sky correctness is still pending;
  host evidence cannot accept the visual gate.
- Clean staging of the original Scripts pool exposed and corrected the original
  mismatched `new[]`/`delete` parameter-array lifetime without changing script
  ownership or importing a replacement provider.
- Strict LeakSanitizer then identified a disabled-teardown lifecycle gap:
  original object destruction detached scripts into `PendingDestroyList`, but
  the disabled `Post_Think` path never drained that queue. `Destroy_All` now
  completes the original pending-script lifecycle after object deletion.
- Headless validation no longer allocates presentation-only powerup icons when
  the original HUD render resources were never initialized. This guard does not
  affect the Vita HUD path, where both original powerup renderers exist.
- The focused strict-ASan run completes two authentic M00 load, 120-frame
  render, and teardown cycles with zero AddressSanitizer/LeakSanitizer findings.
  Fresh canonical host ASan/LeakSanitizer, targeted UBSan, M00/M01/City routes,
  deterministic staging, and complete tool discovery 81/81 pass.
- Canonical build `20260824-093614` completed all 465 ARM actions and passed
  candidate identity, ELF/SELF/VPK inspection, retail exclusion, archive,
  SHA-256 manifest, and diagnostics validation. ELF/SELF/VPK SHA-256 are
  `d3b7d69e40f1968a9beda0b46312c0609d73522b8ce30799cecb169a352d8b1b`,
  `5c254b8a914a603baca2c9b343bb075df58c7d05ed05448db267f2d599a14555`,
  and `7f7e31b37afff79ea1ab662cd9afc5d0e366f9252be6dd236b2ac8fabdf5d63d`.
  The VPK contains only eboot and SFO; no device was accessed by the build.
- The physical runner is now bound to exact dev7/dev13 executable hashes and
  waits for original `star/control=1/1`. Physical record/replay, sky observation,
  and Havoc viewmodel observation after Mission00 grants the pistol remain the
  two uncompleted evidence gates.

## 2026-08-24 — A3.5-dev14 candidate and TT reuse closure

`[████████░░] 8/10 current evidence gates complete`

- Dev14 passed the canonical 465-action ARM build and exact ELF/SELF/VPK,
  manifest, symbols, diagnostics, VPK-inventory, and retail-exclusion gates.
  It restores original background creation, original material/DCG color and
  opacity, bounded conversation state diagnostics, and safe absent-dazzle
  handling. Physical visual and mission acceptance remain pending.
- The official TT 4.8.4 revision-9000 archive/diff remain out of tree and are
  MD5+SHA-256 pinned. The audit now proves five TT/EA equivalences, adding the
  audio callback contract and complete retail audible-definition schema to
  the prior chunk, line-segment, and timer checks. It machine-records TT's
  unqualified dependent-base calls and missing-return WWAudio header defect;
  no Windows/Miles audio boundary or TT runtime source is imported.
- Focused TT and route-runner validation passes 9/9. The unattended runner now
  restores exact dev7 after any failed deployed session, including failures
  after readiness. Read-only Vita admission verified app stopped, dev7
  installed, the retained route SHA-256 `39d915e02611079b29fb43cb2ea11ede583b063745e9675efe15010c606b7cf8`,
  and unchanged retail M00 SHA-256
  `84f14f6267dd8a88563b3d31540bf857df0b8e111144944cb582edd246f2d438`.
- No candidate was deployed because the current contract forbids automatic
  Vita filesystem mutation. The replay remains prepared; work continues on
  the native audio provider beneath original WWAudio ownership using dev13's
  physical `sound_scene=null` and deferred-sound evidence.
