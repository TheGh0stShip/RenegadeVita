# Renegade NoLockScreen diagnostic

This development-only `*main` user plugin resolves the physical Renegade Vita
test device's lock-screen automation blocker. A build configured with
`-DRNV_NOLOCK_PROBE_ONLY=ON` is read-only: it records the device's `SceShell`
fingerprint and twelve bytes at each documented retail-3.65 lock-screen site.
It performs no injection.

The normal build accepts only retail-3.65 NID `0x5549BF1F` and the first eight
stable bytes at each physical-device instruction window. The following four
bytes are logged but excluded because a probe across two boots proved that
they contain an ASLR-relocated Thumb instruction. The plugin validates both
stable fingerprints before either bounded taiHEN injection, verifies the
resulting bytes, and releases a partial or unverifiable patch. The
compatibility offsets are public facts from TheOfficialFloW's GPL-3.0
`VitaTweaks/NoLockScreen` repository.

The device configuration and plugin are outside the Renegade application and
must remain independently reversible. Preserve the pre-change
`ur0:tai/config.txt`, install only under `ur0:tai`, and remove the one `*main`
entry and plugin file to roll back. While active, the helper bypasses the
SceShell lock screen itself, including any lock-screen passcode. It is only
appropriate for the dedicated development Vita used by this project.

The physical-device pre-change configuration is retained as
`ur0:tai/config.txt.renegade-pre-nolock-794c4e91.bak` with SHA-256
`794c4e91b133316c17796641a1a581c20b4528e4c5574e19a15fc871cc8f3a38`.
Rollback must first compare-and-swap that exact file back to
`ur0:tai/config.txt`, reboot so SceShell no longer loads the helper, and only
then remove `ur0:tai/renegade_nolockscreen.suprx`. Never remove a plugin binary
while the active taiHEN configuration still references it.
