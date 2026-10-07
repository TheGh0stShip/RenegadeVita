# M05 campaign readiness (source and retail-metadata review)

Evidence class: source inspection and a read-only host audit of user-owned
retail metadata. No build, emulator or physical Vita run. Nothing here proves
that M05 completes on Vita.

## Result

No M05-specific port defect was found, so no source or patch change was made.
The success chain is complete in source. Every object it uses is present in the
retail `m05.ldd` with the expected script attached. All 467 M05 script bindings
resolve through the static registry. Two script names are attached only from
retail cinematic text files and are absent from the shipped source. Retail PC
handles them the same way, and they fail without crashing.

## Success chain (`staging/scripts/Mission05.cpp`)

1. The level start script `M05_Havoc_DLS` (`:387`) is the `combat_start_script`
   binding and grants the starting weapons. Placed object 100001 has
   `M05_Objective_Controller` (`:45`) attached. Its `Created` handler starts the
   music and timers. It attaches `Test_Cinematic` `X5I_TroopDrop7.txt` (`:81`),
   which drops `M05_Mendoza`. The `M05_CON001` conversation then adds objective
   503 (`:378`).
2. Rescue objectives:
   - 503 Hotwire: `M05_DEAD6_Engineer`, object 100002, completes at `:912`.
   - 501 Gunner: `M05_DEAD6_Rocket_Soldier`, object 100003, completes at `:1196`.
   - 502 Deadeye: `M05_DEAD6_MiniGunner`, object 100004, completes at `:1281`.

   These are not required for success. If any of these characters dies, the
   mission fails: param 2 calls `Mission_Complete(false)` at `:313-323`. Other
   failure calls are at `:947` and `:1448` (Patch killed).
3. **Patch.** Placed object 100006 has `M05_DEAD6_Grenadier` (`:1419`) attached.
   On the first poke by the star (`:1451`) it starts `M05_CON014` and sends
   `M05_INITIATE_CATHEDRAL` (5014) to 100287 (`:1471`). When conversation 300004
   ends or is interrupted, 504 is accomplished and 506 is added (`:1490-1493`).
4. **Cathedral battle.** Placed object 100287 has `M05_Cathedral_Controller`
   (`:5987`) attached.
   - **Vehicle counter.** The counter goes up by 1 for each of 2 `Nod_Apache`
     with `M05_Cathedral_Apache` (`:6023`, `:6099`). It also goes up by 1 for
     each `M05_Swap_Artillery` swap (`:7362`). The three swaps come from
     `M05_XG_VehicleDrop4/5/6.txt`: the text sends `Send_Custom #4, 5029`, which
     `Destroy_Object` defers through `Set_Delete_Pending` at
     `scriptcommands.cpp:429`. Each swap spawns `Nod_Mobile_Artillery` with
     `M05_Cathedral_Artillery`.
   - **Vehicle kills.** `Killed` on an Apache (`:6276`) or a swapped artillery
     (`:7431`) lowers the counter.
   - **Infantry.** Infantry come from `X5D_CHTroopdrop7/8/10.txt`. Each attaches
     `M05_Cathedral_Para_Unit` with Soldier_ID ""/8/10. Each kill sends
     `M05_CATHEDRAL_REINFORCE` (`:6352`). That raises `blackhand_cnt` up to 9,
     and Soldier_ID 7, 8 or 10 re-drops its squad (`:6053-6083`).
5. **Completion.** When the vehicle counter is 0 and `blackhand_cnt` is above 7
   (`:6087-6091`), the controller does two things. It broadcasts the
   `M05_CATHEDRAL_FREE` logical sound, which kills the remaining para units and
   Apaches without counting them. It also sends 506/param 1 to 100001. The
   controller's `Custom` handler then calls `Mission_Complete(true)` (`:299-301`).
   `CombatGameMiscHandlerClass::Mission_Complete` (`combatgmode.cpp:1716`) only
   latches `PendingCampaignContinue`. A repeated success call is therefore
   idempotent.

## Data / registry checks

All checks ran read-only against the Vita3K retail copy. The receipt is in the
git-ignored `build/m05-readiness/m05-bindings.json` and is not committed.

- **Script bindings.** 467/467 bindings are registered:
  - 362 persisted
  - 56 spawner
  - 48 definition
  - 1 combat-start

  This matches the M05 row of `reports/generated/sweeps/live_script_bindings.json`
  (archive `d3b38752…`, `unregistered_bindings: 0`).
- **Discovered closure.** 124 scripts and 0 binding decode findings.
- **Chain object IDs.** All are serialized game objects: 100001, 100002,
  100003, 100004, 100006, 100047, 100048, 100244, 100287, 100632, 108474 and
  108475.
