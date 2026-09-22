# Dev167: M13 object class count inventory

Status: source/tooling candidate, not a runtime acceptance.

Dev167 extends the Dev166 SaveLoad ownership map with per-file
`persist_factory_chunk_counts`, so M13 dynamic and static data now report
source-owned persist object classes and counts. This is still metadata-only:
the tool reads chunk headers and source registrations, and does not export
retail payload data.

Generated inventory:

- Output: `build/dev167-m13-mission-inventory.json`
- `m13.ldd` dynamic factory counts:
  - 117 `DecorationPhysClass`
  - 13 `HumanPhysClass`
  - 8 `Phys3Class`
  - 2 `WheeledVehicleClass`
  - 3 `TrackedVehicleClass`
  - 8 `PowerUpGameObj`
  - 111 `SimpleGameObj`
  - 13 `SoldierGameObj`
  - 11 `VehicleGameObj`
  - 16 `ScriptZoneGameObj`
  - 12 `SoldierObserverClass`
- `m13.lsd` static factory counts:
  - 42 `LightClass`
  - 42 `LightPhysClass`
  - 421 `StaticPhysClass`
  - 2 `StaticAnimPhysClass`
  - 16 `WaypathClass`
  - 66 `WaypointClass`
  - 8 `Sound3DClass`
  - 4 `SoundPseudo3DClass`

Why this matters:

- The intro/ambush/death failures are no longer just cinematic symptoms. M13
  clearly depends on original dynamic soldiers, vehicles, observers, script
  zones, dynamic physics and audio state loaded through SaveLoad. Runtime fixes
  must prove these classes instantiate, retain their scripts/timers, and clean
  up through death/reload and mission transitions.
- Static pathing and audio are present in mission data: M13 has waypaths,
  waypoints and static sounds. The stuck shotgunner, non-firing buggy and
  missing strike effects should be checked against loaded path/action/script
  state rather than by broad animation or renderer guesses.

Verification:

- `python3 -m tools.test_development_checkpoint` PASS.
- Direct execution of every function in
  `tools/test_vita_m13_cinematic_preparation.py` PASS.
- `python3 tools/renegade_cinematic_dependency_scan.py --mission-inventory --quiet --output build/dev167-m13-mission-inventory.json`
  PASS and JSON validates with `python3 -m json.tool`.

Acceptance boundaries:

- No ARM build, Vita3K runtime, physical runtime, visual correctness,
  performance, A/V sync, script-sequence, objective, death/reload, or campaign
  progression acceptance is claimed for Dev167.
- Payload fields, specific object IDs/names, old-pointer fixups, observer
  internals, script timer values, DDB preset transitive references and W3D
  internals are still not decoded.

Next executable step: add bounded runtime or static object-instance inventory
for the M13 dynamic classes above, keyed by original object ID/preset/script
where available, and compare intro start, ambush initiation, Havoc death and
mission cleanup states.
