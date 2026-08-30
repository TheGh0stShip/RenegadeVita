# Renegade Demo Recorder Plugin

This folder contains the Renegade-specific patch and installation notes for a
non-USB demo recorder. It is intended for PSVITA and PSTV testing where USB
capture is not acceptable.

The recorder is built from the GPL-3.0 Vita-MP4-Recorder source at pinned
commit `60c966a75356ea9a95f79479a3e647283586cf11`. No external recorder source
or binary is vendored in this repository. Run:

```bash
bash ./tools/build_renegade_demo_recorder_plugin.sh
```

The script fetches the pinned source into the builder source cache, applies
`vita-mp4-recorder-renegade-autostart.patch`, and writes these artifacts:

```text
dist/RenegadeDemoRecorder-A3.5-dev84.suprx
dist/RenegadeDemoRecorder-A3.5-dev84.skprx
dist/RenegadeDemoRecorder-A3.5-dev84-tai-config.txt
dist/RenegadeDemoRecorder-A3.5-dev84-SHA256SUMS.txt
```

The selected VitaSDK must provide the `SceLibMp4Recorder` stubs. If the SDK
does not provide `psp2/mp4rec.h`, the build wrapper uses the narrow local
compatibility header under `include/psp2/mp4rec.h` for this helper only. The
build wrapper also corrects Vita-MP4-Recorder's kernel CMake library spelling
to `SceIofilemgrForDriver_stub` for the local case-sensitive toolchain layout.

The patch keeps the recorder outside the Renegade VPK and scopes it to title
ID `RNEGA3101`. It enables audio by default and starts recording when the
Renegade process loads. Plain Start remains a Renegade control; use L+Start to
finalize deliberately. `module_stop` also finalizes an active recording as a
fallback, and the hook passes null/empty/malformed display notifications
through before dereference.

The active workspace build produced these hashes:

```text
RenegadeDemoRecorder-A3.5-dev84.suprx       111d2f4f8e9e467e72a1212587d9e882d0c24e67f46e82302b9be16c565ee9a2
RenegadeDemoRecorder-A3.5-dev84.skprx       e8a695c08fe348ab8cb1b16f2264fe67d593c3e82a7e61629f61f04d9e88eba5
RenegadeDemoRecorder-A3.5-dev84-tai-config.txt 75e6f69f9690fd89689cd90be32357113d989be69770ea587cfefc546637d9b5
```

Install manually by copying the generated `.skprx` and `.suprx` to the path
shown in the generated tai config snippet, then add the snippet to the active
`ux0:tai/config.txt` or `ur0:tai/config.txt` and reboot. Keep the plugin
title-scoped to `*RNEGA3101`; do not install it under `*ALL`.

After install, `tools/run_dev82_recorded_demo_session.sh` can launch Renegade
and wait for L+Start/exit. The MP4 recorder writes the video under `ux0:video`
and imports it into the Vita Video app. Runtime logs remain under
`ux0:data/renegade/user/logs/`.

Retrieve completed MP4s with VitaShell FTP or the Vita/PSTV media workflow.
USB is not part of the supported demo path.

Known limits inherited from the upstream recorder:

- It uses Sony's `sceMp4Rec` path, so the capture can slow higher-than-30 FPS
  titles toward 30 FPS.
- Audio can be unavailable or desynchronized on some titles/devices.
- Free storage under `ux0:video` is required.

This plugin is a demo-recording aid, not physical acceptance evidence by
itself. The dev84 physical gate still needs the runtime log, screenshots or
observations, and crash dumps when applicable.

The recorder-enabled dev84 return faulted in the recorder display hook before
an MP4 finalized. It is retained as a recorder-confounded crash, not a
Renegade acceptance result; see `reports/DEV84_RECORDER_CRASH.md`.
