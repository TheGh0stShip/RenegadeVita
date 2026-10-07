# ScriptCommands NULL safety (host source audit)

Evidence class: host source audit plus `arm-vita-eabi-g++ -fsyntax-only` with
the `vita-fast-candidate` compile flags. Nothing here is Vita3K or physical
evidence. No build, link, VPK or device run was performed.

## Scope and method

- Owner: `staging/combat/scriptcommands.cpp`, final staged text (pre-patch
  sha256 `1466877658628e8020c65c4bb222fee7d399c68c57ec82f40fccedb3a7e8a69f`).
  No port file overrides a ScriptCommands body. `port/platform/renegade_script_static_provider.cpp`
  only binds the table, and the `port/compatibility/include/renegade_*_script_defaults.h`
  headers only supply default arguments.
- Every function assigned in `Get_Script_Commands()` (about 180 slots) was read
  for dereferences of `GameObject *` arguments, strings, model, bone, animation,
  file-handle and index inputs. The engine callee was followed when the command
  forwarded the pointer (`HTreeClass::Get_Bone_Index`,
  `DefinitionMgrClass::Find_Typed_Definition`, `ArmorWarheadManager::Get_*_Type`,
  `ConversationMgrClass::Find_Conversation`, `AnimCollisionManagerClass`,
  `PhysicalGameObj::Attach_To_Object_Bone`, WWAudio create paths,
  `ObjectiveManager`, `SpawnManager`, `MapMgrClass`).
- Campaign callers were counted in `Mission0*.cpp`, `Mission1*.cpp`, `mission08.cpp`,
  `MissionX0.cpp`, `Toolkit*.cpp` and `Test_Cinematic.cpp`.
  `ScriptImpClass::Get_Parameter` and the cinematic `Get_Command_Parameter` return `""`, never
  NULL. Script-supplied strings are therefore empty rather than NULL. The
  real NULL sources are `Find_Object`, `Get_A_Star`/`STAR`, `Create_Object`, a
  NULL `killer`/`damager`, and model, animation or asset lookups that miss.
- `SCRIPT_PTR_CHECK` / `Debug_Say` are WWDEBUG-only, so release builds do not
  log these guards.

## Patch

`port/patches/combat-a36-scriptcommands-null-guards.patch` (22 hunks, combat
stage). It is registered at the end of `tools/stage_sources.sh` and anchored
before and after the patch: pre `1466877…a69f` and post
`c6c127c54ac6689703f62612206935da98bd870866148587e2e818a032f61985`. No earlier
anchor moved. `bash tools/stage_sources.sh` exits 0 with zero fuzz. The patch
inventory now has 526 patches.

Policy: the file already uses `SCRIPT_PTR_CHECK`, and the patch applies the
same convention. When a required pointer is NULL, the command is a no-op that
returns its existing failure value. Behavior with valid pointers is unchanged.
Engine-defined NULL semantics are preserved. Examples: `Join_Conversation(NULL)` keeps
adding a body-less orator, and `Attach_To_Object_Bone` with a NULL or non-physical
host still detaches.

## Per-command table

Legend: **orig** means the upstream body already handled the case. **now**
means the guard added by this patch. "–" means no pointer or index input, or
the input was already safe.

### Commands changed by this patch

