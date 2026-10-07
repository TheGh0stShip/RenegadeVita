# Script-zone tunnelling at Vita frame rates

Date: 2026-10-07. Evidence class: source inspection, read-only retail level data
(Vita3K `ux0` retail tree, nothing copied or committed), an ARM
`-fsyntax-only` check of the patched unit and a zero-fuzz restage. Nothing was
built, run in Vita3K or run on hardware. Whether a callback fires on a physical
Vita is still a hardware evidence gate.

## 1. How zone membership is tested (original code)

`ScriptZoneGameObj::Think` (`Combat/scriptzone.cpp`) runs once per
`GameObjManager::Think`, which is once per frame. Zones that have no observers,
are hibernating or are cinematic-frozen do not run it. Each Think:

1. Exit pass: every `InsideList` member whose position is no longer inside fires
   `Exited`.
2. Entry pass: a **point test** of the object's current position against the
   oriented box (`Inside_Me` → `CollisionMath::Overlap_Test(OBBox, point)`).
   There is no sweep, no previous position and no hull overlap.
   * `CheckStarsOnly` zones (most campaign zones) test only the star list. A
     star inside a vehicle tracks the vehicle: `VehicleGameObj::Post_Think`
     sets its transform to the `SEATn` bone every frame.
   * Other zones collect dynamic physics objects whose cull box overlaps the
     zone *now*, then apply the same point test to each `SmartGameObj`.

Each frame advances by the measured frame time. `TimeManager` clamps it to
200 ms (`SLOWEST_FPS 5`). Between two samples an object moves
`speed × frame_time`. A straight crossing always leaves at least one sample
inside only while that step is shorter than the zone's thickness along the
travel direction. Two examples:

| Speed | 60 fps | 30 fps | 15 fps | 5 fps (200 ms cap) |
| --- | ---: | ---: | ---: | ---: |
| 6 m/s (running infantry, approximate) | 0.10 m | 0.20 m | 0.40 m | 1.2 m |
| 20 m/s (buggy/Humvee class, approximate) | 0.33 m | 0.67 m | 1.33 m | 4.0 m |
| 30 m/s | 0.50 m | 1.0 m | 2.0 m | 6.0 m |

Tunnelling is therefore real. Retail data contains many trigger zones thinner
than one Vita frame's move, as listed below.

## 2. Zones that gate progression (static)

`python3 -m tools.audit_script_zone_tunnelling [--markdown] [--output build/…]`
joins every level zone record (`tools.audit_script_zones`: OBBox basis, center
and extent) with its persisted script bindings. It then classifies each bound
script's `Entered()` body in `staging/scripts`:

* `mission_complete`: calls `Mission_Complete`.
* `objective`: calls `Add_Objective`, `Set_Objective_Status` or similar.
* `cinematic`: mentions `Test_Cinematic`, `Cinematic` or a cinematic `.txt`.
* `custom_event`: calls `Send_Custom_Event`, usually to a controller that may
  advance progression.

Thickness is the smallest full width (2 × extent) along the box's horizontal
axes. This is a geometric bound. The real travel direction is unknown.

| Map | Zones | Scripted | Gating (any class) | Gating & thin < 6 m | Hard-gating (not event-only) & thin |
| --- | ---: | ---: | ---: | ---: | ---: |
| M00 | 31 | 31 | 31 | 21 | 0 |
| M01 | 138 | 136 | 105 | 89 | 8 |
| M02 | 57 | 57 | 57 | 23 | 23 |
| M03 | 48 | 48 | 43 | 41 | 1 |
| M04 | 74 | 72 | 50 | 48 | 1 |
| M05 | 41 | 41 | 21 | 21 | 11 |
| M06 | 64 | 64 | 57 | 57 | 3 |
| M07 | 73 | 73 | 54 | 54 | 3 |
| M08 | 97 | 97 | 73 | 73 | 2 |
| M09 | 99 | 99 | 85 | 78 | 1 |
| M10 | 89 | 89 | 51 | 47 | 2 |
| M11 | 56 | 56 | 49 | 48 | 0 |
| M13 | 16 | 16 | 16 | 16 | 3 |

Thickness of the 692 gating zones: 76 under 1 m, 279 from 1 to 2 m, 186 from 2
to 4 m, 75 from 4 to 6 m, and 76 at 6 m or more. Most authored triggers are thin
"tripwires" across a path. At the 200 ms cap, even running infantry can cross
the zones under 1.2 m.

### Highest-risk zones (hard-gating, thin, player vehicles available)

The player vehicle missions are M01, M02, M07, M08 and M10, per
`CAMPAIGN_VEHICLES.md` §1. Thin and long values are in metres.

| Map | Zone ID | Thin | Long | Gating | Script |
| --- | ---: | ---: | ---: | --- | --- |
| M02 | 401114, 401113, 400273, 400272, 401054, 401123, 401196, 405118, 400193, 401080, 401101, 401102, 400271, 303203, 401131, 401066, 400274, 301601, 400270, 400192, 401001, 405117, 405116 | 1.39 – 5.51 | 3.4 – 22 | objective, cinematic, mission_complete paths, events | `M02_Objective_Zone` |
| M01 | 118832 | 1.45 | 2.31 | cinematic | `M01_SniperRifle_02_AirdropZone_JDG` |
| M01 | 108026, 108028, 108024 | 2.0 – 3.94 | 4.5 – 4.8 | objective | `M01_Comm_Mainframe_PogZone_0{1,2,3}_JDG` |
| M01 | 106268, 106267 | 3.25, 3.83 | 8.2, 12.8 | objective + event | `M01_TriggerZone_GDIBase_BaseCommander_JDG` |
| M01 | 119825 | 4.91 | 34.6 | cinematic | `M01_ConDropZone_JDG` |
| M01 | 103006 | 5.66 | 5.77 | cinematic | `M01_Nod_GuardTower_03_Enter_Zone_JDG` |
| M07 | 101131, 100756, 101151 | 0.70, 1.72, 3.09 | 13.8 – 17.2 | cinematic | `M07_Activate_E10_Tank_Drop`, `M07_Activate_Present`, `M07_Activate_Para_Drop` |
| M08 | 103886, 1500225 | 4.10, 4.19 | 6.3, 4.2 | cinematic | `M08_Activate_Excavation`, `M08_Activate_Midtro` |
| M10 | 1110056, 1100161 | 4.03, 4.37 | 22.8, 10.6 | cinematic + event | `DME_Cinematic_Zone`/`M10_Conversation_Zone`, `M10_Cargo_Plane_Dropoff` |

