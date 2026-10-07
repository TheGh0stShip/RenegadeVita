# M10 completion readiness (source + retail-data trace)

Evidence class: staged source inspection and read-only host parsing of the
user's Vita3K retail copy (`M10.mix` SHA-256 `c9bdaa94…3720ec`, matching
CAMPAIGN_SOURCE_MAP_RECONCILIATION). No build, emulator, device or network
action. No retail content is copied here; only names, IDs and counts.

Verdict: no source defect blocks the authored M10 completion chain. One
retail ordering hazard could lose primaries 1001/1002/1004/1005 when a key
conversation was playing. It is now closed for M10 only by
`scripts-a38-m10-objective-conversation-resend.patch` (see
[the fix section](#key-conversation-preemption-fix-2026-10-07)). Native
completion is still unproven; it needs a physical run.

Line numbers in the sections written before that fix refer to the staged
`Mission10.cpp` before it (commit `03447e3`). Since the fix, lines :1-679 are
unchanged, lines :680 to about :2715 move by +4 to +51, and later lines move by +65.

## Objective chain to `Mission_Complete(true)`

All `staging/scripts/Mission10.cpp` unless noted. Controller object `1100154`
(preset `Daves Arrow`, def 81960001) carries `M10_Objective_Controller` as a
persisted level script in `m10.ldd`.

1. `Created` → `HAVOCS_SCRIPT` timer (0.5 s) at :61; `Timer_Expired` adds
   pending objective 1003 and attaches `M10_Havoc_Script` to STAR (:566-580).
2. `Custom(type 1000-1025, param 1)` marks accomplished and counts primaries:
   `type < 1008 || type == 1012` (:532-552). Eight primary IDs exist; 1003 is
   only sent last.
3. Six primary senders. Each sender is the conversation *monitor*, and it
   reports from `Action_Complete` when that conversation ends:
   - 1001 Power Plant (obj 1153931): Killed → M10CON014 → :720-728
   - 1002 Con Yard (1153933): Killed → M10CON005 (action 100005) → :755-762
   - 1004 Comm Center (1153932): Killed → M10CON011 (100011) → :891-899
   - 1005 / 1007 / 1006 gates: `M10_Gate_Check` on 1100166 / 1100169 / 2017706
     (level params `1005,…`, `1007,…`, `1006,…`), `Poked` with key 1
     (:2683-2747) plus conversation ends 100002/100008/100017 (:2661-2679)
4. 1012 Level-1 key: `M10_Refinery_Key_Grant` on 2000890, Killed → creates
   `Level_01_Keycard` + `M10_Refinery_Keycard` (:2631-2642). Pickup →
   `CUSTOM_EVENT_POWERUP_GRANTED` → 1012 (:3355-3366).
5. When the seventh primary is reached, M10CON019 plays and an
   `Invisible_Object` runs `Test_Cinematic` `X10I_GDI_Drop_PowerUp.txt`
   (:536-545). That file is in `always.dat`, not in `M10.mix`. This explains
   "no .txt in its MIX": global cinematics are not a gap. At frame 145 it
   creates `POW_IonCannonBeacon_Player_Grant` on bone `Box01` and attaches
   `M10_Ion_Cannon`.
6. Beacon pickup → `PowerUpGameObj::Grant` (`staging/combat/powerup.cpp:738-760`,
   byte-identical to upstream) → `M10_Ion_Cannon::Custom` (:602-611) → 1003
   param 1 → `primary_count >= 7 && type == 1003` → 5 s `MISSION_COMPLETE` timer
   (:547-549) → `Commands->Mission_Complete(true)` (:595-597).

## Data/registry closure (host parse, `tools/audit_m13_level_owners.py` helpers)

- `m10.ldd`: 628 script bindings, 70 unique names. All 70 resolve in the
  static registry: 1,697 `DECLARE_SCRIPT` names from the 44 Scripts.dsp
  sources. `m10.lsd` has none.
- All 70 placed/spawner preset definitions exist in `always.dbs` `objects.ddb`.
- All 13 literal `Create_Object` presets and the cinematic beacon preset exist.
- All 57 `Create_Conversation` names exist except `M03CON068`. Its only use is
  `M10_Radar_Scramble::Entered` (:4367), which is not on the completion chain.
  `Create_Conversation` returns -1 when it is missing (scriptcommands.cpp:2458),
  and every later call on id -1 is a no-op, so retail PC behaves the same way.
- Cinematics: seven of the files the script references are in `always.dat`.
  The ten `X10A_Apache_0x` / `X10A_Trnspt_0x` flyovers (:3425-3435) are missing
  from every retail archive. `Test_Cinematic` logs the failed open and
  destroys its controller (Test_Cinematic.cpp:209-216, :1074-1079). This matches
  retail and is not a blocker.

## Audio dependence

- `M10_Ion_Cannon_Detector` (:2024-2060) depends on a DESIGNER07 *logical*
  sound. That sound only exists if a real audible sound plays
  (`AudibleSound.cpp:514-525`, `:1846-1867`). However, no retail M10
  level or preset binds this script, so the dependency is unreachable.
- The real dependency is on conversation end. Five building/gate primaries,
  which can supply six counts, complete only when their monitored conversation
  ends (`activeconversation.cpp:1069-1092`). The remark timer comes from speech
  `Get_Duration`. It falls back to 2.0 s when no speech object is created
  (`soldier.cpp:3570`, `:3599-3601`), so missing audio delays dialogue but does
  not stall progression. Residual risk is the known zero-duration speech case in
  KNOWN_GAPS (immediate advance, which is still terminating).

## Risks (open, not fixed)

- `primary_count` counts sends, not distinct objectives. Repeat sends
  are original behaviour (e.g. the 1006 gate paths and the 1007 detector path).
- If 1003 arrives before seven other primaries, completion never fires.
  The authored data prevents this, because the beacon spawns only after count 7.
- Beacon delivery needs the drop cinematic to reach frame 145 and the `Box01`
  bone to resolve on the slot-6 model. The grant itself cannot be refused:
  `POW_IonCannonBeacon_Player_Grant` (def 81950139) has `AlwaysAllowGrant=1`
  and `GrantWeaponID=0`, so `PowerUpGameObjDef::Grant` sets `STATE_GRANTING`
  (powerup.cpp:449-454) even when the player's beacon ammo is full (see the
  full audit below).
- Conversation `Action_Complete` delivery requires the killed building to stay
  a live monitor. Buildings persist after destruction, but this is unverified
  on Vita. Source trace of delivery, zero-length
  speech and save/load: [CONVERSATION_COMPLETION.md](CONVERSATION_COMPLETION.md).
- Large-base performance, Obelisk/Apache/SAM behaviour, M08/M10 Apache callback
  reachability (KNOWN_GAPS 2026-10-04) and save/reload mid-mission are not
  covered here.

## Physical test route

1. Start M10 from a campaign save or the dev launcher. Confirm that objective
   1003 appears about 0.5 s in and that M10CON064 plays.
2. Kill the Refinery key carrier (2000890), pick up the Level-1 key, and confirm
   1012.
3. Use the key on the SE, NW and NE gate consoles in turn. Confirm M10CON002
   and 1005 when it ends, then 1007 and 1006 completing on the poke itself.
   M10CON008/M10CON017 never play with retail data (see the full audit).
   On a second run, poke the SE console while a key conversation (for example
   the M10CON064 intro) is playing. 1005 should complete on the poke, with no
   M10CON002 line (see the fix section below).
4. Destroy the Power Plant (M10CON014 → 1001), the Comm Center (M10CON011 →
   1004) and the Con Yard (M10CON005 → 1002). Let each conversation finish.
5. On the seventh primary, confirm M10CON019 and the GDI drop cinematic, and
   that the Ion Cannon beacon powerup appears.
6. Pick up the beacon. Mission success should follow about 5 s later, then score
   and the M11 handoff.
   Capture runtime log breadcrumbs: conversation transition/monitor
   telemetry, `Text_File_Open` of `X10I_GDI_Drop_PowerUp.txt`, and the
   campaign flight recorder's mission-complete event.

## Full audit (2026-10-07)

Evidence class: staged source, read-only host parsing of `local-builder/retail-host/Data`
(`M10.mix`, `always.dat`, `always.dbs`), the existing all-map receipt
`build/s4-all-map-bindings/m10-bindings.json` and the live script sweeps, plus one
`arm-vita-eabi-g++ -fsyntax-only` of the patched `Mission10.cpp` (exit 0, only the
pre-existing `-Wwrite-strings` warnings). No build, link, VPK, emulator or device.
Line numbers are staged `Mission10.cpp` unless noted.

### Script owners and bindings

- M10 scripts live in `Mission10.cpp` (79 `DECLARE_SCRIPT`). The two `M10_*` scripts in
  `Mission03.cpp` (`M10_Elevator_All_Zone`/`_Controller`, :6886/:6911) are bound only
  in `M03.mix` (8 bindings); none in `M10.mix`.
- `live_script_bindings`: 690 M10 bindings (600 persisted, 62 definition, 28 spawner),
  690 registered, 0 missing. `live_script_parameters`: 357 equal-count, 333
  "excess" that are all one `"0"`-style value against a zero-parameter descriptor
  (never read). No fewer-value binding. The four `M10_Gate_Check` instances carry
  `1005,1286010,1286011`, `1007,1286007,1286006`, `1006,1286008,0` and `0,0,1286009`.
- Runtime attaches (`Attach_Script` in source and in the seven cinematic `.txt` files)
  all resolve to registered scripts (`unknown_shipped_scripts: []`).

### Event and object closure

- 154 of 162 literal `Find_Object` call sites resolve to serialized level objects. Six ids are absent:
  1153934 (Airstrip power-off, :712; conversation zone 36/38 health gates),
  2010415/6000728 (`M10_Obelisk::Killed`, `M10_Obelisk_MCT::Poked`),
  2063322/2063323/2063324 (zone 39/42/47 health gates). All go through null-safe
  commands (`Get_Health`/`Set_Building_Power`/`Send_Custom_Event` use
  `SCRIPT_PTR_CHECK`); `Get_Health(NULL)==0` only suppresses zone conversations 36,
  38, 39 and 47 (secondary objectives), and zone 42 still fires through silo 1153935.
  Retail-identical.
- Level-parameter targets: `RMV_Trigger_Killed(1100177,100,100)` on the Power Plant
  targets a missing object (no-op). `M03_Zone_Enabled_Spawner` ids 2008181-2008186
  are soldiers, not spawners (`Spawner_Enable` no-op). Retail-identical.
- Custom/timer receivers checked: 1110009 carries both `M10_Apache_Controller` and
  `M10_Reinforcement_Controller`, so 1000-5000 (Apache) and 3000/10000/20000
  (reinforcement) all have handlers. Objective controller 1100154 handles 1000-1025
  params 1-4. Gate/fence static objects 1286006-1286011 (`BASEGATE10`, 31 frames) and
  1285077 (`L10_LASERFENCE1`, 2 frames) are `StaticAnimPhys` in `m10.lsd` with their
  anim in `M10.mix`, so `Static_Anim_Phys_Goto_Last_Frame`, which dereferences
  `Peek_Animation()` without a check (scriptcommands.cpp), has a non-null animation.
  Gate id 0 resolves to no static object. 2050007/2058171 (`M10_Gate_Test`,
  `M10_Spacecraft_Check`) are absent but both scripts are unbound.

### Content resolution

- Seven cinematic texts are in `always.dat`; all models, `Create_Real_Object` presets
  and audio resolve. Retail-identical misses: the ten `X10A_Apache_0x`/`X10A_Trnspt_0x`
  flyovers, and anim `v_GDI_trnspt.XG_HD_Transport` (`M10_GDI_Drop_HummVee.txt`,
  W-SAM secondary path) which is absent from every retail archive.
- Paradrop models/anims (`X5D_*`, `H_A_X5D_ParaT_*`, `vf_nod_chinook`) resolve in
  `always.dat`. POG textures resolve as `.dds` except `POG_M10_2_12`, used only by the
  dead `Remove_Pog` (its caller is commented out).
- 72 level conversations in `m10.ldd` cover every `M10CON*` the scripts create;
  `M03CON068` (`M10_Radar_Scramble`) is the only miss, as recorded above.

### Objective chain and the key-conversation question

The seven counted primaries are 1001, 1002, 1004, 1005, 1006, 1007 and 1012; nothing
sends a duplicate, so losing one makes `Mission_Complete(true)` unreachable.

- Gate routing correction: `first`/`second` are per-instance members. Only the 1005
  instance monitors M10CON002 and sets `first`, so the 1007 and 1006 instances always
  send their objective directly from `Poked` (:2721-2749). M10CON008 and M10CON017
  never play with retail data. Only 1005 depends on a conversation end.
- Conversation data (m10.ldd, `ConversationClass::VARID_ISKEY`): M10CON002, M10CON005,
  M10CON011 and M10CON014 are **not key** (stored priority 30; scripts pass 99,
  interruptable false). 23 M10 conversations are key: 001, 003, 004, 007, 010, 013,
  015, 019, 020, 024, 027, 030, 033, 035, 036, 039, 041, 042, 044, 047, 049, 051 and 064.
  These include the zone briefings for the same targets (004 Con Yard, 010 Comm
  Center, 015 Power Plant), the intro (064) and the beacon drop (019).
- Answer to the open question: yes, it is reachable. `ActiveConversationClass::
  Start_Conversation` (activeconversation.cpp:399) stops a non-key conversation with
  INTERRUPTED if any key conversation is in the active list. Priority and the
  interruptable flag are not consulted. The stop happens before the script's
  `Monitor_Conversation`, so `Notify_Monitors_On_End` has no observer, and the late
  `Register_Monitor` never fires. If a building dies (1001/1002/1004), or the SE
  console is poked with the key (1005), while a key conversation is playing, that
  primary is lost permanently (`already_poked` is already set; buildings die once).
  This is PC-retail behaviour. It was resolved later with the M10-only option; see
  [the fix section](#key-conversation-preemption-fix-2026-10-07). Pre-fix telemetry
  signature: monitor outcome 0 for action 100014/100005/100011/100002 with an earlier
  end record and no kind-3 observer call.
- Beacon: `POW_IonCannonBeacon_Player_Grant` (81950139) has `AlwaysAllowGrant=1`,
  `GrantWeaponID=0`; `Level_01_Keycard` (81950037) has `GrantKey=1`,
  `AlwaysAllowGrant=1`. Both always fire `CUSTOM_EVENT_POWERUP_GRANTED`, so full
  beacon ammo or an already-held key cannot block 1003/1012. `M10_Ion_Cannon` is
  attached at frame 146, one frame after the beacon is created at frame 145.

### Crash-prone code

- **Fixed** (`scripts-a36-m10-stealth-attack-loc-bounds.patch`):
  `M10_Stealth_Attack_01/02::Enemy_Seen` read `attack_loc[loc]` with `loc==100` (set in
  `Created`, :3037/:3170) until the first `GOTO_LOC` timer (1.0 s/0.25 s). Both scripts
  are reachable (stealth-tank drops from `DME_Cinematic_Zone` and
  `M10_Cargo_Plane_Dropoff`). The guard returns while `loc` is outside 0..12. That
  is behaviour-neutral: `Modify_Action` only applies to action 10, which exists only
  after `GOTO_LOC` sets a valid `loc`.
- Deferred, unreachable with retail data: `M10_Chinook_ParaDrop` `char params[10]`
  with `sprintf("%d", Get_ID(obj))` (:1720), which overflows for 10-digit dynamic ids
  (>=1500000000). The script is not bound or attached anywhere.
- Deferred, retail-identical: `M10_Flyover_Controller::Created` `last, last2, last3 = 100`
  (:3412) only sets `last3`; harmless because a random 0..7 is compared, not indexed.
  `M10_Apache_Controller::apache_id[0]` is never initialised (area 0 Apache commented
  out); `Find_Object(garbage)` returns NULL or an unrelated object, with no indexing.

### Save/load gaps not in SCRIPT_SAVE_STATE_GAPS.md (deferred, low)

`M10_Stealth_Attack_01/02::attack_loc[13]` and `_02::same`, plus
`M10_Mammoth_Attack::target[4]`, are not registered. After a load the arrays hold
indeterminate ids (`Find_Object` returns NULL, so tanks path toward the origin). None of
them is on the objective chain, and the bounds patch keeps `loc` indexing safe.

### Port patches touching M10

- `scripts-a35-apache-controller-bounds` (also M08): the bounds guards are correct.
  The type-5000 change from `Reload_At_Helipad(area)` to `(param)` is a deliberate
  semantic change: it reloads the requesting Apache instead of the active-area one,
  and avoids `apache_id[-1]` and timer 9. It is reviewed in SCRIPT_LAYER_SWEEP and
  differs from retail only when the player has changed area.
- `scripts-a36-m10-gate-check-save-flags`: correct. Ids 2/3 are unused, and old saves
  load.
- `scripts-a36-m10-stealth-attack-loc-bounds`: new, described above. The staging chain
  is re-run: 526 ordered patches, PASS, and only `Mission10.cpp` changes.
- `scripts-a38-m10-objective-conversation-resend`: see the next section.

Native M10 completion is still unproven. It needs the physical route above.

## Key-conversation preemption fix (2026-10-07)

Evidence class: staged source, host Python source contract, and one
`arm-vita-eabi-g++ -fsyntax-only` of the patched file. No build, link, VPK,
emulator or device. Line numbers are the staged `Mission10.cpp` after this fix.

Patch: `port/patches/scripts-a38-m10-objective-conversation-resend.patch`. It is
registered in `tools/stage_sources.sh` right after
`scripts-a36-m10-stealth-attack-loc-bounds`. Staging re-run: 544 ordered patches,
PASS, zero fuzz, and only `staging/scripts/Mission10.cpp` changes. Engine
conversation code is unchanged.

Design. At the four follow-up sites, `Monitor_Conversation(obj, id)` now runs
before `Start_Conversation`: Power Plant :746, Con Yard :799, Comm Center :957,
SE gate (1005 instance) :2770. Retail called it after.

- Preempted path: if a key conversation is active, `ActiveConversationClass::
  Start_Conversation` calls `Stop_Conversation(INTERRUPTED)`. That stop now finds
  the monitor, and `Notify_Monitors_On_End` calls the existing `Action_Complete`
  synchronously inside `Killed`/`Poked`. The M10 handlers never check the reason,
  so the objective is sent on the kill or poke. The follow-up line does not play,
  which matches retail, where the stopped conversation is also silent.
  No timer or retry is used, so nothing depends on gate-console hibernation and
  no pending state has to survive a save.
- Normal path (no key conversation): `Start_Conversation` and the scriptcommands
  wrapper never read or reset `MonitorArray`, and `Register_Monitor` never reads
  `State`. The conversation, its end and the objective timing are the same as
  retail. A key conversation that starts later still stops the follow-up from
  `ConversationMgrClass::Think` with ENDED, which notifies the monitor as before.
- Missing conversation (`Create_Conversation` returns -1, not reachable with
  retail `m10.ldd`): the script calls its own `Action_Complete` with
  `UNABLE_TO_INIT` (:750, :803, :961, :2774).
- Exactly once: each send is guarded by a flag that is set before the custom event
  is sent and is saved with `SAVE_VARIABLE` under an unused id. Power Plant
  `objective_sent` id 2 (:689), Con Yard id 1 (:771), Comm Center id 1 (:927),
  `M10_Gate_Check::objective_1005_sent` id 4 (:2708). `Stop_Conversation` already
  returns early on `Is_Finished`, so one conversation never notifies twice. The guard
  also covers any second `Killed`. The script factory value-initialises (`a37`), so
  saves made before this patch load the flag as false. Those saves cannot hold a
  conversation that has already delivered.
- Save/load: a save taken mid-conversation restores the monitor through
  `ReferencerClass` (CONVERSATION_COMPLETION.md §3), and the restored conversation
  delivers once at its end. The INTERRUPTED callbacks that `Release_Level` sends to
  the old world's scripts are the same as retail.
- Other observers on the monitored objects (`M00_BUILDING_EXPLODE_NO_DAMAGE_DAK`,
  `RMV_Trigger_Killed`, `M10_Con_Yard_Repair`, `M10_NBase_Damage_Modifier`,
  `M10_Mrls_Grant`, `M10_Pokeable_Item_OnePoke`, per the `m10.ldd` binding receipt)
  have no `Action_Complete`, so the earlier callback reaches no other code.
- Not changed: the M10CON008/M10CON017 gate sites (unreachable with retail data;
  only the 1005 instance sets `first`), the other 53 M10 Start→Monitor sites, and
  every other mission.

Evidence:
- `tools/test_m10_objective_conversation_resend.py`: 5 tests, OK with the upstream
  tree linked. They check the monitor-before-start order, the id<0 fallback, guard
  order and save ids, one sender per objective, the engine assumptions above, that
  upstream minus staged Start→Monitor sites is exactly 4 (57 vs 53), and the patch
  registration order.
- Related host tests (mission event routes, script warning routes, campaign script
  closure, mission conversations/completion/diagnostics, conversation transition
  telemetry, cinematic, script portability and the sweep tests) pass. The only
  failures, in `test_cinematic_filename_diagnostics`, are two existing
  `Test_Cinematic.cpp` hash pins; that file is untouched here.
- `arm-vita-eabi-g++ -fsyntax-only` (compdb flags plus the frame-profile, LAN and
  MSAA defines): exit 0. Warnings are the same before and after: 18
  `-Wwrite-strings` and 7 `-Wattributes`.

Telemetry change: for these four sites, the monitor-registration record
(`monitor_inserted`) now comes before `Set_Action_ID`, so its `action_id` is 0.
Correlate by conversation id and instance token. The end and kind-3 records still
carry 100014/100005/100011/100002. Physical signature of the preempted path: the
kill or poke, then `monitor_inserted` (action 0), then `transition end` with reason
INTERRUPTED and a kind-3 call carrying the action id, all in the same frame, then
the objective.

Residual risks:
- On the preempted path the objective completes at once and the follow-up line
  (for example "Power Plant destroyed") never plays. Retail lost the line too. A
  replay after the key conversation would need a timer on a console object that can
  hibernate, so it was not done.
- The objective custom now arrives inside `Killed`/`Poked`, earlier than in the
  normal path. If it is the seventh primary, `M10CON019` and the GDI drop cinematic
  start from inside that callback. The Killed/Poked code that runs after it only
  sends events and sets power and fences, so the order is harmless by source.
- The physical behaviour is unproven. The route step 3 variant above exercises it.
