# Original decal restoration dependencies

Source review on 2026-10-03 confirms that native decal presentation remains
unfinished. Original explosion code generates configured decals through
PhysicsScene::Create_Decal; mesh ownership creates rigid or skinned decal meshes.
This is an active original effect producer, not merely an unused renderer.

Source correction now restores the original traversal/distance gate, list
prepend/flush/reset and rigid/skinned rendering bodies on Vita. The original
DX8MeshRenderer list owner moved from the optional frontend compatibility object
to the shared native renderer boundary, with initialized camera/list fields.
Native flush sets its camera before consuming the list. Base meshes continue
to submit through the existing native boundary. Headless host draw skips and
unsupported additional procedural passes remain explicit. The source patch
is hash anchored after dazzle restoration and replays with zero fuzz.
Four combined restoration checks pass, including exact original decal draw-body
comparisons. Active staging, compilation and native execution are unchanged.
The depth-bias dependency below remains unresolved; effect closure is not claimed.

Four connected omissions were found (first three now corrected in source):

1. Native MeshClass::Render reports populated decal meshes unsupported instead
   of queueing them. Original traversal excludes additional-passes-only draws,
   transforms the parent bounding sphere to camera space and applies the
   original decal rejection distance before queueing.
2. Native WW3D::Flush skips TheDX8MeshRenderer.Flush. The linked compatibility
   object has only constructor, destructor and invalidation definitions; it
   does not provide the original decal queue/flush methods. Original queueing
   prepends through DecalMeshClass::Set_Next_Visible. Original flush renders
   decals after mesh categories and before delayed procedural rigid passes,
   then clears the queue and unbinds dynamic buffers.
3. Both rigid and skinned decal Render methods return unsupported on the native
   build. Their original bodies use supported dynamic XYZNDUV2 geometry with
   per-run texture, material and shader state. Rigid vertices use the parent
   transform; skinned vertices are deformed into world space, with sorted skins
   rejected. Original material/index-run and rejection semantics must survive.
4. Original Render_Decal_Meshes sets D3DRS_ZBIAS to 8 and resets it to zero.
   Native Apply_DX8_Render_State has no matching case and its unsupported-state
   path returns true after a diagnostic. Successful return therefore does not
   prove depth bias was applied. A measured, documented platform mapping and
   reset/lifecycle handling are needed; arbitrary polygon offset is unverified.

The existing decal release-range patch addresses storage lifetime separately
and does not close these presentation dependencies. Dazzle restoration also
does not restore decals. No per-mission decal count, successful native draw,
depth placement, physical pixels or completion is claimed.

Next correction must preserve the original mesh queue ownership and traversal
gates, parent transforms/deformation, shader/material runs, depth placement,
queue clearing and shutdown lifetime. Source/temporary replay validation is
allowed; compilation and launch remain on hold.
