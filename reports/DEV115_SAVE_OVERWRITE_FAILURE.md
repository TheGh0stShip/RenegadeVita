# Dev115 original quicksave overwrite failure

After successfully reloading the Dev111 original checkpoint and moving
outdoors, native Select+Square changed quicksaveA.sav. The input was accepted
and released; helper receipt is under `build/dev115-outdoors-quicksave`.

The strict archive validator rejected this new save with
`Truncated original save chunk header`. No checkpoint master was created.
The rejected bytes are retained privately at
`build/dev115-outdoors-quicksave/rejected-quicksaveA.sav`.

- New save SHA256: `8e2194c3563d1f290a000741fb06ca666728bc1d49f840e193772260490cb25b`.
- File size: 96458 bytes, unchanged from the overwritten slot.
- Level-info chunk: offset 0, size 51, end 59.
- Level-data chunk: offset 59, size 96387, end 96454.
- Four trailing bytes: `0e000000`.
- The previous valid save's level-data size was 96391, ending at 96458.

This is consistent with a shorter overwrite retaining the old tail, but the
responsible boundary is not yet established. Original SaveGameManager opens
WRITE; staged RawFileClass's Unix WRITE branch uses fopen("wb"), which should
truncate. Investigate the actual native libc/emulator open path and chunk
accounting before changing code. Do not weaken validation or trim saves.

Earlier immutable checkpoint masters remain intact. Successful loading of
those masters does not prove that overwriting existing saves is reliable.
The demonstrated outdoor route and one pause/resume cycle remain valid.

## Host isolation result

`experiments/save-overwrite/host_probe.cpp` exercises the original rooted
file factory, WRITE open, ChunkSave backpatching and close using synthetic
bytes in a private temporary tree. It creates a 15-byte chunk file, then
overwrites it with an 11-byte chunk file and checks the actual bytes and size.
Both passes succeeded. Evidence: `build/save-overwrite-host-PDyjO1/runtime.log`.
The probe uses copied host object files and does not modify the active build.

Matching Dev115 RawFileClass object inspection confirms the WRITE branch calls
fopen. Installed VitaSDK libc routes open through `_fcntl2sony` to sceIoOpen;
the truncate flag conversion is present. This does not prove the native flags
actually supplied during the failed save or exclude save-specific behavior.

Next bounded native comparison: preserve existing quicksave slots, test an
original save into an unused slot, then repeat a shorter overwrite. Keep the
strict parser unchanged and keep emulator findings separate from hardware.

## Emulator ownership closure

Runner session 67049 returned exit 143 while its owned Vita3K process remained
alive. Process 19952 was independently matched by name and start time
2026-09-09T15:13:34Z, then closed. Final runtime log was retained as
`runtime-manual-final.log` in the matching Dev115 evidence directory.
This was an operator close, not proof of the game's mission-end teardown.

## Upstream emulator boundary finding, 2026-09-09

Current upstream Vita3K `translate_open_mode` selects `rb+` for non-append
write opens, with no SCE_O_TRUNC branch. `FileStats` directly opens that mode;
the `_sceIoOpen` export forwards flags to `open_file`, which constructs
FileStats without separately truncating an existing file. This explains how
a correct native WRITE request can retain the old tail on that implementation.

Primary sources inspected:

- https://github.com/Vita3K/Vita3K/blob/master/vita3k/io/src/filesystem.cpp
- https://github.com/Vita3K/Vita3K/blob/master/vita3k/io/include/io/filesystem.h
- https://github.com/Vita3K/Vita3K/blob/master/vita3k/io/include/io/state.h
- https://github.com/Vita3K/Vita3K/blob/master/vita3k/io/src/io.cpp
- https://github.com/Vita3K/Vita3K/blob/master/vita3k/modules/SceIofilemgr/SceIofilemgr.cpp

This is upstream-source evidence consistent with the observed emulator save,
not a verified source identity for the installed executable or physical-Vita
evidence. Do not patch the engine's serialization or discard trailing bytes.
Proceed with the prepared fresh-slot comparison and preserve originals.
