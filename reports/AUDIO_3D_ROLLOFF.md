# Audio 3D rolloff: WWAudio vs. Vita Miles provider

Report-only analysis (no build, no hardware run).

## What WWAudio itself does (staging/wwaudio)
- `Sound3DClass::Set_DropOff_Radius` / `Set_Max_Vol_Radius` (Sound3D.cpp:467-500, also :548)
  call `AIL_set_3D_sample_distances(h, max = m_DropOffRadius, min = max(m_MaxVolRadius, 1.0))`.
  So Miles "max distance" = dropoff radius, "min distance" = max-vol radius (floored at 1 m).
- Culling: static sounds are inserted into the cull system with an AABox extent equal to
  `Get_DropOff_Radius()` (staticsoundcullobj.h:174-176); sounds outside the radius are not
  played/are stopped by WWAudio's scene logic, not by Miles.
- Edge fade: `Sound3DClass::Update_Edge_Volume` (Sound3D.cpp:248-282), called each frame,
  linearly scales the *sample volume* from 1.0 at 0.85*dropoff to 0.0 at dropoff
  (`Internal_Set_Volume(m_RealVolume * percent)`). Skipped for pseudo-3D and dropoff==0.
- Therefore WWAudio already guarantees silence at/after the dropoff radius. The Miles
  provider's job is only the physical inverse-distance law between min and max.

## Provider today
`port/audio/vita/renegade_miles_provider.cpp:746-759` computes
`distance_gain = (max - d) / (max - min)` (linear), 0 beyond max. Combined with WWAudio's
edge fade this double-attenuates and makes the curve linear instead of 1/d: mid-range
sounds are much louder than on PC (e.g. min=1, max=100, d=10: linear 0.91 vs. PC 0.10).

## Faithful formula (DS3D / Miles 3D provider, rolloff factor 1)
```
d = max(d, min)
gain = (min > 0) ? min / d : 1
if (d >= max) gain = min / max     // DS3D: no further attenuation beyond max
```
Replace lines 753-758 with:
```cpp
const float minimum = std::max(1e-3F, std::min(sample->minimum_distance, sample->maximum_distance));
const float maximum = std::max(minimum, sample->maximum_distance);
const float clamped = std::min(std::max(distance, minimum), maximum);
distance_gain = minimum / clamped;
```
Holding at min/max beyond max matches DirectSound3D. Some Miles software providers mute
beyond max instead; for Renegade this difference is inaudible because WWAudio's
`Update_Edge_Volume` has already faded the sample to 0 at the dropoff radius (== max) and
the cull system removes it. Keep the existing `AIL_set_3D_sample_distances` argument
order (max, min) at provider line 1379. Note the 3D position lookup at line ~1369
(`scale = max(1, maximum_distance)`) should be reviewed separately so it does not
re-normalise distance.

## Verification to do later
Host unit test: min=1,max=100 → gains 1.0@0.5, 0.1@10, 0.01@100, 0.01@150; then hardware
listening check against PC at the same M00 positions.
