# Level-data audio readiness: M04, M09, M10, M11

Evidence class: host source review plus read-only retail metadata scan. Nothing
here is a physical-Vita, Vita3K, decode, or audibility result. No C++ was built
or run for this report; no retail bytes were written, exported or committed.

Reproduce (read-only, Python only):

```sh
python3 -m tools.audit_level_static_sounds --data "$RENEGADE_RETAIL_ROOT" --definitions \
    --output reports/generated/sweeps/level_static_sounds.json
python3 -m unittest tools.test_audit_level_static_sounds
```

## Verdict

For the four missions, every level-data audio reference that the original
loader reaches (static sounds in the `.lsd`, background music in the `.ldd`)
resolves in the archives the Vita runtime mounts, uses a format the Vita
provider admits, and stays inside the original preload thresholds. No defect
was found that needs a source fix for these four levels. Two provider/engine
observations that affect fidelity or other levels are listed under "Open
observations"; neither was changed because they cannot be compiled or
listened to in this task.

## How level audio reaches the Vita provider (original path, unchanged)

Level audio lives in two original subsystems:

| Source | Chunk | Original owner | Content |
| --- | --- | --- | --- |
| `.lsd` | `0x30005` > `0x10291220` > `0x101` | `StaticAudioSaveLoadClass` / `SoundSceneClass::Load_Static` | One persisted `Sound3DClass` (`0x30003`) or `SoundPseudo3DClass` (`0x30004`) per placed ambient emitter |
| `.ldd` | `0x3C51C461` > `0x30006` > `0x10291222` | `DynamicAudioSaveLoadClass` | Logical-listener global scale and background music file name; the dynamic scene chunk is empty (0 bytes) in all four |

Flow, all in `staging/wwaudio` (original files plus the existing a35/a36
hardening patches):

1. `Load_Level` (`staging/combat/savegame.cpp`) loads the `.lsd` through the
   registered subsystems; `StaticAudioSaveLoadClass::Load` requires a sound
   scene, then `SoundSceneClass::Load_Static` runs in batch mode.
2. Each sound chunk is turned into an object by its `SimplePersistFactoryClass`
   (`Sound3DClass::Load` > `AudibleSoundClass::Load`). The persisted record
   carries a bare file name (no definition ID), volume, drop-off, loop count,
   transform, and Sound3D max-volume radius.
3. `AudibleSoundClass::Load` calls `WWAudioClass::Get_Sound_Buffer(name, is_3d)`.
   That goes through `_TheFileFactory` (the Vita FileFactoryList: loose Data,
   Always2.dat, always.dbs, always.dat, the selected mission MIX), then
   `Create_Sound_Buffer`, which preloads a file unless it is larger than the
   2D/3D limit (20,000 / 200,000 bytes; `DEF_MAX_3D_BUFFER_SIZE` 100,000 is
   doubled in `WWAudioClass::Initialize`). Larger files become
   `StreamSoundBufferClass`.
4. `Add_To_Scene(true)` registers each sound with the static cull tree
   (`StaticSoundCullObj`, AABox of the drop-off radius), `On_Frame_Update(0)`
   culls/starts them, and `Sound3DHandleClass::Initialize` hands the raw buffer
   and its true length to `AIL_set_3D_sample_file_bounded` (the a35 bounded
   patch), which decodes into the Vita provider sample.
5. `DynamicAudioSaveLoadClass::Load` calls `Set_Background_Music(name)`, which
   creates a TYPE_MUSIC 2D sound with infinite loops; the file is large, so it
   is a streaming buffer and uses the same `AIL_open_stream` /
   `Open_Mpeg_Playback` route that already played `menu.mp3` on hardware.
6. Combat's `SoundEnvironmentClass` is not data driven. It ray-casts upward from
   the camera and checks `GameObjManager::Is_In_Environment_Zone` (script zones
   flagged as environment zones) to produce a 0/0.5/1 amplitude, which only
   scales the two weather loops `Wind01` and `Rainfall01` (2D definitions,
   `wind01.wav` 215,186 bytes and `rainfall01.wav` 112,770 bytes, both
   streaming 2D buffers, both present in always.dat). No audio file or
   provider capability is involved beyond a plain 2D stream.

## Static sound inventory (retail unchanged, read-only)

All files resolve in `always.dat` (nothing needs the mission MIX or the loose
Data directory). Every saved name is a bare file name; no Windows path
component is present. All sounds are type "effect"; `loop_count` is 0
(infinite loop in the original and in the provider) for every sound except one
single-play sound each in M10 and M11.