- **Cinematic text files.** The chain uses `X5D_CHTroopdrop7/8/10`,
  `M05_XG_VehicleDrop4/5/6` and `X5I_TroopDrop7`. All of them are in `always.dat`
  and have `records_match: true` in `host_retail_cinematic_parser.json`.
- **Script defaults.** `Mission05.cpp` compiles with
  `renegade_campaign_script_defaults.h` (`CMakeLists.txt:663`). Defaulted
  arguments match the original `scriptcommands.h`.
- **Unresolved definition IDs.** 18 typed sub-definition IDs did not resolve.
  They are weapon eject/muzzle-flash physics defs and are global
  `objects.ddb` gaps, not M05 owners.

## Leads (not blockers, retail-identical)

- **Unregistered cinematic scripts.** `M05_Inn_Reinforcements` is attached from
  `x5d_chtroopdrop5/6.txt` (Inn reinforcements). `M05_Park_Unit` is attached
  from the `always.dat` copy of `x5d_c130troopdrop7.txt`. Neither has a
  `DECLARE_SCRIPT` in the shipped source. `Attach_Script`
  (`scriptcommands.cpp:557-572`) logs this and attaches nothing. Archive order
  is Always2 then Always. This order is the same in `init.cpp:740-742` and
  `a31_vita_runtime.cpp`, so the `Always2.dat` copy of `x5d_c130troopdrop7.txt`
  is preferred, and it attaches the registered `M05_ParkSniper`. Neither script
  is on the 506 path.
- **Missing text files.** `X5C_Wintroops09/13/19.txt` (Roadblock and Triangle
  reinforcements) and `X7B_ApacheStk.txt` (`M05_Activate_ApacheStrike`,
  `:7177`) are not in the retail archives. `Load_Control_File`
  (`Test_Cinematic.cpp:213-216`) returns on a missing file. This affects only
  optional reinforcement waves.
- **Object IDs not serialized.** 100133/100134 (`M05_Cache_Assault`),
  100272/100273 (`M05_Activate_Entrapment_Civ`), 101239-101241
  (`M05_Activate_Execution`) and 100652 (a spawner ID used by `M05_Mendoza`)
  are not serialized game objects. `Send_Custom_Event` with a null target
  returns at `SCRIPT_PTR_CHECK(to)` (`scriptcommands.cpp:657`), and Cache_Assault
  null-checks. Side encounters lose these sends, as on PC.
- **Objective 513.** 513 is never added because `:1286` is commented out, but
  `:1412` still sets its status. `ObjectiveManager::Set_Objective_Status`
  ignores unknown IDs.

## Risks

- **Save/load during the cathedral battle.** `M05_Cathedral_Apache` does not
  save `fire_loc` (commented out at `:6132`). `M05_Cathedral_Artillery`
  registers `fire_loc[1]` with a duplicate ID 1 (`:7392-7393`), and
  `Auto_Save_Variable` drops the duplicate. After a load, both can target an
  unresolved ID, and `Find_Object` then returns NULL. The vehicle counters are
  saved, so completion is unaffected. Same as PC.
- **Counter stall.** If a swapped artillery or an Apache is stuck where it
  cannot be reached or killed, the counter never reaches 0. This is a
  retail-level design risk. Physical runs should watch vehicle drops for
  physics or collision regressions.
- **Failure after success.** Patch or Dead6 dying after 506 still calls
  `Mission_Complete(false)` → `cGod::Mission_Failed` while
  `PendingCampaignContinue` is set. The precedence is handled by the generic
  campaign handoff and is not M05-specific.
- `M05_APC_Deploy` formatted object IDs into `char param1[10]` (`:7569`). This
  overflows only for dynamic IDs (10 digits). Every M05 owner is a placed
  6-digit object (100144/100247/100248/100256/100608), so it is not reachable
  in M05. Hardened anyway by `scripts-a36-m05-apc-deploy-param-buffer.patch`
  (`char param1[16]` plus `snprintf`); host syntax-checked only.

## Physical test route

Start from campaign or direct M05 entry. Then:

1. Confirm the `M05_CON001` audio and the Mendoza troop drop at start.
2. Rescue Hotwire, Gunner and Deadeye. Keep them alive.
3. Go to the cathedral and poke Patch (object 100006).
4. Confirm `M05_CON014`, the music change, and the 504 → 506 objective update.
5. Kill the 2 Apaches and the 3 artillery pieces. The artillery arrives by
   transport drop and swaps at about frame 437.
6. Kill at least 8 Black Hand para troops.
7. Expect the remaining enemies to die from `M05_CATHEDRAL_FREE`. Then expect
   objective 506 to complete and the campaign to continue to the next
   `campaign.ini` entry.

Optional: quicksave during step 5 and reload to exercise the risk above.
Capture flight-recorder logs and any PSP2 dump.
