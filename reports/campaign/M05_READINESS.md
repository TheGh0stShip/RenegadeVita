# M05 campaign readiness (source and retail-metadata review)

Evidence class: source inspection and a read-only host audit of user-owned
retail metadata. No build, emulator or physical Vita run. Nothing here proves
that M05 completes on Vita.

## Result

The first review found no M05 defect on the success chain. The later Full
audit (below) found a game-thread hang on an optional civilian poke and a
save/load gap, and fixed both with patches. The success chain is complete in
source. Every object it uses is present in the
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

- **Save/load during the cathedral battle.** On PC, `M05_Cathedral_Apache` did
  not save `fire_loc` (the line was commented out), and `M05_Cathedral_Artillery`
  registered `fire_loc[1]` with a duplicate ID 1. After a load, both could
  target an unresolved ID. Both are now fixed:
  `scripts-a36-m05-save-variable-ids.patch` and
  `scripts-a36-m05-fire-loc-save.patch` (see Full audit). The vehicle counters
  were always saved, so completion was never affected.
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

## Full audit (2026-10-07)

Evidence class: source inspection, host Python audits of read-only retail
metadata (Vita3K copy), and an `arm-vita-eabi-g++ -fsyntax-only` check of the
patched `staging/scripts/Mission05.cpp`. There was no build, link, VPK,
emulator or Vita run. Nothing here proves that M05 completes or renders
correctly. Detailed receipts are in the git-ignored `build/m05-full-audit/`
directory (`m05-bindings.json`, `m05-conversations.json`).

Line numbers refer to the staged `Mission05.cpp` after these patches.

### Defects found and fixed

1. **High: game-thread hang when a civilian is poked.** In
   `M05_Resistance_Poke_Conversation` (`:7752`), `Poked()` sets a conversation
   range only for these presets:
   - `Civ_Resist_Female_v0*`
   - `Civ_Resist_Male_v0*`
   - `Civ_Resist_Male_v1*`

   The `M05_Civ_Resist` spawners (100104, 100115, 100140, 100227, 100228,
   100771, 100772) can also spawn `Civ_Resist_Male_v2b` and
   `Civ_Resist_Male_v2c`. Those civilians call `Index(0, 0)`, whose loop can
   only exit when `random == 0 && last != 0`. `last` was never initialized,
   because scripts are allocated with `new T`. On zero-filled heap memory the
   first poke therefore spins forever.

   There is no `Monitor_Conversation`, and orator-only conversations with
   two or fewer orators never report `CONVERSATION_ENDED`. Each civilian
   therefore reaches `Index` only once, and the hang depends only on the
   initial `last` value. The same source is used on PC.

   *Fix:* `scripts-a36-m05-resistance-poke-index-hang.patch`. It sets
   `last = -1` in `Created` (`:7773`), and `Index` returns `Min` for a
   one-entry range (`:7825`). Every range that already terminated returns the
   same index as before.
2. **Low: save/load target loss.** `M05_Triangle_Tank` (`:1693`) and
   `M05_Cathedral_Apache` (`:6121`) fill `fire_loc` only in `Created`, and
   neither saved it. After a load, the timers called `Find_Object` with
   uninitialized IDs.

   *Fix:* `scripts-a36-m05-fire-loc-save.patch` registers both tables with the
   unused ID 2 (12 and 40 bytes).

Both patches are registered in `tools/stage_sources.sh` after
`scripts-a36-m05-save-variable-ids.patch`. Staging applied them with zero fuzz
(527 ordered patches), and the syntax check exited 0.

### 1. Script names and parameters

- **Level bindings.** 467/467 bindings are registered:
  - 362 persisted
  - 56 spawner
  - 48 definition
  - 1 combat-start

  Parameter shapes (`live_script_parameters.json`, M05 row):
  - 165 have equal counts.
  - 301 are `excess_values`: a single `0` token on a script whose descriptor
    is `""`. `Get_Parameter` never reads past the descriptor, so the token is
    ignored.
  - 1 is `parameters_unrecorded` (the combat-start script `M05_Havoc_DLS`).
  - 0 are `fewer_values`.
- **`Attach_Script` from source.** Every target is registered. The parameter
  counts match the descriptors:
  - `M05_Cathedral_Apache`: 1/1
  - `M05_Cathedral_Artillery`: 2/2
  - `M05_APC_Deploy_Soldier`: an object ID (see the existing buffer patch)
- **`attach_script` from the 40 M05 cinematic texts.** There are 28 distinct
  script/parameter pairs, all registered and matching their descriptors, with
  two exceptions:
  - `M05_Inn_Reinforcements` (`x5d_chtroopdrop5/6.txt`)
  - `M05_Park_Unit` (only in the `always.dat` copy of
    `x5d_c130troopdrop7.txt`, which the `Always2.dat` copy shadows)

  Neither has a script in the shipped source. Both are known leads
  (retail-identical).

### 2. Events, timers and object IDs

