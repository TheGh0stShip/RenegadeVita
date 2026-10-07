# Model-less cinematic object safety

Evidence class: host source audit, plus read-only extraction of retail cinematic text from the
Vita3K retail `Data` copy, plus `arm-vita-eabi-g++ -fsyntax-only` using the
`vita-fast-candidate` compile flags. No build, link, VPK, Vita3K or device run was performed.
Nothing here is runtime or physical evidence.

Closes the "Not fully proven: a missing cinematic model" class in
[ASSET_CLOSURE.md](ASSET_CLOSURE.md).

## Verdict

* The class was **not graceful**. Before this patch a missing cinematic model was a certain
  NULL dereference, on the PC and on the Vita, inside `Command_Create_Object` itself:
  `Commands->Set_Facing` (staging/scripts/Test_Cinematic.cpp:520) -> ScriptCommands `Set_Facing`
  (staging/combat/scriptcommands.cpp:374, `pgobj->Get_Position`) -> `PhysClass::Get_Position`
  (staging/wwphys/phys.h:315) -> `DecorationPhysClass::Get_Transform`
  (staging/wwphys/decophys.cpp:112, `assert(Model); return Model->Get_Transform();`). The assert
  compiles out in release, so this is a read near address 0. If that one were skipped, the per-frame
  paths listed below would dereference the same NULL `Model` again.
* **No retail campaign flow reaches it.** All seven cinematic files that name a missing model are
  dead content (see the reachability column). The shipped PC game would crash identically on
  them, which supports the view that they were never run.
* **Fix**: `PhysClass::Set_Model_By_Name` now keeps the current model when the requested name has
  no prototype. `Generic_Cinematic` (definition 82090001) uses `DynamicAnimPhysDef` 327820007, whose
  `ModelName` is `null`. That is the builtin `NullPrototypeClass` (staging/ww3d2/assetmgr.cpp:1598),
  which cannot fail. A cinematic `Create_Object` with a missing model therefore keeps an invisible
  `Null3DObjClass`, and every model-dependent step later works against a valid object. That object
  has identity bone transforms, no sub-objects, an empty bounding box and no-op `Set_Animation`.

## The 13 missing models and how each slot is used

Extracted from the retail mission MIX archives by `Create_Object` slot. "Hosts" means another slot
is attached to a bone of this slot.

| Model | Mission / file | Slot | Later use of the slot | Reachable in retail flow |
|---|---|---|---|---|
| `C_havoc` | M01 `xg_ev5.txt` | 5 | `Play_Animation S_A_Human.XG_EV5_troop` (loop), **attached** to slot 4 bone `Troop_L`, destroyed at -658 | No. No Mission01 source or level binding launches it ([M01_READINESS](M01_READINESS.md)) |
| `X2C_Harness_1` | M02 `x2c_mammothdlv.txt` | 1 | `Play_Animation X2C_Harness_1.X2C_Harness_1` (missing anim), destroyed at -1100 | No, dead content ([M02_READINESS](M02_READINESS.md)) |
| `X2C_Harness_2` | M02 `x2c_mammothdlv.txt` | 2 | `Play_Animation X2C_Harness_2.X2C_Harness_2` (missing), destroyed at -1100 | No |
| `X2C_trnspt_1` | M02 `x2c_mammothdlv.txt` | 3 | `Play_Animation X2C_trnspt_1.X2C_trnspt_1` (missing); **hosts** slot 4 (`V_GDI_Trnspt`) on `Bn_Trajectory`; destroyed at -1680 | No |
| `X2C_Hover_Traj` | M02 `x2c_mammothdlv.txt` | 5 | `X2C_Hover_Traj.X2C_Hover_A/B/C` (missing); **hosts** slot 6 (`V_GDI_VCraft`) on `Bn_Trajectory`; destroyed at -1940 | No |
| `X2C_MMTank_Traj` | M02 `x2c_mammothdlv.txt` | 7 | `X2C_MMTank_A/B/C` (missing); **hosts** `Create_Real_Object 8 v_gdi_mammoth` at `BN_Trajectory` and `Attach_to_bone 8,7` | No |
| `v_gdi_mammoth` | M02 `x2c_mammothdlv.txt` | 8 | Same slot first gets `Create_Real_Object` (the slot id is overwritten); **attached** to slot 7, detached at -2200 | No |
| `X2C_trnspt_2` | M02 `x2c_mammothdlv.txt` | 9 | `X2C_trnspt_2.X2C_trnspt_2` (missing); **hosts** slot 10 (`V_GDI_Trnspt`); destroyed at -1680 | No |
| `X2C_Bottom` | M02 `x2c_mammothdlv.txt` | 11 | `X2C_Bottom.X2C_Bottom` (missing), destroyed at -1000 | No |
| `XG_DEMOCAM` | M02 `xg_democam.txt` | 0 | `XG_DEMOCAM.XG_DEMOCAM` (missing), then **`Control_Camera 0`** (camera host) | No. Only `MissionDemo.cpp:64` (ATI video-card demo) attaches it, and nothing binds that |
| `c_havoc` | M03 `x3_finale.txt` | 1 | `s_a_human.x3_hv0-360` (loop), `x3_hv440-625` (once, so destroy-after-animation applies) | No. Only `objects.ddb` "Finale Controller" names it, and `M03_Outro_Cinematic` is unbound ([M03_READINESS](M03_READINESS.md)) |
| `cx_ag_havoc` | M03 `x3_intro.txt` | 1 | Sub-object animations on `cx_havoc_head/handL/handR`, then `s_a_human.x3_M_havoc1..4` | No. No level, preset or cinematic data references `x3_intro.txt` |
| `v_nod c-130` | M03 `x3_intro.txt` | 5 | `v_nod c-130.x3_c130_a` (missing), destroyed at -1069 | No (same file) |
| `C_havoc` | M08 `x8a_midtro_bak.txt` | 1 | `s_a_head.x8b_hav_facial` on sub-object `c_havoc_head`, `H_A_X8A_HAVOC0/1/2`, `H_A_X8A_MLoop` (missing), destroyed at -1728 | No. This is the `_bak` copy; the live `x8a_midtro.txt` does not use it |
| `X11E_Temp` | M11 `x11e_escape.txt` | 1 | Destroyed at -120. No other use | No. Mission11 drives the cryo escape directly (`Mission11.cpp:3386-3409`). The only data hit is the `x11e_escape.wav` sound preset |

