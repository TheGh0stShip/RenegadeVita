# FPS R4 — WWMATH_ARM: ARM VFP replacements for x86 math fallbacks

Status: implemented and committed; host-proven bit-identical (exhaustive);
ARM TUs compile. Not measured on hardware.

## Hypothesis
The x86 asm/MSVC helpers in `wwmath.h` fall back on Vita to code that calls
newlib out of line (floorf/ceilf: VFPv3 has no VRINTM/VRINTP), performs two
VFP compares + `VMRS APSR_nzcv` flag transfers per float->int range check, or
promotes float math to double. Bit-identical ARM-friendly forms remove the
calls, stalls and f64 ops from per-bone/per-frame animation paths.

## Evidence (ARM objdump, VitaSDK GCC 15.2, real TU flags, -O3)
- `WWMath::Floor/Ceil` = `floorf/ceilf` (staging/wwmath/wwmath.h:163-164 before)
  -> `bl floorf` in `HRawAnimClass::Get_Translation/Get_Orientation/Get_Transform`
  (staging/ww3d2/hrawanim.cpp:476,533,586 — per bone per frame), 9 mapper
  `Apply()` paths (mapper.cpp), lookuptable.h:92, colorspace.h:102. newlib
  floorf itself = ~20 insns incl. a `VADD/VCMPE/VMRS` "raise inexact" check;
  the call also forces `vpush {d8}`/spills in the caller.
- `Float_To_Int_Chop/Floor` (wwmath.h:620,633; a35 portable version) compile
  to 2x `VCMP`+`VMRS` for the range check (+1 VMRS for floor). Inlined into
  `Fast_Sin/Fast_Cos/Fast_Acos/Fast_Asin`; `Fast_Slerp` (quat.cpp:441, used by
  HTree blending) had 16 VMRS.
- `Build_Matrix3/3D/4`, `Matrix3D::Set_Rotation(Quaternion)`, `Matrix3::Set(Quaternion)`
  (quat.cpp:805-875, matrix3d.cpp:215, matrix3.cpp:159): `(float)(1.0 - 2.0*s)`
  kept 2 of 9 elements in double (`vcvt.f64.f32, vadd.f64, vsub.f64,
  vcvt.f32.f64`). GCC had already narrowed the other 7 itself (its convert.c
  double-rounding rule); `Build_Matrix3D` is called 5x in htree.cpp per bone.
- No libm sin/cos replaced original tables: `Fast_Sin/Cos/Acos/Asin` still use
  `_FastSinTable/_FastAcosTable`. `WWMath::Sqrt` already inlines to `vsqrt.f32`
  (C++ `sqrt(float)` overload + `-fno-math-errno`); `Acos/Asin` resolve to
  `acosf/asinf` via the C++ float overloads (current Vita behaviour, unchanged).
- Compat headers: `__forceinline` = `inline __attribute__((always_inline))`;
  `WWINLINE` is plain `inline` on GCC (always.h:85-89). At -O3 (wwmath/ww3d2/
  wwphys) every WWINLINE helper checked was inlined; out-of-line calls that
  remain (`Matrix3D::Multiply`, `Build_Matrix3D`, `Fast_Slerp`) are original
  .cpp functions, not header helpers. `_isnan`->`isnan`; no `_ftol` users.
- FPSCR: the startup FPSCR log (port/platform/vita/a30_main.cpp:151-159) has
  never returned from hardware (no `FPSCR:` line in device evidence), so FZ/DN
  are unknown. NEON (always flush-to-zero) is therefore NOT used anywhere.

## Changes (staging + zero-fuzz patches, registered after wwmath-a36-fabs-vabs)
1. `port/patches/wwmath-a36-arm-int-floor-helpers.patch` (wwmath.h)
   - Vita: `WWMath::Floor/Ceil` = inlined newlib sf_floor.c/sf_ceil.c integer
     algorithm (only Inf/NaN take `x+x`, the same VFP op newlib uses).
     Non-Vita builds keep `floorf/ceilf`.
   - `Float_To_Int_Chop/Floor`: range test `(bits & 0x7FFFFFFF) >= 0x4F000000`
     (|f| >= 2^31 or NaN; -2^31 maps to INT32_MIN either way) replaces the two
     float compares. Floor keeps its single VFP compare for the negative
     fraction fix-up, so denormal handling still follows FPSCR.FZ exactly as
     before.
2. `port/patches/wwmath-a36-quat-matrix-single-precision.patch`
   (quat.cpp, matrix3d.cpp, matrix3.cpp): `(float)(1.0 - 2.0*(s))` ->
   `1.0f - 2.0f*(s)`, `(float)(2.0*(d))` -> `2.0f*(d)`.

## Why bit-identical (invalidation argument)
- Floor/Ceil: integer bit algorithm equals newlib's for all 2^32 inputs; the
  removed `huge+x>0` test is always true on the paths where it was evaluated
  (|x|<2^23) and only raised the inexact flag. Integer ops are FPSCR-independent.
