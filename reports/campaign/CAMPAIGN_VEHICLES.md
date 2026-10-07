# Campaign vehicles (M01..M11): inventory and Vita path audit

Date: 2026-10-07. Evidence class: source inspection, retail-data inspection
(read in place from the Vita3K `ux0` retail tree, nothing copied or committed),
and symbol/map inspection of the last packaged ARM ELF
(`local-builder/dist/RenegadeVita-A3.5-dev238.{symbols.txt,map}`). Nothing was
built, run in Vita3K or run on hardware for this audit. Physical
driving/entry/exit behaviour remains a hardware evidence gate.

## 1. Player-enterable vehicles by mission

Sources: `Create_Object` literals and vehicle-entry script handlers in
`Code/Scripts/Mission*.cpp`; `Create_Real_Object`/`Attach_Script` lines in
retail cinematic `.txt` entries (`always.dat`, `M0x.mix`); script-name strings
in the level MIX files. Presets ending `_Player` are the player-team copies.

| Mission | Vehicle (preset / script owner) | How it appears | Type |
|---|---|---|---|
| M01 | `GDI_Medium_Tank_Player` (`M01_Medium_Tank_JDG`: VEHICLE_ENTERED/EXITED drive the tunnel and barrier zones) | Cinematics `x1d_hover_mtank`, `x1d_fodderhover_mtank`, `x1i_gdi_drop_mediumtank` | Tracked |
| M02 | `GDI_Mammoth_Tank_Player` (`M02_Player_Vehicle "2"`; entry reported to the objective controller) | Script Chinook drop and `x2i_gdi_drop_mammoth` | Tracked |
| M02 | `GDI_Medium_Tank_Player` (`M02_Player_Vehicle "5"`) | `x2i_gdi_drop_mediumtank` | Tracked |
| M02 | `GDI_Humm-vee_Player` | `x2i_gdi_drop_hummvee` | Wheeled |
| M02 | `Nod_Buggy_Player`, `Nod_Light_Tank_Player`, `Nod_Recon_Bike_Player` x2 (`M02_Player_Vehicle 3/5/6/14`, `Enable_Vehicle_Transitions(true)`) | Script area drops | Wheeled / tracked / motorcycle |
| M04 | Ship rocket emplacements 01/02 (`M04_RocketEmplacement_0x_JDG`, IDs 103461/103462; VEHICLE_ENTERED starts the Apache attack) | Level objects | Stationary turret |
| M07 | `Nod_Light_Tank_Player`, `GDI_Mammoth_Tank_Player`, `Nod_Flame_Tank_Player` (`M07_Player_Vehicle`) | `m07_xg_vehicledrop1/3/4` from `M07_Vehicle_Drop_Controller` | Tracked |
| M08 | `Nod_Stealth_Tank_Player` (created if level object 109047 is missing) | Script, and placed in level | Tracked |
| M09 | Stationary stealth tank (`M09_Stationary_StealthTank`, VEHICLE_ENTERED reports to 2000071) | Placed in level | Tracked |
| M10 | `GDI_Mammoth_Tank_Player` (`M10_Mammoth_Grant_Controller` swaps level Mammoth 2000787; `M10_Occupied`) | Script | Tracked |
| M10 | `GDI_MRLS_Player` x2 (`M10_Mrls_Waypath`) | Script timer drop | Vehicle |
| M10 | `GDI_Humm-vee_Player` | `m10_gdi_drop_hummvee` | Wheeled |
| M05, M06, M11 | none found | — | — |

Not player vehicles: the M01 tail guns (`M01_TailGun_0x_JDG`) are crewed by
Nod gunners and attack the player, and `M03_Tailgun` only reports its own
death to a controller.

`M00_Vehicle_Regen_DAK` (health regeneration) is bound in M02, M03, M08 and M10.

The Type column comes from the preset family. It was not decoded from
`objects.ddb` physics definitions. Level-placed objects were found through
their script-name strings only, so a level-placed vehicle with no script
binding would not appear above.

**Player flight:** no `_Player` aircraft (Orca, Apache, transport) appears in
any campaign script literal or cinematic. Aircraft in M01..M11 belong to
enemies or cinematics. No campaign mission requires player VTOL control. The
flying multiplayer maps (`C&C_*_Flying.mix`) are outside campaign scope.

**Gunboats:** `M01_GDI_Gunboat` and the M03 gunboat controller are
AI/cinematic objects. The player does not enter them.

## 2. Entry and exit (TransitionManager, seats)

- Triangle sets `DIK_E`, which is bound to `INPUT_FUNCTION_ACTION` (BUTTON_HIT)
  in `A31_Interactive_Configure_Vita_Controls`. The original
  `ActionCodeClass` copies this to `BOOLEAN_ACTION`.
- On foot, `SoldierGameObj` runs `TransitionManager::Check(this, action)` on
  the server, and a single-player mission is the server. In a vehicle
  (`HumanStateClass::IN_VEHICLE`), `Apply_Control` runs
  `TransitionManager::Check(this, true)` to exit. Both paths are unchanged
  original code.
- Seat and transition owners are linked from the original translation units
  `combat/vehicle.cpp`, `combat/transition.cpp`, `combat/transitiongameobj.cpp`
  and `wwphys/transitioneffect.cpp`. The listed sources are compiled directly
  into the executable, not into an archive, so factory registrations survive
  the link. ELF symbols present: `TransitionManager::Check`,
  `TransitionInstanceClass::Start`, `VehicleGameObj::Add_Occupant` and
  `Remove_Occupant`, `SoldierGameObj::Enter_Vehicle` and `Exit_Vehicle`, and
  the `Enable_Vehicle_Transitions` script command. The map shows
  `VehicleGameObj::Get_Driver` comes from staged `combat/vehicle.cpp`; the
  old A3.0 scalar copy in `a30_static_world_boundary.cpp` is not linked into
  A3.1.
