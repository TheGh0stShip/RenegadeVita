# Dev230 M13 final-gate crash

## Physical observations

On 2026-10-04 the user played the original campaign opening on Recruit using
dev230 after completing Tutorial. Rope descent, the ambush, NPCs, scripts and
tank combat looked mostly intact. The user reported slowdown during the
ambush, unexpected combat/death audio during the cutscene and occasional
out-of-place chatter/reload sounds. The game crashed as a tank pushed through
the final gate before the mission-complete screen. The user's identification
of a Mammoth tank is an observation, not a verified object definition.
Mission completion and the transition to M01 did not pass.

## Matching retained evidence

Installed dev230 SELF: `7d63179f2fb2d4d3b318889d739bcca049928280cf2651bc95d4bb2203e59c95`.
Matching ELF: `197ce0440ad8fc74a60329c594bac83a18c58a79229b973fbcfba52db7b53cab`.
The single new crash inventory entry matches recorded process10363831
(hex9e23b7). Only this dump was pulled.

Private evidence under `build/device-evidence/A3.5-dev230-20261004/`:

- `runtime-m13-gate-crash.log`, SHA-256
  `d6541fde3c03eaffeac4c6a1117f2ef875aef65ea0778c5c20f64935662733aa`.
- `m13-gate-crash.psp2dmp`, SHA-256
  `3687c8433d3c4c2464be0009287a960df70a761dd362cb0ceb27664c16920ed5`.
- `m13-gate-core-metadata.json` and `m13-gate-symbolication.txt`.

The source-derived private-note parser classifies an undefined instruction
on the main thread. Module text starts at runtime0x81039000. Relocated
PC0x8163514a is `_kill_r`'s explicit `udf #255`; captured r2=6 matches abort's
signal. Stock GDB cannot read this private register layout; its unavailable
backtrace is not evidence.

A bounded scan of96 stack words is heuristic, not an unwound call stack.
It contains abort, verbose terminate, exception throw and operator-new return
addresses. Matching disassembly at linked0x8134a56c calls operator new inside
`RenegadeVitaAudio::Decode_Wave_With_Info`; return0x8134a570 is retained on
the stack. This supports an uncaught audio decode allocation-failure lead.
Debug line attribution alone gave a conflicting collision label; disassembly
and symbol boundaries establish the audio function. No collision fault is
claimed. The requested allocation size and reason for heap pressure remain
unverified.

The log ends during original `MX0_A04_CON020` at frame4879 with control
disabled. Its earlier checkpoint has cinematic freeze active, populated
soldiers/vehicles and functioning audio. This does not prove why unwanted
combat audio was audible or whether it was authored cinematic sound.

## Minimal failure handling and open work

Dev233 catches `std::bad_alloc` at the production WAVE decoder boundary,
returning its existing failure result and preserving prior caller output.
The provider already propagates decoder failure. A forced-allocation-failure
test compiles the production decoder, verifies unchanged output/metadata and
then successful decoding on retry. Both audio tests pass, including the
existing sanitized mixer/lifecycle suite. All501 focused host tests pass.
The first ARM attempt rejected catch with the global no-exceptions policy;
`CMakeLists.txt` now enables exceptions only for this decoder translation
unit. The unchanged decoder passed host tests before the compile-option fix;
the repeated ARM/package run skipped those tests and passes two compile/link
and seven package actions. Vita3K installed hashes match, without launch.
The existing mixed wchar_t link warning remains unresolved.

Dev233 ELF: `2399d27407829d6e791142e0e9517d7b01c8abfb7a3447b6d037f2e38e887e76`.
SELF: `dea8ae6ea2a389da0992e7838183145f7cb55770b83223e083c4ebd1b12a77db`.
VPK: `28d5f778d9501b85ca49fadc07654bca0a109a7c222c4c6678b7f52cdf321f67`.
The candidate has not been deployed to physical hardware.

This is allocation-failure containment, not proof of adequate memory or
complete audio correctness. Repeat the original Recruit route on matching
hardware, verify final dialogue, score screen and M01 load; collect bounded
heap/allocation evidence if audio fails. Preserve original cinematic freeze,
conversation, sound and script ownership. Do not globally mute combat or
change simulation behavior on the basis of this observation.

Separate audio investigation: compare camera-host/freeze transitions in
`staging/combat/ccamera.cpp`, original control/think filtering in
`staging/combat/gameobjmanager.cpp`, cinematic objects explicitly exempted
from freeze by `staging/scripts/Test_Cinematic.cpp`, original sound ownership
and provider completion/loop semantics. Those paths exist; no runtime cause
has yet been established. No PSTV result or corrected physical gate is claimed.
