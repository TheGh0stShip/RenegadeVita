# Dev113 buffered rewind correction

Corrected original BufferedFileClass::Seek through a generated, registered,
zero-fuzz staging patch. Before discarding unread buffered data for a negative
SEEK_CUR, the base cursor is restored to the logical position. The requested
negative offset is then applied normally. Separate seeks avoid signed offset
overflow; a failed cursor restoration is returned without dropping the buffer.
Absolute/end-relative seeks and forward buffered consumption retain their
existing paths. No soldier null guard or save-state omission was introduced.

Changed authoritative files:

- `port/patches/wwlib-a35-buffered-relative-seek.patch`
- `tools/stage_sources.sh`

Evidence:

- Full zero-fuzz staging passed: 162 ordered patches, derived inventory.
- Patch identity: `eeee8db620ad458b973917e784cb667b835bc92493e14d3f986186e07a2ff6a2`.
- Isolated ARM bufffile.cpp compilation passed.
- The same ASan interactive M00 fixture that previously crashed now passes
  both in-process cycles with the new conversation compatibility reader active.
- Evidence is retained under `build/dev113-buffered-seek-fix/`, including
  `stage.log`, `arm-compile.log`, and `asan-return.log`.

Next: full dev113 canonical retry, then the already queued unchanged post-Sydney
checkpoint in Vita3K. Native reload, pause and mission ending are still unproven.
Preserve the failed dev113 host log and all dev112 native artifacts.
