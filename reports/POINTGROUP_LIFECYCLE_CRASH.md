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
The physical repeat reached Logan's conversation: the user confirmed it
started, and the matching log records `MTU_LOGAN_START` active at frames31–33.
The prior first-frame table-read crash did not recur before this checkpoint.
Further dialogue/audio, controls, progression and soak remain pending.
Existing mixed wchar_t
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

## Physical repeat limits

Dev230's installed SELF hash was independently read back before launch.
The matching VPK was retained in the Renegade user directory. Movies completed
and the original menu activated. Authenticated automation acknowledged two
100 ms Cross taps and a250 ms Cross tap, but the user observed no activation.
Manual Cross opened Single Player, then Tutorial. Successful RPC acceptance
therefore does not establish effective input on this launch. Do not attribute
the manual route to automated input or claim automated-route acceptance.

The runtime log at `build/device-evidence/A3.5-dev230-20261004/`
`runtime-tutorial-repeat.log` has SHA-256
`a99975af1eac550348452121e76a384d0a04f3f64ab34ed8a9c5da14eebeb7a2`.
It records original tutorial rendering and subsequent conversation startup.
The first simulation/render frame still took approximately983 ms; this is
an unresolved startup cost, not a frame-rate or visual correctness claim.
The projected shader path was not proven to execute by this test.

Continued manual play is retained in `runtime-weapons.log`, SHA-256
`4b142fd1b5814a35761e5c8f501a9444cd9f8b8d3bf1a4e406c6601d1f02bdf8`.
The user reported that it was playing well and progressed toward pistol
acquisition. Subsequent original-engine logs show the first two objectives
at status1 (`STATUS_ACCOMPLISHED`, verified in `combat/objectives.h`), active
Sydney dialogue, pistol shots reaching fired_total9, and Gunner's sniper-rifle
lesson with that weapon selected. This is partial manual tutorial progression,
not mission completion, a visual accuracy audit or proof of every weapon path.
