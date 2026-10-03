# External reference inventory (S8)

The initial inventory compares every blob path in the union of pristine EA
commit `3e00c3a1b97381bb28be89a35b856375e0629a08` and OpenW3D commit
`89cfaaffe7d9245eb22f41882cfc0167c4d9f6d9`.
There are 3,782 rows: 2,830 different blobs, 652 identical blobs, 145 EA-only
paths and 155 OpenW3D-only paths. All rows are `unknown`; none establishes a
bug fix, runtime ownership change or adoption recommendation. Non-code files
remain in the denominator to avoid silently discarding build/configuration work.

The [canonical OpenW3D repository](https://github.com/w3dhub/OpenW3D) identifies
itself as a continuation of the EA release and lists SDL3, OpenAL Soft, FFmpeg,
FreeType and other dependencies. Its project license is GPLv3 with additional
terms. Individual notices and compatibility still need checking before adoption.
Only path/blob metadata was retained; no external source was imported or run.

Reproduce with a GitHub recursive-tree receipt for the pinned commit:

```
python3 -m tools.audit_sweep_external --reference-tree TREE.json --reference-commit 89cfaaffe7d9245eb22f41882cfc0167c4d9f6d9 --output reports/generated/sweeps/external.json
```

The tool rejects truncated trees, duplicate paths and identity mismatches.
Two tests cover unchanged/changed/new/removed paths and incomplete inputs.
Two generations reproduce byte for byte. Source bodies and current port patches
still need compiler, ABI, threading, renderer and audio comparison.

The [official TT downloads page](https://www.tiberiantechnologies.org/downloads)
lists scripts 4.8 Update 4 revision 9000 and reference archives. This listing does
not authorize importing proprietary engine implementations. Existing local TT
audits remain separate evidence. A changelog-based denominator, W3DHub engine
5.x comparison and mod-derived failure classes remain open; community changes
require an explicit keep-retail/consider-fix decision before adoption.

Retail 1.037 behavioral disagreements still require matching private executable
identity, independently verified Ghidra addresses and original-owner comparisons.
No decompiled code or binary payload belongs in this inventory. The sweep is
incomplete and does not establish whole-engine portability coverage.
