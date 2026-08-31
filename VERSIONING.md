# Versioning and evidence policy

`A<major>.<minor>` identifies an engineering milestone. `-devN` identifies an internal candidate. A candidate label, source test, or successful package is not a release or a physical capability claim.

## Physical acceptance

A physical baseline requires:

1. canonical host and ARM/package closure;
2. matching VPK, ELF, map, symbols, source/patch identity, hashes, and diagnostics;
3. observed physical Vita behavior for the declared gate; and
4. durable status and immutable milestone records.

Tag only a documented, physically accepted baseline. Never move or reuse a published tag.

## Evidence labels

- **Source/build validated**: owner, code, or artifact closure only.
- **Vita3K observed**: emulator-only signal.
- **Physical return**: matching hardware observation, not necessarily acceptance.
- **Accepted physical baseline**: matching evidence passes the declared gate.
- **Failed/superseded**: retained evidence that must not be relabelled as success.

Authoritative records are [PORT_STATUS](reports/PORT_STATUS.md), [LIVE_PROGRESS](reports/LIVE_PROGRESS.md), [HARDWARE_TEST_MATRIX](reports/HARDWARE_TEST_MATRIX.md), [CRASH_SYMBOLICATION_INDEX](reports/CRASH_SYMBOLICATION_INDEX.md), and [milestones](reports/milestones/).
