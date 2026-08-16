# A3.0 / A3.1 interactive render comparison

## A3.1.3 physical evidence

The accepted A3.1.3 lifecycle ran 1,354 interactive frames and completed cleanly, but recorded zero mesh, vertex, and triangle submissions. Its `CombatManager::Render()` call did not execute the original `GameModeManager::Render()` PhysicsScene pre/post-render envelope.

## First causal boundary

`PhysicsSceneClass::Customized_Render()` consumes its visible static and dynamic lists. Those lists are populated by `PhysicsSceneClass::Pre_Render_Processing(*COMBAT_CAMERA)` and released by `Post_Render_Processing()`. A3.0 called that original envelope; A3.1.3 did not.

## A3.1.4 host-equivalent first frame

| state | A3.0 physical | A3.1.4 host-equivalent |
| --- | ---: | ---: |
| static objects | 495 | 495 |
| dynamic objects | n/a overview | 24 |
| static lights | 192 | 192 |
| visibility table | 1,684 / 347 | 1,684 / 347 |
| first-frame meshes | nonzero | 205 |
| first-frame vertices | nonzero | 12,426 |
| first-frame triangles | nonzero | 8,661 |
| rejected / unsupported | 0 / 0 | 0 / 0 |

A3.1.4 uses the original Combat scene, CCamera, cGod Commando, PhysicsScene, `CombatManager::Render`, and WW3D path. Projectors and procedural transition materials remain explicit unavailable renderer capabilities; their original subsystem boundaries suppress those passes without suppressing base scene traversal.
