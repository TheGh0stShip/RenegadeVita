# Dev120 original loading animation and menu audio

Final user playthrough remains held until known issues are fixed. Dev119's
new loading overlay was the wrong implementation and is removed entirely,
including its helper. The original retail loading bar remains the owner.

Dev119 runtime reports a corrupt backdrop animation name and null animation.
LoadingScreenClass passed StringClass objects through `%s` varargs. The new
zero-fuzz staging patch passes actual character pointers, producing the
original `IF_LVL94LOAD.IF_LVL94LOAD` animation name. Existing original manual
animation frames and load milestones drive the bar. Ten focused loading and
lifecycle tests pass; visible fill still needs a new candidate capture.

Original MenuGameModeClass2 initializes and plays `menu.mp3`. The unchanged
always.dat entry exists: 1,477,848 bytes, MPEG Layer III, stereo 44,100 Hz.
The Miles provider only decoded RIFF/WAVE. The new boundary uses the installed
VitaSDK libmpg123 in memory feeder mode; original WWAudio retains file access,
music priority, loop count, volume, playback and shutdown. No converted retail
file is created. Decoder output remains bounded by the existing 16M-sample
ceiling and rejects unsupported format changes. Metadata inspection decodes
without retaining PCM; sample preparation retains PCM until original release.
This adds decode work at menu activation and needs measured startup/memory
validation. No streaming-performance improvement is claimed.

Host decode of the unchanged retail menu succeeds: 4,082,688 stereo frames at
44,100 Hz (about 92.6 seconds), 16,330,752 PCM bytes, nonzero samples and exact
metadata agreement. Receipt build/dev120-menu-decode.json records source hash;
retail bytes stayed in memory. This is not audible Vita3K/physical evidence.

Reuse provenance: installed VitaSDK arm-vita-eabi libmpg123.a and mpg123.h /
fmt123.h; header identifies mpg123 project, LGPL 2.1. Existing SDK dependency,
no external source imported. Preserve matching source/license obligations at
release; credits now acknowledge mpg123. Host tests link system libmpg123
and generate their own sine-wave MP3, independent of retail files.

Generated stereo MP3 decode returns 44,100 nonzero frames with matching
metadata; malformed/truncated input is rejected. Existing WAV/provider test
passes. Logs: build/dev120-audio-focused.log, dev120-loading-focused.log,
dev120-staging.log, dev120-loading-audio-arm-retry.log. ARM object validation
does not establish audible menu playback or animation correctness.

Dev119 ending reaches original main menu after clean owned teardown in the
same Vita3K process. Credits imagery is visible but body text cuts off midway;
root cause remains under investigation. Per-frame credits resolution logging
is now disabled while preserving scoped state restoration. Sky/elevator
rendering and repeated menu-to-tutorial lifecycle remain open.

## Matching Vita3K return

Dev120 fast package passes 133 checks and artifact closure. SELF
1fb02f5a5221b60ddec76562d47b44f9a3ca54c049933a36ea8e66ebd8b7325c;
VPK a3ad1772dfb081c4c25fc91c18a4dd601e3525a3daa8255c8f9268f594a841d0.
Fresh original intro/menu/tutorial startup succeeds in engineering r1,
PID 30032. Two owned-window Cross presses released; no movement input.

The original loading animation now binds correctly to 61 frames. Retained
40-second, 15-FPS game-window video proves the retail bar fills, with no second
overlay. At row 530, bright green fill spans x144–154 at the early 1% frame,
x144–735 at captured 80%, x144–749 at 90%, and x144–800 during 97% preparation.
The animation's original shape/interpolation is preserved. Examined extracted
frames: build/dev120-loading-early-01.png, early-06.png, loading-04.png,
loading-06.png, loading-08.png. Video and hash receipt live in
D:/Vita3K/RenegadeEvidence/Dev120-menu-loading-engineering-20260914-r1/.
This is window-video evidence, not native framebuffer or physical proof.

Native post-menu audio telemetry: sample_file 3/3/0, stream 8/8/0,
stream_start 8/8/0/0; 4,429,763 decoded stream frames and 4,461 nonzero
stream-output buffers. The menu MP3 is the long stream in this route, consistent
with successful native menu music output. No listening or isolated audio
recording verdict is claimed. Menu-to-tutorial transition succeeds; stopping
and returning through credits still needs the revised candidate's test.
