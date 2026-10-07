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

## Soft-lock hunt (2026-10-07)

Evidence class: staged-source inspection, host Python reads of the read-only
Vita3K retail copy (`m05.ldd` conversation flags and bindings, cinematic
texts in `always.dat`/`M05.mix`), and one `arm-vita-eabi-g++ -fsyntax-only`
of the patched `staging/scripts/Mission05.cpp` (exit 0). No build, emulator
or device run. Line numbers are the staged file after these patches.

`Mission_Complete(true)` has one caller: 506/param 1 at `:301`. It does not
check objective state, so only the Patch → cathedral chain can block M05.

### Key conversations (`m05.ldd`, `ConversationClass` VARID_ISKEY)

Key: M05_CON003-008, 014, 037 and 038 (the zone radio briefings, the Patch
poke and two secondaries). Every other M05 conversation is non-key. A
non-key start while a key conversation plays stops at once with
INTERRUPTED, before the script's `Monitor_Conversation` (the M10 pattern).

### Fixed: objective locks (reachable, Low; mission still completes)

1. **Deadeye 502** (`:1289`, `:1396`). `M05_CON013` is non-key, and 502
   completes only on ENDED. A poke during a key radio (e.g. `M05_CON004`
   near the Inn), or leaving range mid-talk, left `poke_id == 3` and
   `conversation == true`. Deadeye could not be poked again, and 502 stayed
   pending. *Fix:* `scripts-a38-m05-deadeye-poke-rearm.patch`. The poke state
   and monitor are set before `Start_Conversation`, and an INTERRUPTED 300004
   re-arms the poke.
2. **Gunner 501** (`:1127`, `:1195`). `M05_CON010/011` are non-key, and
   `conversation` resets only on ENDED. The same refusal locked Gunner, so
   the post-Town-Square poke that plays `X5M_MIDTRO_A` (which completes 501)
   could not happen. *Fix:* `scripts-a38-m05-gunner-poke-rearm.patch`. The
   monitor is set before the start, an INTERRUPTED 300001/300002 clears
   `conversation`, and a refused first talk is replayed.

Both patches are idempotent (they only reassign script fields), add no saved
variable, and leave the ENDED path unchanged. They are registered after
`scripts-a36-m05-fire-loc-save.patch`. Staging: 545 ordered patches, PASS,
and only `Mission05.cpp` changed.

### Checked, no patch (retail-identical or not reachable)

- **Patch / cathedral start** (`:1440`, `:1492`). The first star poke always
  sends `M05_INITIATE_CATHEDRAL`, whatever happens to `M05_CON014`. CON014
  is key, and its callback accepts ENDED and INTERRUPTED. Receivers 100001
  and 100287 are placed objects.
- **504/506 ordering.** If Patch is poked before zone 100046 plays
  `M05_CON005`, the 504 completion arrives before 504 exists. It is ignored,
  and the zone later adds 504 as pending. Nothing sends the zone's 100/100
  suppress event. The 501 and 502 zones are the same. This is cosmetic only,
  because `Mission_Complete` does not read objectives.
- **Hotwire 503** (`:910`). `M05_CON009` is non-key, but the
  `M05_X5N_MIDTRO_B` zone (`:7464`) destroys Hotwire and its text sends
  503/1, so there is a second path. The `M05_CON001` start callback only
  adds 503 (`:376`).
- **Cathedral vehicle counter** (`:6110`, exact `== 0`). Delay-0 customs are
  dispatched synchronously. `Apply_Damage` stops at health ≤ 0, killed
  vehicles are delete-pending at once, and `VehicleGameObj::Object_Expired`
  skips Killed once delete-pending. So each counted vehicle sends exactly one
  KILLED, and a flipped artillery that expires still sends Killed. No placed
  object or other text attaches `M05_Cathedral_Apache/_Artillery`, so the
  counter cannot go negative before completion. A placeholder killed while
  slung sends neither event.
