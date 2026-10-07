# Vehicle, weapon, projectile and explosion crash audit (M01..M11)

Date: 2026-10-07. Evidence class: source inspection of the staged original
code and read-only decoding of retail `objects.ddb` (from `always.dbs` in the
Vita3K `ux0` retail tree; nothing copied or committed). Definition fields were
decoded with the original microchunk IDs parsed from the staged loaders
(`weaponmanager.cpp`, `armedgameobj.cpp`, `vehicle.cpp`, `physicalgameobj.cpp`,
`beacongameobj.cpp`, `explosion.cpp`) using the existing
`tools/audit_m13_level_owners.py` chunk reader. The patched file passed
`arm-vita-eabi-g++ -fsyntax-only` with the `vita-fast-candidate` compile
flags. Nothing was built or run, either in Vita3K or on hardware.

## 1. Result

No campaign-reachable crash was found in the audited vehicle, weapon,
projectile, explosion, C4, beacon, harvester, VTOL or stealth code when it runs
against the retail definitions. One latent original NULL dereference on an
unconditionally-run vehicle path is now guarded. Section 4 lists latent
defects that the retail campaign data cannot reach. They are left unpatched
on purpose.

## 2. Bone lookups

- `HTreeClass::Get_Bone_Index`, `Animatable3DObjClass::Get_Bone_Index` and
  `RenderObjClass::Get_Bone_Index` return **0 (the root pivot)** when a bone is
  missing, never -1. Index 0 is always valid, so a missing `turret`,
  `barrel`, `muzzlea0/a1/b0/b1`, `eject` or `SEATn` bone gives the root
  transform, not an out-of-range index. `VehicleGameObj::Post_Think`'s
  `!= -1` check is dead but harmless.
- Turret and barrel bones (`Aquire_Turret_Bones`) are captured only when
  non-zero. `Update_Turret` and `Set_Targeting` act only when non-zero.
  `Set_Targeting` divides by `dist` only when it is non-zero. Its
  `Fast_Asin(Z/dist)` input lies in [-1, 1], and `Fast_Asin`/`Fast_Acos` fall
  back to `asin`/`acos` when |x| > 0.975.
- Cached bone indices can go stale only if a vehicle's model is swapped. Every
  campaign `Commands->Set_Model` target was checked: they are simple or
  cinematic objects, plus Mobius in M09, who is a soldier whose muzzle comes
  from `WeaponRenderModel` by name. No campaign script swaps a vehicle's
  model. Re-initialising muzzle bones on a weapon change is multiplayer-only
  (TT import).
- Muzzle recoil (`MuzzleRecoilClass::Update`) skips bone index <= 0. Muzzle
  flash (`MuzzleFlashClass`) and shell eject check for index > 0.
- C4 stick bones come from `Get_Sub_Object_Bone_Index` on the model that was
  hit, so they are valid for that model.

## 3. Definition lookups vs retail data

There are 15,146 definitions in total: 145 weapon, 140 ammo and 159 vehicle
definitions.

| Check | Retail result | Code behaviour |
|---|---|---|
| Weapon primary/secondary ammo IDs | Only the four editor folder presets (`Weapons_Vehicles`, `Weapons_Structures`, `Weapons_Test`, `Weapons_Infantry`) and multiplayer `CnC_Weapon_Orca_HeavyMachineGun` (secondary 0) are invalid. No armed or vehicle definition references them | `WeaponClass::Init` + `Update` would dereference a NULL ammo definition; not reachable |
| Armed `WeaponDefID`/`SecondaryWeaponDefID` | 5 missing targets: `Orca with A-10 Bomb Dropper`, `A-10 with bomb dropper` (1988), `Obelisk Laser Object`, `generic muzzle invisible` (1993), `Debris Weapon` (2001) | `WeaponBagClass::Add_Weapon(NULL)` returns NULL, so the object has no weapon. Safe |
| Ammo `ExplosionDefID` | All resolve; 7 resolve through Twiddlers (3203, 532480001, 532480010) whose choices are all explosion defs | `Find_Definition` twiddles by default. Safe |
| Physical `KilledExplosion` | 12 use Twiddlers 3204/3205/532480001, all choices explosion defs | Safe |
| Explosion `PhysDefID` | 96 of 96 are `TimedDecorationPhysDef` | Safe |
| Weapon muzzle-flash/eject phys IDs | 5 muzzle-flash and 4 eject IDs resolve to the correct type; 15 muzzle-flash and 10 eject IDs are absent from `objects.ddb` | Both sites check for NULL, and eject also checks the type. Safe |
| C4 ammo (`Ammo_Mine*`) | All six have explosion IDs that resolve | `C4GameObj::Detonate` / `Explosion_Damage_Building` safe |
| Beacon ammo | All six resolve to beacon defs; the beacons' `EXPLOSION_DEFID` values resolve | `Fire_Beacon` and beacon detonation safe |
| Vehicle engine sounds | 326 references, all sound defs | `(AudibleSoundClass *)Create()` safe |
| Ammo `RateOfFire` / `Velocity` = 0 | Only the four folder presets plus `Ammo_MineDiffuse`/`KilledC4` (non-firing) | `1/ROF` and `Range/Velocity` are float divides with no trap; not reached |

