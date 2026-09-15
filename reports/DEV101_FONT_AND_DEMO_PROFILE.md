# Dev101: user-font prerequisite and separate demo profile

Date: 2026-09-08. Durable destination: the complete native Renegade Vita port.
The M00 community demo is an interim showcase, not the final scope.

## Matching Dev100 evidence

Dev100 fast and canonical builds passed after the remaining M01 cache-health
reference was removed. Canonical current contracts passed 148 tests; retained
host semantic evidence is not a new complete tutorial run. Canonical artifacts:

- VPK: `21ce6f926ae751b0289cd59ada6699e87ee10269bf177b866164164e344df1a9`
- ELF: `7a963bdb0d8b731995b1bd24fbcc72ea3b8202b3013cc0e9a354b120c991526f`
- SELF: `08bfad672426dc884313280598b651a52a212e63427a3a551a58d3cd496733dc`

The separate fast-package Vita3K observation used SELF
`b92efbac9133c36ca4fd9dded2082102610b7075f7bdee07fbb548d80ca56930`.
Its exact ELF/SELF/VPK/map/symbols and dependency provenance are retained under
`build/dev100-host-evidence/fast-candidate/`. Do not use the canonical SELF
hash to describe this emulator run.

Emulator evidence is under
`D:\Vita3K\RenegadeEvidence\Dev100-fast-20260908T201856Z`.
The 90-second runner ended `TIMEOUT_UNASSESSED`, but the application log
records a controlled failure at initial StyleMgr validation, not a demonstrated
hang. Title/menu Regatta glyph probes passed; Arial-based controls, lists,
credits and in-game text probes returned zero widths. The runtime refused to
continue to a blank-text frontend. The one foreground screenshot at ten
seconds shows the emulator's loading window, not the original main menu.

The emulator log reports missing Arial font candidates. This establishes an
emulator prerequisite gap; it does not prove that every earlier physical
missing-text symptom had the same cause. No intro playback or M00 completion
was observed in this run. The runner touched no physical device and sent no
synthetic inputs.

## Dev101 source changes

- `RENEGADE_VITA_M00_DEMO` controls the M00-only launch restriction and
  success/fade/message/credits policy. Both build scripts expose it through
  `RENEGADE_M00_DEMO=1` (demo) or `0` (full-port development).
- Generated identity and runtime logs identify `M00-DEMO` versus
  `FULL-PORT-DEVELOPMENT`. Default candidate identity advances to Dev101 to
  preserve the completed Dev100 artifacts and emulator evidence.
- The full-port profile removes only demo policy. It does not claim that all
  later missions already work; current campaign/resource/networking gaps
  remain tracked by the charter and roadmap.
- Credits explicitly identify the native port as the Renegade Vita project's
  work, distinct from the original EA/Westwood game and dependencies.
- The original FileFactory/FreeType boundary retains retail font priority,
  then tries `user/fonts/ARI_____.TTF` and `user/fonts/arial.ttf` for Arial.
  Font reads are capped at 16 MiB before allocation. Successful faces retain
  the existing cache, glyph sizing, rasterization and lifetime owners.

The user's local Windows Arial was placed only in the emulator's user-font
namespace, with a candidate-scoped provenance receipt at
`D:\Vita3K\RenegadeEvidence\A3.5-dev101-user-font-20260908T202445Z`.
No retail file or archive was altered, and no font bytes were packaged or
redistributed. Local font backups and raw config are private setup material,
not public telemetry.

## Next evidence

Dev101 fast/canonical builds run in the background. After exact package
closure, install only the matching emulator title and repeat the bounded
intro/menu observation with the user font available. Record glyph probes and
matching images; do not infer visual correctness from logs. The non-demo ARM
configuration has not yet been independently compiled. All physical, complete
M00, credits/exit, and 60 FPS+ release gates remain open.