Reachability was cross-checked by a raw scan of every non-asset entry (`.ldd/.lsd/.ddb/.dep`)
in every retail archive for the seven file names. Only `objects.ddb` -> `X3_Finale.txt` matched,
and that preset's creator is unbound.

## Path trace for a model-less object (before -> after this patch)

Object: `CinematicGameObj` (ArmedGameObj) with a `DynamicAnimPhysClass` (DecorationPhys ->
DynamicPhys -> PhysClass) in collision group WORLD.

| Path | Code | Before (Model == NULL) | After (keeps builtin `null`) |
|---|---|---|---|
| Create, `Set_Model` | `PhysClass::Set_Model_By_Name` (staging/wwphys/phys.cpp:206) | `Set_Model(NULL)`, old null model released | Replacement skipped; bounded Vita log `A4 Phys Set_Model_By_Name missing model kept current` |
| `Set_Facing` / `Get_Position` / `Get_Facing` | decophys.cpp:112 `Get_Transform` | **NULL deref (first crash)** | Null object transform |
| `Set_Transform`, host-bone teleport | decophys.cpp:118, physicalgameobj.cpp:669 | **NULL deref** | OK |
| Dirty-cull update (every frame, via `Add_To_Dirty_Cull_List`) | pscene.cpp:1107 -> `PhysClass::Update_Cull_Box` (phys.h:759) | Guarded (`if (Model)`) | OK |
| Vis ID (culling) | dynamicphys.cpp:151 `Internal_Update_Visibility_Status` | **NULL deref** | Empty box |
| Lighting cache / sun status | phys.cpp:349, 373 | **NULL deref** when rendered | OK |
| Render / Vis_Render | phys.cpp `Render`, `Vis_Render` | Guarded | Null renders nothing |
| Shadow blob | phys.cpp:290 (`PhysClass`); DecorationPhys override returns cached box | Deco safe | OK |
| Collision: AABox/OBBox intersect, ray/box casts | decophys.cpp:137-183 | **NULL deref** for any query that reaches the object (group WORLD) | Null has no geometry, so nothing collides |
| Physics timestep | dynamicanimphys.cpp:137 -> animcollisionmanager.cpp:1073 / 1166 `Parent.Peek_Model()->Set_Animation` | **NULL deref** once an animation runs | No-op `Set_Animation` on null |
| `Play_Animation` (main path) | scriptcommands.cpp:841+ (DynamicAnimPhys anim manager; missing anim -> `Get_HAnim` NULL) | Timestep NULL deref | Missing anim: idle. Present anim: frames advance, and `DestroyAfterAnimation` deletes the object at its target (same as with a real model) |
| `Play_Animation` with sub-object | scriptcommands.cpp:829 `SCRIPT_PTR_CHECK(model)` | Guarded (A36 patch) | Null has no sub-objects, so skipped |
| `PhysicalGameObj::Set_Animation{,_Frame}` (non-cinematic objects) | physicalgameobj.cpp:883 / 922 | **NULL deref** (`Peek_Model()->Get_Name()` for a bare name, and `SimpleAnimControlClass::Update` -> `AnimChannelClass::Update_Model(NULL)`) | **New guard**: returns before creating the anim control |
| `Attach_to_Bone` with this slot as host | scriptcommands.cpp:2485 `SCRIPT_PTR_CHECK(host model)`; physicalgameobj.cpp:840 | NULL host model: no-op (A36 patch) | Null bone index 0 is the root, so the child follows the host transform (the trajectory animation is missing, so it does not move along it) |
| `Create_Real_Object` / `Create_Object_At_Bone` on this host | scriptcommands.cpp:557 | Returns NULL (A36 patch) | Created at the host transform |
| `Control_Camera` (`XG_DEMOCAM`) | scriptcommands.cpp:1403 -> ccamera.cpp:619 `Get_Bone_Transform("CAMERA")` | NULL host model, camera not hosted. HUD and controls still toggled | Camera at the controller transform |
| `Play_Audio` / `Shake_Camera` / `Create_Explosion` at bone | scriptcommands.cpp `Create_3D_Sound_At_Bone`, `Get_Bone_Position`:343, `Create_Explosion_At_Bone` | Guarded (A36 patch) | Root transform |
| Muzzle bones | armedgameobj.cpp:483 `Init_Muzzle_Bones` (Init and `On_Post_Load`) | NULL deref on post-load | OK (bones 0) |
| Cinematic sound | cinematicgameobj.cpp:301 `Set_Sound` | Unreached: `Generic_Cinematic` `SoundDefID` = 0 | Unchanged |
| Network export | physicalgameobj.cpp:1136 `Export_Rare` | NULL deref (exported only when there are remote clients) | OK |
| Save | phys.cpp:546-554 | NULL model -> `csave.Report_Error()`, so the save fails | Null model chunk saved |
| Destroy | `~CinematicGameObj` -> `Remove_From_Dirty_Cull_List`; `PhysClass::~PhysClass` releases `Model` if set | Safe | Safe |

