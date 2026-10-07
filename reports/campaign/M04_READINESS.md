# M04 (cargo ship) readiness — 2026-10-07

Evidence class: source and read-only retail-data inspection only. Nothing was
built, launched in Vita3K or run on a Vita. No physical M04 result exists, so
this report does not claim that M04 is completable on hardware. It records
which source and data paths can complete the mission, and which risks remain.

Inputs: `staging/scripts/Mission04.cpp` (10,518 lines). It differs from upstream
`Code/Scripts/Mission04.cpp` by one line, from
`port/patches/scripts-a36-m04-save-variable-ids.patch` (see "Full audit"
below). Retail data:
Vita3K `ux0:data/renegade/retail/Data` (M04.mix
`1d084c90…30ffa`, plus always.dbs `objects.ddb` and the `always*` archives).

## Objective chain to `Mission_Complete(true)`

Owner: `M04_Objective_Controller_JDG` (object 100424,
`staging/scripts/Mission04.cpp:44`).

| Step | Source |
|---|---|
| `Created` queues `announce_prisoner_objective` (400) after 3 s | `Mission04.cpp:211` |
| Announce: `prisoner_primary_active = true`, `mission_started = true` | `:397`, `:401` |
| Primaries added: 100 prisoners (`:225`), 300 missiles (`:239`), 110 key (`:320`), 600 first mate (`:343`), 800 (`:357`), 400 torpedoes (`:477`), 700 captain (`:523`); secondaries 200 engines (`:280`) and 500 Apache (`:493`) | — |
| Primary flags set when announced: missiles `:464`, torpedoes `:475`, first mate `:501`, captain `:521` | — |
| Sabotage counters: missiles 4/4 then `completed_missile_room_objective` (`:752`–`:866`), engines 4/4 (`:898`–`:976`), torpedoes 2/2 (`:994`, `:1012`) | — |
| Completion handlers clear each flag and call `Set_Objective_Status`: 100 `:564`, 110 `:580`, 200 `:598`, 300 `:613`, 400 `:627`, 500 `:640`, 600 `:648`, 700 `:675` | — |
| First mate killed, captain already gone: the handler takes the captain completion path directly | `:661` |
| `M01_DO_END_MISSION_CHECK_JDG` requires `mission_started` and all five primary flags to be false | `:713`–`:718` |
| `M01_END_MISSION_PASS_JDG` calls `Mission_Complete(true)` | `:707`–`:710` |
| Sender: `M04_Firefight_RallyZone` (object 101194, `:9395`). The player and prisoners 1–3 must all be at the rally point; it then sends `DO_END_MISSION_CHECK` | `:9501` |
| Prisoner IDs reach the zone from `M04_Firefight_Controller_JDG` (100948) as custom event types 1–3 | `:9290`–`:9296` |
| The only failure path is `Mission_Complete(false)` | `:9157` |

The rally zone's `Created` pre-marks prisoners at the rally point by
difficulty. On Easy all three are pre-marked. On Normal and Hard only prisoners
1 and 2 are, so prisoner 3 must physically enter zone 101194. The rally zone's
`Exited` handler looks up `prisoner01_ID` for all three prisoners. That bug is
in the upstream source and retail has it too. It only means an exit by
prisoner 2 or 3 never clears their flag, which cannot block completion.
Kept unchanged.

## Level-data and script name resolution (verified on retail data)

| Check | Result |
|---|---|
| Level-data script bindings in M04 (`reports/generated/sweeps/live_script_bindings.json`) | 322 in total: 25 definition, 295 persisted, 2 spawner. 322 are registered and 0 are missing. |
| Mission04 scripts in the latest packaged map (`RenegadeVita-A3.5-dev238.map`) | Linked, for example `M04_Objective_Controller_JDG` and `M04_Firefight_RallyZone`. The static provider draws its scripts from the original `Scripts.dsp`. |
| `Create_Object` preset names in Mission04 | 29 of 29 resolve |
| `Create_Conversation` names | 26 of 26 resolve in `conv10.cdb` plus the 29 M04 level conversations |
| `Create_Sound` names | 32 checked. 30 resolve to a definition with a present wave. 2 do not (see below). |
| `Create_2D_Sound` names | 3 of 3 resolve |
| Hard-coded `Find_Object`/`Trigger_Spawner` IDs | 119 checked. 8 are absent from the m04.ldd and m04.lsd bytes. |
| `M04_ForeDeck_Reinforcement_03_JDG`, attached at `:5352` | No script by this name exists in the released source, so retail fails the same way. `Attach_Script` logs "Unable to create script" and continues (`staging/combat/scriptcommands.cpp:557`–`:571`). |

