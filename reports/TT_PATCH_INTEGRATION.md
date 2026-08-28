# Tiberian Technologies patch integration

Date: 2026-08-24

Reference: Tiberian Technologies 4.8 Update 4, revision 9000

Status: audited; toolkit and compatible runtime boundary integrated; no TT source import

## Pinned public source

- Official source: `https://www.tiberiantechnologies.org/files/source-4.8.4.zip`
- Published/source-verified MD5: `5bf9acce0663514ea5e84ff5e0c16fb1`
- Observed SHA-256: `8d3c2df2af0b2a7bb49b4e1a0353947b49fc2b228f849024e1a7bf18a0fddfcd`
- Official update diff: `https://www.tiberiantechnologies.org/files/source-diff-4.8.4.diff`
- Published/source-verified MD5: `c746d12f7bbe06b99e3a15b6856ab3f4`
- Observed SHA-256: `6a73ca645b1591b3c0456bb34c859d8b4644a64401503ae0f30a8ee68d1e314b`
- License observed in `source/scripts/COPYING` and file notices: GPL-2.0-or-later with TT's runtime-linking exception.

The release is a 607-file `scripts.dll` source archive. Its nine-file 4.8.4 diff is relative to the previous TT source release; it is not a cumulative patch against EA's complete Renegade source.

The active-blocker inventory finds only engine-facing headers for audio,
cinematics/conversation, lighting/materials, and render objects. It finds no
portable WWAudio device, controller, sky/background renderer, or conversation
runtime implementation, and none of the nine 4.8.4 diff files touches those
surfaces. Changelog-only binary fixes therefore remain provenance leads, not
source patches that can be safely interpolated.

## Adopted development support

`tools/fetch_tt_484_reference.sh` fetches only the pinned official archive and diff to a temporary or explicitly selected external cache, validates both published MD5 values and the observed SHA-256 values, and runs `tools/audit_tt_reference.py`. The audit independently repeats both digest classes, rejects unsafe ZIP paths, verifies the source notice, inventories the delta, and compares known portable semantics with the EA source used by this port. It never imports the TT tree into staging or the VPK.

The canonical build's host contract now runs the audit-tool unit test. Network retrieval is deliberately not part of the canonical build, so an unavailable third-party site cannot make a Vita candidate non-reproducible.

## Adopted runtime integration

TT's public interfaces and retained sound-definition/callback semantics were
used as a compatibility cross-check, not as a source donor. The Vita target now
links 15 original EA/Westwood WWAudio translation units so playlists, sound
definitions, callbacks, priorities, transforms, looping, and scene ownership
remain in the original engine. A locally implemented Miles-compatible boundary
provides bounded RIFF PCM, Microsoft IMA ADPCM, and Microsoft ADPCM decode,
software rate conversion/mixing, 2D pan, 3D distance/pan, encoded-byte timing,
and a blocking `sceAudioOutOutput` worker. It uses original file callbacks for
stream access and links `SceAudio` without importing TT code or Windows Miles
binaries. A3.5-dev16 additionally restores the authoritative EA application
lifecycle inside the direct runtime: install the rooted retail/MIX chain,
attach Renegade's basename-stripping audio factory, construct and initialize
non-lite `WWAudioClass` before engine/world setup, require the original
scene/2D/3D drivers, call `On_Frame_Update` once per active or suspended frame,
and destroy audio before renderer/factory teardown. TT corroborates those
interface names but does not publish their implementations.

Whole-track stream decode is intentionally bounded at 64 MiB and is a v3.6
resource-memory measurement item; it is not represented as a completed
incremental streaming implementation. Physical Vita output and retail M00
format coverage remain unaccepted until matching hardware evidence returns.

## Source decisions

