# v3.6 resource and memory pipeline status

## Verified host foundation

`tools/renegade_asset_manifest.py` inventories only a user-supplied Data tree.
It does not extract, transcode, cache, or package any retail content. Schema
v1 records normalized paths, byte sizes, SHA-256 values, archive class, a
deterministic whole-manifest digest, required-input absence, and case conflicts.

Local inventory on 2026-08-16: 51 files; all required `always.dat`,
`always2.dat`, `always.dbs`, and `M00_Tutorial.mix` inputs present; optional
`always3.dat` present; no case conflicts; content digest
`a3cc696b1d938c2780f1514875234a2ea9a9aac7b57bd5ac6f0d1599f01f4264`.
Tests cover deterministic output, required-input failure, optional input, and
case conflict handling.

Profiles now make the source availability required by exercised scenes explicit:
`m01` requires the common archives plus `M01.mix`; `city` requires the common
archives plus `C&C_City.mix`. Both profiles validate the same local 51-file
content digest `a3cc696b1d938c2780f1514875234a2ea9a9aac7b57bd5ac6f0d1599f01f4264`
with no missing input. Manifest contracts pass 5/5; the canonical host runner
regenerates both profile manifests. Profile presence is intentionally narrower
than a claim to have enumerated every future transitive campaign dependency.

`tools/renegade_asset_cache_key.py` adds cache-format v1 identity calculation.
The key binds source manifest digest/count/schema, tool version, format version,
and canonicalized conversion options; invalid manifests are refused. Unit tests
prove deterministic ordering and invalidation on source/options changes. It is
not a converter, residency system, or device cache implementation.

`tools/host_a30_definitions/a36_mix_index_main.cpp` adds the next bounded
cache precursor. It asks the original `MixFileFactoryClass` for the archive
filename list and writes only a sorted, versioned archive/name index. It does
not implement a MIX parser, extract entries, transcode assets, or run on the
Vita. M01 produced 231 index entries; two independent writes were byte
identical (SHA-256
`7a277d47fd50388ccec9c7841d3127cb452903b502f67b8dfa2df82605531b34`). The
City smoke archive produced 83 entries (SHA-256
`4b4b310a74b12b344356dd031107d3f35896731a01e73d53c138684b9f03c299`). The
canonical host gate writes M01 twice and rejects a non-identical result.

The v1 index is now bound to a versioned cache metadata sidecar whose key
includes the manifest source identity and cache options. The companion verifier
does not rebuild or read retail archives: it reports `missing`, `stale`, or
`corrupt` states for absent metadata, changed source/options keys, unsafe
paths, missing artifacts, or artifact hash mismatches. Against the real M01
index, metadata and verification are valid with cache key
`55d93acb1240e2b7ddb4416660d0a3b0e7330eb7499eed10099fcd177c762538` and
the indexed artifact hash `7a277d47fd50388ccec9c7841d3127cb452903b502f67b8dfa2df82605531b34`.
Host contracts for manifest/cache-key/metadata/verifier/capture comparison pass
14/14. This is a host cache-format proof, not a native cache writer or runtime
consumer.

The native runtime now performs one bounded, startup-only health probe for the
optional `cache/m01-mix-index-v1.txt` artifact. It accepts only the existing
cache namespace, checks the versioned index schema, archive identity, declared
count, bounded entry records, ordering, and trailing data, then logs its state.
Missing, corrupt, or unsafe cache data is diagnostic-only and leaves the
original `MixFileFactoryClass` retail route unchanged. The dedicated contract
passes 9/9 (missing, valid, corrupt, retail-path, and traversal cases), the
full native source closure links as ARM EABI5 with both probe symbols present,
and the complete host gate again passes at
`logs/a30-20260816-115428-host-runtime.log`. This is a native validation
boundary, not a cache consumer, cache writer, metadata-hash verifier, or
device-cache acceptance claim.

Capture schema v2 now records the current free-memory sample and the lowest
periodic free-memory sample observed for system user/CDRAM/physically
contiguous pools and VitaGL RAM/VRAM/SLOW/ALL pools. Sampling occurs at startup,
each 60th frame, and explicit capture only; it does not add an allocator hook,
claim resource ownership attribution, or alter retail loading. The capture
self-test passes 17/17 and the host comparison tool accepts both v1 and v2
bundles (2/2 tests). The changed native runtime linked for ARM/Vita on
2026-08-16. Actual values remain unmeasured until a physical capture is
returned.