The 8 absent IDs are 100455 (look target at `:5328`) and 101127/128/130/132/
133/134/136 (sub-bay battle-music zones at `:7598`–`:7608`). Each one reaches
only `Get_Position` or `Send_Custom_Event`, and both of those `SCRIPT_PTR_CHECK`
a NULL object and return safely (`scriptcommands.cpp:315`, `:659`). The level
data also shows zones 101131 and 101135, the two the source marks as "stays".
Retail behaves the same way.

The two missing waves are `SFX.Steam_Med_Pressure_01_offset1` and
`Steam_Med_Pressure_01` (engine-room ambience, `:2224`, `:2232`). Both point to
`always\sound\misc ambient\steam\steam_med_pressure_01.wav`, which no retail
archive or loose file contains. The original WWAudio guards a NULL
`m_Buffer`, so these two emitters stay silent on PC as well. No replacement
was added.

## Level-data audio path

- **Static level sounds.** `m04.lsd` contains one `CHUNKID_STATIC_SAVELOAD`
  (0x30005) static scene with 51 sounds: 43 `Sound3DClass` (0x30003) and 8
  `SoundPseudo3DClass` (0x30004). All 51 loop infinitely and have type 1.
  Drop-off radii run from 10 to 70 m. Their 22 distinct wave files all
  resolve in the retail archives. The load path is
  `StaticAudioSaveLoadClass::Load` → `SoundSceneClass::Load_Static` →
  `Find_Persist_Factory` → `AudibleSoundClass::Load`, which calls
  `Get_Sound_Buffer(filename)`. `SoundPseudo3D.cpp` and `Sound3D.cpp` are
  compiled directly into the executable, not into a static archive (see
  `cmake/A31OriginalSources.cmake:175`). Their persist factories appear in the
  dev238 map, so the linker cannot drop them. `VARID_THIS_PTR` reads 4 bytes,
  which matches the ARM32 pointer width.
- **Dynamic level audio.** `m04.ldd` contains one 0x30006 dynamic-audio
  chunk, handled by the existing transactional `DynamicAudioSaveLoadClass`.
- **Parameter-driven zone sounds.** There are 6 `M00_Play_Sound` bindings,
  such as `SFX.Ship_Catwalk_Footsteps,1,,,-1,10.00`. All resolve to sound
  definitions with present waves. `ScriptImpClass::Set_Parameters_String`
  keeps empty fields in position because it does not use `strtok`
  (`staging/scripts/scripts.cpp:237`), and an empty vector3 parses as zero
  (`:505`). There are also 14 `M00_Play_Sound_Object_Bone_DAY` bindings on
  four twiddlers. Three of the twiddlers resolve. `SFX.Nod_Visceroid_Twiddler`
  is empty in retail data, and `TwiddlerClass::Twiddle` returns NULL for an
  empty list (`staging/wwsaveload/twiddler.cpp:110`), so it is silent and safe.
- **Script ambience swap.** `M04_EngineRoom_BuildingController_JDG` creates
  14 looping emitters through `Create_Sound` → `Create_Instant_Sound`
  (`:2221`–`:2234`). When the engines are destroyed it stops them with
  `Stop_Sound(id, true)` and starts 10 broken-engine and klaxon loops plus a 2D
  stop sound (`:2247`–`:2277`). Lookup by ID goes through the original
  `SoundSceneObjClass` global list. Because these are infinite loops created
  as "instant" sounds, each one triggers an original `WWDEBUG_SAY`. That is
  log noise only.
- **Vita provider.** Sample handles in
  `port/audio/vita/renegade_miles_provider.cpp:954` are allocated on demand.
  Only sounds the original `SoundSceneClass` leaves unculled get a Miles
  handle, and the original WWAudio caps 2D and 3D handles.

## Blockers found and fixed

None. No change in this work unit was needed in the source or the patch set.
Every completion-critical name, ID and audio route either resolves or fails
the same way it does on the retail PC build.

## Remaining risks (unverified)

1. Prisoner escort. The Normal and Hard completion needs prisoner 3's
   pathfinding to reach rally zone 101194 (`:9072`). This depends on the
   original pathfinding and frame pacing on Vita, and has not been observed.
2. Voice budget in the engine room. Up to 51 static loops, 14 script loops and
   combat sounds compete for handles. Original culling should hold the count
   down, but the mixer's CPU cost and voice stealing on hardware are
   unmeasured.