- **Custom events.** All 96 live `Send_Custom_Event` sites use literal targets.
  Every serialized target has a receiver for the event type. Objective
  controller 100001 dispatches on `param`, with `type` as the objective ID.
  The only targets that are not serialized are the known ones:
  - 100272 and 100273 (`M05_Activate_Entrapment_Civ`)
  - 101239-101241 (`M05_Activate_Execution`)

  `SCRIPT_PTR_CHECK` drops these sends, as on PC.
- **Timers.** Every timer ID started has a matching `Timer_Expired` branch,
  with one exception. `M05_DEAD6_Grenadier` (Patch, `:1419`) starts `GO_STAR`
  (`:1521`) but has no `Timer_Expired`. The timer expires with no effect. This
  is retail-identical and not on the 506 chain.
- **`Find_Object` literals.** The IDs not located are 100133, 100134, 100272,
  100273, 101239, 101240 and 101241, plus spawner-only ID 100652. They are
  unchanged from the first review.
- **Other 6-digit literals.** The rest are waypath IDs, and each is present in
  `m05.lsd`, with one exception. Waypath 101236 (`M05_Surprise_Tank`, `:5738`)
  is absent from the level data. `PathClass::Initialize(NULL, …)` handles NULL
  and `WWASSERT` is compiled out, so the tank attacks without a path, as on PC.
  100650 is an action ID and 100000 is a damage amount.

### 3. Content resolution (`always.dat`, `Always2.dat`, `M05.mix`, Data root)

- **Script literals.** These all resolve:
  - presets
  - models
  - animations
  - music
  - WAV files
  - POG textures
  - explosions

  One sound preset does not: `"Medium Explosion Sound Twiddler"`
  (`M05_Explode_Debris`, `:6689`). `Create_Instant_Sound` returns 0 for it.
  Retail-identical.
- **Conversations.** 0 literal names are unlocated and 0 orator indices are
  invalid. All 37 names in `Resistance_Conv_Table` resolve.
- **Cinematic texts.** 40 texts (1,145 commands) are checked. All models,
  animations, audio and attached scripts resolve, except:
  - the four known missing texts (`X5C_Wintroops09/13/19`, `X7B_ApacheStk`)
  - three missing `create_real_object` presets:
    - `Civ_Resist_v1c` and `Civ_Resist_v0a` (`x5c_wintroops05.txt`)
    - `Civ_Resist_Male_v0b` (`x5c_wintroops11/18.txt`)

  `Command_Create_Real_Object` null-checks, so those civilians do not spawn.
  Retail-identical.

### 4. Crash review

- **Random-indexed tables.** All are in bounds. `CRandom::Get_Int(min, max)`
  returns a value in `[min, max)`.
- **Arithmetic.** There is no division or modulo by a variable.
- **Buffers.** The only `sprintf` was already hardened.
- **NULL objects.**
  - `Join_Conversation(NULL)` is valid. It covers Mendoza's lookup of spawner
    100652.
  - `Monitor_Sound` and `Innate_*` are only called on `obj` itself.
- **Use after destroy.** `M05_Swap_Artillery::Custom` (`:7343`) uses `obj`
  after `Destroy_Object`. This is safe because destruction is deferred
  (`Set_Delete_Pending`).
- **Mendoza in M05.** `M05_Mendoza` is a spawner definition, not
  `MendozaBossGameObj`. Its C4, conversation and waypath 100011 route uses only
  guarded commands.

### 5. Completion chain

The chain is unchanged and intact.

**Cathedral vehicle counter.** The counter rises by one for each of these:
- the two Apaches, counted when the controller creates them
- each of the three artillery swaps

Each one sends exactly one `VEHICLE_KILLED`. A placeholder destroyed before its
swap sends neither event, so the counter cannot go negative.

**Para-unit supply.** The texts attach `M05_Cathedral_Para_Unit` six times:
- four with an empty `Soldier_ID`
- one with Soldier_ID 8
- one with Soldier_ID 10

Each kill of an 8 or 10 unit re-drops two more units while `blackhand_cnt < 9`.
The 8 kills that `blackhand_cnt > 7` requires are therefore available. Soldier
ID 7 never occurs, so `case 7` is dead code.

### 6. Port patches touching M05

The following patches were all re-read and apply with zero fuzz:
- `scripts-a36-m05-dead6-help-failed-text-save.patch` (ID 4, zeroed in
  `Created`)
- `scripts-a36-m05-apc-deploy-param-buffer.patch`
- `scripts-a36-m05-save-variable-ids.patch` (`M05_Inn_Tank` ID 3,
  `M05_Cathedral_Artillery` `fire_loc[1]` ID 2)
- the two new patches above

The two new patches sit after the existing M05 patches. No later patch touches
`Mission05.cpp`, and no sha256 anchor was changed.

### Physical test additions

- Poke one of each kind of resistance civilian near the spawners above.
  Include a `Male_v2b/v2c` civilian if one can be identified. The game must
  not freeze.
- Quicksave and reload while the Triangle tank or the cathedral Apaches are
  active. They should keep firing at their authored targets.