`DefinitionMgrClass` is a sorted binary search. Find on 0 or a missing ID
returns NULL. `WeaponManager::Find_Weapon_Definition(int)` and
`Find_Ammo_Definition(int)` are already class-checked in staging.

## 4. Physics class vs vehicle type

57 vehicle definitions use non-vehicle physics: 56 `DecorationPhys` and
`Nod_Turret` on `Phys3`. These are campaign objects: SAM sites, M06 tail guns,
gun emplacements, guard towers, ceiling cameras and the M04 rocket
emplacements. On them `VehicleGameObj::Peek_Vehicle_Phys()` returns NULL.
Every dereference in `vehicle.cpp`, `combat.cpp`, `warfactorygameobj.cpp`,
`vehicledriver.cpp` and `action.cpp` was checked, including the port's
`A3.5 vehicle: init` log line. Each one guards NULL or goes through
`As_MoveablePhysClass`. `HarvesterClass::Go_Harvest` dereferences without a
check, but both harvester definitions are tracked vehicles.

## 5. Seats and transitions

`SeatOccupants` is sized to `NumSeats`. `Add_Occupant(obj)` picks the lowest
free seat inside `NumSeats`, and seat-indexed `Add_Occupant(obj, i)` is only
reached from the multiplayer import paths (bounded by the seat array). Lookups go through
`Get_Driver`/`Get_Gunner` (length-checked) and `Find_Seat`. For
`Exit_Destroyed_Vehicle` the seat is masked with `& 3`. On a full vehicle,
`TransitionInstanceClass::End` does nothing, and nothing crashes.

## 6. Guard added

`port/patches/combat-a36-smart-control-disabled-weapon-guard.patch`
(registered last for `smartgameobj.cpp` in `tools/stage_sources.sh`; no
anchor moved; zero fuzz):

`SmartGameObj::Apply_Control`'s `else` branch for disabled control calls
`Get_Weapon()->Set_*_Triggered(false)` without a NULL check. Soldiers reach
`Apply_Control` only while control is enabled. `VehicleGameObj::Think` calls
`Apply_Control()` **unconditionally**, though. A `Control_Enable(vehicle,
false)` on a vehicle with no weapon (`Nod_Truck`, transports, harvesters,
civilian cars, hovercraft) would therefore crash every frame. The branch now
runs only when a weapon exists; with no weapon there is nothing to clear.
Retail campaign scripts and cinematics call `Control_Enable` only on the star,
so this is a latent hardening fix. It does not fix a crash seen in the
campaign.

## 7. Latent, not patched (not reachable with retail campaign data)

1. `WeaponClass::Set_State(STATE_FIRE_SECONDARY)` and `Do_Fire(false)`
   dereference `SecondaryAmmoDefinition` without a check. Only the unreferenced
   multiplayer preset `CnC_Weapon_Orca_HeavyMachineGun` has secondary ammo 0.
2. `C4GameObj::Detonate` passes `AmmoDefinition->ExplosionDefID` to
   `Explosion_Damage_Building`, which does not check the explosion definition
   for NULL. All C4 ammo has an explosion definition that resolves.
3. `C4GameObj::Load` would leave `AmmoDefinition` NULL if a save named an ammo
   ID that no longer exists, and `Think` would then dereference it. Saves from
   this build always carry valid IDs.
4. `HTreeClass::Get_Transform` only asserts its pivot bound. A stale bone index
   after a vehicle model swap would read out of range. The campaign never
   swaps a vehicle's model (section 2).
5. On a NaN input, `Fast_Acos`/`Fast_Asin` index the table at
   `INT32_MIN + 512` (`Float_To_Int_Floor` returns `INT32_MIN`). The address
   wraps to 32 bits and lands on entry 512, so on the 32-bit Vita the result is
   a NaN, not a fault.

## 8. Open evidence gates (hardware)

- Fire both weapons of every M02/M07/M10 player vehicle and the M04 rocket
  emplacements. Throw and detonate remote, timed and proximity C4 on an MCT.
  Destroy a vehicle with the player inside.
- Confirm that SAM sites, M06 tail guns and ceiling cameras (decoration-physics
  vehicles) aim and fire without faults.
