# Dev166: M13 SaveLoad ownership inventory

Status: source/tooling candidate, not a runtime acceptance.

Dev166 extends the Dev165 M13 inventory from raw chunk IDs into original
SaveLoad ownership. `tools/renegade_cinematic_dependency_scan.py` now evaluates
the checked-out chunk-ID enum sources and scans registered
`SimplePersistFactoryClass` declarations, then annotates M13 `.ldd` and `.lsd`
chunk headers with source-owned subsystem and persist-factory names where the
original code exposes them. The tool remains metadata-only and does not export
retail payloads.

Current generated inventory:

- Output: `build/dev166-m13-mission-inventory.json`
- Source chunk symbols resolved: 191.
- Persist factories resolved: 127.
- `m13.ldd`: 4,490 chunk headers. Top-level chunks resolve to
  `CHUNKID_LEVEL_INFO` and `CHUNKID_LEVEL_DATA`. The level-data contents now
  resolve common original owners including `CHUNKID_COMBAT`,
  `PHYSICS_CHUNKID_DYNAMIC_DATA_SUBSYSTEM`, `CHUNKID_DYNAMIC_SAVELOAD`,
  `CHUNKID_CONVERSATION_MGR`, `CHUNKID_MAPMGR`, `CHUNKID_ENCYCLOPEDIAMGR`,
  `SoldierGameObj`, `VehicleGameObj`, `SimpleGameObj`, `PowerUpGameObj`,
  `ScriptZoneGameObj`, `SoldierObserverClass`, and WW3D render-object chunks.
- `m13.lsd`: 19,316 chunk headers. Top-level chunks resolve to
  `PHYSICS_CHUNKID_STATIC_DATA_SUBSYSTEM`,
  `PHYSICS_CHUNKID_STATIC_OBJECTS_SUBSYSTEM`, `CHUNKID_STATIC_SAVELOAD`,
  `CHUNKID_BACKGROUND_MGR`, `CHUNKID_MAPMGR`, and `CHUNKID_WEATHER_MGR`.
  Common resolved owners include `StaticPhysClass`, `StaticAnimPhysClass`,
  `LightPhysClass`, `WaypathClass`, `WaypointClass`, `Sound3DClass`, and
  `SoundPseudo3DClass`.
- The SimplePersistFactory internal object-data chunk
  `SIMPLEFACTORY_CHUNKID_OBJDATA` is recognized as `0x00100101`, which explains
  the high recurring object-data count in both M13 static and dynamic files.

Verification:

- `python3 -m tools.test_development_checkpoint` PASS.
- Direct invocation of every function in
  `tools/test_vita_m13_cinematic_preparation.py` PASS.
- `python3 tools/renegade_cinematic_dependency_scan.py --mission-inventory --quiet --output build/dev166-m13-mission-inventory.json`
  PASS and JSON validates with `python3 -m json.tool`.
- `pytest` is not installed in this WSL Python, so the focused pytest-style file
  was executed directly.

Acceptance boundaries:

- No ARM build, Vita3K runtime, physical runtime, visual correctness,
  performance, A/V sync, script-sequence, objective, death/reload, or campaign
  progression acceptance is claimed for Dev166.
- This does not decode object payload fields, old-pointer fixups, live script
  observer state, DDB preset transitive references, or W3D internals yet.

Next executable step: use the resolved SaveLoad ownership map to add bounded
runtime or static object-semantic inventory for M13 critical classes first:
`CinematicGameObj`, `SoldierGameObj`, `VehicleGameObj`, `ScriptZoneGameObj`,
`ConversationMgrClass`, `BackgroundMgrClass`, `WeatherMgrClass`, and dynamic
audio. The runtime pass should prove which objects, scripts, timers, audio
streams, and letterbox/camera-control states exist at intro start, ambush
initiation, Havoc death, and mission cleanup before further performance A/Bs.
