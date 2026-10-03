# S3 link and registration closure — inventory in progress

The staged-source denominator contains 837 C/C++ translation units. The
retained Dev209 Ninja target selects 604; its link map mentions all 604 object
files. The remaining 233 units require classification, including potential
non-runtime sources. Selection and map mentions do not prove retained code,
static initialization, factory registration or functional behavior.

All 837 rows remain unknown. The generator retains source identities and the
map hash without publishing the raw map or private build paths. Current source
hashes do not establish that they match the original Dev209 build inputs.

Reproduce with `tools/audit_sweep_link.py --build <configured-build> --map
<matching-map> --target RenegadeVitaA31 --output <output.json>`. The authored
test separates target membership from map mentions, retains discarded-section
mentions as uncertain, and verifies deterministic rows and unique identities.

Next: enumerate upstream units absent from staging; discover static/manual
registrars; distinguish discarded and retained sections using matching ARM
symbols and map; cross-check factory IDs against every retail map. This sweep
is incomplete and does not authorize exclusion of any original behavior.
