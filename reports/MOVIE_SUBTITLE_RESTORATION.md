# Original movie subtitle restoration

Date: 2026-11-05 UTC. Base source: `a42506c214e181d6743bb1cbf5e516c93a3d9b6a`.
This is an unreleased, non-play verification checkpoint. All gameplay tests
remain held under REMAINING_PORT_INVENTORY.md.

## Defect and original ownership

The native FFmpeg `BINKMovie::Play` discarded its subtitle filename and font
arguments. The released `MovieGameModeClass` and movie-options caller already
pass `data\subtitle.ini` and release their font reference after Play returns.
The original `SubTitleClass`, `SubTitleParserClass` and `SubTitleManagerClass`
were absent from staging and the frontend target. A successful native link
therefore did not establish the original movie presentation contract.

These three owners and their headers now stage from the pristine released
`Code/BinkMovie` sources through two registered zero-fuzz patches. The original
proprietary Bink SDK caller remains replaced by the existing FFmpeg provider.
Native and host frontend source selections include the original subtitle
owners and `port/platform/renegade_movie_subtitles.cpp`.

## Runtime boundary

The FFmpeg consumer retains `-fno-short-enums`; the adapter and subtitle owners
retain engine short enums and two-byte wchar_t. The interface exposes only an
opaque manager handle, an opaque `FontCharsClass` pointer and `uint32_t` ticks.
No manager, renderer or FFmpeg structure crosses the enum-layout boundary.

Play creates the manager before returning the caller's font reference. The
original sentence owner retains that font. Replacement, Stop, Shutdown and
decoder failure destroy the manager on the movie's main-thread cleanup path.
The original file factory supplies subtitle reads, including rooted,
case-resolved retail paths and existing MIX lookup semantics. FileStraw closes
the file before file_auto_ptr returns it to the factory.

Render processes captions only after a video texture exists and after drawing
the movie and restoring its GL state. Caption time comes from the last
successfully uploaded frame's normalized presentation timestamp, converted to
60-Hz ticks with saturating, overflow-safe arithmetic. Decoder read-ahead,
dropped frames and wall-clock advances do not advance captions ahead of the
image. The released SDK used a one-based frame count and integer frame-rate
arithmetic; this provider deliberately uses displayed-frame PTS. Native
presentation acceptance must account for that timing difference.

## Parser portability and malformed inputs

The original parser remains responsible for subtitle entries and their
defaults. Explicit UTF-16 helpers replace libc operations with incompatible
wchar_t assumptions. The parser admits UTF-16LE with its BOM, bounds filename
conversion and numeric values to the original 32-bit range, and retains the
authored hours/minutes/seconds/hundredths conversion into 60-Hz ticks.

EOF or a new BeginMovie ends a block whose EndMovie is missing. Complete
captions already parsed remain available; another movie's captions are not
consumed. Invalid time, duration, color or position entries are rejected.
Entries require Text, avoiding an original null-caption renderer path. Valid
defaults, zero-duration fallback, unknown-token handling and Unicode caption
text are retained. Collection-add failure releases the unowned caption.
Expiration compares elapsed duration without overflowing an absolute end
timestamp.

## Verification

| Evidence | Result and scope |
| --- | --- |
| Deterministic source staging | 633 registered zero-fuzz patches, 1,954 staged files; six new subtitle inputs. Upstream remains pristine at `3e00c3a1b97381bb28be89a35b856375e0629a08`. |
| Original parser fixture | 54 checks pass with ASan/UBSan, short enums and two-byte wchar_t; valid UTF-16, defaults, timing, invalid fields, missing terminators and truncated inputs. |
| Mixed-enum owner fixture | Seven cases pass with ASan/UBSan. Real adapter, manager, parser, caption, rooted file factories, FileStraw, line readers and original font reference methods execute. |
| Movie lifecycle routing | The same fixture executes production Play, Render, Stop, Shutdown, Mark_Failed and Release_Decoder_State bodies against simulated decoder/GPU APIs. It checks displayed-PTS routing, post-GL-restore drawing, optional subtitles and cleanup. |
| Ownership and time limits | 32 create/render/destroy cycles, balanced file get/return and renderer counters, font retained after caller release, unsigned tick boundary and 10,000 deterministic conversions against an independent 128-bit oracle. |
| Focused regression suite | 77 tests pass, including source-selection/staging contracts and the repaired pre-existing CI fixtures described below. |
| Existing Bink contracts | Eight scheduler/audio tests pass, including native-output lifetime and wrapped PCM transfer fixtures. |
| Source inventory scanner | 49 parser/guard/renderer tests pass. Full function audit completes with 5,082 rows and 2,361 port functions; six parse-unknown rows remain visible and completeness remains false. |
| Native compilation | All five changed native translation units compile to actual ARM objects with GCC 15.2.0. ELF attributes verify ARMv7, ELF32, little endian, VFP-register arguments, two-byte wchar_t and the intended small-enum/int-enum split. |

