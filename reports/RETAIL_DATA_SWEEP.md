# S4 retail closure — all-map binding discovery in progress

The all-map driver enumerates every supplied MIX filename plus all expected
campaign maps. The first scan retains 27 rows: 26 supplied maps audited and
one missing input, M09. This includes 12 campaign/tutorial maps, 13 C&C
multiplayer maps and Skirmish00. Missing-input rows remain visible; no map
is silently excluded. All statuses are unknown, not gameplay passes.

Six discovered script-name leads lack matching registration candidates and
retained ARM symbols: M04_ForeDeck_Reinforcement_03_JDG;
M05_Inn_Reinforcements; M05_Park_Unit; M11_ObeliskWall_FodderGuy01_JDG;
M11_ObeliskWall_FodderGuy02_JDG; M11_TempleRoof_FodderGuy02_JDG.
The M04 name is also attached by original Mission04.cpp:5352. The other
names require authored-binding/caller investigation. These findings do not
justify inventing new scripts or changing original behavior without evidence.

M09 backup copies were located locally. Input identity and completeness must
be verified before filling the missing row. Detailed bindings, parameters,
objects and IDs remain under ignored build/; published JSON retains map names,
hashes, aggregate counts and unresolved script-name leads only. No retail
payload or private root path is published.

Run `python3 -m tools.audit_sweep_retail --data <Data> --link-inventory
reports/generated/sweeps/link.json --private-output build/<receipt-directory>
--output <summary.json>`. Two tests cover expected/missing/non-campaign map
enumeration and registrar reconciliation without serialized parameters.

Open coverage: computed dependencies and IDs, remaining asset/loader classes,
frontend/global-only data, full factory numeric-ID reconciliation, runtime
mount order and actual script registration. The existing dependency parser's
structural findings remain review leads. This is the binding portion of S4;
the complete sweep and full-game acceptance remain open.
