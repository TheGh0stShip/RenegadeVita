# Dev124 native boot diagnosis

Physical return: user reports reaching intro movies, which play at less than
1 FPS. This establishes startup progression for Dev124 with plugins reportedly
disabled; it does not establish why Dev123 hung. Boot/runtime log retrieval is
pending FTP return. Native movie performance is now the active blocker.

Dev123 failed on physical Vita: user saw black screen and unresponsive device.
After recovery, user reports plugins disabled and VitaShell running. FTP
inventories show no Dev123 runtime log and no recent eboot dump in ux0:/data
or ur0:/data. Failed executable retained and exact predecessor restored.
The plugin state during the original failure remains unknown.

Dev87 and Dev123 ELF import-library sets are identical. This rules out a new
import library as a demonstrated explanation, not individual import or loader
problems. Both have similar mapped segment sizes. Current startup initializes
the debug display, prints and waits for vblank, and initializes filesystems
before resetting the normal runtime log. C++ registration also precedes main.
There is no evidence yet identifying which of these boundaries failed.

Dev124 adds raw, allocation-free SceIo boot markers at constructor priority 101,
main entry, display initialization entry/return, bootstrap print/wait return,
filesystem initialization return, and runtime log reset. Each fixed-size record
is synchronized and closed; short writes are handled and errors do not recurse
into logging. Path: ux0:data/renegade/user/logs/A3.5-dev124-boot-v1.log.
Original engine initialization and renderer ownership remain unchanged.
Development checkpoint startup is disabled for the full-demo test profile.

Validation: production trace extraction passes ASan/UBSan for hex formatting,
short writes, zero writes, failed open and bounded phase text. Log:
build/dev124-boot-trace-host.log. Changed startup ARM unit compiles. Incremental
package closure passes 134 focused checks, ARM/ELF/SELF/VPK and matching
diagnostics in build/dev124-fast-console.log. Frozen ELF inspection verifies
the early trace constructor precedes pthread_setup and original engine static
initializers (build/dev124-constructor-order.log); it uses only raw Vita I/O.
Artifacts and hashes are recorded in BUILD_STATE.json. Physical deployment
receipt root: build/device-evidence/dev124-boot-20260914T202219Z/.

This is diagnostic coverage, not an asserted root-cause fix. Next: verify
package and constructor position, deploy with matching hashes and predecessor
backup, user LiveArea launch, then retrieve physical boot/runtime markers.
No port changes will be justified solely by emulator behavior.
