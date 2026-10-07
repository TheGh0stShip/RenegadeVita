# FPS round 4: CODEGEN_FLAGS (Cortex-A9 code generation, simulation side)

Scope: value-preserving compiler/link flags for the sim (~14 ms/frame, Combat ~13.3 ms on dev238
hardware). Nothing was timed on hardware. All evidence is ARM codegen from VitaSDK GCC 15.2 using
the recorded build flags plus `-fno-math-errno -fno-trapping-math`.

## Hypothesis

Combat, Commando and WWLib build at RelWithDebInfo `-O2`; WW3D, WWMath, WWPhys, renderer and
audio build at `-O3`. Moving the sim modules to `-O3`, or adding other Cortex-A9 flags, might cut
sim CPU without changing semantics.

## Baseline facts

- Toolchain defaults (`-Q --help=target`): `-march=armv7-a+simd -mtune=cortex-a9 -mfpu=neon
  -mfloat-abi=hard -mthumb`. The stack protector is off and `-fPIC` is not used. The game target
  passes no `-mcpu` or `-mtune`.
- The target already builds with `-fno-strict-aliasing -fno-exceptions -fno-rtti
  -ffunction-sections -fdata-sections -fno-math-errno -fno-trapping-math` and links with
  `--gc-sections`.
- GCC processes `-O` levels before explicit `-f` flags. With `-O2 -fno-strict-aliasing ... -O3`,
  strict aliasing stays off and a per-TU `-fwrapv` stays on (checked with
  `-Q --help=optimizers`). A trailing per-source `-O3` therefore adds no aliasing or overflow
  assumptions.
- Release validation is compiled out. `-dM` on soldier.cpp shows `NDEBUG` and neither `WWDEBUG`
  nor `_DEBUG`, so `WWASSERT` and `WWDEBUG_SAY` expand to nothing. The remaining
  `Is_Valid_Float`/`Is_Valid()` uses (humanphys.cpp:626-695, rbody.cpp:754-1318,
  phys3.cpp:600/1540, soldier.cpp:1242) are original control flow, not asserts. They compile to
  VMOV plus a mask compare and must stay.

## Per-flag decisions

| Flag | Decision | Evidence |
| --- | --- | --- |
| `-O3` Combat / WWLib | A/B option, default OFF | sections below |
| `-O3` Commando | Rejected | cNetwork ~0.5 ms, control ~0.3 ms of sim; no hot-loop TU |
| `-fno-strict-aliasing` | Keep (required) | wwmath.h:203 `*(int *)(&val)`; hashtemplate.h:59; FastAllocator.h:456-504; datasafe.h:4080-4301; vector2i.h:89/vector3i.h:86 `((int*)this)[n]`; meshmdl.cpp:512-536 |
| `-fwrapv` | No new need | CRC (crc.cpp:120) and hashes (hashtemplate.h:57-61, 415-430) are unsigned. random.cpp already has `-fwrapv` (signed Random3 mix, random.cpp:301-313). Adding `-fwrapv` leaves soldier.o (-O2) and pscene.o (-O3) byte-identical, so GCC exploits no overflow there |
| `-mcpu=cortex-a9` / `-mtune` | No change | Already tuned. Explicit `-mcpu=cortex-a9 -mfpu=neon` gives byte-identical htree/pscene/soldier |
| `-marm` (numeric TUs) | Rejected | htree `-O3 -marm`: text +28% (7510->9618) with the same instruction count in `Anim_Update` 229->229, `Blend_Update` 296->295, `Combo_Update` 404->407 |
| sections + `--gc-sections`, `-fno-exceptions/-fno-rtti` | Already on | only renegade_wave_decoder.cpp re-enables `-fexceptions` |
| `-fno-stack-protector`, `-fno-semantic-interposition` | No-op | protector off by default; static non-PIC executable |
| `-fno-threadsafe-statics` | Rejected | original code runs on wwlib ThreadClass and port threads; DMB guard paths only in cold or small functions (RigidBodyClass::Timestep, Get_Muzzle, pscene Render_Object) |
| `-ffp-contract` | No-op | VFPv3 has no fused FMA. GCC emits chained `vmla.f32` (equal to vmul+vadd), even with `=off` |
| NEON float auto-vectorisation | Unavailable | probe: float loops vectorise only with `-funsafe-math-optimizations` (forbidden; NEON flushes denormals); int loops vectorise at `-O3` |
| LTO | Assessed, not enabled | see LTO |

## -O3 on Combat (codegen)

Text bytes, `-O2`->`-O3`: soldier 50625->56237, action 32932->47064, animcontrol 9474->15278,
vehicle 32592->43204, gameobjmanager 9385->14625. Across 12 Combat TUs, text grows
213526->263899 (+24%), with no new warnings. The hot bodies barely change:

- `SoldierGameObj::Apply_Control` (905 insns), `Handle_Legs` and `SmartGameObj::Post_Think`
  are identical.
- `SoldierGameObj::Think` (873) and `SmartGameObj::Think` (256) differ only in block order or
  operand swaps.
