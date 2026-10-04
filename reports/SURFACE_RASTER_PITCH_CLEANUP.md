# Surface raster pitch failure cleanup

The Vita SurfaceClass boundary now releases every successfully acquired lock
when a raster operation rejects its row pitch. Clear, byte-copy and FindBB
previously returned with the provider locked on some invalid pitches;
rectangle-copy did not validate either provider's pitch before using it.

The correction validates positive pitch and sufficient storage for a complete
row using division, avoiding width multiplication or narrowing in the check.
It preserves original SurfaceClass ownership, valid padded-row behavior,
rectangle clipping, pixel conversion and untouched padding. Failed locks are
not unlocked. No render loop, gameplay or asset-format owner changes.

## Validation

- The retained test failed against the pre-correction production bodies at the
  counted-lock assertion. It executes the production raster bodies and format
  enumeration, with a counted provider replacing only lock/storage services.
- Nineteen cases pass ASan, LeakSanitizer and UBSan outside the tracing sandbox:
  negative/zero/short pitches, failed locks, padded clear/copy rows, rectangle
  failure cleanup, successful subrectangle copy, ARGB conversion and FindBB.
- The focused gate passes all 492 tests. The new regression runs in both the
  canonical and fast build gates. An initial traced run could not run existing
  LeakSanitizer tests; the unchanged gate passes outside tracing.
- Installed GCC 15.2.0 reports ARMv7, little endian, 32-bit long/pointers and
  hard-float calling conventions. Dev226 passes all 651 ARM compile/link
  actions and artifact checks. The ELF is ELF32 little-endian ARM/EABI5,
  ARMv7/Thumb-2 with VFP-register arguments. The existing mixed wchar_t linker
  warning remains open; these checks do not establish complete dependency ABI
  or physical correctness.

Retained candidate identities:

| Artifact | SHA-256 |
|---|---|
| Dev226 ELF | `23bbb3f7cf03f15a5f9319527430784410e50df25a085346b61063239225eb8b` |
| Dev226 map | `7e5585091029ae88c1793e70ab7d36eebd35d359646e75beae9bce8014d91ed2` |
| Surface boundary source | `c536a6cc367e2298f15a7a894e802bb534e278b3ab7db0ec65ba82abef322887` |

The harness does not validate native surface allocation, GPU upload, repeated
actual texture ownership or rendered glyphs. Canonical packaging, installed
artifact verification and physical Vita/PSTV acceptance remain open. No game,
emulator or physical device was launched for this correction.

## Source and retained regression

- `port/renderer/vita/surface_boundary.cpp`
- `tools/test_vita_surface_lock.py`
- `tools/vita_surface_lock_test.cpp`
- `tools/build.sh` and `tools/build_fast_candidate.sh`

Reproduce the focused production-method test outside a tracing sandbox:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_vita_surface_lock
```

Next: retain native allocation/upload and physical text/effect checks as
separate acceptance requirements; continue original material/UV/specular
and renderer ownership work.
