# Original script-zone membership and callbacks

2026-10-03 source inspection; no compilation, launch or retail mutation.
Native mission/runtime gates remain0/10.

Native source selection reaches `Combat/scriptzone.cpp` through
`A31OriginalSources.cmake` and oriented-box point overlap in
`WWMath/colmathobbox.cpp` through the A30/A22 includes. This establishes owner
selection, not current linkage, correct ARM execution or callback delivery.

Original zone Think first calls ScriptableGameObj::Think, then returns when
there are no observers unless the zone is CTF. It processes prior members for
exit before gathering new entrants. The CheckStarsOnly definition selects the
original star list; otherwise the physics scene collects dynamic objects
overlapping the oriented box, then filters for SmartGameObj instances.
Both routes apply Inside_Me and duplicate membership checks. Mission scripts
can apply further player/type filters; source presence does not prove those
conditions hold for a particular entrant or vehicle.

Inside_Me requires a physical object and tests its position point against the
oriented box. Original overlap subtracts the box center, transpose-rotates by
the basis, and rejects a point only when an absolute local coordinate exceeds
its extent. Exact equality is inside. This is not a test that the full actor
hull fits inside the zone. Do not replace it with swept collision or a hull
containment rule while diagnosing missed callbacks.

Entered synchronously calls current observers, then adds the GameObjReference
to InsideList. An observer inspecting team membership during its own Entered
callback therefore does not yet see that newly added entry. Exited callbacks
run before reference removal when an existing actor moves outside. A null
reference is removed without Exited. Death/reference invalidation is not a
guaranteed zone-exit event. Existing callback iteration and actor lifetime
require runtime evidence; this review does not establish a new mutation bug.

Save persists bounding box, player type, parent/script state and non-null inside
references; Load reconstructs InsideList through the original GameObjReference
loader and remaps legacy player types. A save reload does not unconditionally
replay Entered for an already restored member. Correct pointer remapping, loaded
membership and mission script state must be verified together. The general
host pointer-token limitations apply; Linux LP64 save behavior cannot prove
native ARMv7 ILP32 retail compatibility.

GameObjManager gates ordinary Think on hibernation and cinematic-freeze flags.
Thus a placed zone, linked script and overlapping actor do not alone establish
that Think or a callback executes in the observed frame. Current timer/action/
conversation telemetry does not establish zone delivery.

Required validation remains: oriented and exact-boundary entry/exit, star-only
versus all-smart routes, actors/vehicles admitted by original scripts, one-shot
trigger resets, disabled/hibernating/frozen zones, actor removal without exit,
and checkpoint reload inside a zone. Retain exact zone/actor IDs and candidate
identity; distinguish overlap, callback attempts, resulting custom events and
visible mission progression. No replacement trigger logic was introduced.