3. The mission ends with `Mission_Complete(true)`, followed by the campaign
   transition to M05 and the save path. Neither has been observed for M04
   (`reports/DEV136_CAMPAIGN_SAVE_AND_FLOW.md` lists M04 as Open).
4. `x4a_midtro.txt` cinematic, Apache and hangar floors. Cinematic preset
   counts are recorded (`reports/CINEMATIC_PRESET_COUNTS.md`: 1 preset), but
   playback has not been observed.
5. Memory high-water for M04 on PSTV and Vita. The extended-budget question
   in `KNOWN_GAPS.md` is still open.

## Physical test route

1. Start M04 from the campaign, or load a save at the start of M04. Confirm
   the prisoner objective
   (`IDS_Enc_Obj_Primary_M04_01`) appears.
2. Engine room. Destroy all four engines. Expect the turbine and engine loops
   to stop and the klaxon and broken-engine loops plus the 2D
   `SFX.Ship_Engine_Stop` to start. Then confirm objective 200 completes and
   the powerups spawn.
3. Missile room: sabotage all 4 missiles (objective 300). Torpedo room:
   sabotage both torpedoes (objective 400).
4. Take the prison key from the guard (objective 110) and free the three
   prisoners (objective 100).
5. Kill the first mate (objective 600) and the captain (objective 700).
6. Go to the sub bay. Expect the firefight to start and the prisoners to
   gather. Stand in zone 101194 with prisoner 3 (on Normal/Hard). Expect the
   `00-n048e` EVA line and then the mission-complete flow into M05.
7. Collect the runtime log and check for "Unable to create script:
   M04_ForeDeck_Reinforcement_03_JDG" (expected, and the same as retail), plus
   NULL-script-pointer lines for the 8 absent IDs (expected). There should be
   no audio decode failures other than `steam_med_pressure_01.wav`.

## Reproduction

The checks were scratch scripts run on the read-only retail data. They reuse
the existing parsers (`tools/audit_m13_level_owners.chunks`,
`tools/audit_mission_conversations.sound_definitions/RetailFiles/sound_chain`,
`tools/renegade_cinematic_dependency_scan.MixArchive`) and the private
binding receipt `build/s4-all-map-bindings/m04-bindings.json`. Retail data
was not modified and no payloads were exported.

## Full audit — 2026-10-07

Evidence class: source plus read-only retail data (Vita3K
`ux0:data/renegade/retail/Data`, M04.mix `1d084c90…30ffa`). Nothing was built,
launched or run on a Vita. The checks were scratch scripts that reuse
`tools/audit_m13_level_owners`, `tools/audit_mission_conversations`,
`tools/audit_mission_event_routes.numeric_constants`,
`tools/renegade_cinematic_dependency_scan` and the private receipt
`build/s4-all-map-bindings/m04-bindings.json`. Line numbers refer to
`staging/scripts/Mission04.cpp`.

**Result: no new defect needs a patch.** Every finding below either resolves,
or fails the same way as retail PC and cannot crash or block completion. There
is one upstream ordering race (item 5). It is recorded and not patched, because
fixing it would change the original design.

### 1. Script bindings and parameter counts

- There are 322 level and definition bindings and 150 distinct scripts. All
  are registered and linked. The dev238 symbol list contains, for example,
  `M04_Firefight_Prisoner`, `M04_EngineRoom_Stationary_Tech_JDG`,
  `M00_5MetalBarrels_ChainRxn_Controller_JDG` and `Test_Cinematic`. The
  compdb compiles `Mission00/01/04.cpp`, `Toolkit*.cpp` and
  `Test_Cinematic.cpp`.
- Parameter shape (`live_script_parameters.json`): 34 equal counts and 288
  "excess" counts. Every excess is the editor's default `"0"` value on a
  script that takes no parameters. `Set_Parameters_String` ignores values
  past the descriptor, so these are benign.
- The parameterised bindings all match their descriptors:
  - `M00_5MetalBarrels_ChainRxn_Controller_JDG`: 15 of 15 values. The barrel
    types are 4, 6, 3, 5 and 3, which keeps the indexes into
    `simple_barrels[8]` within bounds (`Toolkit.cpp:386`). The descriptor is
    under the 511-byte truncation limit, and `Get_Parameter_Index` trims
    `"Barrel01_Type (1-8)"` correctly (`scripts.cpp:535`).
  - `M04_EngineRoom_Stationary_Tech_JDG` (`Console_ID`, `:6063`): the values
    100416–100419 are all serialized objects.
  - `M04_PlaySound_OnZoneEntry_OneTime_JDG` (`:10265`): 8 sound presets
    (`M04DSGN_DSGN0085/86/92/93/96/97/98/100I1EVAN_SND`). All resolve to a
    definition with a present wave.
  - `M00_Play_Sound` and `M00_Play_Sound_Object_Bone_DAY`: 6 and 4 distinct
    presets. All resolve except `SFX.Nod_Visceroid_Twiddler`, which is an
    empty twiddler in retail and is silent and safe (see above).