| Mission | Static sound instances | Sound3D / Pseudo3D | Unique files | Largest file | Drop-off range (m) |
| --- | ---: | --- | ---: | ---: | --- |
| M04 | 51 | 43 / 8 | 22 | 180,394 B (`wndhigust1.wav`) | 10 to 70 |
| M09 | 123 | 119 / 4 | 25 | 180,394 B | 10 to 80 |
| M10 | 171 | 137 / 34 | 41 | 180,394 B | 6 to 80 |
| M11 | 116 | 101 / 15 | 38 | 180,394 B | 8 to 50 |

Formats of the unique files (WAVE tag, channels, rate, bits):

| Mission | PCM 8-bit mono 22050 | PCM 16-bit mono 22050 | IMA ADPCM mono 22050 | IMA ADPCM mono 11025 | IMA ADPCM stereo 22050 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M04 | 14 | 2 | 1 | 4 | 1 (`amb_water_st.wav`, Pseudo3D) |
| M09 | 18 | 3 | 4 | 0 | 0 |
| M10 | 30 | 2 | 6 | 3 | 0 |
| M11 | 29 | 0 | 8 | 1 | 0 |

Checks applied to every unique file with the same rules as
`tools/audit_mission_wave_headers.py` (strict, i.e. the playback header mode of
`Inspect_Wave`) plus the preload threshold:

- No strict header findings (no oversized RIFF declaration, no chunk outside
  RIFF, no invalid format, no bad ADPCM step index or predictor).
- All tags are 1 or 17, channels 1 or 2, rates 11025 or 22050: inside the
  provider limits (`tag` 1/2/17, 1..2 channels, 8000..192000 Hz,
  decoded ceiling 16 Mi samples, 64 MiB image ceiling).
- Every 3D file is at most 180,394 bytes, below the 200,000-byte stream
  threshold, so every static sound gets a raw buffer and a normal 3D sample.
  No level static sound takes the `StreamSoundBufferClass` route.
- The one stereo file is a `SoundPseudo3DClass`. The provider mixes stereo
  PCM on a spatial sample (`Mix_Pcm_Voice` with stride 2, same distance gain
  on both channels), so it is admitted, not rejected. The tool flags it only
  as a review item.
- Independent evidence: `reports/ALL_ARCHIVE_WAVE_SWEEP.md` already decodes
  all 10,241 WAV entries in the 31 archives with the host C++ decoder under
  sanitizers with zero rejections. The 265 strict-header findings in
  always.dat are not among any M04/M09/M10/M11 level sound.

## Background music

| Mission | File (always.dat) | Bytes | MPEG header walk |
| --- | --- | ---: | --- |
| M04 | `04-ambient industrial.mp3` | 3,801,885 | MPEG-1 Layer III, 44.1 kHz stereo, CBR, 9,096 frames, ~237.6 s |
| M09 | `09-sneakattack.mp3` | 3,643,344 | same class, 8,717 frames, ~227.7 s |
| M10 | `10-stomp.mp3` | 2,781,228 | same class, 6,654 frames, ~173.8 s |
| M11 | `11-ambient beach.mp3` | 2,860,641 | same class, 6,844 frames, ~178.8 s |

All four are CBR (one bitrate), no ID3 header, no Xing/Info/VBRI header, zero
resync bytes, rate 44,100 Hz (provider limit 48,000), 2 channels. They are the
same container class as `menu.mp3` (1,477,848 bytes, 44.1 kHz stereo), whose
native playback was observed on hardware (`DEV120_ORIGINAL_LOADING_AND_MENU_AUDIO.md`).
They are larger, so the stream open reads 2.8 to 3.8 MB and `Open_Mpeg_Playback`
keeps its own encoded copy and runs `mpg123_scan` over 6,600 to 9,100 frames;
transient peak is roughly 2x the file size (under 8 MB) and steady state one
copy. This is a cost and stall question already tracked in
`MPEG_DECODE_COST.md` and `AUDIO_STREAM_MEMORY.md`, not a format rejection. The
libmpg123 decode of these exact files was not run here.

## Script-created sounds in these missions

A second scan took every literal `Commands->Create_*Sound("name")` call in
`Mission04.cpp`, `MissionX0.cpp` (shared with M04), `Mission09.cpp`,
`Mission10.cpp` and `Mission11.cpp` and resolved the name against the 10,004
sound-definition records in `always.dbs/objects.ddb`.

- None of these literal sounds is a 3D definition larger than 200,000 bytes.
- `Twiddler` names (for example `M11_Exterior_GDITank_Twiddler_JDG`,
  `M04_Havoc_Affirmative_Twiddler`) are `Twiddler` definitions (persist chunk
  `0x102`), not plain sound definitions; the original `twiddler.cpp` is part of
  the selected sources. They are not data defects.