The Vita-only code was also checked. It reads `Peek_Model()` in a31_vita_runtime.cpp:413/3315,
a30_world_runtime.cpp:396 and the renderer statistics, and every one of those reads is NULL-checked.

## Guards added

1. `port/patches/wwphys-a38-missing-model-keeps-current.patch` (wwphys stage), staged
   `staging/wwphys/phys.cpp:228-245`. When `Create_Render_Obj` and the prepared-model pool both
   return NULL and the object already has a model, the replacement is skipped. A bounded Vita log
   (first 16) records it. If there is no current model, the original `Set_Model(NULL)` path is
   kept unchanged.
2. `port/patches/combat-a38-modelless-animation-guard.patch` (combat stage), staged
   `staging/combat/physicalgameobj.cpp:885-890` (`Set_Animation`) and `:924-928`
   (`Set_Animation_Frame`). A model-less object now returns before the anim control is created.
   This closes residual 1 of [SCRIPT_COMMANDS_NULL_SAFETY.md](SCRIPT_COMMANDS_NULL_SAFETY.md).

Both are registered at the end of `tools/stage_sources.sh`, before the PersistFactory alias
refresh, with pre/post sha256 anchors. No earlier anchor moved:

| File | Pre | Post |
|---|---|---|
| `wwphys/phys.cpp` | `3c7b9274…d6f2` | `5c83199a…4aa4` |
| `combat/physicalgameobj.cpp` | `6fbbc088…b3dd` | `ef50f329…c5ad` |

Validation: `bash tools/stage_sources.sh` (temporary upstream symlink, restored) exits 0 with zero
fuzz, and the patch inventory passes with 572 ordered patches. The only staging changes are the two
target files and `PATCH_INVENTORY.json`. `arm-vita-eabi-g++ -fsyntax-only` with the
`vita-fast-candidate` flags exits 0 for both files.

## Residual risk

* **Different visuals, not PC parity.** These cinematics would crash the PC game. On the Vita a
  model-less slot is now invisible, and anything attached to it sits at the slot's root transform,
  because the trajectory animation is missing too. The content is dead, so no campaign flow should
  show this.
* **Policy applies to every caller.** All `Set_Model_By_Name` callers now keep the old model when
  the new name is missing. Those callers are scripts' `Set_Model`, `SoldierGameObj::Set_Model`,
  C4 ammo models and the network `Import_Rare` model name. Before, each of these left a NULL model
  and crashed soon afterwards. A script that swaps in a missing model now keeps showing the
  previous model (for example an intact building instead of a destroyed variant).
* **Model-less objects can still be created at Init.** A definition whose PhysDef model is missing
  is created with no model (`PhysClass::Init`, "FATAL ERROR" log). The DecorationPhys, AnimCollision,
  Vis-ID and lighting dereferences above still apply to such an object. No campaign preset is known
  to do this; the asset closure covers preset models (`dep_w3d`/`hlod_child`) separately. Those
  sites were not guarded, because a transform fallback would need new per-object state.
* **Lost `Animation_Complete` events on model-less objects.** A model-less
  soldier or simple object no longer receives an `Animation_Complete` from
  `PhysicalGameObj::Set_Animation`. Before this patch the same call crashed for
  `SimpleAnimControlClass`.
* Not compiled into a packaged artifact. Next gate: a candidate build, then a direct-entry Vita3K run of a dead cinematic, for
  example by attaching `Test_Cinematic` with `XG_DemoCam.txt` from a debug hook. Look for the new
  log line and no crash.
