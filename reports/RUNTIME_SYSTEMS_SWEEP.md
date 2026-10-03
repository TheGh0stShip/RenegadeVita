# S6 runtime systems — frontend denominator in progress

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

Reproduce with `python3 -m tools.audit_sweep_systems --templates
<matching-generated-template-file> --output <inventory.json>`.

Next: owner/factory/callback graph and linked symbols; controls/styles and
navigation/input semantics; other source directories and numeric/dynamic
resource routes. Remaining S6 denominators cover gameplay modes, AI/actions,
bosses, physics, combat, presentation, audio and platform systems. Conditional
resources and duplicate declarations stay explicit risks. The full sweep and
physical behavior acceptance remain incomplete.