- Chop/Floor: identical partition of inputs; in-range conversion unchanged.
- Quaternion matrices: `2*s` is exact (or overflows to Inf identically, since a
  float > FLT_MAX/2 is >= 2^127); `1 - 2s` rounded to double then float equals
  direct float rounding because 53 >= 2*24+2 (Figueroa double-rounding
  theorem — the same rule GCC already applied to m[1][1]); results near 1
  cannot be subnormal, so FZ cannot differ. ARM codegen: new m[0][0]/m[2][2]
  = `vadd.f32; vsub.f32` exactly as GCC already emitted for m[1][1]; VSUB
  returns a NaN operand unchanged like the old VSUB.F64, so NaN bits match
  under DN=0 and DN=1.

## Codegen delta (instruction count / VMRS / f64 / libm calls, -O3)
| function | before | after |
|---|---|---|
| Fast_Slerp | 255 insn, 16 VMRS | 224 insn, 8 VMRS |
| Build_Matrix3D / 3 / 4 | 81/77/84 insn, 9 f64 each | 76/72/79 insn, 0 f64 |
| HRawAnim Get_Orientation | `bl floorf` + `vpush {d8}` | inline, no call/spill |
| HRawAnim Get_Translation / Get_Transform | `bl floorf` | inline |
| Float_To_Int_Floor (isolated) | 3 VMRS | 1 VMRS |
| Float_To_Int_Chop (isolated) | 2 VMRS | 0 VMRS |
| Matrix3D::Set_Rotation(Quaternion) / Set(Quaternion,Vector3) / Lerp | 9 f64 each | 0 f64 |
| mapper Linear/ZigZag/Step/Screen/Edge/SineLinear Apply | 1-2 `bl floorf` each | inline |

## Tests (host x86-64 GCC 13; ARM = VitaSDK GCC 15.2 with recorded TU flags)
- `RENEGADE_WWMATH_EXHAUSTIVE=1`-equivalent run of the new
  `tools/test_wwmath_arm_equivalence.py`: all 2^32 float bit patterns, IEEE
  pass and FTZ|DAZ pass (x86 analogue of FPSCR.FZ; DN=1 is not emulable on x86
  and is covered by the instruction-level argument above): Floor/Ceil bit-identical
  to the newlib sf_floor.c/sf_ceil.c algorithm, Float_To_Int_Chop/Floor equal
  to the a35 code; 6,022,528 quaternions per pass (special-value grid incl.
  ±0, denormals, FLT_MIN, FLT_MAX, 2^127, Inf, NaN payloads; random bit
  patterns; unit quaternions; near-cancellation) bit-identical for
  Build_Matrix3/3D/4, Matrix3D::Set_Rotation, Matrix3::Set. PASS (321 s).
- Default `python3 -m unittest tools.test_wwmath_arm_equivalence` (every 13th
  pattern + ASan/UBSan/float-cast-overflow build at stride 4099): 3/3 PASS.
- Negative controls (perturbed Old_Floor, perturbed reference m[0][0]) make
  the harness FAIL as required.
- `python3 -m unittest tools.test_raw_animation`: PASS. `tools.test_m09_camera`
  fails identically without this change (staged Mission09.cpp save/load
  additions vs the experiment; listed in HOST_TEST_TRIAGE_2026-10-06.md).
- ARM TU compiles OK: staging/wwmath/{quat,matrix3d,matrix3}.cpp,
  staging/ww3d2/{htree,hrawanim,mapper}.cpp, staging/wwphys/{pscene,phys3}.cpp,
  staging/combat/soldier.cpp (-O2 TU: no WWMath/Vector3/Matrix3D header
  helper is emitted out of line, so WWINLINE=`inline` is sufficient).
  (Shared arm_tu_check.sh doubles the worktree prefix on `-c` paths because
  `$wt` lies under `$main`; an object-keeping copy without that sed ran.)
- `patch -p1 -F0 --dry-run` of both patches against the pre-change staged
  files: clean; applying them reproduces the committed staging files exactly.

## Not changed (documented divergences / no bit-identical win)
- `Float_To_Long(float/double)` truncates (vcvt) while x86 `fistp` rounded to
  nearest. Project already corrects live sites (hud.cpp:2572,2644 lrintf;
  hrawanim.cpp:475 Floor). Remaining callers: timemgr.cpp:125 (frame-time
  histogram, diagnostics), lookuptable.h:110 `Get_Value_Quick` (unused),
  visrasterizer.cpp (Ceil'd integral inputs: identical), bwrender.cpp
  (shadow rasteriser, ±1 pixel). Left as is: semantic, not performance.
- `Sin/Cos/Atan2/Acos` stay libm (no bit-identical inline form); `Inv_Sqrt`
  stays `vsqrt+vdiv` (VRSQRTE+Newton is not identical); `Build_Quaternion`
  keeps `sqrt(double)` (narrowing not exact).

## Expected gain (UNMEASURED estimate)
Per call ~15-30 cycles (floorf call) / ~8-15 cycles (VMRS pairs) / ~10 cycles
(f64 chain). With ~20 soldiers + vehicles animating, a few thousand calls per
frame: roughly 0.1-0.3 ms/frame of the ~14 ms sim + animation, i.e. <1%.

## Hardware measurement
Same M13 ambush capture as dev238; compare frame-profile animation/HTree and
sim stage medians, p95, p99 before/after; also confirm the `FPSCR:` startup
log line (FZ/DN) — that line is the prerequisite for any future NEON work.
Runtime/compile switch: none (default-on; revert = drop the two patches).
