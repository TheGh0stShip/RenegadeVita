# Dev129 continuing pause-menu work

## Latest return and Dev130 work (authoritative over historical notes below)

Dev129 is frozen in `build/dev129-closed-incremental/receipt.json` (30 files).
The all-item emulator audit is retained in
`build/dev129-pause-return/return-receipt.json` (101 files).
No physical test occurred. All seven tabs and all six bottom actions were
attempted through the actual original UI, using bounded released input.

| Item | Dev129 observed result |
| --- | --- |
| Objectives / Map / Data | Original text, map, statistics visible. |
| Four discovery tabs | All open, all empty; unchanged checkpoint has zero discovery entries, while INI objects load 48/25/36/18. Populated models/descriptions unproven. |
| Help | Original diagram and Vita control labels visible; Circle returns. Cycle Objectives remains unbound. |
| Options | Audio/Video/Performance pages render and controls respond. Dialogue slider changes; fixed native display/audio capabilities shown. Desktop configuration instructions remain. Load/restart persistence absent. |
| Save | Empty Slot creates original M00 savegame01.sav, 97,728 bytes; strict chunks pass. Private archive kept outside telemetry; metadata hash edb0e6eb2d45f3ebb2f7c830a676469aa3deca9fdd4e9e731b05c66869515814. Existing saves unchanged. Dates incorrectly show 1965. |
| Load | Blank backdrop; original dialog resource 145 omitted. Circle returns. Round trip not performed. |
| Exit / delete confirmations | Exit popup incomplete; resources 209/210 omitted. Circle cancels. Delete and clean exit unproven. |
| Mobius START / Resume | START injected at original active speech frame 2; EVA stays usable. Resume returns to gameplay, then input/log progress stops shortly after frame 600. Owned forced stop; stability failed. |

Dev130 plan: include all original resources, fix settings persistence through
original setters and native user storage, diagnose incorrect save dates and
post-resume hang, repeat all controls and populated discovery from a fresh run.
Keep physical deployment held and continue the hardware optimization ledger.

Dev130 source/check update: 179 zero-fuzz patches stage successfully. All 22
dialog resources / 257 controls match independent LLVM RC output, including
explicit coverage of Load and both confirmation owners. User preference file
replacement, malformed/corrupt data, failed writes and exact budget retention
pass combined ASan/UBSan (`build/dev130-preferences-contract2.log`).
The original Options UI passes two M00 host cycles, including reload from disk,
actual volume setters and preservation of 12345/6789 scene budgets when another
control changes (`build/dev130-settings-m00-host.log`). Save paths pass 22
checks. Retained M00 UBSan is building; native RTC dates and full UI behavior
remain pending ARM/runtime evidence. Projector, particle and NPatches controls
are disabled consistently with this port's existing native capabilities;
the main quality slider now leaves disabled controls unchanged.

Controlled Dev129 baseline: same SELF and emulator rendering backend, one
persistent guest debugger connection, unchanged refinery save. Without the long
pause/settings/save sequence, Mobius completes at frame 471 and the game accepts
movement/action input through frame 8160. Final START enters EVA. The owned
240-second watchdog ends the run; this is not clean-exit or hang-fix acceptance.
Natural discovery attempts did not establish a revealed entry; the original
Soldier poke requires the HUD information target within **2 metres**. No reveal
bits or retail data were changed. Evidence:
`build/dev129-mobius-debug-return/return-receipt.json` (40 files).
Two preceding debugger setup runs never reached gameplay and are excluded.
The guest debugger needs one persistent client, explicit initial continue and
the Windows host address; this version cannot detach/reconnect reliably.

Dev130 retained M00 UBSan passes two cycles with no findings; all 149 focused
checks pass. Native ARM compilation is running with source frozen.

The first Dev130 build process ended with signal 15 / status 143 after 493/563
actions, without a compiler diagnostic. Remaining compiler processes ended;
the unchanged candidate resumes incrementally in `build/dev130-fast-console2.log`.
Keep the first console log as interrupted-build evidence, not a passed package.

User directs independent verification of every pause tab and button. Continue
without asking the user to discover failures. Native ARM/GXM and physical Vita
limits govern implementation; Vita3K is functional evidence only. Physical
testing stays held while correctness and the 60 FPS optimization audit continue.
Release acceptance remains 0/10.

## Dev128 return

Incremental native build passed 146 focused checks and artifact identity.
SELF: `3830e5e57191939e33e9eac6f98a607640bcd67c903258aa6d45f761d10d1df0`.
VPK: `a411996dd1eab1f60a6185458d23fe14b6559d802d2a8431512c19030ba46611`.
The matching emulator run consumed the unchanged refinery checkpoint. Evidence:
`build/dev128-pause-return/return-receipt.json` (80 retained files).

| Item | Observed result |
| --- | --- |
| Objectives | Title, four accomplished objectives and descriptions visible. |
| Map | Tutorial map and title visible; black square corrected in this emulator return. |
| Data | Statistics labels and values visible. |
| Characters / Weapons / Vehicles / Buildings | All reachable, all lists empty at the old checkpoint; discovery-state versus content cause remains open. |
| Resume | Original Combat resumed and Mobius gameplay visible. |
| Help / Save / Load / Options | Source explicitly disables them; not functional. |
| Front touch | Wrong coordinates: 640x480 mapping drives the 800x600 presented menu; bottom actions cannot be reached correctly. |
| Exit | Run ended by owned forced stop; no clean-exit acceptance. |