- **Black Hand count** (`> 7`, `:6305`). Each `X5D_CHTroopdrop7/8/10` drop
  gives one soldier: a minigunner with "" from 7, and rocket soldiers with
  "8" and "10". It also gives the transport helicopter with
  `M05_Cathedral_Para_Unit ""`, which `Destroy_Object` removes at frame 280.
  It counts only if the player shoots it down. The 8 and 10 soldiers re-drop
  on each kill while `blackhand_cnt < 9`, so the supply is unbounded. Killed
  is not filtered by killer, so ally kills count. **Deferred retail risk:**
  a soldier removed without Killed (soldiers' `Object_Expired` only deletes,
  e.g. a COLLIDE_KILL crush) ends its chain. Losing both chains caps the
  count at 1 + shot-down helicopters.
- **Town Square** (`:4416`). This needs exact `unit_id1 == 6 && unit_id2 ==
  6 && unit_id3 == 1 && unit_id4 == 1`, and gates secondary 507 and Gunner's
  `500/500`. The supply is exactly 6 + 6: two placed units each, plus two
  `X5D_CHTroopdrop1/2` drops of two. `Enable_Spawner(100117/100118)`
  (`:4384`) targets placed soldiers, not spawners, so it is a no-op. Unit 4
  is the flame tank from spawner 100618, enabled only by the roadblock zone
  100623 (`:6627`). Its respawn count was not decoded. A lost unit, or a
  second flame tank, blocks 507 and 501 permanently. This is retail design,
  is not on the 506 chain, and is deferred.
- **Save/load and death.** The controller, Patch, Apache, para-unit and
  Dead6 states are saved. Script timers and custom timers are saved with
  their objects. Death restarts or reloads the level.

### Physical test additions

- Enter the Inn radio zone and poke Deadeye while `M05_CON004` still plays.
  Deadeye must stay pokable, and a second poke must play CON013 and complete
  502. Repeat for Gunner during `M05_CON006`.
- In the cathedral battle, record `blackhand_cnt` progress. Telemetry should
  show a REINFORCE for every para death before completion.

## Follow-up fixes (2026-10-07)

Evidence class: staged-source inspection, host Python reads of the read-only
Vita3K retail copy (`m05.ldd` spawner and script records, `objects.ddb` in
`always.dbs`, cinematic texts in `always.dat`), one `arm-vita-eabi-g++
-fsyntax-only` of the patched `Mission05.cpp` (exit 0, only the existing
`-Wwrite-strings` warnings, `-Wimplicit-fallthrough` clean), and a re-run of
`tools.audit_conversation_gated_objectives` into a scratch file. No build,
emulator or device run. Line numbers are the staged file after these
patches.

Three patches are registered after `scripts-a38-m05-gunner-poke-rearm.patch`.
Staging: 573 ordered patches, PASS, zero fuzz, and only `Mission05.cpp`
changed. Each new flag is a `SAVE_VARIABLE` on an unused ID. Scripts are
value-initialised (`ScriptRegistrant::Create`), so saves from before the
patches load with the flags false. No sha256 anchor changed.

### Retail data decoded

- **Town Square supply.** The `M05_TownSquare_Unit` bindings are placed
  100108/100111 (ID 1), 100109/100110 (ID 2) and 100117/100118 (ID 0).
  Spawner 100115 also spawns ID 0 units. `X5D_CHTroopdrop1/2` each drop two
  ID 1 or ID 2 soldiers. `M05_TownSquare_Tank` is placed 100023 (ID 3).
  ID 0 is no `switch` case, so it is never counted.
- **Flame tank.** Spawner 100618 has definition 82050342 with SpawnMax 1,
  StartsDisabled 1 and KillHibernatingSpawn 0. It carries
  `M05_TownSquare_FlameTank "4"` and `M08_Mobile_Vehicle`, which never
  destroys the tank. `SpawnCount` is saved and never reset, so exactly one
  flame tank exists. A second flame tank is not possible.
- **Removal without `Killed`.** All damage, including ally fire and
  visceroid conversion, reaches `DamageableGameObj::Apply_Damage`, which
  sends `Killed` first. A flipped vehicle also sends `Killed`. One path
  calls only `Destroyed`: `PhysicalGameObj` deletes an object that falls
  more than 20 m below the level extents. No M05 script `Destroy_Object`s
  these units.

### Fixes

