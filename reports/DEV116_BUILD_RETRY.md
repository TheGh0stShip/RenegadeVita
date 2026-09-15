# Dev116 build retry

First canonical attempt failed at the host interactive compile:
`Probe_Original_HUD_Digit_Atlas` was not declared at its call sites.
The new probe header include had been placed after main, not before it.

Moved that include into the existing include block, before use. No gameplay
code or test assertion was removed. The failed attempt remains retained in
`build/dev116-canonical.log`; its last successful dist release was unchanged.

Retry launched with the same explicit Dev116 label, checkpoint enabled,
default full staging and `CCACHE_NODIRECT=1`.
Current output: `build/dev116-canonical-retry.log`.
The retry is not yet accepted as a successful build.

## Integrated host evidence

The retry reached ARM compilation after passing the integrated HUD probes.
Both original digit atlases matched their source pixels: FONT12x16 compared
1712 pixels and FONT6x8 compared 384 pixels, each with zero mismatches.
The original M00 interactive host runtime reported PASS for two in-process
cycles. These are canonical integrated results, not only the earlier isolated
experiment. Retained output is in the retry log around lines 34198-34447.

Native compilation was observed at task 321/558. Final artifact closure and
native visual correctness remain pending; do not promote the build yet.
