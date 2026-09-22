# Dev152: WW3D per-instance creation is the M13 stall

The rejected Dev151 loading-time render-object pre-create/release was removed.
Dev152 adds bounded, full-port-only timing to original
`PhysClass::Set_Model_By_Name`, leaving gameplay and demo behavior unchanged.

In the isolated Vita3K/OpenGL M13 route, original
`Set_Model("X00_AG_Explode")` took 6,083,621 us:

| Operation | Process-clock time |
| --- | ---: |
| `WW3DAssetManager::Create_Render_Obj` | 6,083,581 us |
| `PhysClass::Set_Model` scene installation | 39 us |
| Local reference release | 1 us |

The original asset-manager `Create_Render_Obj` locates a prototype and calls
`proto->Create()`. For HLOD prototypes, `HLodClass` recursively creates LOD
and aggregate render objects. The expensive nested operation is not yet
identified; changing cache, loader, or instance sharing now would be
speculative. No performance or A/V sync improvement is accepted.

Evidence: managed AppData `campaign-dev152-physmodel-m13-1/`, matching
SELF SHA-256
`ce01e50e2cf93e273cacfdb91ab3005a9b29f2c94405c47d56964dbabf1307f3`;
asset-free VPK SHA-256
`4eabe813bcafe663a5102212b33b5f4a044cf8040f1896da7da8334117c1327e`.
ARM SELF/VPK and 191 ordered patches pass. Vita3K timed out unassessed;
physical Vita, actor sequencing, audio alignment, and 60 FPS remain open.

Next: time prototype lookup/load/create and nested calls with bounded logs,
then fix the repeated inner work and rerun the same M13 route plus M00.
