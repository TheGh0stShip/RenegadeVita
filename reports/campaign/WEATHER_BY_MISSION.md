# Campaign weather by mission and Vita cost estimate — 2026-10-07

Evidence class: source reading plus read-only retail chunk inspection. Nothing was
built, launched in Vita3K or run on a Vita. The CPU numbers are an analytic model
with stated assumptions, not a measurement, and no physical weather result exists.

Inputs: `staging/combat/WeatherMgr.{h,cpp}` (pristine upstream plus
`combat-a31-weather-gcc15.patch` and `combat-a36-weather-dynamic-admission.patch`),
`Code/Scripts/Mission{01,03,07,09}.cpp`, `combat/combat.cpp`, `combat/beacongameobj.cpp`,
`port/renderer/vita/ww3d_dx8_boundary.cpp`, and every `.lsd` in the retail Vita3K Data
tree. The level dump is reproducible with
`python3 -m tools.audit_level_weather --data <Data> [--output file.json]`
(new read-only tool, `tools/audit_level_weather.py`).

## Where weather comes from

Weather has exactly four sources. The port does not add or alter any of them.

1. **Level data.** `_TheWeatherMgr` is one of the subsystems in each level `.lsd`
   (chunk `0x40800`). Its static micro chunk (`0x03020113`) is empty in all 27 retail
   maps and `Load_Micro_Chunks` ignores it. The authored values live in the dynamic
   micro chunk (`0x11020245`): current/normal/target/duration/override values for wind
   heading/speed/variability, rain/snow/ash density and fog start/end, plus the fog
   enable byte. Every retail level has exactly one such chunk and no unknown micro IDs,
   so the strict one-dynamic-chunk admission patch cannot reject any retail level.
2. **Mission scripts** through `Commands->Set_Rain/Snow/Ash/Wind/Fog_Enable/Fog_Range`
   (`scriptcommands.cpp:3030`–`3070`). The `prime` argument of Rain/Snow/Ash is ignored by
   the original wrapper, so priming is decided only by `WeatherMgrClass::_Prime`.
3. **Beacons** (`beacongameobj.cpp:881`–`961`): arming an ion beacon overrides rain to
   2.0 for `DetonateTimer/2`; arming a nuke overrides wind to (0, 3, 1) and, after
   detonation, ash to 0.3. These apply wherever a beacon is armed (M13 finale, MP).
4. **Console** (`consolefunction.cpp`): developer commands only.

Fog is always enabled by level data (`fog_enabled = 1` in all 27 maps); the game
therefore always pays the fixed-function fog state, but fog itself involves no particles.
Lightning and clouds belong to `BackgroundMgr`, not `WeatherMgr`, and are not covered here.

## Weather per campaign mission

Densities are particles per second per unit emitter area as passed to the original
classes. `rays` and `particles` come from the original formulas below, evaluated for
open ground with the camera about 2 m above it (fall length L of about 22 m).

| Mission | Source | Wind (heading deg / speed / variability) | Precipitation | Fog start–end | Rays | Particles (L=22 m) |
|---|---|---|---|---|---|---|
| M00 Tutorial | none | none | none | 20–450 | 0 | 0 |
| M01 | scripts (`M01_Mission_Controller_JDG`, bound in `m01.ldd`) | 0/0/0 at start; 60/3/0.5 near church, 60/5/1.0 at Nod base, 60/1/0.5 at barn (ramps 15–120 s); cleared over 5 s at the end | rain 0.75 (30 s ramp) at church and bridge; 1.0 (15 s) at Nod base; 0.5 (120 s) at barn; 0 at end | 1–400 | 100 / 133 / 66 | 485 / 647 / 323 |
| M02 | level data | none | snow 0.3 | 0–300 | 1,371 | 3,737 |
| M03 | script (`RMV_Volcano_And_Lava_Ball_Creator`, bound in `m03.ldd`) | `Set_Wind(90,5,2)` in `M03_Objective_Controller` is rejected (variability 2.0 > 1.0) | ash 0.15 (3 s ramp) after the Sakura dogfight; the rain timer is commented out in source | 150–300 | 799 | 2,120 |
| M04 | level data | 177 / 0.14 / 0.41 | rain 5.0 for the whole mission | 25–200 | 666 | 3,233 |
| M05 | none | none | none | 200–300 | 0 | 0 |
| M06 | level data | 64 / 0.07 / 0.4 | snow 0.1 | 1–200 | 457 | 1,246 |
| M07 | script (`M07_Cathedral_Controller`, bound in `m07.ldd`) | `Set_Wind(90,5,2)` rejected as in M03 | ash 0.15 (3 s ramp) at the nuke impact | 0–300 | 799 | 2,120 |
| M08 | none | none | none | 25–225 | 0 | 0 |
| M09 | scripts `M09_Weather_On` / `M09_Weather_Off` (two zones each, bound in `M09.ldd`) | none | **rain 10.0** (2 s ramp) when a zone is entered, back to 0 (2 s) on exit; fog range set to 0–150 then 0–1000 | 1–100 (level), 0–150 in zone | 1,333 | **6,467** |
| M10 | none | none | none | 170–300 | 0 | 0 |
| M11 | level data | none | rain 0.2 | 100–300 | 26 | 129 |
| M13 | none in data; ion beacon override rain 2.0, nuke override wind then ash 0.3 | beacon only | beacon only | 30–300 | 266 / 1,599 | 1,293 / 4,240 |

