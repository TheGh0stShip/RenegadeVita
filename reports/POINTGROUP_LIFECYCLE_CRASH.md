# Original particle lifecycle restoration

## Dev229 physical failure

The physical Vita installed executable matched SHA-256
`78e59ac9795e13983d4c70f871e1f88b81c8637c3fa8b759ecddf38d5c192fef`.
The user observed both startup movies without audio issues or slowdown, a
readable original menu, and successful navigation into Tutorial. The game
then crashed before Logan's conversation. The final log records the first
original tutorial simulation and render frame; this is failed gameplay evidence.

The collected dump process identifier matches the observed launch PID.
Dump SHA-256:
`95580ca9175d5af53818fd59c9012fa42d912d9345b2527b9c1d1abf882b3449`.
Matching ELF SHA-256:
`d20f154a7531010bac465b4d6caf834eb0a8f741b9233ceb6928f13913dc4e1d`.
Private artifacts remain under `build/device-evidence/A3.5-dev229-20261004/`.
They are not published.

The local parser reports unsupported private thread schema 6; its host GDB
report has no usable registers. VitaDevBridge's source-derived parser
(`vitadevbridge/crash/metadata.py`, provenance
`xyzz/vita-parse-core` revision `644b5f081c5f3c9b205180793ab8f4209dfd9d97`)
decodes a main-thread data abort at PC `0x811527aa`. These private-note
interpretations are source-derived, not independently verified kernel fields.
It reports the executable text base as `0x81077000`; the matching ELF text
base is `0x81000000`. Relocation maps the PC to `0x810db7aa` in
`PointGroupClass::Update_Arrays`, inlined `Vector2::operator=`. The instruction
is `ldr r1, [r2]`, with source-derived r2=`0xa8`, r5=`3` and r7=`1`.
The preceding instructions read the triangle UV table indexed by r5 and add
a frame offset of `7 * 3 * sizeof(Vector2)`, consistent with a null table.
This supports the missing-initialization diagnosis; it is not an unwound call
stack or proof of every earlier memory operation.

## Original ownership and correction

Original `upstream/CnC_Renegade/Code/ww3d2/dx8wrapper.cpp` calls
`PointGroupClass::_Init()` after `VertexMaterialClass::Init()` during
device-dependent initialization and calls its matching shutdown.
`pointgr.cpp` owns orientation tables, five triangle/quad UV frame tables,
four original index buffers and the preset material reference. The native
WW3D boundary restored the material pool but omitted PointGroup initialization.

`port/patches/ww3d-a35-pointgroup-lifecycle.patch` restores those original calls
in native `WW3D::Init` and `WW3D::Shutdown`, after material initialization and
after asset release but before material/backend teardown. It introduces no
replacement particle geometry, UV tables or gameplay behavior. Staging
requires exact input SHA-256 and applies the patch with zero fuzz.

## Validation and remaining gates

The focused lifecycle test replays the original source patch chain and checks
single initialization, material dependency ordering, asset-release ordering,
and shutdown before material/backend teardown. Three lifecycle tests pass.
Dev230 passes 494 full focused contracts, the three separately run lifecycle
tests, 11 DDS checks and 13 render-state checks. The first wrapper invocation
stopped after host validation because its script was edited while running;
the unchanged-source restart completed six ARM compile/link actions and seven
SELF/VPK actions. Package identity and retail exclusion pass. All seven
Vita3K installed title hashes match; emulator launch was not requested.
The physical repeat remains pending. Existing mixed wchar_t
link warnings remain open. Host checks do not establish physical correctness.

Dev230 ELF SHA-256:
`197ce0440ad8fc74a60329c594bac83a18c58a79229b973fbcfba52db7b53cab`.
SELF SHA-256:
`7d63179f2fb2d4d3b318889d739bcca049928280cf2651bc95d4bb2203e59c95`.
VPK SHA-256:
`48ae69571849a3fcf0829b0650a383159f5fbebe8e95bfe5ec8bf96aeeb6f871`.

Movie/menu success is separate from tutorial acceptance. The unsupported
original projector render target remains open; its log message does not
establish this crash's cause. Projected shader compilation/pixels, Logan's
conversation, controls, mission progression, repeat transitions, performance
and soak stability remain pending. No PSTV result is claimed.