| Command | Guarded originally | Guarded now | Campaign callers / at-risk sites |
|---|---|---|---|
| `Has_Key(obj,key)` | **No**: `obj->As_SmartGameObj()` on NULL | `obj` NULL → `false` | 27. **At risk:** M03 `M03_Officer_With_Key_Card{,2}::Killed` uses `Has_Key(killer,…)` (killer can be NULL). `Has_Key(STAR,…)` appears in M01 ×5, M02 ×1, M03 ×5, M04 ×2 and M10 ×3, and `STAR`=`Get_A_Star` is NULL with no live human soldier. M00 `enterer` is safe. |
| `Create_3D_Sound_At_Bone(name,obj,bone)` | **No** obj check, model check, or name/bone check | `name`/`obj`/`bone` NULL or `Peek_Model()` NULL → `0` | 17. **At risk:** paratroopers in M03 4753/4765/4777, M09 2365/2377/2389 and M10 1761/1773/1785 use `Create_Object("Generic_Cinematic")` and then `Set_Model("X5D_Parachute")`. Each is unchecked, and a missing model gives a NULL model. Test_Cinematic 693 checks obj but not the model. |
| `Create_3D_WAV_Sound_At_Bone` | **No** (same as above) | same → `0` | 1 (Toolkit_Sounds 679) |
| `Create_Object_At_Bone` | obj, name and bone orig. Model **no** | `Peek_Model()` NULL → `NULL` | 42 (M11 ×18, M09 ×5, M03 ×4, M10 ×4, Test_Cinematic 566 host from slot) |
| `Create_Explosion_At_Bone` | name, obj and bone orig. Model **no** | `Peek_Model()` NULL → no explosion | 10 (M03 ×6, Test_Cinematic 613 host from slot, Toolkit) |
| `Attach_To_Object_Bone(obj,host,bone)` | obj orig. Host model and bone **no** (`HTree` `stricmp(NULL)`) | physical host with NULL model or NULL bone → no-op. Non-physical or NULL host still detaches | 69 (M11 ×35 Kane hologram, cryo; M09 ×7, M03 ×6, M01 ×5, M10 ×5) |
| `Set_Is_Rendered` | obj orig. Model **no** | `Peek_Model()` NULL → no-op | 37 (M03 ×8, M09 ×8, M11 ×8) |
| `Set_Animation` (sub-object path) | obj orig. Model **no** | `Peek_Model()` NULL → no-op | 170 total. Only the sub-object path is affected (Test_Cinematic `Play_Animation` with sub_obj) |
| `Static_Anim_Phys_Goto_Last_Frame` | lookup orig. `Peek_Animation()` **no** | NULL anim → mode set, target unchanged (same as engine `Set_Target_Frame_End`) | 14 (M09 elevators ×3, M10 ×4, M06 doors ×3, mission08 ×2) |
| `Get_Bone_Position` | obj and model orig. Bone **no** | `bone` NULL → `(0,0,0)` | 3 (literals) |
| `Create_Object(name,tm)` (internal) | `WWASSERT` only before `As_PhysicalGameObj()->` | non-physical preset → no transform. Observers still start | 949 through the guarded `Vector3` overload. No campaign preset is non-physical (`Invisible_Object` is physical) |
| `Find_Random_Simple_Object` | **No** (`stricmp(…,NULL)`) | NULL → `NULL` | 0 campaign (Test_RMV_Toolkit only) |
| `Create_Sound` / `Create_2D_Sound` | **No** (`Find_Typed_Definition` `stricmp(…,NULL)`) | NULL name → `0` | 330 / 16 (all literals or `Get_Parameter`) |
| `Set_Shield_Type` / `Apply_Damage` (name) | **No** (`Get_Armor/Warhead_Type` `stricmp`) | NULL name → no-op | 14 / 105 (all literals) |
| `Create_Conversation` | **No** (`strcmpi(…,NULL)`) | NULL name → `-1`. Lookup telemetry is still recorded | 565 (literals) |
| `Text_File_Open` | **No** (`Get_File(NULL)`) | NULL → handle `0`. Telemetry is still recorded | 1 (Test_Cinematic, `Get_Parameter`) |
| `Text_File_Get_String` | host-ABI only. **Vita derefs handle 0** | NULL buffer or handle 0 → `false` on Vita too | 1 (Test_Cinematic checks the handle first) |

### Commands verified already safe (no change)

