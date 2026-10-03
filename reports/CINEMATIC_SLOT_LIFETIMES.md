# Cinematic ordering and slot lifetime leads — 2026-10-03

The continuation traces all 166 cinematic candidates reached by the prior
Tutorial/M13/M01 authored-binding receipts. It corrects a discovery error:
Send_Custom arguments are destination, event type, parameter. The old inventory
reported the parameter as the event type. Both the inventory and new typed
tracer now retain the original roles.

The tracer is read-only source/data evidence. It does not execute the game,
prove successful creation or lookup, or establish native mission progression.
No C++ build, launch, installation, device action or retail/save change occurred.

## Original ownership and chronology

Test_Cinematic keeps 40 numeric object-ID slots. Creation writes a slot only
after success. Failed creation can leave a previous ID intact. Move_Slot
transfers the ID and clears the old slot; moving a slot to itself does nothing.
Destroy_Object requests deletion without clearing the numeric slot. Custom
events can fill empty slots from outside the control file.

Control timestamps are stored as 32-bit floats. Negative tokens become frames
divided by 30; positive tokens represent seconds. The tracer explicitly rounds
to float32 and preserves source order when normalized timestamps are equal.
This models the original stored ordering, not timer delivery, frame pacing or
the Vita callback time budget.

PrimaryKilled discards commands at or below 999000 seconds and dispatches the
remaining tail. The ordinary scheduler uses that boundary to end a sequence.
The tail therefore begins with an unknown death-time slot snapshot. It is
traced separately; the normal timeline's ending slots are never substituted
for that unknown state. Boundary commands are retained separately.

The parser follows original narrow parameter/quote handling, command-title
prefix matching, atoi numeric-prefix/zero behavior and the 199-byte text-line
limit. Overflow/nonfinite unsupported values remain findings. The source
loader ignores a timestamp-only line and treats unrecognized decorative
header text as unknown commands; those remain distinct from missing assets.

## Inspected scope

Input archive and binding-receipt identities match
[authored bindings](AUTHORED_MISSION_BINDINGS.md). Each control-file candidate
is rehashed before tracing; changes cause refusal. Detailed metadata remains
private under build/dev208-cinematic-slots-20261003.

| Map | Text candidates | Normal command records | Primary-killed tail records | Typed slot uses | Normal uses without a local producer |
|---|---:|---:|---:|---:|---:|
| Tutorial | 1 | 53 | 10 | 61 | 0 |
| M13 / Scorpion Hunters | 18 | 857 | 72 | 884 | 2 |
| M01 | 147 | 1816 | 88 | 1703 | 2 |

The M01 normal count includes two decorative unknown-command records; one
timestamp-only line is ignored. No inspected active line exceeded the original
199-byte limit. No boundary records or unchecked out-of-range host-slot uses
were found in this scope. One M01 negative object slot is skipped by the
original guard. Metadata presence never proves a live object.

The 170 tail references without local producers have unknown primary-death
snapshots. They are not 170 missing-object defects. The four normal references
are retained with source time, slot role and external-fill uncertainty:

- M13 x00_intro.txt:203 targets slot 13 at time zero; its local creation is
  later at line 201, 43 seconds. File-line order cannot justify treating it as
  already created.
- M13 x00_intro.txt:455 targets slot 11 without a prior local producer.
- M01 x01d_c130troopdrop.txt:39 uses host slot 2 without a local producer.
- M01 x1z_finale.txt:139 attaches to slot 8 without a local producer.

No external-fill path or runtime failure is established by these four leads.

## Findings that change the next investigation

The unlocated M13 MX0_GDITROOPER4_HIT6 conversation has a narrower lifetime
question. Slot 13 is attempted at x00_intro.txt:201 (43 seconds), then receives
M00_Cinematic_Kill_Object_DAY at line 205 (about 44.667 seconds). That script's
Created callback in original Test_DAY.cpp immediately calls Apply_Damage.
The generic conversation attachment follows at line 468 (about 48.033 seconds).
Successful creation, damage/death processing, remaining object membership and
conversation behavior all need runtime evidence. The absent conversation name
remains a conditional lead; this does not establish an audible omission or
justify an invented replacement.

M01 x1z_finale.txt:238/239 use a four-argument Play_Audio layout. Original
Command_Play_Audio consumes preset name, optional host slot, bone name. Both
lines therefore request preset name 14; the following nonnumeric token becomes
host slot 0, the third token becomes the bone name, and the fourth is ignored.
No definition named 14 was found in the inspected objects.ddb. This is an
authored data/source-signature mismatch lead, not verified retail-executable
behavior or a newly demonstrated port-only regression. Retail files and the
shared command implementation remain unchanged.

All ten literal cinematic custom-event destinations in M13/M01 are present in
the inspected serialized GameObj namespace. Event types and literal custom
parameters are kept separate from object IDs. Runtime delivery, live membership
and observer behavior remain unverified. The cross-map M08 helicopter callback
and other source-level missing-ID leads are outside this textual destination
check and remain open.

## Reproduction and validation

```sh
python3 -m tools.audit_cinematic_slots \
  --data /absolute/path/to/user-owned/retail/Data \
  --bindings-directory build/dev208-authored-bindings-20261003 \
  --output-directory build/dev208-cinematic-slots-20261003
python3 -m unittest tools.test_cinematic_slots tools.test_mission_text_routes \
  tools.test_mission_conversations tools.test_mission_content_bindings \
  tools.test_m13_level_owners tools.test_deep_content_audit \
  tools.test_requested_mission_owner_contract tools.test_m13_mission_inventory \
  tools.test_m13_script_coverage tools.test_script_provider_contract
```

117 focused Python/source checks pass, including 24 new counterexamples.
They cover float32 ties/boundaries,
negative frame tokens, separate unknown tail snapshots, creation failures,
move/clear/self-move, deferred deletion candidates, callback effects, optional
hosts/restoration, typed custom arguments/zero-ID sentinels, original quote/atoi/header behavior,
line truncation, changed archive/member hashes and private output enforcement.
Both build entry points select the suite for future builds. Full focused and
publication validation receipts are retained in the current build state. The
32 publication guards, 24-document validation and syntax/diff checks pass.

| Private receipt | SHA-256 |
|---|---|
| m00_tutorial-cinematic-slots.json | `3dd064dff8758da9d0875e703762431527f07031e5ed4dee134ac2d8290189bb` |
| m13-cinematic-slots.json | `48f1a6a515c9ef7cdf5900e90ef4aa6a8147a8108f0d406c041287a74df9e594` |
| m01-cinematic-slots.json | `f3fec98fdbb1386f664b3c2903c0937e8ad6f3c68ceb7fc906a51036f756e9c7` |

Native is little-endian ARMv7-A/Cortex-A9 ILP32. The host tool uses explicit
32-bit numeric boundaries and never treats IDs as pointers. It validates no
target floating-point ABI or physical behavior. Script effect calls remain
source leads across callbacks, not a complete inter-script dataflow proof.
Computed content, external IDs, global voice references, voiced PC controls,
compiled registration and full native/physical mission coverage remain open.
