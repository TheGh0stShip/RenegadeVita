# A3.5-dev84 recorder-confounded physical crash

Status: retained hardware evidence; Renegade Start-exit acceptance is still
pending. The user has requested that no further device launch occur until an
explicit `READY`.

## Returned artifacts

- Physical core: `psp2core-1788127044-0x0000072b4f-eboot.bin.psp2dmp`,
  171,840 bytes, SHA-256
  `c42665a0a5a10f8e235b4096d4a1d4dbc2962ca68dcd5bafa8050d7f6cb683d8`.
  The raw core remains only in the candidate-scoped local evidence tree
  `build/device-evidence/a35-dev84-start-crash-20260830T215650Z/`; it is not
  committed or uploaded.
- Runtime log: SHA-256
  `66bff1ec63685e56372abc217cd5ff0c8a3dd3cfa8e4dbaf040b93c9d64cb2bb`.
- Title-scoped `ux0:/video/22` and `ux0:/video/37` were empty after the crash;
  no finalized MP4 exists to upload.

## Classification

The core parser marks module/thread records source-derived, not VDB-verified.
Its faulting `RNEGA3101` thread reports a data-abort PC of `0x814755fa`. That
PC is inside the loaded `VitaMP4Recorder` executable range
`0x81474000..0x8147792c`, at offset `0x15fa`, rather than in the dev84
Renegade RX range `0x81033000..0x81414008`.

The exact recorder `.suprx` active for this run has a matching host build.
Applying its observed load bias maps the PC to recorder function
`updateFramebuf`; the emitted ARM instruction dereferences the display-frame
parameter at offset 16. Thread register data is unavailable in this core, so
the evidence cannot distinguish a null framebuffer argument from another
invalid argument. It does establish that the failure is in the optional
recorder display hook, not a symbolicated Renegade engine frame.

## Corrected recorder candidate

The title-scoped source patch now:

- passes null, empty, and clearly malformed framebuffer notifications directly
  to the original display call before recorder dereference;
- leaves plain Start for Renegade; upstream L+Start remains the deliberate
  recording-finalize control; and
- retains the existing module-stop finalization fallback.

`python3 -m unittest tools.test_demo_recorder_workflow` passes 5/5 and the
zero-fuzz external patch application succeeds. The rebuilt user recorder SHA
is `111d2f4f8e9e467e72a1212587d9e882d0c24e67f46e82302b9be16c565ee9a2`;
the kernel recorder remains
`e8a695c08fe348ab8cb1b16f2264fe67d593c3e82a7e61629f61f04d9e88eba5`.
This host evidence does not prove that the recorder or Start exit is fixed on
physical hardware.

## Separate follow-up

The returned dev84 runtime log records a successful original-owner prewarm but
names the dev82 prewarm receipt path. That candidate-label receipt bug is
retained as a separate correctness item; it was not changed in this
recorder-only publication.
