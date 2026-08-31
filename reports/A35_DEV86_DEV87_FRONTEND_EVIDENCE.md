# A3.5-dev86 returned frontend evidence and dev87 decision record

## Evidence boundary

Dev86 is a retained physical usability failure. Its canonical VPK, ELF, and
packaged SELF SHA-256 values are respectively
`9a9f36c15f699b72e736f2b2a4b29d4e57537e59c3cfeb5b41f206884b85aa10`,
`954be81d22f9c0ec527549b84b39ce9e87e5ed61eddcd130b74ac53021ec540d`, and
`3b20079eca192cdf2d5869fbc3bfb485ec0528cfa2969f006a60f9567b44b4a8`.
The matching returned runtime log is
`build/device-evidence/a35-dev86-user-return-20260831T011721Z/a35-dev86-runtime-user-report.log`
with SHA-256
`2294297c434034fee78c0d92285346cb913265b501fb7793217b640c739cb9c4`.

The user reports that the EA intro remains very slow with buzzy/laggy audio and
that the main-menu labels are missing. The log proves original `MovieGameMode`,
BINK, main-menu, loading-screen progress, M00 prewarm, and original player
control paths executed. It does not prove visual correctness. The single
returned gallery item is
`docs/history/screenshots/a35-dev86-vita-original-loading-screen-level-ready-t119137636-annotated.png`
(SHA-256 `442d1b504d4123b7736df8451334f6053d544f0efcdf3b48bb18443e64194d79`).
It is explicitly an `original-loading-screen`/`level-ready` diagnostic image,
not a menu or gameplay acceptance image. No finalized video was returned.

## Measured BINK baseline

For `EA_WW.BIK`, dev86 recorded 22,976 ms wall time and 202 frames. Audio
decode totals 671,221 us (59,507 us worst); video decode totals 1,561,800 us
(20,009 us worst); and video upload totals 13,476,510 us (68,901 us worst).
The provider also reports 10,893 audio waits. The ratio makes the per-frame
Vita upload the leading measured movie cost. This is an inference from the
matching runtime log, not a claim that it is the only source of A/V defects.

`R_INTRO.BIK` shows the same ordering over its 19 user-skipped frames: audio
decode 43,209 us, video decode 160,563 us, and video upload 1,243,660 us
(67,570 us worst).

## Dev87 bounded changes and decision

1. Original `Render2DSentence` creates procedural A4R4G4B4 glyph textures and
   copies glyph data through texture surfaces. The Vita-only `TextureClass`
   constructor had not allocated its `D3DTexture`, leaving these original
   surfaces unavailable. Dev87 routes this constructor through the established
   Vita `DX8Wrapper::_Create_DX8_Texture` allocation path; unsupported desktop
   `DX8TextureManager` tracking remains excluded on Vita. This preserves the
   original UI/glyph owner and targets the missing labels.
2. The BINK boundary changes only the *in-memory decoded upload* to RGB565.
   Its padded 1024x1024 upload changes from 4 MiB RGBA to 2 MiB RGB565 per
   frame. No retail BIK is converted, changed, packaged, or uploaded.

Risk: RGB565 can introduce visible color quantization/banding; the original
movie timing and ownership remain the acceptance criteria. The source is
adopted only as a candidate pending hardware visual/A-V evidence. There is no
after-performance result yet.

## Readiness/pre-cache scope

Current startup pre-cache indexes original archives and reads bounded small
slices; later it warms one loading-screen frame and 60 M00 scene frames. It
does not retain a frontend glyph atlas, BINK decoder, or BINK upload surface.
A subsequent readiness change must establish a real persistent owner and
measure boot time, memory high-water, and subsequent movie/menu behavior.
Blindly reading or fully decoding retail movies before the frontend would add
startup latency and memory pressure and is rejected for now.

## Validation status