1. **Town Square 507 and Gunner's 501 path.** Before this fix, one lost
   counted unit stalled the drop schedule or left a counter below its target.
   That blocked 507 and the 500/500 leave order for the rest of the mission.
   *Fix:* `scripts-a38-m05-townsquare-count-robust.patch`.
   - The check uses `>=` (`:4460`). Retail supplies exactly 6/6/1/1, so the
     normal path fires on the same kill.
   - `M05_TownSquare_Unit` (`:4531`), `M05_TownSquare_FlameTank` (`:4562`)
     and `M05_TownSquare_Tank` (`:1864`) report a `Destroyed` without
     `Killed` once as the same REINFORCE. This keeps the drop schedule
     moving.
2. **Black Hand count (`> 7`, `:6195`).** An ID 8 or 10 soldier removed
   without `Killed` ended its re-drop chain. *Fix:*
   `scripts-a38-m05-blackhand-redrop-on-loss.patch`.
   - `M05_Cathedral_Para_Unit::Destroyed` (`:6475`) reports such a soldier
     once as `M05_CATHEDRAL_REINFORCE` with its ID, so the chain continues.
   - `Killed` also sets the flag, and there is no report after
     `M05_CATHEDRAL_FREE`.
   - ID "" units are not reported. These are the drop-7 minigunner and the
     transports, which the text removes at frame 280.

   The count therefore cannot cap below 8. The `< 9` re-drop bound and the
   vehicle counter are unchanged.
3. **`M05_Escapee_Brother` (509) and `M05_Babushka` (510): was REVIEW, now
   a real lock.**
   - **Receivers.** Objective controller 100001 handles 509/1, 509/2, 510/1
     and 510/2 (`param` 1 accomplishes, 2 fails). 5001 is
     `M05_CUSTOM_ACTIVATE` to 100037, the escapee visceroid. Neither
     objective gates `Mission_Complete`.
   - **What was lost.** The Brother's ENDED path also drops the Personal Ion
     Cannon powerup and starts the invaders.
   - **How it locked.** Both started a non-key conversation before
     `Monitor_Conversation`. Their own radio briefings, `M05_CON038` and
     `M05_CON008`, are key, so poking during the briefing refused the start
     with no monitor. A walk-away INTERRUPTED was ignored. Either way the
     character could never be poked again.

   *Fix:* `scripts-a38-m05-escapee-babushka-poke-rearm.patch` (M10 pattern).
   - The poke state and monitor are set before `Start_Conversation`
     (`:2414`, `:2754`).
   - INTERRUPTED or UNABLE_TO_INIT of 300509 re-arms the poke (`:2433`,
     `:2783`).
   - Babushka re-arms to a new `case 3` (`:2743`), which replays only the
     thanks conversation. Her first-poke animation, `Action_Reset` and team
     change run once.
   - The ENDED handlers are guarded by the existing saved `complete` and
     `saved` flags, so 509/1 and 510/1 are sent exactly once.

   In the scratch audit re-run, the M05 row changed from 1 FIXED and 2
   REVIEW to 3 FIXED and 0 REVIEW.

### Lost-unit report mechanics

Each report is a `Send_Custom_Event` with a 1 s delay. It is held as a
custom timer on the receiving controller (`Start_Custom_Timer`), which only
`Think` runs. Level exit and reload use `GameObjManager::Destroy_All`, which
calls `Destroyed` on every object and runs no `Think`. A teardown therefore
discards the report and cannot change objectives.

### Not changed

- **Cathedral 506 chain.** No hole was found. The vehicle counter and the
  REINFORCE kill path are untouched.
- **Stuck units.** A live but unreachable Town Square or Black Hand unit
  still has to be killed (retail design). Town Square units walk to 100112.
  Para units chase the star.
- **Flame tank not spawned.** If the player never enters the roadblock zone
  100623, the flame tank never spawns and 507 stays pending. This is retail
  design.

### Deferred

- Regenerate `CONVERSATION_GATED_OBJECTIVES.md` from the integrated tree.
  This round only re-ran the audit into a scratch file.

### Physical test additions

- Poke the Escapee's brother while `M05_CON038` plays, and Babushka while
  `M05_CON008` plays. Each must stay pokable, and a later poke must play the
  conversation and complete the objective once. Check that only one Ion
  Cannon powerup appears.
- Complete Town Square normally. 507 and Gunner's departure must happen on
  the last kill, as before.