- Three referenced sound definitions point at WAV files that exist in no
  retail archive on this Data directory (including `always3.dat` and every
  mission MIX): `Steam_Med_Pressure_01` and `SFX.Steam_Med_Pressure_01_offset1`
  (M04, `steam_med_pressure_01.wav`), `Air_Compressor_01` (M11, four calls,
  `air_compressor_01.wav`), and `Mutant_Heal_Cry` (M11, `mutant_idle02.wav`).
  The original reports "Sound not found" and returns NULL; scripts do not
  require the sound. These are retail data gaps, identical to the PC Data
  directory this was copied from, so they are expected silence, not a Vita
  defect. Do not substitute content.
- M09 has no literal script-created sounds; its audio is the 123 static
  sounds plus music.

## Open observations (not changed)

1. **3D sounds above 200,000 bytes have no raw buffer (original behavior,
   other levels/events).** `StreamSoundBufferClass::Get_Raw_Buffer()` is NULL,
   `Sound3DClass` always uses `Sound3DHandleClass`, and the provider rejects a
   NULL image (`Decode_Into_Sample`: "invalid or oversized WAVE image"). The
   result is a silent sound plus a debug line, not a crash. In
   `objects.ddb` 56 definitions flagged 3D are larger than 200,000 bytes
   (examples: `Explosion_Large_05/07/09` at 218 to 253 KB, `Thunder03`
   266 KB, `Ambient_Screams_03` 274 KB, `Ocean_Heavy_Surf_03/04`, plus M00 and
   idle-dialog voice definitions up to 531 KB). None is referenced by a
   literal script call or static sound in M04/M09/M10/M11, so these four
   levels are unaffected, but large explosions and some ambience elsewhere
   would be silent. Nothing in upstream calls `Set_Max_3D_Sound_Buffer`, so
   retail PC used the same thresholds; whether PC audibly played them is not
   established here. A candidate (not adopted) is a Vita-side
   `Set_Max_3D_Sound_Buffer(600000)` after `Initialize`; it changes memory
   behavior (preloading up to 531 KB images, 4:1 ADPCM decode to PCM) and
   needs a measured decision and a listening check.
2. **Spatial samples ignore stereo placement.** Commit `0fda496` makes
   `Mix_Locked` use center pan for any `spatial` sample, while
   `AIL_set_3D_position` still computes a pan from the listener-space X value
   (`x / max_distance`) that is now unused. All 3D level emitters (the 51 to
   171 static sounds per level) therefore get distance attenuation only, with
   no left/right localization. The earlier formula was a weak approximation
   (it normalised by the drop-off radius, not the actual distance), so a proper
   fix would pan from the azimuth (`x / distance`) rather than restore the old
   line. Candidate for a later, listening-validated change with an updated
   `vita_audio_mixer_equivalence_test`.
3. **always3.dat is not mounted** by the original `Game_Init` (it mounts
   Always2.dat, always.dbs, always.dat and `data\*.mix`) or by the Vita file
   factory list. Its 23 WAVs are not referenced by M04/M09/M10/M11 level audio.
4. **Retail definition leftovers.** 66 sound definitions reference files that
   exist in no archive (editor paths such as `e:\commando\assets`, jump/land
   and walking foley such as `jumpland1.wav`, `mudwlk1.wav`,
   `sniper_rifle_fire.wav`, mission 05 dialog). They fail soft in the original
   loader and are not mission-4/9/10/11 level data.

## Not verified here

- Native decode and audible playback on Vita or Vita3K of any file above.
- The libmpg123 scan time and memory for the four music files.
- Whether the static emitter count (up to 171 in M10) fits the provider's
  sample-slot and CPU budget when many are in range at once; only culling by
  drop-off radius limits the audible set.
- Name resolution precedence if a mission MIX duplicates an always.dat sound
  (none of the 86 distinct level sound names across the four missions, 126
  per-mission unique entries, exists in more than one mounted archive).

## Files added

- `tools/audit_level_static_sounds.py`: read-only parser and auditor for the
  static-sound chunks, dynamic-audio variables, file resolution in mount order,
  provider-admission and preload checks, an MPEG frame-chain walk, and an
  optional `objects.ddb` sound-definition scan.
- `tools/test_audit_level_static_sounds.py`: synthetic-data tests (no retail).
- `reports/generated/sweeps/level_static_sounds.json`: public metadata receipt
  (names, sizes, formats only).
