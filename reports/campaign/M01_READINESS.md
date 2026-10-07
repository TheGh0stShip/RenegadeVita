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