## Scene evidence

The retail inventory contains `M00_Tutorial.mix`, `M01.mix`, `C&C_City.mix`,
`C&C_Field.mix`, and `C&C_Walls.mix`. A dedicated host probe now validates
`M01.mix` through original `MixFileFactoryClass`: 231 entries and the expected
LDD/LSD/DEP classes are enumerated. Original `CombatManager::Load_Level_Threaded`
is the selected ownership route for a future M01 runtime test. This archive
proof is not a scene-load, renderer, memory, or physical-Vita claim.

The parameterized original interactive harness then loaded `M01.mix` through
`CombatManager::Load_Level_Threaded` for two in-process lifecycle cycles. Both
completed 120 original update/render frames without rejected or unsupported
submissions. The first M01 render frame had 21 meshes, 2,228 vertices, and
2,204 triangles; the loaded scene reported 2,405 static objects, 296 dynamic
objects, 818 static lights, and a 18,630-entry visibility table. This is a
host-only correctness/load-lifecycle proof; visual fidelity, memory behavior,
and Vita performance are not inferred from it.

The expanded canonical host gate passed on 2026-08-16, including retained M00
ASan/LeakSanitizer/UBSan lifecycle coverage, the 14/14 asset-manifest/cache
metadata/verifier/capture-comparison contracts, valid real-M01 cache metadata,
M01 MIX preflight, and the two-cycle M01 original Combat load/render/teardown
test. Log: `logs/a30-20260816-114055-host-runtime.log`. The runner now invokes
all Python cache tools through `python3`, so their execution does not depend on
source-file permission bits.

The selected original multiplayer archive `C&C_City.mix` then passed the same
two-cycle host `CombatManager::Load_Level_Threaded` route. Its first frame
submitted 43 meshes, 4,115 vertices, and 2,963 triangles with zero rejected or
unsupported submissions; the scene reported 1,181 static objects, 110 dynamic
objects, 425 static lights, and 937 visibility-table entries. This is a
distinct resource/scene rendering and lifecycle smoke only. It does not start,
emulate, or claim a multiplayer session. The canonical runner now retains this
normal host smoke after M01; direct evidence is `build/a36-city-host-smoke.log`.

## Remaining v3.6 gates

- Original-engine M01 archive/LDD/LSD validation and host load/unload lifecycle: PASS; physical evidence remains required.
- Canonical host M00 sanitizer regression plus M01 and City two-cycle scene
  gates: PASS (`a30-20260816-114055-host-runtime.log`); these remain host-only.
- A second distinct physical scene and physical multiplayer-map render smoke.
- Native device cache consumption, invalidation, and stale-entry rebuild.
- Measured resource residency, allocation high-water, and bounded eviction.
- Repeated level lifecycle and device-storage behavior.

## Resource-boundary telemetry (2026-08-16)

`RenegadeRootedFileFactoryClass` now has fixed-size, per-session counters for
factory acquisition/return, read/write path resolutions, prepared-resolution
hits, resolve failures, and Open/Is_Available/Create/Delete attempts and
failures. The 12/12 host contract uses only temporary fixture files and proves
retail traversal is rejected and user writes remain outside retail. It does
not capture logical names or payload bytes, allocate per event, change archive
precedence, consume the index cache, or alter original `MixFileFactoryClass`
loading. The Vita runtime resets the counters before its original factory
chain is constructed and logs one summary during teardown.

The same boundary now also records total `Read`/`Write` calls and successful
byte counts, without retaining content, paths, or per-operation records. The
focused contract is 13/13: one two-byte read and no writes are accounted
exactly. The modified source re-linked as ARM EABI5. These are still bounded
boundary measurements, not complete archive/MIX residency telemetry.

The first expanded canonical run also revealed a pre-existing harness
lifecycle omission: `PathMgrClass` was being used by original Combat actions
without the original Commando `Initialize`/`Shutdown` ownership, retaining a
`PathSolveClass` under LSan. The direct host and Vita routes now preserve the
original ordering from `commando/init.cpp` and `shutdown.cpp`; the focused
two-cycle M00 ASan/LSan rerun is clean. Full canonical revalidation also now
passes (`logs/a30-20260816-122251-host-runtime.log`); all device resource
measurements remain pending.
