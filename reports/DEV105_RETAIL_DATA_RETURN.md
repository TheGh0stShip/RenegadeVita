# Dev105 retail-data repair and runtime return

## Closed local installation checks

- Current authoritative local source: E:/SteamLibrary/steamapps/common/Command
  & Conquer Renegade/Data, identified through Steam library/install metadata.
- All 51 source files now have byte-identical SHA-256 matches in the emulator.
  The emulator contains 53 files: pre-existing keys.cfg and M09.mix are retained
  as extras, not removed or misrepresented as source-verified content.
- Added only the missing always.thu and always2.thu. Their receipts record
  destination absence before copying and matching source/installed hashes.
  No existing retail file was changed and no retail bytes were redistributed.
- All 31 installed MIX-style archives passed header, index ordering, filename
  CRC mapping and payload-bounds checks. This is structural verification, not
  proof that every asset is playable or semantically correct.
- The original host MixFileFactoryClass separately indexed always.dat and
  returned its hd_reticle.dds filename entry among 15161 entries.
- The stale retail-pc symlink was backed up and redirected from the absent C:
  install to the current E: install. Link-target receipts are retained.

Evidence: build/dev105-host-evidence/retail-repair/, retail-link-repair/,
retail-original-owner/, retail-probe-classification.json.

## Native source correction and exact runtime proof

Original Game_Init searches loose Data files before archive fallback. The
native factory list lacked that Data read root. Dev105 now adds it using the
existing rooted file factory and original FileFactoryList, preserving archive
order, explicit namespaces, writable roots and original MIX ownership.

Dev105 fast ARM/package closure passed 126 contracts. SELF:
fba11aeb090b5ea018b43cdf2f97ce20cc8c68da5c9fb4b4b14288efd46bf5fe.
Matching Vita3K startup emitted all three successful original-owner reads:

```
logical=stylemgr.ini opened=1 bytes=4 readable=1 backing=stylemgr.ini
logical=WWAudio.ini opened=1 bytes=4 readable=1 backing=WWAudio.ini
logical=hd_reticle.dds opened=1 bytes=4 readable=1 backing=Data\Always.dat
```

The reticle probe also checks the DDS signature. This proves the actual game
opened and read the archived asset, not merely a host index or loose file.
It does not prove full texture upload, visual HUD correctness, or full M00.
Retained snapshot/hashes: build/dev105-host-evidence/retail-runtime-return/.

prepare_vita3k_demo.py now requires complete source-file hash coverage before
installing a candidate, rather than treating six prerequisite files as proof
of a complete installation. It preserves extras and records runtime proof as
false independently of installation checks.

## Remaining lookup classifications, not fabricated missing assets

The Dev104 emulator log contained 431 distinct failed loose-path probes.
Most have exact archive or DDS-alias matches. Six further DDS probes have
original TGA assets in always.dat. Lightmap pseudo-directory probes have
archived children (tut_lm015+ and mgbar_int_lm001+); directory absence does not
mean those children are missing from MIX.

ARI/Arial probes use the already installed local user-font fallback; Dev104
font probes passed. Do not package or relocate the private font into retail.
M00_Tutorial.ddb is absent from the source and original M00 layout; do not
synthesize it. subtitle.ini is absent from the source and is an optional
startup probe. Original HumanAnimControl tries alternate skeleton animation
names and retains the original name when absent; the H_B animation misses
must not be addressed by inventing or renaming retail animations.

One malformed W3D-name request in Dev104 remains an engine-side diagnostic
lead, not a source-file copy gap. Its cause and any gameplay impact are not
established. Complete source coverage does not close this separate issue.

## Updated emulator retry

The first Dev105 launch command used a literal shell-variable suffix in its
evidence path. Its actual retained directory is
D:/Vita3K/RenegadeEvidence$rv_run/ (PID 7088), not the intended timestamp name.
Its receipt ended at 2026-09-08T22:32:33.5825567Z. No input was injected.
Do not discard or mislabel this evidence.

User updated Vita3K. The updated executable SHA-256 is
c5976240add4cf7219d27f12abdfeab29eef69a1dac9aee398d9ed027478b0fe.
The same installed Dev105 SELF was checked and a separate 900-second run
started at D:/Vita3K/RenegadeEvidence/Dev105-updated-20260908T223341Z/.
This run is pending assessment. No physical Vita/PSTV access occurred.
