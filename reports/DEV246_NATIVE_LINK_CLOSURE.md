# dev246 direct native compile/link closure — 2026-11-04

The direct build of RenegadeVitaA31 completed all 681 steps with exit 0.
This supplements the earlier failed canonical build; it does not replace that
failure record, create a package, or establish runtime/physical acceptance.
The user's play-test hold remains active.

Build directory: build/vita-a35-dev246-candidate-20261104-143651.
Log: local-builder/logs/a35-dev246-arm-link-closure.log; session 54511 terminal.
Staging inventory: 631 ordered patches. Configured source inventory remains
1,490 released units, with 632 selected directly plus the separately traced
LoadingScreenClass extraction. The remaining target sources include port code
and the VitaSDK common/debugScreen.c helper; they are not additional released
Renegade translation units.

## Retained identity

| Artifact | SHA-256 |
| --- | --- |
| RenegadeVitaA31 ELF | `34fcbf38701f3f63266da1e3b80c81524e52af04c8b79803b5dd6ea55ff7d2b9` |
| RenegadeVita-A3.5-dev246.map | `8b0e0ce5bbab4125fe75636a82366695ab80187ac5a36b9eaea6312b44853ccd` |
| compile_commands.json | `b534833b8f33ad9f339a3397628333d85a184487ae12309c623d9373e656d9ac` |
| dev246-native-build-inputs.json | `062f51469398f698745aa116204b2299c363a0b3bd395a4e7110e787b96ccc7e` |

The input/object receipt under local-builder/logs records all 681 selected
source, object and command hashes, including the external SDK helper. Matching
FFmpeg archive hashes are retained in dev246-linked-ffmpeg-archive-hashes.txt
before the new dependency recipe replaces that installation. The native ELF
contains 45,811 defined external symbols; raw identities are retained in
dev246-native-defined-symbols.txt.

## Scope of evidence

readelf confirms ELF32 little-endian ARMv7, EABI5 hard-float and VFP-register
arguments. Attributes are retained in dev246-native-elf-attributes.txt. Final
merged wchar/enum attributes are not proof of every component's type layout.
The linker emitted 140 enum-size warnings, all from the scoped int-enum Bink
consumer and FFmpeg archives. Keep the engine short-enum ABI and audit that
opaque/scalar boundary; do not suppress these warnings or pass engine object
layouts across it. This is not a claim of complete ABI closure.

The final ELF defines original AnimatedSoundMgr trigger/lookup, PointGroup
init/shutdown, Debug_Statistics::Record_Texture, LoadingScreenClass lifecycle,
mission Display_Text forwarding, render-target cleanup and sorting submission.
These are symbol-retention checks; their complete runtime behavior remains
unproven. The full 1,490-unit exclusion/functional-owner inventory is still OPEN.

## Revised dependency build and reuse

The verified-install FFmpeg recipe subsequently completed with exit 0. Receipt
input identity is `fa616f92cc3191eb7cdf9c2e293b3d3b9d8f0b141229ac8ec51567cbe5f593cf`;
173 installed files are covered. A second invocation took verified reuse in
2.86 seconds, leaving all five archives and the receipt hashes/mtimes unchanged.
All five rebuilt archive hashes match those already used by this native ELF.
Actual target probe: compiler-default enum layout rejects the transform
sentinel as expected; explicit int-enum layout passes. avutil's 99 emitted enum
attributes report int, and its 101 emitted FP argument attributes report VFP
registers; omitted attributes are not inferred.

Retained logs under local-builder/logs: ffmpeg-verified-install-20261104.log,
ffmpeg-verified-reuse-proof.{log,json}, ffmpeg-verified-input-identity.{log,json}
and ffmpeg-verified-install-enum-probe.log. The input identity document hashes
the actual selected SDK/compiler/header/library inputs and matches the receipt.

Next: continue excluded-owner reconciliation, then restore original subtitles through a
separate engine-ABI adapter. No VPK, Vita3K install/launch, physical device or
interactive host play test was performed for this direct-build gate.
