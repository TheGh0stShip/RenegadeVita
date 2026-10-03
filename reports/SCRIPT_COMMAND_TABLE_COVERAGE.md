# Original script command table coverage

2026-10-03 source-only comparison; no compilation or launch. Native/runtime
gates remain0/10.

`python3 -m tools.audit_script_command_table` compares direct command calls
inside the selected Scripts.dsp declared-script bodies with lexical assignments
to the original Combat EngineCommands table. Current result:

| Scope | Distinct used commands | Missing assignments | Unresolved assignments |
| --- | ---: | ---: | ---: |
| Mission00, MissionX0, Mission01 declared script bodies |118|0|0|
| All selected DSP declared script bodies |179|0|0|

The source table has204 assigned fields in this lexical model. These counts
have different scopes from the supplied overview's campaign-wide143 used
commands and202 API functions; do not substitute one count for another.
Helper/global functions outside declared bodies, indirect function calls and
runtime behavior are outside this audit. Named assignments do not prove that
their owners compile, link, register or work on Vita. Platform preprocessor
branches are not evaluated; conflicting candidates stay unresolved.

The report includes SHA-256 identities for inspected original owners, Scripts.dsp
and scriptcommands.cpp. Full output is retained privately at
`build/script-command-table-20261003.json`. It contains source metadata only.
Five counterexample tests pass: comment/string masking, missing versus null,
conditional conflicts, unsupported expressions and repeated-owner provenance.

A parallel boundary inspection confirms the selected full-port CMake graph
defines original WWAudio and, with the original frontend, original game-mode
and movie owners. The no-op MovieGameMode Start_Movie is guarded by absence
of the original movie-owner define; the headless game-mode implementation is
guarded by absence of original game-mode ownership. Their source presence is
not evidence that native missions select those stubs. The logical sound command
uses original WWAudio logical sound creation, masks, radius and scene insertion;
that source route still needs AI-stimulus delivery evidence.

Original Scale_AI_Awareness changes sight range but leaves its hearing-scale
call commented out. This is original source behavior, not a newly established
port omission. Preserve it rather than implementing a different retail AI rule
from the summary alone.

Next verify native command behavior by original subsystem, including AI/actions,
logical sounds, triggers, objectives, cinematic actor lifetimes and save-state
restoration. The build/launch hold leaves those integration gates open.
