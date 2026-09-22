# Dev149: M13 ambush PostThink owner diagnostic

Status: full-port-only diagnostic, **not a performance fix**. The existing
M00 demo profile and retail data are unchanged. No physical Vita result.

The prior Dev148 scene-render attribution did not explain the multi-second
ambush hitch. Dev149 adds bounded timing at the scene, Combat render, Combat
Think, and original GameObjManager PostThink boundaries. In the isolated
Vita3K/OpenGL M13 route, a matching run at frame 633 measured:

| Phase | Process-clock time |
| --- | ---: |
| Whole frame | 6,777,956 us |
| Simulation | 6,740,308 us |
| Render | 37,647 us |
| GameObjManager PostThink | 6,700,854 us |
| One object PostThink, ID 1500000007 | 6,700,026 us |
| Observer deletion / script destruction | 1 / 1 us |

This identifies the blocking original object callback, not its inner
operation. It is consistent with the user's audio continuing while video
stalls, but A/V sync and actor sequencing were not visually accepted. The
run timed out unassessed at 120 seconds; it is not a full mission test.

Matching evidence: managed AppData
`evidence/campaign-dev149-postowner-m13-2/`, including runtime before/after
and runner receipt. SELF SHA-256
`d4035771f2820779c6e33604fcd83d016287213ec433a43d6fcb8f59644ad482`;
asset-free VPK SHA-256
`b14700ab99397071c4bef75e811700147942a7672b26d0ea1d4e425224d98958`.
ARM SELF/VPK built and the 189-patch ordered staging inventory passed.

Next executable step: record object 1500000007's definition and time its
`PhysicalGameObj::Post_Think` animation update and `Animation_Complete`
observer callback separately. Trace any synchronous W3D/asset request there.
Apply a loading-time preparation or platform-boundary fix only after the
inner operation is identified. Repeat the fixed M13 route and M00 regression;
measure p50/p95/p99/worst, clock drift, visual script sequence, and audio
alignment. Physical Vita performance acceptance remains pending.

Two Dev149 launch attempts did not reach gameplay: one lacked the VPK at the
runner's package path, and one remained in Vita3K's library. They are not
performance evidence. The matching run explicitly launched the title after
package installation.