M02 carries the most risk. Its 23 `M02_Objective_Zone` instances (1.4 to 5.5 m)
drive the objective chain, and M02 gives the player a buggy, a Humvee and recon
bikes. A 20 m/s vehicle at 15 fps can skip the 1.4 m zones. At the 200 ms cap it
can skip anything under 4 m.

### Infantry-only thin hard-gating zones (at risk only on frame spikes)

* M05: 100274 (0.47 m), 100027, 100039 (0.86 m), 100664 (0.91 m), 107478, 100668,
  101228, 101221, 101218, 101219 (1.0 to 1.9 m), 1100605 (4.26 m). These are
  objective, Apache-strike, midtro and tank-drop activators.
* M06: 108285 (0.60 m, `M06_Activate_MidtroC`), 101011 (0.87 m,
  `M06_Activate_Midtro`), 101518 (2.16 m).
* M03 2000817 (3.31 m, `M03_Mission_Complete_Zone`), M04 101146 (1.08 m), M09
  2000612 (1.53 m) and M13 1200019, 1400143, 1400004 (1.7 to 5.1 m).

A further 558 thin zones gate only through `Send_Custom_Event`. Detailed rows,
including parameters and filters, are kept privately in
`build/script-zone-tunnelling.json`.

## 3. Fix: swept entry for stars

Patch: `port/patches/combat-a37-scriptzone-swept-entry.patch`, registered in
`tools/stage_sources.sh` after the overlay clamp. It applies with zero fuzz and
leaves no other staged files changed.

* Each zone keeps up to 4 samples (`ObjID`, sync time, frame ticks, position)
  for stars and star vehicles. Samples are not saved, so they rebuild after a
  load.
* `Update_Sweep_Sample` reports a crossing only when **all** of these hold:
  1. The previous sample came from this zone's immediately preceding Think:
     `prev.SyncTime + FrameTicks == WW3D::Get_Sync_Time()`, and both ticks are
     nonzero. Zones that stopped thinking, paused frames, prewarm `Sync`
     calls and level loads never sweep.
  2. The move is longer than the zone's **thinnest side** (2 × min extent).
     Shorter moves always leave a sample inside on a straight crossing, so the
     original point test alone decides. Behaviour is therefore bit-identical
     whenever per-frame moves are smaller than the zone, which covers every
     zone at high frame rates.
  3. The move is at most 50 m/s × the sampled frame's ticks. Larger moves are
     treated as teleports (script `Set_Position`, vehicle exit placement).
  4. Both endpoints are outside the box, and the original
     `CollisionMath::Overlap_Test(OBBox, LineSegClass)` hits it. If the
     previous sample was inside (the object just exited), nothing re-fires.
* Star-only zones: `Entered` fires when `Inside_Me || swept` and the object is
  not already in the list.
* All-smart zones: after the original `Collect_Objects` pass, each star and
  its `Get_Vehicle()` is checked. Each must still have a culling system and an
  observer, the conditions the original physics-scene gather depends on.
* `Entered` is the original function. The object enters `InsideList`, and the
  next Think's original exit pass fires `Exited`. The sequence matches a
  60 fps pass: one Entered, then one Exited.
* Each sweep hit emits a `Debug_Say` breadcrumb with the zone ID, object ID and
  distance.

Check: `arm-vita-eabi-g++ -fsyntax-only` with the vita-fast-candidate compdb
flags and the four requested defines passed with no diagnostics in
`scriptzone.cpp`.

## 4. Residual risk

* **AI-driven objects** are not swept: escort convoys, harvesters, NPCs that
  must reach a zone. Only stars and star vehicles have samples. An AI vehicle
  that crosses a thin all-smart zone within one frame can still miss it, as
  before. Escort zones should be checked on hardware.
* **Corner clips** shorter than the zone's thinnest side are not swept. The
  original also misses them at 60 fps.
* **Curved paths**: the sweep assumes a straight line between samples. A
  vehicle that turns around a zone corner within one 200 ms frame could get a
  spurious entry, or miss a real one.
* **Teleports under 50 m/s × dt**, such as a short vehicle-exit placement or a
  script nudge across a zone thinner than the jump, can fire an `Entered` the
  original would skip.
* **More than 4 star or star-vehicle candidates per zone** (large LAN games)
  fall back to the point test for the extra objects.
* Gating classification is a source heuristic. Custom-event-only zones may or
  may not gate. The thickness is the horizontal minimum, not the actual
  crossing width.
* Not yet proven: that `TimeManager::Update_Frame_Time` advances the sync time
  exactly once per Think on the Vita runtime. If it does not, the continuity
  check fails and the original behaviour applies. That is safe, but tunnelling
  would remain. Hardware validation should drive a buggy or Humvee through an
  M02 objective zone while forcing low frame rates, and look for the
  `swept entry` breadcrumb and the matching objective update.
