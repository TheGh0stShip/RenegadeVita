# Dev118 original NPC path service

User reports Logan never walks during Follow Me segments, then player controls
remain locked after MTU_LOGAN_OUTRO and the GDI lieutenant never approaches.
Retained Dev117 recovery-r2 log advances through frame 33120 after the outro at
21926–21928. This is an advancing simulation with a stalled mission sequence,
distinct from the previous WF/Refinery freeze. Snapshot and hashes are under
build/dev117-finale-stall/. No gameplay input or save mutation was performed.

Original Mission00.cpp disables player control at ACTIVATE_FINALE and waits for
MTU_ACTION_MOVE_LOGAN_EXIT before starting the lieutenant's approach. Original
GotoActionCodeClass waits while its PathSolveClass remains THINKING. The desktop
Commando mainloop.cpp calls PathMgrClass::Resolve_Paths before game-mode Think;
the Vita simulation boundary omitted this service despite initializing and
shutting down the original path manager. That omission is a demonstrated
integration defect and a likely cause of the reported movement/finale failure.

Restored the original camera-prioritized Resolve_Paths call before control,
network and simulation updates in port/platform/a31_gameplay_boundary.cpp.
The existing inactive-Combat return keeps pause suspended. The original default
5 ms solver budget, path data, actions, mission callbacks and control ownership
are unchanged. Platform performance counters already provide monotonic ticks
and matching frequency. No mission bypass or forced completion is introduced.

Validation: 18 focused checks pass (build/dev118-npc-focused.log), including
execution of the production frame function with observable engine-owner doubles
for path/control/network/simulation ordering, no-camera and suspended-frame
behavior. Affected ARM boundary object compiled successfully in the existing
fast tree (build/dev118-npc-arm.log). These checks do not execute the path solver
or prove NPC traversal; matching runtime testing remains required.

Dev118 consolidated fast package now passes 130 focused contracts, original
DDS alias executable validation, ARM link/SELF/VPK closure and identity checks.
All 2430 captured source hashes remained unchanged through the build. Matching
ELF/map/symbols/header, package inventory, compiler log and manifests are in
dist/. Original PathMgrClass::Resolve_Paths is now present in the linked ELF.
Installed Dev117 and its current user session remain untouched.

SELF: 4a6c1a14c17f078e3062014ff055920c3f7cf4010f16c431280d1fba1d6ed642
VPK: 181d9bf49fa450fece7b2cbe0784bbecce577c8e61804dfe8d10e4c785cc08ba
ELF: 217eb3a64b98ab92fdbf185bb92f357d4d6b20abe202b44dc7be5bc50505ec2c

Next: reload the immutable Power Plant save into a
fresh slot when the current user session can be replaced, then observe Logan's
exit, lieutenant approach, original officer objective and mission completion.
Sky and elevator visual defects remain open. Physical PS Vita/PSTV access held.