- Every `Attach_Script` literal in Mission04 exists with a matching parameter
  count, including `Test_Cinematic("X4A_MIDTRO.txt")`, with one exception:
  `M04_ForeDeck_Reinforcement_03_JDG` (`:5352`). That script is missing from
  the released source, so retail fails the same way.

### 2. Custom events, timers and Find_Object IDs

- 87 self-sent events. 85 have a handler. The 2 without one are
  `M04_TorpedoRoom_Target01/02_JDG` sending `M01_MODIFY_YOUR_ACTION_JDG` to
  themselves (`:9599`, `:9664`). Those scripts have no `Custom` method, so the
  event is a no-op. Retail behaves the same way.
- 1 `Start_Timer` (`M04_Ships_Captain_JDG`, `STATIONARY_DELAY_TIMER`). It is
  handled.
- 211 events sent to `Find_Object` targets:
  - All 23 distinct (type, param) pairs sent to objective controller 100424
    are handled. These are 4, 100–130, 200/210, 300–330, 401, 410, 430–470,
    500–590 and `DO_END_MISSION_CHECK`.
  - Targets created at runtime (via `Create_Object`, then `Attach_Script`,
    then `Get_ID`) were resolved to their attached scripts, and the handler
    was found for: the missile upper guards, the first-mate bodyguards, the
    Apache, the closet and mess-hall guys, the mutant chambers, and firefight
    prisoners (666 and 1).
