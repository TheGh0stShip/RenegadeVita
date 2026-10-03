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

## Authored metadata sweep

The read-only `tools.audit_script_zones` scanner decodes original microchunk
widths explicitly: one-byte booleans, signed32 zone type and15 little-endian
float32 OBBox fields (basis, center, extent). It follows persisted factory
containers, retains object/definition identities and applies level definition
overlays over objects.ddb. Missing fields remain unknown; duplicate fields,
incorrect widths and nonfinite bounds are rejected. Negative extents are
retained as findings rather than silently corrected.

| Map | Zone records | Star-only | All-smart | Unknown filters | Bounds findings |
| --- | ---: | ---: | ---: | ---: | ---: |
| Tutorial |31|31|0|0|0|
| M13 / Scorpion Hunters |16|16|0|0|0|
| M01 |138|130|8|0|0|

These counts are serialized zone records, not executed callbacks or verified
trigger coverage. The scanner records basis dot-product error leads at
tolerance0.001; it does not prove orthonormal basis validity, actual
physics broadphase gathering, spawn positions or saved reference remapping.
Zero bounds findings means no nonfinite values or negative extents in the
decoded scope, not proof that a zone has valid placement or nonzero volume.

Thirty-three focused Python checks pass, including ten synthetic decoder/container
counterexamples and existing level-owner/binding checks. Detailed rows remain
private in `build/script-zones-20261003.json`, with map/member/global-definition
and original source hashes. Reproduce with:
`python3 -m tools.audit_script_zones --data <retail-Data> --output build/script-zones.json`.
No data mutation, asset extraction for distribution, build or launch occurred.

The deeper scan adds zero-extent and basis orthogonality leads without changing
retail bounds. All three maps retain zero findings at the declared0.001 dot
error tolerance and have no zero extents. Maximum observed dot error is about
0.000061. This is not a runtime collision accuracy measurement. Synthetic
tests reject ambiguous factory variables and ignore unanchored variable bytes
outside a persisted factory.

M01's eight all-smart zone records resolve to seven attached script names (the
barn exit script appears twice). Map/global definition hashes match the authored
binding receipt used for that linkage. Original source shows vehicle identity
gates in tunnel/tank-blocking cases and NPC identity gates in GDI-base/barn exits;
warroom/MCT cases involve escort state and named actors. Preserve all-smart
collection rather than globally forcing star-only gathering. The gunboat
hovercraft-zone script's callbacks are commented out in original source; an
attached name alone is not an active Entered handler or evidence of a lost port
callback. No commented retail behavior was re-enabled.

Valid synthetic factory cases now verify unsigned32 object/definition IDs,
oriented-box field layout, false star-only filters and signed zone types through
the complete scanner route. Duplicate base-object identity fields are rejected
before the shared inventory reader can silently select the last value. A fresh
read-only retail scan retains the counts and zero findings above. These checks
validate metadata interpretation, not native loading or callback execution.

## Saved membership reference ownership

`GameObjReference` is the original `ReferencerClass`, not a numeric level-object
ID wrapper. Its saved target is the old pointer token for the object's
`ReferenceableClass<ScriptableGameObj>` base. That base registers its old token
against the newly loaded base address. Referencer Load requests pointer remapping
and registers a post-load callback. After remapping, On_Post_Load obtains the
ScriptableGameObj and uses the original assignment operator to relink the
referencer into the target's reference list. Object destruction clears that list's
references; this explains a later null membership without a guaranteed Exited.

SaveLoadSystem Load processes and resets pointer-remap tables before optional
post-load callbacks. A missing token mapping sets the requested pointer to null;
the callback then leaves it null. Zone Think removes that null reference without
Exited. Missing remapping can therefore remove restored membership and permit a
later fresh Entered, while a correctly restored member suppresses duplicate entry.
Neither outcome is established by serialized zone bounds alone.

The native runtime waits for the original threaded load, resumes texture loading,
calls original Post_Load_Processing, and then Post_Load_Level/finalizes the level.
Original Referencer and PointerRemap source units remain selected through the
A31/A30 source chain. The registered combat pointer-token patch writes/reads
explicit uint32 targets and referenceable tokens while retaining remap requests
and post-load relinking. No missing relink step was found in this source review.

These tokens are separate from mission Find_Object IDs and must not be replaced
with those IDs. On native ARMv7 ILP32 a pointer token is four bytes. The current
save-side cast from an actual pointer to uint32 does not establish a safe LP64
host save identity: distinct host pointers can lose high bits and collide.
Host-only serialization limitations remain open; do not globally truncate live
pointers or treat host save success as native compatibility proof. Physical
checkpoint validation must retain matching artifacts and verify actor identity,
reference relinking, callback behavior and subsequent mission progression.