- Port patches that touch vehicles: `combat-a35-tt-vehicle-state.patch`
  changes only network import and gates its effects on `TTStateActive`, which
  defaults to `false`, so campaign behaviour is the original.
  `combat-a35-vehicledriver-borrowed-remap.patch` fixes AI path pointer
  remapping. The three `wwphys-a35-trackedvehicle-*` patches change only
  track UV animation and render.

## 3. Vehicle input mapping (Vita → original functions)

| Vehicle function | Original consumer | Vita input | Status |
|---|---|---|---|
| Throttle forward/back | `MOVE_FORWARD/BACKWARD` → `ANALOG_MOVE_FORWARD` | Left stick Y (`SLIDER_JOYSTICK_UP/DOWN`) | Mapped |
| Steering | `Input::Update` sets `VEHICLE_TURN_* = max(MOVE_*, TURN_*)` → `ANALOG_TURN_LEFT` | Left stick X (`SLIDER_JOYSTICK_LEFT/RIGHT`) | Mapped. The original derivation still runs; the zeroed `VEHICLE_TURN_*` bindings are overwritten every frame |
| Turret/camera aim | CCamera `WEAPON_LEFT/RIGHT/UP/DOWN` → star targeting → `VehicleGameObj::Set_Targeting`/`Update_Turret` | Right stick (mouse delta) | Mapped |
| Fire primary/secondary | `FIRE_WEAPON_PRIMARY/SECONDARY` (`Get_Weapon_Control_Owner`) | R / L trigger (joystick buttons 1/0) | Mapped. Secondary covers Mammoth missiles |
| Reload | `RELOAD_WEAPON` | Square (`DIK_R`) | Mapped |
| Enter/exit | `ACTION` | Triangle (`DIK_E`) | Mapped |
| First/third person | `FIRST_PERSON_TOGGLE` | Rear touch, Select+Circle (campaign), R3 (PSTV) | Mapped |
| VTOL up/down | `MOVE_UP/MOVE_DOWN` | Cross / Circle (copied from Jump/Crouch by `Input::Set_Primary_Key_For_Function`, as on PC) | Mapped; not used in the campaign |
| Toggle gunner | `VEHICLE_TOGGLE_GUNNER` (retail default `Q_Key`) | none | Not reachable on Vita. Matters only when a second soldier occupies the gunner seat, which is multiplayer only |
| Horn | — | — | The original has no horn input function or handler |

## 4. Third-person vehicle camera

`CombatManager::Update_Star` switches to `vehicle->Get_Profile()` (vehicle
profiles from the retail `cameras.ini`) through `CCameraClass::Use_Profile`.
CCamera follows `Get_Profile_Vehicle()`. Both live in staged original
`combat/combat.cpp` and `combat/ccamera.cpp`. No port patch touches profile
selection or vehicle following; the only CCamera patch is the silent-listener
change.

## 5. Vehicle physics classes compiled

All of these are in `cmake/A30OriginalSources.cmake`, which A3.1 includes,
and appear in the dev238 ELF:

- `wwphys/vehiclephys.cpp`: `VehiclePhysClass::Timestep`
- `wwphys/wheelvehicle.cpp` and `wheel.cpp`: `_WheeledVehicle{,Def}Factory`, `WheeledVehicleClass::Compute_Force_And_Torque`, `WheelClass::*`
- `wwphys/trackedvehicle.cpp`: `_TrackedVehicle{,Def}Factory`, `Compute_Force_And_Torque`
- `wwphys/motorcycle.cpp`: `_Motorcycle{,Def}Factory` (Recon Bike)
- `wwphys/vtolvehicle.cpp`: `_VTOLVehicle{,Def}Factory`, `Compute_Force_And_Torque`
- `wwphys/vehicledazzle.cpp`, `wwmath/vehiclecurve.cpp`
- `combat/vehicle.cpp`: `_VehicleGameObj{Def,}PersistFactory`

## 6. Defects and divergences

No campaign-path defect was found, so no code changed.

Divergences outside the campaign, recorded for multiplayer or flying-map
work and left unfixed on purpose:

1. **`VEHICLE_TOGGLE_GUNNER` has no Vita input.** Only a multi-occupant
   vehicle uses it. A later fix would be an MP-only Select chord, bound like
   the existing radio and chat chords.
2. **Aircraft strafe modifier.** The original `ActionCodeClass` turns aircraft
   turning into strafing while `DIK_LCONTROL` or `DIK_LMENU` is held. On Vita,
   Circle drives `DIK_LCONTROL` (crouch, and therefore MOVE_DOWN), so
   descending also switches strafing on. On PC the defaults are C (descend)
   and Ctrl (strafe), which are independent. Changing the hardware-validated
   crouch key would affect the rebinding UI and saved input profiles, so it
   is deferred until flying-map work.
3. `TURN_AROUND` (retail `X_Key`) and `WALK_MODE` (Shift) have no Vita input.
   Neither applies to vehicles.

## 7. Open evidence gates (hardware)

- Enter and exit a tank in M01 (Medium Tank tunnel) and M02 (Mammoth or
  Humvee drop); confirm `VEHICLE_ENTERED` reaches the objective scripts.
- Drive and steer a wheeled vehicle, a tracked vehicle and the M02 Recon Bike
  (motorcycle) with the left stick. Aim the turret with the right stick.
  Fire both weapons with R and L.
- Man the M04 ship rocket emplacements and survive the Apache attack they start.
- Confirm the third-person vehicle camera profile and track animation look
  right; logs cannot show this.
