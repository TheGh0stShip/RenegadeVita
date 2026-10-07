# M04 (cargo ship) readiness — 2026-10-07

Evidence class: source and read-only retail-data inspection only. Nothing was
built, launched in Vita3K or run on a Vita. No physical M04 result exists, so
this report does not claim that M04 is completable on hardware. It records
which source and data paths can complete the mission, and which risks remain.

Inputs: `staging/scripts/Mission04.cpp` (10,518 lines; identical to upstream
`Code/Scripts/Mission04.cpp`, so no staging patch is applied). Retail data:
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
