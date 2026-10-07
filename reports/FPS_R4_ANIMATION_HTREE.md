# FPS round 4 — ANIMATION_HTREE (hierarchy animation cost)

Status: first slice committed (exact codegen changes + bit-identity test).
Nothing here is measured on hardware.

## Hypothesis

Skeleton evaluation for ~20 soldiers / ~15 vehicles (M13 ambush) spends
avoidable cycles in the per-pivot sampling path under the original
`HTreeClass::Anim_Update` / `Blend_Update`: out-of-line channel reads, a libm
`floorf` per sampler call, and double-precision diagonal terms in
`Build_Matrix3D`. All three can go without changing a single output bit.

## Evidence

- Retail format census (`local-builder/retail-host/Data`): `always.dat` has
  1,704 raw (`W3D_CHUNK_ANIMATION`), 20 timecoded and **0 adaptive-delta**
  anims; M13.mix 49 raw / 2 timecoded; M01 50 / 1. The hot path is
  `HRawAnimClass` + `MotionChannelClass::Get_Vector`. Adaptive-delta
  pre-decoding or a timecoded key hint would not pay (timecoded already has
  `CachedIdx` + look-ahead + binary search, `motchan.cpp` `get_index`).
- Skeletons: `S_A_HUMAN` 23 pivots (594 anims), `S_B_HUMAN` 24, transports 17.
  7,962 of 19,389 animated nodes carry translation channels; the rest are
  rotation-only.
- Per pivot (`htree.cpp` Anim_Update): `Matrix3D::Multiply` call; virtual
  `Get_Translation`, `Get_Orientation`, `Get_Visibility`; `Build_Matrix3D`
  call; inline Translate + `operator*`. Blend doubles the sampling and adds
  a `Fast_Slerp`.
- Baseline ARM codegen (-O3, fast-build-graph flags): `HRawAnimClass` samplers
  call `floorf`, then out-of-line `Get_Vector` (2 calls in Get_Orientation,
  6 in Get_Translation, 11 in Get_Transform). `Build_Matrix3D`
  (`quat.cpp` L829/L839) keeps two f32→f64→f32 chains (9 f64/convert ops)
  for m[0][0]/m[2][2]; GCC had already narrowed the other elements.
- Between consecutive keys, `Fast_Slerp` nearly always calls `acosf`
  (`Fast_Acos` falls back to libm when |cos| > 0.975). That is original
  math, so it was left alone.
- Revalidation: `Set_Animation`, `Set_Transform` and `Control_Bone` each
  invalidate the whole tree, and `Get_Bone_Transform`/`Render` then rerun the
  full update. Combat order (combat.cpp L734-790) is Think → Scene (physics
  moves models) → Camera → Post_Think (`AnimControl->Update` →
  `Set_Animation`) → render. A revalidation with unchanged animation state can
  therefore happen; how often is unmeasured. No port patch adds per-frame
  animation work (checked raw-animation-frame-floor, hanim-combo guard,
  prim-anim patches).
- Skin deform is ~0.2-0.45 ms/frame (SKIN_PATH_COST.md) and belongs to the
  SKIN_* slugs, so it is unchanged here.

## Change made (default on, no switch; outputs bit-identical)

1. `port/patches/ww3d2-a36-raw-anim-sampler-inline.patch`:
   `MotionChannelClass::Get_Vector` moved into `motchan.h` as `WWINLINE`
   (adds `#include "wwdebug.h"` for its `WWASSERT`). The raw-data copy is the
   original loop unrolled for VectorLen 1 and 4, the only W3D widths; any
   other width still runs the original loop. The unroll is needed because when
   the loop was inlined verbatim, GCC turned it into `memcpy` calls (the local
   destination no longer aliases `Data`). In `hrawanim.cpp`, the three
   `static_cast<int>(WWMath::Floor(frame))` key selections now call
   `Raw_Anim_Frame_Floor(frame)`. On `[0, 2^31)` it returns
   `static_cast<int>(frame)`, where floor equals truncation. Every other input
   (negative, huge, NaN) still evaluates the original expression.
2. `port/patches/wwmath-a36-build-matrix3d-float-diagonal.patch`:
   `Build_Matrix3D` m[0][0]/m[2][2] `2.0 *` → `2.0f *` (the form original
   m[1][1] already has). Doubling is exact in both precisions. GCC then
   narrows the outer `1.0 - x` itself, and it does that only when exact.
   Even without the narrowing, rounding one float subtraction through double
   is innocuous (53 ≥ 2·24+2), and overflow, NaN and flush-to-zero give
   identical results.
