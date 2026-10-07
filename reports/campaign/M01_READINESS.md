# M01 readiness (source/data evidence only)

Evidence class: static source and retail-metadata audit plus deterministic
staging. No build, no Vita3K, no physical run. This report does not claim that
M01 completes on hardware. Line numbers refer to `staging/scripts/Mission01.cpp`
after this change.

## Completion chain (primary objectives)

Controller: `M01_Mission_Controller_JDG` (object 100376), declared at :45.
Primary state starts false (`player_has_unlocked_pen` :288,
`commcenter_sam_objective_active` :291, `prisoners_are_freed` :292,
`commcenter_sam_destroyed` :320).

1. Prisoner objective added by `M01_Objective_Pog_Controller_JDG` :11570.
   It is marked accomplished when announced (:1496), which adds the
   unlock-gate objective (:1398).
2. Unlock the pen through either of two routes:
   - Poke the Comm Center PCT. Its Poked handler (:11515) sends
     `M01_PLAYER_HAS_POKED_COMM_CENTER_PCT_JDG` (:1295). That plays an EVA
     chain driven by `CUSTOM_EVENT_SOUND_ENDED` (:366-396). Its last line
     sets `player_has_unlocked_pen` and sends `M01_CLEAR_UNLOCK_GATE_OBJECTIVE_JDG`.
   - Destroy the Comm Center (:522-541).
   `M01_CLEAR_UNLOCK_GATE_OBJECTIVE_JDG` (:1414) announces the SAM objective
   if the SAM is alive (:1425-1427 -> :1358, which sets
   `commcenter_sam_objective_active` :1366 and adds the objective at :1375).
3. Poke the pen gate. The gate script's Poked handler (:15662) sends
   `M01_PLAYER_HAS_POKED_PEN_GATE_JDG` (:1308). That opens the gate, marks
   `M01_OPEN_THE_GATE_JDG` accomplished (:1329), sets `prisoners_are_freed`
   (:1348-1351) and sends `M01_CLEAR_PRISONERS_PASS_JDG` (:1500).
4. Destroy the Comm Center SAM. The SAM's Killed handler (:15699) sends
   `M01_COMMCENTER_SAMSITE_HAS_BEEN_DESTROYED_JDG` (:772). If the objective
   is active, this leads to `M01_PASS_COMM_SAM_OBJECTIVE_JDG` (:1444), which
   clears the active flag. If the prisoners are already free, it also
   schedules `M01_DO_END_MISSION_CHECK_JDG` after **60 s** (:1449-1451,
   original authored delay).
5. `M01_DO_END_MISSION_CHECK_JDG` (:1506) requires `!commcenter_sam_objective_active
   && prisoners_are_freed`. It runs one-shot (`final_conv_played`): weather
   reset, detention actors removed, player moved, then `Invisible_Object` +
   `Test_Cinematic` `X1Z_Finale.txt` (:1574-1575), and `M01_END_MISSION_PASS_JDG`
   is scheduled after 20 s (:1577).
6. Success is reached by two original routes:
   - `M01_END_MISSION_PASS_JDG` -> `Commands->Mission_Complete(true)` (:1591).
   - `X1Z_Finale.txt` `Send_Custom 100376,0,0` at frame 618 (about 20.6 s)
     -> type0/param0 -> `Mission_Complete(true)` (:405).
   `CombatGameMiscHandlerClass::Mission_Complete` only latches
   `PendingCampaignContinue=true` (`staging/commando/combatgmode.cpp:1716`),
   so the duplicate call is idempotent.

The secondary objectives (HON, church, turrets, barn, GDI base POW/commander)
do not gate success.

## Audit results (retail Vita3K copy, read-only)

