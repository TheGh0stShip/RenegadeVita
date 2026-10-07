# Rejected-load discard safety (F4) — 2026-10-07

Evidence class: staged-source review, `arm-vita-eabi-g++ -fsyntax-only` with the
`vita-fast-candidate` compile flags, and a host ASan/UBSan fault-injection test.
No Vita build, Vita3K run or hardware run backs this report.

## Defect

`SaveLoadSystemClass::Load` remaps every pointer token and then, when the load is
rejected, calls `Discard_Post_Load_Callbacks()` instead of `On_Post_Load()`. The
same discard runs in `combatgmode.cpp` and twice in `a31_vita_runtime.cpp`, including
the campaign-source mismatch path, which discards after a load that succeeded. Some
objects store a remapped pointer during `Load` and only link it into the target in
`On_Post_Load`. When the partial state is destroyed after a discard:

- **`ReferencerClass` (`GameObjReference`, including `Objective::Object`, about forty
  members):** `~ReferencerClass` searches the target's referencer list for itself. It
  is not in that list, so it reads `NULL->TargetReferencerListNext`. If the target was
  freed first, the target's destructor could not clear the referencer, so the search
  reads freed memory.
- **`MoveablePhysClass::Carrier` (riders on elevators and doors):** the carrier's
  `RiderManagerClass` never received the rider. If the carrier is destroyed first,
  `~MoveablePhysClass -> Link_To_Carrier(NULL)` makes a virtual call through a freed
  carrier.
- **`ScriptableGameObj` observers:** NULL entries (registered-NULL scripts, or
  unresolved remaps, which are themselves a cause of rejection) are purged only in
  `On_Post_Load`. `Remove_All_Observers -> Remove_Observer(NULL)` then calls
  `NULL->Detach`.

## Fix (zero-fuzz staging patches, applied after every existing anchor)

| Patch | Change |
|---|---|
| `wwsaveload-a37-rejected-load-discard-hook.patch` | `PostLoadableClass::On_Post_Load_Discarded()` (virtual, no-op by default). `Discard_Post_Load_Callbacks` calls it before clearing the registration flag, while every registered object is still alive. |
| `combat-a37-rejected-load-discard-unlink.patch` | `ReferencerClass` override sets `ReferenceTarget = NULL` and `TargetReferencerListNext = NULL`. This is exact because a registered referencer is unlinked by construction. The override never dereferences the target. `ScriptableGameObj` override purges NULL observers, the same loop as `On_Post_Load`, and runs no scripts and no `Created` or `Attach`. |
| `wwphys-a37-rejected-load-carrier-discard.patch` | `MoveablePhysClass` override drops `Carrier`/`CarrierSubObject` without calling `Link_To_Carrier`. |

Accepted loads are unchanged: `Post_Load_Processing` never calls the hook.

## PostLoadable inventory (37 registration sites)

| Class (`On_Post_Load` linking) | Discard-safe? |
|---|---|
| `ReferencerClass` / `RefCountedReferencerClass` (relinks into the target list) | **Fixed** |
| `MoveablePhysClass` and subclasses Phys3/RigidBody/Vehicle/Tracked/VTOL/Human (`Link_To_Carrier`) | **Fixed** |
| `ScriptableGameObj` (purges NULL observers) | **Fixed** |
| `PhysicalGameObj` (`PhysObj->Set_Observer(this)`) | Safe. `PhysClass::Observer` is saved and remapped to the same owner, so it matches the original post-load state. |
| `BulletClass` (`Projectile->Set_Observer`) | Safe. The destructor clears the observer. |
| `SmartGameObj` (`Register_Listener`, `Set_Player_Data`, stealth effect) | Safe. `Remove_From_Scene` checks `m_Scene`. The PlayerData pair is already remapped mutually. |
| `SoldierGameObj` (weapon sub-object, anim control, back gun, speech) | Safe. `Remove_Sub_Object` tolerates a missing child. Nothing to unlink. |
| `VehicleGameObj`, `TransitionGameObj` (transitions, wheel effects, turret bones) | Safe. The destructors tolerate none being created. |
| Sakura/Mendoza/Raveshaw bosses, `CinematicGameObj`, `ArmedGameObj`, `PowerUpGameObj`, `SimpleGameObj`, `BeaconGameObj`, `BuildingAggregateClass` | Safe. These only create or initialise owned state that the destructors tolerate as absent. |
| Static, StaticAnim, Decoration, DynamicAnim, RenderObj, Light and Dynamic phys; `PathSolveClass`; `WaypathClass` | Safe. Cull box, model user data, projector and path init only. No cross-object list membership. |
| Subsystems: `CombatSaveLoad`, Phys static/dynamic, `MapMgr`, `EvaSettings` | Safe. Global refresh only. |

## Test

`python3 tools/test_rejected_load_discard.py`: 6/6 pass.

- The host ASan/UBSan probe (`tools/host_rejected_load_discard_test.cpp`) compiles the
  real staged `saveload.cpp`, `pointerremap.cpp`, `chunkio.cpp`, `persistfactory.cpp`
  and `reflist.cpp`. It saves a linked referencer, reloads it through
  `SaveLoadSystemClass::Load`, and forces rejection after the remap. It then destroys
  the partial state in both orders. Accepted loads still relink, and a later accepted
  load works after a discard.
- Negative control: the forked pre-fix state crashes at `reflist.cpp` with UBSan
  "member access within null pointer". With the hook call removed from `saveload.cpp`,
  the probe fails with ASan heap-use-after-free in `ReferencerClass::operator=`.
- Source-contract checks cover the hook order and the three overrides, including that
  the destructor paths they protect are present.

## Residual risk

- A `ScriptableGameObj` whose own `Load` fails never registers (`if (loaded)`), so a
  NULL observer in that same object is not purged. This needs both a malformed object
  chunk and a NULL script in the same object.
- The discard still assumes every registered object is alive (an a36 design invariant).
  The hook adds a virtual call to that existing assumption.
- `MoveablePhysClass` and `ScriptableGameObj` are covered by source-contract checks
  only. They are not in the host probe because the dependency trees are wwphys and
  combat.
- Not physically validated. This needs a Vita build and a forced rejected-load repro.
