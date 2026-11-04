# Retail archive route audit — 2026-11-04

## Implementation follow-through

Full-port startup now enumerates all top-level Data MIX archives through the
existing rooted boundary and mounts original MixFileFactoryClass instances in
the original FileFactoryListClass. Tutorial is borrowed at its enumeration
position; the remaining factories are session-owned and detached before list
destruction. Failure rolls back the whole new set. Demo profile stays explicit.
No proprietary data is converted or cached by this helper.

ASan/UBSan fixture using the actual staged original classes passes four trees:
valid, malformed MIX, missing tutorial and no regular MIX files. Checks cover
cross-mission lookup, global fallback, M09 priority, network temp priority,
duplicate selected-map indices, repeated failure rollback and teardown. A
read-only run against the local reference mounts 27 MIX files and reads the
M08-only lv8_hbag.dds header through the general factory route. No game loop ran.
Five route-model fixtures pass; the all-retail model has zero excluded archive
CRC keys across 13 initial SP routes. That is availability evidence only.

DeepSeek's bounded advisory review prompted explicit rollback and failure/retry
fixtures. Its claimed name-lifetime concern is refuted by the original
DynamicVectorClass<StringClass> name copies; pointer removal removes one match,
and each owned pointer is distinct. Its duplicate-priority concern was checked
with actual duplicate indices and M09/temp lookup in the fixture. No requirement
to tolerate a missing tutorial was adopted: current startup explicitly requires
it. The review supplied no project/device observations.

The M01/M04-specific M08 supplement is removed. Selected-map and Glacier
indices remain redundant but retained during the network round-swap transition. Their
cleanup, real duplicate-payload precedence and always3.dat provider role remain
OPEN. Final runtime ARM object compilation PASS; ELF32 little-endian ARMv7,
VFP-register arguments, two-byte wchar and small enums verified. Object SHA-256
`3b813e48bdda2f920dc4eb2f6ecb38d4b2076446c32c73030c2ae6a1b3c7ae11`.
Input/object/log hashes: local-builder/logs/retail-mix-mounts-validation-receipt.json.
There is no new full link, SELF/VPK or installation from this focused build;
this does not establish whole-game content coverage or physical acceptance.

Evidence: local-builder/logs/retail-mix-mounts-tests.log,
retail-archive-route-tests.log, retail-archive-route-all-retail-summary.json;
private archive-routes-all-retail.json retains source/catalogue hashes.

## Discovery before correction

Historical discovery state: confirmed search-contract discrepancy, then OPEN. No play tests,
builds, installation, deployment or retail mutation performed.

Original Commando/init.cpp mounts loose data, Always2.dat, Always.dbs,
Always.dat and every top-level data/*.mix. Combat/ffactorylist.cpp tries the
temporary factory, SearchStartIndex, then remaining insertion order. Add/remove
resets the search start. Combat/savegame.cpp resets it at load preparation,
then specially promotes M09.mix for direct loads and saves. Windows directory
enumeration order is not an alphabetical-order contract.

Current full-port a31_vita_runtime.cpp constructs globals/tutorial, then adds
only the selected mission plus hand-picked M08 or Glacier/M02 supplements.
This differs from original archive availability before and during missions.
Loose files may mask a discrepancy. Native round/provider lifetimes need review.

The reference catalogue has 31 archive files; original startup would mount 30:
three globals and 27 top-level MIX files. always3.dat is outside that startup
rule; its retail provider/version role remains OPEN rather than silently being
included or declared unnecessary.

The read-only tools/audit_retail_archive_routes.py retains physical duplicate
providers, uint32 CRC keys, absent route archives and excluded nested archives.
Its model describes initial SP routes, not actual resource use or round swaps.

| Initial route | Archive CRC keys outside modeled mounts |
| --- | ---: |
| Tutorial | 3,222 |
| M13 | 3,085 |
| M01 with M08 supplement | 2,705 |
| M02 | 2,906 |
| M03 | 2,904 |
| M04 with M08 supplement | 2,744 |
| M05 | 3,079 |
| M06 | 2,900 |
| M07 | 3,035 |
| M08 | 2,936 |
| M09 | 3,038 |
| M10 | 3,073 |
| M11 | 3,084 |

These include resources belonging only to other missions: NOT missing-feature
counts. M13 leads include 119 TXT and 118 WAV keys. Dependency/event-chain use,
loose files and dynamic providers remain unmodeled. The original mounted set
has 18,637 unique CRC keys and 161 duplicate-provider groups. Payload equivalence
is UNKNOWN; equal names do not establish interchangeable bytes or semantics.

Evidence: private build/retail-content-baseline/archive-routes.json records
catalogue/archive-set/analyzer/four-owner-source hashes. Sanitized counts:
local-builder/logs/retail-archive-route-summary.json. Four isolated tests PASS:
cross-mission availability, supplements, duplicate/alias providers, top-level
scope, case ambiguity and 32-bit bounds. No game loop ran; host membership
arithmetic is not ARM execution evidence.

Next: restore all top-level retail MIX availability through original
MixFileFactoryClass/FileFactoryListClass and existing rooted enumeration.
Preserve shutdown lifetime, original M09 search-start and temporary/network
provider priority. Review checkpoint/round swaps before removing supplements.
Verify focused lookup behavior and ARM compilation during the play-test hold.
