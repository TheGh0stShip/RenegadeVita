# S3 link and registration closure — inventory in progress

The staged-source denominator contains 837 C/C++ translation units. The
retained Dev209 Ninja target selects 604; its link map mentions all 604 object
files. The remaining 233 units require classification, including potential
non-runtime sources. Selection and map mentions do not prove retained code,
static initialization, factory registration or functional behavior.

The upstream denominator now includes all 1,490 C/C++ units under Code,
including tools and editor code; 654 have no case-insensitive relative-path
staged counterpart. Case-insensitive matching retains all candidates rather
than silently resolving ambiguous names. These are unknowns, not exclusions.

Source discovery also retains 1,981 registration candidates: 1,744 scripts,
140 persist factories, 58 definition factories and 39 network factories.
Comments and ordinary string/character literals are masked with offsets
preserved. Inactive preprocessor branches remain candidates. Header/manual,
alternate/template registration forms, raw strings, console functions, game
modes and prototype registration still require discovery. Macro names and
symbolic IDs are not proof of retained initialization or numeric ID coverage.
Three authored tests pass, covering lexical masking and unstaged/case mapping
alongside the original target/map distinction test.

All staged, upstream and registration rows remain unknown. The generator retains source identities and the
map hash without publishing the raw map or private build paths. Current source
hashes do not establish that they match the original Dev209 build inputs.

Reproduce with `tools/audit_sweep_link.py --build <configured-build> --map
<matching-map> --target RenegadeVitaA31 --output <output.json>`. The authored
test separates target membership from map mentions, retains discarded-section
mentions as uncertain, and verifies deterministic rows and unique identities.

Next: classify upstream units absent from staging; expand static/manual
registrar discovery; distinguish discarded and retained sections using matching ARM
symbols and map; cross-check factory IDs against every retail map. This sweep
is incomplete and does not authorize exclusion of any original behavior.
