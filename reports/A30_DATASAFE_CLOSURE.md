# A3.0 Original Commando DataSafe Closure

Status: **ready for integration / validated on host and Vita ARM**

This slice compiles the original `Commando/datasafe.cpp` and unmodified
`Combat/crandom.cpp`. It preserves the original DataSafe allocation,
encryption/decryption, checksum, shuffling, handle, type-registration, and
tamper-detection behavior. The only removed dependency edge is the optional
multiplayer-chat notification performed after a security fault is detected.

## Legitimate platform boundary

On the Vita port, `GenericDataSafeClass::Say_Security_Fault` calls
`RenegadeOptionalServices::Report_DataSafe_Security_Fault()`. The boundary
retains a flushed `stderr` fallback and permits the A3 runtime owner to install
a durable-log callback with `Set_Security_Fault_Reporter`. The original
`cNetwork`/`cScTextObj`/player/translation implementation remains unchanged for
non-port builds. Do not pull WOL, GameSpy, multiplayer UI, or player management
into the single-player world bring-up solely to report this optional event.

Files added:

- `port/platform/renegade_optional_services.h`
- `port/platform/renegade_optional_services.cpp`

The centralized `GetCurrentThreadId` compatibility shim hashes the complete
`pthread_t` object representation into a stable, nonzero 32-bit runtime token.
It does not assume that `pthread_t` is an integer or pointer. The token is
runtime-only and must never be serialized.

## Exact portability patches

Apply after the existing Commando sources are copied, with the normal
`--batch --forward --fuzz=0 --no-backup-if-mismatch` policy:

1. `commando-a30-datasafe-gcc15.patch`
   `d82ed1bbc1406363314c14178059868eaf116fffd1f2ad60993eda45f254e99b`
   - replaces the x86 inline-assembly type token with a pointer-width runtime
     token on non-MSVC/x86 targets;
   - fixes the invalid `delete[] void *` expression and canonical include case.
2. `commando-a30-optional-services.patch`
   `49edeebfe193523ae60f2f8df339e8100ac99a0be9ed1023aa10b445e523edf6`
   - isolates only the security-fault multiplayer notification edge.
3. `commando-a30-datasafe-definitions-gcc15.patch`
   `13d47b30e4468a6453171c7e26a77da2efc85f0479036deb03984e84ab77bf7d`
   - emits standards-correct, initialized explicit template static-member
     definitions under GCC while retaining the original MSVC form.
4. `commando-a30-datasafe-ilp32.patch`
   `90390a04ca0b216fb56e2ee46b7a74f4ad32f8bf37fff410b1bd4aa40692f1ef`
   - uses the compatibility `DWORD` for semantically Win32 32-bit DataSafe
     words, keys, checksums, timers, and sizes;
   - uses `uintptr_t` only for a runtime pointer difference.

Resulting staged source fingerprints:

- `datasafe.h`: `94a4116dd871bce12130abfcbfcd30d1b476db3fd44c7574f955c1aa6d79fbf1`
- `datasafe.cpp`: `db3e64123fb3253efc03eb1317802c484bdc1384c54c2eccdd2bc1482c6fcefd`

No `.orig` or `.rej` residue was produced, and canonical upstream remained
clean.

## ABI defect found and corrected

The original four-byte cipher loops cast buffers to C++ `unsigned long *`.
That is correct on Win32 and Vita ILP32 but performs eight-byte accesses on the
LP64 host. ASan reproduced a dynamic stack-buffer overflow in
`GenericDataSafeClass::Mem_Copy_Encrypt` during static DataSafe initialization.
The fixed-width patch changes only those semantically 32-bit words to `DWORD`;
it does not redesign the algorithm or alter the Vita ABI.

Evidence:

- before fix: `logs/a30-20260807-datasafe-host-asan-before-fixed-width.log`
  (`1edd589ce2ce9f0ea1c5dd8b91f57d969196e22d13ebe77df9bc591b65af02d1`)
- final ASan/leak run: `logs/a30-20260807-datasafe-clean-host-asan-final.log`
  (`71d9b39a31230c237f53b8f57488db9acf421709ffd63df77772b809f8397ea7`)
- semantic result: `DATASAFE_SEMANTIC_PASS add/get/set/delete int+float; reporting boundary callback`
- final result: `FINAL_CLEAN_ASAN_RC=0`

Host and Vita ARM compile proof both cover original `datasafe.cpp`, original
`crandom.cpp`, and the optional-services boundary:

- `logs/a30-20260807-datasafe-clean-host-compile.log`: 3/3 PASS
- `logs/a30-20260807-datasafe-clean-vita-compile.log`: 3/3 PASS

The only warning is the pre-existing `#endif WWDEBUG` token in
`devoptions.h`.

## Combat frontier linker delta

Adding original DataSafe resolves **32 of the 68** engine symbols introduced by
the current nine-translation-unit Combat frontier. **36 engine symbols remain**
and DataSafe introduces no new engine dependency. `pthread_self` is the sole
new platform reference and is resolved by the already-required pthread link.

Evidence:

- `logs/a30-20260807-datasafe-linker-delta-summary.log`
- `logs/a30-20260807-combat-after-datasafe-unresolved.txt`
- `logs/a30-20260807-combat-after-datasafe-unresolved.mangled.txt`

The remaining closure belongs to existing Combat/save-load registration,
definition/translation globals, WWAudio, gameplay objects, damage/explosion,
and game-state boundaries. It must not be "solved" by restoring DataSafe's
optional multiplayer reporting graph.

## Integration requirements

- Compile original `Commando/datasafe.cpp` and original
  `Combat/crandom.cpp`.
- Compile `port/platform/renegade_optional_services.cpp` and expose
  `port/platform` to the original target.
- Retain the existing original `wwlib/random.cpp` and `wwlib/systimer.cpp`.
- Keep pthread linked for the runtime thread token.
- Install the A3 runtime-log callback before entering substantial Commando
  startup; the flushed fallback remains valid during earlier initialization.
- Preserve the original DataSafe code path and do not replace it with a new
  container, cipher, or integrity system.
