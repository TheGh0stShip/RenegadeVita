# Dev84 Demo Recording

USB capture is not the default demo path for this project. It does not cover
PSTV and it is a poor fit for handheld charging during long tests.

The supported non-USB workflow is a title-scoped Vita recorder plugin that
captures locally to `ux0:video`. The Renegade VPK remains unchanged, and retail
data is not packaged or copied.

## Build The Recorder

Run this from the bash workspace:

```bash
bash ./tools/build_renegade_demo_recorder_plugin.sh
```

This fetches pinned Vita-MP4-Recorder source commit
`60c966a75356ea9a95f79479a3e647283586cf11`, applies the Renegade patch under
`tools/vita_plugins/renegade_demo_recorder/`, and writes:

```text
dist/RenegadeDemoRecorder-A3.5-dev84.suprx
dist/RenegadeDemoRecorder-A3.5-dev84.skprx
dist/RenegadeDemoRecorder-A3.5-dev84-tai-config.txt
dist/RenegadeDemoRecorder-A3.5-dev84-SHA256SUMS.txt
```

The recorder requires the `SceLibMp4Recorder` stubs in VitaSDK. If the
installed SDK does not ship `psp2/mp4rec.h`, the build uses the narrow
compatibility header under `tools/vita_plugins/renegade_demo_recorder/include/`
for this helper only. Set `RENEGADE_VITASDK` if your default SDK is missing the
`SceLibMp4Recorder` stubs.

The generated plugin is scoped to title ID `RNEGA3101`. It enables audio by
default, starts recording when the Renegade process loads, and finalizes the
MP4 on the first Start press. If the process exits without that input, module
stop finalizes any active recording as a fallback.

Current active-workspace build evidence:

```text
RenegadeDemoRecorder-A3.5-dev84.suprx       8a856e76b99654b1d21fde65b8040c41cc29225da91076631b5ee76be564270d
RenegadeDemoRecorder-A3.5-dev84.skprx       e8a695c08fe348ab8cb1b16f2264fe67d593c3e82a7e61629f61f04d9e88eba5
RenegadeDemoRecorder-A3.5-dev84-tai-config.txt 75e6f69f9690fd89689cd90be32357113d989be69770ea587cfefc546637d9b5
```

## Manual Install

Copy the generated `.skprx` and `.suprx` to `ur0:tai/` and add the generated
tai config snippet to the active tai config:

```text
*KERNEL
ur0:tai/RenegadeDemoRecorder-A3.5-dev84.skprx
*RNEGA3101
ur0:tai/RenegadeDemoRecorder-A3.5-dev84.suprx
```

Reboot after changing tai config. Keep this title-scoped to `*RNEGA3101`; do
not install it under `*ALL`.

## Run A Recorded Session

After the recorder plugin is installed and dev84 is installed from VitaShell:

```bash
bash ./tools/run_dev82_recorded_demo_session.sh
```

The plugin starts recording as soon as Renegade loads. Play the demo normally.
Press Start when done. The app exits, the plugin finalizes the MP4, and the
script pulls the dev84 runtime log into `build/device-evidence/`.

The MP4 is written under `ux0:video` and imported into the Vita Video app by
the recorder. Copy it off the Vita with VitaShell FTP or the device's normal
media workflow after the run.

## Evidence Boundary

This is a demo-recording aid. It is not physical acceptance by itself. For
dev84 acceptance, still return:

- `ux0:data/renegade/user/logs/a35-dev84-runtime.log`
- observations or screenshots for intro movies, main menu, loading, HUD,
  subtitles, textures, gate behavior, FPS, and freeze/crash state
- any matching `psp2core-*.psp2dmp`

## External Source Notes

The recorder build is based on Vita-MP4-Recorder, which describes PSVITA/PSTV
MP4 recording through `sceMp4Rec`, H.264 video, AAC audio, local output under
`ux0:video`, the title-scoped plugin install pattern, and known limitations
around audio availability/desync and 30 FPS slowdown:

```text
https://github.com/Rinnegatamante/Vita-MP4-Recorder
```

Vita-Recorder remains useful as a study reference for local MJPEG capture, but
it does not solve the requested audio path:

```text
https://github.com/Rinnegatamante/Vita-Recorder
```

The local `mp4rec.h` fallback follows the public VitaSDK `SceLibMp4Recorder`
API documentation and is only compiled into the optional recorder plugin.