| Check | Result |
| --- | --- |
| Script names bound by M01 level data plus closure (`tools.audit_mission_content_bindings`) | 528 level bindings, 573 total, 275 scripts; **0 unknown**. Owners are Mission01/03/11, Test_Cinematic, Test_DAK/DAY/RMV_Toolkit, Toolkit, Toolkit_Objects/Powerup. All of them are in the Scripts.dsp list that CMake links (`CMakeLists.txt` `RENEGADE_SCRIPT_DSP_SOURCES`), and lookup goes through the original `ScriptRegistrar` (`port/platform/renegade_script_static_provider.cpp`). |
| Literal presets created by scripts | 0 missing |
| Cinematic `.txt` named in Mission01.cpp (157 incl. the 18 M01.mix members) | All resolve except `X01_ConYardDrop.txt` (:18007) |
| Cinematic models (81) / animations (133) | Missing: `C_havoc` (`xg_ev5.txt` frame 600) and `v_GDI_trnspt.XG_HD_Transport` (`x1i_gdi_drop_mediumtank.txt`) |
| Cinematic `Create_Real_Object` presets (29) | All resolve in objects.ddb plus the M01 overlay |
| `kM01ScriptSpawnPresets` (`port/platform/vita/a31_vita_runtime.cpp:3333`) | All 17 resolve |
| M01 preparation block models (`a31_vita_runtime.cpp:5278-5334`, 32 entries) | All 32 `.w3d` files present |
| Conversations (`tools.audit_mission_conversations`) | 89 level conversations, 0 invalid orators. One unlocated literal, `M01_TurretBeach_TurnOverTank_Conversation` (:8069), is in a script outside the discovered closure. |
| Script save variables (115 scripts) | **2 duplicate-ID defects** (fixed below) |

The missing items are non-blocking:
- `X01_ConYardDrop.txt`: `Test_Cinematic::Load_Control_File` returns when
  `Text_File_Open` fails, so `Controls==NULL` and the controller destroys
  itself (`staging/scripts/Test_Cinematic.cpp:213-216, 1076-1078`). This
  matches retail PC behavior.
- `xg_ev5.txt`/`C_havoc`: no Mission01 source or level binding launches
  `xg_ev5.txt`. Mission01 drives the EV5 models directly (:11873-11944).
- `X1I_GDI_Drop_MediumTank.txt` is only referenced from a commented-out line (:1804).
- 14 weapon eject/muzzle-flash phys definition IDs are not located in the
  retail database. This is also true on retail PC; they are not on the
  completion path.

## Blockers found / fixed

Fixed: original save-ID collisions that leave script members uninitialized
after load.
`ScriptImpClass::Auto_Save_Variable` drops a duplicate ID
(`staging/scripts/scripts.cpp:681-686`). Loaded script objects never run
`Created`, so these members held indeterminate memory after any save/load:
- `M01_TailgunRun_NOD_Commander_JDG::playerSeen` (ID 2, shared with
  `firstTimeDamaged`). Now ID 3.
- `M01_Church_Priest_JDG::prayerSound` (ID 1, shared with `lucky_charms`). Now
  ID 2. A garbage sound ID was then passed to `Start_Sound`/`Stop_Sound`.

The fix is `port/patches/scripts-a36-m01-save-variable-ids.patch`, registered
in `tools/stage_sources.sh` after the Duncan beacon patch and anchored to
SHA-256 `9c28882b…cb901`. Staging regenerated with 507 ordered patches at
fuzz 0 (inventory `3e26cc91…ff1e0f`). Only `Mission01.cpp` and the inventory
changed. Saves made before this change still lack the new IDs, so those two
members stay indeterminate on old saves. New saves round-trip.

No blocking missing script, preset, model, animation or conversation was found
on the primary path.

## Residual risks (open, need runtime evidence)

