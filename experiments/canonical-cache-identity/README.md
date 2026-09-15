# Canonical retry cache identity

Status: isolated, reproduced; not integrated into canonical flags.

During Dev111 r6, the existing native ccache showed 30 hits and 72 misses from
102 cacheable calls. Each canonical retry configures a new timestamped build
directory. The installed ccache manual documents that debug compilations hash
their working directory unless a matching base directory and debug prefix map
are supplied. Do not disable this protection with CCACHE_NOHASHDIR: that can
reuse objects with incorrect debug paths.

`replay.sh` uses the actual ARM compiler with debug information and isolated
caches. The baseline compiles identical source from two sibling directories:
two misses. Mapping each working directory to one stable sibling debug context
produces one miss followed by one direct hit. Both mapped object files are
byte-identical, and baseline/mapped .text bytes match. The DWARF compilation
directory names the stable context, from which ../source.cpp resolves correctly.

Retained run: build/dev111-host-evidence/canonical-cache-replay.log and its
canonical-cache-replay/ directory. This is one fixture, not a measured full
canonical-build speedup or a gameplay optimization.

Potential adoption in the next source batch: a debug-only prefix map from each
native binary directory to an existing stable directory at the same filesystem
depth, beneath build/. Preserve original source paths, candidate-specific
identity strings, matching ELF/map/symbol artifacts and normal cache safety.
Validate representative original and boundary objects and source resolution
before adopting. Do not change current in-flight build flags or compile mode.
