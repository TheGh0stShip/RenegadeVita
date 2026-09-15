# Original bitmap HUD atlas diagnostic

The retained original host runtime currently checks only that Font3D objects
exist. Both HUD source TGAs are 32-bit BGRA; a missing 16-bit conversion does
not explain the observed digits.

`probe.h` is an isolated, host-oriented diagnostic. Invoke
`Probe_Original_HUD_Digit_Atlas(font, filename)` immediately after the original
host runtime creates each Font3D instance, before releasing it or scaling it.
It uses the original surface loader, font metrics and packed texture surface.
For digits 0 through 9 it independently scans source alpha bounds, checks
character dimensions/UV placement and compares every packed A4R4G4B4 pixel
against source BGRA nibbles. It does not replace an engine owner or mutate
retail data. No candidate source includes this header yet.

A pass would establish CPU-side packing consistency only. Source orientation,
GPU upload/sampling, Render2D geometry and visible HUD correctness require
separate evidence. This is not a performance optimization or a visual fix.

## Retained host investigation

The probe compiles and links against the canonical ASan engine objects in an
isolated executable. It fails before comparing glyph pixels: original Targa
Open returns `TGAERR_READ` (-2), and the source surface is 0x0. On this LP64
host, `sizeof(TGA2Footer)` is 34, while Targa::Open seeks 26 bytes before EOF
and attempts to read that whole structure. The source header remains 18 bytes.
Consequently this run does not establish broken native Vita atlas packing.

Evidence is retained in `build/hud-font-probe-huUwW4/`: `tga-runtime.log`,
`tga-layout-result.log`, earlier failed probes and matching compile/link logs.
The first non-sanitized link also exposed stale host objects with an older
render-function signature; the ASan-linked probe avoided that mismatch.

`host-validation-entrypoints.patch` is a separate pending tooling correction.
It adds the non-sanitized interactive target to the canonical runner's build
list before that executable is used for M01/City checks, and supplies the
required dialog-resource header argument to the standalone dialog validator.
Both corrected shell-script copies pass shell syntax checks. The active
Dev115 build inputs were not changed. No Targa ABI or glyph-math correction
has been adopted from this experiment.