- `BulletClass::Think`, `Move_To_Absolute` and `VehicleGameObj::Apply_Control` are the same size.

Most of the growth is cold code: Load, destructors, `Import_*` thunks, `Set_Weapon_Model`. Some is
same-TU inlining, for example `HumanAnimControlClass::Update` (346->770 insns).

The hot paths are bound by cross-TU calls, which `-O3` cannot inline:
`SoldierGameObj::Post_Think` calls `ArmedGameObj::Get_Weapon()` 10x at both levels, and `Think`
calls `Get_Weapon` 8x and `DefenseObjectClass::Get_Health` 3x.

Expected gain is about 0, and the larger code may cost I-cache (32 KiB L1I).

## WWLib

- multilist.cpp: text 856->1276. `-O3` inlines the cold pool refill into `Internal_Add*`.
  `Contains`, `Internal_Remove` and `Count` are unchanged.
- wwstring.cpp: text 1284->2924. `Copy_Wide` is vectorised; `Get_String` and `Format` grow from
  inlining.

There is no clear hot gain. Container templates are instantiated in the calling TUs anyway.

## LTO (assessment)

The toolchain supports it (`lto1`, `liblto_plugin.so`, `gcc-ar`). A probe linked with
`-flto=auto -Wl,-q --gc-sections` inlines a cross-TU `Get_Weapon()` getter that the non-LTO link
calls. LTO is the only flag that targets the call pattern above.

It is not enabled:
- ~700 TUs on a shared 15 GB host; LTO link memory and time are unknown.
- ODR hazard: `scripts/wwmath.h` differs from `wwmath/wwmath.h` while defining the same inline
  `WWMath` members.
- Some TUs build with `-fpermissive` or `-fexceptions`.
- Original UB becomes exposed across TUs.
- Symbolication must be revalidated.

Next step if wanted: a `-Wodr`-clean `-flto` build of `staging/(combat|wwphys|wwmath)`, then a
host/Vita3K regression and a hardware A/B.

## Out of flag scope (leads for COMBAT_THINK / time-source owners)

- Every `DataSafeClass<T>::Get/Set` (datasafe.h:1756-1855; Get_Health etc.) calls `Shuffle()`
  and `Security_Check()`. Each of those reads `TIMEGETTIME()` -> `timeGetTime()`, which is
  `gettimeofday` plus a 64-bit /1000 (mmsystem.h:17-29). That is two clock reads per protected
  value read.
- `HumanAnimControlClass::Update` calls `StringClass::Format` and
  `pthread_mutex_lock/unlock` every call.

## Change made

- CMakeLists.txt: `option(RENEGADE_VITA_SIM_O3 ... OFF)`. A block after the hot-path `-O3`
  block appends `-O3` to `/staging/(combat|wwlib)/` sources (125 + 40 objects in the recorded
  graph) when the option is ON. It is independent of `RENEGADE_VITA_HOT_PATH_O3`, and the
  default build is unchanged.
- tools/test_vita_codegen_flags.py checks:
  - the value-preserving target flags are present and no unsafe-math flag is;
  - the option defaults to OFF and its block follows every `set_source_files_properties`;
  - a CMake option-matrix harness built from the real block text gives OFF = unchanged, and
    ON = `-O3` appended, with random.cpp `-fwrapv;-O3`, scripts.cpp `-fpermissive;-O3` and
    Commando untouched;
  - VitaSDK keeps `-fno-strict-aliasing`/`-fwrapv` under a trailing `-O3`.

## Risk and invalidation

With the option OFF (the default) the build is unchanged, so there is no risk. With it ON,
semantics are kept: no aliasing, overflow or FP flag change, and the flag precedence is verified.
The only risk is I-cache pressure. No caching is involved.

## Tests

- `python3 -m unittest tools.test_vita_codegen_flags -v`: 4/4 OK.
- ARM TU compiles (VitaSDK, recorded flags) at `-O2` and `-O3`, all OK:
  - Combat: soldier, smartgameobj, action, animcontrol, armedgameobj, bullet, gameobjmanager,
    humanstate, pathaction, physicalgameobj, vehicle, weapons.
  - Others: humanphys, pscene, htree, multilist, wwstring.
  - Variants: `-mcpu`, `-marm` (htree) and `-fwrapv` (soldier, pscene).
- No .cpp or header changed. The full CMake configure needs build/deps and was not run in the
  worktree.

## Expected gain (unmeasured)

The default build gains nothing. `SIM_O3=ON` is estimated at about ±2% of Combat and could be net
negative. The real sim levers are code-level: cross-TU getters (LTO or inline-getter patches)
and the DataSafe clock reads.

## Hardware measurement

Build twice, identical except for `-DRENEGADE_VITA_SIM_O3=ON`, and run the same M13 route. Over at
least 1200 frames each, compare `A4 campaign pacing` combat avg_us and `A3.5 perf` sim p50/p95/p99.
Adopt only if combat drops by at least 3% with no p99 regression.
