# Original M00 checkpoints

Use original Renegade save serialization, never process snapshots or fabricated
mission state. Dev104 maps Select + Square to original F5/Quicksave and routes
original save reads and writes to `ux0:data/renegade/user/save/`. The original
two quicksave slots still rotate; archive a passed segment before reusing them.
Runtime save/load and cross-build compatibility are pending validation.

Load Game admission checks the save's original embedded map through
SaveGameManager::Peek_Map_Name. Only M00 tutorial saves may pass the demo gate.
The native loader now receives the selected save instead of always loading a
fresh M00 MIX. The retail save format, scripts and object reconstruction stay
owned by the original engine. No new save is claimed until gameplay reaches a
proven segment and the original save operation completes.

`tools/tutorial_checkpoints.py` archives unchanged local .sav bytes and a
manifest in ignored `build/tutorial-checkpoints/`. Supply the SHA256 identity of
the unchanged retail dataset as `--content-id`; this is operator-supplied, not
automatically inferred. Creating build is provenance, not a compatibility key.
Bump the compatibility epoch when serialized semantics change. Matching hashes
and epoch permit an attempted load, not a claim that every future build works.

```bash
python3 tools/tutorial_checkpoints.py capture --id logan-complete \
  --user-dir /path/to/renegade/user --slot quicksaveA.sav \
  --build A3.5-dev104 --content-id "$RETAIL_CONTENT_SHA256" \
  --passed-evidence /path/to/retained-segment-receipt.json
python3 tools/tutorial_checkpoints.py restore --id logan-complete \
  --user-dir /path/to/renegade/user --content-id "$RETAIL_CONTENT_SHA256" \
  --slot rv_cp_logan_run2.sav --offline
```

Capture only after a segment is demonstrated, recording actual evidence rather
than marking a scripted checkpoint automatically passed. Restore only while
the game is stopped, into a new unused slot. Existing saves, profiles, registry
state, retail files and checkpoint masters are not overwritten. No hardware
access is performed by this host-local tool. Never package or publish saves.

Suggested segment boundaries: Logan movement/ladder/keycard; Sydney/EVA;
Gunner weapons; Hotwire vehicle training; final objective before original
mission completion. These are a plan, not completed gates. Keep one fresh
start-to-finish M00 run for final acceptance; resumed segments and recorded-input
replays reduce iteration time but cannot substitute for that full run.