| TT item | Local result | Decision |
|---|---|---|
| `ChunkLoadClass::Close_Micro_Chunk` residual seek and parent position accounting | The same semantics are already in EA `wwlib/chunkio.cpp`; the M00 host path exercises the loader | Already present; no duplicate patch |
| `LineSegClass::Set` transformed endpoints, direction, delta, and length | EA `WWMath/lineseg.cpp` already has the same behavior | Already present; no duplicate patch |
| `SysTimeClass::Get` relative clock and wrap behavior | EA `wwlib/systimer.h` has equivalent unsigned wrap semantics | Equivalent implementation retained |
| `AudioCallbackListClass` add/get/remove behavior | EA `AudioEvents.h` has the same behavior plus the explicit `this->` qualification required by GCC's dependent-base lookup | Existing ARM/GCC-compatible implementation retained; TT header not copied |
| `AudibleSoundDefinitionClass` chunk and micro-chunk schema | EA `AudibleSound.cpp` preserves TT's `0x100`/`0x200` chunks and fields 3 through 22 used by unchanged retail sound definitions | Original EA schema retained as the input side of the current Vita audio provider |
| 4.8.4 preliminary PC controller support | No portable implementation appears in the public delta; Vita input is already owned by the native SceCtrl boundary | Platform mismatch; not imported |
| 4.8.2 Communications Center campaign crash fix | The official changelog names the fix, but the public 4.8.2 `scripts.dll` diff does not contain the engine implementation | Study-only until source/provenance exists |
| TT audio initialization/looping fixes | The public archive declares `WWAudioClass(bool lite=false)` and `On_Frame_Update` but contains no constructor, frame-update, main-loop, conversation, or usable output-device implementation; none of the nine 4.8.4 delta files touches those paths | No TT code imported. Dev16 restores the original EA construction/init/frame-service lifecycle above the locally implemented Vita Miles ABI/provider; bounded format/timing/mixer tests and `SceAudio` ARM linkage pass |
| TT lighting/DirectX renderer improvements | No portable Vita renderer implementation is published in the archive | Do not substitute for WW3D/VitaGL work |
| `HashTemplateClass` copy operations | This port's EA template intentionally forbids copying and no active call site requires it | Not adopted without a demonstrated owner/call-site need |

## Validation

- Official 4.8.4 archive/diff checksum verification: passed.
- Archive safety, license, inventory, and semantic audit: passed.
- Portable patterns already/equivalently present: 5/5, including the callback list and complete retail audible-definition schema.
- Audit and wrapper tests: 2 test methods; passed.
- Audio provider contract: PCM8/16, mono/stereo IMA ADPCM, mono/stereo
  Microsoft ADPCM, bounded/truncated WAVE inspection, encoded-byte 3D seek,
  mixer pan/volume, and 3D distance tests passed.
- Audio provider ASan/UBSan and Vita ARM `-Werror` checks: passed.
- Canonical Python contract suite after dev16 staging: 42 tests passed; the
  focused lifecycle/provider/TT/runner subset passes 14/14 and post-build full
  discovery passes 90/90.
- Dev16 lifecycle contract verifies retail/MIX and path-stripping-factory
  ordering, non-lite construction and initialization before engine/world setup,
  absence of the lite construction, driver gates, updates in both active and
  suspended frame paths, and audio teardown before renderer/factory teardown.
- Canonical A3.5-dev16: fresh D:-retail M00/M01/City host routes, ASan,
  LeakSanitizer, targeted UBSan, all 482 ARM/packaging actions, identity 15/15,
  required symbols, compressed-data validation, manifest, diagnostics bundle,
  and retail-exclusion gates passed. SELF/VPK SHA-256 are
  `4dd1f7fd4a10ee26605986c58c1aad9e63986fbbf5c91e48326c9d4a0c81169f`
  and `fa7903ba94442c7f18b554dd986d868bd90fe4dedfbcbcfc732b9f506e741a63`.

This evidence proves the required original lifecycle is present and ARM-linked;
it does not prove physical audio or that the Logan conversation defect is fixed.

No TT binaries, external source tree, proprietary SDK material, or retail assets are included in this project or its packages.