Notes:

- Mission numbering follows the mix file names. Script names above were each confirmed
  as present in the matching retail level data.
- M03 and M07 call `Set_Wind(90, 5, 2, 0)`. `WeatherMgrClass::Set_Wind` requires
  variability within [0, 1], so the call fails and only a debug line is printed. That is
  identical to the PC build and is intentionally not patched.
- Wind speeds in M04/M06 are tiny (0.14 and 0.07). Any speed above 0 still creates the
  `WindClass` and its `Wind01` 2D stream, as on PC.
- Densest level-data weather is M04 rain 5.0; densest script weather is M09 rain 10.0
  (the densest campaign weather overall); M02 snow 0.3 has the most rays. Skirmish00
  (snow 0.02) is not part of the campaign.

## Particle model (original code, unchanged)

Parameters from `RainSystemClass`, `SnowSystemClass`, `AshSystemClass` constructors:

| Type | Emitter size S | Particles/unit length | Speed | Static time | Ray count | Steady-state particles |
|---|---|---|---|---|---|---|
| Rain | 20 | 0.2 | 15 | 0.1–0.2 s | `d*S*S/(ppul*speed)` = 133.3 d | `d*S*S*(L/speed + static)` = 400 d (L/15 + 0.15) |
| Snow | 40 | 0.1 | 3.5 | 1–2 s | 4,571 d | 1,600 d (L/3.5 + 1.5) |
| Ash | 40 | 0.1 | 3.0 | 1–2 s | 5,333 d | 1,600 d (L/3 + 1.5) |

- Particle count scales with fall length L: for M09 rain 10.0 it is about 3,800 at L=12 m,
  6,500 at 22 m and 9,900 at 35 m. Rays under a roof spawn nothing, so interiors are near
  zero. The hard ceiling is the original global cap `USHRT_MAX/6 = 10,922` particles
  (`Spawn`), which snow at density 0.9 or more, or rain above about 17, would reach.
- Memory (original pools): `ParticleStruct` 80 B (6,467 particles ≈ 505 KiB, cap ≈ 854 KiB),
  `RayStruct` 56 B (M09 ≈ 73 KiB), weather texture `weatherparticles.dds` DXT5 128×128
  (22,000 B in `always.dat`), a 6,144-index (12 KiB) index buffer per system and a dynamic
  vertex buffer that grows once to at least 6,144 vertices × 44 B ≈ 270 KiB. Total for M09
  is roughly 0.9 MiB plus the grown dynamic buffer, an addition to the M09 memory
  estimate in `MISSION_MEMORY_ESTIMATES.md`, which does not mention weather.
- Render path: `MAX_IB_PARTICLE_COUNT = 2048` triangles per batch, so M09 draws in
  `ceil(6467/2048) = 4` indexed submissions and the particle cap would need 6. The port's
  `Submit_Bound_Triangles` handles `BUFFER_TYPE_DYNAMIC_DX8` and the `D3DRS_ZBIAS`
  state weather uses (`ww3d_vita_renderer.cpp:3663`), so this path is mapped, but it
  has not been exercised on hardware: M00 and M13 have no weather particles.

## Per-frame CPU cost estimate (Vita, 444 MHz, 30 fps)

`scePowerSetArmClockFrequency(444)` is applied at startup (`a31_vita_runtime.cpp:2439`).
Work per frame, all single-threaded on the game thread:

- **Update** (`WeatherSystemClass::Update`, inside `WWPROFILE("Weather")`):
  - one pass over every particle (80 B list nodes, pointer-chased, working set larger
    than L1): modeled at 0.27 / 0.35 / 0.45 µs each;
  - one pass over every ray (cheap unless relocated): 0.08 / 0.10 / 0.15 µs each;
  - `Scene->Cast_Ray` (terrain only) for `max(rays*0.018, 1)` refresh rays plus the rays
    that leave the emitter as the camera moves (modeled for a 6 m/s walk): 30 / 50 /
    100 µs each. No measured Vita ray-cast cost exists; this is the largest uncertainty;
  - spawn and kill through `AutoPoolClass` plus the random generator.
- **Render build** (`WeatherSystemClass::Render`): every particle is walked and frustum
  tested (0.25 / 0.30 / 0.40 µs), and an assumed 20% in view are built into the dynamic
  vertex buffer and converted by the backend (0.8 / 1.0 / 1.5 µs each, backend
  conversion cost assumed). GPU fill is not included.

Results as low / central / high milliseconds per frame:

