# Static script linkage and mission-rank storage — 2026-10-03

The expanded campaign manifest exposed a collision between two original
`strtrim(char *)` definitions. The source sweep also confirmed that mission
ranks had no persistent native storage. Both have source changes now; C++
compilation, linking, restart behavior and physical acceptance remain open.
The user's build/launch hold remains active.

## Original script linkage

`Scripts/strtrim.cpp` and `wwlib/trim.cpp` define the same external function.
They previously belonged to different executable/DLL images. Selecting all
44 original Scripts.dsp code units joins both definitions in the port.
Their whitespace handling differs, so substituting the WWLib implementation
for the Scripts implementation would change original parameter parsing.

`cmake/RenegadeScriptSources.cmake` now assigns
`strtrim=Renegade_Script_strtrim` only to the original Scripts definition and
its caller, `Scripts/scripts.cpp`. Both native and host configuration invoke
that helper. The original source remains unchanged; WWLib and unrelated
mission units receive no rename. This addresses the source-confirmed collision
without claiming a successful final link.

The source guards now require the manifest variable in the native source set
and the retained host executable's source list. A variable name in a configure
call or compile property no longer suffices. Negative-control fixtures remove
each actual attachment while retaining those other references. Compiler-free
CMake fixtures inspect the two source properties and independently reject a
missing caller or definition rename. The manifest parser additionally rejects
duplicate, invalid or missing original filenames.

The integration-report generator also expands Scripts.dsp where that manifest
is attached to the native source graph. Its report previously omitted those
indirectly selected units. These parsers handle the repository's supported
manifest structure; they are not a complete CMake interpreter or symbol check.

## Mission ranks and replay access

Original ownership is unchanged:

- `Commando/scorescreen.cpp:178` submits the calculated overall stars.
- `LoadSPGameMenuClass::Set_Game_Rank` strips the four-character extension,
  retains the maximum of old and new ranks, and calls `RegistryClass::Set_Int`.
- `Get_Game_Rank` reads the same key; the replay menu consults it for access.

The registry boundary now routes only the configured original mission-rank
key to `port/filesystem/renegade_mission_ranks.h`. Native and retained host
startup resolve `user/config/mission-ranks-v1.cfg` beneath their user root
before activating the original frontend. Native storage is therefore
`ux0:data/renegade/user/config/mission-ranks-v1.cfg`. No retail file or original
save chunk is changed. General registry bulk-load/save methods remain separate
open work; this change does not claim to persist every registry preference.

The provider preserves case-insensitive ASCII mission-name lookup, stored
name spelling, signed 32-bit values and RegistryClass read-only behavior.
It bounds storage at 128 entries and 95 characters per name. The versioned
text file has an exact header, declared record count and mandatory end marker.
Missing rows, truncation at row boundaries, duplicate names ignoring case,
out-of-range values, embedded NULs and trailing data are rejected. This is
structural validation, not a checksum or detection of every possible mutation.

An unreadable or malformed existing file disables writes and leaves that file
untouched; the current binding exposes default ranks and logs the load error.
This conservative behavior does not recover lost progression automatically.
Writes create a sibling temporary file, check stream writes, flush, fsync,
close and rename, and publish new in-memory values only after success. A
process mutex serializes provider access. Power-loss durability, filesystem
semantics on Vita and interaction with live score/replay screens need testing.
This is not a multi-process profile service.

Registry-key composition was also corrected to insert one backslash separator,
matching the original `Commando/init.cpp` helper. The prior boundary inserted
two. Other registry providers retain their existing storage ownership.

## Evidence retained

41 source/CMake/Python diagnostic checks pass across:

```sh
python3 -m unittest \
  tools.test_requested_mission_owner_contract \
  tools.test_script_provider_contract \
  tools.test_audit_campaign_source_surface \
  tools.test_renegade_script_dsp_cmake \
  tools.test_m13_script_coverage \
  tools.test_integration_source_inventory \
  tools.test_analyze_runtime_gaps \
  tools.test_collect_pstv_runtime_log \
  tools.test_validate_campaign_flight_bundle -q
```

Shell syntax, Python syntax and `git diff --check` pass. The campaign inventory
was regenerated with the strengthened selection and symbol-isolation checks.
These results do not exercise the new C++ storage provider.

Publication checks also pass: 32 guard tests, validation of 24 public documents
and repository hygiene with no violations. They validate publication only.

Prepared but **not compiled or run**:

- `tools/test_vita_mission_ranks.py`: sanitizer probe using production storage,
  separate processes, replacement/delete, deterministic failed writes, signed
  boundaries, capacity/name limits and 21 malformed/truncated file cases.
- `--mission-ranks-selftest`: retained host probe through the original public
  `Set_Game_Rank` and RegistryClass paths, covering best-rank retention,
  extension/case, read-only protection, reload and deletion.

Both build entry points include the new static contracts and the future rank
test; the normal/sanitized host runner includes the original-owner probe.
Do not run these compiling tests while the build hold applies.

Installed toolchain metadata reports `arm-vita-eabi`, GCC 15.2.0. Read-only
ELF attribute inspection of installed `libpthread.a` and `libstdc++.a` reports
ARMv7 Application profile and VFP-register arguments for all 134 and 191
reported attribute blocks respectively. Native remains little-endian ARMv7-A
ILP32, not AArch64. The existing native ABI header enforces target widths and
endianness. This inspection is not an ARM compilation of the changes or a
complete dependency audit.

## Remaining campaign work

The original DSP inventory now selects every campaign source unit, but linked
factory presence and runtime registration still require matching artifacts.
Retail object-ID ownership, dynamic script parameters and media closure remain
open. M01's attached `X01_ConYardDrop.txt` is still unresolved. Death/failure,
save/load feedback, unsupported Options routes, radio input, round transitions
and projector targets retain their previously documented gaps. Existing short
Dev197 PSTV logs do not verify these changes or a complete mission route.
No new native mission/runtime gate is closed.
