# Retail content discovery — 2026-11-04

Current state: discovery seed and minimum campaign-asset checks implemented.
Full feature/sequence enumeration, semantic owner reconciliation and all-content
admission remain OPEN. No port play tests, app launches, installation, deployment
or retail-file modification occurred in this work.

## Independent retail inputs

The collector starts from retail archives and campaign.ini, independently of
the current port/source selection. It preserves physical MIX index records,
including duplicate names, unknown script names and unknown timed command verbs.
All binary chunk nodes are counted and hashed by their full ancestor path;
unknown paths remain visible. Offset examples are bounded to eight per path.
This compact census replaces an oversized intermediate per-node JSON listing.
Unclassified text lines and formats remain explicit. No count is a content pass.

| Observation | Steam-linked retail-pc Data | Local Vita3K retail Data reference |
| --- | ---: | ---: |
| Archive files | 30 | 31 |
| Archive index entries | 18,651 | 18,836 |
| Decoded level members | 52 | 54 |
| Level script bindings | 6,923 | 7,446 |
| Definition records across two database members | 15,153 | 15,153 |
| Timed command candidates | 10,294 | 10,397 |
| Structural chunk nodes still semantically unreviewed | 3,614,803 | 3,748,201 |
| Unclassified text lines | 683 | 685 |
| Unreviewed loose files | 21 | 22 |

Both datasets contain the same 36 campaign flow entries, listing M13 and M01
through M11. The Steam-linked dataset is missing required M09.mix. The reference
contains it, and all 30 common archives match byte-for-byte. No archive was
copied between roots. The reference permits discovery of M09 without changing
the incomplete dataset. This establishes archive identity/availability, not
equivalence of executable versions or gameplay.

Archive-set fingerprints (sorted case-normalized names and SHA-256 pairs):

- Steam: `06053a146c93b47e8be156d50fa97d4227ad1fa1c84af0c8858cf5e6e0cc9316`
- Reference: `297787005648c526123b4ddc4364e21c459300c37c1823fbaac0e539e8146cdd`

Detailed receipts remain private in build/retail-content-baseline. The latest
steam-catalogue.json and reference-catalogue.json include archive/decoder hashes,
per-entry provenance, all campaign sections/tokens and explicit decode states.
root-comparison.json captures the two-root comparison. Sanitized counts and
actual campaign-default regression results are retained in
local-builder/logs/retail-baseline-final-verification.log.

## Concrete admission correction

renegade_asset_manifest.py previously defaulted to M00 prerequisites. Its
general API/CLI now default to a campaign profile derived from the installed
retail campaign.ini, including required maps and Data-relative movies. Unknown,
empty, ambiguous or unsupported campaign requirements fail closed. Loose
campaign overrides require precedence review rather than silently trusting the
packed table. The current two datasets derive 28 required files: the incomplete
Steam dataset now fails specifically on m09.mix; the reference passes only the
file-availability check. Both explicitly report gameplay parity unverified.

The repair tool inherits this campaign preflight and refuses an incomplete
source before its first copy. A synthetic regression verifies that destination
bytes remain unchanged and no backup/copy step begins. The dedicated demo
helper explicitly requests m00 and records that campaign content is not checked.
Canonical/fast generated reports now label diagnostic packages and retain the
play-test hold, rather than advertising hardware-test readiness or generating
M00 play instructions. The canonical entry point stops before fresh integrated
host gameplay validation during the hold; explicit retained-log diagnostic
mode remains distinct. No regression suite was weakened or marked freshly
passed. A full feature-based promotion gate is still unfinished.

## Content and provider leads

tools/retail_gameplay_features.json seeds 50 player-visible requirements from
the installed publisher manual, with printed-page references. Examples include
secondary-objective rewards, EVA intelligence/data discs, item capacity behavior,
seat roles, repair/disarming, beacon interruption and production dependencies.
All remain OPEN; this seed is explicitly not exhaustive.

The English manual fingerprint is
`b48960cbb7d3449eb277da406410fff2f3436d578d9c25547f65d0ec1cc8bad4`.
The manual and extracted text remain local. No retail payload is published.

A first limited join of all discovered level bindings against every released
Scripts CPP (including files outside Scripts.dsp) and the matching dev246 ELF
found 998 distinct level-script names. The three known M11 names have no
released owner/defined factory in this join and remain OPEN. Other matches
prove only source/defined-factory presence, not registration, activation or
correct behavior. Definition-attached and dynamically attached paths still
need their own complete join and content-impact review.

Do not infer retail behavior from a single DLL search: the installed scripts.dll
has no tested positive-control mission labels and contains a Scripts2.dll name
lead. Scripts2.dll contains those positive-control labels. Static name searches
alone do not resolve the three M11 behaviors or establish the active provider
chain/version. Private evidence: script-library-labels.json and
level-owner-first-join.json. No third-party implementation was imported.

## Verification and next work

50 focused tests PASS, including retained binary readers and manifest deltas.
New counterexamples cover unknown scripts/verbs/classes/chunks, unsigned
32-bit tokens, duplicate member/campaign names, root overrides, CRC mismatch,
missing M09/movie requirements, bounded-census unsampled-node hashing,
ancestor/case identity separation, read-only CLI output protection,
pre-mutation repair rejection and the integrated host-play hold. Shell syntax
checks pass. These are host metadata/fixture checks, not native gameplay proof.

Next: join authored bindings and event/resource prerequisites to actual mission
sequences; build the complete independent feature catalogue and semantic stub
audit; verify retail/provider version provenance; implement shared all-content
admission for both workflows. Missing functionality, including subtitles and
audio effects, remains implementation work. Research is 37/100; play tests held.
