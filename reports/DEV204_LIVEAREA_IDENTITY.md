# Dev204 LiveArea identity

## Scope

Dev204 packages an original R/V insignia, application icon, launch image,
LiveArea background, and gate. The background and gate place the candidate
number where Vita3K's Start control does not cover it. No EA or Westwood logo
artwork or retail data was used. Dev203 was the first package with artwork;
Dev204 supersedes its crowded initial LiveArea composition without changing
the game runtime.

## Evidence

| Gate | Result |
| --- | --- |
| Focused tests | 177 tests passed. |
| ARM package | Fast ELF, SELF, VPK identity, and seven-entry retail-exclusion checks passed. This is not a canonical build. |
| VPK SHA-256 | `840966d4a7c17a0fbb78f4b1c47a345309e17022cb95f8f834bbd9584e10c11d` |
| Packaged SELF SHA-256 | `5b15a10d9dd02a0088dc772b63abf51f01e0e9014e68cc6c80958055a9576a8f` |
| Vita3K install | Installed title files matched the VPK, including all five artwork files. Receipt: local `build/vita3k-backups/A3.5-dev204-setup-20260927T053840890405Z/setup-receipt.json`. |
| Vita3K visual | The [LiveArea screenshot](../docs/media/vita3k/dev204-livearea.png) shows the versioned gate and background. PNG SHA-256: `001e27fea0d44693ecee0c2b0139b4b176e8a36daabb02972a1c1c8f3838c10e`. |

The visual check opened the installed Vita3K title presentation. An intro
frame appeared during navigation, but no gameplay, natural exit, or
performance result is claimed. Vita3K was stopped after capture. Physical
Vita/PSTV LiveArea appearance and canonical package acceptance remain pending.

## References

- [VitaSDK VPK resource packaging](https://github.com/vitasdk/vita-toolchain/blob/master/cmake_toolchain/vita.cmake)
- [VitaSDK sample LiveArea layout](https://github.com/vitasdk/samples/blob/master/hello_cpp_world/Makefile)
- [Project-authored artwork and build rules](../docs/BRANDING.md)