| Case | Particles | Raycasts per frame | Update | Render build | Total | Share of 33.3 ms |
|---|---|---|---|---|---|---|
| M04 rain 5.0 | 3,233 | 14 | 1.4 / 1.9 / 3.0 | 1.3 / 1.6 / 2.3 | 2.7 / 3.6 / 5.3 | 8% / 11% / 16% |
| M02 snow 0.3 | 3,737 | 27 | 1.9 / 2.8 / 4.6 | 1.5 / 1.9 / 2.6 | 3.5 / 4.7 / 7.3 | 11% / 14% / 22% |
| **M09 rain 10.0** | 6,467 | 30 | 2.8 / 3.9 / 6.2 | 2.7 / 3.2 / 4.5 | **5.4 / 7.2 / 10.7** | 16% / 22% / 32% |
| Global cap | 10,922 | 30 | 4.0 / 5.5 / 8.2 | 4.5 / 5.5 / 7.6 | 8.5 / 11.0 / 15.9 | 26% / 33% / 48% |

Consequences:

- The densest mission is M09 while the player stands in the weather zone on open ground:
  about 7 ms per frame central (5–11 ms), a fifth of a 30 fps frame. It is bounded by the
  10,922-particle cap at about 11 ms central.
- Cost is linear in particles, not in density. Roof cover, the cap and the 2-second
  ramps (`Set_Density` adds rays incrementally) all keep the transitions smooth.
- **First-frame stall.** `_Prime` is true for the first `Update` after a level load, so a
  level-data system (M02, M04, M06, M11) is created primed and spawns its whole steady
  population in one frame, with one ray cast for every ray: M02 about 1,371 casts
  (roughly 40–140 ms at the modeled cast cost) and M04 about 666 casts (20–65 ms),
  once per level load. Script-driven weather (M01, M03, M07, M09) is not primed and ramps in.
- Rain adds a 2D stream (`Rainfall01`), wind a second (`Wind01`); both are already
  covered in `LEVEL_AUDIO_READINESS.md`.

No performance change is adopted. Per the project rule, the next step is measurement:
the `Weather` scope is already routed into the A3.6 frame profile (top scopes and the
worst frame of each 120-frame window), so an M04 and an M09 physical run will give
Update cost directly. Render cost is not separately scoped; if the profile shows Weather
Update plus the scene render growing in M09, the candidates are (a) a measured scope
around `WeatherSystemClass::Render`, then (b) a lower `maxparticlecount` in `Spawn`
as a visual trade-off. Both are deferred and neither changes physics or gameplay.

## Session reset verification (source reading)

The lifecycle is symmetric and runs on every level load and unload:

- `CombatManager::Pre_Load_Level`: `WeatherMgrClass::Init(SoundEnvironment)` (`combat.cpp:348`)
  clears `_Wind` and `_Precipitation[]` and calls `Reset()`. This happens before the level
  `.lsd` is loaded, so the level data then overwrites the parameters.
- `CombatManager::Unload_Level`: `WeatherMgrClass::Shutdown()` (`combat.cpp:648`) runs
  `Reset()` and drops its sound-environment reference, ahead of
  `BackgroundMgrClass::Shutdown()`, the combat sound-environment release and
  `WW3DAssetManager::Free_Assets()`.
- `Reset()` re-initializes all 8 parameters (current, targets, durations, override
  values), deletes the `WindClass` (stops `Wind01` and removes the sound-environment
  user), removes and releases each precipitation system (destructor kills every
  particle, so `_GlobalParticleCount` returns to 0, stops `Rainfall01`), sets wind and
  fog to defaults, disables fog, sets fog range 200–300, `_Prime = true`,
  `_Imported = false`, both override counters 0, and marks the state dirty so the new
  scene gets its fog on the first `Update`.
- Render objects held in the WW3D static sort list are released every frame by
  `Render_And_Clear_Static_Sort_Lists`, so no weather system survives teardown there.

Findings:

- One upstream asymmetry remains: `WeatherParameterClass::Initialize()` does not zero
  `NormalValue`. It cannot leak into the next session: the level load overwrites it from
  the dynamic chunk, and for a level without a weather chunk the first `Update` resolves
  `NormalValue` against the zeroed `NormalTarget` before `CurrentValue` is derived from
  it, in the same call. It is therefore not patched, which avoids churn in the 513-patch
  staging inventory.
- Not reset by design (also true on PC): the weather random generator keeps its state
  across sessions, so particle placement differs between two runs of one level.
- `Spawn` contains the upstream precedence quirk
  `_RandomNumber(0, PageCount - (StaticPageExists) ? 2 : 1)`. It evaluates to pages
  0–2 for rain (matching the intent) and also 0–2 for snow and ash (intent was 0–3), so
  the fourth snow page is never used. Preserved for PC parity.
- Not verified here: that Vita3K or hardware reaches `Unload_Level` on every exit path
  (restart, quit, failed reload recovery). `Init` clears the pointers without freeing,
  which is safe only if `Shutdown` ran; the reports show recovery goes through the shared
  teardown, but this report did not trace it. A physical or Vita3K soak that cycles M04
  → M05 → M04 and then reads `_GlobalParticleCount` (or just checks the particle cap is
  not reduced) would close it.

## Defects fixed

None. No clear defect was found in the weather source, staging patches or backend
mapping, so no source changed. The only repository change is the new read-only tool
`tools/audit_level_weather.py` and this report.
