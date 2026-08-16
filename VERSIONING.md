# Versioning and evidence policy

`A<major>.<minor>` identifies an engineering milestone. `-devN` identifies an
internal candidate within that stream. A developer label is not a release,
baseline, or public capability claim.

An accepted physical baseline requires, at minimum:

1. a successful canonical host and ARM build;
2. preserved ELF, map, symbols, VPK inventory, hashes, source/patch identity,
   build log, and telemetry-only archive;
3. manual physical Vita installation and the relevant hardware-test evidence;
4. updates to the living reports and an immutable milestone record.

The authoritative records are:

- `reports/PORT_STATUS.md` — current program state;
- `reports/LIVE_PROGRESS.md` — current work and open evidence;
- `reports/HARDWARE_TEST_MATRIX.md` — physical gates;
- `reports/CRASH_SYMBOLICATION_INDEX.md` — dump/symbol identity;
- `reports/milestones/` — accepted or frozen historical evidence.

Tag only commits that correspond to a documented, physically accepted baseline.
Do not move or reuse a tag after publication. Internal candidates should retain
their `-devN` name and must not be promoted merely because host validation
passes.