The focused suite used `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1` and
`UBSAN_OPTIONS=halt_on_error=1`. This environment does not permit LeakSanitizer's
process inspection. Explicit lifetime counters run; this is not leak-scanner
evidence. No retail movie or subtitle content is distributed by the fixtures.

The host's original `unsigned long` fields are 64-bit. The near-`UINT32_MAX`
case verifies scheduling across the explicit-width interface, not a runtime
reproduction of native 32-bit end-time overflow. That arithmetic correction is
reviewed separately. The Bink fixture assigns uploaded PTS directly; it does
not execute FFmpeg decoding, actual texture upload or glyph rasterization.

Reproduce the focused subtitle checks after normal staging:

```sh
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1 \
python3 -m unittest tools.test_subtitle_parser tools.test_movie_subtitle_abi
```

Both canonical and fast build gates now run these fixtures and require the
original subtitle and adapter symbols in the linked native ELF. A new patch
inventory receipt records registry SHA-256
`8dc140a16551dd8640594895b2867e38970f4606a94241cdb2e45634900550bc`.

### Native object evidence

[MOVIE_SUBTITLE_NATIVE_COMPILE.json](MOVIE_SUBTITLE_NATIVE_COMPILE.json)
retains complete compiler commands, current-source/object SHA-256 values,
compiler-warning summaries, ELF attributes and dependency provenance. Local paths use
documented placeholders. All five source and object hashes were rechecked
before publication.

| Source | Object bytes | ELF enum attribute |
| --- | ---: | --- |
| `staging/binkmovie/subtitle.cpp` | 22,184 | small |
| `staging/binkmovie/subtitleparser.cpp` | 80,632 | small |
| `staging/binkmovie/subtitlemanager.cpp` | 80,256 | small |
| `port/platform/renegade_movie_subtitles.cpp` | 24,568 | small |
| `port/platform/a4_binkmovie_boundary.cpp` | 432,564 | int |

The official SDK is `sdk-snapshot-20260813.576.1`, with downloaded archive
SHA-256 `c76b242aef15c5682e41448fda1e5a169ea19a5306e25023e62ea908b86dbfd9`
matching its published asset digest. It has the same date as the CI image pin;
byte identity with that Docker image has not been established. The real native
FFmpeg branch is confirmed by unresolved decoder references and all four
subtitle adapter references in its object. No host ABI override or substitute
dependency declarations were used. The only compiler warning is the existing
trailing text after `#endif` in `chunkio.h`.

FFmpeg 9.0.1 was configured from the repository-pinned, hash-verified archive
to install 137 public/generated headers. No FFmpeg libraries were built for
this check. The pinned vitaGL header and an immutable upstream vitaShaRK header
provide the native declarations; their revisions and hashes are retained in
the evidence JSON. These results establish object compilation, not a full
native link or packaged runtime.

## Existing CI blockers corrected

The base commit's GitHub native job failed before ARM compilation. Its source
fixtures still assumed historical action/cinematic/dazzle patch inputs and an
older mesh/DDS production block. Forward replay now reproduces the canonical
normalization step, retains verified cinematic hashes, and proves current
effect owners equal staged bytes. The action fixture additionally checks that
the existing logical-time/freeze implementation remains unchanged.

The mesh fixture selects the current production ordinary-mesh loop and keeps
its prior state/corner equivalence checks. Unexpected entry into the separate
client-array route fails explicitly. It passes 1,425,120 corners across 40
comparisons; the shared generic indexed fixture passes 216,000 corners. The
DDS fixture includes the actual upload-probe wrapper and checks balanced
telemetry while retaining transactional failure checks: 800 DXT cases,
9,762,188 blocks, 12 retained-chain cases and eight surface-owner cases pass.
These repairs change test support, not the renderer's production behavior.

The base host ASan job also stopped in the source inventory scanner: its
synthetic name for anonymous fixed-type enums was longer than `enum : int` in
the actual Vita clocks header. A one-character parser-only name preserves
original byte and line positions, including compact/multiline declarations.
Regression checks verify original definition hashes and retain unrelated parse
errors. The full audit now completes without promoting unknown rows to parity.

Three existing reports also contained local home-directory prefixes rejected
by the publication hygiene gate. Neutral placeholders replace those prefixes;
the original measurements and conclusions remain unchanged.

## Remaining gates

Full native link and symbol retention for this checkpoint, packaged identity,
retail subtitle coverage and native presentation remain distinct evidence
gates. Host fixtures do not establish glyph appearance, line placement,
readability, timing on retail movies, audio synchronization or hardware
performance. No VPK, release, emulator launch, physical run or complete mission
progression is claimed here. The independent retail content/feature inventory
and remaining full-port work stay open.
