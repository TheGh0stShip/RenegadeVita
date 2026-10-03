# S4 retail closure — all-map binding discovery in progress

The nested W3D dependency census now covers all 31 archives and all 3,999 W3D
index records. It finds 117,411 texture references and 50,186 HLOD subobject
references with zero parser/archive errors. Fifteen unique texture names have
298 occurrences without an exact filename or DDS sibling anywhere in supplied
archive indices or loose-file names. Their first origin, hashes and all distinct
parent paths are retained publicly; full resolved-reference provenance is local.
These are unknown missing-name leads, not proven rendering defects. HLOD
subobjects are internal names and require registry/header resolution.

Nineteen focused/shared tests pass, including later-map inclusion, duplicate
archive names, DDS sibling availability, aggregation and malformed child bounds.
Reproduce with `python3 -m tools.audit_nested_w3d_references --data DATA --output OUTPUT --private-output LOCAL_RECEIPT`.
The compact public inventory has 62 archive/kind rows; zero-reference rows are
retained. It is the seventh supplement in the consolidated register. Runtime
mount precedence, name selection and natural mission dependency closure remain
open. No assets were changed or fabricated.

Seven supplemental inventories are now included in the consolidated gap register:
level chunks, spatial presence, visibility bounds, W3D chunks, W3D consumer
candidates, DDS formats and nested W3D references. Their nested status records retain original JSON
pointers and input hashes. Parent-inventory identity mismatches fail generation.
Records overlap across evidence layers; they are not unique defects. All
supplemental statuses remain unknown pending behavior/impact/acceptance review.
The DDS header inventory was refreshed over all 31 current archives, including
M09: 3,463 DDS members (2,985 DXT1, 474 DXT5, four DXT3), zero archive errors.
The earlier 30-archive HUD literal-reference search remains a separate limited
receipt and is not included as a status inventory.

W3D consumer reconciliation retains all 97 observed IDs and their retail parent
paths. 61 IDs have staged symbolic case-label candidates; six have no global
symbolic source reference, including four absent from the global chunk enum.
All four unnamed IDs resolve to reviewed sphere/ring local chunks or primitive
animation variables through exact parent paths. Existing local case consumers
are recorded with lines/hashes; this avoids false missing-loader findings from
global numeric matching. Headers are not counted as selected translation units.
Pivot fixups and obsolete HModel auxiliary data remain the two named IDs without
symbolic references. Original loader skip behavior requires review before any
missing-support verdict. Source candidates include saves and inactive branches;
all 97 statuses remain unknown until dispatch, registration and runtime proof.

Seventeen focused/shared checks pass. Reproduce with
`python3 -m tools.audit_w3d_chunk_consumers --inventory reports/generated/sweeps/w3d_chunks.json --link-inventory reports/generated/sweeps/link.json --output OUTPUT`.
Enum, input, generator and contributing source hashes are retained. Numeric
dispatch beyond the reviewed primitive contexts, port-owned consumers, macro
dispatch and full affected-mission reachability remain open.

The generalized W3D census scans all 31 supplied MIX/DAT/DBS archives, retaining
3,999 W3D member index records, 1,294,901 chunk occurrences, 2,181 per-archive
ancestry paths and 97 distinct chunk IDs. Zero members fail bounded parsing.
Archive/member hashes and duplicate index records are retained; path aggregates
include first-member/index/offset provenance without payload bytes. Fourteen
focused/shared checks pass, including duplicate names, M11 inclusion, repeated
children, parent context and malformed bounds. All coverage statuses remain
unknown. No loader behavior or natural asset reachability is accepted.

Reproduce with `python3 -m tools.audit_w3d_loader_coverage --data DATA --output OUTPUT`.
The optional historical `--build` census still covers only four bootstrap
loaders; it is not used to classify this full asset denominator. Loose W3D,
nested archives, full staged-loader mapping, per-member nested-path provenance,
mission dependency closure remain open. Consolidated-gap integration is now
included in the six-supplement reconciliation above.

