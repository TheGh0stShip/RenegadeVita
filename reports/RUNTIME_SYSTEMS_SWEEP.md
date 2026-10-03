# S6 runtime systems — frontend denominator in progress

Reference evidence now distinguishes `#define IDD_*` declarations from source
uses and cross-checks translation-unit selection against the retained S3 build
inventory. Seven absent-template resources have uses in selected Commando
translation units: quit-to-desktop, main multiplayer, multiplayer connecting,
wheeled/tracked vehicle settings and GameSpy main/options. Selected source uses
may still be inactive branches or legacy provider routes. Included headers,
numeric/dynamic routes and other directories remain open, so seven is not a
complete runtime-need count. Resource definitions alone establish no caller.
Each reference has its source hash; the report pins the parent link inventory.
Two authored tests cover definition/use distinction and selected-unit matching.

The initial denominator enumerates all 112 dialog declarations in original
Commando/*.rc, with source lines, unique identities, resolved IDs and source
token-reference candidates. Dev209's retained generated template file contains
31 of these resources; 81 are absent. All 112 rows remain unknown because
template presence does not establish factory routing, actions or display, and
absence does not rule out alternate resource providers.

Absent-template leads include movie/credits, high-score tabs, multiplayer
options, LAN host tabs and settings, quick-match options and server-settings
save/load. Original tools/provider/debug dialogs are not excluded without
caller, retail and project-membership proof. Source token references include
header definitions; they are not automatically runtime callers.

The generator retains RC and template hashes and reproduces byte-for-byte.
Two authored inventory tests and seven existing style/resource tests pass,
including original frontend equivalence for 31 dialogs and 389 controls.
No runtime code or resource-selection set changed.

Reproduce with `python3 -m tools.audit_sweep_systems --link-inventory
reports/generated/sweeps/link.json --templates
<matching-generated-template-file> --output <inventory.json>`.

Next: owner/factory/callback graph and linked symbols; controls/styles and
navigation/input semantics; other source directories and numeric/dynamic
resource routes. Remaining S6 denominators cover gameplay modes, AI/actions,
bosses, physics, combat, presentation, audio and platform systems. Conditional
resources and duplicate declarations stay explicit risks. The full sweep and
physical behavior acceptance remain incomplete.
# Runtime owner groups added

## Input-lock owner trace

Source review locates the command-to-owner chain:
`staging/combat/scriptcommands.cpp:1505` forwards to SmartGameObj's
`Control_Enable`; `smartgameobj.h:130` stores the original ControlEnabled flag.
Original `smartgameobj.cpp:708` and staged `smartgameobj.cpp:731` gate Apply_Control
in Think. The disabled branch resets the controller and clears weapon triggers.
Original `ccamera.cpp:1443` and staged `ccamera.cpp:1448` return before ordinary
camera movement when the player's control flag is false. Save/load preserves
the flag in original microchunks. These are source findings, not execution proof.

The Vita input provider's `gameplay_input_active` at
`port/platform/renegade_directinput.cpp:609` distinguishes dialog navigation;
it does not itself inspect the mission control flag. Front touch feeds the
original left-mouse button at line 653, while back touch feeds the F binding
at line 650. Gameplay enforcement therefore requires the original control/action
and camera owners; a blanket provider shutdown would also affect frontend input.
Action-key side effects, menu access and cinematic camera paths still require
individual caller review. Do not infer that every input is suppressed by one gate.

The native `Control_Enable(true)` occurrence at
`port/platform/vita/a31_vita_runtime.cpp:2880` belongs to the bounded development
M13 A03 field setup. Its caller at line 4552 is guarded by development-checkpoint
configuration and a pending diagnostic route. It is not evidence of an ordinary
per-frame unlock. Diagnostic-route activation and natural mission routes must
remain separate in acceptance evidence.

Next evidence: host replay of original script lock/unlock, action and weapon
effects; balanced restoration across save/load and cinematic termination; then
authorized Vita/PSTV input replay with controller and touch. No runtime patch was
made because this trace does not establish a missing owner gate.

The input-lock denominator retains 23 `Control_Enable(...)` token occurrences
across staged and port C++/headers, including 17 Commands-member candidates.
Declarations and inactive branches remain visible; source lines/hashes and direct
translation-unit selection are recorded. Native restoration in the runtime is
included. Controller/touch enforcement and balanced lock/unlock paths remain open.
Four parser tests pass, including comment/string rejection and declaration retention.

S6 now retains 27 explicit gameplay/platform/presentation owner groups alongside
the 112 dialogs. Case-insensitive original path matching preserves source hashes,
unmatched patterns and source keys for S3 reconciliation. These are investigation
candidates, not proven complete caller closure or runtime acceptance. All groups
remain unknown; platform replacements and Control_Enable locks need deeper tracing.
