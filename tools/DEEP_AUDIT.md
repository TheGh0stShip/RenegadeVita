# Reproduce the cross-system static audit

The [authored-binding audit](../reports/AUTHORED_MISSION_BINDINGS.md) now retains
script parameters, spawner instance IDs and cinematic-to-script provenance.
It works without a configured build or executable:

```bash
python3 -m tools.audit_mission_content_bindings --data /absolute/path/to/user-owned/retail/Data --output-directory build/dev208-authored-bindings-20261003
python3 -m unittest tools.test_mission_content_bindings tools.test_m13_level_owners tools.test_deep_content_audit
```

Detailed receipts are restricted to build/. Tool execution does not pass a
mission gate; malformed bindings and unlocated references remain explicit.

The [follow-up sweep](../reports/DEEP_AUDIT_FOLLOWUP.md) adds nested W3D
reference discovery and source-traced bootstrap, progression and round-flow
findings. Run `python3 -m unittest tools.test_nested_w3d_references` for its
four parser checks; the combined audit suites now contain 81 checks.

Run from the active repository root. These Python tools inspect existing source,
build graphs, ELF symbols and user-owned retail data. They do not compile or
launch the game. Keep generated receipts local under `build/`; do not distribute
retail data or saves. The existing build must contain staged source, generated
resources and the matching executable. A stale build is historical evidence,
not evidence that current source changes have been compiled.

```bash
python3 tools/audit_requested_content.py --data build/host-m13-diagnostic/retail/Data --build build/vita-fast-candidate --output-directory build/dev208-deep-content --multiplayer
python3 tools/audit_cross_system_owners.py --build build/vita-fast-candidate --output build/dev208-cross-system-owners.json
python3 tools/audit_frontend_resources.py --build build/vita-fast-candidate --output build/dev208-frontend-resources.json
python3 tools/audit_w3d_loader_coverage.py --data build/host-m13-diagnostic/retail/Data --build build/vita-fast-candidate --output build/dev208-w3d-loader-coverage.json
python3 tools/check_deep_audit_receipts.py --maps build/dev208-deep-content/summary.json --frontend build/dev208-frontend-resources.json --owners build/dev208-cross-system-owners.json --w3d build/dev208-w3d-loader-coverage.json --output build/dev208-deep-coverage-gate.json
```

The last command currently **must exit 1**, reporting INCOMPLETE and 73 grouped
findings. Repeated map manifestations are not distinct bugs. This standalone
guard is not wired into the build and cannot establish runtime acceptance.

For authorized local saves, pass their directory explicitly; the scanner reads
recursively and writes metadata rather than save payloads:

```bash
python3 tools/audit_deep_saved_content.py --data build/host-m13-diagnostic/retail/Data --saves /absolute/path/to/local/saves --build build/vita-fast-candidate --output build/dev208-deep-saved-content.json
```

Asset-free, Python-only validation (77 checks):

```bash
python3 -m unittest tools.test_deep_content_audit tools.test_m13_level_owners tools.test_m13_script_coverage tools.test_m13_mission_inventory tools.test_script_provider_contract tools.test_a4_original_frontend_contract tools.test_mission_teardown_contract tools.test_mission_conversation_diagnostics_contract
```

See [the findings report](../reports/CROSS_SYSTEM_DEEP_AUDIT.md) for source
anchors, exclusions, architecture evidence and remaining dynamic uncertainty.
Do not equate an empty static finding list with successful native gameplay.
