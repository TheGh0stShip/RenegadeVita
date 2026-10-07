# Campaign script pointer state (2026-10-07)

Scope: `DECLARE_SCRIPT` members of pointer type in `staging/scripts/`
Mission01-07, mission08, Mission09-11, MissionX0, Test_DLS and Toolkit*.cpp.
This is a host-only static audit. Nothing was built and nothing ran on a Vita.
It follows on from `SCRIPT_SAVE_STATE_GAPS.md`.

## Why pointer members matter

On a savegame load `Created()` does not run again, and
`ScriptImpClass::Load` restores only `SAVE_VARIABLE` members (see
`SCRIPT_SAVE_STATE_GAPS.md`). No script in scope registers a pointer. A
pointer member therefore holds indeterminate heap content after a load until
a callback assigns it again. Reading it before that point is a data abort on
Vita. On PC this often went unnoticed.

## Method (reproducible)

1. Pointer members were enumerated in two independent ways, and both gave the
   same 9 declarations in 8 classes:
   - a brace-depth parser over every `DECLARE_SCRIPT` body, reporting depth-1
     declarations that contain `*`;
   - `grep -nP "^(\t| {1,4})(?!//|/\*|\*)[^()\t]*\*[^()]*;"` over the
     in-scope files.
2. No in-scope file has a file-scope or `static` pointer, or a class outside
   `DECLARE_SCRIPT`. No string literal contains a brace, so the parser's
   depth count is sound.
3. Pointers passed as an `int` custom-event param (M03 `3000`/`5000`/`6300`)
   are synchronous stack exchanges and are never stored. They are already
   covered by `scripts-a35-host-m03-pointer-exchange.patch`.
4. Retail reachability was checked with `grep -a -l <ScriptName>` (also
   `-i`) over the host retail copy
   `local-builder/retail-host/Data/{M0*,M1*}.mix` and `always*.dat`.
   `DECLARE_SCRIPT` stringifies the name, so source literals do not reveal
   `Attach_Script` use. A literal search for each name found no dynamic
   attach.

## Findings

| Class (file:line) | Member | Assigned | Read after assignment | Retail binding | Status |
|---|---|---|---|---|---|
| `M09_KeyCard_Zone` (`Mission09.cpp:4342`) | `GameObject *mobius` | `Created` :4361, `Entered` :4387, `Action_Complete` :4466 | `Join_Conversation(mobius, ...)` in `Custom(COUNT)` :4428/4440/4454 and in `Action_Complete` | M09.mix | **Fixed** by `scripts-a36-m09-keycard-mobius-refetch.patch`, which re-fetches `Find_Object(2000010)` at the top of `Custom(COUNT)` (:4419). `Entered` and `Action_Complete` already re-fetch before they use it, and `Timer_Expired` does not use it. Every read is now preceded by a fresh fetch. |
| `M09_Elevator_All_Zone` (`Mission09.cpp:3291`) | `GameObject *mobius` | `Created` :3304 | never | M09.mix | Dead store, so there is no hazard. No patch. |
| `M09_Elevator_All_Controller` (`Mission09.cpp:3335`) | `GameObject *mobius` | `Created` :3368 | never. `Custom` uses `Find_Object(2000010)` inline. | M09.mix | Dead store, so there is no hazard. No patch. |
| `M10_Elevator_All_Controller` (`Mission03.cpp:6920`) | `GameObject *mobius` | never | never | M03.mix | Unused, so there is no hazard. No patch. |
| `M06_Clear_For_Mendoza` (`Mission06.cpp:5629`) | `const char *anim` | never | never | M06.mix | Unused, so there is no hazard. No patch. |
| `M00_Debug_Text_File_RMV` (`Toolkit.cpp:77-78`) | `const char *filename, *desc`, `FILE *file` | `Created` (`Get_Parameter`, `fopen`) | `fprintf` in `Custom`, `Damaged`, `Enemy_Seen`, `Action_Complete`, `Killed`. `fclose` in `Destroyed`. | none (not in any retail M*.mix or always*.dat, and no `Attach_Script` literal) | Not on a campaign path. This is a real hazard if the script is ever attached: after a load `file`/`desc` are stale, and `fopen` is unchecked, so a relative `DebugLog.txt` that fails to open passes NULL to `fprintf` even without a load. `start_time` is never initialised (an original bug). Documented only. |
| `M00_Activate_Weapon_At_Object_On_Frame_RMV` (`Toolkit.cpp:161`) | `GameObject *target` | `Created` | `Get_Position(target)` in `Timer_Expired` | n/a | Compiled out (`#if 0` :151-301). |
| `M00_Activate_Weapon_At_Object_On_Timer_RMV` (`Toolkit.cpp:201`) | `GameObject *target` | `Created` | `Get_Position(target)` in `Timer_Expired` | n/a | Compiled out (`#if 0` :151-301). |

**Result:** `M09_KeyCard_Zone` is the only campaign-reachable pointer member
that is read after save/load without a re-fetch, and it is already fixed. No
other in-scope script dereferences a stored pointer, so this audit adds no new
`scripts-*` patch.

## Outside the stated scope (same scan, for later)

The other `staging/scripts/*.cpp` units hold the pointer members below. None
of them is bound in retail M*.mix or always*.dat (case-insensitive grep), so
none is on a campaign path today:
`DrMobius.cpp:42 Dr_Mobius_Script::CurrentLeader`,
`GroupScript.cpp:47 MXX_Group_Member_DEL::mGroupName`,
`PRDemo.cpp:1770 MPR_A05_Tank_Controller_RAD::p_target`,
`Test_DME.cpp:313/822 ::destination_object`,
`Test_PDS.cpp:559/800/868 ::m_GameObj/GameObj`, and
`unitcombat.cpp:69-70 Unit_Combat::anim_script/speech_script`.
The `Test_Cinematic.cpp` pointers `Controls` and `NextParameter` are
already NULL-initialised in staging. `Controls` is owned by
`scripts-a35-cinematic-control-lifetime.patch`.

## Limits

- This is static evidence only. There is no save/load repro on host, in
  Vita3K or on hardware, and the M09 fix is host syntax-checked only.
- Only members are covered. Indeterminate non-pointer state is tracked in
  `SCRIPT_SAVE_STATE_GAPS.md`.
- Retail reachability was taken from the host retail copy and assumes it
  matches the Vita retail tree.