- Events with no receiver. All are no-ops and match retail:
  - 700 to cargo controller 100558 (`:2164`; the comment says "turn off
    spawners", but no handler exists).
  - 100 to first mate 100400 (`:3991`) and captain 100401 (`:5283`). Neither
    script has a `Custom` method.
  - 2000 to Tiberium-hold controller 100572 (`:7552`).
  - Type 200 to the missile-room guards (`:1289`, `:1294`).
  - Apache `MODIFY_YOUR_ACTION_04..09` from the rocket emplacements and the
    hangar zones (`:5952`, `:6049`, `:8429`–`:8678`). The Apache's ID is held
    in another script's variable, so this route was not resolved
    statically.
  - The 7 absent sub-bay music zones (`:7598`–`:7608`, already listed above).
- Several members are never initialised: the cargo controller guard IDs, the
  rally-zone prisoner IDs before custom types 1–3 arrive, and
  `M04_BigSam_Script_JDG` sound IDs. The original
  `ScriptRegistrant::Create` uses `new T` (`scriptregistrant.h:52`), so
  these values start as heap garbage. They only ever reach
  `Find_Object`/`==`, which are safe. Retail is the same.

### 3. Content resolution (retail archives)

| Kind | Checked | Unresolved |
|---|---|---|
| `Create_Object` presets | 29 | 0 |
| Sound literals (`Create_Sound`/`Create_2D_Sound`/…) | 35 | 2. Both are the known `steam_med_pressure_01.wav`, missing on PC too. |
| Animations (`Set_Animation*`/`Set_Animation` params) | 25 | 1. `H_A_J06C` (`:3221`, prisoner 1 "hanging head" idle, action id 102 with no completion consumer). No `h_a_j06c.w3d` in M04/always/Always2. The original anim lookup returns NULL and nothing plays, the same as retail. |
| String IDs (`IDS_*`) against `strings.tdb` | 26 | 0 |
| Conversations | 26 | 0 (previous section) |
| `x4a_midtro.txt` (the only M04 cinematic, 60 commands) | 27 deps (models, real-object presets, animations, audio) | 0 |
| Keycard definitions `M04_L01/L02/L03_Keycard` (81950043/44/45) | 3 | 0. Their definition scripts `M04_Keycard_0N_Script_JDG` are bound. |

M04.mix has no `.ddb` overlay, so all presets come from `always.dbs`.

### 4. Crash review (script layer)

- The analysis recomputed the NULL guards of every `scriptcommands.cpp`
  command that takes a `GameObject *`. The swept
  `script_command_bodies.json` under-reports these guards because it misses
  `SCRIPT_PTR_CHECK_RET`. Only 5 commands dereference without a guard:
  `Has_Key`, `Create_3D_Sound_At_Bone`, `Create_3D_WAV_Sound_At_Bone`,
  `Create_Logical_Sound` and `Monitor_Sound`.
- Mission04 uses `Has_Key(STAR)` only when `enterer == STAR` (`:3057`,
  `:3497`), so STAR is not NULL there. It calls `Monitor_Sound` only with
  `obj`. `Create_Logical_Sound` appears only in commented-out code.
- Every other `Find_Object`, `Create_Object` and `Trigger_Spawner` result
  either goes to a guarded command or is checked against NULL first.
  Mission04 dereferences no pointers directly. `Join_Conversation(NULL, …)`
  is handled.
- Random indexes stay in bounds. `Get_Random_Int(min, max)` returns values
  in [min, max) (`crandom.h:87`), so `powerups[2]`, `mutantAnimations[4]`
  and `M01_Choose_Cheer_Animation` cannot overflow. The hazing
  `conversations[counter]` index is reset when it reaches 3 (`:2889`).
- No `sprintf`/`strcpy`/fixed buffers. The single division is a float
  (`last_health` ratio, `:9014`) on a soldier with non-zero max health.

### 5. Objective chain (re-verified) and the residual race

The chain in the first section holds. Only `Mission_Complete(false)` (`:9157`)
and `Mission_Complete(true)` (`:710`) end the mission.

There is one upstream race, retail-identical and not patched:
`announce_torpedo_room_objective` (450) sets `torpedo_primary_active = true`
without checking whether it already completed. The trigger zone sends 450
only after `M04_Add_Torpedo_Objective_Conversation` ends (`:10110`). The
torpedoes are pokable from `Created`, without waiting for the announcement.
So a player who sabotages both torpedoes while that conversation is playing
would leave the flag stuck at true, and `DO_END_MISSION_CHECK` (`:713`) would
never pass.

The missile announce (440) fires immediately when the player enters the zone
(`:7840`), which makes the same race much narrower. Watch for this race on
hardware. Do not change it without physical evidence that it is reachable.

### 6. Port patches touching M04

Only `port/patches/scripts-a36-m04-save-variable-ids.patch` touches M04. It is
registered at `tools/stage_sources.sh:1153` and listed in
`staging/PATCH_INVENTORY.json`. It changes `M04_Firefight_Prisoner`'s
`warningPlayed` save ID from 3, which duplicated `pokable`, to 4 (`:8996`).
The staging diff against upstream is exactly that one line. The patch is
correct, and it is backward compatible with older saves: a missing chunk
leaves the value as initialised by `Created`.

One save-state gap remains open and is not patched: `M04_BigSam_Script_JDG`
has no REGISTER block (`:10197`, `SCRIPT_SAVE_STATE_GAPS.md`). If the game is
saved during the Big SAM sound sequence, the cosmetic gun animation can stall
after a load. No objective depends on it.

## Soft-lock hunt — 2026-10-07

Evidence class: staged source, read-only retail data (Vita3K
`ux0:data/renegade/retail/Data`: `M04.mix` `m04.ldd`, `always.dbs`
`conv10.cdb`, `strings.tdb` and wave headers), the binding receipt
`build/s4-all-map-bindings/m04-bindings.json`, one `arm-vita-eabi-g++
-fsyntax-only` of the patched `Mission04.cpp` (exit 0, only pre-existing
warnings) and a full `tools/stage_sources.sh` run (PASS, 545 ordered patches,
only `Mission04.cpp` and the inventory change). Nothing was built, linked,
packaged, launched in Vita3K or run on a Vita. Line numbers refer to the newly
staged `staging/scripts/Mission04.cpp` (sha256 `48dcc115…36c0e6`). This
section supersedes the "differs from upstream by one line" note and the
"not patched" decision in item 5 of the full audit above.

### Key conversations in M04 (m04.ldd, `ConversationClass::VARID_ISKEY`, micro-chunk 13)

Key: `M04_Prisoner_Guard_is_in_Medlab_Conversation`,
`M04_MissileRack_01/02/03_Sabotaged_Conversation` and
`M04_Add_Captains_Key_Objective_Conversation`. The other 24 level
conversations are not key, and none of the 3,606 global conversations in
`conv10.cdb` is key. `ActiveConversationClass::Start_Conversation`
(`staging/combat/activeconversation.cpp:399`) stops a non-key conversation
with INTERRUPTED while any key conversation plays. That happens before the
script's `Monitor_Conversation`, so no callback arrives. A key conversation
that starts later stops a running non-key one with the default reason ENDED
(`conversationmgr.cpp` Think), which M04 handles. Every M04 `Action_Complete`
acts on ENDED only.

### Issues fixed

| # | Issue | Where | Reachability | Severity | Fix |
|---|---|---|---|---|---|
| 1 | Torpedo objective completed before its announcement. The racks are pokable from `Created` (`:9585`). Announce 450 is sent only after the zone's conversation ends (`:10150`). A late 450 set `torpedo_primary_active` back to true and re-added 400 as pending, so the end check (`:753`) could never pass. | `:499`–`:525`, `:662` | Reaching both torpedoes before crossing announce zones 105238/105239, then crossing one. Or poking both inside the ~2 s window of the voiceless one-remark announce conversation. Zone/torpedo geometry was not measured. | Hard soft-lock | `scripts-a38-m04-torpedo-objective-race.patch`: new flag `torpedo_objective_completed` (save id 47) set by 550. When 450 arrives after completion (flag, or saved counter `number_torpedos_sabotaged >= 2` for older saves), objective 400 is added and marked accomplished and the flag is left false. The normal order runs the original branch unchanged. |
| 2 | Missile briefing dropped. 440 sets `missile_primary_active` and starts the non-key `M04_Add_MissileRoom_Objective_Conversation`. Only its ENDED callback adds objective 300 and sends `M01_START_ACTING_JDG` to racks 100420–100423, which ignore pokes until then (`:7951`). Zones 100429/100431 send 440 once and are destroyed (`:7880`). | `:243`, `:467`–`:497` | Entering the missile-room zone while a key conversation plays: the captain-key line (4.8 s; 10 s after the key-2 pickup, with post-first-mate patrols spawned on the route back past the missile room), or the prisoner-1 medlab line (7.8 s). | Hard soft-lock | `scripts-a38-m04-missile-briefing-drop.patch`: 440 also schedules self-custom 441 after 20 s (the briefing is two remarks, about 8.2 s of wave data). If the end callback has not run by then, 441 runs the original end-of-briefing branch through `Action_Complete(obj, missileConv, ENDED)`. A new flag `missile_objective_activated` (save id 48) makes that branch run once. On the normal path the callback runs first and 441 does nothing. |

Both patches are registered after `scripts-a36-m04-save-variable-ids.patch`
in `tools/stage_sources.sh` and apply with zero fuzz. Save ids 47 and 48 were
unused (the controller used 1–46). Custom timers are saved
(`scriptablegameobj.cpp` `CHUNKID_CUSTOM_TIMER`) and fire even when the sender
is gone, so the fallback survives save/load. Saves written before these
patches load the new flags as false. Issue 1 is still covered for them
through the counter. Issue 2 is covered unless the briefing had already been
dropped before the save.

### Reviewed, no soft-lock (retail-identical, not changed)

- **(a) Other non-key monitored conversations** (dropped the same way):
  mission start (objective 100 HUD/markers; `prisoner_primary_active` is set
  at announce and cannot be dropped in the first 3 s), engine room (430,
  secondary 200 entry only), prison key (401, objective 110 entry only; the
  warden still drops key 1 on death, `:7767`), Eva guard hint (marker 111),
  first mate (600 entry only; the flag is set at 410), protect POWs (800 entry
  only), firefight reminder (`missionIntroConv_playing`, `:9365`, reminder
  silenced). None of them gates a flag in the end check, so a drop only hides
  an objective entry. The torpedo announce zone (`:10134`) is the same
  pattern: a dropped announce leaves `conversationPlaying` true and 450 is
  never sent. The torpedoes then stop being required (the flag stays false),
  which is permissive, not blocking. Prisoner 1's key medlab conversation
  (`:3291`) is key, so it cannot be dropped at start; a newer key
  conversation ends it through Think with ENDED.
- **(b) Other completion-before-activation orders**: first mate is guarded by
  `first_mate_primary_triggered` (`:537`, set again by 510). If the captain
  dies first, 510 takes the 520 path (`:683`). Captain 420 after 520 needs the
  captain killed and key 3 collected within 10 s of the key-2 pickup at the
  opposite end of the ship. Not reachable, so it is not patched. Missiles
  cannot complete before 440 (racks are gated). The prisoner announce comes
  3 s after start.
- **(c) Counters**: missiles 4/4 and torpedoes 2/2 are poke-once (`poked_yet`
  saved). Engines 4/4 count `Killed` from any killer (secondary). No
  objective filters on `killer == STAR`. The rally zone's `Exited` bug
  (`:9545`, all three use `prisoner01_ID`) can only keep prisoners 2 and 3
  marked, so it cannot undercount. The end check is sent only from
  `Entered`, so a player who arrives before the last objective re-enters the
  zone afterwards.
- **(d) One-shot triggers**: battle-music zones latch key 3 and resend 100 on
  every entry until the firefight starts (`:5525`). A key-3 pickup before the
  rescue only plays a reminder. The mission is still completable after the
  rescue.
- **(e) Required NPCs**: warden, first mate and captain drop keycards on
  death from any cause. `Create_Object` powerups do not expire, because only
  `Expire_Powerup` expires them and M04 never calls it. Prison prisoners are
  not needed (the midtro and firefight create new actors). A dead firefight
  prisoner fails the mission on purpose (`:9197`). Prisoner 3 on Normal/Hard
  still depends on pathfinding to zone 101194 (remaining risk 1). The midtro
  sends its custom to 104514, which the receipt confirms is bound to
  `M04_Prisoners_Rescued_Controller_JDG`.
- **(f) Save/load**: the controller saves `firstmateConv` twice (ids 37 and
  45). That is the same variable, so it is harmless. `Test_Cinematic` saves its
  state. All objective-chain state named above is registered.
  Death/restart reloads the whole level.

### Deferred

- Partial torpedo race (one torpedo sabotaged before 450): 450 re-adds radar
  marker 401 or 402 for the sabotaged torpedo, and the pog controller labels
  100410 as "target01". Both are cosmetic.
- Objective-list entries that disappear when a non-key briefing is dropped (see (a)).
  They are cosmetic, and fixing them would add fallbacks to seven more call
  sites.
- Physical check: in M04, kill the first mate, collect key 2, then enter the
  missile-room zone about 10 s later while the captain-key line plays. Expect
  objective 300 about 20 s after entry, and pokable racks. To check the torpedo
  race, poke both torpedoes before crossing 105238/105239, then cross. Expect
  objective 400 to appear already accomplished, and the rally-zone end check to
  pass.

## Conversation-gate fixes — 2026-10-07

Evidence class: staged source and read-only retail data only. Nothing was
built, linked, packaged, launched in Vita3K or run on a Vita. Checks: one
`arm-vita-eabi-g++ -fsyntax-only` of the patched `Mission04.cpp` with the
candidate flags (exit 0; the same 120 warnings as before the patch, no new
ones), a full `tools/stage_sources.sh` run (Patch inventory PASS, 571 ordered
patches, zero fuzz; only `Mission04.cpp` and `PATCH_INVENTORY.json` change),
`tools/test_m04_conversation_gate_preempt.py` (9 tests, all pass with the
upstream tree present), and `tools.audit_conversation_gated_objectives
--mission M04` (now 8 FIXED, 0 AT RISK, 0 REVIEW; was 5 AT RISK, 2 REVIEW).
`CONVERSATION_GATED_OBJECTIVES.md` was not regenerated. Line numbers refer to
the newly staged `staging/scripts/Mission04.cpp` (sha256 `2e7bfadc…59cc0`).
This section supersedes item (a) of "Reviewed, no soft-lock" and the
"objective-list entries" and partial torpedo race marker items under
"Deferred" above.

Patch: `port/patches/scripts-a38-m04-conversation-gate-preempt.patch`,
registered after `scripts-a38-m04-missile-briefing-drop.patch`.

**Mechanism.** Retail starts each briefing, then registers the monitor. While a
key conversation plays, `ActiveConversationClass::Start_Conversation` stops the
non-key briefing with INTERRUPTED before the monitor exists, so the
`Action_Complete` step never runs. The fix uses the M10 pattern. The monitor
is registered before Start. A transient `conversation_starting` (not saved, 0
outside the start window) names the briefing for the length of the Start call.
The `Action_Complete` switch also accepts INTERRUPTED and UNABLE_TO_INIT, but
only when `action_id == conversation_starting`. INTERRUPTED from anywhere else
(for example `ConversationMgrClass::Reset` on a level reset or load) keeps the
retail result. `Briefing_Start_Done` (`:255`) closes the window. If
`Create_Conversation` failed (id < 0), it runs the step directly. Saved
once-flags use the unused controller ids 49–53, so each step runs once. When
no key conversation is playing, Start does not touch the monitor array, so the
order, timing and effects match retail.

| Gate (old line) | Step side effects (Action_Complete branch) | Not in the branch (unaffected) | Impact of a drop before the fix | Fix (new lines) |
|---|---|---|---|---|
| Mission start, 400 (`:401`) | self-custom 1 (Havoc twiddler), `Add_Objective 100`, markers 101–103 on prisoners 1–3, HUD position of 100 | `prisoner_primary_active`, `mission_started`, reminder pog 0 | Objective 100, its markers and HUD missing. 500 later completes an objective that was never added. Not blocking. | Monitor `:462`, start `:464`, branch `:278`, flag `mission_intro_step_done` (49) |
| Prison key, 401 (`:425`) | `Add_Objective 110`, then starts the non-key Eva hint, whose end adds marker 111 on the warden and the HUD position of 110 | reminder pog 2, twiddler | Objective 110 and the Eva hint lost. The warden still drops key 1. | Monitor `:488`, branch `:379`, flag `prison_key_step_done` (50). The nested Eva start is also monitor-first (`:387`–`:390`). On the preempted path, the key conversation is still playing, so the hint would otherwise always be dropped. |
| Missile room, 440 (`:469`) | `Add_Objective 300`, `M01_START_ACTING_JDG` to racks 100420–100423 (unpokable until then), pog 300 | `missile_primary_active`, reminder pog 1 | Hard soft-lock. Already covered by the 441 fallback. | Verified and kept: 441 (`:558`) runs the step through `Action_Complete(…, ENDED)` only while flag 48 is false. Now also monitor-first (`:538`), so a preempted briefing runs the step immediately. 441 stays as a backstop, for example when `Register_Monitor` finds no free slot. |
| First mate, 410 (`:542`) | sound `00-n040e`, `Add_Objective 600`, marker 601 on the first mate, self-custom 1 after 2 s, HUD position of 600 | `first_mate_primary_triggered`/`_active` (set before Start), reminder pog 3 | Objective 600, marker and HUD lost. 510 completes it independently. Not blocking. | Monitor `:624`, branch `:405`, flag `first_mate_step_done` (52) |
| Protect POWs, 470 (`:582`) | `Add_Objective 800`, marker 801, HUD position of 800 | reminder pog 6 | Objective 800 entry and marker lost. The end check does not use 800. | Monitor `:667`, branch `:421`, flag `protect_pows_step_done` (53) |
| REVIEW engine room, 430 (`:460`) | secondary `Add_Objective 200`. The unresolved "custom 6/200" is `M01_ADD_OBJECTIVE_POG_JDG`/200 to 104693 = `M04_Pog_Controller_JDG` (binding receipt), which sets the 200 HUD on the first live terminal. Also objective blips on the 4 engine terminals. | none | Secondary objective, pog and blips lost. Completion 530 (kill count, power-ups) is independent, so mission completion is not gated. | Fixed anyway with the same pattern: monitor `:527`, branch `:336`, flag `engine_room_step_done` (51) |
| REVIEW torpedo zone (`:10135`) | Custom 450 to the controller (100424), which sets `torpedo_primary_active`, adds 400, markers 401/402, twiddler and reminder pog 5, or takes the race branch. Also pog 400 to 104693 and destroys both zones 105238/105239. | none | The zone stays latched (`conversationPlaying`). If the other zone is not crossed, primary 400 is never announced and the torpedoes are silently not required (permissive). | Monitor-first and the same guarded accept in the zone (`:10228`, `:10247`–`:10250`). Each zone starts the announcement once through its existing saved `conversationPlaying` latch, so no new flag is needed. |

**Cosmetic (partial torpedo race).** The controller now records each sabotaged
torpedo (`torpedo_01_done`/`torpedo_02_done`, ids 54/55, set at `:1107` and
`:1126`). A 450 that arrives after one torpedo was sabotaged no longer re-adds
that torpedo's marker 401/402 (`:590`–`:597`). Nothing would clear that
marker. The pog controller labelling 100410 as "target01" is unchanged
(cosmetic only).

**Saves.** Scripts are value-initialised (`scriptregistrant.h`), so saves
written before this patch load the new flags as false and
`conversation_starting` as 0. That keeps retail behaviour. A briefing that
was already dropped before such a save is not recovered, except the missile
step (441 timer).

**Physical check.** In M04, kill the first mate, collect key 2 and, while the
captain-key line plays (about 10 s after the pickup), enter the missile-room
zone. Expect objective 300 to appear at once and the racks to be pokable.
Independently, trigger the first-mate announce (410) or the prison-key
announce (401) during a key line. Expect objective 600, or objective 110 plus
the warden marker, to appear at once.