3. Both patches are registered in `tools/stage_sources.sh`, after
   `wwmath-a36-fabs-vabs` and `ww3d2-a36-sorting-depth-sort-and-runs`. Staged
   files are updated identically. Each patch dry-runs `-F0` clean against the
   pre-change staged files and reproduces them byte for byte.
   `PATCH_INVENTORY.json` is untouched. Source-contract tests that pinned the
   old floor text were updated (`tools/test_raw_animation.py`,
   `tools/test_vita_m13_cinematic_preparation.py`).

## Risk and invalidation argument

No caching was added, so nothing needs invalidating. Each change is a pure
codegen transformation: (1) copies the same elements and its floor helper
gives the same integer for every float input (-0.0, negatives, NaN,
out-of-range); (2) is exact arithmetic.

Residual risk is build-only: `motchan.h` now includes `wwdebug.h`, and its
users (hanim, hrawanim, hcanim, motchan) all ARM-compile.

## Tests (all PASS)

- New `tools/test_vita_raw_anim_sampler_identity.py` (+
  `tools/vita_raw_anim_sampler_identity_test.cpp`) builds the real staged
  `hrawanim.cpp`, `motchan.cpp`, `quat.cpp`, `htree.cpp`, `pivot.cpp` and a
  copy with both patches reversed (`patch -R -F0`). It drives 100k
  `Build_Matrix3D` calls (denormal/huge/inf/NaN components) and 24,000
  samples over 120 random trees/raw anims (missing channels, ranges beyond
  NumFrames, identical/opposite/near/far quaternion keys, vis bits; negative,
  wrapping, ±0, 2^31-edge and 1e30 frames) through all four samplers,
  `Anim_Update` and `Blend_Update`. The two output streams (> 5 MB) match
  byte for byte at -O2 and under ASan+UBSan. Mutation checks (wrong floor
  bound, re-associated m[0][0]) are detected. Command:
  `python3 -m unittest tools.test_vita_raw_anim_sampler_identity` (~2.5 min).
- `python3 -m unittest tools.test_raw_animation
  tools.test_vita_m13_cinematic_preparation.RuntimeInstrumentationContracts.test_raw_animation_samplers_use_portable_lower_key
  tools.test_vita_hanim_combo_guard`: 7 tests OK. These ran with the
  temporary `upstream/CnC_Renegade` symlink, removed afterwards.
- ARM TU compiles (VitaSDK GCC 15, -O3): hrawanim, motchan, hcanim, hanim,
  quat. objdump: `Build_Matrix3D` 81 → 76 insns, 9 → 0 f64/convert ops;
  no `Get_Vector` calls left in the raw samplers; `floorf` only on the
  negative/huge/NaN branch; 1/4-wide copies are plain loads/stores (only the
  unused-width fallback loop may still become `memcpy`).

## Expected gain (estimate, unmeasured)

Rough Cortex-A9 model, ~550-650 cycles per animated pivot before: saves ~2
`floorf` calls (~25-35 cycles each), 2-11 call/reload sequences (~10-15 each)
and ~20 cycles of double conversion per `Build_Matrix3D`. Roughly 15-20 % of
hierarchy sampling, very roughly 0.1-0.4 ms/frame in the M13 ambush (more when
soldiers blend). Animation is not the dominant Combat cost.

## Not done / next steps

1. Memoise samples when the animation state is unchanged (largest exact
   lever; measure first). Add a sampled counter in
   `Animatable3DObjClass::Update_Sub_Object_Transforms` for updates per frame
   and those whose (mode, motions, frame/percentage bits) equal the object's
   previous update. Only if repeats exceed ~30 %: cache per pivot in
   `HTreeClass` the pre-scale translation, quaternion and visibility, keyed on
   a never-reused `HAnimClass` serial (pointers are reused after free) plus
   the frame/percentage bits, for `HRawAnimClass` only; replay the unchanged
   Multiply → Translate → `Build_Matrix3D` → `operator*` sequence so output
   stays bit-identical.
2. When more than two anims blend, `HumanAnimControlClass::Update` allocates
   one `HAnimComboDataClass` per anim per frame. This belongs to HEAP_CHURN.

## Hardware measurement to take

M13 ambush with a fixed replay and camera: compare frame-profile `Combat` and
`Post Think` median/p95 before and after, plus the revalidation counter above
if it is added. Expect at most a few tenths of a millisecond on Combat.