| Command(s) | Guarded originally | Notes / campaign callers |
|---|---|---|
| `Action_Reset/Goto/Attack/Play_Animation/Enter_Exit/Face_Location/Dock/Follow_Input`, `Modify_Action`, `Get_Action_ID`, `Get_Action_Params`, `Is_Performing_Pathfind_Action` | Yes (obj). `Get_Action()` returns `&Action` | Action_Goto 680, Action_Attack 319 |
| `Set_Position`, `Get_Position`, `Get_Facing`, `Set_Facing`, collision commands, `Destroy_Object`, `Get_ID`, `Get_Preset_ID/Name`, `Add_To_Dirty_Cull_List` | Yes (obj + non-physical) | Get_Position 884, Set_Facing 435, Destroy_Object 519 |
| `Attach_Script` | Yes (obj, name). NULL params is assert-only, and scripts pass literals | 788 |
| `Start_Timer`, `Trigger_Weapon`, `Select_Weapon` (NULL weapon name selects index 0 in `WeaponBagClass`) | Yes | 709 / 8 / 34 |
| `Send_Custom_Event` (`to`), `Send_Damaged_Event` (`object`) | Yes. NULL `from`/`damager` is allowed | 3,247 / 0 |
| `Set_Model`, `Set_Animation_Frame`, `Set_Animation` (main path) | Yes (obj). NULL or empty anim is handled by `StringClass` | 122 / 61 / 170 |
| `Create_2D_WAV_Sound`, `Create_Logical_Sound` (NULL creator OK), `Monitor_Sound` (NULL obj unregisters; deref only under `ScriptTrace`), `Start/Stop_Sound`, music commands | Yes | 82 / 29 / 34 |
| Health, shield and player-type getters and setters | Yes (obj + non-damageable) | Get_Health 194, Set_Health 137 |
| `Set_Camera_Host` (NULL = detach), `Force_Camera_Look`, `Find_Closest_Soldier`, `Get_The_Star`, `Get_A_Star`, `Is_A_Star` | Yes | Get_A_Star returns NULL by design. Callers are covered above |
| `Control_Enable`, `Is_Object_Visible`, `Enable_Enemy_Seen`, innate commands, `Innate_Force_State_*` | Yes | Set_Innate_Is_Stationary 306 |
| `Display_Text/Float/Int` (`Convert_From(NULL)` safe), `Set_Display_Color` | Yes | debug only |
| Save/Load/Chunk commands | Yes (A35/A36 capacity and status patches) | |
| Radar, objective commands (missing id → `Find_Objective` NULL handled), `Set_Objective_Radar_Blip_Object` | Yes | Add_Objective 174 |
| `Create_Explosion`, `Give_PowerUp`, `Grant_Key`, `Enable_Hibernation`, `Enable_Engine`, `Enable_Stealth`, `Enable_Vehicle_Transitions` | Yes | Enable_Hibernation 215 |
| `Join_Conversation` (NULL obj → body-less orator by design), `Join_Conversation_Facing`, `Start/Stop/Monitor_Conversation` (missing id handled), `Start_Random_Conversation`, `Stop_All_Conversations` | Yes | Join_Conversation 840, including literal `NULL` |
| `Lock/Unlock_Soldier_Facing`, `Set_Loiters_Allowed`, `Set_Is_Visible`, points/money, building commands, `Find_Nearest_Building*`, `Team_Members_In_Zone` | Yes | |
| `Enable_Spawner`/`Trigger_Spawner` (unknown id → no-op / NULL) | Yes | 401 / 116 |
| Weather, fog, map, HUD, letterbox and fade commands, `Get_Sync_Time`, `Get_Difficulty_Level`, `Get_Safe_Flight_Height` | – | Clear_Map_Cell 130 (constant non-negative cells; see residual 2) |
| `Display_*_Player_Terminal` (NULL star is handled in `RenegadePlayerTerminalClass`), encyclopedia, `Scale_AI_Awareness`, `Enable_Cinematic_Freeze`, `Expire_Powerup`, `Enable_HUD_Pokable_Indicator`, `Enable_Innate_Conversations`, `Display_Health_Bar`, `Enable_Shadow`, `Clear_Weapons` | Yes | |

## Residual risks (not changed: outside ScriptCommands, or a behavior choice)

1. `PhysicalGameObj::Set_Animation/Set_Animation_Frame` dereference `Peek_Model()->Get_Name()`
   when the anim name has no `.` and the model is NULL. That code is in combat, not ScriptCommands.
2. `MapMgrClass::Clear_Cloud_Cell(int,int)` has an upstream clamp bug: it clamps
   `x_pos` rather than `cell_x`, so negative cells index `CloudVector` out of bounds. Campaign
   callers use only non-negative constants. Separately, `bit = offset%32 + 1`
   gives `1 << 32`. That masks bit 0 on x86 and is 0 on ARM, so every 32nd shroud cell
   differs from PC. This is visual, not a crash, and needs a mapmgr.h patch.
3. Script-side unchecked indices: Test_Cinematic `Command_Create_Explosion` and
   `Command_Create_Real_Object` host slot (`ObjectSlots[atoi(..)]` without a NUM_SLOTS check), and M09
   `elevators[Get_Int_Parameter("Anim_num")]`. These are safe with retail data.
4. `Create_Object` presets that the definition lookup returns as non-physical are
   still C-cast to `PhysicalGameObj *` in `ObjectLibraryManager`. The guard only
   avoids the transform deref.

Next gate: a full candidate build and a Vita3K/physical M01/M03/M09/M10 run. This
patch has not been compiled into a packaged artifact.
