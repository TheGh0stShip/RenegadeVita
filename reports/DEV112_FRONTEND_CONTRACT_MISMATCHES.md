# Dev112 focused frontend contract result

The focused run completed 21 tests with two failures and 19 passes. Evidence:
`build/dev112-native-preflight/frontend-checkpoint-contracts.log` and `.exit`.

The failed assertions in `tools/test_a4_original_frontend_contract.py` encode
superseded source behavior, rather than observing a runtime failure:

- `test_controller_navigation_maps_to_wwui_without_breaking_gameplay_keys`
  requires the exact gameplay Start suppression condition and log message.
  The new native path intentionally forwards Start to original menu-toggle
  input and presents EVA from the outer runtime owner.
- `test_main_menu_tutorial_handoff_reaches_existing_original_m00_route`
  compares the first Input calls across the entire runtime file. The new pause
  helper contains earlier calls, so this no longer tests startup ordering.
  Later assertions in the same test also require post-menu StyleMgr
  reinitialization, which is intentionally removed to retain the WWUI lifetime.

The tests have not been changed or bypassed. Canonical closure is not claimed.
An updated contract needs separate startup and pause scopes, retained dialog
ownership, original Continue_Game, input-edge priming, dialog-before-world
teardown, disabled unsafe menu routes, and default-off checkpoint startup.
String checks alone cannot establish pause stability or save-load correctness.

The corrected native runtime compilation passed separately in
`build/dev112-native-preflight/runtime-corrected-compile.log`, with exit 0 in
`runtime-corrected-compile.exit`. All five changed native boundary translation
units have now compiled in the isolated preflight. This is not link/package or
Vita3K evidence and does not supersede the retained dev111 artifact identity.
