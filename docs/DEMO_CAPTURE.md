# Evidence capture

This project separates three different capture mechanisms. They are not interchangeable.

| Mechanism | Current status | What it captures |
| --- | --- | --- |
| Game-owned diagnostic capture | Present in historical candidates | An engine-frame diagnostic; it can be too early to represent the visible panel. |
| Title-scoped MP4 recorder | Installed optional helper | A local video recording when it finalizes successfully. The red `R` means recording has started, not that an MP4 is recoverable. |
| VDB framebuffer capture | **Not installed on the current Vita** | The intended exact-title post-render logical framebuffer route, independent of game capture timing. |

## Current capture limitation

The paired Vita advertises VitaCompanion `screen.v1`, which controls panel power with `screen on|off`. It is not VDB screenshot capture. The VDB client supports `capture.screen.v1`, but that requires its separately authenticated exact-title gateway and target-local agent; neither is active on this device.

Do not describe a panel wake command, an early engine capture, or a recorder overlay as a verified VDB screenshot.

## Optional MP4 recorder

The recorder helper is built from the pinned GPL-3.0 Vita-MP4-Recorder source and is scoped only to `RNEGA3101`. It starts with the title, writes under `ux0:/video` (`ux0:video` in VitaDevBridge-style path output), and remains outside the Renegade VPK.

USB capture is not the default. PSTV capture may be useful for an external operator, but project evidence should prefer exact-title VDB framebuffer capture when that provider exists, or a title-scoped MP4 recorder when a finalized file is available. VitaShell FTP is only a read-only transfer route for finalized recordings or screenshots that already exist on the device.

The recorder starts recording when the Renegade process loads. To finalize the MP4, use L+Start to finalize the MP4; Plain Start
remains available to Renegade and must not be stolen by the recorder. A recorder output is supporting media, not physical acceptance. Known limitations include audio availability/desync, 30 FPS slowdown, and failure to finalize if the game crashes first.

Source provenance: https://github.com/Rinnegatamante/Vita-MP4-Recorder

```bash
bash ./tools/build_renegade_demo_recorder_plugin.sh
```

Install only the generated title-scoped configuration:

```text
*KERNEL
ur0:tai/RenegadeDemoRecorder-<candidate>.skprx
*RNEGA3101
ur0:tai/RenegadeDemoRecorder-<candidate>.suprx
```

Never place it under `*ALL`.

The intended explicit finalize control is L+Start; module stop is a fallback. A crash can interrupt either path, leaving no usable MP4. In particular, do not use the recorder as a workaround for a candidate with an unresolved Start crash without a safe, approved route.

After the Dev87 return, forced VDB1 search of `ux0:/video` found no finalized MP4. No video is claimed or published.

## Future VDB capture route

The VDB provider must be built and validated separately, first against its disposable probe target, then as an exact `RNEGA3101` agent bound to the current executable SHA-256. It must capture through `sceDisplayGetFrameBuf` in the target process, authenticated mailbox IPC, bounded buffers, and exact title/PID/build verification. It must not use `*ALL`, SceShell/private framebuffer hooks, FTP fallback, or game-source timing changes.

When available, use it for labelled post-render comparison frames; retain its metadata and hashes with the candidate. The raw frame remains local evidence. Only reviewed, non-retail PNG derivatives belong in the GitHub gallery.

See [Evidence and capture policy](EVIDENCE.md) and the [historical screenshot timeline](HISTORICAL_SCREENSHOT_TIMELINE.md).
