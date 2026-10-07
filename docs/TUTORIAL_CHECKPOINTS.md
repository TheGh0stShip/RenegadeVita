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

## Catalogue and boot straight into a segment

`catalog` reads only what the original save serializes: the level-info map,
description ("Quicksave A/B" for F5 saves) and the six Mission00 objectives
(status and game-time age) from the Combat objective chunk. The segment name
is derived from the youngest visible objective (for example `to-gunner`,
`gunner-range`, `mobius-refinery`); `logan-course` means every objective is
still hidden. It is a label, not proof of position or lesson completion.
Rows marked `REJECTED` would also be refused by the native envelope check.

```bash
python3 tools/tutorial_checkpoints.py catalog                      # vault masters
python3 tools/tutorial_checkpoints.py catalog --user-dir /pulled/user \
  --log /pulled/user/logs/<candidate runtime log>                   # live slots
python3 tools/tutorial_checkpoints.py launch --segment gunner-range \
  --user-dir /staging/user --content-id "$RETAIL_CONTENT_SHA256" --offline [--sticky]
python3 tools/tutorial_checkpoints.py verify-log --id <checkpoint-id> \
  --log /pulled/user/logs/<candidate runtime log>
```

`launch` restores the master into `user/save/rv_cp_<id>.sav` (reusing a
byte-identical slot, refusing a different one) and queues either the one-shot
`user/config/dev-checkpoint-launch-v1.txt` (`RVCP1 <slot>`) or, with
`--sticky`, the retained `user/config/tutorial-checkpoint-v1.flag`
(`RVTC1 <slot>`). Copy those two files to the same paths under
`ux0:data/renegade/user/`. Only `RENEGADE_DEVELOPMENT_CHECKPOINT=1` builds read
them; public packages ignore both. A one-shot request wins over the sticky flag;
the sticky flag is honoured at the first frontend entry of each process, so
quitting to the menu stays there. Delete the flag (or run
`request_tutorial_checkpoint.py --user-dir ... --offline --clear-sticky`) to
restore normal startup. `verify-log` passes only when the first
`A3.5 mission progress` line after the handoff shows the save's objective
vector; it does not prove full world or script restoration.
