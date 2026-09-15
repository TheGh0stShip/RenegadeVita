# Dev133 repeated Load and Cycle Objectives

Dev132's extended native menu check found Load no longer opening after one full
save reload. Touch and Cross both failed while Save remained functional. The
original dialog manager allocates its auto-link factories at process startup,
deletes them in Shutdown, and never reconstructs them. Native session reload
re-enters the manager, so all six supported auto-links lose their factories.

The native boundary now restores missing factories during original Initialize;
original command dispatch, dialog types, and Shutdown ownership remain intact.
The retained original host test invokes the Load auto-link during both manager
lifetimes. Dev132 baseline opens it on cycle one and fails on cycle two:
build/dev133-factory-baseline-host.log. Corrected normal and UBSan runs pass both
cycles, build/dev133-factory-host.log and build/dev133-factory-ubsan.log. Final
combined validation follows the input correction below.

Help exposed unbound Cycle Objectives. SELECT tap now produces the original
DIK_BACK action on release, bound to INPUT_FUNCTION_CYCLE_POG; HUD still owns
objective selection. Any button/touch chord consumes the tap, preserving
SELECT+Square quicksave. Menu/IME/focus loss suppresses pending taps until
release. Help labels the action SELECT. The production gesture receives
ASan/UBSan tests for held input, both chord press/release orders, focus loss,
menu/diagnostic suppression and original logical key transitions.

SELECT screenshot diagnostics now require the explicit regular marker
ux0:data/renegade/user/config/input-capture-select.flag, read once at input
initialization. With the marker, legacy recorded SELECT capture edges remain
available and objective taps are suppressed; without it, SELECT cycles
objectives and does no capture/readback. Existing automatic first-frame capture
prohibition, checkpoint-readiness checks, exit/fatal evidence remain. This
removes an input conflict; no measured FPS improvement is claimed.

Combined retained normal and UBSan runs PASS two M00 cycles each, with both
factory auto-link and original CyclePog binding assertions:
build/dev133-host.log and build/dev133-ubsan.log. SELECT/capture/camera contracts
PASS in build/dev133-select-tests2.log. Source is frozen for ARM build.

Incremental ARM, 152 focused checks and ELF/SELF/VPK identity PASS. Matching
artifacts are frozen at build/dev133-closed-incremental/receipt.json (34 files).
Runtime return: build/dev133-reload-return/return-receipt.json (275 files).
Four complete original reloads of new Manual savev returned to Hotwire gameplay;
Load reopened after every reload. Touch opens Load Delete, controller No preserves
the exact SHA256, controller reopens the prompt and Yes removes only that file.
All 14 existing saves remain byte-identical. SELECT feeds the original CyclePog
input with no manual screenshot; Help visibly labels it SELECT. The current
checkpoint has no displayed active HUD objective, so visible POG switching is
not established. Native END clean and separate unforced owned-shell stop are
retained; wrapper PROCESS_FAILED/null is not a zero process exit.

109 native steps have release acknowledgments. One additional accepted Load
step ended its native input session during teardown before acknowledgment;
full teardown/new session and subsequent neutral/input operation are retained.
Initial unfocused host-window touch was ineffective; rejected size checks sent
no press, followed by explicit release and owned-window size correction. These
are automation limits, not native renderer changes. Two controller attempts to
reach Load Delete instead loaded the selected test save; explicit list-to-button
focus regression is still needed. Touch/focused-controller Delete itself passes.
The Hotwire walk used original camera/movement/collision, but did not reach a
vehicle entry or building destruction. Those populated-page checks remain open.

Follow-up original host focus test PASS in both manager lifetimes:
build/dev133-focus-followup-host.log. From the Load list, four VK_TAB transitions
reach Back (11034), Delete (11036), Load (11037), and List (11035). Delete is the
second SELECT stop; no production focus defect reproduced. The optional private
fixture test is newer than the frozen Dev133 package and does not alter it.
Its initial compilation failed for a missing listctrl.h include; corrected build
and two complete host cycles pass. The native controller sequence is next.

Next: targeted original discovery checkpoints and further hardware FPS audit.
Physical testing is held; Vita3K
functional evidence remains separate from hardware performance/acceptance.
0/10 release gates; no new native FPS claim.