`tools/build_fast_candidate.sh` passed 89 focused contracts, deterministic
staging, ARM link, ELF/SELF/VPK identity, compressed archive integrity, and SHA
verification in `logs/a35-dev87-fast-20260830-204232-build.log`. Dev87 fast
VPK SHA-256 is
`7e108cffe2c5c858be66136ab0c0498c3c1ee1377aad6dbf513abf0bbbf60185`.
Canonical validation now passes in `logs/a35-dev87-20260830-204706-build.log`:
retained host/current contracts, deterministic 136-patch staging, 549
ARM/package actions, original-runtime symbols, ELF/SELF/VPK identity,
compressed archive, SHA manifest, diagnostics, and retail exclusion. Canonical
VPK/ELF/SELF SHA-256 values are respectively
`bbb48f91c879c99e2944497b97a56cbf1e015c7af4a20ed75871bf02bb86e521`,
`cd50c8a7c1c406bf324996d09fe74755e757230619ac003099bf103d9b829194`, and
`d7bdadbff7296dad0d5460d0febfe70116502c9a80695bfa3577f6c629f9c596`.
Source/report publication is complete at `origin/main` commit
`015c83bde9653fc9bfc58f1a731eb2492e351558` (`Fix dev87 frontend glyphs and
BINK upload`). The commit contains source, focused tests, sanitized reports,
and the explicitly diagnostic gallery PNG; VPK/ELF/SELF, logs, raw captures,
video, dumps, retail data, saves, and credentials remain excluded. Future
explicitly authorized physical validation is still pending.

## Dev87 returned frontend failure and Dev88 correction

Dev87 is no longer a pending physical observation. The user reports that its
main-menu text is still missing, intro playback remains very laggy with buzzy
audio, and the original grey gameplay dialogue box is present but its subtitle
text is empty. The retained partial runtime log is
`build/device-evidence/a35-dev87-user-return-20260831T022728Z/a35-dev87-runtime.log`
with SHA-256
`a01c0b54159fefa2fa4c4ebefdaf181f11330f23e0287f2b426e7cbb1eac911c`.
It reaches original main-menu activation and contains partial BINK timing, but
ends before M00 dialogue breadcrumbs. Thus it does not establish whether a
translated dialogue string was available; it does establish that the reported
blank subtitle cannot be called fixed. User-taken screenshots are expected and
must be pulled from title-scoped locations, reviewed, accurately labelled, and
added to the generated gallery/timeline before publication.

The shared concrete renderer lead is now fixed locally in Dev88. Original menu
entries use `Render2DSentence`; original `MessageWindow` owns a
`TextWindowClass` for the gameplay dialogue box. Both render glyph quads through
the same original `Render2DClass::Render` dynamic indexed submission. The Vita
boundary previously applied blend/depth state there but not the original
per-stage texture combiner state. A glyph atlas could therefore inherit a
preceding mesh's incompatible alpha rule even when it had valid pixels. Dev88
supplies the stage-0/stage-1 texture-presence contract to
`Apply_Indexed_Shader_State` and applies the original texture-stage state
before the draw. This retains original UI, dialogue, translation, and renderer
owners; it does not add a replacement subtitle path.

The Dev87 partial BINK telemetry showed 33–59 ms worst upload/decode work while
the previous one-buffer audio startup reserve represented only about 21 ms.
Dev88 raises the reserve to three real 1024-frame stereo buffers, about 64 ms
at 48 kHz, before starting the Vita audio output worker. This is an inference-
driven buffering correction for starvation/buzz, not an artificial-silence
workaround and not retail movie conversion. Dev87's RGB565 in-memory upload
change remains otherwise intact; retail BIK files remain unchanged.

Dev88 focused contracts passed 54/54 and `git diff --check` passed. Its
canonical local-only closure in `logs/a35-dev88-20260830-214253-build.log`
passed retained host validation, 115 current contracts, deterministic 136-patch
staging, 549 ARM/package actions, original-runtime symbol, identity, archive,
diagnostics, and retail-exclusion checks. VPK SHA-256 is
`be78097b98a3c0a0e9e9cd1fbdb0d5cdb9d7d630145bec8736d7ebad0cf07138`; packaged
SELF is `cd5726251dbdd33c2d19a97aa83ccc95d992ad6800c945497ec473fe40228fce`.
No Dev88 artifact has been copied to, installed on, or launched on the Vita.