1. M01 intro/beach freeze. KNOWN_GAPS/PORT_STATUS report a native freeze
   during the M01 intro aircraft sequence (issue #1 PSTV; "M01 beach freeze").
   It is still unresolved, and source audit cannot close it.
   Retained-log boundary (read-only, 2026-10-07): the Dev197 PSTV log
   (`build/device-evidence/a35-dev197-pstv-20260927/a35-dev197-m01-freeze-runtime.log`)
   and the Dev197 Vita3K log
   (`local-builder/logs/dev197-m01-guest-debug-20260926/runtime-before.log`)
   both end on an `X1C_Intro.txt` yield with `pending_time=1.067` (current
   1.194 and 1.167). Dev192 also ended after the `X1C_AG_Missile` instance was
   consumed. Frame 32 (1.067 s) of retail `X1C_Intro.txt` creates slot 5
   `X1C_AG_Missile`, plays `X1C_missile.X1C_missile`, then runs
   `Play_Audio "SFX.Missile_Launch_2second",5,"XO_missile11"`. That reaches
   `Command_Play_Audio` -> `Create_3D_Sound_At_Bone`
   (`staging/combat/scriptcommands.cpp:980`), and the preset resolves to
   `missile_launch_2s1.wav` (8-bit PCM, valid header). The next authored X1C
   records are at 2.667 s, and a slow-frame record is written only after a
   frame returns. The logs therefore cannot say whether the stall is in that
   command, in the missile's animation or render, or elsewhere in the frames
   that follow. No fix is claimed.
   Next-run breadcrumbs: `A4 M01 cinematic command begin/end` (first 160 `X1*`
   commands, `port/patches/scripts-a36-m01-intro-command-breadcrumbs.patch`)
   and `A4 M01 intro phase: frame=N phase=simulation-begin|render-begin|audio-begin|audio-end`
   (first 120 M01 frames, with one log sync per frame). A trailing `begin`
   with no `end` names the command. Otherwise the last phase line names the
   stalled frame stage.
2. Finale preparation (static audit of `X1Z_Finale.txt`, retail Vita3K copy,
   read-only). The generic `Prepare_Original_Level_Loading_Resources` path
   (`Warm_Level_Cinematic_Preset_Models`) now covers the finale:
   - All 8 `Create_Real_Object` presets (`GDI_Transport_Helicopter_Flyover`,
     `Civ_Female_v0a`, `Civ_Male_v1a/v2a`, `GDI_Prisoner_v0a/v1a/v2a`,
     `GDI_MiniGunner_3Boss`) are soldier (factory `0x4010f`) or vehicle
     (`0x40129`) definitions, so they are warmed with their weapon models
     (`v_gdi_trnspt`, `c_ag_civ4`, `c_ag_civ1_male`, `c_ag_civ2_male`,
     `c_ag_gdi_pr/pr1/pr2`, `c_ag_havoc`).
   - All 18 distinct `Play_Animation` names parse (host re-implementation of
     `Parse_Cinematic_Play_Animation_Name`) and map to existing files
     (`X1Z_CAMERA`, `X1Z_Traject_01..04`, `x1z_trnspt`, ten `H_A_X1Z_*`, one
     `H_B_X1Z_CivF01`, `v_gdi_trnspt`). `Get_HAnim` -> `Load_3D_Assets` also
     registers the HLOD prototypes in `X1Z_CAMERA.w3d` and
     `X1Z_Traject_01..04.w3d`, so those `Create_Object` models are prepared
     as a side effect.
   - Remaining `Create_Object` model `o_crate_sm` (slot 20, ROOTTRANSFORM host,
     4 KB in `always.dat`, used only by the finale) is now in the M01 warm list.
   Still unprepared: finale sounds (`Play_audio` presets, two unlocated, and
   `01_A`). Preparation stops at the 24 MB vitaGL free-memory floor, which skips
   the animation pass; check `A4 cinematic animation preparation: archive=M01.mix`
   for `memory_floor=0` and `loaded=` equal to `named=` on hardware.
3. Two finale `Play_audio` presets (`M00NSMG_KILL0053I1GBMG_SND`,
   `M03DSGN_DSGN0039RIGBMG_SND`) are unlocated (cosmetic). Eleven oversized
   M01 WAV RIFF headers also still need decoder validation.
4. Ordering of the two success routes, and teardown while the X1Z cinematic is
   still alive (the 20 s timer fires before frame 618), need a runtime trace.
5. Score screen, `campaign.ini` continuation to M02, and saves taken
   mid-cinematic remain unverified. Duplicate preset names (`NOD_Apache`,
   `Nod_Cargo_Plane`) resolve to the first definition, as in the original.
6. The SAM-path end check waits 60 s after the SAM dies if the prisoners were
   freed first (authored). Testers should not mistake that for a hang.

## Physical test route

Use the candidate built from this commit with the full-port (campaign) profile.
1. Start New Campaign (or M01 direct entry). Confirm that the X1C intro
   reaches control without freezing. Capture the log breadcrumbs
   `A4 M01 retained preparation` and `A4 slow campaign cinematic command`.
2. Follow the beach -> GDI base -> Comm Center route. Destroy the Comm Center
   SAM site first; it is the fastest deterministic order.
3. Enter the Comm Center and poke the PCT (Triangle = `INPUT_FUNCTION_ACTION`).
   Wait for EVA "data acquisition complete" (the unlock objective clears).
4. Poke the detention pen gate (Triangle). The gate opens and the prisoners
   objective completes. Expected: within about 1 s the finale fades in
   (`X1Z_Finale`), and mission success fires at about 20 s.
5. Alternate order: free the prisoners before killing the SAM. After the SAM
   dies, expect a deliberate wait of about 60 s before the finale.
6. Save/load check: quicksave near the church and the tailgun commander
   before step 2, reload, and confirm no audio/AI anomaly.
7. Confirm the score screen appears, then continuation to M02 loads. Collect
   `ux0:data/renegade/user/logs/*` and any psp2dmp.

## Full audit (2026-10-07)

Evidence class: static source, retail-metadata (Vita3K retail copy, read-only)
and `arm-vita-eabi-g++ -fsyntax-only` of the patched `Mission01.cpp` (rc 0). No
build, no Vita3K, no hardware. Receipts are in the ignored
`build/m01-full-audit/`. Line numbers below are `staging/scripts/Mission01.cpp`
after this change unless they say otherwise.

| Check | Result |
| --- | --- |
| Level/preset script bindings (`audit_mission_content_bindings`) | 573/573 registered; 0 unknown; 0 bindings with fewer values than the descriptor (538 "excess" are a single `0`/empty value on a 0-parameter script) |
| Literal `Attach_Script` calls in Mission01 | 95; 86 literal, all registered with equal counts; 9 use `flyovers[random]`, all indices in bounds (`Get_Random_Int(0,N)` is `[0,N)`) |
| Cinematic `Attach_Script` (all M01-referenced `.txt`) | 33 distinct names, all registered; extra `FUSELAGE` value only on 0-parameter scripts |
| `Start_Timer` ids | every id is handled by the owning script's `Timer_Expired` |
| `Send_Custom_Event` receivers | 6 sends with no receiver anywhere (`M00_CUSTOM_SAM_SITE_IGNORE` to the HON SAM, `M01_GDI_BASE_POWS_OVER_JDG`, `M01_HON_CUE_WARROOM_LEVEL_ACTORS_JDG`, `M01_MODIFY_YOUR_ACTION_07/10_JDG`, `M01_YOUR_OPERATOR_IS_DEAD_JDG`); original no-ops, none on the primary chain |
| Cinematic `Send_Custom` | one: `X1Z_Finale.txt` frame 618 -> 100376 type 0 param 0 -> `Mission_Complete(true)` (:440) |
| Hard-coded `Find_Object` ids absent from level data | 18 ids (34 sites). Every site reaches only NULL-safe `Commands` (`SCRIPT_PTR_CHECK`), e.g. `Get_Position(NULL)` returns the origin (:8223, :8271 evac spots). Retail-identical |
| Missing cinematic `.txt` | `X01_ConYardDrop.txt` (:18058, known); `XG_M01_Detention_EvacAnim.txt` and `XG_M01_HumveeDrop.txt` only in commented-out lines |
| Literal presets/sounds/anims/models (151 presets, 89 anims, 4 models) plus string arrays | unresolved in every retail archive: `M01_Nod_HupHup` (:5503, `Create_3D_Sound_At_Bone` returns 0), `H_A_442A` (:3820) and `H_A_V11A` (:3916, :4095) looping `Action_Play_Animation` (NULL anim handled in `AnimChannelClass::Set_Animation`), `01-I048E` in the Comm Center ambient table (`Create_Sound` returns 0). All retail-identical, cosmetic |
| Objective chain | unchanged from the chain above; both `Mission_Complete(true)` routes (:440, :1626) intact; `endMission_conv` route (:2525) is unreachable (never assigned) |
| Port patches touching M01 | Duncan beacon handoff (adds a 3.5 s fallback that calls the same original beacon/conversation code once; `gaveIonBeacon` guards a double grant), save-variable IDs, cinematic original dispatch (budget yield removed; `Parse_Commands` matches upstream), command timing and the intro breadcrumbs (log only). No defect found |

### Defects fixed

1. **Save/load: unregistered constant tables (crash risk).** Both of these are
   filled only in `Created()`. A loaded script never re-runs `Created()`, so
   after any M01 load they hold indeterminate heap data:
   - `M01_GDI_Base_Artillery_Controller_JDG::locs[35]` (102294): the next
     `M01_PICK_A_NEW_LOCATION_JDG` places the bomb sound and then
     `Create_Explosion("Ground Explosions Twiddler", ...)` at a garbage
     position.
   - `M01_PrisonPen_Civilian_JDG::wanderSpot[10]` (detention-pen prisoners
     101929-101931, primary objective actors): `Timer_Expired` issues
     `Action_Goto` to a garbage position.
   Fix: `port/patches/scripts-a36-m01-load-position-tables.patch` moves each
   table into an `Init_*` helper that `Created()` calls. The helper is also
   called right before the table is indexed. The values are the same
   constants, so first-load behavior is unchanged.
2. **Indeterminate controller IDs.** `M01_Mission_Controller_JDG::Created`
   left 31 conversation, sound and object IDs unset. Several are compared in
   `Action_Complete`/`Custom` before they are assigned, and seven are never
   assigned (`endMission_conv` gates a `Mission_Complete(true)` branch). A
   stale value that equals a live conversation ID (IDs restart at 1000 each
   level) would take the wrong branch. Fix:
   `port/patches/scripts-a36-m01-controller-id-init.patch` sets them to 0,
   which no conversation (>= 1000) or sound (>= 1000000000) uses. Saves still
   restore them, because all of them are registered.

Both patches are registered after the intro-breadcrumb patch in
`tools/stage_sources.sh`, anchored to the previous final `Mission01.cpp`
(`3e873be0...0dba1`). No earlier anchor moved. Staging was regenerated at
fuzz 0: 527 ordered patches, inventory `982ace83...ab7b`. Only `Mission01.cpp`
changed (new SHA-256 `21e55a66...faea`).

### Deferred (not fixed)

- `Has_Key` (`staging/combat/scriptcommands.cpp:2406`) dereferences `object`
  without a NULL check. M01 calls `Has_Key(STAR, n)` at :1095-1097 (a card
  carrier dies) and :5974 (`M01_Comm_Base_Commander_JDG::Killed` with
  `killer == STAR`, which is also true when both are NULL). `STAR` is NULL
  once a dead player's corpse is deleted (`soldier.cpp:2630-2637`). This is
  a retail-identical latent crash. A one-line `SCRIPT_PTR_CHECK_RET(object,
  false)`, matching `Grant_Key`, is the suggested fix. It was left out of this
  M01-scoped change because it touches the shared combat command table.
- `Create_3D_Sound_At_Bone`/`Create_3D_WAV_Sound_At_Bone` do not NULL-check
  `obj` or `Peek_Model()`. Every M01 caller passes a live object (the
  `Test_Cinematic` `Play_Audio` path checks the slot object first). The
  attached sound holds a reference to the model (`REF_PTR_SET`), so the
  X1C missile sound cannot outlive its model. No intro-freeze cause was
  found on this path.
- `M01_TurretBeach_Engineer_JDG::last_health` and
  `M01_MediumTank_ReminderZone_JDG::reminderConv` are still unregistered
  (cosmetic AI/reminder state).
- Runtime evidence is still needed for everything listed under the residual
  risks above. After a mid-mission load, run the save/load test-route step
  near the GDI base artillery and the detention pen.

## Soft-lock hunt (2026-10-07)

Evidence class: static source review, retail metadata (Vita3K retail copy, read-only:
`m01.ldd` conversation key flags, `always.dat` EVA wave headers, the existing
`s4-all-map-bindings/m01-bindings.json`), deterministic staging (rc 0, fuzz 0,
545 ordered patches) and `arm-vita-eabi-g++ -fsyntax-only` of the patched
`Mission01.cpp` (rc 0, no new warnings). No build, no Vita3K, no hardware. Line
numbers are `staging/scripts/Mission01.cpp` after this change.

Success needs only `prisoners_are_freed && !commcenter_sam_objective_active`
(:1610). No objective status, counter or secondary gates it.

### Fixed

1. **PCT unlock lost after save/load (or a stuck EVA line). Reachable, high.**
   The PCT poke is one-shot (`poked`, :11620). The unlock is driven only by
   five chained `CUSTOM_EVENT_SOUND_ENDED` events (:431-459). Those lines are
   IMA ADPCM `00-n000e/002e/026e/028e/030e.wav` in `always.dat`, about 8.2 s
   in total. Dynamic sounds are not saved (`SoundSceneClass::Save_Dynamic`
   writes nothing), and `Update_Play_Position` never ends a sound whose
   `m_Length` is 0. So a save taken during the chain and then loaded, or a line
   that fails to decode, leaves `player_has_unlocked_pen` false for good. The
   only way out is to destroy the Comm Center, which the game never suggests.
   This is retail-identical, but it is a real soft-lock.
   Fix: `port/patches/scripts-a38-m01-pct-unlock-watchdog.patch`. The poke also
   arms a 30 s controller custom (:1373; custom timers are saved). When it
   fires (:1391) with the pen still locked, it zeroes the five line IDs so a
   late line cannot repeat the unlock, then runs the exact
   line-5 action (`M01_CLEAR_UNLOCK_GATE_OBJECTIVE_JDG` and
   `player_has_unlocked_pen = true`). On the normal path the chain finishes
   first and the watchdog does nothing. Log: `A4 M01 PCT unlock watchdog`.
2. **"Open the gate" objective never added. Reachable, medium (guidance, not a
   hard blocker).** `M01_Remove_Unlock_Gate_Objective` is **not key** in
   `m01.ldd`. The key conversations that can be playing at that moment include
   `Kane_and_Havoc`, `Kane_and_Number02_01` (both in the Comm Center where the
   PCT is), `Add_Unlock_Gate_Objective` and `Radar_Scrambled`. If one of them
   is playing, `ActiveConversationClass::Start_Conversation` stops the new
   conversation with INTERRUPTED before `Monitor_Conversation` runs. M01's
   `Action_Complete` is also limited to `ACTION_COMPLETE_CONVERSATION_ENDED`.
   As a result `M01_OPEN_THE_GATE_JDG`, its radar blip and its POG are never
   added. A typical trigger is killing the SAM first, then poking the PCT during
   the Kane hologram talk. The gate still works, but no primary objective points
   at it. Fix: `port/patches/scripts-a38-m01-open-gate-objective-fallback.patch`.
   The original objective block moves into `A38_Add_Open_Gate_Objective` (:276),
   which adds it at most once and records `open_gate_objective_added` (new
   save ID 90). Both start sites (:853, :1526) arm a 30 s fallback (:1381). The
   fallback adds the objective only if the callback has not and the gate is
   still closed. The conversation has 2 remarks, so on the normal path the
   callback adds the objective first. Log: `A4 M01 open-gate objective fallback`.

Both patches are registered after `scripts-a36-m01-controller-id-init.patch`.
The existing `3e873be0…dba1` anchor is unchanged. Staging was regenerated and
only `Mission01.cpp` (SHA-256 `c05156b1…fff5`) and `PATCH_INVENTORY.json`
changed. Saves made before this change carry no watchdog or fallback timer, so
an old save already stuck in the EVA chain stays stuck.

### Checked, not reachable or retail-identical (no change)

- `endMission_conv` (:2588 branch) is never assigned. With the controller-ID
  init it stays 0, so the branch is dead and `Mission_Complete(true)` comes only from
  :468 (X1Z frame 618) or :1695 (`END_MISSION_PASS`).
- SAM-pass 60 s branch (:1548): the pen gate accepts a poke only after
  `samDead` (:15774), which is set 5 s after the SAM's `Killed` (:15791). The
  synchronous SAM pass therefore always runs before the prisoners can be freed,
  and the 60 s delay is unreachable. This corrects residual risk 6 and test
  route step 5 above: the prisoners cannot be freed before the SAM dies.
- Gate poke re-announcing the SAM objective after the SAM is dead
  (`Find_Object(M01_COMMCENTER_SAM_JDG)` at the gate): `PhysicalGameObj::
  Completely_Damaged` sets the SAM delete-pending, and the 5 s `samDead` delay
  covers it. Not reachable.
- Completion before activation: the SAM dying before its objective
  (`commcenter_sam_destroyed`), and the Comm Center dying before or during the
  PCT chain, are both latched by the original code. The SAM `Killed` receivers
  (controller 100376, pen gate 101117) are persisted level objects.
- Counters (prisoners, HON, church, barn, turrets): none gates success.
  Undercounts only affect secondaries. They were not exhaustively traced in
  this timebox.
- Lost actors: no NPC, vehicle or item is on the primary chain. The detention
  prisoners can die without blocking the gate, and the finale destroys any
  survivors (:1610 onward).
- Save/load: delayed customs (`samDead` 5 s, finale 20 s, the new 30 s timers)
  are saved by `ScriptableGameObj` `CHUNKID_CUSTOM_TIMER`, and conversation
  monitors are relinked. A save made mid-finale still reaches
  `Mission_Complete` through the saved 20 s timer.
- Comm Center destroyed during the PCT chain: `CLEAR_UNLOCK_GATE` runs twice
  (duplicate SAM announcement or objective), as in retail and cosmetic. The
  watchdog adds no third run.
- Still deferred: `Has_Key(NULL)` (see Full audit).

Physical check: poke the PCT, quicksave within about 5 s, load, and wait. The
unlock should arrive about 30 s after the poke, with the watchdog log line.
Then kill the SAM first and poke the PCT during the Kane talk. The "Open the
gate" objective should appear within 30 s.