Key captures: `step-20260914T224950790Z.png` (Map),
`step-20260914T225011832Z.png` (Data), and
`step-20260914T225026264Z.png` through `step-20260914T225031845Z.png`
(four viewer tabs), all in the return directory. The second pause happened after
the Mobius conversation had completed; it does not prove START during speech.
Native input receipts in `build/dev128-*.json` record release acknowledgments;
Windows touch/key receipts are also retained. Attempted bottom-row touches hit
the wrong controls and must not be counted as successful button tests.

## Current changes and checks

- DDS on-disk surface pointer now keeps its original four-byte representation
  on LP64 hosts, with a 124-byte compile-time layout check. Vita's disk layout
  is unchanged. Independent literal DDS fixture passes 11 checks. The stronger
  retained M00 host assertion requires the actual 512x512 map and passes two
  cycles: `build/dev129-map-m00-host.log`.
- Front touch uses the inverse current presentation rectangle and original
  logical resolution. Pillarbox taps do not become clicks. Production inverse
  mapping, bottom buttons, gameplay identity and invalid coordinates pass
  ASan/UBSan; 15 combined input/frontend checks pass in
  `build/dev129-touch-tests.log`. Native compilation/runtime remain pending.
- Original Help and Save owners are selected. Help uses physical control labels
  and returns to its parent menu. Save entry data uses existing pointer-token
  ownership and actual free-space queries on the user volume. 15 resources and
  167 controls match independent LLVM RC output (`build/dev129-expanded-rc.log`).
- Save/Load enumeration roots were never installed. Native and host lifecycle
  now install the actual roots. Original data/save and bare .sav requests map
  to the same user save namespace, with focused checks being compiled.
- Per-viewer bounded counts will distinguish missing INI content from hidden
  discovery entries. No fabricated reveals or retail/save edits are introduced.
  Structural parsing now confirms all four discovery chunks in the retained
  Dev117 refinery save have zero bytes (metadata only:
  `build/dev128-checkpoint-discovery-metadata.json`). A fresh session must prove
  original discovery, populated entries, models and descriptions.
- Load now queues the selected original source and leaves pause, then requires
  complete original session teardown before the outer lifecycle starts another
  original load. The active host build includes a deferred-request lifecycle
  check. This source is not yet ARM/runtime validated; Options remains disabled.

## Latest local validation

Help/Save/deferred Load host build and two original M00 cycles passed in
`build/dev129-help-save-load-m00-host.log`. Save-root/free-space tests passed
19 cases. Dev128 binaries and dependencies are frozen in
`build/dev128-closed-incremental/receipt.json` (30 files).

Original Tech Options and its Audio/Video/Performance pages are now selected
and host-linked. All 19 resources / 247 controls match LLVM RC. The native UI
shows physical 960x544 output and fixed audio/display capabilities; unsupported
gamma/device switches are disabled. Closing unchanged performance controls must
preserve custom scene budgets. A production-owner host check is building.
Registry settings currently persist within the process only; restart persistence
is not established. These source changes have no ARM/runtime acceptance yet.

Further source audit: the native session constructs a new WWAudio object and
calls the fixed-format Initialize overload, so even same-process Load can reset
changed volumes. Original UI writes RegistryClass, but the lifecycle does not
consume those saved category settings. Validate the UI first, then repair
bounded user-config persistence and reapplication through original setters.
Do not claim settings survive Load or application restart in Dev129.

The Save audit also found keyboard-required empty descriptions and desktop
relative deletion paths. New native slots default to "Manual save"; Save and
Load deletion now use the same bounded user-save namespace as enumeration.
Controller text renaming remains unavailable. All 22 save-path checks now pass
(`build/dev129-save-files-contract.log`), including case-insensitive deletion
and rejection of retail/traversal requests. Two original M00 host cycles now
exercise the original Tech Options and three child pages, change the sound
volume through the original slider callback, and preserve non-preset scene
budgets and texture reduction on close (`build/dev129-settings-m00-host.log`).
The host audio provider is deliberately silent: this validates UI/state wiring,
not native sound output. Native builds retain original WWAudio.cpp methods.
24 focused checks pass (`build/dev129-pause-focused.log`).

Retained UBSan now passes two original M00 cycles, actual settings-dialog
behavior and the fresh original MTU_Commando starting-weapon discovery event:
`build/dev129-settings-m00-ubsan.log`. No sanitizer findings. The old checkpoint
still has no prior discovery bits; no synthetic reveals were added.

The first fast gate exposed three obsolete test assumptions after the touch
helper and reload API changes. Corrected extraction/API checks and actual clean
reload/failed-teardown cases pass. All 147 fast checks now pass; the Dev129 ARM
build and package verification now pass (`build/dev129-fast-console3.log`).
The intermediate link succeeded; its old two-argument symbol check was corrected
in both build scripts for the deferred-load API. All 147 checks passed again.
ELF/SELF/VPK identities and inventory passed. Supplemental source/dependency
identity and telemetry closure precede the next bounded emulator test.
The next emulator run includes a bounded watcher that presses START immediately
after gameplay activates while the original Mobius conversation is active.

## Next steps

1. Finish focused host/ARM compilation of Help, Save, touch, disk-space and save
   path routing; fix any failures before candidate packaging.
2. Validate deferred Load and the restored original Options controls, including
   unchanged settings on close, volume changes and save creation/deletion.
3. Diagnose the empty viewer lists with the new counts and original discovery
   behavior. Check models, text and navigation for genuinely revealed entries.
4. Close Dev129 artifacts, run every page/button and save/reload in bounded
   Vita3K checks, test START during the retained Mobius speech window, and retain
   matching evidence. Continue the existing native optimization route ledger.

No claim of full pause-menu completion, physical correctness or 60 FPS.