Optional host LZO2 safe decoding checks all 25,784 visibility tables across
27 maps: zero decode errors and zero decoded-size mismatches. Expected sizes
follow original `VisTableClass::Get_Long_Count` and `Get_Byte_Count`:
`((VisObjectCount + 31) / 32) * 4`. Original owner source hashes are retained.
Eight focused tests pass, including malformed-stream/output-capacity rejection
and the 33-object word-rounding case. No decoded asset bytes are published.
Run the visibility command with `--decode-lzo` to reproduce this evidence.
The optional provider is host liblzo2 2.10, using host-size `lzo_uint` as defined
in its [public header](https://raw.githubusercontent.com/nemequ/lzo/master/include/lzo/lzoconf.h).
It does not validate the original ARM decoder, object/sector linkage or visual
culling. The audit allocation cap is 16 MiB per table; exceeding it is reported
as decode rejection, not evidence of malformed retail data.

Visibility bounds validation reports duplicate variable fields and unknown
compressed-table children. It now checks every exact-ancestry occurrence,
reconciling counts, first offsets and payload-size totals against the parent
inventory. Reads preserve archive index identity instead of collapsing duplicate
member names. Parser source hashes are retained. Six focused parser tests pass,
including repeated-chunk and wrong-parent fixtures; a fresh scan retains 27
rows, zero parser errors and zero findings. This is serialized-bounds evidence
only; original ARM decompression, linkage and runtime culling remain open.

The 19 missing cinematic names are also absent from an exact-name search of
all 31 supplied archive indices (18,836 records, duplicates retained) and
loose files below the diagnostic Data root. All archives parse without errors.
Input archive hashes and the parent inventory hash are retained in
reports/generated/sweeps/missing_cinematic_names.json; no payloads are emitted.
Every name has an original quoted source reference: M01 17994; M05 4263,
6473/6507/6513 and 7177; M06 4943–4945; M09 592/631; M10 3417–3427.
Source line ranges locate leads, not proof that their branches execute.
Other editions/roots, computed aliases, runtime selection and natural gameplay
remain open. Do not fabricate replacements or exclude affected sequences.
The reusable name resolver preserves duplicate index candidates and compares
case-insensitively; its authored test covers loose-file and missing-name cases.

All-map factory reconciliation compares level persist-factory counts and
discovered-definition factory IDs with numeric template Load symbols retained
in Dev209. There are 1,506 per-map requirement rows spanning 79 unique IDs;
all 79 have a matching Load method. There are 346 cinematic-control candidates
and 19 missing-name leads summed across maps, not unique global totals.
These per-map requirements keep unknown status even when a method
matches: section/storage initialization and runtime registration remain open.
The driver also retains candidate cinematic-control counts and missing-name
leads from the existing dependency parser. Shared driver/parser validation
passes 44 tests. Conversation and other deliberately unparsed subsystems,
unreached definitions, computed dependencies and the remaining S4 asset
classes are outside this partial factory denominator.

M09 input recovery supersedes the first-scan missing-input row below. Three
local backup copies match archive SHA-256
3132c75426a357ddff60bf2b1c8f2810d27172978b763bc587310f83797d76d7;
a fourth differs in both LDD and LSD members. The matching input was copied
without overwriting an existing file into the ignored diagnostic Data folder,
with a private hash receipt. Retail-edition provenance remains unverified.
All 27 maps now have binding scans: 13 campaign/tutorial, 13 multiplayer and
Skirmish00. M09 adds 533 level bindings, 574 discovered bindings and 66 script
names with matching registrar symbols; its 15 unresolved definition-ID leads
remain unverified. Total level bindings now 7,456.

Provenance separates the six missing-name leads: three M11 names occur in
m11.ldd; M05_Inn_Reinforcements occurs in x5d_chtroopdrop5/6.txt at lines
72 and 79, and M05_Park_Unit in x5d_c130troopdrop7.txt at lines 71 and 78,
all in always.dat. M04_BH_MessHall_Guy_JDG attaches the M04 name in original
Mission04.cpp:5352. Public summaries retain binding member/offset/kind and
cinematic archive/member/line provenance without parameter payloads.
Thirteen driver and shared-parser tests pass. No behavior fix is adopted.

The all-map driver enumerates every supplied MIX filename plus all expected
campaign maps. The first scan retains 27 rows: 26 supplied maps audited and
one missing input, M09. This includes 12 campaign/tutorial maps, 13 C&C
multiplayer maps and Skirmish00. Missing-input rows remain visible; no map
is silently excluded. All statuses are unknown, not gameplay passes.

Six discovered script-name leads lack matching registration candidates and
retained ARM symbols: M04_ForeDeck_Reinforcement_03_JDG;
M05_Inn_Reinforcements; M05_Park_Unit; M11_ObeliskWall_FodderGuy01_JDG;
M11_ObeliskWall_FodderGuy02_JDG; M11_TempleRoof_FodderGuy02_JDG.
The M04 name is also attached by original Mission04.cpp:5352. The other
names require authored-binding/caller investigation. These findings do not
justify inventing new scripts or changing original behavior without evidence.

M09 backup copies were located locally. Input identity and completeness must
be verified before filling the missing row. Detailed bindings, parameters,
objects and IDs remain under ignored build/; published JSON retains map names,
hashes, aggregate counts and unresolved script-name leads only. No retail
payload or private root path is published.

Run `python3 -m tools.audit_sweep_retail --data <Data> --link-inventory
reports/generated/sweeps/link.json --private-output build/<receipt-directory>
--output <summary.json>`. Two tests cover expected/missing/non-campaign map
enumeration and registrar reconciliation without serialized parameters.

Open coverage: computed dependencies and IDs, remaining asset/loader classes,
frontend/global-only data, full factory numeric-ID reconciliation, runtime
mount order and actual script registration. The existing dependency parser's
structural findings remain review leads. This is the binding portion of S4;
the complete sweep and full-game acceptance remain open.
# All-map level chunk denominator

## Visibility serialization bounds

All 27 first located visibility chunks pass manager-variable widths, table ID
sector bounds, compressed byte-count matching and ID/data pairing checks, with
zero parser errors or findings. `visibility_bounds.json` retains counts and
member hashes only. Original owner layouts are in `vistablemgr.cpp:186` and
`:417`, and `vistable.cpp:399`. One authored fixture checks valid pairing,
out-of-range IDs and wrong-width IDs. Reproduction matches byte for byte.

Run `python3 -m tools.audit_visibility_bounds --data DATA --presence reports/generated/sweeps/spatial_presence.json --output OUTPUT`.
No LZO decompression, reference linkage or runtime visibility result is proved.
Only each candidate's first offset is validated; repeated chunks need review.
All statuses remain unknown. Latest compile/hygiene CI for 6707976 is queued;
earlier 629bf76 hygiene passed. No queued job was restarted or treated as failed.

## Spatial owner context reconciliation

Three reviewed chunk paths identify visibility tables, static-object culling
and the pathfind database under the original physics static-data subsystem.
All 81 map/family pairs across 27 maps have matching candidates. Reused leaf
IDs under other parents do not match. Member hashes, offsets/counts and reviewed
source hashes are retained in `spatial_presence.json`.

The owner chain is `saveloadids.h:60` -> `wwphysids.h:55` ->
`physstaticsavesystem.h:80` -> `PhysStaticDataSaveSystemClass::Load`:
scene data goes to `PhysicsSceneClass::Load_Level_Static_Data`; pathfind data
goes to `PathfindClass::Load`. Visibility/culling cases are in
`pscene_saveload.cpp:231` and `:243`; the pathfind database enum starts at
`Pathfind.cpp:83`. These are source locations, not runtime execution evidence.

Run `python3 -m tools.audit_level_spatial_presence --chunks reports/generated/sweeps/level_chunks.json --output OUTPUT`.
Three focused tests pass including rejection of a matching leaf under the wrong
parent. Output reproduces. All statuses remain unknown until semantic bounds,
post-load linkage and runtime navigation/culling are verified. Numeric signatures
are reviewed constants; source changes require re-review. No runtime fix made.

The supplemental `level_chunks.json` inventory covers all 27 supplied maps and
54 LSD/LDD member index records. It retains 12,687 distinct chunk-ancestry paths
per member, with occurrence counts, first offsets, aggregate payload sizes and
member/archive hashes. All 54 members parse without a bounds error. Every row
remains unknown; chunk presence does not prove loader support or usable data.

Reproduce with `python3 -m tools.audit_level_chunk_inventory --data DATA --output OUTPUT`.
Two authored tests check little-endian parent context, repeated local IDs and
truncated bounds; 26 checks pass including the existing level-owner reader tests.
The existing reader deliberately leaves ConversationMgr's
0x40700 subsystem opaque because its payload starts with a raw category field.
No guessed recursion or raw payload is published. Parser input hashes are retained.

Source-to-chunk owner reconciliation, pathfinding/visibility semantic validation,
geometry dependencies remain open. Consolidated-gap integration is now included
above. This supplement does not close S4 or establish runtime level correctness.
